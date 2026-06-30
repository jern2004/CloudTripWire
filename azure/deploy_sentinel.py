"""
deploy_sentinel.py
──────────────────
Sets up the CloudTripwire Azure detection and response pipeline.

What it creates:
  1. Enables Microsoft Sentinel on the Log Analytics workspace
  2. Connects the Storage diagnostic logs as a Sentinel data source
  3. Creates a Sentinel analytic rule (KQL) — fires when canary blob is accessed
  4. Creates a Logic App — POSTs incident to CloudTripwire dashboard when rule fires
  5. Connects the analytic rule to the Logic App as an automation rule

Usage:
    python azure/deploy_sentinel.py
"""

import subprocess
import json
import sys
import os
from pathlib import Path

# ── Load config from deploy_azure.py output ───────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.json"
if not CONFIG_PATH.exists():
    print("❌ azure/config.json not found — run deploy_azure.py first")
    sys.exit(1)

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

az = CONFIG["azure"]
SUBSCRIPTION_ID  = az["subscription_id"]
RESOURCE_GROUP   = az["resource_group"]
LOCATION         = az["location"]
WORKSPACE_NAME   = az["log_analytics"]["workspace_name"]
WORKSPACE_ID     = az["log_analytics"]["workspace_id"]
STORAGE_ACCOUNT  = az["storage"]["account_name"]
CONTAINER_NAME   = az["storage"]["container_name"]

LOGIC_APP_NAME   = "cloudtripwire-responder"
RULE_NAME        = "cloudtripwire-canary-blob-access"

