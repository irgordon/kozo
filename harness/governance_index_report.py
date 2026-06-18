from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.registry import CHECKS

REPORT_PATH = ROOT / "docs" / "generated" / "governance_index.md"
LATEST_VERIFY_REFERENCE = "artifacts/latest_verify.json"
CHANGELOG_REFERENCE = "CHANGELOG.md"
GENERATED_REPORT_REFERENCES = (
    "docs/generated/syscall_surface.md",
    "docs/generated/abi_surface.md",
    "docs/generated/governance_index.md",
)
NON_GOALS = (
    "no Linux compatibility claim",
    "no userspace execution claim",
    "no process model behavior claim",
    "no VFS behavior claim",
    "no scheduler behavior claim",
    "no ELF loading behavior claim",
    "no file descriptor behavior claim",
    "no production readiness claim",
    "generated reports are non-authoritative",
)
CONTRACT_ROLES = {
    "kozo_abi_manifest.json": "ABI manifest",
    "syscall_boundary_contract.v0.json": "syscall boundary contract",
    "syscall_table_contract.v0.json": "syscall table contract",
    "syscall_class_contract.v0.json": "syscall class contract",
    "syscall_catalog.v0.json": "syscall catalog",
}


@dataclass(frozen=True)
class ChangelogVersion:
    version: str
    date: str
    status: str


@dataclass(frozen=True)
class VerifySummary:
    status: str
    summary_code: str
    total_checks: int
    failed_check_count: int
    run_id: str
    generated_at: str


@dataclass(frozen=True)
class ContractSummary:
    path: str
    version: str
    role: str


@dataclass(frozen=True)
class SchemaSummary:
    path: str
    title: str


@dataclass(frozen=True)
class GovernanceIndexInputs:
    current_version: ChangelogVersion
    verification: VerifySummary
    validators: tuple[str, ...]
    contracts: tuple[ContractSummary, ...]
    schemas: tuple[SchemaSummary, ...]
    generated_reports: tuple[str, ...]
    proof_artifact_path: str
    non_goals: tuple[str, ...]


def load_report_inputs(root: Path = ROOT) -> GovernanceIndexInputs:
    return GovernanceIndexInputs(
        current_version=_latest_changelog_version(root / CHANGELOG_REFERENCE),
        verification=_latest_verify_summary(root / LATEST_VERIFY_REFERENCE),
        validators=tuple(CHECKS.keys()),
        contracts=_contract_summaries(root),
        schemas=_schema_summaries(root),
        generated_reports=GENERATED_REPORT_REFERENCES,
        proof_artifact_path=LATEST_VERIFY_REFERENCE,
        non_goals=NON_GOALS,
    )


def render_governance_index_report(inputs: GovernanceIndexInputs) -> str:
    return "\n".join(_report_lines(inputs))


def expected_report_text(root: Path = ROOT) -> str:
    return render_governance_index_report(load_report_inputs(root))


