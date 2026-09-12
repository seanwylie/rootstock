# Phase 0 test environment.
#
# Deliberately almost empty. Phase 0 proves the *harness* -- that apply and destroy run
# clean twice in a row and that teardown provably leaves nothing behind -- not the substrate.
# Tables, queues, and roles arrive in Phase 1.
#
# One tagged bucket is enough to exercise provider configuration, the account guardrail, the
# naming convention, the tagging convention, destroy, and the teardown verifier.

locals {
  # Same file scripts/check_aws_context.py reads, so the Terraform guard and the shell guard
  # cannot disagree about which account is which.
  accounts           = jsondecode(file("${path.module}/../accounts.json"))
  sandbox_account_id = local.accounts.profiles["rootstock-sandbox"].account_id
  sandbox_profile = one([
    for name, entry in local.accounts.profiles : name if entry.zone == "sandbox"
  ])

  # Matches SANDBOX_BUCKET_PREFIX in src/rootstock/shared/vocabulary.py. The teardown
  # verifier sweeps on this prefix, so the two must not drift.
  bucket_prefix = "rootstock-sbx-"

  common_tags = {
    "rootstock:managed-by"  = "terraform"
    "rootstock:environment" = "test"
    "rootstock:purpose"     = "phase-0-harness"
    "rootstock:owner"       = "rootstock"
  }
}

data "aws_caller_identity" "current" {}

# Redundant with the provider's allowed_account_ids, which is the point: the guardrail that
# matters most is the one with a spare. This one also produces a legible error rather than a
# provider-level refusal.
resource "terraform_data" "account_guard" {
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == local.sandbox_account_id
      error_message = "Refusing to apply: credentials resolve to account ${data.aws_caller_identity.current.account_id}, not Rootstock Sandbox (${local.sandbox_account_id}). Set AWS_PROFILE=rootstock-sandbox."
    }
  }
}

resource "aws_s3_bucket" "harness" {
  bucket        = "${local.bucket_prefix}${var.name_suffix}-harness"
  force_destroy = true # disposable by design; destroy must not need manual emptying
}

resource "aws_s3_bucket_public_access_block" "harness" {
  bucket = aws_s3_bucket.harness.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "harness" {
  bucket = aws_s3_bucket.harness.id

  versioning_configuration {
    status = "Disabled"
  }
}
