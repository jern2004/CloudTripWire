"""
isolate_and_log.py
──────────────────
AWS Lambda function — triggered by EventBridge when a honeytoken is accessed.

What it does:
  1. Reads the CloudTrail event from EventBridge
  2. Extracts who, what, where, how, when
  3. Determines severity based on the signals
  4. Disables the IAM key that was used
  5. Isolates EC2 instance if the attack came from inside your network
  6. POSTs the full incident to your CloudTripwire dashboard

Triggered by:
  - EventBridge rule: detect-honeytoken-iam  (IAM key used)
  - EventBridge rule: detect-honeytoken-s3   (S3 canary accessed)

Environment variables (set in Lambda console):
  DASHBOARD_API_URL  — your FastAPI endpoint e.g. https://abc123.ngrok.io/api/incidents
  HONEYTOKEN_USER    — the decoy IAM username (default: honeytoken-user)
  QUARANTINE_SG_ID   — optional: a Security Group with no rules to isolate EC2 instances
"""

import json
import os
import ipaddress
import urllib.request
import urllib.error
import boto3
from datetime import datetime, timezone

# ── Config from environment variables ─────────────────────────────────────────

DASHBOARD_URL   = os.environ.get("DASHBOARD_API_URL", "http://127.0.0.1:8000/api/incidents")
HONEYTOKEN_USER = os.environ.get("HONEYTOKEN_USER",   "honeytoken-user")
QUARANTINE_SG   = os.environ.get("QUARANTINE_SG_ID",  None)

# ── AWS clients ────────────────────────────────────────────────────────────────

iam = boto3.client("iam")
ec2 = boto3.client("ec2")

# ── Private IP ranges — if source IP is here, attacker is inside your network ─

PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]

# ── MITRE ATT&CK mapping ───────────────────────────────────────────────────────
# Maps CloudTrail eventName → MITRE technique

MITRE_MAP = {
    # Discovery / Reconnaissance
    "ListBuckets":            {"id": "T1526",   "tactic": "Discovery",           "name": "Cloud Service Discovery"},
    "DescribeInstances":      {"id": "T1526",   "tactic": "Discovery",           "name": "Cloud Service Discovery"},
    "ListSecrets":            {"id": "T1526",   "tactic": "Discovery",           "name": "Cloud Service Discovery"},
    "DescribeSecurityGroups": {"id": "T1526",   "tactic": "Discovery",           "name": "Cloud Service Discovery"},
    # Collection / Exfiltration
    "GetObject":              {"id": "T1530",   "tactic": "Collection",          "name": "Data from Cloud Storage"},
    "Scan":                   {"id": "T1530",   "tactic": "Collection",          "name": "Data from Cloud Storage"},
    "Query":                  {"id": "T1530",   "tactic": "Collection",          "name": "Data from Cloud Storage"},
    # Credential Access
    "GetSecretValue":         {"id": "T1552.001", "tactic": "Credential Access", "name": "Credentials in Files"},
    # Privilege Escalation
    "AssumeRole":             {"id": "T1078.004", "tactic": "Privilege Escalation", "name": "Valid Accounts: Cloud Accounts"},
    # Persistence
    "CreateUser":             {"id": "T1136.003", "tactic": "Persistence",       "name": "Create Account: Cloud Account"},
    "CreateAccessKey":        {"id": "T1098.001", "tactic": "Persistence",       "name": "Additional Cloud Credentials"},
    "AttachUserPolicy":       {"id": "T1098",     "tactic": "Persistence",       "name": "Account Manipulation"},
    # Initial Access
    "ConsoleLogin":           {"id": "T1078.004", "tactic": "Initial Access",    "name": "Valid Accounts: Cloud Accounts"},
    # Impact / Resource Abuse
    "RunInstances":           {"id": "T1496",   "tactic": "Impact",              "name": "Resource Hijacking"},
    "InvokeFunction":         {"id": "T1648",   "tactic": "Impact",              "name": "Serverless Execution"},
}

# ── Human-readable trigger descriptions ───────────────────────────────────────

