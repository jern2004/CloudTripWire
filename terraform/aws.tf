# ──────────────────────────────────────────────────────────────────────────────
# CloudTripwire — AWS Infrastructure
# ──────────────────────────────────────────────────────────────────────────────
#
# Provisions the complete honeytoken detection and response stack:
#   - Decoy IAM user (the honeytoken credential)
#   - S3 canary bucket with tempting files
#   - CloudTrail trail (logs every API call)
#   - EventBridge rules (watches for honeytoken activity)
#   - Lambda function (disables key + POSTs incident to dashboard)
#   - All IAM roles and policies with least-privilege
#
# Usage:
#   cd terraform
#   terraform init
#   terraform plan
#   terraform apply
#
# To tear everything down:
#   terraform destroy
# ──────────────────────────────────────────────────────────────────────────────

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.3.0"
}

provider "aws" {
  region = var.aws_region
}

# ── 1. Decoy IAM honeytoken user ───────────────────────────────────────────────

resource "aws_iam_user" "honeytoken" {
  name = var.honeytoken_username

  tags = {
    Purpose   = "honeytoken"
    Project   = "cloudtripwire"
    ManagedBy = "terraform"
  }
}

# No policies attached — zero permissions by design
# Any API call using this user's keys is definitionally malicious

# ── 2. S3 canary bucket ────────────────────────────────────────────────────────

resource "aws_s3_bucket" "canary" {
  bucket = var.canary_bucket_name

  tags = {
    Purpose   = "honeytoken-canary"
    Project   = "cloudtripwire"
    ManagedBy = "terraform"
  }
}

resource "aws_s3_bucket_public_access_block" "canary" {
  bucket = aws_s3_bucket.canary.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "canary" {
  bucket = aws_s3_bucket.canary.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Canary files — tempting names that an attacker would go after
resource "aws_s3_object" "canary_creds" {
  bucket  = aws_s3_bucket.canary.id
  key     = "internal/aws-backup-creds.txt"
  content = "AWS_ACCESS_KEY_ID=FAKEKEYDONOTUSE\nAWS_SECRET_ACCESS_KEY=FAKESECRETDONOTUSE"
}

resource "aws_s3_object" "canary_salaries" {
  bucket  = aws_s3_bucket.canary.id
  key     = "finance/employee-salaries-2025.csv"
  content = "name,salary\nJohn Doe,95000\nJane Smith,102000"
}

resource "aws_s3_object" "canary_db" {
  bucket  = aws_s3_bucket.canary.id
  key     = "backups/db-dump-prod.sql"
  content = "-- Production database backup\n-- Date: 2025-10-01\n-- DO NOT SHARE"
}

# ── 3. CloudTrail ──────────────────────────────────────────────────────────────

# Bucket to store CloudTrail logs
resource "aws_s3_bucket" "trail_logs" {
  bucket = var.trail_log_bucket_name

  tags = {
    Purpose   = "cloudtrail-logs"
    Project   = "cloudtripwire"
    ManagedBy = "terraform"
  }
}

# CloudTrail requires a specific bucket policy to write logs
resource "aws_s3_bucket_policy" "trail_logs" {
  bucket = aws_s3_bucket.trail_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AWSCloudTrailAclCheck"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:GetBucketAcl"
        Resource  = aws_s3_bucket.trail_logs.arn
      },
      {
        Sid       = "AWSCloudTrailWrite"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.trail_logs.arn}/AWSLogs/${var.account_id}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      }
    ]
  })
}

resource "aws_cloudtrail" "main" {
  name                          = var.trail_name
  s3_bucket_name                = aws_s3_bucket.trail_logs.id
  is_multi_region_trail         = true
  enable_log_file_validation    = true
  include_global_service_events = true

  # Capture S3 data events — needed to detect GetObject on canary bucket
  event_selector {
    read_write_type           = "All"
    include_management_events = true

    data_resource {
      type   = "AWS::S3::Object"
      values = ["${aws_s3_bucket.canary.arn}/"]
    }
  }

  depends_on = [aws_s3_bucket_policy.trail_logs]

  tags = {
    Project   = "cloudtripwire"
    ManagedBy = "terraform"
  }
}

# ── 4. Lambda IAM role ─────────────────────────────────────────────────────────

resource "aws_iam_role" "lambda" {
  name = "cloudtripwire-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Project   = "cloudtripwire"
    ManagedBy = "terraform"
  }
}

