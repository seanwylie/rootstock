"""The stub is the experimental control for Phases 1-5, so its determinism is load-bearing."""

from __future__ import annotations

import pytest

from rootstock.runtime.reasoner import (
    Observation,
    Proposal,
    Reasoner,
    StubMode,
    StubReasoner,
)
from rootstock.shared import vocabulary
from rootstock.shared.capability import Provenance


def observation(cycle: int = 1) -> Observation:
    return Observation(
        cycle_number=cycle,
        constitution_version="v1:abc123",
        capabilities_granted=tuple(sorted(vocabulary.DECLARED_AT_V0)),
    )


def test_stub_satisfies_the_reasoner_protocol() -> None:
    # Phase 6 swaps this implementation for a model-backed one. If that swap requires
    # changing anything outside the adapter, the propose/execute boundary leaked.
    assert isinstance(StubReasoner(), Reasoner)


def test_same_script_and_observation_produce_identical_proposals() -> None:
    a = StubReasoner(StubMode.NORMAL).propose(observation(7))
    b = StubReasoner(StubMode.NORMAL).propose(observation(7))
    assert a == b


def test_noop_proposes_nothing() -> None:
    assert StubReasoner(StubMode.NOOP).propose(observation()) is None


def test_script_advances_in_order_then_cycles() -> None:
    stub = StubReasoner([StubMode.NORMAL, StubMode.NOOP])
    assert stub.propose(observation(1)) is not None
    assert stub.propose(observation(2)) is None
    assert stub.propose(observation(3)) is not None


def test_non_repeating_script_stops_proposing() -> None:
    stub = StubReasoner([StubMode.NORMAL], repeat=False)
    assert stub.propose(observation(1)) is not None
    assert stub.propose(observation(2)) is None


def test_empty_script_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one mode"):
        StubReasoner([])


def test_normal_proposal_is_in_vocabulary_and_carries_a_checkable_expectation() -> None:
    proposal = StubReasoner(StubMode.NORMAL).propose(observation(42))
    assert isinstance(proposal, Proposal)
    assert proposal.capability in vocabulary.DECLARED_AT_V0
    assert proposal.expected_outcome
    assert "cycle-42" in proposal.parameters["suffix"]


def test_normal_proposal_supplies_a_suffix_not_a_bucket_name() -> None:
    # AR-16: the caller supplies the variable part; the executor applies the prefix.
    proposal = StubReasoner(StubMode.NORMAL).propose(observation())
    assert proposal is not None
    assert "suffix" in proposal.parameters
    assert not any(
        str(v).startswith(vocabulary.SANDBOX_BUCKET_PREFIX) for v in proposal.parameters.values()
    )


def test_undeclared_mode_proposes_the_generic_proxy_shape() -> None:
    # Drives D5. This is exactly the shape AR-16 exists to make unroutable.
    proposal = StubReasoner(StubMode.UNDECLARED).propose(observation())
    assert proposal is not None
    assert proposal.capability not in vocabulary.DECLARED_AT_V0


def test_untrusted_provenance_mode_marks_the_request() -> None:
    proposal = StubReasoner(StubMode.UNTRUSTED_PROVENANCE).propose(observation())
    assert proposal is not None
    assert proposal.provenance is Provenance.DERIVED_FROM_UNTRUSTED


@pytest.mark.parametrize("mode", list(StubMode))
def test_every_mode_is_constructible(mode: StubMode) -> None:
    StubReasoner(mode).propose(observation())


def test_stub_records_what_it_was_shown() -> None:
    stub = StubReasoner(StubMode.NOOP)
    stub.propose(observation(1))
    stub.propose(observation(2))
    assert [o.cycle_number for o in stub.calls] == [1, 2]


def test_proposal_converts_to_a_request_without_acquiring_authority() -> None:
    proposal = StubReasoner(StubMode.NORMAL).propose(observation(9))
    assert proposal is not None
    request = proposal.to_request(actor="runtime", idempotency_key="9", decision_ref="dec_9")
    assert request.idempotency_key == "9"
    assert request.capability == vocabulary.SANDBOX_S3_CREATE_BUCKET
    # No request id: the broker derives the canonical id itself (AR-15).
    assert not hasattr(request, "request_id")
