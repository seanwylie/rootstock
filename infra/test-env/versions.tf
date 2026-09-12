terraform {
  required_version = "~> 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  # Local state, deliberately. This environment is disposable and single-operator; remote
  # state would add a bootstrap dependency that Phase 0 exists to avoid. Revisit when the
  # broker runs unattended.
}

provider "aws" {
  region  = var.region
  profile = local.sandbox_profile

  # Read from infra/accounts.json rather than accepted as input. There is no variable a
  # caller could set wrongly, and Management has no entry anywhere in that file, so no
  # invocation of this configuration can target it (AR-1, AR-2).
  #
  # profile pins the credential source so Terraform never falls through to `default`.
  # allowed_account_ids is the spare: even a mis-pointed profile cannot apply here unless
  # it actually is Sandbox.
  allowed_account_ids = [local.sandbox_account_id]

  default_tags {
    tags = local.common_tags
  }
}
