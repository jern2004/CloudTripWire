"""
update_dashboard_url.py
───────────────────────
Updates the Lambda environment variable when your ngrok URL changes.

Usage:
    python response/aws_lambda/update_dashboard_url.py https://abc123.ngrok.io
"""

import boto3
import json
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "honeytokens" / "config.json"
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

REGION        = CONFIG["aws"]["region"]
FUNCTION_NAME = CONFIG["aws"]["lambda"]["function_name"]
HONEYTOKEN_USER = CONFIG["aws"]["iam_honeytoken"]["username"]

if len(sys.argv) < 2:
    print("Usage: python update_dashboard_url.py <ngrok-url>")
    print("Example: python update_dashboard_url.py https://abc123.ngrok.io")
    sys.exit(1)

ngrok_url   = sys.argv[1].rstrip("/")
api_url     = f"{ngrok_url}/api/incidents"

lam = boto3.client("lambda", region_name=REGION)

lam.update_function_configuration(
    FunctionName=FUNCTION_NAME,
    Environment={
        "Variables": {
            "DASHBOARD_API_URL": api_url,
            "HONEYTOKEN_USER":   HONEYTOKEN_USER,
        }
    }
)

print(f"✅  Updated Lambda env var:")
print(f"    DASHBOARD_API_URL = {api_url}")
