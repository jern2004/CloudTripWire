from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class IncidentBase(BaseModel):
    """Base incident schema"""
    cloud: str
    principal: str
    trigger_type: str
    region: Optional[str] = None
    severity: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource_arn: Optional[str] = None 


class IncidentCreate(IncidentBase):
    """Schema for creating a new incident"""
    response_actions: Optional[List[Dict[str, Any]]] = None
    timeline: Optional[List[Dict[str, Any]]] = None
    threat_indicators: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, str]] = None


class IncidentResponse(IncidentBase):
    """Schema for incident API responses"""
    id: str
    timestamp: str  # ISO format string
    status: str
    response_actions: Optional[List[Dict[str, Any]]] = None
    timeline: Optional[List[Dict[str, Any]]] = None
    threat_indicators: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, str]] = None
    
    class Config:
        from_attributes = True


class MetricsResponse(BaseModel):
    """Schema for metrics API response"""
    total_incidents: int
    active_incidents: int
    resolved_incidents: int
    aws_incidents: int
    azure_incidents: int


class TimeSeriesDataPoint(BaseModel):
    """Schema for time series data point"""
    date: str
    count: int


class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str
    service: str
