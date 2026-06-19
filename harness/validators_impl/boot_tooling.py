from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.codes import BOOT_TOOLING_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_BOOT_TOOLING_PATH = _ROOT / "docs" / "BOOT_TOOLING.md"
_BOOT_DOC_PATH = _ROOT / "docs" / "BOOT.md"
_BOOT_IMAGE_PATH = _ROOT / "docs" / "BOOT_IMAGE.md"
_BOOT_BLOCKERS_PATH = _ROOT / "docs" / "BOOT_BLOCKERS.md"
_RUNTIME_EVIDENCE_PATH = _ROOT / "docs" / "RUNTIME_EVIDENCE.md"
_RELEASE_EVIDENCE_PATH = _ROOT / "docs" / "RELEASE_EVIDENCE.md"
_CI_WORKFLOW_PATH = _ROOT / ".github" / "workflows" / "ci.yml"
_BUILD_SCRIPT_PATH = _ROOT / "scripts" / "build_boot_image.sh"
_REPORT_PATH = _ROOT / "artifacts" / "runtime" / "boot_blocker_report.json"


@dataclass(frozen=True)
class RequiredText:
    name: str
    source_path: Path
    needle: str
    detail: str


@dataclass(frozen=True)
class BootToolingIssue:
    reason: str
    contract_field: str
    detail: str


class BootToolingValidator(BaseValidator):
    name = "boot_tooling"
    subsystem = "boot_tooling"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _boot_tooling_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Boot tooling policy documents Limine and xorriso acquisition without claiming boot success",
        )


def _boot_tooling_issue() -> BootToolingIssue | None:
    missing = _missing_file_issue(_required_paths())
    if missing is not None:
        return missing
    return _first_issue(
        _required_text_issue(_required_texts()),
        _blocker_report_issue(),
    )


def _required_paths() -> tuple[Path, ...]:
    return (
        _BOOT_TOOLING_PATH,
        _BOOT_DOC_PATH,
        _BOOT_IMAGE_PATH,
        _BOOT_BLOCKERS_PATH,
        _RUNTIME_EVIDENCE_PATH,
        _RELEASE_EVIDENCE_PATH,
        _CI_WORKFLOW_PATH,
        _BUILD_SCRIPT_PATH,
        _REPORT_PATH,
    )


