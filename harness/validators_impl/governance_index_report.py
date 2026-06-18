from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness import governance_index_report
from harness.abi_manifest import ROOT
from harness.codes import GOVERNANCE_INDEX_REPORT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_REPORT_PATH = governance_index_report.REPORT_PATH
_REPORT_ROOT = ROOT
_VOLATILE_PREFIXES = (
    "* Run ID:",
    "* Generated at:",
)


@dataclass(frozen=True)
class GovernanceIndexIssue:
    reason: str
    contract_field: str
    detail: str


class GovernanceIndexReportValidator(BaseValidator):
    name = "governance_index_report"
    subsystem = "governance_index_report"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _governance_index_issue(_REPORT_PATH)
        if issue is not None:
            return _failure_result(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Generated governance index matches the current governance surfaces",
        )


def _governance_index_issue(report_path: Path) -> GovernanceIndexIssue | None:
    if not report_path.is_file():
        return _issue("missing_index_file", "docs/generated/governance_index.md", f"Missing governance index file: {report_path}")
    actual = report_path.read_text()
    expected = governance_index_report.expected_report_text(_REPORT_ROOT)
    inputs = governance_index_report.load_report_inputs(_REPORT_ROOT)
    return _first_issue(
        _manual_edit_issue(actual),
        _current_version_issue(actual, inputs),
        _verification_status_issue(actual, inputs),
        _registered_validator_issue(actual, inputs),
        _active_contract_issue(actual, inputs),
        _schema_issue(actual, inputs),
        _generated_report_issue(actual, inputs),
        _latest_proof_artifact_issue(actual, inputs),
        _non_goal_issue(actual, inputs),
        _stale_report_issue(actual, expected),
    )


def _manual_edit_issue(actual: str) -> GovernanceIndexIssue | None:
    if "This document is generated. Do not edit manually." in actual:
        return None
    return _issue("manual_edit_detected", "generated_notice", "Generated edit warning is missing or changed")


def _current_version_issue(actual: str, inputs: governance_index_report.GovernanceIndexInputs) -> GovernanceIndexIssue | None:
    version = inputs.current_version
    if f"* Version: `{version.version}`" not in actual:
        return _issue("missing_current_version", "current_version.version", f"Missing current version {version.version}")
    if f"* Date: `{version.date}`" not in actual:
        return _issue("missing_current_version", "current_version.date", f"Missing current version date {version.date}")
    if f"* Status: {version.status}" not in actual:
        return _issue("missing_current_version", "current_version.status", f"Missing current version status {version.status}")
    return None


def _verification_status_issue(actual: str, inputs: governance_index_report.GovernanceIndexInputs) -> GovernanceIndexIssue | None:
    verification = inputs.verification
    expected_lines = (
        ("verification.status", f"* Status: `{verification.status}`"),
        ("verification.summary_code", f"* Summary code: `{verification.summary_code}`"),
        ("verification.total_checks", f"* Total checks: {verification.total_checks}"),
        ("verification.failed_check_count", f"* Failed checks: {verification.failed_check_count}"),
        ("verification.run_id", "* Run ID:"),
        ("verification.generated_at", "* Generated at:"),
    )
    for contract_field, expected in expected_lines:
        if expected not in actual:
            return _issue("missing_verification_status", contract_field, f"Missing verification field {contract_field}")
    return None


def _registered_validator_issue(actual: str, inputs: governance_index_report.GovernanceIndexInputs) -> GovernanceIndexIssue | None:
    for index, validator in enumerate(inputs.validators, start=1):
        if f"| {index} | `{validator}` |" not in actual:
            return _issue("missing_registered_validator", f"validators.{validator}", f"Missing registered validator {validator}")
    return None


def _active_contract_issue(actual: str, inputs: governance_index_report.GovernanceIndexInputs) -> GovernanceIndexIssue | None:
    for contract in inputs.contracts:
        if f"`{contract.path}`" not in actual:
            return _issue("missing_active_contract", f"contracts.{contract.path}", f"Missing active contract {contract.path}")
    return None


def _schema_issue(actual: str, inputs: governance_index_report.GovernanceIndexInputs) -> GovernanceIndexIssue | None:
    for schema in inputs.schemas:
        if f"`{schema.path}`" not in actual:
            return _issue("missing_schema", f"schemas.{schema.path}", f"Missing schema {schema.path}")
    return None


def _generated_report_issue(actual: str, inputs: governance_index_report.GovernanceIndexInputs) -> GovernanceIndexIssue | None:
    if f"`{governance_index_report.GENERATED_REPORT_REFERENCES[0]}`" not in actual:
        return _issue("missing_syscall_report_reference", "generated_reports.syscall_surface", "Missing syscall surface report reference")
    if f"`{governance_index_report.GENERATED_REPORT_REFERENCES[1]}`" not in actual:
        return _issue("missing_abi_report_reference", "generated_reports.abi_surface", "Missing ABI surface report reference")
    for report in inputs.generated_reports:
        if f"`{report}`" not in actual:
            return _issue("missing_generated_report_reference", f"generated_reports.{report}", f"Missing generated report {report}")
    return None


def _latest_proof_artifact_issue(actual: str, inputs: governance_index_report.GovernanceIndexInputs) -> GovernanceIndexIssue | None:
    if f"* Path: `{inputs.proof_artifact_path}`" not in actual:
        return _issue("missing_latest_proof_artifact", "latest_proof_artifact.path", "Missing latest proof artifact path")
    if f"* Check count: {inputs.verification.total_checks}" not in actual:
        return _issue("missing_latest_proof_artifact", "latest_proof_artifact.check_count", "Missing latest proof check count")
    if f"* Failure count: {inputs.verification.failed_check_count}" not in actual:
        return _issue("missing_latest_proof_artifact", "latest_proof_artifact.failure_count", "Missing latest proof failure count")
    return None


def _non_goal_issue(actual: str, inputs: governance_index_report.GovernanceIndexInputs) -> GovernanceIndexIssue | None:
    for non_goal in inputs.non_goals:
        if f"* {non_goal}" not in actual:
            return _issue("missing_non_goal", f"non_goals.{non_goal}", f"Missing non-goal {non_goal}")
    return None


def _stale_report_issue(actual: str, expected: str) -> GovernanceIndexIssue | None:
    if _stable_text(actual) == _stable_text(expected):
        return None
    return _issue("stale_index_content", "docs/generated/governance_index.md", "Governance index content does not match generated output")


def _stable_text(text: str) -> str:
    lines = _normalize_newlines(text).splitlines()
    return "\n".join(
        line
        for line in lines
        if not line.startswith(_VOLATILE_PREFIXES)
    )


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n")


def _first_issue(*issues: GovernanceIndexIssue | None) -> GovernanceIndexIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, contract_field: str, detail: str) -> GovernanceIndexIssue:
    return GovernanceIndexIssue(reason, contract_field, detail)


def _failure_result(issue: GovernanceIndexIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=GOVERNANCE_INDEX_REPORT_INVALID,
        detail=f"Governance index report invalid: {issue.reason}: {issue.contract_field}: {issue.detail}",
        action="Regenerate docs/generated/governance_index.md from harness.governance_index_report",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
