from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.codes import BOOT_BLOCKER_REPORT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_REPORT_PATH = _ROOT / "artifacts" / "runtime" / "boot_blocker_report.json"
_BOOT_DOC_PATH = _ROOT / "docs" / "BOOT.md"
_BOOT_BLOCKERS_PATH = _ROOT / "docs" / "BOOT_BLOCKERS.md"
_RUNTIME_EVIDENCE_PATH = _ROOT / "docs" / "RUNTIME_EVIDENCE.md"
_RELEASE_EVIDENCE_PATH = _ROOT / "docs" / "RELEASE_EVIDENCE.md"

_EXPECTED_FIELDS = {
    "phase": "v0.3.0",
    "outcome": "blocked",
    "evidence_type": "boot-blocker-report",
    "generated_by": "scripts/boot_blocker_report.sh",
    "validator": "boot_blocker_report",
    "blocker_category": "missing_boot_protocol_and_image_packaging",
    "next_required_fix": "Add a governed boot protocol, linker script, loader configuration, and boot image packaging before claiming QEMU boot evidence.",
}

_REQUIRED_MISSING_COMPONENTS = (
    "linker script",
    "boot protocol",
    "loader configuration",
    "boot image packaging",
)

_REQUIRED_CURRENT_SURFACES = (
    "kernel/arch/x86_64/boot.asm defines a 64-bit _start symbol",
    "kernel/main.odin exports kernel_entry",
    "kernel/arch/x86_64/serial.odin initializes COM1 serial output",
    "scripts/runtime_smoke.sh proves runtime-adjacent object and symbol evidence",
)

_REQUIRED_NON_CLAIMS = (
    "QEMU boot",
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

_REQUIRED_DOC_REFERENCES = (
    "artifacts/runtime/boot_blocker_report.json",
    "scripts/boot_blocker_report.sh",
    "boot_blocker_report",
    "missing_boot_protocol_and_image_packaging",
)


@dataclass(frozen=True)
class BootBlockerIssue:
    reason: str
    contract_field: str
    detail: str


class BootBlockerReportValidator(BaseValidator):
    name = "boot_blocker_report"
    subsystem = "boot_blocker_report"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _boot_blocker_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Boot blocker report identifies why QEMU boot cannot yet be claimed",
        )


def _boot_blocker_issue() -> BootBlockerIssue | None:
    report_issue, report = _load_report()
    if report_issue is not None:
        return report_issue

    docs_issue = _documentation_issue()
    if docs_issue is not None:
        return docs_issue

    return _first_issue(
        _field_contract_issue(report),
        _list_contract_issue(report, "missing_components", _REQUIRED_MISSING_COMPONENTS, "missing_component"),
        _list_contract_issue(report, "current_surfaces", _REQUIRED_CURRENT_SURFACES, "missing_current_surface"),
        _list_contract_issue(report, "cannot_claim", _REQUIRED_NON_CLAIMS, "missing_non_claim"),
    )


def _load_report() -> tuple[BootBlockerIssue | None, dict[str, object]]:
    if not _REPORT_PATH.is_file():
        return _issue("missing_report", "boot_blocker.report", "Missing boot blocker report"), {}
    try:
        report = json.loads(_REPORT_PATH.read_text())
    except json.JSONDecodeError:
        return _issue("invalid_report_json", "boot_blocker.report_json", "Boot blocker report is not valid JSON"), {}
    if not isinstance(report, dict):
        return _issue("invalid_report_json", "boot_blocker.report_json", "Boot blocker report must be a JSON object"), {}
    return None, report


def _documentation_issue() -> BootBlockerIssue | None:
    for path in (_BOOT_DOC_PATH, _BOOT_BLOCKERS_PATH, _RUNTIME_EVIDENCE_PATH, _RELEASE_EVIDENCE_PATH):
        if not path.is_file():
            return _issue("missing_documentation", _relative_contract_field(path), f"Missing boot blocker documentation: {path}")
        text = path.read_text()
        for reference in _REQUIRED_DOC_REFERENCES:
            if reference not in text:
                return _issue("missing_documentation_reference", f"{_relative_contract_field(path)}.{reference}", f"Boot blocker documentation is missing {reference}")
    return None


def _field_contract_issue(report: dict[str, object]) -> BootBlockerIssue | None:
    for field, expected in _EXPECTED_FIELDS.items():
        if report.get(field) != expected:
            return _issue("field_mismatch", f"boot_blocker.{field}", f"Boot blocker field {field} must be {expected}")
    return None


def _list_contract_issue(
    report: dict[str, object],
    field: str,
    required_values: tuple[str, ...],
    reason: str,
) -> BootBlockerIssue | None:
    values = report.get(field)
    if not isinstance(values, list):
        return _issue(reason, f"boot_blocker.{field}", f"Boot blocker field {field} must be a list")
    for required in required_values:
        if required not in values:
            return _issue(reason, f"boot_blocker.{field}.{required}", f"Boot blocker field {field} is missing {required}")
    return None


def _relative_contract_field(path: Path) -> str:
    try:
        return str(path.relative_to(_ROOT))
    except ValueError:
        return "/".join(path.parts[-2:])


def _first_issue(*issues: BootBlockerIssue | None) -> BootBlockerIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> BootBlockerIssue:
    return BootBlockerIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: BootBlockerIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=BOOT_BLOCKER_REPORT_INVALID,
        detail=issue.detail,
        action="Run scripts/boot_blocker_report.sh and keep boot blocker documentation aligned",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