def _required_texts() -> tuple[RequiredText, ...]:
    return (
        RequiredText("limine_doc", _BOOT_TOOLING_PATH, "Limine purpose:", "Boot tooling doc must document Limine"),
        RequiredText("xorriso_doc", _BOOT_TOOLING_PATH, "xorriso purpose:", "Boot tooling doc must document xorriso"),
        RequiredText("local_install_path", _BOOT_TOOLING_PATH, "Local development path:", "Boot tooling doc must document local installation"),
        RequiredText("ci_install_path", _BOOT_TOOLING_PATH, "CI installation path:", "Boot tooling doc must document CI installation"),
        RequiredText("limine_pin", _BOOT_TOOLING_PATH, "v12.3.3", "Boot tooling doc must name pinned Limine version"),
        RequiredText("limine_checksum", _BOOT_TOOLING_PATH, "9e97c9fedc714daa5d7fd2b66a32d85df6bcbf3452657fd26bebad7c8b423009", "Boot tooling doc must name pinned Limine checksum"),
        RequiredText("ci_limine_source", _BOOT_TOOLING_PATH, "Download Limine v12.3.3 from the upstream GitHub release source tarball.", "Boot tooling doc must document CI Limine source acquisition"),
        RequiredText("ci_xorriso_install", _BOOT_TOOLING_PATH, "Install xorriso through apt.", "Boot tooling doc must document CI xorriso installation"),
        RequiredText("provenance", _BOOT_TOOLING_PATH, "Tool Provenance", "Boot tooling doc must document provenance"),
        RequiredText("no_opaque_binaries", _BOOT_TOOLING_PATH, "Opaque vendored binaries are discouraged.", "Boot tooling doc must discourage opaque vendored binaries"),
        RequiredText("future_iso_path", _BOOT_TOOLING_PATH, "artifacts/runtime/boot_image/kozo.iso", "Boot tooling doc must name expected ISO path"),
        RequiredText("current_blocker", _BOOT_TOOLING_PATH, "missing_iso_generation_tooling", "Boot tooling doc must name current blocker"),
        RequiredText("workflow_limine_pin", _CI_WORKFLOW_PATH, "LIMINE_VERSION: v12.3.3", "CI workflow must pin Limine version"),
        RequiredText("workflow_limine_checksum", _CI_WORKFLOW_PATH, "LIMINE_TARBALL_SHA256: 9e97c9fedc714daa5d7fd2b66a32d85df6bcbf3452657fd26bebad7c8b423009", "CI workflow must verify Limine checksum"),
        RequiredText("workflow_xorriso_install", _CI_WORKFLOW_PATH, "xorriso", "CI workflow must install xorriso"),
        RequiredText("workflow_build_boot_image", _CI_WORKFLOW_PATH, "scripts/build_boot_image.sh", "CI workflow must run boot image build script"),
        RequiredText("workflow_upload_iso", _CI_WORKFLOW_PATH, "artifacts/runtime/boot_image/kozo.iso", "CI workflow must upload boot ISO when produced"),
        RequiredText("build_script_limine_dir", _BUILD_SCRIPT_PATH, "${LIMINE_DIR:-}", "Build script must support explicit Limine directory"),
        RequiredText("build_script_limine_install", _BUILD_SCRIPT_PATH, "${LIMINE_INSTALL:-}", "Build script must support explicit Limine install directory"),
        RequiredText("build_script_limine_path", _BUILD_SCRIPT_PATH, "${LIMINE:-}", "Build script must support explicit Limine executable"),
        RequiredText("build_script_xorriso_path", _BUILD_SCRIPT_PATH, "${XORRISO:-}", "Build script must support explicit xorriso executable"),
        RequiredText("boot_doc_tooling", _BOOT_DOC_PATH, "docs/BOOT_TOOLING.md", "Boot doc must reference boot tooling doc"),
        RequiredText("boot_doc_blocker", _BOOT_DOC_PATH, "missing_iso_generation_tooling", "Boot doc must name current blocker"),
        RequiredText("image_doc_tooling", _BOOT_IMAGE_PATH, "docs/BOOT_TOOLING.md", "Boot image doc must reference boot tooling doc"),
        RequiredText("blockers_doc_tooling", _BOOT_BLOCKERS_PATH, "docs/BOOT_TOOLING.md", "Boot blockers doc must reference boot tooling doc"),
        RequiredText("runtime_doc_tooling", _RUNTIME_EVIDENCE_PATH, "docs/BOOT_TOOLING.md", "Runtime evidence doc must reference boot tooling doc"),
        RequiredText("release_doc_tooling", _RELEASE_EVIDENCE_PATH, "docs/BOOT_TOOLING.md", "Release evidence doc must reference boot tooling doc"),
    )


def _missing_file_issue(paths: tuple[Path, ...]) -> BootToolingIssue | None:
    for path in paths:
        if not path.is_file():
            return _issue("missing_document", _contract_field(path), f"Missing boot tooling file: {path}")
    return None


def _required_text_issue(required_texts: tuple[RequiredText, ...]) -> BootToolingIssue | None:
    for required in required_texts:
        if required.needle not in required.source_path.read_text():
            return _issue(f"missing_{required.name}", _contract_field(required.source_path, required.name), required.detail)
    return None


def _blocker_report_issue() -> BootToolingIssue | None:
    try:
        report = json.loads(_REPORT_PATH.read_text())
    except json.JSONDecodeError:
        return _issue("invalid_report_json", _contract_field(_REPORT_PATH), "Boot blocker report must be valid JSON")
    if report.get("blocker_category") != "missing_iso_generation_tooling":
        return _issue("blocker_mismatch", "boot_blocker.blocker_category", "Boot blocker must be narrowed to missing_iso_generation_tooling")
    return None


def _contract_field(path: Path, name: str | None = None) -> str:
    try:
        field = str(path.relative_to(_ROOT))
    except ValueError:
        field = "/".join(path.parts[-2:])
    if name is None:
        return field
    return f"{field}.{name}"


def _first_issue(*issues: BootToolingIssue | None) -> BootToolingIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> BootToolingIssue:
    return BootToolingIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: BootToolingIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=BOOT_TOOLING_INVALID,
        detail=issue.detail,
        action="Keep docs/BOOT_TOOLING.md, boot docs, and boot blocker state aligned",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
