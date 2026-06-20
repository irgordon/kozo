from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.codes import KERNEL_LOADABILITY_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_REPORT_PATH = _ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_BOOT_BLOCKER_REPORT_PATH = _ROOT / "artifacts" / "runtime" / "boot_blocker_report.json"

_COMMON_FIELDS = {
    "phase": "v0.4.2",
    "evidence_type": "kernel-elf-loadability",
    "generated_by": "scripts/kernel_elf_report.py",
    "kernel_elf": "artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf",
    "linker_script": "linker/kernel.ld",
    "architecture": "x86_64",
    "elf_class": "ELF64",
    "endianness": "little",
    "elf_type": "EXEC",
    "entry_symbol": "_start",
}

_REQUIRED_NON_CLAIMS = (
    "QEMU boot",
    "kernel entry execution",
    "serial initialization",
    "hardware trap execution",
    "Linux compatibility",
    "POSIX compatibility",
    "general userspace execution",
    "process model behavior",
    "VFS behavior",
    "scheduler maturity",
    "ELF loading by Limine",
    "file descriptor behavior",
    "production readiness",
)

_ISSUE_BLOCKERS = {
    "invalid_kernel_elf",
    "missing_load_segments",
    "invalid_kernel_entry",
    "linker_output_invalid",
    "limine_lower_half_phdr",
}


@dataclass(frozen=True)
class KernelLoadabilityIssue:
    reason: str
    contract_field: str
    detail: str


class KernelLoadabilityValidator(BaseValidator):
    name = "kernel_loadability"
    subsystem = "kernel_loadability"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _kernel_loadability_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Kernel ELF loadability report proves entry, architecture, and PT_LOAD structure without claiming boot",
        )


def _kernel_loadability_issue() -> KernelLoadabilityIssue | None:
    report_issue, report = _load_json(_REPORT_PATH, "kernel_loadability.report")
    if report_issue is not None:
        return report_issue

    blocker_issue, blocker_report = _load_json(_BOOT_BLOCKER_REPORT_PATH, "boot_blocker.report")
    if blocker_issue is not None:
        return blocker_issue

    return _first_issue(
        _common_field_issue(report),
        _entry_issue(report),
        _program_header_issue(report),
        _load_segment_issue(report),
        _load_layout_issue(report),
        _blocker_category_issue(report),
        _list_contract_issue(report, "does_not_prove", _REQUIRED_NON_CLAIMS, "missing_non_goal"),
        _blocker_report_issue(report, blocker_report),
    )


def _load_json(path: Path, contract_field: str) -> tuple[KernelLoadabilityIssue | None, dict[str, object]]:
    if not path.is_file():
        return _issue("missing_report", contract_field, f"Missing kernel ELF loadability report: {path}"), {}
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError:
        return _issue("invalid_report", contract_field, f"Kernel ELF loadability report is not valid JSON: {path}"), {}
    if not isinstance(value, dict):
        return _issue("invalid_report", contract_field, f"Kernel ELF loadability report must be a JSON object: {path}"), {}
    return None, value


def _common_field_issue(report: dict[str, object]) -> KernelLoadabilityIssue | None:
    for field, expected in _COMMON_FIELDS.items():
        if report.get(field) != expected:
            return _issue("field_mismatch", f"kernel_loadability.{field}", f"Kernel ELF report field {field} must be {expected}")
    return None


def _entry_issue(report: dict[str, object]) -> KernelLoadabilityIssue | None:
    if not _nonzero_hex_string(report.get("entry_address")):
        return _issue("missing_entry", "kernel_loadability.entry_address", "Kernel ELF report must record a non-zero entry address")
    if not _nonzero_hex_string(report.get("entry_symbol_address")):
        return _issue("missing_entry", "kernel_loadability.entry_symbol_address", "Kernel ELF report must record a non-zero _start address")
    if report.get("entry_symbol_matches_entry") is not True:
        return _issue("invalid_entry", "kernel_loadability.entry_symbol_matches_entry", "Kernel ELF _start symbol must match the ELF entry point")
    return None


def _program_header_issue(report: dict[str, object]) -> KernelLoadabilityIssue | None:
    if not _positive_int(report.get("program_header_count")):
        return _issue("missing_program_headers", "kernel_loadability.program_header_count", "Kernel ELF must have program headers")
    if not _positive_int(report.get("section_count")):
        return _issue("missing_sections", "kernel_loadability.section_count", "Kernel ELF report must record section count")
    return None