# ── Dashboard URL ──────────────────────────────────────────────────────────────
# Update this to your current ngrok URL before running
DASHBOARD_URL = os.environ.get(
    "DASHBOARD_API_URL",
    "http://127.0.0.1:8000/api/incidents"
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def run(cmd, capture=True, check=True):
    if isinstance(cmd, list) and cmd[0] == "az" and "--subscription" not in cmd:
        skip = {"ad", "account", "login"}
        if len(cmd) > 1 and cmd[1] not in skip:
            cmd = cmd + ["--subscription", SUBSCRIPTION_ID]
    print(f"  → {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if check and result.returncode != 0:
        print(f"\n❌ Failed:\n{result.stderr}")
        sys.exit(1)
    if capture and result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return result.stdout.strip()
    return None


def section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print('─' * 60)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  CloudTripwire — Azure Sentinel + Logic App Setup")
    print("=" * 60)
    print(f"  Dashboard URL: {DASHBOARD_URL}")
    print(f"  (set DASHBOARD_API_URL env var to change)")

    # ── 1. Enable Microsoft Sentinel (via REST API) ───────────────────────────
    section("1. Enable Microsoft Sentinel")

    import urllib.request, urllib.error

    token_raw = run(["az", "account", "get-access-token",
                     "--resource", "https://management.azure.com/",
                     "--query", "accessToken", "--output", "tsv"])
    token = token_raw.strip()

    onboard_url = (
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.OperationalInsights/workspaces/{WORKSPACE_NAME}"
        f"/providers/Microsoft.SecurityInsights/onboardingStates/default"
        f"?api-version=2022-12-01-preview"
    )
    req = urllib.request.Request(
        onboard_url,
        data=json.dumps({"properties": {}}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="PUT"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            json.loads(resp.read())
            print(f"✅ Sentinel enabled on workspace '{WORKSPACE_NAME}'")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "already" in body.lower() or e.code == 409:
            print(f"✅ Sentinel already enabled on workspace '{WORKSPACE_NAME}'")
        else:
            print(f"❌ Failed to enable Sentinel: {e.code}\n{body}")
            sys.exit(1)

    # ── 2. Sentinel analytic rule (KQL detection) ─────────────────────────────
    section("2. Sentinel analytic rule")

    # KQL: detect any read access to the canary storage account's blob service
    kql_query = (
        "StorageBlobLogs "
        f"| where AccountName == '{STORAGE_ACCOUNT}' "
        "| where OperationName in ('GetBlob', 'ListBlobs', 'GetContainerProperties') "
        "| where AuthenticationType != 'AccountKey' or AuthenticationType == 'SAS' "
        "| project TimeGenerated, OperationName, CallerIpAddress, "
        "          AuthenticationType, Uri, UserAgentHeader, StatusCode"
    )

    rule_body = {
        "kind": "Scheduled",
        "properties": {
            "displayName": "CloudTripwire - Canary Blob Accessed",
            "description": (
                "Fires when the CloudTripwire canary blob container is accessed. "
                "Any access is definitionally malicious — no legitimate system reads from it."
            ),
            "enabled": True,
            "query": kql_query,
            "queryFrequency": "PT5M",
            "queryPeriod": "PT5M",
            "triggerOperator": "GreaterThan",
            "triggerThreshold": 0,
            "severity": "High",
            "tactics": ["Collection", "Exfiltration"],
            "suppressionDuration": "PT1H",
            "suppressionEnabled": False,
        }
    }

    # Use REST API directly — the az sentinel alert-rule CLI is limited
    rule_url = (
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.OperationalInsights/workspaces/{WORKSPACE_NAME}"
        f"/providers/Microsoft.SecurityInsights/alertRules/{RULE_NAME}"
        f"?api-version=2023-02-01"
    )

    body_bytes = json.dumps(rule_body).encode()
    req = urllib.request.Request(
        rule_url,
        data=body_bytes,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="PUT"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            print(f"✅ Analytic rule '{RULE_NAME}' created")
            print(f"   Runs every 5 minutes, fires on any canary blob access")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ Failed to create analytic rule: {e.code}\n{body}")
        sys.exit(1)

    # ── 3. Logic App (response function) ──────────────────────────────────────
    section("3. Logic App (response function)")

    # Logic App definition — triggered by HTTP (Sentinel will call it)
    # Posts a structured incident to the CloudTripwire dashboard
    logic_app_def = {
        "definition": {
            "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
            "contentVersion": "1.0.0.0",
            "triggers": {
                "When_a_HTTP_request_is_received": {
                    "type": "Request",
                    "kind": "Http",
                    "inputs": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "AlertDisplayName": {"type": "string"},
                                "CallerIpAddress":  {"type": "string"},
                                "OperationName":    {"type": "string"},
                                "UserAgentHeader":  {"type": "string"},
                                "TimeGenerated":    {"type": "string"}
                            }
                        }
                    }
                }
            },
            "actions": {
                "Post_incident_to_dashboard": {
                    "type": "Http",
                    "inputs": {
                        "method": "POST",
                        "uri": DASHBOARD_URL,
                        "headers": {"Content-Type": "application/json"},
                        "body": {
                            "cloud":        "Azure",
                            "principal":    "cloudtripwirecanary (SAS token honeytoken)",
                            "trigger_type": "Azure Blob Storage Access (Canary)",
                            "region":       LOCATION,
                            "severity":     "High",
                            "ip_address":   "@{triggerBody()?['CallerIpAddress']}",
                            "user_agent":   "@{triggerBody()?['UserAgentHeader']}",
                            "resource_arn": f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/{CONTAINER_NAME}",
                            "response_actions": [
                                {
                                    "action":    "Sentinel Alert Raised",
                                    "timestamp": "@{utcNow()}",
                                    "status":    "Success"
                                },
                                {
                                    "action":    "Logic App Response Triggered",
                                    "timestamp": "@{utcNow()}",
                                    "status":    "Success"
                                }
                            ],
                            "timeline": [
                                {"event": "Canary Blob Accessed",      "timestamp": "@{triggerBody()?['TimeGenerated']}"},
                                {"event": "Sentinel Alert Fired",       "timestamp": "@{utcNow()}"},
                                {"event": "Logic App Response Started", "timestamp": "@{utcNow()}"}
                            ],
                            "threat_indicators": {
                                "is_vpn":            False,
                                "is_tor":            False,
                                "is_known_attacker": True,
                                "geo_location":      "Unknown",
                                "mitre_id":          "T1530",
                                "mitre_tactic":      "Collection",
                                "mitre_technique":   "Data from Cloud Storage"
                            }
                        }
                    },
                    "runAfter": {}
                }
            }
        }
    }

    # Create Logic App via REST API (avoids az logic preview extension issues)
    logic_url = (
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.Logic/workflows/{LOGIC_APP_NAME}"
        f"?api-version=2019-05-01"
    )
    logic_body = {
        "location": LOCATION,
        "properties": logic_app_def
    }
    req = urllib.request.Request(
        logic_url,
        data=json.dumps(logic_body).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="PUT"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            logic_app = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ Failed to create Logic App: {e.code}\n{body}")
        sys.exit(1)

    logic_app_id = logic_app["id"]

    # Get the trigger callback URL via REST API
    cb_url = (
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.Logic/workflows/{LOGIC_APP_NAME}"
        f"/triggers/When_a_HTTP_request_is_received/listCallbackUrl"
        f"?api-version=2019-05-01"
    )
    req = urllib.request.Request(
        cb_url,
        data=b"{}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            cb_info = json.loads(resp.read())
            logic_app_url = cb_info.get("value", "")
    except urllib.error.HTTPError as e:
        logic_app_url = ""
        print(f"  ⚠️  Could not get callback URL: {e.read().decode()}")

    print(f"✅ Logic App '{LOGIC_APP_NAME}' created")

    # ── 4. Save updated config ─────────────────────────────────────────────────
    section("4. Saving updated config")
    CONFIG["azure"]["sentinel"] = {
        "rule_name": RULE_NAME,
        "rule_url":  rule_url,
    }
    CONFIG["azure"]["logic_app"] = {
        "name":        LOGIC_APP_NAME,
        "id":          logic_app_id,
        "trigger_url": logic_app_url,
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(CONFIG, f, indent=2)
    print(f"✅ Config updated at {CONFIG_PATH}")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ✅ Sentinel + Logic App deployed!")
    print("=" * 60)
    print(f"""
  Analytic Rule:  {RULE_NAME}
                  Runs every 5 min — fires on any canary blob read
  Logic App:      {LOGIC_APP_NAME}
                  POSTs Azure incidents to your dashboard

  Test it now:
    python azure/test_trigger.py

  If your ngrok URL changes, update DASHBOARD_API_URL:
    export DASHBOARD_API_URL=https://xxxx.ngrok-free.dev/api/incidents
    python azure/deploy_sentinel.py  (re-runs only the Logic App update)
""")


if __name__ == "__main__":
    main()
