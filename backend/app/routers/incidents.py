from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
from app.schemas import (
    IncidentResponse, 
    IncidentCreate,
    TimeSeriesDataPoint
)
from app.database import get_db
from app.models import Incident
from app.core.utils import generate_incident_id, get_severity_level

router = APIRouter(prefix="/api", tags=["Incidents"])


@router.get("/incidents", response_model=List[IncidentResponse])
async def get_incidents(
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    cloud: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get list of incidents with optional filters
    Frontend calls: fetchIncidents({ limit: 10 })
    """
    query = db.query(Incident).order_by(desc(Incident.timestamp))
    
    # Apply filters if provided
    if status:
        query = query.filter(Incident.status == status)
    if cloud:
        query = query.filter(Incident.cloud == cloud)
    
    # Limit results
    incidents = query.limit(limit).all()
    
    return incidents


@router.get("/incident/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific incident
    Frontend calls: fetchIncidentById(id) -> GET /api/incident/{id}
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    
    return incident


@router.post("/incidents", response_model=IncidentResponse, status_code=201)
async def create_incident(
    incident: IncidentCreate,
    db: Session = Depends(get_db)
):
    """Create a new incident"""
    # Generate unique ID
    incident_id = generate_incident_id()
    
    # Ensure severity is set
    severity = incident.severity if incident.severity else get_severity_level(incident.trigger_type)
    
    now = datetime.utcnow().isoformat() + "Z"

    # Create database object — use Lambda-provided values when present, fall back to defaults
    db_incident = Incident(
        id=incident_id,
        cloud=incident.cloud,
        principal=incident.principal,
        trigger_type=incident.trigger_type,
        region=incident.region,
        severity=severity,
        ip_address=incident.ip_address,
        user_agent=incident.user_agent,
        resource_arn=incident.resource_arn,
        status="Active",
        timestamp=now,
        timeline=incident.timeline or [
            {"event": "Honeytoken Triggered", "timestamp": now}
        ],
        response_actions=incident.response_actions or [
            {"action": "Credential Revoked", "timestamp": now, "status": "Success"}
        ],
        threat_indicators=incident.threat_indicators or {
            "is_vpn": False,
            "is_tor": False,
            "is_known_attacker": True,
            "geo_location": "Unknown"
        },
        evidence=incident.evidence or {
            "cloudtrail_log": "https://s3.amazonaws.com/evidence/cloudtrail.json",
            "vpc_flow_logs": "https://s3.amazonaws.com/evidence/vpc-flow.log"
        }
    )
    
    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)
    
    return db_incident


@router.patch("/incident/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: str,
    update_data: dict,
    db: Session = Depends(get_db)
):
    """
    Update incident (mark as resolved)
    Frontend calls: markIncidentResolved(id) -> PATCH /api/incident/{id} with {status: 'Resolved'}
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    
    # Update status if provided
    if "status" in update_data:
        incident.status = update_data["status"]
    
    db.commit()
    db.refresh(incident)
    
    return incident


@router.get("/incidents/timeseries", response_model=List[TimeSeriesDataPoint])
async def get_timeseries(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Get daily incident counts for the line chart.
    Frontend calls: fetchTimeSeriesData(7) -> GET /api/incidents/timeseries?days=7

    Timestamps are stored as ISO strings ("2025-10-27T14:23:45Z").
    We pull all incidents in the window, then bucket them by the date
    prefix (first 10 chars) in Python — avoids SQLite strftime quirks.
    """
    start_date = datetime.utcnow().date() - timedelta(days=days - 1)
    end_date   = datetime.utcnow().date()

    # Fetch only the timestamp column for efficiency
    rows = (
        db.query(Incident.timestamp)
        .filter(Incident.timestamp >= start_date.isoformat())
        .all()
    )

    # Count how many incidents fall on each date
    counts: dict[str, int] = {}
    for (ts,) in rows:
        date_key = ts[:10]  # "2025-10-27T..." -> "2025-10-27"
        counts[date_key] = counts.get(date_key, 0) + 1

    # Build a result for every day in the range, filling zeros for quiet days
    results = []
    current = start_date
    while current <= end_date:
        results.append(TimeSeriesDataPoint(
            date=current.isoformat(),
            count=counts.get(current.isoformat(), 0)
        ))
        current += timedelta(days=1)

    return results
