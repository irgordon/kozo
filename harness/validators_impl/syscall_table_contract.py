from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from harness import abi_manifest, syscall_boundary_contract, syscall_table_contract
from harness.codes import OK, SYSCALL_TABLE_CONTRACT_INVALID
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = syscall_table_contract.CONTRACT_PATH
_ABI_MANIFEST_PATH = abi_manifest.MANIFEST_PATH
_BOUNDARY_CONTRACT_PATH = syscall_boundary_contract.CONTRACT_PATH

_EXPECTED_ARCHITECTURE = "x86_64"
_EXPECTED_DISPATCHER_SYMBOL = "syscall_dispatch"
_EXPECTED_SYSCALL_ID_TYPE = "K_SYSCALL_ID"
_EXPECTED_RETURN_TYPE = "K_STATUS"
_EXPECTED_BOUNDARY_CONTRACT = "debug_heartbeat"


@dataclass(frozen=True)
class TableIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class SourceBundle:
    dispatcher_source: str
    rust_binding: str
    odin_binding: str


@dataclass(frozen=True)
class TableContext:
    contract: syscall_table_contract.SyscallTableContract
    manifest: abi_manifest.AbiManifest
    boundary: syscall_boundary_contract.SyscallBoundaryContract
    sources: SourceBundle


@dataclass(frozen=True)
class DispatcherBlocks:
    declaration: str
    body: str
    switch_body: str
    default_path: str


class SyscallTableContractValidator(BaseValidator):
    name = "syscall_table_contract"
    subsystem = "syscall_table_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _table_contract_issue(_CONTRACT_PATH, _ABI_MANIFEST_PATH, _BOUNDARY_CONTRACT_PATH)
        if issue is not None:
            return _failure_result(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Syscall table contract v0 matches the live heartbeat dispatcher model",
        )


def _table_contract_issue(
    contract_path: Path,
    manifest_path: Path,
    boundary_path: Path,
) -> TableIssue | None:
    context = _load_table_context(contract_path, manifest_path, boundary_path)
    if isinstance(context, TableIssue):
        return context
    blocks = _dispatcher_blocks(context)
    if isinstance(blocks, TableIssue):
        return blocks
    return _first_issue(
        _architecture_issue(context.contract),
        _relationship_issue(context.contract),
        _dispatcher_contract_issue(context, blocks),
        _type_contract_issue(context),
        _syscall_contract_issue(context, blocks),
        _unknown_syscall_issue(context, blocks),
    )


def _load_table_context(
    contract_path: Path,
    manifest_path: Path,
    boundary_path: Path,
) -> TableContext | TableIssue:
    contract = _load_contract(contract_path)
    if isinstance(contract, TableIssue):
        return contract
    manifest = _load_manifest(manifest_path)
    if isinstance(manifest, TableIssue):
        return manifest
    boundary = _load_boundary(boundary_path)
    if isinstance(boundary, TableIssue):
        return boundary
    sources = _load_sources(contract, manifest)
    if isinstance(sources, TableIssue):
        return sources
    return TableContext(contract, manifest, boundary, sources)


def _load_contract(path: Path) -> syscall_table_contract.SyscallTableContract | TableIssue:
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Syscall table contract is missing: {path}")
    data = _load_contract_data(path)
    if isinstance(data, TableIssue):
        return data
    return _parse_contract(data)


