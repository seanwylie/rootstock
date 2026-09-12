terraform {
  required_version = "~> 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

locals {
  accounts           = jsondecode(file("${path.module}/../accounts.json"))
  core_account_id    = local.accounts.profiles["rootstock-core"].account_id
  sandbox_account_id = local.accounts.profiles["rootstock-sandbox"].account_id
  core_profile       = "rootstock-core"
  sandbox_profile    = "rootstock-sandbox"

  name_prefix   = "rootstock"
  bucket_prefix = "rootstock-sbx-"

  # Geo CRIS id on bedrock-runtime. IAM pins this profile; the prompt cannot escalate.
  bedrock_model_id         = "us.openai.gpt-5.6-terra"
  bedrock_foundation_model = "openai.gpt-5.6-terra"

  common_tags = {
    "rootstock:managed-by"  = "terraform"
    "rootstock:environment" = "v0"
    "rootstock:owner"       = "rootstock"
  }
}

provider "aws" {
  alias   = "core"
  region  = var.region
  profile = local.core_profile

  allowed_account_ids = [local.core_account_id]

  default_tags {
    tags = merge(local.common_tags, {
      "rootstock:purpose" = "core-substrate"
    })
  }
}

provider "aws" {
  alias   = "sandbox"
  region  = var.region
  profile = local.sandbox_profile

  allowed_account_ids = [local.sandbox_account_id]

  default_tags {
    tags = merge(local.common_tags, {
      "rootstock:purpose" = "sandbox-operator"
    })
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "wake_state" {
  type        = string
  default     = "DISABLED"
  description = "EventBridge wake. Disabled after stub qualification until Terra cycles."
}

variable "wake_schedule" {
  type        = string
  default     = "rate(4 hours)"
  description = "Design cadence. Override to rate(1 minute) only while accumulating 100 cycles."
}

variable "reasoner" {
  type        = string
  default     = "stub"
  description = "Live runtime reasoner. Default stub. Never combine model with an enabled wake."

  validation {
    condition     = contains(["stub", "model"], var.reasoner)
    error_message = "reasoner must be stub or model."
  }
}

variable "heartbeat_silence_seconds" {
  type        = string
  default     = "604800"
  description = "Silence window. 7d while wake is DISABLED so the watch does not sit in ALARM."
}

data "aws_caller_identity" "core" {
  provider = aws.core
}

data "aws_caller_identity" "sandbox" {
  provider = aws.sandbox
}

data "aws_organizations_organization" "this" {
  provider = aws.core
}

resource "terraform_data" "account_guards" {
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.core.account_id == local.core_account_id
      error_message = "Core provider resolved to ${data.aws_caller_identity.core.account_id}, expected ${local.core_account_id}."
    }
    precondition {
      condition     = data.aws_caller_identity.sandbox.account_id == local.sandbox_account_id
      error_message = "Sandbox provider resolved to ${data.aws_caller_identity.sandbox.account_id}, expected ${local.sandbox_account_id}."
    }
    precondition {
      condition     = !(var.wake_state == "ENABLED" && var.reasoner == "model")
      error_message = "Unattended model inference is forbidden: wake ENABLED cannot be applied with REASONER=model. Keep wake DISABLED and invoke supervised cycles."
    }
  }
}
