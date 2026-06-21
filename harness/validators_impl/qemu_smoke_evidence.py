from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.runtime_evidence_taxonomy import (
    get_expected_smoke_marker,
    get_qemu_smoke_blocker_categories,
    get_smoke_marker_order,
    get_smoke_outcomes,
)
from harness.codes import OK, QEMU_SMOKE_EVIDENCE_INVALID
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_METADATA_PATH = _ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_LOG_PATH = _ROOT / "artifacts" / "runtime" / "qemu_smoke.log"
_STDERR_LOG_PATH = _ROOT / "artifacts" / "runtime" / "qemu_smoke.stderr.log"
_SUMMARY_PATH = _ROOT / "artifacts" / "runtime" / "qemu_smoke.summary.txt"
_BOOT_BLOCKER_REPORT_PATH = _ROOT / "artifacts" / "runtime" / "boot_blocker_report.json"
_BOOT_DOC_PATH = _ROOT / "docs" / "BOOT.md"
_RUNTIME_EVIDENCE_PATH = _ROOT / "docs" / "RUNTIME_EVIDENCE.md"
_RELEASE_EVIDENCE_PATH = _ROOT / "docs" / "RELEASE_EVIDENCE.md"

_COMMON_FIELDS = {
    "phase": "v0.4.1",
    "evidence_type": "qemu-serial-smoke",
    "boot_protocol": "Limine",
    "architecture": "x86_64",
    "generated_by": "scripts/qemu_smoke.sh",
    "serial_log": "artifacts/runtime/qemu_smoke.log",
    "stderr_log": "artifacts/runtime/qemu_smoke.stderr.log",
    "validator": "qemu_smoke_evidence",
}

_PASS_PROVES = (
    "QEMU launched the KOZO ISO",
    "serial output was captured",
    "the expected KOZO boot smoke marker was observed",
)

_BLOCKED_PROVES = (
    "QEMU serial smoke was attempted or checked",
    "QEMU boot evidence remains unclaimed",
)

_REQUIRED_NON_GOALS = (
    "hardware trap execution",
    "Linux compatibility",
    "POSIX compatibility",
    "general userspace execution",
    "process model behavior",
    "VFS behavior",
    "scheduler maturity",
    "ELF loading",
    "file descriptor behavior",
    "production readiness",
)

_ALLOWED_BLOCKERS = get_qemu_smoke_blocker_categories()
_EARLY_MARKERS = get_smoke_marker_order()
_PASS_OUTCOME, _BLOCKED_OUTCOME = get_smoke_outcomes()
_EXPECTED_MARKER = get_expected_smoke_marker()

_REQUIRED_DOC_REFERENCES = (
    "artifacts/runtime/qemu_smoke.log",
    "artifacts/runtime/qemu_smoke.stderr.log",
    "artifacts/runtime/qemu_smoke.metadata.json",
    "artifacts/runtime/qemu_smoke.summary.txt",
    "qemu_smoke_evidence",
    "KOZO_BOOT_SMOKE_OK",
)


@dataclass(frozen=True)
class QemuSmokeIssue:
    reason: str
    contract_field: str
    detail: str


class QemuSmokeEvidenceValidator(BaseValidator):
    name = "qemu_smoke_evidence"
    subsystem = "qemu_smoke_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _qemu_smoke_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="QEMU smoke evidence records pass or exact blocker without overclaiming runtime behavior",
        )


