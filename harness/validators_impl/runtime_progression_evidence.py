from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import runtime_progression_entry_contract as contract_module
from harness.abi_manifest import ROOT
from harness.codes import OK, RUNTIME_PROGRESSION_EVIDENCE_INVALID
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_BOOT_SOURCE_PATH = ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_RUNTIME_SOURCE_PATH = ROOT / "kernel" / "runtime_progression.odin"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_LOG_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"
_STAGES_PATH = ROOT / "contracts" / "runtime_progression_stages.v0.json"
_TOOLING_BLOCKERS = {
    "missing_iso_generation_tooling",
    "missing_qemu_tooling",
    "missing_boot_image",
    "qemu_launch_failed",
}
_REQUIRED_SYMBOLS = (
    "runtime_progression_entry",
    "runtime_bootstrap_context",
    "runtime_progression_state",
    "runtime_serial_write_init_marker",
)


@dataclass(frozen=True)
class RuntimeProgressionEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class RuntimeProgressionContext:
    contract: contract_module.RuntimeProgressionEntryContract
    boot_lines: tuple[str, ...]
    runtime_lines: tuple[str, ...]


class RuntimeProgressionEvidenceValidator(BaseValidator):
    name = "runtime_progression_evidence"
    subsystem = "runtime_progression_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _runtime_progression_evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Runtime progression evidence aligns the bounded assembly-to-Odin call with symbols, markers, stages, and halt",
        )


def _runtime_progression_evidence_issue() -> RuntimeProgressionEvidenceIssue | None:
    context = _load_context()
    if isinstance(context, RuntimeProgressionEvidenceIssue):
        return context
    return _first_issue(
        _assembly_boundary_issue(context),
        _bootstrap_context_issue(context),
        _odin_boundary_issue(context),
        _binary_symbol_issue(),
        _stage_status_issue(),
        _qemu_evidence_issue(),
    )


def _load_context() -> RuntimeProgressionContext | RuntimeProgressionEvidenceIssue:
    contract = _load_contract()
    if isinstance(contract, RuntimeProgressionEvidenceIssue):
        return contract
    boot = _load_source(_BOOT_SOURCE_PATH, "progression_entry.source_file")
    if isinstance(boot, RuntimeProgressionEvidenceIssue):
        return boot
    runtime = _load_source(_RUNTIME_SOURCE_PATH, "runtime_initialization.source_file")
    if isinstance(runtime, RuntimeProgressionEvidenceIssue):
        return runtime
    return RuntimeProgressionContext(contract, tuple(_normalized_lines(boot)), tuple(_normalized_lines(runtime)))


def _load_contract():
    try:
        return contract_module.load_runtime_progression_entry_contract(_CONTRACT_PATH)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Runtime progression contract is invalid JSON: {exc}")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Runtime progression contract is unavailable or malformed: {exc}")


def _load_source(path: Path, field: str) -> str | RuntimeProgressionEvidenceIssue:
    if path.is_file():
        return path.read_text()
    return _issue("missing_source", field, f"Runtime progression source is missing: {path}")


def _assembly_boundary_issue(context: RuntimeProgressionContext) -> RuntimeProgressionEvidenceIssue | None:
    entry = context.contract.progression_entry
    boundary = context.contract.return_boundary
    expected = (
        "WRITE_COM1_MARKER memory_init_marker, memory_init_marker_end",
        "test rsp, 0x0f",
        "jnz .halt",
        f"lea rdi, [rel {context.contract.bootstrap_context.symbol}]",
        f"WRITE_COM1_MARKER runtime_progress_entry_marker, runtime_progress_entry_marker_end",
        f"call {entry.target_symbol}",
        f"cmp eax, {boundary.required_status}",
        "jne .halt",
        "WRITE_COM1_MARKER runtime_return_marker, runtime_return_marker_end",
        "cli",
        ".halt:",
        "hlt",
        "jmp .halt",
    )
    return _ordered_issue(context.boot_lines, expected, "assembly_boundary_mismatch", "progression_entry")


def _bootstrap_context_issue(context: RuntimeProgressionContext) -> RuntimeProgressionEvidenceIssue | None:
    contract = context.contract.bootstrap_context
    expected = (
        f"{contract.symbol}:",
        f"dq {contract.version}",
        f"dq {contract.size_bytes}",
        "dq boot_stack",
        "dq boot_stack_top",
        "dq boot_memory_region",
        "dq boot_memory_region_end",
        "dq 0",
        "dq 0",
    )
    return _ordered_issue(context.boot_lines, expected, "invalid_context_layout", "bootstrap_context.fields")


