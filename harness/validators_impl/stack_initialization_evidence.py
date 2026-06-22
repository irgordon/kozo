from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import stack_initialization_evidence_contract
from harness.abi_manifest import ROOT
from harness.codes import OK, STACK_INITIALIZATION_EVIDENCE_INVALID
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validator import BaseValidator, ValidationResult

_BOOT_ASM_PATH = ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_CONTRACT_PATH = stack_initialization_evidence_contract.CONTRACT_PATH
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_LOG_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"
_STACK_MARKER = "KOZO_STACK_INIT_OK"
_BOOT_MARKER = "KOZO_BOOT_SMOKE_OK"
_TOOLING_BLOCKERS = (
    "missing_iso_generation_tooling",
    "missing_qemu_tooling",
    "missing_boot_image",
    "qemu_launch_failed",
)


@dataclass(frozen=True)
class StackInitializationEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


class StackInitializationEvidenceValidator(BaseValidator):
    name = "stack_initialization_evidence"
    subsystem = "stack_initialization_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _stack_initialization_evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Stack initialization evidence is aligned with the controlled boot stack marker path",
        )


def _stack_initialization_evidence_issue() -> StackInitializationEvidenceIssue | None:
    contract = _load_contract()
    if isinstance(contract, StackInitializationEvidenceIssue):
        return contract
    boot_source = _load_boot_source()
    if isinstance(boot_source, StackInitializationEvidenceIssue):
        return boot_source
    return _first_issue(
        _contract_marker_issue(contract),
        _stack_source_issue(contract, boot_source),
        _stack_order_issue(boot_source),
        _qemu_evidence_issue(),
    )


def _load_contract():
    try:
        return stack_initialization_evidence_contract.load_stack_initialization_evidence_contract(_CONTRACT_PATH)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Stack initialization evidence contract is invalid JSON: {exc}")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return _issue("contract_mismatch", "contract", f"Stack initialization evidence contract is unavailable or malformed: {exc}")


def _load_boot_source() -> str | StackInitializationEvidenceIssue:
    if not _BOOT_ASM_PATH.is_file():
        return _issue("missing_boot_source", "stack.source_file", f"Boot assembly source is missing: {_BOOT_ASM_PATH}")
    return _BOOT_ASM_PATH.read_text()


def _contract_marker_issue(contract) -> StackInitializationEvidenceIssue | None:
    definition = contract.stack_definition
    if definition.reserved_marker != _STACK_MARKER:
        return _issue("contract_mismatch", "stack_definition.reserved_marker", "Stack contract must identify KOZO_STACK_INIT_OK")
    if definition.marker_status != "emitted" or definition.marker_emitted is not True:
        return _issue("contract_mismatch", "stack_definition.marker_emitted", "Stack contract must mark KOZO_STACK_INIT_OK as emitted")
    return None


def _stack_source_issue(contract, boot_source: str) -> StackInitializationEvidenceIssue | None:
    definition = contract.stack_definition
    return _first_issue(
        _source_contains_issue(boot_source, f"{definition.stack_symbol}:", "missing_stack_region", "stack_definition.stack_symbol"),
        _source_contains_issue(boot_source, f"resb {definition.stack_size_bytes}", "wrong_stack_size", "stack_definition.stack_size_bytes"),
        _source_contains_issue(boot_source, f"{definition.stack_top_symbol}:", "missing_stack_top", "stack_definition.stack_top_symbol"),
        _source_contains_issue(boot_source, f"lea {definition.stack_pointer_register}, [rel {definition.stack_top_symbol}]", "missing_stack_pointer_setup", "stack_definition.stack_pointer_register"),
        _source_contains_issue(boot_source, "push rax", "missing_stack_use", "stack_definition.stack_pointer_register"),
        _source_contains_issue(boot_source, "pop rax", "missing_stack_use", "stack_definition.stack_pointer_register"),
        _source_contains_issue(boot_source, "stack_init_marker:", "missing_marker", "kernel.boot.asm.stack_init_marker"),
    )