def _qemu_smoke_issue() -> QemuSmokeIssue | None:
    metadata_issue, metadata = _load_json(_METADATA_PATH, "qemu_smoke.metadata")
    if metadata_issue is not None:
        return metadata_issue

    blocker_issue, blocker_report = _load_json(_BOOT_BLOCKER_REPORT_PATH, "boot_blocker.report")
    if blocker_issue is not None:
        return blocker_issue

    return _first_issue(
        _common_field_issue(metadata),
        _stderr_log_issue(),
        _outcome_issue(metadata),
        _blocked_marker_issue(metadata),
        _pass_evidence_issue(metadata),
        _diagnostic_field_issue(metadata),
        _entry_handoff_field_issue(metadata),
        _observed_marker_issue(metadata),
        _marker_sequence_issue(metadata),
        _summary_issue(metadata),
        _blocker_taxonomy_issue(metadata),
        _list_contract_issue(metadata, "does_not_prove", _REQUIRED_NON_GOALS, "missing_non_goal"),
        _blocker_report_issue(metadata, blocker_report),
        _documentation_issue(),
    )


def _load_json(path: Path, contract_field: str) -> tuple[QemuSmokeIssue | None, dict[str, object]]:
    if not path.is_file():
        return _issue("missing_metadata", contract_field, f"Missing QEMU smoke metadata: {path}"), {}
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError:
        return _issue("invalid_metadata", contract_field, f"QEMU smoke metadata is not valid JSON: {path}"), {}
    if not isinstance(value, dict):
        return _issue("invalid_metadata", contract_field, f"QEMU smoke metadata must be a JSON object: {path}"), {}
    return None, value


def _common_field_issue(metadata: dict[str, object]) -> QemuSmokeIssue | None:
    for field, expected in _COMMON_FIELDS.items():
        if metadata.get(field) != expected:
            return _issue("field_mismatch", f"qemu_smoke.{field}", f"QEMU smoke field {field} must be {expected}")
    if metadata.get("expected_marker") != _EXPECTED_MARKER:
        return _issue("missing_expected_marker", "qemu_smoke.expected_marker", "QEMU smoke expected marker must match runtime evidence taxonomy")
    if not metadata.get("boot_image"):
        return _issue("missing_boot_image_reference", "qemu_smoke.boot_image", "QEMU smoke boot image reference must be non-empty")
    if not isinstance(metadata.get("qemu_exit_code"), int):
        return _issue("field_mismatch", "qemu_smoke.qemu_exit_code", "QEMU smoke exit code must be recorded")
    return None


def _stderr_log_issue() -> QemuSmokeIssue | None:
    if not _STDERR_LOG_PATH.is_file():
        return _issue("missing_stderr_log", "qemu_smoke.stderr_log", "QEMU smoke metadata requires a QEMU stderr log")
    return None


def _diagnostic_field_issue(metadata: dict[str, object]) -> QemuSmokeIssue | None:
    if metadata.get("early_markers") != list(_EARLY_MARKERS):
        return _issue("field_mismatch", "qemu_smoke.early_markers", "QEMU smoke early marker list must match the boot marker contract")
    if not isinstance(metadata.get("observed_markers"), list):
        return _issue("field_mismatch", "qemu_smoke.observed_markers", "QEMU smoke observed markers must be recorded")
    if not isinstance(metadata.get("earliest_observed_marker"), str):
        return _issue("field_mismatch", "qemu_smoke.earliest_observed_marker", "QEMU smoke earliest observed marker must be recorded")
    if not isinstance(metadata.get("timed_out"), bool):
        return _issue("field_mismatch", "qemu_smoke.timed_out", "QEMU smoke timeout status must be recorded")
    if not isinstance(metadata.get("timeout_seconds"), int):
        return _issue("field_mismatch", "qemu_smoke.timeout_seconds", "QEMU smoke timeout seconds must be recorded")
    if not isinstance(metadata.get("serial_log_bytes"), int):
        return _issue("field_mismatch", "qemu_smoke.serial_log_bytes", "QEMU smoke serial byte count must be recorded")
    if not isinstance(metadata.get("stderr_log_bytes"), int):
        return _issue("field_mismatch", "qemu_smoke.stderr_log_bytes", "QEMU smoke stderr byte count must be recorded")
    if _SERIAL_LOG_PATH.is_file() and metadata.get("serial_log_bytes") != _SERIAL_LOG_PATH.stat().st_size:
        return _issue("byte_count_mismatch", "qemu_smoke.serial_log_bytes", "QEMU smoke serial byte count must match the serial log")
    if _STDERR_LOG_PATH.is_file() and metadata.get("stderr_log_bytes") != _STDERR_LOG_PATH.stat().st_size:
        return _issue("byte_count_mismatch", "qemu_smoke.stderr_log_bytes", "QEMU smoke stderr byte count must match the stderr log")
    return None


