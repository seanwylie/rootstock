resource "aws_s3_object" "constitution" {
  provider = aws.core
  bucket   = aws_s3_bucket.grant.id
  key      = "constitution.json"
  source   = "${path.module}/grant-store/constitution.json"
  etag     = filemd5("${path.module}/grant-store/constitution.json")
}

resource "aws_s3_object" "constitution_digest" {
  provider = aws.core
  bucket   = aws_s3_bucket.grant.id
  key      = "constitution.sha256"
  content  = filesha256("${path.module}/grant-store/constitution.json")
}

resource "aws_s3_object" "policy" {
  provider = aws.core
  bucket   = aws_s3_bucket.grant.id
  key      = "policy.json"
  source   = "${path.module}/grant-store/policy.json"
  etag     = filemd5("${path.module}/grant-store/policy.json")
}

resource "aws_s3_object" "capabilities" {
  for_each = fileset("${path.module}/grant-store/capabilities", "*.json")

  provider = aws.core
  bucket   = aws_s3_bucket.grant.id
  key      = "capabilities/${each.value}"
  source   = "${path.module}/grant-store/capabilities/${each.value}"
  etag     = filemd5("${path.module}/grant-store/capabilities/${each.value}")
}

resource "aws_s3_object" "session_policies" {
  for_each = fileset("${path.module}/grant-store/session-policies", "*.json")

  provider = aws.core
  bucket   = aws_s3_bucket.grant.id
  key      = "session-policies/${each.value}"
  source   = "${path.module}/grant-store/session-policies/${each.value}"
  etag     = filemd5("${path.module}/grant-store/session-policies/${each.value}")
}

resource "aws_s3_object" "prompts" {
  for_each = fileset("${path.module}/grant-store/prompts", "*.json")

  provider = aws.core
  bucket   = aws_s3_bucket.grant.id
  key      = "prompts/${each.value}"
  source   = "${path.module}/grant-store/prompts/${each.value}"
  etag     = filemd5("${path.module}/grant-store/prompts/${each.value}")
}
