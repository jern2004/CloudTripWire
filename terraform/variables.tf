variable "aws_region" {
  description = "AWS region to deploy all resources"
  type        = string
  default     = "us-east-1"
}

variable "account_id" {
  description = "Your AWS account ID"
  type        = string
  default     = "100382203640"
}

variable "dashboard_api_url" {
  description = "CloudTripwire FastAPI endpoint for Lambda to POST incidents to"
  type        = string
  # Set this to your ngrok URL when testing:
  # export TF_VAR_dashboard_api_url="https://abc123.ngrok-free.app/api/incidents"
  default     = "http://127.0.0.1:8000/api/incidents"
}

variable "honeytoken_username" {
  description = "IAM username for the decoy honeytoken user"
  type        = string
  default     = "honeytoken-user"
}

variable "canary_bucket_name" {
  description = "S3 bucket name for canary files"
  type        = string
  default     = "cloudtripwire-canary-100382203640"
}

variable "trail_log_bucket_name" {
  description = "S3 bucket name for CloudTrail logs"
  type        = string
  default     = "cloudtripwire-trail-logs-100382203640"
}

variable "trail_name" {
  description = "CloudTrail trail name"
  type        = string
  default     = "cloudtripwire-trail"
}

variable "lambda_function_name" {
  description = "Lambda function name for incident response"
  type        = string
  default     = "cloudtripwire-responder"
}
