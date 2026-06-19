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

_COMMON_FIELDS = {
    "phase": "v0.3.9",
    "evidence_type": "boot-blocker-report",
    "generated_by": "scripts/boot_blocker_report.sh",
    "validator": "boot_blocker_report",
}

_PASS_FIELDS = {
    "outcome": "pass",
    "blocker_category": "none",
    "next_required_fix": "Do not expand runtime claims beyond QEMU serial smoke until separate hardware trap, userspace, or subsystem evidence exists.",
}

_TOOLING_BLOCKER_FIELDS = {
    "outcome": "blocked",
    "blocker_category": "missing_iso_generation_tooling",
    "next_required_fix": "Install or provide the documented Limine executable, Limine bootloader artifacts, and xorriso executable so scripts/build_boot_image.sh can create artifacts/runtime/boot_image/kozo.iso, then run scripts/qemu_smoke.sh to capture serial output before claiming QEMU boot evidence.",
}

_QEMU_BLOCKER_FIELDS = {
    "outcome": "blocked",
    "blocker_category": "missing_qemu_serial_evidence",
    "next_required_fix": "Run scripts/qemu_smoke.sh with QEMU available, capture serial output, and validate the expected KOZO marker before claiming QEMU boot evidence.",
}

_EXACT_QEMU_BLOCKER_FIELDS = {
    "outcome": "blocked",
    "next_required_fix": "Resolve the exact QEMU smoke blocker recorded in artifacts/runtime/qemu_smoke.metadata.json before claiming QEMU boot evidence.",
}

_TOOLING_MISSING_COMPONENTS = (
    "Limine executable",
    "xorriso executable",
    "Limine bootloader artifacts",
    "bootable ISO artifact",
    "validated QEMU serial smoke execution",
)

_QEMU_MISSING_COMPONENTS = (
    "validated QEMU serial smoke execution",
)

_PASS_CURRENT_SURFACES = (
    "scripts/qemu_smoke.sh captured artifacts/runtime/qemu_smoke.log",
    "artifacts/runtime/qemu_smoke.metadata.json records passing QEMU serial smoke metadata",
)

_EXACT_QEMU_CURRENT_SURFACES = (
    "scripts/qemu_smoke.sh records exact QEMU serial smoke blocker metadata",
    "artifacts/runtime/qemu_smoke.metadata.json records the current QEMU smoke blocker",
)

_COMMON_CURRENT_SURFACES = (
    "kernel/arch/x86_64/boot.asm defines a 64-bit _start symbol",
    "kernel/main.odin exports kernel_entry",
    "kernel/arch/x86_64/serial.odin initializes COM1 serial output",
    "linker/kernel.ld defines the kernel ELF layout",
    "boot/limine.conf defines the Limine boot entry",
    "scripts/build_boot_image.sh stages the boot image skeleton",
    "docs/BOOT_TOOLING.md documents Limine and xorriso acquisition paths",
    "scripts/build_boot_image.sh implements the Limine and xorriso ISO generation path",
    "scripts/qemu_smoke.sh fails closed until kozo.iso exists",
    "scripts/runtime_smoke.sh proves runtime-adjacent object and symbol evidence",
)

_TOOLING_CURRENT_SURFACES = (
    "scripts/build_boot_image.sh writes package metadata for the blocked ISO tooling attempt",
)

_QEMU_CURRENT_SURFACES = (
    "scripts/build_boot_image.sh produced artifacts/runtime/boot_image/kozo.iso",
    "artifacts/runtime/boot_image/package_metadata.json records packaged ISO metadata",
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
    "artifacts/runtime/boot_image/package_metadata.json",
    "artifacts/runtime/boot_image/kozo.iso",
    "artifacts/runtime/qemu_smoke.metadata.json",
    "artifacts/runtime/qemu_smoke.log",
    "docs/BOOT_TOOLING.md",
    "scripts/boot_blocker_report.sh",
    "scripts/qemu_smoke.sh",
    "boot_blocker_report",
    "missing_iso_generation_tooling",
    "missing_qemu_serial_evidence",
)

_ALLOWED_EXACT_QEMU_BLOCKERS = (
    "missing_iso_generation_tooling",
    "missing_qemu_tooling",
    "missing_boot_image",
    "missing_serial_marker",
    "qemu_launch_failed",
    "qemu_timeout",
    "limine_load_failed",
    "kernel_entry_not_reached",
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
        _list_contract_issue(report, "missing_components", _required_missing_components(report), "missing_component"),
        _list_contract_issue(report, "current_surfaces", _required_current_surfaces(report), "missing_current_surface"),
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
    for field, expected in _COMMON_FIELDS.items():
        if report.get(field) != expected:
            return _issue("field_mismatch", f"boot_blocker.{field}", f"Boot blocker field {field} must be {expected}")
    expected_fields = _expected_blocker_fields(report)
    if expected_fields is None:
        return _issue("field_mismatch", "boot_blocker.blocker_category", "Boot blocker category must be none, missing_iso_generation_tooling, missing_qemu_serial_evidence, or an allowed exact QEMU blocker")
    for field, expected in expected_fields.items():
        if report.get(field) != expected:
            return _issue("field_mismatch", f"boot_blocker.{field}", f"Boot blocker field {field} must be {expected}")
    return None


def _expected_blocker_fields(report: dict[str, object]) -> dict[str, object] | None:
    if report.get("blocker_category") == "none":
        return _PASS_FIELDS
    if report.get("blocker_category") == "missing_iso_generation_tooling":
        return _TOOLING_BLOCKER_FIELDS
    if report.get("blocker_category") == "missing_qemu_serial_evidence":
        return _QEMU_BLOCKER_FIELDS
    if report.get("blocker_category") in _ALLOWED_EXACT_QEMU_BLOCKERS:
        return _EXACT_QEMU_BLOCKER_FIELDS | {"blocker_category": report.get("blocker_category")}
    return None


def _required_missing_components(report: dict[str, object]) -> tuple[str, ...]:
    if report.get("blocker_category") == "none":
        return ()
    if report.get("blocker_category") == "missing_iso_generation_tooling":
        return _TOOLING_MISSING_COMPONENTS
    if report.get("blocker_category") == "missing_qemu_serial_evidence":
        return _QEMU_MISSING_COMPONENTS
    if report.get("blocker_category") in _ALLOWED_EXACT_QEMU_BLOCKERS:
        return _QEMU_MISSING_COMPONENTS
    return _TOOLING_MISSING_COMPONENTS


def _required_current_surfaces(report: dict[str, object]) -> tuple[str, ...]:
    if report.get("blocker_category") == "none":
        return _COMMON_CURRENT_SURFACES + _PASS_CURRENT_SURFACES
    if report.get("blocker_category") == "missing_iso_generation_tooling":
        return _COMMON_CURRENT_SURFACES + _TOOLING_CURRENT_SURFACES
    if report.get("blocker_category") == "missing_qemu_serial_evidence":
        return _COMMON_CURRENT_SURFACES + _QEMU_CURRENT_SURFACES
    if report.get("blocker_category") in _ALLOWED_EXACT_QEMU_BLOCKERS:
        return _COMMON_CURRENT_SURFACES + _EXACT_QEMU_CURRENT_SURFACES
    return _COMMON_CURRENT_SURFACES + _TOOLING_CURRENT_SURFACES


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
