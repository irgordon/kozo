from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness.codes import BOOT_PROTOCOL_DECISION_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_ADR_PATH = _ROOT / "docs" / "decisions" / "0001-boot-protocol.md"
_BOOT_PROTOCOL_PATH = _ROOT / "docs" / "BOOT_PROTOCOL.md"
_BOOT_DOC_PATH = _ROOT / "docs" / "BOOT.md"
_BOOT_BLOCKERS_PATH = _ROOT / "docs" / "BOOT_BLOCKERS.md"
_PHASEMAP_PATH = _ROOT / "PHASEMAP.md"
_ROADMAP_PATH = _ROOT / "ROADMAP.md"


@dataclass(frozen=True)
class RequiredText:
    name: str
    source_path: Path
    needle: str
    detail: str


@dataclass(frozen=True)
class BootProtocolIssue:
    reason: str
    contract_field: str
    detail: str


class BootProtocolDecisionValidator(BaseValidator):
    name = "boot_protocol_decision"
    subsystem = "boot_protocol_decision"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _boot_protocol_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Boot protocol decision selects Limine and stays aligned with the current boot blocker state",
        )


def _boot_protocol_issue() -> BootProtocolIssue | None:
    missing_file_issue = _missing_file_issue(_required_paths())
    if missing_file_issue is not None:
        return missing_file_issue
    return _required_text_issue(_required_texts())


def _required_paths() -> tuple[Path, ...]:
    return (
        _ADR_PATH,
        _BOOT_PROTOCOL_PATH,
        _BOOT_DOC_PATH,
        _BOOT_BLOCKERS_PATH,
        _PHASEMAP_PATH,
        _ROADMAP_PATH,
    )


def _required_texts() -> tuple[RequiredText, ...]:
    return (
        RequiredText("adr_status", _ADR_PATH, "Status: Accepted", "ADR must be accepted"),
        RequiredText("selected_protocol", _ADR_PATH, "Selected protocol: Limine", "ADR must select Limine"),
        RequiredText("target_architecture", _ADR_PATH, "Target architecture: x86_64", "ADR must name x86_64"),
        RequiredText("initial_boot_target", _ADR_PATH, "Initial boot target: QEMU serial smoke", "ADR must name QEMU serial smoke as target"),
        RequiredText("limine_alternative", _ADR_PATH, "## Limine", "ADR must discuss Limine"),
        RequiredText("multiboot2_alternative", _ADR_PATH, "## Multiboot2", "ADR must discuss Multiboot2"),
        RequiredText("uefi_first_alternative", _ADR_PATH, "## UEFI-first", "ADR must discuss UEFI-first"),
        RequiredText("raw_loader_alternative", _ADR_PATH, "## Raw custom loader", "ADR must discuss raw custom loader"),
        RequiredText("qemu_non_goal", _ADR_PATH, "This decision does not claim QEMU boot.", "ADR must preserve QEMU non-goal"),
        RequiredText("linux_non_goal", _ADR_PATH, "This decision does not claim Linux compatibility.", "ADR must preserve Linux non-goal"),
        RequiredText("production_non_goal", _ADR_PATH, "This decision does not claim production readiness.", "ADR must preserve production non-goal"),
        RequiredText("boot_protocol_doc_selects_limine", _BOOT_PROTOCOL_PATH, "Selected protocol: Limine", "Boot protocol doc must select Limine"),
        RequiredText("boot_protocol_doc_next_phase", _BOOT_PROTOCOL_PATH, "v0.3.2 Boot Image Skeleton", "Boot protocol doc must name next phase"),
        RequiredText("boot_doc_references_protocol", _BOOT_DOC_PATH, "Selected boot protocol: Limine", "Boot doc must reference selected protocol"),
        RequiredText("boot_doc_remaining_blocker", _BOOT_DOC_PATH, "Remaining blocker: `missing_qemu_execution_evidence`.", "Boot doc must name remaining blocker"),
        RequiredText("boot_blockers_decision_complete", _BOOT_BLOCKERS_PATH, "Boot protocol decision: complete.", "Boot blockers doc must record decision completion"),
        RequiredText("boot_blockers_reduced", _BOOT_BLOCKERS_PATH, "The previous `missing_boot_protocol_and_image_packaging` blocker is reduced.", "Boot blockers doc must record reduced blocker"),
        RequiredText("phasemap_next_phase", _PHASEMAP_PATH, "v0.3.2", "Phase map must include v0.3.2"),
        RequiredText("phasemap_boot_image_skeleton", _PHASEMAP_PATH, "Boot Image Skeleton", "Phase map must include Boot Image Skeleton"),
        RequiredText("roadmap_next_phase", _ROADMAP_PATH, "v0.3.2", "Roadmap must include v0.3.2"),
        RequiredText("roadmap_qemu_serial_smoke", _ROADMAP_PATH, "QEMU serial smoke", "Roadmap must include QEMU serial smoke path"),
    )


def _missing_file_issue(paths: tuple[Path, ...]) -> BootProtocolIssue | None:
    for path in paths:
        if not path.is_file():
            return _issue("missing_document", _contract_field(path), f"Missing boot protocol document: {path}")
    return None


def _required_text_issue(required_texts: tuple[RequiredText, ...]) -> BootProtocolIssue | None:
    for required in required_texts:
        text = required.source_path.read_text()
        if required.needle not in text:
            return _issue(f"missing_{required.name}", _contract_field(required.source_path, required.name), required.detail)
    return None


def _contract_field(path: Path, name: str | None = None) -> str:
    try:
        field = str(path.relative_to(_ROOT))
    except ValueError:
        field = _fallback_contract_path(path)
    if name is None:
        return field
    return f"{field}.{name}"


def _fallback_contract_path(path: Path) -> str:
    parts = path.parts
    if "docs" in parts:
        return "/".join(parts[parts.index("docs"):])
    return path.name


def _issue(reason: str, contract_field: str, detail: str) -> BootProtocolIssue:
    return BootProtocolIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: BootProtocolIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=BOOT_PROTOCOL_DECISION_INVALID,
        detail=issue.detail,
        action="Keep docs/decisions/0001-boot-protocol.md, docs/BOOT_PROTOCOL.md, boot docs, PHASEMAP.md, and ROADMAP.md aligned",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