def _observed_marker_issue(metadata: dict[str, object]) -> QemuSmokeIssue | None:
    observed = metadata.get("observed_markers")
    if not isinstance(observed, list):
        return None
    if any(marker not in _EARLY_MARKERS for marker in observed):
        return _issue("marker_consistency", "qemu_smoke.observed_markers", "QEMU smoke observed markers must be known early markers")
    actual_observed = _observed_markers_from_logs()
    if observed != actual_observed:
        return _issue("marker_consistency", "qemu_smoke.observed_markers", "QEMU smoke observed markers must match serial and stderr logs")
    earliest = metadata.get("earliest_observed_marker")
    expected_earliest = actual_observed[0] if actual_observed else ""
    if earliest != expected_earliest:
        return _issue("marker_consistency", "qemu_smoke.earliest_observed_marker", "QEMU smoke earliest observed marker must match observed markers")
    return None


def _observed_markers_from_logs() -> list[str]:
    serial_text = _SERIAL_LOG_PATH.read_text(errors="replace") if _SERIAL_LOG_PATH.is_file() else ""
    stderr_text = _STDERR_LOG_PATH.read_text(errors="replace") if _STDERR_LOG_PATH.is_file() else ""
    combined = f"{serial_text}\n{stderr_text}"
    return [marker for marker in _EARLY_MARKERS if marker in combined]


def _summary_issue(metadata: dict[str, object]) -> QemuSmokeIssue | None:
    if not _SUMMARY_PATH.is_file():
        return _issue("missing_summary", "qemu_smoke.summary", "Missing QEMU smoke summary artifact")
    text = _SUMMARY_PATH.read_text(errors="replace")
    return _first_issue(
        _summary_section_issue(text),
        _summary_outcome_issue(text, metadata),
        _summary_blocker_issue(text, metadata),
        _summary_marker_issue(text, metadata),
        _summary_reference_issue(text),
    )


def _summary_section_issue(text: str) -> QemuSmokeIssue | None:
    for section in (
        "QEMU Smoke Summary",
        "Outcome",
        "Blocker Category",
        "Observed Markers",
        "Expected Marker",
        "Verifier Result",
        "Last 50 serial lines",
        "Last 50 stderr lines",
    ):
        if section not in text:
            return _issue("summary_missing_section", f"qemu_smoke.summary.{section}", f"QEMU smoke summary is missing {section}")
    return None


def _summary_outcome_issue(text: str, metadata: dict[str, object]) -> QemuSmokeIssue | None:
    expected = f"Outcome: {metadata.get('outcome')}"
    if expected not in text:
        return _issue("summary_metadata_mismatch", "qemu_smoke.summary.outcome", "QEMU smoke summary outcome must match metadata")
    return None


def _summary_blocker_issue(text: str, metadata: dict[str, object]) -> QemuSmokeIssue | None:
    blocker = "none" if metadata.get("outcome") == "pass" else metadata.get("blocker_category")
    expected = f"Blocker: {blocker}"
    if expected not in text:
        return _issue("summary_metadata_mismatch", "qemu_smoke.summary.blocker_category", "QEMU smoke summary blocker must match metadata")
    return None


