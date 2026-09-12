data "aws_iam_policy_document" "sandbox_operator_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.broker.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = [random_password.sandbox_external_id.result]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:PrincipalOrgID"
      values   = [data.aws_organizations_organization.this.id]
    }
  }
}

data "aws_iam_policy_document" "sandbox_operator" {
  statement {
    sid     = "CreateBuckets"
    actions = ["s3:CreateBucket"]
    resources = [
      "arn:aws:s3:::${local.bucket_prefix}*",
    ]
  }

  # CreateBucket does not surface aws:RequestTag. PutBucketTagging does not either
  # (IAM simulate allows RequestTag; the S3 API does not populate it). Tags are
  # applied by the executor and verified independently. AR-13 at the IAM layer for
  # S3 buckets is not currently enforceable.
  statement {
    sid     = "TagBucketsAtCreate"
    actions = ["s3:PutBucketTagging"]
    resources = [
      "arn:aws:s3:::${local.bucket_prefix}*",
    ]
  }

  statement {
    sid     = "PutAndListOwn"
    actions = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
    resources = [
      "arn:aws:s3:::${local.bucket_prefix}*",
      "arn:aws:s3:::${local.bucket_prefix}*/*",
    ]
  }

  statement {
    sid = "ReadLogs"
    actions = [
      "logs:FilterLogEvents",
      "logs:GetLogEvents",
      "logs:DescribeLogGroups",
    ]
    resources = ["arn:aws:logs:${var.region}:${local.sandbox_account_id}:log-group:*"]
  }
}

resource "aws_iam_role" "sandbox_operator" {
  provider           = aws.sandbox
  name               = "RootstockSandboxOperatorRole"
  assume_role_policy = data.aws_iam_policy_document.sandbox_operator_trust.json
}

resource "aws_iam_role_policy" "sandbox_operator" {
  provider = aws.sandbox
  name     = "rootstock-sandbox-operator"
  role     = aws_iam_role.sandbox_operator.id
  policy   = data.aws_iam_policy_document.sandbox_operator.json
}
