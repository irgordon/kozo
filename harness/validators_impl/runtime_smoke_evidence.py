from __future__ import annotations

import re
import json
from dataclasses import dataclass
from pathlib import Path

from harness.codes import OK, RUNTIME_SMOKE_EVIDENCE_INVALID
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_LOG_PATH = _ROOT / "artifacts" / "runtime" / "runtime_smoke.log"
_RUNTIME_METADATA_PATH = _ROOT / "artifacts" / "runtime" / "runtime_smoke.metadata.json"
_RELEASE_EVIDENCE_PATH = _ROOT / "docs" / "RELEASE_EVIDENCE.md"
_EXPECTED_RESULT = "KOZO_RUNTIME_SMOKE_RESULT=pass"
_FAILURE_MARKERS = ("KOZO_RUNTIME_SMOKE_RESULT=fail", "FAIL:")
_VERSION_PATTERN = re.compile(r"^KOZO_RUNTIME_SMOKE_VERSION=([1-9][0-9]*)$", re.MULTILINE)
_EXPECTED_METADATA_FIELDS = {
    "evidence_type": "runtime-adjacent-object-symbol-smoke",
    "artifact": "artifacts/runtime/runtime_smoke.log",
    "generated_by": "scripts/runtime_smoke.sh",
    "validator": "runtime_smoke_evidence",
}
_REQUIRED_PROVES = (
    "freestanding x86_64 kernel object generation",
    "required entry symbol presence",
    "dispatcher symbol presence",
    "bridge symbol presence",
    "serial marker presence in binary evidence",
)
_REQUIRED_NON_GOALS = (
    "QEMU boot",
    "hardware trap execution",
    "Linux compatibility",
    "userspace execution",
    "process model",
    "VFS behavior",
    "scheduler maturity",
    "ELF loading",
    "file descriptor behavior",
    "production readiness",
)


@dataclass(frozen=True)
class RuntimeEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


class RuntimeSmokeEvidenceValidator(BaseValidator):
    name = "runtime_smoke_evidence"
    subsystem = "runtime_smoke_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _runtime_evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Runtime smoke evidence artifact exists, is bounded, and is referenced by release evidence policy",
        )


def _runtime_evidence_issue() -> RuntimeEvidenceIssue | None:
    if not _RUNTIME_LOG_PATH.is_file():
        return _issue("missing_runtime_artifact", "artifacts.runtime.runtime_smoke_log", "Missing runtime smoke artifact")
    if not _RUNTIME_METADATA_PATH.is_file():
        return _issue("missing_metadata", "artifacts.runtime.runtime_smoke_metadata", "Missing runtime smoke metadata")

    log_text = _RUNTIME_LOG_PATH.read_text()
    metadata_issue, metadata = _load_metadata(_RUNTIME_METADATA_PATH)
    if metadata_issue is not None:
        return metadata_issue
    release_evidence_text = _RELEASE_EVIDENCE_PATH.read_text()

    return _first_issue(
        _empty_log_issue(log_text),
        _metadata_issue(log_text),
        _metadata_contract_issue(metadata),
        _missing_marker_issue(log_text),
        _failure_marker_issue(log_text),
        _release_reference_issue(release_evidence_text),
    )


def _empty_log_issue(log_text: str) -> RuntimeEvidenceIssue | None:
    if log_text.strip():
        return None
    return _issue("empty_runtime_artifact", "artifacts.runtime.runtime_smoke_log", "Runtime smoke artifact is empty")


def _metadata_issue(log_text: str) -> RuntimeEvidenceIssue | None:
    if _VERSION_PATTERN.search(log_text):
        return None
    return _issue("malformed_runtime_metadata", "runtime_smoke.version", "Runtime smoke metadata is missing or malformed")


def _load_metadata(path: Path) -> tuple[RuntimeEvidenceIssue | None, dict[str, object]]:
    try:
        metadata = json.loads(path.read_text())
    except json.JSONDecodeError:
        return _issue("invalid_metadata_json", "runtime_smoke.metadata_json", "Runtime smoke metadata is not valid JSON"), {}
    if not isinstance(metadata, dict):
        return _issue("invalid_metadata_json", "runtime_smoke.metadata_json", "Runtime smoke metadata must be a JSON object"), {}
    return None, metadata


