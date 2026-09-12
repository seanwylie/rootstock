"""Phase 6 live: prompt in grant store, Bedrock model id pinned, runtime still on the stub."""

from __future__ import annotations

import json

import pytest
from botocore.exceptions import ClientError

from tests.live.helpers import connect_live, invoke_lambda

pytestmark = pytest.mark.live


def test_live_prompt_exists_runtime_stays_stub_no_model_secret() -> None:
    aws = connect_live()
    s3 = aws.core.client("s3")
    body = s3.get_object(
        Bucket=str(aws.outputs["grant_bucket"]), Key=str(aws.outputs["prompt_key"])
    )["Body"].read()
    prompt = json.loads(body)
    assert prompt["id"] == "rootstock.reasoner.v0"
    assert "instructions" in prompt

    lam = aws.core.client("lambda")
    cfg = lam.get_function_configuration(FunctionName=str(aws.outputs["runtime_function_name"]))
    env = cfg["Environment"]["Variables"]
    assert env.get("REASONER", "stub") == "stub"
    assert env.get("BEDROCK_MODEL_ID") == aws.outputs["bedrock_model_id"]
    assert env.get("BEDROCK_MODEL_ID") == "us.openai.gpt-5.6-terra"
    assert "MODEL_SECRET_ID" not in env

    secrets = aws.core.client("secretsmanager")
    try:
        described = secrets.describe_secret(SecretId="rootstock/model-api-key")
    except ClientError as exc:
        assert exc.response["Error"]["Code"] == "ResourceNotFoundException"
    else:
        assert described.get("DeletedDate") is not None, described

    noop = invoke_lambda(aws.core, str(aws.outputs["runtime_function_name"]), {"stub_mode": "noop"})
    assert noop["action"] == "noop", noop
