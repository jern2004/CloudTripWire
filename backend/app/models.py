from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Incident(Base):
    """Incident database model"""
    __tablename__ = "incidents"
    
    id = Column(String, primary_key=True, index=True)
    cloud = Column(String, nullable=False)  # AWS, Azure, GCP
    principal = Column(String, nullable=False)  # User/Service that triggered
    trigger_type = Column(String, nullable=False)  # Type of access
    timestamp = Column(String, nullable=False)  # ISO timestamp string
    status = Column(String, default="Active", nullable=False)  # Active or Resolved
    region = Column(String, nullable=True)
    severity = Column(String, nullable=False)  # Critical, High, Medium, Low
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    resource_arn = Column(String, nullable=True)
    
    # JSON fields for complex data
    response_actions = Column(JSON, nullable=True)  # List of automated responses
    timeline = Column(JSON, nullable=True)  # Event timeline
    threat_indicators = Column(JSON, nullable=True)  # Threat intelligence data
    evidence = Column(JSON, nullable=True)  # Links to evidence (logs, screenshots)
    
    def __repr__(self):
        return f"<Incident {self.id}: {self.cloud} - {self.status}>"