def _stack_order_issue(boot_source: str) -> StackInitializationEvidenceIssue | None:
    boot_marker = boot_source.find("WRITE_COM1_MARKER boot_smoke_marker")
    stack_pointer = boot_source.find("lea rsp, [rel boot_stack_top]")
    stack_marker = boot_source.find("WRITE_COM1_MARKER stack_init_marker")
    halt = boot_source.find(".halt:")
    if min(boot_marker, stack_pointer, stack_marker, halt) < 0:
        return _issue("marker_order_mismatch", "kernel.boot.asm", "Stack evidence path must include boot marker, stack setup, stack marker, and halt")
    if not boot_marker < stack_pointer < stack_marker < halt:
        return _issue("marker_order_mismatch", "kernel.boot.asm", "Stack marker must follow boot smoke and stack setup before halt")
    return None


def _qemu_evidence_issue() -> StackInitializationEvidenceIssue | None:
    metadata = _load_metadata()
    if metadata is None:
        return None
    if isinstance(metadata, StackInitializationEvidenceIssue):
        return metadata
    if metadata.get("outcome") == "blocked" and metadata.get("blocker_category") in _TOOLING_BLOCKERS:
        return None
    if metadata.get("outcome") != "pass":
        return _issue("missing_marker", "qemu_smoke.outcome", "Stack initialization evidence requires passing QEMU smoke or a local tooling blocker")
    return _first_issue(
        _expected_marker_issue(metadata),
        _observed_marker_issue(metadata),
        _serial_marker_issue(metadata),
    )


def _load_metadata() -> dict[str, object] | StackInitializationEvidenceIssue | None:
    if not _METADATA_PATH.is_file():
        return None
    try:
        return json.loads(_METADATA_PATH.read_text())
    except json.JSONDecodeError as exc:
        return _issue("invalid_metadata", "qemu_smoke.metadata", f"QEMU smoke metadata is invalid JSON: {exc}")


def _expected_marker_issue(metadata: dict[str, object]) -> StackInitializationEvidenceIssue | None:
    if metadata.get("expected_marker") == get_expected_smoke_marker() == _STACK_MARKER:
        return None
    return _issue("contract_mismatch", "qemu_smoke.expected_marker", "QEMU smoke expected marker must be KOZO_STACK_INIT_OK")


def _observed_marker_issue(metadata: dict[str, object]) -> StackInitializationEvidenceIssue | None:
    observed = metadata.get("observed_markers")
    if observed == list(get_smoke_marker_order()):
        return None
    if isinstance(observed, list) and _STACK_MARKER not in observed:
        return _issue("missing_marker", "qemu_smoke.observed_markers", "QEMU smoke evidence must include KOZO_STACK_INIT_OK")
    return _issue("marker_order_mismatch", "qemu_smoke.observed_markers", "QEMU smoke evidence must preserve the governed stack marker order")


def _serial_marker_issue(metadata: dict[str, object]) -> StackInitializationEvidenceIssue | None:
    if not _SERIAL_LOG_PATH.is_file():
        return _issue("missing_marker", "qemu_smoke.serial_log", "QEMU serial log is missing for passing stack evidence")
    serial_text = _SERIAL_LOG_PATH.read_text(errors="replace")
    if _ordered_markers_present(serial_text, get_smoke_marker_order()):
        return None
    return _issue("marker_order_mismatch", "qemu_smoke.serial_log", "QEMU serial log must contain the ordered stack evidence sequence")


def _ordered_markers_present(text: str, markers: tuple[str, ...]) -> bool:
    position = -1
    for marker in markers:
        next_position = text.find(marker, position + 1)
        if next_position < 0:
            return False
        position = next_position
    return True


def _source_contains_issue(source: str, needle: str, reason: str, field: str) -> StackInitializationEvidenceIssue | None:
    if needle in source:
        return None
    return _issue(reason, field, f"Boot stack evidence source must contain: {needle}")


def _first_issue(*issues: StackInitializationEvidenceIssue | None) -> StackInitializationEvidenceIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> StackInitializationEvidenceIssue:
    return StackInitializationEvidenceIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: StackInitializationEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=STACK_INITIALIZATION_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Keep stack initialization evidence aligned with the controlled stack marker path",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
