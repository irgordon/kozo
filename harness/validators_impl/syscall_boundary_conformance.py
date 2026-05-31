from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from harness import syscall_boundary_contract
from harness.codes import OK, SYSCALL_BOUNDARY_CONFORMANCE_INVALID
from harness.registry import CHECKS
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_CONTRACT_PATH = syscall_boundary_contract.CONTRACT_PATH
_RUST_MAIN = _ROOT / "userspace" / "core_service" / "src" / "main.rs"
_ODIN_MAIN = _ROOT / "kernel" / "main.odin"
_LABEL_PATTERN = re.compile(r"^(?P<label>[A-Za-z_.$][\w.$]*):\s*$")


@dataclass(frozen=True)
class SourceBundle:
    assembly: str
    rust: str
    odin: str


@dataclass(frozen=True)
class ConformanceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class ConformanceContext:
    contract: syscall_boundary_contract.SyscallBoundaryContract
    sources: SourceBundle


@dataclass(frozen=True)
class TextAnchor:
    reason: str
    contract_field: str
    needle: str
    detail: str


class SyscallBoundaryConformanceValidator(BaseValidator):
    name = "syscall_boundary_conformance"
    subsystem = "syscall_boundary_conformance"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _conformance_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure_result(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Live sources conform to syscall boundary contract v0 for the heartbeat trap path",
        )


def _conformance_issue(contract_path: Path) -> ConformanceIssue | None:
    context = _load_conformance_context(contract_path)
    if isinstance(context, ConformanceIssue):
        return context
    return _first_issue(
        _assembly_conformance_issue(context),
        _rust_conformance_issue(context),
        _odin_conformance_issue(context),
        _proof_ownership_issue(context.contract),
    )


def _load_conformance_context(contract_path: Path) -> ConformanceContext | ConformanceIssue:
    contract = _load_contract(contract_path)
    if isinstance(contract, ConformanceIssue):
        return contract
    sources = _load_sources(contract)
    if isinstance(sources, ConformanceIssue):
        return sources
    return ConformanceContext(contract, sources)


def _load_contract(path: Path) -> syscall_boundary_contract.SyscallBoundaryContract | ConformanceIssue:
    try:
        return syscall_boundary_contract.load_syscall_boundary_contract(path)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return _issue("contract_unavailable", "contract", f"Syscall boundary contract could not be loaded: {exc}")


