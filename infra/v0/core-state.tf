resource "aws_dynamodb_table" "memory" {
  provider     = aws.core
  name         = "rootstock-memory"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
}

resource "aws_dynamodb_table" "decisions" {
  provider     = aws.core
  name         = "rootstock-decisions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cycle_number"

  attribute {
    name = "cycle_number"
    type = "N"
  }
}

resource "aws_dynamodb_table" "claims" {
  provider     = aws.core
  name         = "rootstock-claims"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "canonical_id"

  attribute {
    name = "canonical_id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "approvals" {
  provider     = aws.core
  name         = "rootstock-approvals"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "canonical_id"

  attribute {
    name = "canonical_id"
    type = "S"
  }
}

resource "aws_s3_bucket" "grant" {
  provider      = aws.core
  bucket        = "rootstock-grant-${local.core_account_id}"
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "grant" {
  provider                = aws.core
  bucket                  = aws_s3_bucket.grant.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "grant" {
  provider = aws.core
  bucket   = aws_s3_bucket.grant.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket" "audit" {
  provider            = aws.core
  bucket              = "rootstock-audit-${local.core_account_id}"
  object_lock_enabled = true
  force_destroy       = false
}

resource "aws_s3_bucket_public_access_block" "audit" {
  provider                = aws.core
  bucket                  = aws_s3_bucket.audit.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "audit" {
  provider = aws.core
  bucket   = aws_s3_bucket.audit.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_object_lock_configuration" "audit" {
  provider = aws.core
  bucket   = aws_s3_bucket.audit.id

  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = 30
    }
  }

  depends_on = [aws_s3_bucket_versioning.audit]
}

resource "aws_sqs_queue" "dlq" {
  provider                  = aws.core
  name                      = "rootstock-capability-requests-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "requests" {
  provider                   = aws.core
  name                       = "rootstock-capability-requests"
  visibility_timeout_seconds = 180
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })
}

resource "random_password" "sandbox_external_id" {
  length  = 32
  special = false
}

resource "aws_ssm_parameter" "sandbox_external_id" {
  provider    = aws.core
  name        = "/rootstock/sandbox-assume-external-id"
  type        = "SecureString"
  value       = random_password.sandbox_external_id.result
  description = "sts:ExternalId for RootstockSandboxOperatorRole"
}

resource "aws_cloudwatch_log_group" "runtime" {
  provider          = aws.core
  name              = "/rootstock/runtime"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "broker" {
  provider          = aws.core
  name              = "/rootstock/broker"
  retention_in_days = 30
}

resource "aws_cloudwatch_event_rule" "wake" {
  provider            = aws.core
  name                = "rootstock-runtime-wake"
  description         = "v0 wake schedule. DISABLED after stub qualification; still REASONER=stub."
  schedule_expression = var.wake_schedule
  state               = var.wake_state
}
