"""
deploy_lambda.py
────────────────
Creates and wires up the CloudTripwire Lambda response function in AWS.

Run after deploy_honeytokens.py:
    cd cloudtripwire
    python response/aws_lambda/deploy_lambda.py

What this script does:
  1. Creates an IAM role so Lambda can call IAM + write logs
  2. Zips isolate_and_log.py into a deployment package
  3. Creates (or updates) the Lambda function
  4. Sets environment variables (dashboard URL, honeytoken username)
  5. Adds Lambda as the target for both EventBridge rules
  6. Grants EventBridge permission to invoke the Lambda
"""

import boto3
import json
import zipfile
import time
import sys
import os
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent.parent.parent / "honeytokens" / "config.json"
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

AWS_CFG       = CONFIG["aws"]
REGION        = AWS_CFG["region"]
ACCOUNT_ID    = AWS_CFG["account_id"]
IAM_RULE      = AWS_CFG["eventbridge"]["iam_rule_name"]
S3_RULE       = AWS_CFG["eventbridge"]["s3_rule_name"]
FUNCTION_NAME = AWS_CFG["lambda"]["function_name"]
ROLE_NAME     = AWS_CFG["lambda"]["role_name"]
DASHBOARD_URL = CONFIG["dashboard"]["api_url"]
HONEYTOKEN_USER = AWS_CFG["iam_honeytoken"]["username"]

LAMBDA_FILE   = Path(__file__).parent / "isolate_and_log.py"
ZIP_FILE      = Path(__file__).parent / "lambda_package.zip"

# ── AWS clients ────────────────────────────────────────────────────────────────

iam    = boto3.client("iam",    region_name=REGION)
lam    = boto3.client("lambda", region_name=REGION)
events = boto3.client("events", region_name=REGION)

# ── Helpers ────────────────────────────────────────────────────────────────────

def step(msg):
    print(f"\n{'─'*60}")
    print(f"  {msg}")
    print(f"{'─'*60}")

def ok(msg):   print(f"  ✅  {msg}")
def warn(msg): print(f"  ⚠️   {msg}")
def info(msg): print(f"  ℹ️   {msg}")


# ── Step 1: IAM role for Lambda ────────────────────────────────────────────────

def create_lambda_role() -> str:
    """
    Creates an IAM role that allows Lambda to:
    - Write its own logs to CloudWatch
    - Disable IAM access keys (to contain the attacker)
    - Modify EC2 instance security groups (to isolate compromised instances)
    Returns the role ARN.
    """
    step("Step 1 — Creating IAM role for Lambda")

    # Trust policy: allows Lambda service to assume this role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    # Try to create the role
    try:
        response = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="CloudTripwire Lambda - incident response role",
            Tags=[
                {"Key": "Project", "Value": "cloudtripwire"},
            ]
        )
        role_arn = response["Role"]["Arn"]
        ok(f"Created role: {ROLE_NAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/{ROLE_NAME}"
        warn(f"Role '{ROLE_NAME}' already exists — using existing")

    # Attach basic Lambda execution policy (CloudWatch logs)
    try:
        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
        ok("Attached: AWSLambdaBasicExecutionRole (CloudWatch logging)")
    except Exception as e:
        warn(f"Could not attach basic execution policy: {e}")

    # Inline policy: specific permissions for our response actions
    response_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                # Disable IAM keys (contain the attacker)
                "Sid": "DisableIAMKeys",
                "Effect": "Allow",
                "Action": [
                    "iam:UpdateAccessKey",
                    "iam:ListAccessKeys"
                ],
                "Resource": f"arn:aws:iam::{ACCOUNT_ID}:user/{HONEYTOKEN_USER}"
            },
            {
                # Isolate compromised EC2 instances
                "Sid": "IsolateEC2",
                "Effect": "Allow",
                "Action": [
                    "ec2:ModifyInstanceAttribute",
                    "ec2:DescribeInstances",
                    "ec2:DescribeSecurityGroups"
                ],
                "Resource": "*"
            }
        ]
    }

    try:
        iam.put_role_policy(
            RoleName=ROLE_NAME,
            PolicyName="cloudtripwire-response-policy",
            PolicyDocument=json.dumps(response_policy)
        )
        ok("Attached: cloudtripwire-response-policy (IAM disable + EC2 isolate)")
    except Exception as e:
        warn(f"Could not attach response policy: {e}")

    # IAM roles take a few seconds to propagate
    info("Waiting 10 seconds for IAM role to propagate...")
    time.sleep(10)

    return role_arn


# ── Step 2: Zip the Lambda code ────────────────────────────────────────────────

def build_zip() -> bytes:
    """Zips isolate_and_log.py into a deployment package and returns the bytes."""
    step("Step 2 — Building Lambda deployment package")

    with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
        # Lambda expects the handler file at the root of the zip
        zf.write(LAMBDA_FILE, "isolate_and_log.py")

    with open(ZIP_FILE, "rb") as f:
        zip_bytes = f.read()

    ok(f"Built: {ZIP_FILE.name} ({len(zip_bytes) / 1024:.1f} KB)")
    return zip_bytes


