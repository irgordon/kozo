from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import memory_initialization_evidence_contract
from harness.abi_manifest import ROOT
from harness.codes import MEMORY_INITIALIZATION_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = memory_initialization_evidence_contract.CONTRACT_PATH
_BOOT_ASM_PATH = ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_LOG_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"
_MEMORY_MARKER = "KOZO_MEMORY_INIT_OK"
_TOOLING_BLOCKERS = (
    "missing_iso_generation_tooling",
    "missing_qemu_tooling",
    "missing_boot_image",
    "qemu_launch_failed",
)


@dataclass(frozen=True)
class MemoryInitializationEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class MemoryEvidenceContext:
    contract: memory_initialization_evidence_contract.MemoryInitializationEvidenceContract
    source_text: str
    lines: tuple[str, ...]


class MemoryInitializationEvidenceValidator(BaseValidator):
    name = "memory_initialization_evidence"
    subsystem = "memory_initialization_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _memory_initialization_evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Memory initialization evidence matches the controlled region, probe, marker, and halt path",
        )


def _memory_initialization_evidence_issue() -> MemoryInitializationEvidenceIssue | None:
    context = _load_context()
    if isinstance(context, MemoryInitializationEvidenceIssue):
        return context
    return _first_issue(
        _contract_state_issue(context.contract),
        _region_issue(context),
        _binary_region_issue(context.contract),
        _initialization_issue(context),
        _probe_issue(context),
        _marker_and_halt_issue(context),
        _qemu_evidence_issue(),
    )


def _load_context() -> MemoryEvidenceContext | MemoryInitializationEvidenceIssue:
    contract = _load_contract()
    if isinstance(contract, MemoryInitializationEvidenceIssue):
        return contract
    source = _load_source(contract)
    if isinstance(source, MemoryInitializationEvidenceIssue):
        return source
    return MemoryEvidenceContext(contract, source, tuple(_normalized_lines(source)))


def _load_contract():
    try:
        return memory_initialization_evidence_contract.load_memory_initialization_evidence_contract(_CONTRACT_PATH)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Memory evidence contract is invalid JSON: {exc}")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Memory evidence contract is unavailable or malformed: {exc}")


def _load_source(contract) -> str | MemoryInitializationEvidenceIssue:
    source_path = memory_initialization_evidence_contract.contract_repo_path(contract.controlled_region.source_file)
    if not source_path.is_file():
        return _issue("missing_boot_source", "controlled_region.source_file", f"Memory evidence source is missing: {source_path}")
    return source_path.read_text()


def _contract_state_issue(contract) -> MemoryInitializationEvidenceIssue | None:
    marker = contract.marker_placement
    if contract.current_state.implemented is not True:
        return _issue("contract_mismatch", "current_state.implemented", "Memory evidence contract must record the implemented path")
    if marker.marker_status != "emitted" or marker.marker_emitted is not True:
        return _issue("contract_mismatch", "marker_placement.marker_emitted", "Memory evidence contract must record emitted marker status")
    if marker.reserved_marker != _MEMORY_MARKER:
        return _issue("contract_mismatch", "marker_placement.reserved_marker", "Memory evidence contract must identify KOZO_MEMORY_INIT_OK")
    return None


def _region_issue(context: MemoryEvidenceContext) -> MemoryInitializationEvidenceIssue | None:
    region = context.contract.controlled_region
    return _first_issue(
        _required_line_issue(context.lines, f"global {region.start_symbol}", "missing_region_symbol", "controlled_region.start_symbol"),
        _required_line_issue(context.lines, f"global {region.end_symbol}", "missing_region_symbol", "controlled_region.end_symbol"),
        _region_sequence_issue(context),
        _stack_overlap_issue(context),
    )


def _region_sequence_issue(context: MemoryEvidenceContext) -> MemoryInitializationEvidenceIssue | None:
    region = context.contract.controlled_region
    expected = (
        f"align {region.alignment_bytes}",
        f"{region.start_symbol}:",
        f"resb {region.size_bytes}",
        f"{region.end_symbol}:",
    )
    return _ordered_sequence_issue(context.lines, expected, "invalid_region_geometry", "controlled_region")


def _stack_overlap_issue(context: MemoryEvidenceContext) -> MemoryInitializationEvidenceIssue | None:
    stack_end = _line_index(context.lines, "boot_stack_top:")
    region_start = _line_index(context.lines, f"{context.contract.controlled_region.start_symbol}:")
    if stack_end is not None and region_start is not None and stack_end < region_start:
        return None
    return _issue("region_overlap", "controlled_region.owner", "Controlled memory region must follow and remain separate from the boot stack")