def _summary_marker_issue(text: str, metadata: dict[str, object]) -> QemuSmokeIssue | None:
    marker = metadata.get("expected_marker")
    expected = f"Expected Marker: {marker}"
    if expected not in text:
        return _issue("summary_metadata_mismatch", "qemu_smoke.summary.expected_marker", "QEMU smoke summary expected marker must match metadata")
    for marker in metadata.get("observed_markers", []):
        if isinstance(marker, str) and f"  - {marker}" not in text:
            return _issue("summary_metadata_mismatch", "qemu_smoke.summary.observed_markers", "QEMU smoke summary observed markers must match metadata")
    return None


def _summary_reference_issue(text: str) -> QemuSmokeIssue | None:
    for reference in (
        "artifacts/runtime/qemu_smoke.log",
        "artifacts/runtime/qemu_smoke.stderr.log",
        "artifacts/runtime/qemu_smoke.metadata.json",
        "artifacts/runtime/boot_blocker_report.json",
    ):
        if reference not in text:
            return _issue("summary_missing_reference", f"qemu_smoke.summary.{reference}", f"QEMU smoke summary is missing {reference}")
    return None


def _log_text() -> str:
    serial_text = _SERIAL_LOG_PATH.read_text(errors="replace") if _SERIAL_LOG_PATH.is_file() else ""
    stderr_text = _STDERR_LOG_PATH.read_text(errors="replace") if _STDERR_LOG_PATH.is_file() else ""
    return f"{serial_text}\n{stderr_text}"


def _marker_sequence_issue(metadata: dict[str, object]) -> QemuSmokeIssue | None:
    log_text = _log_text()
    if metadata.get("outcome") == _PASS_OUTCOME:
        for marker in _EARLY_MARKERS:
            if marker not in log_text:
                return _issue("marker_sequence_incomplete", f"qemu_smoke.marker_sequence.{marker}", "QEMU smoke pass requires the full boot marker sequence")
    return _marker_order_issue(log_text)


def _marker_order_issue(log_text: str) -> QemuSmokeIssue | None:
    positions = [(marker, log_text.find(marker)) for marker in _EARLY_MARKERS if marker in log_text]
    ordered_positions = [position for _, position in positions]
    if ordered_positions != sorted(ordered_positions):
        return _issue("marker_order_invalid", "qemu_smoke.marker_sequence", "QEMU smoke markers must appear in boot order")
    return None


def _entry_handoff_field_issue(metadata: dict[str, object]) -> QemuSmokeIssue | None:
    if not isinstance(metadata.get("limine_entry_point_observed"), bool):
        return _issue("field_mismatch", "qemu_smoke.limine_entry_point_observed", "QEMU smoke metadata must record Limine entry-point evidence")
    if metadata.get("expected_entry_symbol") != "_start":
        return _issue("field_mismatch", "qemu_smoke.expected_entry_symbol", "QEMU smoke metadata must name _start as the expected entry symbol")
    if metadata.get("entry_marker_expected") != _EARLY_MARKERS[0]:
        return _issue("field_mismatch", "qemu_smoke.entry_marker_expected", "QEMU smoke metadata must name the first entry marker")
    if not isinstance(metadata.get("entry_marker_observed"), bool):
        return _issue("field_mismatch", "qemu_smoke.entry_marker_observed", "QEMU smoke metadata must record whether the entry marker was observed")
    if not isinstance(metadata.get("entry_fault_signal"), str):
        return _issue("field_mismatch", "qemu_smoke.entry_fault_signal", "QEMU smoke metadata must record the entry fault signal")
    if metadata.get("limine_entry_point_observed") != _has_limine_entry_point_evidence(_log_text()):
        return _issue("entry_handoff_mismatch", "qemu_smoke.limine_entry_point_observed", "QEMU smoke Limine entry-point metadata must match logs")
    if metadata.get("entry_marker_observed") != (_EARLY_MARKERS[0] in _observed_markers_from_logs()):
        return _issue("entry_handoff_mismatch", "qemu_smoke.entry_marker_observed", "QEMU smoke entry-marker metadata must match logs")
    return None