# Basic Lambda execution (CloudWatch logs)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Least-privilege policy — only what the Lambda actually needs
resource "aws_iam_role_policy" "lambda_response" {
  name = "cloudtripwire-response-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DisableHoneytokenKey"
        Effect = "Allow"
        Action = [
          "iam:UpdateAccessKey",
          "iam:ListAccessKeys"
        ]
        # Scoped to the honeytoken user only — not all IAM users
        Resource = "arn:aws:iam::${var.account_id}:user/${var.honeytoken_username}"
      },
      {
        Sid    = "IsolateEC2"
        Effect = "Allow"
        Action = [
          "ec2:ModifyInstanceAttribute",
          "ec2:DescribeInstances",
          "ec2:DescribeSecurityGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

# ── 5. Lambda function ─────────────────────────────────────────────────────────

# Package the Lambda code
data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/../response/aws_lambda/isolate_and_log.py"
  output_path = "${path.module}/../response/aws_lambda/lambda_package.zip"
}

resource "aws_lambda_function" "responder" {
  function_name    = var.lambda_function_name
  role             = aws_iam_role.lambda.arn
  handler          = "isolate_and_log.handler"
  runtime          = "python3.11"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 30
  memory_size      = 128
  description      = "CloudTripwire - auto-isolate and log honeytoken incidents"

  environment {
    variables = {
      DASHBOARD_API_URL = var.dashboard_api_url
      HONEYTOKEN_USER   = var.honeytoken_username
    }
  }

  tags = {
    Project   = "cloudtripwire"
    ManagedBy = "terraform"
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_basic]
}

# ── 6. EventBridge rules ───────────────────────────────────────────────────────

# Rule 1: fires when the honeytoken IAM user's keys are used for any API call
resource "aws_cloudwatch_event_rule" "honeytoken_iam" {
  name        = "detect-honeytoken-iam"
  description = "CloudTripwire: fires when decoy IAM user credentials are used"

  event_pattern = jsonencode({
    source      = ["aws.iam", "aws.s3", "aws.sts", "aws.ec2", "aws.lambda", "aws.dynamodb", "aws.secretsmanager"]
    detail-type = ["AWS API Call via CloudTrail"]
    detail = {
      userIdentity = {
        userName = [var.honeytoken_username]
      }
    }
  })

  tags = {
    Project   = "cloudtripwire"
    ManagedBy = "terraform"
  }
}

resource "aws_cloudwatch_event_target" "honeytoken_iam" {
  rule = aws_cloudwatch_event_rule.honeytoken_iam.name
  arn  = aws_lambda_function.responder.arn
}

resource "aws_lambda_permission" "allow_eventbridge_iam" {
  statement_id  = "allow-eventbridge-iam-rule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.responder.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.honeytoken_iam.arn
}

# Rule 2: fires when anyone accesses the canary S3 bucket
resource "aws_cloudwatch_event_rule" "honeytoken_s3" {
  name        = "detect-honeytoken-s3"
  description = "CloudTripwire: fires when canary S3 bucket is accessed"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["AWS API Call via CloudTrail"]
    detail = {
      requestParameters = {
        bucketName = [var.canary_bucket_name]
      }
    }
  })

  tags = {
    Project   = "cloudtripwire"
    ManagedBy = "terraform"
  }
}

resource "aws_cloudwatch_event_target" "honeytoken_s3" {
  rule = aws_cloudwatch_event_rule.honeytoken_s3.name
  arn  = aws_lambda_function.responder.arn
}

resource "aws_lambda_permission" "allow_eventbridge_s3" {
  statement_id  = "allow-eventbridge-s3-rule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.responder.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.honeytoken_s3.arn
}

# ── Outputs ────────────────────────────────────────────────────────────────────

output "honeytoken_user_arn" {
  description = "ARN of the decoy IAM user"
  value       = aws_iam_user.honeytoken.arn
}

output "canary_bucket_name" {
  description = "Name of the S3 canary bucket"
  value       = aws_s3_bucket.canary.bucket
}

output "lambda_function_arn" {
  description = "ARN of the response Lambda function"
  value       = aws_lambda_function.responder.arn
}

output "cloudtrail_trail_arn" {
  description = "ARN of the CloudTrail trail"
  value       = aws_cloudtrail.main.arn
}