TRIGGER_DESCRIPTIONS = {
    "ListBuckets":            "S3 Bucket Enumeration",
    "GetObject":              "S3 Object Access (Data Exfiltration Attempt)",
    "PutObject":              "S3 Object Write",
    "DeleteObject":           "S3 Object Deletion",
    "AssumeRole":             "IAM Role Assumption (Privilege Escalation)",
    "GetSecretValue":         "Secrets Manager Access (Credential Harvesting)",
    "ListSecrets":            "Secrets Manager Enumeration",
    "ConsoleLogin":           "AWS Console Login",
    "CreateUser":             "IAM User Creation (Persistence)",
    "CreateAccessKey":        "Access Key Creation (Persistence)",
    "AttachUserPolicy":       "Policy Attachment (Privilege Escalation)",
    "InvokeFunction":         "Lambda Invocation (Compute Abuse)",
    "RunInstances":           "EC2 Launch (Resource Hijacking / Cryptomining)",
    "Scan":                   "DynamoDB Table Scan (Data Exfiltration)",
    "Query":                  "DynamoDB Query",
    "DescribeInstances":      "EC2 Enumeration (Reconnaissance)",
    "DescribeSecurityGroups": "Security Group Enumeration (Reconnaissance)",
}


# ── Signal analysis ────────────────────────────────────────────────────────────

def is_internal_ip(ip: str) -> bool:
    """Returns True if the source IP is inside a private network range."""
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in network for network in PRIVATE_RANGES)
    except ValueError:
        return False


def determine_severity(event_name: str, source_ip: str, user_agent: str,
                       identity_type: str, mfa_used: bool) -> str:
    """
    Determines incident severity based on the combination of signals.

    Critical  — attacker already inside the network, or creating persistence
    High      — external credential use or data exfiltration
    Medium    — reconnaissance / enumeration
    """
    # Attacker is inside the network — highest urgency
    if is_internal_ip(source_ip):
        return "Critical"

    # Persistence or privilege escalation — attacker trying to stay
    if event_name in ("CreateUser", "CreateAccessKey", "AttachUserPolicy", "AssumeRole"):
        return "Critical"

    # Console login without MFA — credential theft or stuffing
    if event_name == "ConsoleLogin" and not mfa_used:
        return "Critical"

    # Active exfiltration — they found something and are taking it
    if event_name in ("GetObject", "GetSecretValue", "Scan", "Query"):
        return "High"

    # Compute abuse — cryptomining etc.
    if event_name in ("RunInstances", "InvokeFunction"):
        return "High"

    # Reconnaissance / enumeration
    return "Medium"


def extract_identity(user_identity: dict) -> dict:
    """
    Pulls the important identity fields out of the CloudTrail userIdentity block.
    Handles IAM users, assumed roles (EC2, Lambda), and console logins.
    """
    identity_type = user_identity.get("type", "Unknown")
    account_id    = user_identity.get("accountId", "Unknown")

    if identity_type == "IAMUser":
        username   = user_identity.get("userName", "Unknown")
        access_key = user_identity.get("accessKeyId", "")
        principal  = f"arn:aws:iam::{account_id}:user/{username}"
        return {
            "type":       "IAMUser",
            "username":   username,
            "access_key": access_key,
            "principal":  principal,
            "arn":        principal,
        }

    elif identity_type == "AssumedRole":
        arn          = user_identity.get("arn", "Unknown")
        session_name = user_identity.get("sessionContext", {}) \
                                    .get("sessionIssuer", {}) \
                                    .get("userName", "Unknown")
        return {
            "type":       "AssumedRole",
            "username":   session_name,
            "access_key": user_identity.get("accessKeyId", ""),
            "principal":  arn,
            "arn":        arn,
        }

    else:
        return {
            "type":       identity_type,
            "username":   user_identity.get("userName", "Unknown"),
            "access_key": "",
            "principal":  f"arn:aws:iam::{account_id}:unknown",
            "arn":        "",
        }


# ── Response actions ───────────────────────────────────────────────────────────

