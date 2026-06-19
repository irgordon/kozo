from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.codes import BOOT_IMAGE_SKELETON_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_LINKER_PATH = _ROOT / "linker" / "kernel.ld"
_LIMINE_CONFIG_PATH = _ROOT / "boot" / "limine.conf"
_BUILD_SCRIPT_PATH = _ROOT / "scripts" / "build_boot_image.sh"
_MEMORY_ASM_PATH = _ROOT / "kernel" / "arch" / "x86_64" / "memory.asm"
_BOOT_IMAGE_DOC_PATH = _ROOT / "docs" / "BOOT_IMAGE.md"
_BOOT_DOC_PATH = _ROOT / "docs" / "BOOT.md"
_BOOT_BLOCKERS_PATH = _ROOT / "docs" / "BOOT_BLOCKERS.md"
_BOOT_BLOCKER_REPORT_PATH = _ROOT / "artifacts" / "runtime" / "boot_blocker_report.json"
_ALLOWED_BLOCKERS = (
    "missing_iso_generation_tooling",
    "missing_qemu_serial_evidence",
    "missing_qemu_tooling",
    "missing_boot_image",
    "missing_serial_marker",
    "qemu_launch_failed",
    "qemu_timeout",
    "limine_load_failed",
    "kernel_entry_not_reached",
)


@dataclass(frozen=True)
class RequiredText:
    name: str
    source_path: Path
    needle: str
    detail: str


@dataclass(frozen=True)
class BootImageIssue:
    reason: str
    contract_field: str
    detail: str


class BootImageSkeletonValidator(BaseValidator):
    name = "boot_image_skeleton"
    subsystem = "boot_image_skeleton"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _boot_image_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Boot image skeleton has linker, Limine config, build script, docs, and matching blocker state",
        )


def _boot_image_issue() -> BootImageIssue | None:
    missing = _missing_file_issue(_required_paths())
    if missing is not None:
        return missing
    return _first_issue(
        _required_text_issue(_required_texts()),
        _blocker_report_issue(),
    )


def _required_paths() -> tuple[Path, ...]:
    return (
        _LINKER_PATH,
        _LIMINE_CONFIG_PATH,
        _BUILD_SCRIPT_PATH,
        _MEMORY_ASM_PATH,
        _BOOT_IMAGE_DOC_PATH,
        _BOOT_DOC_PATH,
        _BOOT_BLOCKERS_PATH,
        _BOOT_BLOCKER_REPORT_PATH,
    )


def _required_texts() -> tuple[RequiredText, ...]:
    return (
        RequiredText("entry_symbol", _LINKER_PATH, "ENTRY(_start)", "Linker script must define _start as entry"),
        RequiredText("text_section", _LINKER_PATH, ".text", "Linker script must define text layout"),
        RequiredText("rodata_section", _LINKER_PATH, ".rodata", "Linker script must define rodata layout"),
        RequiredText("data_section", _LINKER_PATH, ".data", "Linker script must define data layout"),
        RequiredText("bss_section", _LINKER_PATH, ".bss", "Linker script must define bss layout"),
        RequiredText("limine_protocol", _LIMINE_CONFIG_PATH, "PROTOCOL=limine", "Limine config must select Limine protocol"),
        RequiredText("kernel_path", _LIMINE_CONFIG_PATH, "KERNEL_PATH=boot:///boot/kozo/kozo-kernel.elf", "Limine config must name staged kernel ELF"),
        RequiredText("build_script_linker", _BUILD_SCRIPT_PATH, "linker/kernel.ld", "Build script must use the linker script"),
        RequiredText("build_script_limine", _BUILD_SCRIPT_PATH, "boot/limine.conf", "Build script must stage Limine config"),
        RequiredText("build_script_output", _BUILD_SCRIPT_PATH, "artifacts/runtime/boot_image", "Build script must use documented output path"),
        RequiredText("memory_memset", _MEMORY_ASM_PATH, "global memset", "Memory support must provide memset"),
        RequiredText("memory_memmove", _MEMORY_ASM_PATH, "global memmove", "Memory support must provide memmove"),
        RequiredText("doc_no_boot_claim", _BOOT_IMAGE_DOC_PATH, "This phase does not prove boot success.", "Boot image doc must avoid boot claim"),
        RequiredText("doc_no_qemu_claim", _BOOT_IMAGE_DOC_PATH, "This phase does not prove QEMU execution.", "Boot image doc must avoid QEMU claim"),
        RequiredText("doc_output_path", _BOOT_IMAGE_DOC_PATH, "artifacts/runtime/boot_image/", "Boot image doc must name output path"),
        RequiredText("boot_doc_remaining_blocker", _BOOT_DOC_PATH, "Remaining blocker: `missing_iso_generation_tooling`.", "Boot doc must name remaining blocker"),
        RequiredText("blockers_doc_remaining_blocker", _BOOT_BLOCKERS_PATH, "The remaining blocker is `missing_iso_generation_tooling`.", "Boot blockers doc must name remaining blocker"),
    )


def _missing_file_issue(paths: tuple[Path, ...]) -> BootImageIssue | None:
    for path in paths:
        if not path.is_file():
            return _issue("missing_file", _contract_field(path), f"Missing boot image skeleton file: {path}")
    return None


def _required_text_issue(required_texts: tuple[RequiredText, ...]) -> BootImageIssue | None:
    for required in required_texts:
        if required.needle not in required.source_path.read_text():
            return _issue(f"missing_{required.name}", _contract_field(required.source_path, required.name), required.detail)
    return None


def _blocker_report_issue() -> BootImageIssue | None:
    try:
        report = json.loads(_BOOT_BLOCKER_REPORT_PATH.read_text())
    except json.JSONDecodeError:
        return _issue("invalid_blocker_report_json", _contract_field(_BOOT_BLOCKER_REPORT_PATH), "Boot blocker report must be valid JSON")
    if report.get("blocker_category") not in _ALLOWED_BLOCKERS:
        return _issue("blocker_state_mismatch", "boot_blocker.blocker_category", "Boot blocker must be narrowed to ISO tooling or QEMU serial evidence")
    missing_components = report.get("missing_components")
    if not isinstance(missing_components, list) or _required_missing_component(report) not in missing_components:
        return _issue("blocker_state_mismatch", "boot_blocker.missing_components", "Boot blocker must name the remaining required component")
    return None


def _required_missing_component(report: dict[str, object]) -> str:
    if report.get("blocker_category") != "missing_iso_generation_tooling":
        return "validated QEMU serial smoke execution"
    return "Limine executable"


def _contract_field(path: Path, name: str | None = None) -> str:
    try:
        field = str(path.relative_to(_ROOT))
    except ValueError:
        field = "/".join(path.parts[-2:])
    if name is None:
        return field
    return f"{field}.{name}"


def _first_issue(*issues: BootImageIssue | None) -> BootImageIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> BootImageIssue:
    return BootImageIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: BootImageIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=BOOT_IMAGE_SKELETON_INVALID,
        detail=issue.detail,
        action="Keep linker/kernel.ld, boot/limine.conf, scripts/build_boot_image.sh, docs/BOOT_IMAGE.md, and boot blocker state aligned",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
