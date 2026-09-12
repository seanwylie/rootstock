# Phase 4 liveness: heartbeat sink (not the runtime), silence watch, DLQ + lease alarms.
# The runtime may GET the sink URL. It cannot write the heartbeat table, disable the
# watch rule, or delete these alarms.

resource "aws_dynamodb_table" "heartbeat" {
  provider     = aws.core
  name         = "rootstock-heartbeat"
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

resource "random_password" "heartbeat_token" {
  length  = 32
  special = false
}

resource "aws_ssm_parameter" "heartbeat_silence_seconds" {
  provider    = aws.core
  name        = "/rootstock/heartbeat-silence-seconds"
  type        = "String"
  value       = var.heartbeat_silence_seconds
  description = "Silence window. 7d while wake is DISABLED; tighten when the schedule is live."
}

data "aws_iam_policy_document" "heartbeat_sink_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "heartbeat_sink" {
  statement {
    sid = "OwnLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.heartbeat_sink.arn}:*"]
  }

  statement {
    sid       = "RecordPing"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.heartbeat.arn]
  }
}

data "aws_iam_policy_document" "silence_watch" {
  statement {
    sid = "OwnLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.silence_watch.arn}:*"]
  }

  statement {
    sid       = "ReadLastPing"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.heartbeat.arn]
  }

  statement {
    sid       = "ReadWindow"
    actions   = ["ssm:GetParameter"]
    resources = [aws_ssm_parameter.heartbeat_silence_seconds.arn]
  }

  statement {
    sid       = "SilenceMetric"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["Rootstock"]
    }
  }
}

resource "aws_iam_role" "heartbeat_sink" {
  provider           = aws.core
  name               = "rootstock-heartbeat-sink-role"
  assume_role_policy = data.aws_iam_policy_document.heartbeat_sink_trust.json
}

resource "aws_iam_role" "silence_watch" {
  provider           = aws.core
  name               = "rootstock-silence-watch-role"
  assume_role_policy = data.aws_iam_policy_document.heartbeat_sink_trust.json
}

resource "aws_iam_role_policy" "heartbeat_sink" {
  provider = aws.core
  name     = "rootstock-heartbeat-sink"
  role     = aws_iam_role.heartbeat_sink.id
  policy   = data.aws_iam_policy_document.heartbeat_sink.json
}

resource "aws_iam_role_policy" "silence_watch" {
  provider = aws.core
  name     = "rootstock-silence-watch"
  role     = aws_iam_role.silence_watch.id
  policy   = data.aws_iam_policy_document.silence_watch.json
}

resource "aws_cloudwatch_log_group" "heartbeat_sink" {
  provider          = aws.core
  name              = "/rootstock/heartbeat-sink"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "silence_watch" {
  provider          = aws.core
  name              = "/rootstock/silence-watch"
  retention_in_days = 30
}

resource "aws_cloudwatch_event_rule" "silence_watch" {
  provider            = aws.core
  name                = "rootstock-silence-watch"
  description         = "Evaluate heartbeat silence. Enabled; independent of the wake rule."
  schedule_expression = "rate(1 minute)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_metric_alarm" "dlq" {
  provider            = aws.core
  alarm_name          = "rootstock-dlq-messages"
  alarm_description   = "A poison capability request reached the DLQ."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }
}

resource "aws_cloudwatch_metric_alarm" "expired_lease" {
  provider            = aws.core
  alarm_name          = "rootstock-expired-lease"
  alarm_description   = "Runtime halted because a broker lease expired."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ExpiredLease"
  namespace           = "Rootstock"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "heartbeat_silence" {
  provider            = aws.core
  alarm_name          = "rootstock-heartbeat-silence"
  alarm_description   = "Heartbeat sink has gone silent for the configured window."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "HeartbeatSilence"
  namespace           = "Rootstock"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
}