def disable_iam_key(username: str, access_key_id: str) -> dict:
    """Disables the IAM access key that was used in the attack."""
    if not access_key_id:
        return {"action": "Disable IAM Key", "status": "Skipped", "reason": "No access key ID found"}

    try:
        iam.update_access_key(
            UserName=username,
            AccessKeyId=access_key_id,
            Status="Inactive"
        )
        print(f"[RESPONSE] Disabled IAM key: {access_key_id}")
        return {
            "action":    "IAM Key Disabled",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status":    "Success",
            "detail":    f"Key {access_key_id} set to Inactive"
        }
    except Exception as e:
        print(f"[ERROR] Could not disable key {access_key_id}: {e}")
        return {
            "action":    "IAM Key Disabled",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status":    "Failed",
            "detail":    str(e)
        }


def isolate_ec2_instance(instance_id: str) -> dict:
    """
    Replaces the EC2 instance's security groups with a quarantine SG (no rules).
    Only runs if QUARANTINE_SG_ID is set and an instance ID can be identified.
    """
    if not QUARANTINE_SG or not instance_id:
        return {
            "action":    "EC2 Isolation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status":    "Skipped",
            "detail":    "No quarantine SG configured or no instance ID found"
        }

    try:
        ec2.modify_instance_attribute(
            InstanceId=instance_id,
            Groups=[QUARANTINE_SG]
        )
        print(f"[RESPONSE] Isolated EC2 instance: {instance_id}")
        return {
            "action":    "EC2 Instance Isolated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status":    "Success",
            "detail":    f"Instance {instance_id} moved to quarantine SG {QUARANTINE_SG}"
        }
    except Exception as e:
        print(f"[ERROR] Could not isolate instance {instance_id}: {e}")
        return {
            "action":    "EC2 Instance Isolated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status":    "Failed",
            "detail":    str(e)
        }


