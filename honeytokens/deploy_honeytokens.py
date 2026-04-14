"""
deploy_honeytokens.py
─────────────────────
Plants all CloudTripwire honeytokens into your AWS account.

Run once after setting up your AWS CLI:
    cd cloudtripwire
    python honeytokens/deploy_honeytokens.py

What this script does:
  1. Creates a decoy IAM user with zero permissions (the "leaked credential")
  2. Creates an access key for it (this is what you plant / leak)
  3. Creates a private S3 bucket with tempting-looking files
  4. Enables CloudTrail to log every API call
  5. Creates EventBridge rules that watch for honeytoken activity
"""

import boto3
import json
import time
import sys
from pathlib import Path

# ── Load config ────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

AWS_CFG      = CONFIG["aws"]
REGION       = AWS_CFG["region"]
ACCOUNT_ID   = AWS_CFG["account_id"]

IAM_USERNAME = AWS_CFG["iam_honeytoken"]["username"]
BUCKET_NAME  = AWS_CFG["s3_canary"]["bucket_name"]
CANARY_FILES = AWS_CFG["s3_canary"]["files"]
TRAIL_NAME   = AWS_CFG["cloudtrail"]["trail_name"]
LOG_BUCKET   = AWS_CFG["cloudtrail"]["log_bucket"]
IAM_RULE     = AWS_CFG["eventbridge"]["iam_rule_name"]
S3_RULE      = AWS_CFG["eventbridge"]["s3_rule_name"]

# ── AWS clients ────────────────────────────────────────────────────────────────

iam         = boto3.client("iam",         region_name=REGION)
s3          = boto3.client("s3",          region_name=REGION)
cloudtrail  = boto3.client("cloudtrail",  region_name=REGION)
events      = boto3.client("events",      region_name=REGION)


# ── Helper ─────────────────────────────────────────────────────────────────────

def step(msg):
    print(f"\n{'─'*60}")
    print(f"  {msg}")
    print(f"{'─'*60}")

def ok(msg):   print(f"  ✅  {msg}")
def warn(msg): print(f"  ⚠️   {msg}")
def info(msg): print(f"  ℹ️   {msg}")


# ── Step 1: Decoy IAM user ─────────────────────────────────────────────────────

def create_honeytoken_user():
    step("Step 1 — Creating decoy IAM user (zero permissions)")

    # Create the user
    try:
        iam.create_user(
            UserName=IAM_USERNAME,
            Tags=[
                {"Key": "Purpose",     "Value": "honeytoken"},
                {"Key": "Project",     "Value": "cloudtripwire"},
                {"Key": "ManagedBy",   "Value": "deploy_honeytokens.py"},
            ]
        )
        ok(f"Created IAM user: {IAM_USERNAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        warn(f"User '{IAM_USERNAME}' already exists — skipping creation")

    # Create access keys — THIS is the "leaked credential" you plant
    try:
        response = iam.create_access_key(UserName=IAM_USERNAME)
        key = response["AccessKey"]

        ok("Created access key (this is your honeytoken credential):")
        print()
        print(f"    AWS_ACCESS_KEY_ID     = {key['AccessKeyId']}")
        print(f"    AWS_SECRET_ACCESS_KEY = {key['SecretAccessKey']}")
        print()
        print("    ⚠️  Save these — the secret is only shown once.")
        print("    Plant them in a fake .env file or commit to test.")

        # Save to a local file for reference
        key_file = Path(__file__).parent / "honeytoken_keys.txt"
        with open(key_file, "w") as f:
            f.write(f"# CloudTripwire Honeytoken Keys\n")
            f.write(f"# These are DECOY credentials — plant them somewhere fake\n")
            f.write(f"# Any use of these keys will trigger an incident\n\n")
            f.write(f"AWS_ACCESS_KEY_ID={key['AccessKeyId']}\n")
            f.write(f"AWS_SECRET_ACCESS_KEY={key['SecretAccessKey']}\n")
            f.write(f"AWS_REGION={REGION}\n")
        ok(f"Keys also saved to: honeytokens/honeytoken_keys.txt")

        return key["AccessKeyId"]

    except Exception as e:
        # User may already have 2 keys (AWS limit)
        warn(f"Could not create access key: {e}")
        warn("The user may already have 2 keys. Check IAM console.")
        return None


# ── Step 2: S3 canary bucket ───────────────────────────────────────────────────

def create_s3_canary():
    step("Step 2 — Creating S3 canary bucket with tempting files")

    # Create bucket (us-east-1 has no LocationConstraint)
    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=BUCKET_NAME)
        else:
            s3.create_bucket(
                Bucket=BUCKET_NAME,
                CreateBucketConfiguration={"LocationConstraint": REGION}
            )
        ok(f"Created bucket: {BUCKET_NAME}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        warn(f"Bucket '{BUCKET_NAME}' already exists — skipping creation")
    except Exception as e:
        warn(f"Could not create bucket: {e}")
        return

    # Block all public access
    s3.put_public_access_block(
        Bucket=BUCKET_NAME,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls":       True,
            "IgnorePublicAcls":      True,
            "BlockPublicPolicy":     True,
            "RestrictPublicBuckets": True,
        }
    )
    ok("Blocked all public access")

    # Upload canary files with tempting names
    for file in CANARY_FILES:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=file["key"],
            Body=file["content"].encode(),
            ServerSideEncryption="AES256",
        )
        ok(f"Uploaded: s3://{BUCKET_NAME}/{file['key']}")
        info(f"  → {file['description']}")


# ── Step 3: CloudTrail ─────────────────────────────────────────────────────────

