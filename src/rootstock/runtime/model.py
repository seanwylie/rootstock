"""ModelReasoner: the Phase 6 adapter. Same Reasoner interface as StubReasoner.

Holds a client and a prompt. Cannot execute, cannot assume a role, and never places a
secret in the observation or the proposal (AR-12). Inference uses Amazon Bedrock over
IAM/SigV4. The model id is constructor configuration, like heartbeat.ping(): complete()
takes no model argument, and there is no provider API key.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from rootstock.runtime.memory import NOOP_EXPECTED
from rootstock.runtime.observe import observation_hash, observation_payload
from rootstock.runtime.reasoner import Observation, Proposal
from rootstock.shared.canonical import canonical_json
from rootstock.shared.capability import Cost, Provenance

logger = logging.getLogger("rootstock.runtime.model")

MODEL_MARKER = "[model-generated]"
DEFAULT_BEDROCK_MODEL_ID = "us.openai.gpt-5.6-terra"


class SpendCapError(RuntimeError):
    """Provider-side cap would be exceeded. Do not call the model; do not enqueue."""


class SpendCap:
    """Hard remaining budget. Charge before the call; exceeding severs inference."""

    def __init__(self, max_usd: float) -> None:
        if max_usd < 0:
            raise ValueError("max_usd must be >= 0")
        self.max_usd = max_usd
        self.spent_usd = 0.0

    def charge(self, usd: float) -> None:
        if usd < 0:
            raise ValueError("charge must be >= 0")
        if self.spent_usd + usd > self.max_usd + 1e-12:
            raise SpendCapError(
                f"spend cap {self.max_usd} exceeded (spent {self.spent_usd}, charge {usd})"
            )
        self.spent_usd += usd


class ModelClient(Protocol):
    def complete(self, *, system: str, user: str) -> str: ...


class FakeModelClient:
    """In-process provider for tests. Charges the cap."""

    def __init__(
        self,
        replies: list[str] | None = None,
        *,
        call_cost_usd: float = 0.0,
        cap: SpendCap | None = None,
    ) -> None:
        self.replies = list(replies or [])
        self.call_cost_usd = call_cost_usd
        self.cap = cap
        self.calls: list[tuple[str, str]] = []

    def complete(self, *, system: str, user: str) -> str:
        if self.cap is not None:
            self.cap.charge(self.call_cost_usd)
        self.calls.append((system, user))
        if not self.replies:
            return json.dumps({"noop": True})
        return self.replies.pop(0)


class BedrockModelClient:
    """Invoke one configured Bedrock model via IAM.

    The model id is not an argument of complete().
    """

    def __init__(
        self,
        session: Any,
        model_id: str,
        *,
        cap: SpendCap | None = None,
        call_cost_usd: float = 0.05,
    ) -> None:
        pinned = model_id.strip()
        if not pinned:
            raise ValueError("bedrock model id is required")
        self._runtime = session.client("bedrock-runtime")
        self._model_id = pinned
        self.cap = cap
        self.call_cost_usd = call_cost_usd
        self.last_usage: dict[str, int] | None = None

    def complete(self, *, system: str, user: str) -> str:
        if self.cap is not None:
            self.cap.charge(self.call_cost_usd)
        response = self._runtime.converse(
            modelId=self._model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
        )
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
        input_tokens = int(usage.get("inputTokens") or 0)
        output_tokens = int(usage.get("outputTokens") or 0)
        self.last_usage = {"input_tokens": input_tokens, "output_tokens": output_tokens}
        logger.info(
            "bedrock.usage model=%s input_tokens=%s output_tokens=%s",
            self._model_id,
            input_tokens,
            output_tokens,
        )
        return _text_from_converse(response)


class ModelReasoner:
    """Reasoner backed by a model client and a versioned prompt artifact."""

    def __init__(self, client: ModelClient, prompt: dict[str, Any]) -> None:
        instructions = prompt.get("instructions")
        if not isinstance(instructions, str) or not instructions.strip():
            raise ValueError("prompt.instructions is required")
        self._client = client
        self._prompt = prompt
        self._instructions = instructions
        self.last_input_hash: str | None = None
        self.last_raw: str | None = None
        self.last_usage: dict[str, int] | None = None
        self.capped = False
        self.calls: list[Observation] = []

    def propose(self, observation: Observation) -> Proposal | None:
        self.calls.append(observation)
        self.capped = False
        self.last_usage = None
        user = canonical_json(observation_payload(observation)).decode("utf-8")
        self.last_input_hash = observation_hash(observation)
        try:
            raw = self._client.complete(system=self._instructions, user=user)
        except SpendCapError:
            logger.critical("model spend cap exceeded; proposing nothing")
            self.capped = True
            self.last_raw = None
            return None
        self.last_raw = raw
        usage = getattr(self._client, "last_usage", None)
        self.last_usage = usage if isinstance(usage, dict) else None
        parsed = _parse_reply(raw)
        if _is_noop(parsed):
            return _noop_proposal(parsed, input_hash=self.last_input_hash, raw=raw)
        return _proposal_from_mapping(parsed, input_hash=self.last_input_hash, raw=raw)


def _text_from_converse(response: dict[str, Any]) -> str:
    output = response.get("output") or {}
    if not isinstance(output, dict):
        raise ValueError("bedrock converse output is not an object")
    message = output.get("message") or {}
    if not isinstance(message, dict):
        raise ValueError("bedrock converse message is not an object")
    content = message.get("content") or []
    if not isinstance(content, list):
        raise ValueError("bedrock converse content is not a list")
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        text = block.get("text")
        if isinstance(text, str) and text:
            parts.append(text)
    if not parts:
        raise ValueError("bedrock converse returned no text")
    return "\n".join(parts)


def _parse_reply(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        inner = "\n".join(lines[1:])
        if inner.rstrip().endswith("```"):
            inner = inner.rstrip()[: inner.rstrip().rfind("```")]
        text = inner.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("model reply is not JSON") from None
        data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("model reply is not a JSON object")
    return data


def _is_noop(data: dict[str, Any]) -> bool:
    if data.get("action") == "noop":
        return True
    return data.get("noop") is True


def _noop_proposal(data: dict[str, Any], *, input_hash: str, raw: str) -> Proposal:
    reason = str(data.get("reason") or data.get("justification") or "noop")
    expected = str(data.get("expected_outcome") or NOOP_EXPECTED)
    raw_rationale = str(data.get("rationale") or raw)[:4000]
    rationale = f"{MODEL_MARKER} input_hash={input_hash}\n{raw_rationale}"
    return Proposal(
        capability="",
        target="",
        parameters={},
        estimated_cost=Cost(usd=0.0, tokens=0, duration_ms=0),
        justification=reason,
        expected_outcome=expected,
        alternatives=tuple(str(item) for item in (data.get("alternatives") or ())),
        rationale=rationale,
        provenance=Provenance.TRUSTED,
    )


def _proposal_from_mapping(data: dict[str, Any], *, input_hash: str, raw: str) -> Proposal:
    cost_raw = data.get("estimated_cost") or {}
    if not isinstance(cost_raw, dict):
        cost_raw = {}
    parameters = data.get("parameters") or {}
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")
    alternatives_raw = data.get("alternatives") or ()
    alternatives = tuple(str(item) for item in alternatives_raw)
    rationale = (
        f"{MODEL_MARKER} input_hash={input_hash}\n{str(data.get('rationale') or raw)[:4000]}"
    )
    return Proposal(
        capability=str(data.get("capability") or ""),
        target=str(data.get("target") or ""),
        parameters=dict(parameters),
        estimated_cost=Cost(
            usd=float(cost_raw.get("usd", 0) or 0),
            tokens=int(cost_raw.get("tokens", 0) or 0),
            duration_ms=int(cost_raw.get("duration_ms", 0) or 0),
        ),
        justification=str(data.get("justification") or "model proposal"),
        expected_outcome=str(data.get("expected_outcome") or ""),
        alternatives=alternatives,
        rationale=rationale,
        provenance=Provenance.TRUSTED,
    )


def load_prompt(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("prompt must be a JSON object")
    return raw


def stub_like_create_bucket_reply(cycle_number: int) -> str:
    """Canned model output with the same shape as StubMode.NORMAL."""
    suffix = f"cycle-{cycle_number}"
    return json.dumps(
        {
            "capability": "sandbox.s3.create_bucket",
            "target": f"rootstock-sbx-{suffix}",
            "parameters": {"suffix": suffix, "purpose": "cycle-artifact"},
            "justification": "Create a bucket to hold this cycle's artifacts.",
            "expected_outcome": (
                f"bucket rootstock-sbx-{suffix} exists, is tagged, "
                "and appears in inventory next cycle"
            ),
            "alternatives": ["do nothing", "write the summary to memory instead"],
            "estimated_cost": {"usd": 0.0, "tokens": 0},
            "rationale": "canned model reply for tests",
        }
    )
