output "core_account_id" {
  value = data.aws_caller_identity.core.account_id
}

output "sandbox_account_id" {
  value = data.aws_caller_identity.sandbox.account_id
}

output "organization_id" {
  value = data.aws_organizations_organization.this.id
}

output "runtime_role_arn" {
  value = aws_iam_role.runtime.arn
}

output "broker_role_arn" {
  value = aws_iam_role.broker.arn
}

output "sandbox_operator_role_arn" {
  value = aws_iam_role.sandbox_operator.arn
}

output "grant_bucket" {
  value = aws_s3_bucket.grant.id
}

output "audit_bucket" {
  value = aws_s3_bucket.audit.id
}

output "request_queue_url" {
  value = aws_sqs_queue.requests.id
}

output "constitution_sha256" {
  value = filesha256("${path.module}/grant-store/constitution.json")
}

output "runtime_function_name" {
  value = aws_lambda_function.runtime.function_name
}

output "broker_function_name" {
  value = aws_lambda_function.broker.function_name
}

output "wake_rule_state" {
  value = aws_cloudwatch_event_rule.wake.state
}

output "wake_schedule" {
  value = aws_cloudwatch_event_rule.wake.schedule_expression
}

output "request_dlq_url" {
  value = aws_sqs_queue.dlq.id
}

output "dlq_alarm_name" {
  value = aws_cloudwatch_metric_alarm.dlq.alarm_name
}

output "expired_lease_alarm_name" {
  value = aws_cloudwatch_metric_alarm.expired_lease.alarm_name
}

output "heartbeat_silence_alarm_name" {
  value = aws_cloudwatch_metric_alarm.heartbeat_silence.alarm_name
}

output "heartbeat_sink_function_name" {
  value = aws_lambda_function.heartbeat_sink.function_name
}

output "silence_watch_function_name" {
  value = aws_lambda_function.silence_watch.function_name
}

output "silence_watch_rule_name" {
  value = aws_cloudwatch_event_rule.silence_watch.name
}

output "heartbeat_table" {
  value = aws_dynamodb_table.heartbeat.name
}

output "heartbeat_silence_param" {
  value = aws_ssm_parameter.heartbeat_silence_seconds.name
}

output "heartbeat_url" {
  value     = "${aws_lambda_function_url.heartbeat_sink.function_url}?token=${random_password.heartbeat_token.result}"
  sensitive = true
}

output "runtime_reasoner" {
  value = var.reasoner
}

output "bedrock_model_id" {
  value = local.bedrock_model_id
}

output "prompt_key" {
  value = "prompts/v0.json"
}

output "core_budget_name" {
  value = aws_budgets_budget.core.name
}

output "sandbox_budget_name" {
  value = aws_budgets_budget.sandbox.name
}
