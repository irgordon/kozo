from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Pattern

from harness.codes import BRIDGE_ALIGNMENT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_SYSCALL_ASM = _ROOT / "kernel" / "arch" / "x86_64" / "syscall.asm"
_MAIN_ODIN = _ROOT / "kernel" / "main.odin"

_LABEL_PATTERN = re.compile(r"^(?P<label>[A-Za-z_.$][\w.$]*):\s*$")


@dataclass(frozen=True)
class OrderedAssemblyAnchor:
    name: str
    pattern: Pattern[str]
    detail: str


@dataclass(frozen=True)
class AssemblySymbolContract:
    name: str
    pattern: Pattern[str]
    detail: str


@dataclass(frozen=True)
class DispatcherContract:
    name: str
    pattern: Pattern[str]
    detail: str


_SYMBOL_CONTRACTS = (
    AssemblySymbolContract(
        "extern_dispatcher_symbol",
        re.compile(r"^extern\s+syscall_dispatch\s*$", re.MULTILINE),
        "syscall.asm must declare extern syscall_dispatch",
    ),
    AssemblySymbolContract(
        "global_syscall_entry_symbol",
        re.compile(r"^global\s+syscall_entry\s*$", re.MULTILINE),
        "syscall.asm must export global syscall_entry",
    ),
)

_DISPATCHER_CONTRACT = DispatcherContract(
    "odin_dispatcher_signature",
    re.compile(
        r'@\(export\)\s*syscall_dispatch\s*::\s*proc\s*"c"\s*'
        r"\(\s*id:\s*abi\.K_SYSCALL_ID,\s*"
        r"payload:\s*\^abi\.Heartbeat_Payload,\s*\)\s*->\s*abi\.K_STATUS",
        re.DOTALL,
    ),
    'kernel/main.odin must export proc "c" syscall_dispatch(id, payload) -> abi.K_STATUS',
)

_ORDERED_BRIDGE_ANCHORS = (
    OrderedAssemblyAnchor(
        "preserve_rbx",
        re.compile(r"\bpush\s+rbx\b"),
        "syscall_entry must preserve rbx",
    ),
    OrderedAssemblyAnchor(
        "preserve_r11",
        re.compile(r"\bpush\s+r11\b"),
        "syscall_entry must preserve r11",
    ),
    OrderedAssemblyAnchor(
        "preserve_rcx",
        re.compile(r"\bpush\s+rcx\b"),
        "syscall_entry must preserve rcx",
    ),
    OrderedAssemblyAnchor(
        "align_stack",
        re.compile(r"\bsub\s+rsp,\s*8\b"),
        "syscall_entry must align rsp before the dispatcher call",
    ),
    OrderedAssemblyAnchor(
        "capture_syscall_id",
        re.compile(r"\bmov\s+rax,\s*rdi\b"),
        "syscall_entry must capture the C ABI id from rdi into rax",
    ),
    OrderedAssemblyAnchor(
        "capture_payload",
        re.compile(r"\bmov\s+rbx,\s*rsi\b"),
        "syscall_entry must capture the C ABI payload pointer from rsi into rbx",
    ),
    OrderedAssemblyAnchor(
        "dispatch_id_argument",
        re.compile(r"\bmov\s+rdi,\s*rax\b"),
        "syscall_entry must pass the trap id from rax into dispatcher argument rdi",
    ),
    OrderedAssemblyAnchor(
        "dispatch_payload_argument",
        re.compile(r"\bmov\s+rsi,\s*rbx\b"),
        "syscall_entry must pass the payload pointer from rbx into dispatcher argument rsi",
    ),
    OrderedAssemblyAnchor(
        "dispatcher_handoff",
        re.compile(r"\bcall\s+syscall_dispatch\b"),
        "syscall_entry must call syscall_dispatch from the live entry block",
    ),
    OrderedAssemblyAnchor(
        "restore_stack",
        re.compile(r"\badd\s+rsp,\s*8\b"),
        "syscall_entry must restore rsp after dispatcher return",
    ),
    OrderedAssemblyAnchor(
        "restore_rcx",
        re.compile(r"\bpop\s+rcx\b"),
        "syscall_entry must restore rcx",
    ),
    OrderedAssemblyAnchor(
        "restore_r11",
        re.compile(r"\bpop\s+r11\b"),
        "syscall_entry must restore r11",
    ),
    OrderedAssemblyAnchor(
        "restore_rbx",
        re.compile(r"\bpop\s+rbx\b"),
        "syscall_entry must restore rbx",
    ),
    OrderedAssemblyAnchor(
        "return_to_caller",
        re.compile(r"\bret\b"),
        "syscall_entry must return to the caller after dispatcher return",
    ),
)