def setup_cloudtrail():
    step("Step 3 — Enabling CloudTrail")

    # Create log bucket with correct policy
    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=LOG_BUCKET)
        else:
            s3.create_bucket(
                Bucket=LOG_BUCKET,
                CreateBucketConfiguration={"LocationConstraint": REGION}
            )
        ok(f"Created log bucket: {LOG_BUCKET}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        warn(f"Log bucket already exists — skipping")
    except Exception as e:
        warn(f"Could not create log bucket: {e}")
        return

    # CloudTrail requires a specific bucket policy to write logs
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AWSCloudTrailAclCheck",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:GetBucketAcl",
                "Resource": f"arn:aws:s3:::{LOG_BUCKET}"
            },
            {
                "Sid": "AWSCloudTrailWrite",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:PutObject",
                "Resource": f"arn:aws:s3:::{LOG_BUCKET}/AWSLogs/{ACCOUNT_ID}/*",
                "Condition": {
                    "StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}
                }
            }
        ]
    }
    s3.put_bucket_policy(
        Bucket=LOG_BUCKET,
        Policy=json.dumps(bucket_policy)
    )
    ok("Applied CloudTrail bucket policy")

    # Create the trail
    try:
        cloudtrail.create_trail(
            Name=TRAIL_NAME,
            S3BucketName=LOG_BUCKET,
            IsMultiRegionTrail=True,
            EnableLogFileValidation=True,
        )
        ok(f"Created trail: {TRAIL_NAME}")
    except cloudtrail.exceptions.TrailAlreadyExistsException:
        warn(f"Trail '{TRAIL_NAME}' already exists — skipping creation")

    # Start logging
    cloudtrail.start_logging(Name=TRAIL_NAME)
    ok("Started logging")

    # Enable S3 data events — off by default, needed to catch GetObject calls
    cloudtrail.put_event_selectors(
        TrailName=TRAIL_NAME,
        EventSelectors=[
            {
                "ReadWriteType": "All",
                "IncludeManagementEvents": True,
                "DataResources": [
                    {
                        # Log all S3 object access on the canary bucket
                        "Type": "AWS::S3::Object",
                        "Values": [f"arn:aws:s3:::{BUCKET_NAME}/"]
                    }
                ]
            }
        ]
    )
    ok("Enabled S3 data events for canary bucket")


# ── Step 4: EventBridge detection rules ───────────────────────────────────────

def create_eventbridge_rules():
    step("Step 4 — Creating EventBridge detection rules")

    # Rule 1: fires when ANYONE uses the honeytoken IAM user's keys
    iam_pattern = json.dumps({
        "source": ["aws.iam", "aws.s3", "aws.sts",
                   "aws.ec2", "aws.lambda", "aws.dynamodb",
                   "aws.secretsmanager"],
        "detail-type": ["AWS API Call via CloudTrail"],
        "detail": {
            "userIdentity": {
                "userName": [IAM_USERNAME]
            }
        }
    })

    try:
        iam_rule = events.put_rule(
            Name=IAM_RULE,
            EventPattern=iam_pattern,
            State="ENABLED",
            Description="CloudTripwire: fires when decoy IAM user credentials are used"
        )
        ok(f"Created rule: {IAM_RULE}")
        info(f"  → Watches for any API call using '{IAM_USERNAME}' keys")
    except Exception as e:
        warn(f"Could not create IAM rule: {e}")

    # Rule 2: fires when anyone accesses the canary S3 bucket
    s3_pattern = json.dumps({
        "source": ["aws.s3"],
        "detail-type": ["AWS API Call via CloudTrail"],
        "detail": {
            "requestParameters": {
                "bucketName": [BUCKET_NAME]
            }
        }
    })

    try:
        s3_rule = events.put_rule(
            Name=S3_RULE,
            EventPattern=s3_pattern,
            State="ENABLED",
            Description="CloudTripwire: fires when canary S3 bucket is accessed"
        )
        ok(f"Created rule: {S3_RULE}")
        info(f"  → Watches for any access to s3://{BUCKET_NAME}")
    except Exception as e:
        warn(f"Could not create S3 rule: {e}")


# ── Summary ────────────────────────────────────────────────────────────────────

def print_summary():
    print(f"\n{'═'*60}")
    print("  DEPLOYMENT COMPLETE")
    print(f"{'═'*60}")
    print()
    print("  Honeytokens planted:")
    print(f"  • IAM decoy user:   {IAM_USERNAME}")
    print(f"  • S3 canary bucket: s3://{BUCKET_NAME}")
    print(f"    ├── internal/aws-backup-creds.txt")
    print(f"    ├── finance/employee-salaries-2025.csv")
    print(f"    └── backups/db-dump-prod.sql")
    print()
    print("  Detection active:")
    print(f"  • CloudTrail trail: {TRAIL_NAME}")
    print(f"  • EventBridge rule: {IAM_RULE}")
    print(f"  • EventBridge rule: {S3_RULE}")
    print()
    print("  Next steps:")
    print("  1. Start ngrok:      ngrok http 8000")
    print("  2. Update config:    honeytokens/config.json → dashboard.api_url")
    print("  3. Deploy Lambda:    response/aws_lambda/isolate_and_log.py")
    print("  4. Test the trigger: python honeytokens/test_trigger.py")
    print(f"{'═'*60}\n")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("  CloudTripwire — Honeytoken Deployment")
    print(f"  Account: {ACCOUNT_ID}  |  Region: {REGION}")
    print()

    create_honeytoken_user()
    time.sleep(1)

    create_s3_canary()
    time.sleep(1)

    setup_cloudtrail()
    time.sleep(1)

    create_eventbridge_rules()

    print_summary()
