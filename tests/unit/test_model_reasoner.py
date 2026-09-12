"""Phase 6: ModelReasoner is a drop-in Reasoner. The broker still gates."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from rootstock.runtime.loop import in_memory_runtime
from rootstock.runtime.model import (
    DEFAULT_BEDROCK_MODEL_ID,
    MODEL_MARKER,
    BedrockModelClient,
    FakeModelClient,
    ModelReasoner,
    SpendCap,
    SpendCapError,
    stub_like_create_bucket_reply,
)
from rootstock.runtime.reasoner import Observation, Reasoner, StubReasoner
from rootstock.shared.capability import Outcome
from rootstock.shared.vocabulary import SANDBOX_BUCKET_PREFIX

PROMPT_PATH = (
    Path(__file__).resolve().parents[2] / "infra" / "v0" / "grant-store" / "prompts" / "v0.json"
)
PROMPT = json.loads(PROMPT_PATH.read_text())


def observation(cycle: int = 1) -> Observation:
    return Observation(
        cycle_number=cycle,
        constitution_version="v1:abc123",
        capabilities_granted=("sandbox.s3.create_bucket",),
    )


def test_prompt_gives_the_model_a_real_noop() -> None:
    instructions = PROMPT["instructions"]
    assert '"action":"noop"' in instructions
    assert "noop is not a capability" in instructions


def test_model_reasoner_satisfies_the_reasoner_protocol() -> None:
    reasoner = ModelReasoner(FakeModelClient([json.dumps({"noop": True})]), PROMPT)
    assert isinstance(reasoner, Reasoner)
    assert isinstance(StubReasoner(), Reasoner)


def test_structured_noop_is_not_a_capability_invocation() -> None:
    client = FakeModelClient(
        [
            json.dumps(
                {
                    "action": "noop",
                    "reason": "enough buckets already exist",
                    "expected_outcome": "No Sandbox mutation occurs this cycle.",
                    "capability": "sandbox.s3.create_bucket",
                    "target": "rootstock-sbx-should-not-exist",
                }
            )
        ]
    )
    reasoner = ModelReasoner(client, PROMPT)
    _, harness = in_memory_runtime(reasoner=reasoner)
    result = harness.wake_and_drain()
    assert result.action == "noop"
    assert result.reason == "enough buckets already exist"
    assert harness.executor.calls == 0
    record = harness.decisions.get(result.cycle_number)
    assert record is not None
    assert record.actual_outcome == "no_action"
    assert record.capability is None
    assert record.expected_outcome == "No Sandbox mutation occurs this cycle."
    assert MODEL_MARKER in record.rationale


def test_canned_model_matches_stub_happy_path() -> None:
    client = FakeModelClient([stub_like_create_bucket_reply(1)])
    reasoner = ModelReasoner(client, PROMPT)
    _, harness = in_memory_runtime(reasoner=reasoner)
    result = harness.wake_and_drain()
    assert result.action == "enqueued"
    assert harness.executor.calls == 1
    bucket = f"{SANDBOX_BUCKET_PREFIX}cycle-1"
    assert bucket in harness.executor.buckets
    record = harness.decisions.get(result.cycle_number)
    assert record is not None
    assert record.rationale.startswith(MODEL_MARKER)
    assert reasoner.last_input_hash == record.observed_hash


def test_undeclared_model_proposal_is_rejected_like_the_stub() -> None:
    client = FakeModelClient(
        [
            json.dumps(
                {
                    "capability": "aws.call",
                    "target": "s3",
                    "parameters": {"operation": "CreateBucket"},
                    "justification": "bypass",
                    "expected_outcome": "should not execute",
                }
            )
        ]
    )
    _, harness = in_memory_runtime(reasoner=ModelReasoner(client, PROMPT))
    result = harness.wake_and_drain()
    assert result.action == "enqueued"
    assert harness.executor.calls == 0
    assert harness.claims.rows == {}


def test_out_of_scope_model_proposal_is_denied_like_the_stub() -> None:
    client = FakeModelClient(
        [
            json.dumps(
                {
                    "capability": "sandbox.s3.put_object",
                    "target": "someone-elses-bucket",
                    "parameters": {"suffix": "fixture", "key": "x"},
                    "justification": "out of scope",
                    "expected_outcome": "denied",
                }
            )
        ]
    )
    _, harness = in_memory_runtime(reasoner=ModelReasoner(client, PROMPT))
    result = harness.wake_and_drain()
    assert harness.executor.calls == 0
    closed = harness.decisions.get(result.cycle_number)
    assert closed is not None
    assert closed.actual_outcome == Outcome.DENIED


def test_spend_cap_severs_inference_and_enqueues_nothing() -> None:
    cap = SpendCap(max_usd=0.01)
    client = FakeModelClient(
        [stub_like_create_bucket_reply(1), stub_like_create_bucket_reply(2)],
        call_cost_usd=0.01,
        cap=cap,
    )
    reasoner = ModelReasoner(client, PROMPT)
    first = reasoner.propose(observation(1))
    assert first is not None
    second = reasoner.propose(observation(2))
    assert second is None
    assert reasoner.capped is True
    with pytest.raises(SpendCapError):
        client.complete(system="x", user="y")


def test_bedrock_client_rejects_empty_model_id() -> None:
    with pytest.raises(ValueError, match="model id is required"):
        BedrockModelClient(_FakeBedrockSession(), "")


def test_bedrock_client_invokes_only_the_configured_model() -> None:
    session = _FakeBedrockSession(reply=json.dumps({"noop": True}))
    client = BedrockModelClient(session, DEFAULT_BEDROCK_MODEL_ID)
    assert client.complete(system="sys", user="usr") == json.dumps({"noop": True})
    assert session.runtime.kwargs["modelId"] == DEFAULT_BEDROCK_MODEL_ID
    assert session.runtime.kwargs["system"] == [{"text": "sys"}]
    assert client.last_usage == {"input_tokens": 11, "output_tokens": 7}


def test_model_output_never_contains_a_provider_secret() -> None:
    client = FakeModelClient([stub_like_create_bucket_reply(3)])
    reasoner = ModelReasoner(client, PROMPT)
    proposal = reasoner.propose(observation(3))
    assert proposal is not None
    blob = json.dumps(asdict(proposal), default=str)
    assert "sk-ant" not in blob
    assert "sk-proj" not in blob
    assert MODEL_MARKER in proposal.rationale


class _FakeBedrockRuntime:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.kwargs: dict[str, object] = {}

    def converse(self, **kwargs: object) -> dict[str, object]:
        self.kwargs = kwargs
        return {
            "output": {"message": {"content": [{"text": self.reply}]}},
            "usage": {"inputTokens": 11, "outputTokens": 7},
        }


class _FakeBedrockSession:
    def __init__(self, reply: str = "{}") -> None:
        self.runtime = _FakeBedrockRuntime(reply)

    def client(self, name: str) -> _FakeBedrockRuntime:
        assert name == "bedrock-runtime"
        return self.runtime


def test_bedrock_client_charges_cap_before_converse() -> None:
    session = _FakeBedrockSession(reply="{}")
    cap = SpendCap(max_usd=0.01)
    client = BedrockModelClient(session, DEFAULT_BEDROCK_MODEL_ID, cap=cap, call_cost_usd=0.05)
    with pytest.raises(SpendCapError):
        client.complete(system="s", user="u")
    assert session.runtime.kwargs == {}


def test_model_reasoner_source_has_no_assume_role() -> None:
    path = Path(__file__).resolve().parents[2] / "src" / "rootstock" / "runtime" / "model.py"
    for line in path.read_text().splitlines():
        stripped = line.split("#", 1)[0]
        if "assume_role(" in stripped or "urlopen(" in stripped or "GetSecretValue" in stripped:
            raise AssertionError(line)