def _outcome_issue(metadata: dict[str, object]) -> QemuSmokeIssue | None:
    if metadata.get("outcome") == _PASS_OUTCOME:
        return _list_contract_issue(metadata, "proves", _PASS_PROVES, "missing_proves_claim")
    if metadata.get("outcome") == _BLOCKED_OUTCOME:
        return _blocked_outcome_issue(metadata)
    return _issue("field_mismatch", "qemu_smoke.outcome", "QEMU smoke outcome must be pass or blocked")


def _blocked_outcome_issue(metadata: dict[str, object]) -> QemuSmokeIssue | None:
    blocker = metadata.get("blocker_category")
    if blocker not in _ALLOWED_BLOCKERS:
        return _issue("unknown_blocker_category", "qemu_smoke.blocker_category", "QEMU smoke blocker category is not allowed")
    return _list_contract_issue(metadata, "proves", _BLOCKED_PROVES, "missing_proves_claim")


def _blocker_taxonomy_issue(metadata: dict[str, object]) -> QemuSmokeIssue | None:
    if metadata.get("outcome") != _BLOCKED_OUTCOME:
        return None
    expected = _expected_blocker_from_logs(metadata)
    if expected is None:
        return None
    if metadata.get("blocker_category") != expected:
        return _issue("blocker_taxonomy_mismatch", "qemu_smoke.blocker_category", "QEMU smoke blocker must match observed diagnostic markers")
    return None


def _expected_blocker_from_logs(metadata: dict[str, object]) -> str | None:
    blocker = metadata.get("blocker_category")
    if blocker in ("missing_iso_generation_tooling", "missing_qemu_tooling", "missing_boot_image", "qemu_launch_failed"):
        return None
    serial_text = _SERIAL_LOG_PATH.read_text(errors="replace") if _SERIAL_LOG_PATH.is_file() else ""
    stderr_text = _STDERR_LOG_PATH.read_text(errors="replace") if _STDERR_LOG_PATH.is_file() else ""
    combined = f"{serial_text}\n{stderr_text}"
    observed = _observed_markers_from_logs()
    if not combined.strip():
        return "limine_not_reached"
    if "limine" not in combined.lower() and not observed:
        return "limine_not_reached"
    if _has_lower_half_phdr_failure(combined):
        return "limine_lower_half_phdr"
    if "limine" in combined.lower() and _has_kernel_open_failure(combined):
        return "kernel_not_loaded"
    if "limine" in combined.lower() and not _has_kernel_load_evidence(combined, observed):
        return "kernel_not_loaded"
    if _EARLY_MARKERS[1] in observed and _EARLY_MARKERS[2] not in observed:
        return "serial_not_initialized"
    if _has_kernel_load_evidence(combined, observed) and _EARLY_MARKERS[0] not in observed:
        return "kernel_entry_not_reached"
    if _EARLY_MARKERS[0] in observed and _EARLY_MARKERS[2] not in observed:
        return "serial_not_initialized"
    if _EARLY_MARKERS[2] in observed and _EARLY_MARKERS[3] not in observed:
        return "marker_not_emitted"
    if observed and observed[0] != _EARLY_MARKERS[0]:
        return "qemu_timeout"
    return "qemu_timeout"


def _has_kernel_load_evidence(text: str, observed: list[str]) -> bool:
    lowered = text.lower()
    return bool(observed) or "entry point" in lowered or "handoff" in lowered or "starting kernel" in lowered


def _has_limine_entry_point_evidence(text: str) -> bool:
    return "elf entry point:" in text.lower()


def _has_kernel_open_failure(text: str) -> bool:
    lowered = text.lower()
    return "failed to open executable" in lowered or "failed to load executable" in lowered


def _has_lower_half_phdr_failure(text: str) -> bool:
    return "lower half phdrs are not allowed" in text.lower()