def _odin_boundary_issue(context: RuntimeProgressionContext) -> RuntimeProgressionEvidenceIssue | None:
    return _first_issue(
        _entry_signature_issue(context),
        _marker_ownership_issue(context),
        _runtime_entry_flow_issue(context.runtime_lines),
        _context_validation_issue(context.runtime_lines),
        _runtime_state_issue(context),
    )


def _entry_signature_issue(context: RuntimeProgressionContext) -> RuntimeProgressionEvidenceIssue | None:
    symbol = context.contract.runtime_initialization.entry_symbol
    signature = f'{symbol} :: proc "c" (bootstrap: ^Runtime_Bootstrap_Context) -> u32 {{'
    index = _line_index(context.runtime_lines, signature)
    if index is not None and index > 0 and context.runtime_lines[index - 1] == "@(export)":
        return None
    if any(line.startswith(f"{symbol} ::") for line in context.runtime_lines):
        return _issue("wrong_entry_signature", "runtime_initialization.entry_symbol", "Odin runtime entry must use the governed exported C signature")
    return _issue("missing_entry_symbol", "runtime_initialization.entry_symbol", "Odin runtime entry symbol is missing")


def _context_validation_issue(lines: tuple[str, ...]) -> RuntimeProgressionEvidenceIssue | None:
    required = (
        "if bootstrap == nil {",
        "return bootstrap.version == RUNTIME_BOOTSTRAP_VERSION &&",
        "bootstrap.structure_size == RUNTIME_BOOTSTRAP_SIZE &&",
        "bootstrap.flags == 0 &&",
        "bootstrap.reserved == 0",
        "runtime_stack_range_is_valid(bootstrap) &&",
        "runtime_memory_range_is_valid(bootstrap)",
    )
    for line in required:
        issue = _required_line_issue(lines, line, "missing_context_validation", "bootstrap_context.validation")
        if issue is not None:
            return issue
    return None


def _runtime_entry_flow_issue(lines: tuple[str, ...]) -> RuntimeProgressionEvidenceIssue | None:
    expected = (
        "if !runtime_bootstrap_context_is_valid(bootstrap) {",
        "return RUNTIME_PROGRESSION_INVALID_CONTEXT",
        "if !runtime_state_probe_succeeds() {",
        "return RUNTIME_PROGRESSION_STATE_FAILURE",
        "runtime_emit_init_marker()",
        "return RUNTIME_PROGRESSION_OK",
    )
    return _ordered_issue(lines, expected, "runtime_entry_flow_mismatch", "runtime_initialization.success_path")


def _runtime_state_issue(context: RuntimeProgressionContext) -> RuntimeProgressionEvidenceIssue | None:
    expected = (
        'import "base:intrinsics"',
        "intrinsics.volatile_store(&runtime_progression_state, RUNTIME_STATE_SENTINEL)",
        "observed := intrinsics.volatile_load(&runtime_progression_state)",
        "intrinsics.volatile_store(&runtime_progression_state, 0)",
        "restored := intrinsics.volatile_load(&runtime_progression_state)",
        "return observed == RUNTIME_STATE_SENTINEL && restored == 0",
    )
    return _ordered_issue(context.runtime_lines, expected, "runtime_state_probe_missing", "runtime_initialization.operation")


def _marker_ownership_issue(context: RuntimeProgressionContext) -> RuntimeProgressionEvidenceIssue | None:
    return _first_issue(
        _required_line_issue(context.runtime_lines, "runtime_emit_init_marker()", "runtime_marker_not_owned_by_odin", "runtime_initialization.marker_emission_owner"),
        _ordered_issue(
            context.boot_lines,
            ("runtime_serial_write_init_marker:", "WRITE_COM1_MARKER runtime_init_marker, runtime_init_marker_end", "ret"),
            "runtime_marker_not_owned_by_odin",
            "runtime_initialization.serial_bridge_symbol",
        ),
    )


def _binary_symbol_issue() -> RuntimeProgressionEvidenceIssue | None:
    report = _load_json(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, RuntimeProgressionEvidenceIssue):
        return report
    symbols = report.get("runtime_progression_symbols")
    if not isinstance(symbols, dict):
        return _issue("binary_symbol_missing", "kernel_elf_report.runtime_progression_symbols", "Kernel ELF report must record runtime progression symbols")
    for symbol in _REQUIRED_SYMBOLS:
        record = symbols.get(symbol)
        if not isinstance(record, dict) or record.get("present") is not True or not record.get("address"):
            return _issue("binary_symbol_missing", f"kernel_elf_report.runtime_progression_symbols.{symbol}", f"Kernel ELF is missing progression symbol: {symbol}")
    return None


