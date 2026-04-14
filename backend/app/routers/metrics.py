from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas import MetricsResponse
from app.database import get_db
from app.models import Incident

router = APIRouter(prefix="/api", tags=["Metrics"])


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(db: Session = Depends(get_db)):
    """
    Get current incident metrics/statistics
    
    Returns:
        Dashboard metrics including total, active, and cloud-specific incident counts
    """
    # Count total incidents
    total = db.query(Incident).count()
    
    # Count active incidents
    active = db.query(Incident).filter(Incident.status == "Active").count()
    
    # Count resolved incidents
    resolved = db.query(Incident).filter(Incident.status == "Resolved").count()
    
    # Count AWS incidents
    aws = db.query(Incident).filter(Incident.cloud == "AWS").count()
    
    # Count Azure incidents
    azure = db.query(Incident).filter(Incident.cloud == "Azure").count()
    
    return MetricsResponse(
        total_incidents=total,
        active_incidents=active,
        resolved_incidents=resolved,
        aws_incidents=aws,
        azure_incidents=azure
    )
