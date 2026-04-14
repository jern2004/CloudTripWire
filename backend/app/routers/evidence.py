from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Incident

router = APIRouter(prefix="/api", tags=["Evidence"])


@router.get("/evidence/{incident_id}")
async def get_incident_evidence(
    incident_id: str,
    db: Session = Depends(get_db)
):
    """Get evidence files for an incident"""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    
    if not incident.evidence:
        return {"evidence": {}, "message": "No evidence available"}
    
    return {
        "incident_id": incident_id,
        "evidence": incident.evidence
    }