def _stage_status_issue() -> RuntimeProgressionEvidenceIssue | None:
    document = _load_json(_STAGES_PATH, "runtime_progression_stages")
    if isinstance(document, RuntimeProgressionEvidenceIssue):
        return document
    statuses = {stage.get("stage_name"): stage.get("status") for stage in document.get("stages", []) if isinstance(stage, dict)}
    expected = {
        "MEMORY_INITIALIZATION_EVIDENCE": "proven",
        "RUNTIME_PROGRESSION_ENTRY": "proven",
        "RUNTIME_INITIALIZATION_EVIDENCE": "proven",
        "CONTROLLED_RUNTIME_LOOP": "planned",
    }
    for stage, status in expected.items():
        if statuses.get(stage) != status:
            return _issue("stage_status_mismatch", f"runtime_progression_stages.{stage}.status", f"Expected {stage} status {status}")
    return None


def _qemu_evidence_issue() -> RuntimeProgressionEvidenceIssue | None:
    metadata = _load_json(_METADATA_PATH, "qemu_smoke.metadata")
    if isinstance(metadata, RuntimeProgressionEvidenceIssue):
        return metadata
    if metadata.get("outcome") == "blocked" and metadata.get("blocker_category") in _TOOLING_BLOCKERS:
        return None
    if metadata.get("outcome") != "pass":
        return _issue("runtime_evidence_missing", "qemu_smoke.outcome", "Runtime progression requires passing QEMU evidence or an allowed local tooling blocker")
    return _passing_qemu_issue(metadata)


def _passing_qemu_issue(metadata: dict[str, object]) -> RuntimeProgressionEvidenceIssue | None:
    markers = get_smoke_marker_order()
    if metadata.get("expected_marker") != get_expected_smoke_marker():
        return _issue("metadata_log_mismatch", "qemu_smoke.expected_marker", "QEMU expected marker must match runtime taxonomy")
    if metadata.get("observed_markers") != list(markers):
        return _issue("metadata_log_mismatch", "qemu_smoke.observed_markers", "QEMU metadata must contain the complete runtime progression sequence")
    if not _SERIAL_LOG_PATH.is_file() or not _ordered_markers_present(_SERIAL_LOG_PATH.read_text(errors="replace"), markers):
        return _issue("metadata_log_mismatch", "qemu_smoke.serial_log", "QEMU serial log must contain the ordered runtime progression sequence")
    return None


def _load_json(path: Path, field: str) -> dict[str, object] | RuntimeProgressionEvidenceIssue:
    if not path.is_file():
        return _issue("missing_evidence", field, f"Required runtime progression evidence is missing: {path}")
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return _issue("invalid_evidence", field, f"Runtime progression evidence is invalid JSON: {exc}")
    if not isinstance(value, dict):
        return _issue("invalid_evidence", field, "Runtime progression evidence must be a JSON object")
    return value


def _normalized_lines(source: str) -> list[str]:
    lines = []
    for raw_line in source.splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if line:
            lines.append(" ".join(line.split()))
    return lines


def _ordered_issue(lines, expected, reason: str, field: str) -> RuntimeProgressionEvidenceIssue | None:
    position = -1
    for item in expected:
        position = _line_index(lines, item, position + 1)
        if position is None:
            return _issue(reason, field, f"Runtime progression path is missing ordered operation: {item}")
    return None


def _required_line_issue(lines, expected: str, reason: str, field: str) -> RuntimeProgressionEvidenceIssue | None:
    if _line_index(lines, expected) is not None:
        return None
    return _issue(reason, field, f"Runtime progression source must contain: {expected}")


def _line_index(lines, expected: str, start: int = 0) -> int | None:
    for index in range(start, len(lines)):
        if lines[index] == expected:
            return index
    return None


def _ordered_markers_present(text: str, markers: tuple[str, ...]) -> bool:
    position = -1
    for marker in markers:
        position = text.find(marker, position + 1)
        if position < 0:
            return False
    return True


def _first_issue(*issues: RuntimeProgressionEvidenceIssue | None) -> RuntimeProgressionEvidenceIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, field: str, detail: str) -> RuntimeProgressionEvidenceIssue:
    return RuntimeProgressionEvidenceIssue(reason, field, detail)


def _failure(issue: RuntimeProgressionEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_PROGRESSION_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Keep runtime progression source, ELF symbols, QEMU evidence, stage status, and terminal halt aligned",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
