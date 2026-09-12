data "aws_iam_policy_document" "runtime_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "broker_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "runtime" {
  provider           = aws.core
  name               = "rootstock-runtime-role"
  assume_role_policy = data.aws_iam_policy_document.runtime_trust.json
}

resource "aws_iam_role" "broker" {
  provider           = aws.core
  name               = "rootstock-broker-role"
  assume_role_policy = data.aws_iam_policy_document.broker_trust.json
}

data "aws_iam_policy_document" "runtime" {
  statement {
    sid = "OwnLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.runtime.arn}:*"]
  }

  statement {
    sid = "MemoryAppend"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:PutItem",
    ]
    resources = [aws_dynamodb_table.memory.arn]
  }

  statement {
    sid = "DecisionsOpen"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:PutItem",
    ]
    resources = [aws_dynamodb_table.decisions.arn]
  }

  statement {
    sid       = "VerifyClaimsAndApprovals"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.claims.arn, aws_dynamodb_table.approvals.arn]
  }

  statement {
    sid       = "ReadGrantStore"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.grant.arn}/*"]
  }

  statement {
    sid       = "Enqueue"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.requests.arn]
  }

  statement {
    sid     = "BedrockTerraProfile"
    actions = ["bedrock:InvokeModel"]
    resources = [
      "arn:aws:bedrock:${var.region}:${local.core_account_id}:inference-profile/${local.bedrock_model_id}",
      "arn:aws:bedrock:${var.region}:${local.core_account_id}:project/default",
    ]
  }

  statement {
    sid     = "BedrockTerraFoundation"
    actions = ["bedrock:InvokeModel"]
    resources = [
      "arn:aws:bedrock:us-east-1::foundation-model/${local.bedrock_foundation_model}",
      "arn:aws:bedrock:us-east-2::foundation-model/${local.bedrock_foundation_model}",
      "arn:aws:bedrock:us-west-2::foundation-model/${local.bedrock_foundation_model}",
    ]
    condition {
      test     = "StringEquals"
      variable = "bedrock:InferenceProfileArn"
      values   = ["arn:aws:bedrock:${var.region}:${local.core_account_id}:inference-profile/${local.bedrock_model_id}"]
    }
  }

  statement {
    sid       = "ExpiredLeaseMetric"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["Rootstock"]
    }
  }
}

data "aws_iam_policy_document" "broker" {
  statement {
    sid = "OwnLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.broker.arn}:*"]
  }

  statement {
    sid = "QueueConsume"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [aws_sqs_queue.requests.arn]
  }

  statement {
    sid = "Claims"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
    ]
    resources = [aws_dynamodb_table.claims.arn]
  }

  statement {
    sid = "Approvals"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
    ]
    resources = [aws_dynamodb_table.approvals.arn]
  }

  statement {
    sid       = "DecisionsClose"
    actions   = ["dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.decisions.arn]
  }

  statement {
    sid       = "ReadGrantStore"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.grant.arn}/*"]
  }

  statement {
    sid       = "AuditAppend"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.audit.arn}/*"]
  }

  statement {
    sid       = "ReadExternalId"
    actions   = ["ssm:GetParameter"]
    resources = [aws_ssm_parameter.sandbox_external_id.arn]
  }

  statement {
    sid       = "AssumeSandboxOperator"
    actions   = ["sts:AssumeRole"]
    resources = ["arn:aws:iam::${local.sandbox_account_id}:role/RootstockSandboxOperatorRole"]
  }
}

resource "aws_iam_role_policy" "runtime" {
  provider = aws.core
  name     = "rootstock-runtime"
  role     = aws_iam_role.runtime.id
  policy   = data.aws_iam_policy_document.runtime.json
}

resource "aws_iam_role_policy" "broker" {
  provider = aws.core
  name     = "rootstock-broker"
  role     = aws_iam_role.broker.id
  policy   = data.aws_iam_policy_document.broker.json
}