def _metadata_contract_issue(metadata: dict[str, object]) -> RuntimeEvidenceIssue | None:
    return _first_issue(
        _metadata_field_issue(metadata, "evidence_type", "wrong_evidence_type", "runtime_smoke.metadata.evidence_type"),
        _metadata_field_issue(metadata, "artifact", "metadata_artifact_mismatch", "runtime_smoke.metadata.artifact"),
        _metadata_field_issue(metadata, "generated_by", "metadata_generated_by_mismatch", "runtime_smoke.metadata.generated_by"),
        _metadata_field_issue(metadata, "validator", "metadata_validator_mismatch", "runtime_smoke.metadata.validator"),
        _metadata_claim_issue(metadata, "proves", _REQUIRED_PROVES, "metadata_missing_proves_claim", "runtime_smoke.metadata.proves"),
        _metadata_claim_issue(metadata, "does_not_prove", _REQUIRED_NON_GOALS, "metadata_missing_non_goal", "runtime_smoke.metadata.does_not_prove"),
    )


def _metadata_field_issue(metadata: dict[str, object], key: str, reason: str, contract_field: str) -> RuntimeEvidenceIssue | None:
    expected = _EXPECTED_METADATA_FIELDS[key]
    if metadata.get(key) == expected:
        return None
    return _issue(reason, contract_field, f"Runtime smoke metadata field {key} must be {expected}")


def _metadata_claim_issue(
    metadata: dict[str, object],
    key: str,
    required_claims: tuple[str, ...],
    reason: str,
    contract_field: str,
) -> RuntimeEvidenceIssue | None:
    claims = metadata.get(key)
    if not isinstance(claims, list):
        return _issue(reason, contract_field, f"Runtime smoke metadata field {key} must be a list")
    for claim in required_claims:
        if claim not in claims:
            return _issue(reason, f"{contract_field}.{claim}", f"Runtime smoke metadata field {key} is missing claim {claim}")
    return None


def _missing_marker_issue(log_text: str) -> RuntimeEvidenceIssue | None:
    for marker in _required_markers():
        if marker not in log_text:
            return _issue("missing_expected_marker", _marker_contract_field(marker), f"Runtime smoke artifact is missing marker {marker}")
    return None


def _failure_marker_issue(log_text: str) -> RuntimeEvidenceIssue | None:
    for marker in _FAILURE_MARKERS:
        if marker in log_text:
            return _issue("failure_marker_present", f"runtime_smoke.failure_marker.{marker}", f"Runtime smoke artifact contains failure marker {marker}")
    return None


def _release_reference_issue(release_evidence_text: str) -> RuntimeEvidenceIssue | None:
    if "artifacts/runtime/runtime_smoke.log" not in release_evidence_text:
        return _issue("missing_release_evidence_reference", "release_evidence.runtime_smoke_log", "Release evidence policy does not reference runtime smoke artifact")
    if "artifacts/runtime/runtime_smoke.metadata.json" not in release_evidence_text:
        return _issue("missing_release_metadata_reference", "release_evidence.runtime_smoke_metadata", "Release evidence policy does not reference runtime smoke metadata")
    return None


def _required_markers() -> tuple[str, ...]:
    return (
        "KOZO_RUNTIME_SMOKE_KIND=runtime-adjacent-object-symbol-smoke",
        "KOZO_RUNTIME_SMOKE_LIMITATION=not_boot_or_hardware_trap_execution",
        "KOZO_RUNTIME_SMOKE_MARKER=_start",
        "KOZO_RUNTIME_SMOKE_MARKER=kernel_entry",
        "KOZO_RUNTIME_SMOKE_MARKER=syscall_entry",
        "KOZO_RUNTIME_SMOKE_MARKER=syscall_dispatch",
        "KOZO_RUNTIME_SMOKE_MARKER=SYSCALL[DEBUG_HEARTBEAT] Recv Seq: 0x",
        "KOZO_RUNTIME_SMOKE_MARKER=SYSCALL[DEBUG_HEARTBEAT] New Time: 0x",
        _EXPECTED_RESULT,
    )


def _marker_contract_field(marker: str) -> str:
    marker_name = marker.removeprefix("KOZO_RUNTIME_SMOKE_MARKER=")
    return f"runtime_smoke.marker.{marker_name}"


def _first_issue(*issues: RuntimeEvidenceIssue | None) -> RuntimeEvidenceIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> RuntimeEvidenceIssue:
    return RuntimeEvidenceIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: RuntimeEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_SMOKE_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Run scripts/runtime_smoke.sh and keep docs/RELEASE_EVIDENCE.md aligned with runtime evidence policy",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
