from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.codes import BOOT_IMAGE_PACKAGING_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_METADATA_PATH = _ROOT / "artifacts" / "runtime" / "boot_image" / "package_metadata.json"
_BOOT_BLOCKER_REPORT_PATH = _ROOT / "artifacts" / "runtime" / "boot_blocker_report.json"
_BOOT_DOC_PATH = _ROOT / "docs" / "BOOT.md"
_BOOT_IMAGE_DOC_PATH = _ROOT / "docs" / "BOOT_IMAGE.md"
_BOOT_BLOCKERS_PATH = _ROOT / "docs" / "BOOT_BLOCKERS.md"
_RUNTIME_EVIDENCE_PATH = _ROOT / "docs" / "RUNTIME_EVIDENCE.md"
_RELEASE_EVIDENCE_PATH = _ROOT / "docs" / "RELEASE_EVIDENCE.md"
_IMAGE_PATH = _ROOT / "artifacts" / "runtime" / "boot_image" / "kozo.iso"

_COMMON_FIELDS = {
    "phase": "v0.3.6",
    "image_type": "iso",
    "boot_protocol": "Limine",
    "architecture": "x86_64",
    "image_path": "artifacts/runtime/boot_image/kozo.iso",
    "generated_by": "scripts/build_boot_image.sh",
}

_BLOCKED_FIELDS = {
    "outcome": "blocked",
    "blocker_category": "missing_iso_generation_tooling",
    "image_exists": False,
}

_PACKAGED_FIELDS = {
    "outcome": "packaged",
    "blocker_category": "missing_qemu_serial_evidence",
    "image_exists": True,
}

_REQUIRED_BLOCKED_COMPONENTS = (
    "Limine executable",
    "xorriso executable",
    "Limine bootloader artifacts",
)

_REQUIRED_NON_GOALS = (
    "QEMU boot",
    "serial output",
    "hardware trap execution",
    "Linux compatibility",
    "POSIX compatibility",
    "userspace execution",
    "process model behavior",
    "VFS behavior",
    "scheduler maturity",
    "ELF loading",
    "file descriptor behavior",
    "production readiness",
)

_REQUIRED_DOC_REFERENCES = (
    "artifacts/runtime/boot_image/package_metadata.json",
    "artifacts/runtime/boot_image/kozo.iso",
    "missing_iso_generation_tooling",
)


@dataclass(frozen=True)
class BootImagePackagingIssue:
    reason: str
    contract_field: str
    detail: str


class BootImagePackagingValidator(BaseValidator):
    name = "boot_image_packaging"
    subsystem = "boot_image_packaging"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _boot_image_packaging_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Boot image packaging metadata records ISO generation status without claiming boot success",
        )


def _boot_image_packaging_issue() -> BootImagePackagingIssue | None:
    metadata_issue, metadata = _load_json(_METADATA_PATH, "boot_image_packaging.metadata")
    if metadata_issue is not None:
        return metadata_issue

    blocker_issue, blocker_report = _load_json(_BOOT_BLOCKER_REPORT_PATH, "boot_blocker.report")
    if blocker_issue is not None:
        return blocker_issue

    return _first_issue(
        _metadata_contract_issue(metadata),
        _image_state_issue(metadata),
        _blocked_component_issue(metadata),
        _list_contract_issue(metadata, "does_not_prove", _REQUIRED_NON_GOALS, "missing_non_goal"),
        _blocker_state_issue(metadata, blocker_report),
        _documentation_issue(),
    )


def _load_json(path: Path, contract_field: str) -> tuple[BootImagePackagingIssue | None, dict[str, object]]:
    if not path.is_file():
        return _issue("missing_file", contract_field, f"Missing boot image packaging file: {path}"), {}
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError:
        return _issue("invalid_json", contract_field, f"Boot image packaging file is not valid JSON: {path}"), {}
    if not isinstance(value, dict):
        return _issue("invalid_json", contract_field, f"Boot image packaging file must be a JSON object: {path}"), {}
    return None, value