def _binary_region_issue(contract) -> MemoryInitializationEvidenceIssue | None:
    report = _load_json_object(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, MemoryInitializationEvidenceIssue):
        return report
    region = report.get("memory_evidence_region")
    if not isinstance(region, dict):
        return _issue("binary_region_mismatch", "controlled_region", "Kernel ELF report must record the governed memory region")
    return _binary_region_geometry_issue(contract.controlled_region, region)


def _binary_region_geometry_issue(contract_region, report_region) -> MemoryInitializationEvidenceIssue | None:
    start = _hex_address(report_region.get("start_address"))
    end = _hex_address(report_region.get("end_address"))
    if _binary_region_fields_match(contract_region, report_region, start, end):
        return None
    return _issue("binary_region_mismatch", "controlled_region", "Kernel ELF memory-region symbols must match governed size and alignment")


def _binary_region_fields_match(contract_region, report_region, start, end) -> bool:
    if start is None or end is None:
        return False
    return all((
        report_region.get("start_symbol") == contract_region.start_symbol,
        report_region.get("end_symbol") == contract_region.end_symbol,
        end - start == contract_region.size_bytes,
        report_region.get("size_bytes") == contract_region.size_bytes,
        report_region.get("required_alignment_bytes") == contract_region.alignment_bytes,
        report_region.get("start_aligned") is True,
        start % contract_region.alignment_bytes == 0,
    ))


def _initialization_issue(context: MemoryEvidenceContext) -> MemoryInitializationEvidenceIssue | None:
    region = context.contract.controlled_region
    operation = context.contract.initialization_operation
    count = region.size_bytes // operation.width_bytes
    expected = (
        "WRITE_COM1_MARKER stack_init_marker, stack_init_marker_end",
        "cld",
        f"lea rdi, [rel {region.start_symbol}]",
        "xor eax, eax",
        f"mov ecx, {count}",
        "rep stosq",
    )
    return _ordered_sequence_issue(context.lines, expected, "partial_zero_fill", "initialization_operation.coverage")


def _probe_issue(context: MemoryEvidenceContext) -> MemoryInitializationEvidenceIssue | None:
    probe = context.contract.survival_probe
    symbol = _probe_symbol(context)
    expected = (
        f"cmp qword [rel {symbol}], 0",
        "jne .halt",
        f"mov rax, {probe.sentinel_value}",
        f"mov qword [rel {symbol}], rax",
        f"mov rdx, qword [rel {symbol}]",
        "cmp rdx, rax",
        "sete r8b",
        f"mov qword [rel {symbol}], 0",
        "test r8b, r8b",
        "jz .halt",
        f"cmp qword [rel {symbol}], 0",
        "jne .halt",
    )
    return _ordered_sequence_issue(context.lines, expected, "invalid_probe_sequence", "survival_probe.required_steps")


def _probe_symbol(context: MemoryEvidenceContext) -> str:
    region = context.contract.controlled_region
    offset = context.contract.survival_probe.offset_bytes
    return region.start_symbol if offset == 0 else f"{region.start_symbol} + {offset}"


def _marker_and_halt_issue(context: MemoryEvidenceContext) -> MemoryInitializationEvidenceIssue | None:
    marker = context.contract.marker_placement
    definition_issue = _marker_definition_issue(context.source_text, marker.reserved_marker)
    if definition_issue is not None:
        return definition_issue
    early_halt_issue = _halt_before_marker_issue(context.lines)
    if early_halt_issue is not None:
        return early_halt_issue
    issue = _ordered_sequence_issue(context.lines, _marker_halt_sequence(context), "marker_order_mismatch", "marker_placement")
    if issue is not None:
        return issue
    return _fallthrough_issue(context.lines)


def _marker_halt_sequence(context: MemoryEvidenceContext) -> tuple[str, ...]:
    return (
        "WRITE_COM1_MARKER stack_init_marker, stack_init_marker_end",
        "rep stosq",
        "cmp rdx, rax",
        f"mov qword [rel {context.contract.controlled_region.start_symbol}], 0",
        f"WRITE_COM1_MARKER memory_init_marker, memory_init_marker_end",
        "cli",
        ".halt:",
        "hlt",
        "jmp .halt",
    )


def _halt_before_marker_issue(lines: tuple[str, ...]) -> MemoryInitializationEvidenceIssue | None:
    marker = _line_index(lines, "WRITE_COM1_MARKER memory_init_marker, memory_init_marker_end")
    halt = _line_index(lines, "hlt")
    if marker is not None and (halt is None or marker < halt):
        return None
    return _issue("halt_before_marker", "marker_placement.required_before", "Memory evidence marker must precede halt execution")


