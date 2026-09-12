"""Read-only grant store. Authority lives here, not in code (AR-6)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from rootstock.shared import vocabulary


@dataclass(frozen=True, slots=True)
class ParameterField:
    type: str
    pattern: str | None = None
    required: bool = False


@dataclass(frozen=True, slots=True)
class CapabilityDeclaration:
    id: str
    zone: str
    parameter_schema: dict[str, ParameterField]
    autonomy_level: str
    requires_approval: bool
    reversible: bool
    retry_after_unknown: str
    never_execute_without_prefix: bool = False


@dataclass(frozen=True, slots=True)
class PolicyDocument:
    grants: dict[str, frozenset[str]]
    never_granted: tuple[str, ...]


class GrantStore(Protocol):
    def policy(self) -> PolicyDocument: ...
    def capability(self, capability_id: str) -> CapabilityDeclaration | None: ...
    def declared_ids(self) -> frozenset[str]: ...
    def session_policy_template(self, capability_id: str) -> dict[str, Any] | None: ...


def _parse_fields(raw: dict[str, Any]) -> dict[str, ParameterField]:
    fields: dict[str, ParameterField] = {}
    for name, spec in raw.items():
        if not isinstance(spec, dict):
            raise ValueError(f"parameter_schema.{name} must be an object")
        fields[name] = ParameterField(
            type=str(spec.get("type", "string")),
            pattern=str(spec["pattern"]) if "pattern" in spec else None,
            required=bool(spec.get("required", False)) or name == "suffix",
        )
    return fields


def parse_capability(raw: dict[str, Any]) -> CapabilityDeclaration:
    schema = raw.get("parameter_schema", {})
    if not isinstance(schema, dict):
        raise ValueError("parameter_schema must be an object")
    semantics = raw.get("execution_semantics", {})
    if not isinstance(semantics, dict):
        semantics = {}
    fields = _parse_fields(schema)
    return CapabilityDeclaration(
        id=str(raw["id"]),
        zone=str(raw.get("zone", "")),
        parameter_schema=fields,
        autonomy_level=str(raw.get("autonomy_level", "L0")),
        requires_approval=bool(raw.get("requires_approval", False)),
        reversible=bool(semantics.get("reversible", False)),
        retry_after_unknown=str(semantics.get("retry_after_unknown", "halt")),
    )


def parse_policy(raw: dict[str, Any]) -> PolicyDocument:
    actors = raw.get("actors", {})
    grants: dict[str, frozenset[str]] = {}
    if isinstance(actors, dict):
        for actor, body in actors.items():
            if isinstance(body, dict) and isinstance(body.get("granted"), list):
                grants[str(actor)] = frozenset(str(x) for x in body["granted"])
    never = raw.get("never_granted", [])
    never_t = tuple(str(x) for x in never) if isinstance(never, list) else ()
    return PolicyDocument(grants=grants, never_granted=never_t)


class FilesystemGrantStore:
    """Loads the authored grant-store directory. Used by tests and local fixtures."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._policy = parse_policy(json.loads((root / "policy.json").read_text()))
        self._caps: dict[str, CapabilityDeclaration] = {}
        for path in sorted((root / "capabilities").glob("*.json")):
            raw = json.loads(path.read_text())
            decl = parse_capability(raw)
            self._caps[decl.id] = decl
        self._session: dict[str, dict[str, Any]] = {}
        session_dir = root / "session-policies"
        if session_dir.is_dir():
            for path in session_dir.glob("*.json"):
                self._session[path.stem] = json.loads(path.read_text())

    def policy(self) -> PolicyDocument:
        return self._policy

    def capability(self, capability_id: str) -> CapabilityDeclaration | None:
        return self._caps.get(capability_id)

    def declared_ids(self) -> frozenset[str]:
        return frozenset(self._caps) | vocabulary.DECLARED_AT_V0

    def session_policy_template(self, capability_id: str) -> dict[str, Any] | None:
        return self._session.get(capability_id)


def default_grant_store() -> FilesystemGrantStore:
    root = Path(__file__).resolve().parents[3] / "infra" / "v0" / "grant-store"
    return FilesystemGrantStore(root)


def matches_never_granted(capability_id: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        if pattern.endswith(".*") and capability_id.startswith(pattern[:-1]):
            return True
        if capability_id == pattern:
            return True
    return False


def compile_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)