def _missing_symbol_contract(source: str) -> AssemblySymbolContract | None:
    for contract in _SYMBOL_CONTRACTS:
        if contract.pattern.search(source) is None:
            return contract
    return None


def _extract_entry_block(source: str, label_name: str) -> str | None:
    lines = source.splitlines()
    start = _label_line_index(lines, label_name)
    if start < 0:
        return None
    end = _next_label_line_index(lines, start)
    return "\n".join(lines[start:end])


def _label_line_index(lines: list[str], label_name: str) -> int:
    for index, line in enumerate(lines):
        match = _LABEL_PATTERN.match(line.strip())
        if match is not None and match.group("label") == label_name:
            return index
    return -1


def _next_label_line_index(lines: list[str], start: int) -> int:
    for index in range(start + 1, len(lines)):
        if _is_global_label(lines[index]):
            return index
    return len(lines)


def _is_global_label(line: str) -> bool:
    match = _LABEL_PATTERN.match(line.strip())
    return match is not None and not match.group("label").startswith(".")


def _dispatcher_contract_result(source: str) -> ValidationResult | None:
    if _DISPATCHER_CONTRACT.pattern.search(source) is not None:
        return None
    return _failure_result(
        "missing_odin_dispatcher_contract",
        _DISPATCHER_CONTRACT.name,
        _DISPATCHER_CONTRACT.detail,
    )


def _symbol_contract_result(source: str) -> ValidationResult | None:
    missing = _missing_symbol_contract(source)
    if missing is None:
        return None
    return _failure_result("missing_assembly_symbol", missing.name, missing.detail)


def _entry_block_result(source: str) -> tuple[str | None, ValidationResult | None]:
    block = _extract_entry_block(source, "syscall_entry")
    if block is not None:
        return block, None
    return None, _failure_result(
        "missing_entry_block",
        "syscall_entry_block",
        "syscall.asm must define the live syscall_entry block",
    )


def _ordered_anchor_result(block: str, source: str) -> ValidationResult | None:
    cursor = 0
    for anchor in _ORDERED_BRIDGE_ANCHORS:
        match = anchor.pattern.search(block, cursor)
        if match is None:
            return _assembly_anchor_failure(block, source, cursor, anchor)
        cursor = match.end()
    return None


def _assembly_anchor_failure(
    block: str,
    source: str,
    cursor: int,
    anchor: OrderedAssemblyAnchor,
) -> ValidationResult:
    if anchor.pattern.search(block) is not None:
        return _failure_result("out_of_order_assembly_anchor", anchor.name, anchor.detail)
    if anchor.pattern.search(source) is not None:
        return _failure_result("dead_snippet_outside_entry_block", anchor.name, anchor.detail)
    return _failure_result("missing_assembly_anchor", anchor.name, anchor.detail)


def _failure_result(reason: str, contract_field: str, detail: str) -> ValidationResult:
    return ValidationResult.fail(
        code=BRIDGE_ALIGNMENT_INVALID,
        detail=f"Bridge alignment invalid: {reason}: {contract_field}: {detail}",
        action="Keep the live syscall_entry block aligned with the exported Odin dispatcher contract",
        meta={"reason": reason, "contract_field": contract_field},
    )


class BridgeAlignmentValidator(BaseValidator):
    name = "bridge_alignment"
    subsystem = "bridge_alignment"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        asm_source = _SYSCALL_ASM.read_text()
        odin_source = _MAIN_ODIN.read_text()

        entry_block, entry_result = _entry_block_result(asm_source)
        for result in (
            _dispatcher_contract_result(odin_source),
            _symbol_contract_result(asm_source),
            entry_result,
            _ordered_anchor_result(entry_block, asm_source) if entry_block is not None else None,
        ):
            if result is not None:
                return result

        return ValidationResult.pass_(
            code=OK,
            detail="Live syscall_entry block and exported Odin dispatcher signature align with the trap-path contract",
        )