def _marker_definition_issue(source: str, marker: str) -> MemoryInitializationEvidenceIssue | None:
    if "memory_init_marker:" not in source or f'db "{marker}", 13, 10' not in source:
        return _issue("missing_marker", "marker_placement.reserved_marker", "Runtime source must define KOZO_MEMORY_INIT_OK")
    return None


def _fallthrough_issue(lines: tuple[str, ...]) -> MemoryInitializationEvidenceIssue | None:
    jump = _line_index(lines, "jmp .halt")
    if jump is None:
        return _issue("fallthrough_after_marker", "marker_placement.required_before", "Memory evidence path must end in the halt loop back edge")
    for line in lines[jump + 1:]:
        if not line.endswith(":"):
            return _issue("fallthrough_after_marker", "marker_placement.required_before", "Executable fallthrough after the memory evidence halt loop is forbidden")
    return None


def _qemu_evidence_issue() -> MemoryInitializationEvidenceIssue | None:
    metadata = _load_metadata()
    if isinstance(metadata, MemoryInitializationEvidenceIssue):
        return metadata
    if metadata.get("outcome") == "blocked" and metadata.get("blocker_category") in _TOOLING_BLOCKERS:
        return None
    if metadata.get("outcome") != "pass":
        return _issue("missing_marker", "qemu_smoke.outcome", "Memory evidence requires passing QEMU evidence or an allowed local tooling blocker")
    return _passing_qemu_issue(metadata)


def _load_metadata() -> dict[str, object] | MemoryInitializationEvidenceIssue:
    return _load_json_object(_METADATA_PATH, "qemu_smoke.metadata")


def _load_json_object(path: Path, contract_field: str) -> dict[str, object] | MemoryInitializationEvidenceIssue:
    if not path.is_file():
        return _issue("missing_metadata", contract_field, f"Required evidence JSON is missing: {path}")
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return _issue("invalid_metadata", contract_field, f"Required evidence JSON is invalid: {exc}")
    if not isinstance(value, dict):
        return _issue("invalid_metadata", contract_field, "Required evidence JSON must be an object")
    return value


def _passing_qemu_issue(metadata: dict[str, object]) -> MemoryInitializationEvidenceIssue | None:
    markers = get_smoke_marker_order()
    if metadata.get("expected_marker") != get_expected_smoke_marker() or metadata.get("observed_markers") != list(markers):
        return _issue("qemu_evidence_mismatch", "qemu_smoke.observed_markers", "QEMU metadata must contain the governed memory marker sequence")
    if not _SERIAL_LOG_PATH.is_file():
        return _issue("missing_marker", "qemu_smoke.serial_log", "QEMU serial log is missing")
    if _ordered_markers_present(_SERIAL_LOG_PATH.read_text(errors="replace"), markers):
        return None
    return _issue("marker_order_mismatch", "qemu_smoke.serial_log", "QEMU serial log must contain the ordered memory evidence sequence")


def _normalized_lines(source: str) -> list[str]:
    lines = []
    for raw_line in source.splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if line:
            lines.append(" ".join(line.split()))
    return lines


def _ordered_sequence_issue(lines, expected, reason, field) -> MemoryInitializationEvidenceIssue | None:
    position = -1
    for item in expected:
        position = _line_index(lines, item, position + 1)
        if position is None:
            return _issue(reason, field, f"Memory evidence source is missing ordered operation: {item}")
    return None


def _required_line_issue(lines, expected, reason, field) -> MemoryInitializationEvidenceIssue | None:
    if _line_index(lines, expected) is not None:
        return None
    return _issue(reason, field, f"Memory evidence source must contain: {expected}")


def _line_index(lines, expected: str, start: int = 0) -> int | None:
    for index in range(start, len(lines)):
        if lines[index] == expected:
            return index
    return None


def _hex_address(value: object) -> int | None:
    if not isinstance(value, str) or not value.startswith("0x"):
        return None
    try:
        return int(value, 16)
    except ValueError:
        return None


def _ordered_markers_present(text: str, markers: tuple[str, ...]) -> bool:
    position = -1
    for marker in markers:
        position = text.find(marker, position + 1)
        if position < 0:
            return False
    return True


def _first_issue(*issues: MemoryInitializationEvidenceIssue | None) -> MemoryInitializationEvidenceIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> MemoryInitializationEvidenceIssue:
    return MemoryInitializationEvidenceIssue(reason, contract_field, detail)


def _failure(issue: MemoryInitializationEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=MEMORY_INITIALIZATION_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Keep memory initialization evidence aligned with the governed static-region runtime path",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
