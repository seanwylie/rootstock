# Member-account AWS Budgets with IAM-attach actions (AR-8, AWS spend only).
# Management org backstop (SCP rootstock-budget-halt) is operated by hand: this
# repository has no Management profile (AR-1).

variable "budget_alert_email" {
  type        = string
  default     = "ops@example.com"
  description = "Email for budget threshold and action notifications. Override in terraform.tfvars."
}

locals {
  budget_limit_usd = "10"
}

# --- Core ----------------------------------------------------------------------

data "aws_iam_policy_document" "budgets_actions_trust_core" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.core_account_id]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:budgets::${local.core_account_id}:budget/*"]
    }
  }
}

data "aws_iam_policy_document" "budget_sever" {
  statement {
    sid       = "SeverWhenBudgetExceeded"
    effect    = "Deny"
    actions   = ["*"]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "budgets_actions_core" {
  statement {
    sid = "AttachSeverPolicyToOrganismRoles"
    actions = [
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
    ]
    resources = [
      aws_iam_role.runtime.arn,
      aws_iam_role.broker.arn,
    ]
  }
  statement {
    sid = "ReadPolicyAndRoles"
    actions = [
      "iam:GetRole",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListAttachedRolePolicies",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "budget_sever" {
  provider    = aws.core
  name        = "rootstock-budget-sever"
  description = "Deny-all attached by AWS Budgets when Core monthly cap is exceeded."
  policy      = data.aws_iam_policy_document.budget_sever.json
}

resource "aws_iam_role" "budgets_actions" {
  provider           = aws.core
  name               = "rootstock-budgets-actions"
  description        = "Assumed by AWS Budgets to attach the Core spend-cap Deny policy."
  assume_role_policy = data.aws_iam_policy_document.budgets_actions_trust_core.json
}

resource "aws_iam_role_policy" "budgets_actions" {
  provider = aws.core
  name     = "attach-sever"
  role     = aws_iam_role.budgets_actions.id
  policy   = data.aws_iam_policy_document.budgets_actions_core.json
}

resource "aws_budgets_budget" "core" {
  provider     = aws.core
  name         = "rootstock-core-monthly"
  budget_type  = "COST"
  limit_amount = local.budget_limit_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }

  lifecycle {
    ignore_changes = [time_period_start, time_period_end]
  }
}

resource "aws_budgets_budget_action" "core" {
  provider           = aws.core
  budget_name        = aws_budgets_budget.core.name
  action_type        = "APPLY_IAM_POLICY"
  approval_model     = "AUTOMATIC"
  notification_type  = "ACTUAL"
  execution_role_arn = aws_iam_role.budgets_actions.arn

  action_threshold {
    action_threshold_type  = "PERCENTAGE"
    action_threshold_value = 100
  }

  definition {
    iam_action_definition {
      policy_arn = aws_iam_policy.budget_sever.arn
      roles = [
        aws_iam_role.runtime.name,
        aws_iam_role.broker.name,
      ]
    }
  }

  subscriber {
    address           = var.budget_alert_email
    subscription_type = "EMAIL"
  }

  depends_on = [aws_iam_role_policy.budgets_actions]
}

# --- Sandbox -------------------------------------------------------------------

data "aws_iam_policy_document" "budgets_actions_trust_sandbox" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.sandbox_account_id]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:budgets::${local.sandbox_account_id}:budget/*"]
    }
  }
}

data "aws_iam_policy_document" "budgets_actions_sandbox" {
  statement {
    sid = "AttachSeverPolicyToOperatorRole"
    actions = [
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
    ]
    resources = [aws_iam_role.sandbox_operator.arn]
  }
  statement {
    sid = "ReadPolicyAndRoles"
    actions = [
      "iam:GetRole",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListAttachedRolePolicies",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "sandbox_budget_sever" {
  provider    = aws.sandbox
  name        = "rootstock-budget-sever"
  description = "Deny-all attached by AWS Budgets when Sandbox monthly cap is exceeded."
  policy      = data.aws_iam_policy_document.budget_sever.json
}

resource "aws_iam_role" "sandbox_budgets_actions" {
  provider           = aws.sandbox
  name               = "rootstock-budgets-actions"
  description        = "Assumed by AWS Budgets to attach the Sandbox spend-cap Deny policy."
  assume_role_policy = data.aws_iam_policy_document.budgets_actions_trust_sandbox.json
}

resource "aws_iam_role_policy" "sandbox_budgets_actions" {
  provider = aws.sandbox
  name     = "attach-sever"
  role     = aws_iam_role.sandbox_budgets_actions.id
  policy   = data.aws_iam_policy_document.budgets_actions_sandbox.json
}

resource "aws_budgets_budget" "sandbox" {
  provider     = aws.sandbox
  name         = "rootstock-sandbox-monthly"
  budget_type  = "COST"
  limit_amount = local.budget_limit_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }

  lifecycle {
    ignore_changes = [time_period_start, time_period_end]
  }
}

resource "aws_budgets_budget_action" "sandbox" {
  provider           = aws.sandbox
  budget_name        = aws_budgets_budget.sandbox.name
  action_type        = "APPLY_IAM_POLICY"
  approval_model     = "AUTOMATIC"
  notification_type  = "ACTUAL"
  execution_role_arn = aws_iam_role.sandbox_budgets_actions.arn

  action_threshold {
    action_threshold_type  = "PERCENTAGE"
    action_threshold_value = 100
  }

  definition {
    iam_action_definition {
      policy_arn = aws_iam_policy.sandbox_budget_sever.arn
      roles      = [aws_iam_role.sandbox_operator.name]
    }
  }

  subscriber {
    address           = var.budget_alert_email
    subscription_type = "EMAIL"
  }

  depends_on = [aws_iam_role_policy.sandbox_budgets_actions]
}
