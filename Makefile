.DEFAULT_GOAL := help
TF := terraform -chdir=infra/test-env
TF_V0 := terraform -chdir=infra/v0

# Named per target, never inherited from the shell. The machine has a `default` profile
# pointing at unrelated personal credentials, so an inherited AWS_PROFILE is exactly the
# accident these assignments prevent.
SANDBOX_PROFILE := rootstock-sandbox
CORE_PROFILE    := rootstock-core

# Static keys in the environment override --profile in Terraform. Strip them so a leftover
# `export AWS_ACCESS_KEY_ID=...` from the personal default profile cannot leak through.
CLEAR_AMBIENT := env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN -u AWS_DEFAULT_PROFILE

# Every AWS-touching target runs the context check first, and make stops on its non-zero exit.
GUARD_SANDBOX := $(CLEAR_AMBIENT) uv run python scripts/check_aws_context.py --profile $(SANDBOX_PROFILE) --expect sandbox
GUARD_CORE    := $(CLEAR_AMBIENT) uv run python scripts/check_aws_context.py --profile $(CORE_PROFILE) --expect core

TF_SANDBOX := $(CLEAR_AMBIENT) AWS_PROFILE=$(SANDBOX_PROFILE) $(TF)
TF_V0_ENV := $(CLEAR_AMBIENT) AWS_PROFILE=$(CORE_PROFILE) $(TF_V0)

.PHONY: help setup fmt lint typecheck test check destructive-list \
        aws-context aws-context-core \
        infra-init infra-fmt infra-validate infra-plan infra-apply infra-destroy \
        verify-teardown verify-presence infra-cycle \
        v0-init v0-plan v0-apply v0-assert-iam v0-broker-live v0-runtime-live \
        v0-liveness-live v0-destructive-live v0-model-live v0-qualify v0-qualify-7b clean

help: ## Show available targets
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies into a local venv
	uv sync --extra dev

fmt: ## Format Python
	uv run ruff format src tests scripts
	uv run ruff check --fix src tests scripts

lint: ## Lint Python
	uv run ruff check src tests scripts
	uv run ruff format --check src tests scripts

typecheck: ## Type-check
	uv run mypy

test: ## Unit tests (excludes destructive)
	uv run pytest

check: lint typecheck test infra-fmt infra-validate ## Everything runnable without AWS

destructive-list: ## Show D1-D8 and their implementation status
	uv run python -m tests.destructive.runner

# --- AWS context --------------------------------------------------------------------

aws-context: ## Verify credentials resolve to Rootstock Sandbox
	$(GUARD_SANDBOX)

aws-context-core: ## Verify credentials resolve to Rootstock Core
	$(GUARD_CORE)

# --- infrastructure -----------------------------------------------------------------
# Everything below targets Sandbox and makes real changes. The account id is read from
# infra/accounts.json by both the guard and Terraform, so they cannot disagree.

infra-init: ## terraform init
	$(TF_SANDBOX) init

infra-fmt: ## terraform fmt check (no AWS)
	terraform fmt -check -recursive infra

infra-validate: ## terraform validate (no AWS)
	$(TF) validate

infra-plan: ## terraform plan (reads AWS)
	$(GUARD_SANDBOX)
	$(TF_SANDBOX) plan

infra-apply: ## terraform apply (REAL AWS CHANGES)
	$(GUARD_SANDBOX)
	$(TF_SANDBOX) apply

infra-destroy: ## terraform destroy (REAL AWS CHANGES)
	$(GUARD_SANDBOX)
	$(TF_SANDBOX) destroy

verify-teardown: ## Ask the provider whether anything remains (exit 1 if so)
	$(GUARD_SANDBOX)
	$(CLEAR_AMBIENT) AWS_PROFILE=$(SANDBOX_PROFILE) uv run python scripts/verify_teardown.py --expect absent

verify-presence: ## Ask the provider whether the harness bucket exists (exit 1 if not)
	$(GUARD_SANDBOX)
	$(CLEAR_AMBIENT) AWS_PROFILE=$(SANDBOX_PROFILE) uv run python scripts/verify_teardown.py --expect present

infra-cycle: ## Phase 0 exit criteria 1 and 3: apply/destroy clean, twice, independently verified
	$(GUARD_SANDBOX)
	$(TF_SANDBOX) apply -auto-approve
	$(MAKE) verify-presence
	$(TF_SANDBOX) destroy -auto-approve
	$(MAKE) verify-teardown
	$(TF_SANDBOX) apply -auto-approve
	$(MAKE) verify-presence
	$(TF_SANDBOX) destroy -auto-approve
	$(MAKE) verify-teardown
	@echo "Two clean apply/destroy cycles; presence and absence verified against the provider."

# --- v0 substrate (Core + Sandbox) --------------------------------------------------

v0-init: ## terraform init for Phase 1 substrate
	$(TF_V0_ENV) init

v0-plan: ## terraform plan Phase 1 (reads Core and Sandbox)
	$(GUARD_CORE)
	$(GUARD_SANDBOX)
	$(TF_V0_ENV) plan

v0-apply: ## terraform apply Phase 1 (REAL AWS CHANGES in Core and Sandbox)
	$(GUARD_CORE)
	$(GUARD_SANDBOX)
	$(TF_V0_ENV) apply

v0-assert-iam: ## Simulate denied actions on runtime/broker roles
	$(GUARD_CORE)
	$(CLEAR_AMBIENT) AWS_PROFILE=$(CORE_PROFILE) uv run python scripts/assert_iam_negatives.py

v0-broker-live: ## Phase 2 live broker: create one tagged bucket, replay, IAM session
	$(GUARD_CORE)
	$(GUARD_SANDBOX)
	$(CLEAR_AMBIENT) uv run pytest -m live tests/live/test_phase2_broker.py -q

v0-runtime-live: ## Phase 3 live runtime: ten cycles through EventBridge-shaped invokes
	$(GUARD_CORE)
	$(GUARD_SANDBOX)
	$(CLEAR_AMBIENT) uv run pytest -m live tests/live/test_phase3_runtime.py -q

v0-liveness-live: ## Phase 4 live: DLQ alarm, D1 silence, runtime cannot mute the monitor
	$(GUARD_CORE)
	$(CLEAR_AMBIENT) uv run pytest -m live tests/live/test_phase4_liveness.py -q

v0-destructive-live: ## Phase 5 live: D1-D8, CloudTrail join, cost per cycle
	$(GUARD_CORE)
	$(GUARD_SANDBOX)
	$(CLEAR_AMBIENT) uv run pytest -m destructive tests/live/test_phase5_validation.py -q

v0-model-live: ## Phase 6 live: prompt artifact, Bedrock id; runtime remains stub
	$(GUARD_CORE)
	$(CLEAR_AMBIENT) uv run pytest -m live tests/live/test_phase6_model.py -q

v0-qualify: ## Phase 7a: wait for 100 EventBridge cycles (does not invoke the runtime)
	$(GUARD_CORE)
	$(GUARD_SANDBOX)
	$(CLEAR_AMBIENT) AWS_PROFILE=$(CORE_PROFILE) uv run python scripts/qualify_v0.py

v0-qualify-7b: ## Phase 7b: 12 supervised Terra invokes. Refuses if wake is ENABLED.
	$(GUARD_CORE)
	$(GUARD_SANDBOX)
	$(CLEAR_AMBIENT) AWS_PROFILE=$(CORE_PROFILE) uv run python scripts/qualify_7b.py

clean: ## Remove local caches
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
