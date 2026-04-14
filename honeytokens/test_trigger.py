"""
test_trigger.py
───────────────
Simulates an attacker using the honeytoken credentials.

This makes a real AWS API call using the decoy keys, which:
  → CloudTrail logs it
  → EventBridge fires
  → Lambda runs
  → IAM key disabled
  → Incident appears on your dashboard

Run AFTER deploy_lambda.py and after starting ngrok:
    python honeytokens/test_trigger.py

The call will return AccessDenied (the user has no permissions)
but CloudTrail still logs it — that's the point.
"""

import boto3
import json
from pathlib import Path

# Load the honeytoken keys
KEYS_FILE = Path(__file__).parent / "honeytoken_keys.txt"

if not KEYS_FILE.exists():
    print("❌  honeytoken_keys.txt not found.")
    print("    Run deploy_honeytokens.py first.")
    exit(1)

# Parse the keys file
keys = {}
with open(KEYS_FILE) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            keys[k.strip()] = v.strip()

access_key_id     = keys.get("AWS_ACCESS_KEY_ID")
secret_access_key = keys.get("AWS_SECRET_ACCESS_KEY")
region            = keys.get("AWS_REGION", "us-east-1")

if not access_key_id or not secret_access_key:
    print("❌  Could not read keys from honeytoken_keys.txt")
    exit(1)

print()
print("  CloudTripwire — Simulating Attacker")
print(f"  Using honeytoken key: {access_key_id}")
print()
print("  Making API call as the attacker...")
print("  (This will return AccessDenied — that is expected)")
print()

# Create a boto3 session using the decoy credentials
# This simulates an attacker who found the leaked .env file
attacker_session = boto3.Session(
    aws_access_key_id     = access_key_id,
    aws_secret_access_key = secret_access_key,
    region_name           = region
)

# Try several things an attacker would do
s3  = attacker_session.client("s3")
iam = attacker_session.client("iam")

actions = [
    ("List S3 buckets",    lambda: s3.list_buckets()),
    ("List IAM users",     lambda: iam.list_users()),
]

for label, action in actions:
    try:
        result = action()
        print(f"  ⚠️  {label}: Succeeded (unexpected!)")
    except Exception as e:
        error = str(e)
        if "AccessDenied" in error or "InvalidClientTokenId" in error:
            print(f"  ✅  {label}: AccessDenied — CloudTrail logged the attempt")
        else:
            print(f"  ❓  {label}: {error[:80]}")

print()
print("  ─────────────────────────────────────────────────────")
print("  CloudTrail has logged these API calls.")
print("  EventBridge will fire within ~30 seconds.")
print("  Your Lambda will then:")
print("    1. Disable this IAM key")
print("    2. POST an incident to your dashboard")
print()
print("  Watch your dashboard at: http://localhost:5173")
print("  Or check Lambda logs:    AWS Console → Lambda → Monitor → Logs")
print()