# ── Step 3: Create or update Lambda function ───────────────────────────────────

def deploy_lambda(role_arn: str, zip_bytes: bytes) -> str:
    """Creates the Lambda function, or updates its code if it already exists."""
    step("Step 3 — Deploying Lambda function")

    env_vars = {
        "DASHBOARD_API_URL": DASHBOARD_URL,
        "HONEYTOKEN_USER":   HONEYTOKEN_USER,
    }

    try:
        response = lam.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime="python3.11",
            Role=role_arn,
            Handler="isolate_and_log.handler",   # filename.function_name
            Code={"ZipFile": zip_bytes},
            Description="CloudTripwire - auto-isolate and log honeytoken incidents",
            Timeout=30,        # seconds
            MemorySize=128,    # MB — more than enough
            Environment={"Variables": env_vars},
            Tags={"Project": "cloudtripwire"},
        )
        function_arn = response["FunctionArn"]
        ok(f"Created Lambda: {FUNCTION_NAME}")

    except lam.exceptions.ResourceConflictException:
        # Function already exists — update the code and config
        warn(f"Function '{FUNCTION_NAME}' already exists — updating")

        lam.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_bytes,
        )
        time.sleep(3)  # wait for code update to complete

        response = lam.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Handler="isolate_and_log.handler",
            Timeout=30,
            MemorySize=128,
            Environment={"Variables": env_vars},
        )
        function_arn = response["FunctionArn"]
        ok(f"Updated Lambda: {FUNCTION_NAME}")

    info(f"  Handler:  isolate_and_log.handler")
    info(f"  Runtime:  Python 3.11")
    info(f"  Timeout:  30s")
    info(f"  Env:      DASHBOARD_API_URL = {DASHBOARD_URL}")

    return function_arn


# ── Step 4: Wire EventBridge rules to Lambda ───────────────────────────────────

def wire_eventbridge(function_arn: str):
    """Adds the Lambda as the target for both EventBridge detection rules."""
    step("Step 4 — Wiring EventBridge rules to Lambda")

    for rule_name, target_id in [
        (IAM_RULE, "cloudtripwire-iam-target"),
        (S3_RULE,  "cloudtripwire-s3-target"),
    ]:
        # Add Lambda as the target
        try:
            events.put_targets(
                Rule=rule_name,
                Targets=[
                    {
                        "Id":  target_id,
                        "Arn": function_arn,
                    }
                ]
            )
            ok(f"Wired: {rule_name} → {FUNCTION_NAME}")
        except Exception as e:
            warn(f"Could not wire {rule_name}: {e}")

        # Grant EventBridge permission to invoke the Lambda
        try:
            lam.add_permission(
                FunctionName=FUNCTION_NAME,
                StatementId=f"allow-eventbridge-{rule_name}",
                Action="lambda:InvokeFunction",
                Principal="events.amazonaws.com",
                SourceArn=f"arn:aws:events:{REGION}:{ACCOUNT_ID}:rule/{rule_name}",
            )
            ok(f"Granted: EventBridge can invoke {FUNCTION_NAME}")
        except lam.exceptions.ResourceConflictException:
            warn(f"Permission already exists for {rule_name} — skipping")
        except Exception as e:
            warn(f"Could not grant permission for {rule_name}: {e}")


# ── Summary ────────────────────────────────────────────────────────────────────

def print_summary(function_arn: str):
    print(f"\n{'═'*60}")
    print("  LAMBDA DEPLOYED — FULL PIPELINE ACTIVE")
    print(f"{'═'*60}")
    print()
    print("  Detection pipeline:")
    print(f"  Honeytoken touch")
    print(f"    → CloudTrail logs it")
    print(f"    → EventBridge matches rule")
    print(f"    → Lambda fires: {FUNCTION_NAME}")
    print(f"    → IAM key disabled")
    print(f"    → Incident POSTed to dashboard")
    print()
    print("  Lambda ARN:")
    print(f"  {function_arn}")
    print()
    print("  Next steps:")
    print("  1. Start your FastAPI:   cd backend && uvicorn app.main:app --reload")
    print("  2. Install ngrok:        https://ngrok.com/download")
    print("  3. Start ngrok:          ngrok http 8000")
    print("  4. Copy the ngrok URL and run:")
    print("       python response/aws_lambda/update_dashboard_url.py <your-ngrok-url>")
    print("  5. Test the trigger:     python honeytokens/test_trigger.py")
    print(f"{'═'*60}\n")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("  CloudTripwire — Lambda Deployment")
    print(f"  Account: {ACCOUNT_ID}  |  Region: {REGION}")
    print()

    role_arn     = create_lambda_role()
    zip_bytes    = build_zip()
    function_arn = deploy_lambda(role_arn, zip_bytes)
    wire_eventbridge(function_arn)
    print_summary(function_arn)
