# Note what is absent: there is no account_id variable.
#
# The Sandbox account id is read from infra/accounts.json (see main.tf), so it cannot be
# passed in wrongly, overridden on the command line, or drift from what
# scripts/check_aws_context.py enforces. An operator's only remaining way to target the
# wrong account is to use the wrong credentials, which is what the provider's
# allowed_account_ids and the caller-identity precondition catch.

variable "region" {
  description = "Region for the disposable test environment."
  type        = string
  default     = "us-east-1"
}

variable "name_suffix" {
  description = <<-EOT
    Suffix for this environment's resources. Lets two operators, or a rerun after a failed
    destroy, coexist without collision.
  EOT
  type        = string
  default     = "phase0"

  validation {
    condition     = can(regex("^[a-z0-9-]{3,20}$", var.name_suffix))
    error_message = "name_suffix must be 3-20 chars of lowercase letters, digits, or hyphens."
  }
}
