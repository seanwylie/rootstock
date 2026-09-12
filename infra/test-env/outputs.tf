output "account_id" {
  description = "Account this environment was applied to. Always Sandbox, or the apply failed."
  value       = data.aws_caller_identity.current.account_id
}

output "caller_arn" {
  description = "Principal that applied. Expected to be an AWSReservedSSO_ assumed role."
  value       = data.aws_caller_identity.current.arn
}

output "region" {
  value = var.region
}

output "bucket_prefix" {
  description = "Prefix the teardown verifier sweeps on."
  value       = local.bucket_prefix
}

output "harness_bucket" {
  description = "The single Phase 0 resource."
  value       = aws_s3_bucket.harness.id
}

# Populated in Phase 1, once the broker ingress exists. Named now so the fixture library's
# guidance message stays accurate:
#   export ROOTSTOCK_REQUEST_QUEUE_URL=$(terraform -chdir=infra/test-env output -raw request_queue_url)
output "request_queue_url" {
  description = "Broker ingress. Empty until Phase 1."
  value       = ""
}