def _metadata_contract_issue(metadata: dict[str, object]) -> BootImagePackagingIssue | None:
    for field, expected in _COMMON_FIELDS.items():
        if metadata.get(field) != expected:
            return _issue("field_mismatch", f"boot_image_packaging.{field}", f"Boot image packaging field {field} must be {expected}")
    expected_fields = _expected_outcome_fields(metadata)
    if expected_fields is None:
        return _issue("field_mismatch", "boot_image_packaging.outcome", "Boot image packaging outcome must be blocked or packaged")
    for field, expected in expected_fields.items():
        if metadata.get(field) != expected:
            return _issue("field_mismatch", f"boot_image_packaging.{field}", f"Boot image packaging field {field} must be {expected}")
    return None


def _expected_outcome_fields(metadata: dict[str, object]) -> dict[str, object] | None:
    if metadata.get("outcome") == "blocked":
        return _BLOCKED_FIELDS
    if metadata.get("outcome") == "packaged":
        return _PACKAGED_FIELDS
    return None


def _image_state_issue(metadata: dict[str, object]) -> BootImagePackagingIssue | None:
    if metadata.get("outcome") == "packaged" and not _IMAGE_PATH.is_file():
        return _issue("missing_image", "boot_image_packaging.image_path", "Boot image metadata claims packaging succeeded but kozo.iso is missing")
    if _IMAGE_PATH.is_file() and metadata.get("outcome") == "blocked":
        return _issue("blocker_state_mismatch", "boot_image_packaging.outcome", "Boot image exists but metadata still reports blocked packaging")
    return None


def _blocked_component_issue(metadata: dict[str, object]) -> BootImagePackagingIssue | None:
    if metadata.get("outcome") != "blocked":
        return None
    return _list_contract_issue(metadata, "missing_components", _REQUIRED_BLOCKED_COMPONENTS, "missing_component")


def _list_contract_issue(
    metadata: dict[str, object],
    field: str,
    required_values: tuple[str, ...],
    reason: str,
) -> BootImagePackagingIssue | None:
    values = metadata.get(field)
    if not isinstance(values, list):
        return _issue(reason, f"boot_image_packaging.{field}", f"Boot image packaging field {field} must be a list")
    for required in required_values:
        if required not in values:
            return _issue(reason, f"boot_image_packaging.{field}.{required}", f"Boot image packaging field {field} is missing {required}")
    return None


def _blocker_state_issue(metadata: dict[str, object], blocker_report: dict[str, object]) -> BootImagePackagingIssue | None:
    if blocker_report.get("phase") != "v0.3.6":
        return _issue("blocker_state_mismatch", "boot_blocker.phase", "Boot blocker report must be updated for v0.3.6")
    if blocker_report.get("blocker_category") != metadata.get("blocker_category"):
        return _issue("blocker_state_mismatch", "boot_blocker.blocker_category", "Boot blocker must match boot image packaging metadata")
    return None


def _documentation_issue() -> BootImagePackagingIssue | None:
    for path in (_BOOT_DOC_PATH, _BOOT_IMAGE_DOC_PATH, _BOOT_BLOCKERS_PATH, _RUNTIME_EVIDENCE_PATH, _RELEASE_EVIDENCE_PATH):
        if not path.is_file():
            return _issue("missing_documentation", _contract_field(path), f"Missing boot image packaging documentation: {path}")
        text = path.read_text()
        for reference in _REQUIRED_DOC_REFERENCES:
            if reference not in text:
                return _issue("missing_documentation_reference", f"{_contract_field(path)}.{reference}", f"Boot image packaging documentation is missing {reference}")
    return None


def _contract_field(path: Path) -> str:
    try:
        return str(path.relative_to(_ROOT))
    except ValueError:
        return "/".join(path.parts[-2:])


def _first_issue(*issues: BootImagePackagingIssue | None) -> BootImagePackagingIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> BootImagePackagingIssue:
    return BootImagePackagingIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: BootImagePackagingIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=BOOT_IMAGE_PACKAGING_INVALID,
        detail=issue.detail,
        action="Run scripts/build_boot_image.sh and keep boot image packaging docs, metadata, and blocker state aligned",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