def post_to_dashboard(incident: dict) -> bool:
    """POSTs the incident to your CloudTripwire FastAPI dashboard."""
    try:
        body = json.dumps(incident).encode("utf-8")
        req  = urllib.request.Request(
            DASHBOARD_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            print(f"[DASHBOARD] Incident created: {result.get('id', 'unknown')}")
            return True
    except urllib.error.URLError as e:
        print(f"[ERROR] Could not reach dashboard at {DASHBOARD_URL}: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error posting to dashboard: {e}")
        return False


# ── Main Lambda handler ────────────────────────────────────────────────────────

def handler(event, context):
    """
    Entry point — AWS Lambda calls this function when EventBridge fires.

    'event' is the full EventBridge event containing the CloudTrail detail.
    """
    print(f"[TRIGGER] Received event: {json.dumps(event)}")

    # ── 1. Pull the CloudTrail detail out of the EventBridge wrapper ──────────

    detail = event.get("detail", {})
    if not detail:
        print("[ERROR] No detail found in event — skipping")
        return {"status": "error", "reason": "no detail"}

    event_name   = detail.get("eventName",    "Unknown")
    event_time   = detail.get("eventTime",    datetime.now(timezone.utc).isoformat())
    source_ip    = detail.get("sourceIPAddress", "0.0.0.0")
    user_agent   = detail.get("userAgent",    "Unknown")
    aws_region   = detail.get("awsRegion",    "us-east-1")
    error_code   = detail.get("errorCode",    None)
    resource_arn = detail.get("requestParameters", {}) or {}

    # MFA check (relevant for ConsoleLogin events)
    mfa_used = detail.get("additionalEventData", {}) \
                     .get("MFAUsed", "No") == "Yes"

    # ── 2. Extract identity ───────────────────────────────────────────────────

    identity = extract_identity(detail.get("userIdentity", {}))
    print(f"[IDENTITY] {identity['type']}: {identity['principal']}")
    print(f"[EVENT]    {event_name} from {source_ip} via {user_agent[:60]}")

    # ── 3. Determine severity ─────────────────────────────────────────────────

    severity = determine_severity(
        event_name    = event_name,
        source_ip     = source_ip,
        user_agent    = user_agent,
        identity_type = identity["type"],
        mfa_used      = mfa_used
    )
    print(f"[SEVERITY] {severity}")

    # ── 4. Determine trigger type (human readable) ────────────────────────────

    trigger_type = TRIGGER_DESCRIPTIONS.get(event_name, event_name)

    # ── 5. Look up MITRE ATT&CK technique ────────────────────────────────────

    mitre = MITRE_MAP.get(event_name, {
        "id":     "T1078",
        "tactic": "Initial Access",
        "name":   "Valid Accounts"
    })

    # ── 6. Build timeline ─────────────────────────────────────────────────────

    now = datetime.now(timezone.utc).isoformat()

    timeline = [
        {"event": "Honeytoken Triggered",         "timestamp": event_time},
        {"event": "Lambda Response Initiated",     "timestamp": now},
    ]

    # ── 7. Run response actions based on identity type ────────────────────────

    response_actions = []

    # Always try to disable the IAM key
    if identity["access_key"]:
        action = disable_iam_key(identity["username"], identity["access_key"])
        response_actions.append(action)
        if action["status"] == "Success":
            timeline.append({"event": "IAM Key Disabled", "timestamp": now})

    # If the attack came from inside (assumed role from EC2), isolate the instance
    if is_internal_ip(source_ip) and identity["type"] == "AssumedRole":
        # Try to extract EC2 instance ID from the session name
        session_context = detail.get("userIdentity", {}) \
                                .get("sessionContext", {}) \
                                .get("sessionIssuer", {})
        instance_id = None
        # Session name for EC2 looks like: i-0abc1234abcd5678
        session_name = detail.get("userIdentity", {}).get("arn", "")
        if "/i-" in session_name:
            instance_id = "i-" + session_name.split("/i-")[-1]

        action = isolate_ec2_instance(instance_id)
        response_actions.append(action)
        if action["status"] == "Success":
            timeline.append({"event": "EC2 Instance Isolated", "timestamp": now})

    # Mark evidence stage
    response_actions.append({
        "action":    "Security Team Notified",
        "timestamp": now,
        "status":    "Success"
    })
    timeline.append({"event": "Evidence Captured by CloudTrail", "timestamp": now})

    # ── 8. Build resource ARN ─────────────────────────────────────────────────

    # Try to build a meaningful resource ARN from the request parameters
    req_params = detail.get("requestParameters") or {}
    if "bucketName" in req_params:
        res_arn = f"arn:aws:s3:::{req_params['bucketName']}"
        if "key" in req_params:
            res_arn += f"/{req_params['key']}"
    else:
        res_arn = identity["arn"]

    # ── 9. Build threat indicators ────────────────────────────────────────────

    threat_indicators = {
        # Fields rendered by the dashboard's Threat Intelligence section
        "is_vpn":            False,                       # no VPN detection yet
        "is_tor":            False,                       # no Tor detection yet
        "is_known_attacker": True,                        # any honeytoken access is malicious
        "geo_location":      "Unknown",
        # Extra context shown alongside
        "is_internal_ip":    is_internal_ip(source_ip),
        "mfa_used":          mfa_used,
        "error_code":        error_code,
        "mitre_id":          mitre["id"],
        "mitre_tactic":      mitre["tactic"],
        "mitre_technique":   mitre["name"],
    }

    # ── 10. Build the incident payload ────────────────────────────────────────

    incident = {
        "cloud":            "AWS",
        "principal":        identity["principal"],
        "trigger_type":     trigger_type,
        "region":           aws_region,
        "severity":         severity,
        "ip_address":       source_ip,
        "user_agent":       user_agent,
        "resource_arn":     res_arn,
        "response_actions": response_actions,
        "timeline":         timeline,
        "threat_indicators": threat_indicators,
        "evidence": {
            "cloudtrail_event_id": detail.get("eventID", "unknown"),
            "cloudtrail_event_name": event_name,
            "event_source": detail.get("eventSource", "unknown"),
        }
    }

    # ── 11. POST to dashboard ─────────────────────────────────────────────────

    success = post_to_dashboard(incident)

    print(f"[DONE] Incident posted: {success} | Severity: {severity} | Event: {event_name}")

    return {
        "status":         "success" if success else "dashboard_unreachable",
        "event_name":     event_name,
        "severity":       severity,
        "source_ip":      source_ip,
        "key_disabled":   any(
            a.get("action") == "IAM Key Disabled" and a.get("status") == "Success"
            for a in response_actions
        )
    }