def _load_contract_data(path: Path) -> dict | TableIssue:
    try:
        return syscall_table_contract.load_contract_json(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Syscall table contract is invalid JSON: {exc}")


def _parse_contract(data: dict) -> syscall_table_contract.SyscallTableContract | TableIssue:
    try:
        syscall_table_contract.validate_contract_shape(data)
        return syscall_table_contract.parse_syscall_table_contract(data)
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Syscall table contract schema violation: {exc}")


def _load_manifest(path: Path) -> abi_manifest.AbiManifest | TableIssue:
    try:
        return abi_manifest.load_abi_manifest(path)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return _issue("abi_manifest_unavailable", "relationships.abi_manifest", f"ABI manifest could not be loaded: {exc}")


def _load_boundary(path: Path) -> syscall_boundary_contract.SyscallBoundaryContract | TableIssue:
    try:
        return syscall_boundary_contract.load_syscall_boundary_contract(path)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return _issue("boundary_contract_unavailable", "relationships.syscall_boundary_contract", f"Boundary contract could not be loaded: {exc}")


def _load_sources(
    contract: syscall_table_contract.SyscallTableContract,
    manifest: abi_manifest.AbiManifest,
) -> SourceBundle | TableIssue:
    dispatcher_path = syscall_table_contract.contract_repo_path(contract.dispatcher.source_path)
    if not dispatcher_path.is_file():
        return _issue("missing_dispatcher_source", "dispatcher.source_path", f"Dispatcher source does not exist: {contract.dispatcher.source_path}")
    rust_binding_path = abi_manifest.manifest_repo_path(manifest.generated_bindings.rust)
    odin_binding_path = abi_manifest.manifest_repo_path(manifest.generated_bindings.odin)
    try:
        return SourceBundle(
            dispatcher_source=dispatcher_path.read_text(),
            rust_binding=rust_binding_path.read_text(),
            odin_binding=odin_binding_path.read_text(),
        )
    except OSError as exc:
        return _issue("source_unavailable", "source", f"Syscall table source could not be read: {exc}")


def _dispatcher_blocks(context: TableContext) -> DispatcherBlocks | TableIssue:
    declaration = _braced_declaration_block(
        context.sources.dispatcher_source,
        rf"\b{re.escape(context.contract.dispatcher.symbol)}\s*::\s*proc\b",
    )
    if declaration is None:
        return _issue("wrong_dispatcher_symbol", "dispatcher.symbol", f"Dispatcher symbol {context.contract.dispatcher.symbol} is missing")
    switch_body = _switch_body(declaration, "id")
    if switch_body is None:
        return _issue("missing_unknown_syscall_branch", "unknown_syscall_behavior", "Dispatcher switch over syscall id is missing")
    default_path = _after_switch_body(declaration, switch_body)
    return DispatcherBlocks(declaration, declaration, switch_body, default_path)


def _architecture_issue(contract: syscall_table_contract.SyscallTableContract) -> TableIssue | None:
    if contract.architecture == _EXPECTED_ARCHITECTURE:
        return None
    return _issue("wrong_architecture", "architecture", f"Expected {_EXPECTED_ARCHITECTURE}, got {contract.architecture}")


def _relationship_issue(contract: syscall_table_contract.SyscallTableContract) -> TableIssue | None:
    return _first_issue(
        _relationship_path_issue(contract.relationships.abi_manifest, "contracts/kozo_abi_manifest.json", "relationships.abi_manifest"),
        _relationship_path_issue(contract.relationships.syscall_boundary_contract, "contracts/syscall_boundary_contract.v0.json", "relationships.syscall_boundary_contract"),
    )


def _relationship_path_issue(actual: str, expected: str, contract_field: str) -> TableIssue | None:
    if actual == expected and syscall_table_contract.contract_repo_path(actual).is_file():
        return None
    return _issue("relationship_mismatch", contract_field, f"Expected existing relationship path {expected}, got {actual}")


def _dispatcher_contract_issue(context: TableContext, blocks: DispatcherBlocks) -> TableIssue | None:
    dispatcher = context.contract.dispatcher
    return _first_issue(
        _expected_value_issue(dispatcher.symbol, _EXPECTED_DISPATCHER_SYMBOL, "wrong_dispatcher_symbol", "dispatcher.symbol"),
        _dispatcher_signature_issue(blocks.declaration, dispatcher),
    )


def _dispatcher_signature_issue(
    declaration: str,
    dispatcher: syscall_table_contract.TableDispatcher,
) -> TableIssue | None:
    return _first_issue(
        _text_issue(declaration, f"id: abi.{dispatcher.syscall_id_type}", "wrong_dispatcher_signature", "dispatcher.syscall_id_type"),
        _text_issue(declaration, f"-> abi.{dispatcher.return_type}", "wrong_dispatcher_signature", "dispatcher.return_type"),
    )


def _type_contract_issue(context: TableContext) -> TableIssue | None:
    dispatcher = context.contract.dispatcher
    return _first_issue(
        _expected_value_issue(dispatcher.syscall_id_type, _EXPECTED_SYSCALL_ID_TYPE, "wrong_syscall_id_type", "dispatcher.syscall_id_type"),
        _expected_value_issue(dispatcher.return_type, _EXPECTED_RETURN_TYPE, "wrong_return_type", "dispatcher.return_type"),
        _binding_type_issue(context, dispatcher.syscall_id_type, "dispatcher.syscall_id_type"),
        _binding_type_issue(context, dispatcher.return_type, "dispatcher.return_type"),
    )


def _binding_type_issue(context: TableContext, type_name: str, contract_field: str) -> TableIssue | None:
    if _rust_type_exists(context.sources.rust_binding, type_name) and _odin_type_exists(context.sources.odin_binding, type_name):
        return None
    return _issue("missing_abi_type", contract_field, f"{type_name} is missing from generated ABI bindings")


def _syscall_contract_issue(context: TableContext, blocks: DispatcherBlocks) -> TableIssue | None:
    for syscall in context.contract.valid_syscalls:
        issue = _single_syscall_issue(context, blocks, syscall)
        if issue is not None:
            return issue
    return None


def _single_syscall_issue(
    context: TableContext,
    blocks: DispatcherBlocks,
    syscall: syscall_table_contract.PayloadSyscall | syscall_table_contract.NoPayloadSyscall,
) -> TableIssue | None:
    branch = _case_block(blocks.switch_body, f"case {syscall.branch_selector}:")
    if isinstance(syscall, syscall_table_contract.NoPayloadSyscall):
        return _no_payload_syscall_issue(context, blocks, syscall, branch)
    return _payload_syscall_issue(context, blocks, syscall, branch)


def _payload_syscall_issue(
    context: TableContext,
    blocks: DispatcherBlocks,
    syscall: syscall_table_contract.PayloadSyscall,
    branch: str | None,
) -> TableIssue | None:
    return _first_issue(
        _syscall_constant_issue(context, syscall),
        _payload_layout_issue(context, syscall),
        _boundary_mapping_issue(context, syscall),
        _branch_selector_consistency_issue(syscall),
        _branch_selector_presence_issue(branch, syscall),
        _branch_mapping_issue(branch or "", syscall),
        _unique_branch_selector_issue(blocks.switch_body, syscall),
    )


def _no_payload_syscall_issue(
    context: TableContext,
    blocks: DispatcherBlocks,
    syscall: syscall_table_contract.NoPayloadSyscall,
    branch: str | None,
) -> TableIssue | None:
    return _first_issue(
        _syscall_constant_issue(context, syscall),
        _no_payload_shape_issue(syscall),
        _status_constant_issue(context, syscall.return_status, f"valid_syscalls.{syscall.name}.return_status"),
        _branch_selector_consistency_issue(syscall),
        _branch_selector_presence_issue(branch, syscall),
        _no_payload_branch_issue(branch or "", syscall),
        _unique_branch_selector_issue(blocks.switch_body, syscall),
    )


def _syscall_constant_issue(
    context: TableContext,
    syscall: syscall_table_contract.PayloadSyscall | syscall_table_contract.NoPayloadSyscall,
) -> TableIssue | None:
    if syscall.constant in context.manifest.constants.syscalls:
        return None
    return _issue("missing_abi_syscall_constant", f"valid_syscalls.{syscall.name}.constant", f"{syscall.constant} is not declared in ABI manifest syscalls")


def _payload_layout_issue(
    context: TableContext,
    syscall: syscall_table_contract.PayloadSyscall,
) -> TableIssue | None:
    if syscall.payload_layout == "heartbeat_payload":
        return None
    return _issue("missing_payload_layout", f"valid_syscalls.{syscall.name}.payload_layout", f"{syscall.payload_layout} is not declared in ABI manifest layouts")


def _boundary_mapping_issue(
    context: TableContext,
    syscall: syscall_table_contract.PayloadSyscall,
) -> TableIssue | None:
    if syscall.boundary_contract == _EXPECTED_BOUNDARY_CONTRACT and syscall.constant == context.boundary.debug_heartbeat.constant:
        return None
    return _issue("wrong_branch_mapping", f"valid_syscalls.{syscall.name}.boundary_contract", "Table syscall does not map to the debug heartbeat boundary contract")


def _branch_selector_consistency_issue(
    syscall: syscall_table_contract.PayloadSyscall | syscall_table_contract.NoPayloadSyscall,
) -> TableIssue | None:
    expected_selector = f"abi.{syscall.constant}"
    if syscall.branch_selector == expected_selector:
        return None
    return _issue("wrong_branch_mapping", f"valid_syscalls.{syscall.name}.branch_selector", f"Expected {expected_selector}, got {syscall.branch_selector}")


def _branch_selector_presence_issue(
    branch: str | None,
    syscall: syscall_table_contract.PayloadSyscall | syscall_table_contract.NoPayloadSyscall,
) -> TableIssue | None:
    if branch is not None:
        return None
    return _issue("missing_branch_selector", f"valid_syscalls.{syscall.name}.branch_selector", f"Dispatcher is missing {syscall.branch_selector}")


def _branch_mapping_issue(branch: str, syscall: syscall_table_contract.PayloadSyscall) -> TableIssue | None:
    if "payload.sequence != 0xCAFEFEED" in branch and "payload.status_bits = u32(abi.K_OK)" in branch:
        return None
    return _issue("wrong_branch_mapping", f"valid_syscalls.{syscall.name}.branch_selector", f"{syscall.branch_selector} does not map to the heartbeat branch body")


def _no_payload_shape_issue(syscall: syscall_table_contract.NoPayloadSyscall) -> TableIssue | None:
    if not syscall.prohibited_fields:
        return None
    field = syscall.prohibited_fields[0]
    return _issue("no_payload_payload_layout_reference", f"valid_syscalls.{syscall.name}.{field}", f"No-payload syscall {syscall.name} must not declare {field}")


def _no_payload_branch_issue(branch: str, syscall: syscall_table_contract.NoPayloadSyscall) -> TableIssue | None:
    return _first_issue(
        _no_payload_return_issue(branch, syscall),
        _no_payload_mutation_issue(branch, syscall),
        _no_payload_heartbeat_layout_issue(branch, syscall),
    )


def _no_payload_return_issue(branch: str, syscall: syscall_table_contract.NoPayloadSyscall) -> TableIssue | None:
    if f"return abi.{syscall.return_status}" in branch:
        return None
    return _issue("wrong_no_payload_return_status", f"valid_syscalls.{syscall.name}.return_status", f"{syscall.name} must return abi.{syscall.return_status}")


def _no_payload_mutation_issue(branch: str, syscall: syscall_table_contract.NoPayloadSyscall) -> TableIssue | None:
    if not syscall.must_not_mutate_payload or re.search(r"\bpayload\.[a-z_][a-z0-9_]*\s*=(?!=)", branch) is None:
        return None
    return _issue("no_payload_mutates_payload", f"valid_syscalls.{syscall.name}.must_not_mutate_payload", f"{syscall.name} must not mutate payload")


def _no_payload_heartbeat_layout_issue(branch: str, syscall: syscall_table_contract.NoPayloadSyscall) -> TableIssue | None:
    if "payload" not in branch and "Heartbeat_Payload" not in branch and "0xCAFE" not in branch:
        return None
    return _issue("no_payload_uses_payload_layout", f"valid_syscalls.{syscall.name}", f"{syscall.name} must not use heartbeat payload layout or sentinels")


def _unique_branch_selector_issue(
    switch_body: str,
    syscall: syscall_table_contract.PayloadSyscall | syscall_table_contract.NoPayloadSyscall,
) -> TableIssue | None:
    if switch_body.count(f"case {syscall.branch_selector}:") == 1:
        return None
    return _issue("wrong_branch_mapping", f"valid_syscalls.{syscall.name}.branch_selector", f"{syscall.branch_selector} must appear exactly once")


def _unknown_syscall_issue(context: TableContext, blocks: DispatcherBlocks) -> TableIssue | None:
    behavior = context.contract.unknown_syscall_behavior
    return _first_issue(
        _status_constant_issue(context, behavior.return_status, "unknown_syscall_behavior.return_status"),
        _unknown_default_path_issue(blocks.default_path),
        _unknown_return_issue(blocks.default_path, behavior.return_status),
        _unknown_mutation_issue(blocks.default_path, behavior.must_not_mutate_payload),
    )


def _status_constant_issue(context: TableContext, constant: str, contract_field: str) -> TableIssue | None:
    if constant in context.manifest.constants.status:
        return None
    return _issue("unknown_status_constant", contract_field, f"{constant} is not declared in ABI manifest status constants")


def _unknown_default_path_issue(default_path: str) -> TableIssue | None:
    if re.search(r"\breturn\s+abi\.\w+", default_path) is not None:
        return None
    return _issue("missing_unknown_syscall_branch", "unknown_syscall_behavior.return_status", "Dispatcher has no default unknown-syscall return")


def _unknown_return_issue(default_path: str, status: str) -> TableIssue | None:
    if f"return abi.{status}" in default_path:
        return None
    return _issue("wrong_unknown_syscall_return", "unknown_syscall_behavior.return_status", f"Unknown syscall path must return abi.{status}")


def _unknown_mutation_issue(default_path: str, must_not_mutate: bool) -> TableIssue | None:
    if not must_not_mutate or re.search(r"\bpayload\.[a-z_][a-z0-9_]*\s*=(?!=)", default_path) is None:
        return None
    return _issue("unknown_path_mutates_payload", "unknown_syscall_behavior.must_not_mutate_payload", "Unknown syscall path mutates the heartbeat payload")


def _expected_value_issue(actual: object, expected: object, reason: str, contract_field: str) -> TableIssue | None:
    if actual == expected:
        return None
    return _issue(reason, contract_field, f"Expected {expected!r}, got {actual!r}")


def _text_issue(source: str, needle: str, reason: str, contract_field: str) -> TableIssue | None:
    if needle in source:
        return None
    return _issue(reason, contract_field, f"Missing {needle!r}")


def _rust_type_exists(source: str, type_name: str) -> bool:
    return re.search(rf"\bpub\s+type\s+{re.escape(type_name)}\b", source) is not None


def _odin_type_exists(source: str, type_name: str) -> bool:
    return re.search(rf"\b{re.escape(type_name)}\s*::", source) is not None


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


def _switch_body(source: str, expression: str) -> str | None:
    match = re.search(rf"\bswitch\s+{re.escape(expression)}\s*{{", source)
    if match is None:
        return None
    opening_brace = source.find("{", match.start())
    return _balanced_block(source, opening_brace)


def _after_switch_body(source: str, switch_body: str) -> str:
    switch_start = source.find(switch_body)
    if switch_start < 0:
        return ""
    return source[switch_start + len(switch_body):]


def _case_block(switch_body: str, case_label: str) -> str | None:
    lines = switch_body.splitlines()
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


def _balanced_block(source: str, opening_brace: int) -> str | None:
    depth = 0
    for index in range(opening_brace, len(source)):
        depth += source[index] == "{"
        depth -= source[index] == "}"
        if depth == 0:
            return source[opening_brace:index + 1]
    return None


def _first_issue(*issues: TableIssue | None) -> TableIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, contract_field: str, detail: str) -> TableIssue:
    return TableIssue(reason, contract_field, detail)


def _failure_result(issue: TableIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=SYSCALL_TABLE_CONTRACT_INVALID,
        detail=f"Syscall table contract invalid: {issue.reason}: {issue.contract_field}: {issue.detail}",
        action="Keep contracts/syscall_table_contract.v0.json aligned with the ABI manifest, boundary contract, and live dispatcher source",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