def _load_sources(
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> SourceBundle | ConformanceIssue:
    assembly_path = syscall_boundary_contract.contract_repo_path(contract.entry.assembly_path)
    if not assembly_path.is_file():
        return _issue("missing_assembly_path", "entry.assembly_path", f"Assembly path does not exist: {contract.entry.assembly_path}")
    try:
        return SourceBundle(
            assembly=assembly_path.read_text(),
            rust=_RUST_MAIN.read_text(),
            odin=_ODIN_MAIN.read_text(),
        )
    except OSError as exc:
        return _issue("source_unavailable", "source", f"Conformance source could not be read: {exc}")


def _assembly_conformance_issue(context: ConformanceContext) -> ConformanceIssue | None:
    block = _assembly_entry_block(context.sources.assembly, context.contract.entry.symbol)
    if block is None:
        return _issue("missing_assembly_entry_symbol", "entry.symbol", f"Assembly is missing entry block {context.contract.entry.symbol}")
    return _first_issue(
        _assembly_anchor_issue(block, _dispatcher_anchor(context.contract)),
        _assembly_anchor_issue(block, _syscall_id_capture_anchor(context.contract)),
        _assembly_anchor_issue(block, _syscall_id_handoff_anchor(context.contract)),
        _assembly_anchor_issue(block, _payload_capture_anchor(context.contract)),
        _assembly_anchor_issue(block, _payload_handoff_anchor(context.contract)),
        _return_register_issue(block, context.contract),
    )


def _rust_conformance_issue(context: ConformanceContext) -> ConformanceIssue | None:
    heartbeat_block = _rust_function_block(context.sources.rust, "heartbeat_request")
    return_path_block = _rust_function_block(context.sources.rust, "validate_heartbeat_return_path")
    return _first_issue(
        _rust_extern_issue(context.sources.rust, context.contract),
        _rust_bridge_call_issue(context.sources.rust, context.contract),
        _missing_block_issue(heartbeat_block, "rust_missing_heartbeat_path", "rust.heartbeat_request", "Rust heartbeat_request is missing"),
        _rust_heartbeat_issue(heartbeat_block or "", context.contract),
        _missing_block_issue(return_path_block, "rust_missing_return_validation", "rust.validate_heartbeat_return_path", "Rust return-path validation is missing"),
        _rust_return_validation_issue(return_path_block or "", context.contract),
    )


def _odin_conformance_issue(context: ConformanceContext) -> ConformanceIssue | None:
    dispatch_block = _odin_proc_block(context.sources.odin, context.contract.entry.dispatcher_symbol)
    heartbeat_branch = _odin_case_block(context.sources.odin, f"case abi.{context.contract.debug_heartbeat.constant}:")
    return _first_issue(
        _missing_block_issue(dispatch_block, "odin_dispatcher_symbol_mismatch", "entry.dispatcher_symbol", "Odin dispatcher proc is missing"),
        _odin_dispatcher_signature_issue(dispatch_block or "", context.contract),
        _missing_block_issue(heartbeat_branch, "odin_wrong_syscall_constant", "syscalls.debug_heartbeat.constant", "Odin heartbeat branch is missing"),
        _odin_heartbeat_issue(heartbeat_branch or "", context.contract),
    )


def _proof_ownership_issue(
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> ConformanceIssue | None:
    for entry in contract.proof_ownership:
        if entry.validator_name not in CHECKS:
            return _issue("unknown_proof_validator", f"proof_ownership.{entry.validator_name}", f"{entry.validator_name} is not a registered validator")
    return None


def _rust_heartbeat_issue(
    heartbeat_block: str,
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> ConformanceIssue | None:
    request = contract.debug_heartbeat.request
    return _first_issue(
        _text_anchor_issue(heartbeat_block, _rust_syscall_anchor(contract)),
        _text_anchor_issue(heartbeat_block, _rust_request_sequence_anchor(request.sequence)),
        _text_anchor_issue(heartbeat_block, _rust_request_timestamp_anchor(request.timestamp)),
        _text_anchor_issue(heartbeat_block, _rust_request_status_anchor(request.status_bits)),
    )


def _rust_return_validation_issue(
    return_path_block: str,
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> ConformanceIssue | None:
    response = contract.debug_heartbeat.response
    success = contract.debug_heartbeat.success_behavior.return_status
    return _first_issue(
        _text_anchor_issue(return_path_block, _rust_return_status_anchor(success)),
        _text_anchor_issue(return_path_block, _rust_response_sequence_anchor(response.sequence)),
        _text_anchor_issue(return_path_block, _rust_response_timestamp_anchor(response.timestamp)),
        _text_anchor_issue(return_path_block, _rust_response_status_anchor(response.status_bits)),
    )


def _odin_heartbeat_issue(
    heartbeat_branch: str,
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> ConformanceIssue | None:
    return _first_issue(
        _text_anchor_issue(heartbeat_branch, _odin_null_payload_anchor(contract.debug_heartbeat.invalid_behavior.null_payload)),
        _text_anchor_issue(heartbeat_branch, _odin_bad_sequence_anchor(contract)),
        _odin_mutation_set_issue(heartbeat_branch, contract),
        _text_anchor_issue(heartbeat_branch, _odin_response_sequence_anchor(contract.debug_heartbeat.response.sequence)),
        _text_anchor_issue(heartbeat_branch, _odin_response_timestamp_anchor(contract.debug_heartbeat.response.timestamp)),
        _text_anchor_issue(heartbeat_branch, _odin_response_status_anchor(contract.debug_heartbeat.response.status_bits)),
        _text_anchor_issue(heartbeat_branch, _odin_success_return_anchor(contract.debug_heartbeat.success_behavior.return_status)),
    )


def _rust_extern_issue(source: str, contract: syscall_boundary_contract.SyscallBoundaryContract) -> ConformanceIssue | None:
    pattern = re.compile(
        rf"fn\s+{re.escape(contract.entry.symbol)}\s*\(\s*id:\s*u64,\s*payload:\s*\*mut\s+abi::HeartbeatPayload\s*\)\s*->\s*u64\s*;"
    )
    if pattern.search(source) is not None:
        return None
    return _issue("rust_extern_symbol_mismatch", "entry.symbol", f"Rust extern declaration does not match {contract.entry.symbol}")


def _rust_bridge_call_issue(source: str, contract: syscall_boundary_contract.SyscallBoundaryContract) -> ConformanceIssue | None:
    needle = f"{contract.entry.symbol}(u64::from(syscall), payload as *mut abi::HeartbeatPayload)"
    if needle in source:
        return None
    return _issue("rust_bridge_call_mismatch", "calling_convention", "Rust bridge helper does not pass syscall id and payload pointer to the contract entry")


def _odin_dispatcher_signature_issue(
    dispatch_block: str,
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> ConformanceIssue | None:
    for anchor in (
        TextAnchor("odin_dispatcher_symbol_mismatch", "entry.dispatcher_symbol", f"{contract.entry.dispatcher_symbol} :: proc", "Odin dispatcher symbol does not match the contract"),
        TextAnchor("odin_dispatcher_symbol_mismatch", "calling_convention.syscall_id.type", "id: abi.K_SYSCALL_ID", "Odin dispatcher syscall id type does not match the contract"),
        TextAnchor("odin_dispatcher_symbol_mismatch", "calling_convention.payload.type", "payload: ^abi.Heartbeat_Payload", "Odin dispatcher payload type does not match the contract"),
        TextAnchor("odin_dispatcher_symbol_mismatch", "calling_convention.return.type", "-> abi.K_STATUS", "Odin dispatcher return type does not match the contract"),
    ):
        issue = _text_anchor_issue(dispatch_block, anchor)
        if issue is not None:
            return issue
    return None


def _assembly_anchor_issue(block: str, anchor: TextAnchor) -> ConformanceIssue | None:
    return _text_anchor_issue(block, anchor)


def _return_register_issue(block: str, contract: syscall_boundary_contract.SyscallBoundaryContract) -> ConformanceIssue | None:
    call_index = block.find(f"call {contract.entry.dispatcher_symbol}")
    ret_index = block.find("ret", call_index)
    if call_index >= 0 and ret_index > call_index and not re.search(r"\bmov\s+rax\b", block[call_index:ret_index]):
        return None
    return _issue("wrong_return_register", "calling_convention.return.register", "Assembly must leave dispatcher return value in rax")


def _odin_mutation_set_issue(
    heartbeat_branch: str,
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> ConformanceIssue | None:
    mutated_fields = tuple(re.findall(r"\bpayload\.([a-z_][a-z0-9_]*)\s*=", heartbeat_branch))
    allowed = contract.ownership.kernel_may_mutate
    unknown = tuple(field for field in mutated_fields if field not in allowed)
    if unknown:
        return _issue("odin_unknown_mutated_field", "ownership.kernel_may_mutate", f"Odin mutates non-contract payload field {unknown[0]}")
    expected = contract.debug_heartbeat.success_behavior.mutates_payload
    if mutated_fields == expected:
        return None
    return _issue("odin_mutated_field_set_mismatch", "syscalls.debug_heartbeat.success_behavior.mutates_payload", f"Expected mutations {expected}, got {mutated_fields}")


def _dispatcher_anchor(contract: syscall_boundary_contract.SyscallBoundaryContract) -> TextAnchor:
    return TextAnchor("wrong_dispatcher_symbol", "entry.dispatcher_symbol", f"call {contract.entry.dispatcher_symbol}", "Assembly handoff does not call the contract dispatcher")


def _syscall_id_capture_anchor(contract: syscall_boundary_contract.SyscallBoundaryContract) -> TextAnchor:
    return TextAnchor("wrong_syscall_id_register", "calling_convention.syscall_id.register", f"mov rax, {contract.calling_convention.syscall_id.register}", "Assembly does not capture syscall id from the contract register")


def _syscall_id_handoff_anchor(contract: syscall_boundary_contract.SyscallBoundaryContract) -> TextAnchor:
    return TextAnchor("wrong_syscall_id_register", "calling_convention.syscall_id.register", "mov rdi, rax", "Assembly does not hand syscall id to the dispatcher")


def _payload_capture_anchor(contract: syscall_boundary_contract.SyscallBoundaryContract) -> TextAnchor:
    return TextAnchor("wrong_payload_register", "calling_convention.payload.register", f"mov rbx, {contract.calling_convention.payload.register}", "Assembly does not capture payload from the contract register")


def _payload_handoff_anchor(contract: syscall_boundary_contract.SyscallBoundaryContract) -> TextAnchor:
    return TextAnchor("wrong_payload_register", "calling_convention.payload.register", "mov rsi, rbx", "Assembly does not hand payload to the dispatcher")


def _rust_syscall_anchor(contract: syscall_boundary_contract.SyscallBoundaryContract) -> TextAnchor:
    return TextAnchor("rust_wrong_syscall_constant", "syscalls.debug_heartbeat.constant", f"let syscall: abi::K_SYSCALL_ID = abi::{contract.debug_heartbeat.constant};", "Rust live path does not use the contract syscall constant")


def _rust_request_sequence_anchor(sequence: str | int) -> TextAnchor:
    return TextAnchor("rust_request_sentinel_mismatch", "syscalls.debug_heartbeat.request.sequence", f"sequence: {_literal(sequence)}", "Rust request sequence sentinel does not match the contract")


def _rust_request_timestamp_anchor(timestamp: str | int) -> TextAnchor:
    return TextAnchor("rust_request_sentinel_mismatch", "syscalls.debug_heartbeat.request.timestamp", f"timestamp: {_literal(timestamp)}", "Rust request timestamp sentinel does not match the contract")


def _rust_request_status_anchor(status: str) -> TextAnchor:
    return TextAnchor("rust_request_sentinel_mismatch", "syscalls.debug_heartbeat.request.status_bits", f"status_bits: abi::{status}", "Rust request status_bits sentinel does not match the contract")


def _rust_return_status_anchor(status: str) -> TextAnchor:
    return TextAnchor("rust_response_validation_mismatch", "syscalls.debug_heartbeat.success_behavior.return_status", f"if status != abi::{status}", "Rust returned status validation does not match the contract")


def _rust_response_sequence_anchor(sequence: str | int) -> TextAnchor:
    return TextAnchor("rust_response_validation_mismatch", "syscalls.debug_heartbeat.response.sequence", f"if payload.sequence != {_literal(sequence)}", "Rust response sequence validation does not match the contract")


def _rust_response_timestamp_anchor(timestamp: str | int) -> TextAnchor:
    return TextAnchor("rust_response_validation_mismatch", "syscalls.debug_heartbeat.response.timestamp", f"if payload.timestamp != {_literal(timestamp)}", "Rust response timestamp validation does not match the contract")


def _rust_response_status_anchor(status: str) -> TextAnchor:
    return TextAnchor("rust_response_validation_mismatch", "syscalls.debug_heartbeat.response.status_bits", f"if payload.status_bits != abi::{status}", "Rust response status_bits validation does not match the contract")


def _odin_null_payload_anchor(status: str) -> TextAnchor:
    return TextAnchor("odin_null_payload_invalid_return_mismatch", "syscalls.debug_heartbeat.invalid_behavior.null_payload", f"if payload == nil {{\n\t\t\treturn abi.{status}", "Odin null payload invalid return does not match the contract")


def _odin_bad_sequence_anchor(contract: syscall_boundary_contract.SyscallBoundaryContract) -> TextAnchor:
    sequence = contract.debug_heartbeat.request.sequence
    status = contract.debug_heartbeat.invalid_behavior.bad_sequence
    return TextAnchor("odin_bad_sequence_invalid_return_mismatch", "syscalls.debug_heartbeat.invalid_behavior.bad_sequence", f"if payload.sequence != {_literal(sequence)} {{\n\t\t\treturn abi.{status}", "Odin bad-sequence invalid return does not match the contract")


def _odin_response_sequence_anchor(sequence: str | int) -> TextAnchor:
    return TextAnchor("odin_response_sentinel_mismatch", "syscalls.debug_heartbeat.response.sequence", f"payload.sequence = {_literal(sequence)}", "Odin response sequence write does not match the contract")


def _odin_response_timestamp_anchor(timestamp: str | int) -> TextAnchor:
    return TextAnchor("odin_response_sentinel_mismatch", "syscalls.debug_heartbeat.response.timestamp", f"payload.timestamp = {_literal(timestamp)}", "Odin response timestamp write does not match the contract")


def _odin_response_status_anchor(status: str) -> TextAnchor:
    return TextAnchor("odin_response_sentinel_mismatch", "syscalls.debug_heartbeat.response.status_bits", f"payload.status_bits = u32(abi.{status})", "Odin response status_bits write does not match the contract")


def _odin_success_return_anchor(status: str) -> TextAnchor:
    return TextAnchor("odin_success_return_mismatch", "syscalls.debug_heartbeat.success_behavior.return_status", f"return abi.{status}", "Odin success return does not match the contract")


def _assembly_entry_block(source: str, label_name: str) -> str | None:
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
        match = _LABEL_PATTERN.match(lines[index].strip())
        if match is not None and not match.group("label").startswith("."):
            return index
    return len(lines)


def _rust_function_block(source: str, function_name: str) -> str | None:
    return _braced_block(source, rf"\bfn\s+{re.escape(function_name)}\s*\(")


def _odin_proc_block(source: str, proc_name: str) -> str | None:
    return _braced_declaration_block(source, rf"\b{re.escape(proc_name)}\s*::\s*proc\b")


def _braced_block(source: str, start_pattern: str) -> str | None:
    match = re.search(start_pattern, source)
    if match is None:
        return None
    opening_brace = source.find("{", match.end())
    if opening_brace == -1:
        return None
    return _balanced_block(source, opening_brace)


def _braced_declaration_block(source: str, start_pattern: str) -> str | None:
    match = re.search(start_pattern, source)
    if match is None:
        return None
    opening_brace = source.find("{", match.end())
    if opening_brace == -1:
        return None
    body = _balanced_block(source, opening_brace)
    if body is None:
        return None
    return source[match.start():opening_brace] + body


def _balanced_block(source: str, opening_brace: int) -> str | None:
    depth = 0
    for index in range(opening_brace, len(source)):
        depth += source[index] == "{"
        depth -= source[index] == "}"
        if depth == 0:
            return source[opening_brace:index + 1]
    return None


def _odin_case_block(source: str, case_label: str) -> str | None:
    lines = source.splitlines()
    start = _case_line_index(lines, case_label)
    if start < 0:
        return None
    end = _case_block_end(lines, start, _line_indent(lines[start]))
    return "\n".join(lines[start + 1:end])


def _case_line_index(lines: list[str], case_label: str) -> int:
    for index, line in enumerate(lines):
        if line.strip() == case_label:
            return index
    return -1


def _case_block_end(lines: list[str], start: int, case_indent: str) -> int:
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        indent = _line_indent(lines[index])
        if len(indent) > len(case_indent):
            continue
        if indent == case_indent and (stripped.startswith("case ") or stripped == "}"):
            return index
    return len(lines)


def _line_indent(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def _missing_block_issue(
    block: str | None,
    reason: str,
    contract_field: str,
    detail: str,
) -> ConformanceIssue | None:
    if block is not None:
        return None
    return _issue(reason, contract_field, detail)


def _text_anchor_issue(source: str, anchor: TextAnchor) -> ConformanceIssue | None:
    if anchor.needle in source:
        return None
    return _issue(anchor.reason, anchor.contract_field, anchor.detail)


def _literal(value: str | int) -> str:
    return str(value)


def _first_issue(*issues: ConformanceIssue | None) -> ConformanceIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, contract_field: str, detail: str) -> ConformanceIssue:
    return ConformanceIssue(reason, contract_field, detail)


def _failure_result(issue: ConformanceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=SYSCALL_BOUNDARY_CONFORMANCE_INVALID,
        detail=f"Syscall boundary conformance invalid: {issue.reason}: {issue.contract_field}: {issue.detail}",
        action="Keep live assembly, Rust, and Odin sources conformant with contracts/syscall_boundary_contract.v0.json",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
