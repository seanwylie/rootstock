data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../../src"
  output_path = "${path.module}/build/rootstock.zip"
  excludes    = ["__pycache__", "rootstock/__pycache__"]
}

resource "aws_lambda_function" "runtime" {
  provider         = aws.core
  function_name    = "rootstock-runtime"
  role             = aws_iam_role.runtime.arn
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  handler          = "rootstock.runtime.handler.handler"
  runtime          = "python3.12"
  timeout          = 120
  memory_size      = 256

  environment {
    variables = {
      GRANT_BUCKET        = aws_s3_bucket.grant.id
      AUDIT_BUCKET        = aws_s3_bucket.audit.id
      CLAIMS_TABLE        = aws_dynamodb_table.claims.name
      APPROVALS_TABLE     = aws_dynamodb_table.approvals.name
      DECISIONS_TABLE     = aws_dynamodb_table.decisions.name
      MEMORY_TABLE        = aws_dynamodb_table.memory.name
      QUEUE_URL           = aws_sqs_queue.requests.id
      CONSTITUTION_SHA256 = filesha256("${path.module}/grant-store/constitution.json")
      STUB_MODE           = "normal"
      REASONER            = var.reasoner
      BEDROCK_MODEL_ID    = local.bedrock_model_id
      PROMPT_KEY          = "prompts/v0.json"
      HEARTBEAT_URL       = "${aws_lambda_function_url.heartbeat_sink.function_url}?token=${random_password.heartbeat_token.result}"
    }
  }

  depends_on = [aws_cloudwatch_log_group.runtime]
}

resource "aws_lambda_function" "broker" {
  provider         = aws.core
  function_name    = "rootstock-broker"
  role             = aws_iam_role.broker.arn
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  handler          = "rootstock.broker.handler.handler"
  runtime          = "python3.12"
  timeout          = 90
  memory_size      = 256

  environment {
    variables = {
      GRANT_BUCKET              = aws_s3_bucket.grant.id
      AUDIT_BUCKET              = aws_s3_bucket.audit.id
      CLAIMS_TABLE              = aws_dynamodb_table.claims.name
      APPROVALS_TABLE           = aws_dynamodb_table.approvals.name
      DECISIONS_TABLE           = aws_dynamodb_table.decisions.name
      SANDBOX_OPERATOR_ROLE_ARN = aws_iam_role.sandbox_operator.arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.broker]
}

resource "aws_lambda_function" "heartbeat_sink" {
  provider         = aws.core
  function_name    = "rootstock-heartbeat-sink"
  role             = aws_iam_role.heartbeat_sink.arn
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  handler          = "rootstock.runtime.heartbeat.sink_handler"
  runtime          = "python3.12"
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      HEARTBEAT_TABLE = aws_dynamodb_table.heartbeat.name
      HEARTBEAT_TOKEN = random_password.heartbeat_token.result
    }
  }

  depends_on = [aws_cloudwatch_log_group.heartbeat_sink]
}

resource "aws_lambda_function_url" "heartbeat_sink" {
  provider           = aws.core
  function_name      = aws_lambda_function.heartbeat_sink.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "heartbeat_sink_url" {
  provider               = aws.core
  statement_id           = "AllowPublicHeartbeatPing"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.heartbeat_sink.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "heartbeat_sink_invoke" {
  provider      = aws.core
  statement_id  = "AllowPublicHeartbeatInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.heartbeat_sink.function_name
  principal     = "*"
}

resource "aws_lambda_function" "silence_watch" {
  provider         = aws.core
  function_name    = "rootstock-silence-watch"
  role             = aws_iam_role.silence_watch.arn
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  handler          = "rootstock.runtime.watch.handler"
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 128

  environment {
    variables = {
      HEARTBEAT_TABLE         = aws_dynamodb_table.heartbeat.name
      HEARTBEAT_SILENCE_PARAM = aws_ssm_parameter.heartbeat_silence_seconds.name
    }
  }

  depends_on = [aws_cloudwatch_log_group.silence_watch]
}

resource "aws_lambda_permission" "silence_watch" {
  provider      = aws.core
  statement_id  = "AllowEventBridgeSilenceWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.silence_watch.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.silence_watch.arn
}

resource "aws_cloudwatch_event_target" "silence_watch" {
  provider = aws.core
  rule     = aws_cloudwatch_event_rule.silence_watch.name
  arn      = aws_lambda_function.silence_watch.arn
}

resource "aws_lambda_event_source_mapping" "broker_queue" {
  provider                           = aws.core
  event_source_arn                   = aws_sqs_queue.requests.arn
  function_name                      = aws_lambda_function.broker.arn
  batch_size                         = 1
  function_response_types            = ["ReportBatchItemFailures"]
  maximum_batching_window_in_seconds = 0
}

resource "aws_lambda_permission" "wake" {
  provider      = aws.core
  statement_id  = "AllowEventBridgeWake"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.runtime.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.wake.arn
}

resource "aws_cloudwatch_event_target" "wake" {
  provider = aws.core
  rule     = aws_cloudwatch_event_rule.wake.name
  arn      = aws_lambda_function.runtime.arn
}