def _blocked_marker_issue(metadata: dict[str, object]) -> QemuSmokeIssue | None:
    if metadata.get("outcome") != _BLOCKED_OUTCOME:
        return None
    marker = metadata.get("expected_marker")
    if isinstance(marker, str) and _SERIAL_LOG_PATH.is_file() and marker in _SERIAL_LOG_PATH.read_text(errors="replace"):
        return _issue("marker_present_but_blocked", "qemu_smoke.outcome", "QEMU smoke cannot report blocked when the expected marker is present")
    return None


def _pass_evidence_issue(metadata: dict[str, object]) -> QemuSmokeIssue | None:
    if metadata.get("outcome") != _PASS_OUTCOME:
        return None
    if not _SERIAL_LOG_PATH.is_file():
        return _issue("missing_serial_log", "qemu_smoke.serial_log", "QEMU smoke pass metadata requires a serial log")
    marker = metadata.get("expected_marker")
    if not isinstance(marker, str) or marker not in _SERIAL_LOG_PATH.read_text(errors="replace"):
        return _issue("marker_missing", "qemu_smoke.expected_marker", "QEMU smoke serial log is missing the expected marker")
    return _pass_boot_image_issue(metadata)


def _pass_boot_image_issue(metadata: dict[str, object]) -> QemuSmokeIssue | None:
    boot_image = metadata.get("boot_image")
    if not isinstance(boot_image, str):
        return _issue("missing_boot_image_reference", "qemu_smoke.boot_image", "QEMU smoke boot image reference must be a string")
    image_path = Path(boot_image)
    if not image_path.is_absolute():
        image_path = _ROOT / image_path
    if not image_path.is_file():
        return _issue("missing_boot_image", "qemu_smoke.boot_image", "QEMU smoke pass metadata references a missing boot image")
    return None


def _list_contract_issue(
    metadata: dict[str, object],
    field: str,
    required_values: tuple[str, ...],
    reason: str,
) -> QemuSmokeIssue | None:
    values = metadata.get(field)
    if not isinstance(values, list):
        return _issue(reason, f"qemu_smoke.{field}", f"QEMU smoke field {field} must be a list")
    for required in required_values:
        if required not in values:
            return _issue(reason, f"qemu_smoke.{field}.{required}", f"QEMU smoke field {field} is missing {required}")
    return None


def _blocker_report_issue(metadata: dict[str, object], blocker_report: dict[str, object]) -> QemuSmokeIssue | None:
    if metadata.get("outcome") == _PASS_OUTCOME:
        expected_category = "none"
    else:
        expected_category = metadata.get("blocker_category")
    if blocker_report.get("blocker_category") != expected_category:
        return _issue("blocker_report_mismatch", "boot_blocker.blocker_category", "Boot blocker report must match QEMU smoke evidence")
    return None


def _documentation_issue() -> QemuSmokeIssue | None:
    for path in (_BOOT_DOC_PATH, _RUNTIME_EVIDENCE_PATH, _RELEASE_EVIDENCE_PATH):
        if not path.is_file():
            return _issue("missing_documentation", _contract_field(path), f"Missing QEMU smoke documentation: {path}")
        text = path.read_text()
        for reference in _REQUIRED_DOC_REFERENCES:
            if reference not in text:
                return _issue("missing_documentation_reference", f"{_contract_field(path)}.{reference}", f"QEMU smoke documentation is missing {reference}")
    return None


def _contract_field(path: Path) -> str:
    try:
        return str(path.relative_to(_ROOT))
    except ValueError:
        return "/".join(path.parts[-2:])


def _first_issue(*issues: QemuSmokeIssue | None) -> QemuSmokeIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> QemuSmokeIssue:
    return QemuSmokeIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: QemuSmokeIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=QEMU_SMOKE_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Run scripts/qemu_smoke.sh and keep QEMU smoke docs, metadata, and blocker state aligned",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