def write_report(root: Path = ROOT, output_path: Path = REPORT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(expected_report_text(root))


def _report_lines(inputs: GovernanceIndexInputs) -> list[str]:
    return [
        "# KOZO governance index",
        "",
        "Generated from repository governance surfaces.",
        "",
        "This document is generated. Do not edit manually.",
        "",
        *_scope_lines(),
        *_current_version_lines(inputs.current_version),
        *_verification_status_lines(inputs.verification),
        *_registered_validator_lines(inputs.validators),
        *_active_contract_lines(inputs.contracts),
        *_schema_lines(inputs.schemas),
        *_generated_report_lines(inputs.generated_reports),
        *_latest_proof_artifact_lines(inputs),
        *_non_goal_lines(inputs.non_goals),
    ]


def _scope_lines() -> list[str]:
    return [
        "## Scope",
        "",
        "This index summarizes active governance, verification, contract, schema, and generated report surfaces.",
        "",
        "This index is not authoritative. Checked-in contracts, schemas, validators, generated proof artifacts, and the changelog remain the source of truth.",
        "",
    ]


def _current_version_lines(version: ChangelogVersion) -> list[str]:
    return [
        "## Current version",
        "",
        f"* Version: `{version.version}`",
        f"* Date: `{version.date}`",
        f"* Status: {version.status}",
        "",
    ]


def _verification_status_lines(verification: VerifySummary) -> list[str]:
    return [
        "## Verification status",
        "",
        f"* Status: `{verification.status}`",
        f"* Summary code: `{verification.summary_code}`",
        f"* Total checks: {verification.total_checks}",
        f"* Failed checks: {verification.failed_check_count}",
        f"* Run ID: `{verification.run_id}`",
        f"* Generated at: `{verification.generated_at}`",
        "",
    ]


def _registered_validator_lines(validators: tuple[str, ...]) -> list[str]:
    return [
        "## Registered validators",
        "",
        "| Order | Validator |",
        "| --: | --- |",
        *[
            f"| {index} | `{validator}` |"
            for index, validator in enumerate(validators, start=1)
        ],
        "",
    ]


def _active_contract_lines(contracts: tuple[ContractSummary, ...]) -> list[str]:
    return [
        "## Active contracts",
        "",
        "| Path | Version | Role |",
        "| --- | --- | --- |",
        *[
            f"| `{contract.path}` | `{contract.version}` | {contract.role} |"
            for contract in contracts
        ],
        "",
    ]


def _schema_lines(schemas: tuple[SchemaSummary, ...]) -> list[str]:
    return [
        "## Schemas",
        "",
        "| Path | Title |",
        "| --- | --- |",
        *[
            f"| `{schema.path}` | {schema.title} |"
            for schema in schemas
        ],
        "",
    ]


def _generated_report_lines(reports: tuple[str, ...]) -> list[str]:
    return [
        "## Generated reports",
        "",
        "| Path | Authority |",
        "| --- | --- |",
        *[
            f"| `{report}` | non-authoritative |"
            for report in reports
        ],
        "",
    ]


def _latest_proof_artifact_lines(inputs: GovernanceIndexInputs) -> list[str]:
    verification = inputs.verification
    return [
        "## Latest proof artifact",
        "",
        f"* Path: `{inputs.proof_artifact_path}`",
        f"* Status: `{verification.status}`",
        f"* Check count: {verification.total_checks}",
        f"* Failure count: {verification.failed_check_count}",
        "",
    ]


def _non_goal_lines(non_goals: tuple[str, ...]) -> list[str]:
    return [
        "## Non-goals",
        "",
        *[
            f"* {non_goal}"
            for non_goal in non_goals
        ],
        "",
    ]


def _latest_changelog_version(path: Path) -> ChangelogVersion:
    text = path.read_text()
    match = re.search(r"^## (v\d+\.\d+\.\d+) - ([0-9-]+)\n\n\*\*Status:\*\* (.+)$", text, re.MULTILINE)
    if match is None:
        return ChangelogVersion("unknown", "unknown", "unknown")
    return ChangelogVersion(match.group(1), match.group(2), match.group(3))


def _latest_verify_summary(path: Path) -> VerifySummary:
    data = _load_json(path)
    summary = data.get("summary", {})
    return VerifySummary(
        status=str(data.get("status", "unknown")),
        summary_code=str(data.get("summary_code", "unknown")),
        total_checks=int(summary.get("total_checks", 0)),
        failed_check_count=int(summary.get("failed_check_count", 0)),
        run_id=str(data.get("run_id", "unknown")),
        generated_at=str(data.get("generated_at", "unknown")),
    )


def _contract_summaries(root: Path) -> tuple[ContractSummary, ...]:
    return tuple(
        _contract_summary(root, path)
        for path in sorted((root / "contracts").glob("*.json"))
    )


def _contract_summary(root: Path, path: Path) -> ContractSummary:
    data = _load_json(path)
    return ContractSummary(
        path=_relative_path(root, path),
        version=str(data.get("version", "unknown")),
        role=CONTRACT_ROLES.get(path.name, _role_from_filename(path.name)),
    )


def _schema_summaries(root: Path) -> tuple[SchemaSummary, ...]:
    return tuple(
        _schema_summary(root, path)
        for path in sorted((root / "schemas").glob("*.json"))
    )


def _schema_summary(root: Path, path: Path) -> SchemaSummary:
    data = _load_json(path)
    title = data.get("title") or data.get("$id") or path.name
    return SchemaSummary(_relative_path(root, path), str(title))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _relative_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _role_from_filename(filename: str) -> str:
    stem = filename.removesuffix(".json").replace("_", " ")
    return stem