def _load_segment_issue(report: dict[str, object]) -> KernelLoadabilityIssue | None:
    segments = report.get("load_segments")
    if not isinstance(segments, list) or not segments:
        return _issue("missing_load_segments", "kernel_loadability.load_segments", "Kernel ELF must have at least one PT_LOAD segment")
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict) or segment.get("type") != "PT_LOAD":
            return _issue("invalid_load_segment", f"kernel_loadability.load_segments.{index}", "Kernel ELF load segments must be PT_LOAD records")
    return None


def _load_layout_issue(report: dict[str, object]) -> KernelLoadabilityIssue | None:
    minimum_vaddr = report.get("minimum_load_virtual_address")
    if not _nonzero_hex_string(minimum_vaddr):
        return _issue(
            "missing_load_layout",
            "kernel_loadability.minimum_load_virtual_address",
            "Kernel ELF report must record the minimum PT_LOAD virtual address",
        )
    if not isinstance(report.get("has_lower_half_load_segment"), bool):
        return _issue(
            "missing_load_layout",
            "kernel_loadability.has_lower_half_load_segment",
            "Kernel ELF report must record whether PT_LOAD segments are lower-half",
        )
    if not isinstance(report.get("entry_is_lower_half"), bool):
        return _issue(
            "missing_load_layout",
            "kernel_loadability.entry_is_lower_half",
            "Kernel ELF report must record whether the entry point is lower-half",
        )
    expected_blocker = "limine_lower_half_phdr" if report.get("has_lower_half_load_segment") is True else "none"
    if report.get("load_layout_blocker") != expected_blocker:
        return _issue(
            "load_layout_mismatch",
            "kernel_loadability.load_layout_blocker",
            "Kernel ELF load-layout blocker must match lower-half PT_LOAD detection",
        )
    return None


def _blocker_category_issue(report: dict[str, object]) -> KernelLoadabilityIssue | None:
    issues = report.get("detected_issues")
    blocker = report.get("blocker_category")
    if not isinstance(issues, list):
        return _issue("field_mismatch", "kernel_loadability.detected_issues", "Kernel ELF report must record detected issues")
    layout_blocker = report.get("load_layout_blocker")
    if layout_blocker == "limine_lower_half_phdr" and "limine_lower_half_phdr" not in issues:
        return _issue(
            "load_layout_mismatch",
            "kernel_loadability.detected_issues",
            "Kernel ELF report must include limine_lower_half_phdr when lower-half PT_LOAD segments are detected",
        )
    if issues and blocker not in _ISSUE_BLOCKERS:
        return _issue("blocker_mismatch", "kernel_loadability.blocker_category", "Kernel ELF report blocker must match detected ELF issues")
    if not issues and blocker != "none":
        return _issue("blocker_mismatch", "kernel_loadability.blocker_category", "Kernel ELF report must use blocker_category none when no ELF issues were detected")
    return None


def _blocker_report_issue(report: dict[str, object], blocker_report: dict[str, object]) -> KernelLoadabilityIssue | None:
    report_blocker = report.get("blocker_category")
    boot_blocker = blocker_report.get("blocker_category")
    external_blockers = {"missing_iso_generation_tooling", "missing_qemu_tooling", "missing_boot_image", "qemu_launch_failed"}
    if report_blocker in _ISSUE_BLOCKERS and boot_blocker in external_blockers:
        return None
    if report_blocker in _ISSUE_BLOCKERS and boot_blocker != report_blocker:
        return _issue("blocker_mismatch", "boot_blocker.blocker_category", "Boot blocker report must narrow to the kernel ELF issue when the ELF report detects one")
    if report_blocker == "none" and boot_blocker not in {"kernel_not_loaded", "missing_iso_generation_tooling"}:
        return _issue("blocker_mismatch", "boot_blocker.blocker_category", "Boot blocker report must preserve the external load blocker when the kernel ELF itself is structurally loadable")
    return None


def _list_contract_issue(
    report: dict[str, object],
    field: str,
    required_values: tuple[str, ...],
    reason: str,
) -> KernelLoadabilityIssue | None:
    values = report.get(field)
    if not isinstance(values, list):
        return _issue(reason, f"kernel_loadability.{field}", f"Kernel ELF report field {field} must be a list")
    for required in required_values:
        if required not in values:
            return _issue(reason, f"kernel_loadability.{field}.{required}", f"Kernel ELF report field {field} is missing {required}")
    return None


def _nonzero_hex_string(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("0x"):
        return False
    try:
        return int(value, 16) != 0
    except ValueError:
        return False


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and value > 0


def _first_issue(*issues: KernelLoadabilityIssue | None) -> KernelLoadabilityIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> KernelLoadabilityIssue:
    return KernelLoadabilityIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: KernelLoadabilityIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=KERNEL_LOADABILITY_INVALID,
        detail=issue.detail,
        action="Run scripts/build_boot_image.sh and keep kernel ELF loadability evidence aligned with the boot blocker report",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
