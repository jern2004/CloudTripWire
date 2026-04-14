from datetime import datetime
import uuid


def generate_incident_id() -> str:
    """
    Generate a guaranteed-unique incident ID.
    Format: inc-<8 hex chars>  e.g. inc-3f2a1b4c
    Uses UUID4 so collisions are cryptographically impossible.
    """
    return f"inc-{uuid.uuid4().hex[:8]}"


def get_severity_level(trigger_type: str) -> str:
    """
    Determine severity level based on trigger type
    
    Args:
        trigger_type: Type of honeytoken trigger
        
    Returns:
        Severity level: Critical, High, Medium, or Low
    """
    critical_triggers = ["IAM Root Access", "Database Root Login", "Key Vault Access"]
    high_triggers = ["S3 Access", "S3 Bucket Access", "Lambda Invocation", "Storage Blob Read"]
    medium_triggers = ["DynamoDB Query", "API Call"]
    
    if trigger_type in critical_triggers:
        return "Critical"
    elif trigger_type in high_triggers:
        return "High"
    elif trigger_type in medium_triggers:
        return "Medium"
    else:
        return "Low"
