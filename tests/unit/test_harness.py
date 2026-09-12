"""Phase 0's own exit criteria, as tests.

The harness is the deliverable of Phase 0, so it needs the same scrutiny as the system it
will later be used to break.
"""

from __future__ import annotations

import pytest

from rootstock.shared.capability import Outcome
from tests.destructive import runner
from tests.fixtures import requests, submit


class TestSubstrateFailsClearly:
    """Phase 0 exit criterion 2."""

    def test_missing_queue_raises_substrate_not_ready(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(submit.QUEUE_NAME_ENV, raising=False)
        with pytest.raises(submit.SubstrateNotReadyError):
            submit.submit(requests.create_bucket_request())

    def test_the_error_says_what_to_do_next(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A harness whose failure mode is a wall of traceback trains people to skim
        # failures, which is the opposite of what the destructive tests need.
        monkeypatch.delenv(submit.QUEUE_NAME_ENV, raising=False)
        with pytest.raises(submit.SubstrateNotReadyError) as caught:
            submit.resolve_queue_url()
        message = str(caught.value)
        assert submit.QUEUE_NAME_ENV in message
        assert "Phase 1" in message
        assert "terraform" in message

    def test_harness_errors_are_distinct_from_test_failures(self) -> None:
        assert issubclass(submit.SubstrateNotReadyError, submit.HarnessError)
        assert issubclass(submit.CredentialsUnavailableError, submit.HarnessError)
        assert not issubclass(submit.HarnessError, AssertionError)


class TestFixtureLibrary:
    def test_baseline_request_is_well_formed(self) -> None:
        request = requests.create_bucket_request(suffix="abc")
        assert request.parameters["suffix"] == "abc"
        assert request.target.startswith("rootstock-sbx-")

    def test_same_key_different_parameters_serialise_differently(self) -> None:
        # The canonical id tracks content as well as the key, so this pair must stay
        # distinguishable or a legitimate variation would be swallowed as a duplicate.
        base = requests.create_bucket_request(idempotency_key="1", suffix="a")
        varied = requests.with_parameters(base, suffix="b")
        assert base.idempotency_key == varied.idempotency_key
        assert base.as_json() != varied.as_json()

    def test_adversarial_fixtures_exist_for_each_ingress_path(self) -> None:
        assert requests.undeclared_capability_request().capability == "aws.call"
        assert requests.malformed_request().parameters["suffix"] == "INVALID_Suffix!!"
        assert requests.out_of_scope_request().target == "someone-elses-bucket"


class TestDestructiveRegistry:
    def test_all_eight_are_registered(self) -> None:
        assert [spec.id for spec in runner.REGISTRY] == [f"D{n}" for n in range(1, 9)]

    def test_each_names_the_requirement_it_proves(self) -> None:
        for spec in runner.REGISTRY:
            assert spec.requirement.startswith("AR-"), spec.id
            assert spec.must_observe, spec.id

    def test_d7_and_d8_both_cover_ar4_from_opposite_directions(self) -> None:
        # D7 catches auditing too late; D8 catches the overcorrection that reports FAILURE
        # for a side effect which already happened.
        assert runner.BY_ID["D7"].requirement == "AR-4"
        assert runner.BY_ID["D8"].requirement == "AR-4"
        assert "UNKNOWN" in runner.BY_ID["D8"].must_observe
        assert "never FAILURE" in runner.BY_ID["D8"].must_observe

    def test_all_eight_are_implemented(self) -> None:
        assert runner.unimplemented() == ()
        assert all(spec.implemented for spec in runner.REGISTRY)

    def test_summary_renders(self) -> None:
        assert "D1" in runner.summary()


class TestOutcomeSemantics:
    def test_unknown_is_not_terminal(self) -> None:
        # UNKNOWN must hold a request out of both the success and failure paths until
        # reconciliation resolves it (AR-4).
        assert Outcome.UNKNOWN not in runner.__dict__.get("TERMINAL", set())
        from rootstock.shared.capability import TERMINAL_OUTCOMES

        assert Outcome.UNKNOWN not in TERMINAL_OUTCOMES
        assert Outcome.SUCCESS in TERMINAL_OUTCOMES
