from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from harness import abi_manifest, syscall_table_contract
from harness.codes import OK, SYSCALL_TABLE_CONFORMANCE_INVALID
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = syscall_table_contract.CONTRACT_PATH
_ABI_MANIFEST_PATH = abi_manifest.MANIFEST_PATH


@dataclass(frozen=True)
class ConformanceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class ConformanceContext:
    contract: syscall_table_contract.SyscallTableContract
    manifest: abi_manifest.AbiManifest
    dispatcher_source: str


@dataclass(frozen=True)
class DispatcherSource:
    declaration: str
    switch_body: str
    default_path: str


@dataclass(frozen=True)
class DispatcherBranch:
    selector: str
    body: str


class SyscallTableConformanceValidator(BaseValidator):
    name = "syscall_table_conformance"
    subsystem = "syscall_table_conformance"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _conformance_issue(_CONTRACT_PATH, _ABI_MANIFEST_PATH)
        if issue is not None:
            return _failure_result(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Live dispatcher source conforms to syscall table contract v0",
        )


def _conformance_issue(contract_path: Path, manifest_path: Path) -> ConformanceIssue | None:
    context = _load_conformance_context(contract_path, manifest_path)
    if isinstance(context, ConformanceIssue):
        return context
    dispatcher = _extract_dispatcher(context)
    if isinstance(dispatcher, ConformanceIssue):
        return dispatcher
    return _first_issue(
        _dispatcher_signature_issue(context, dispatcher),
        _valid_syscall_issue(context, dispatcher),
        _extra_branch_issue(context, dispatcher),
        _unknown_behavior_issue(context, dispatcher),
    )


def _load_conformance_context(
    contract_path: Path,
    manifest_path: Path,
) -> ConformanceContext | ConformanceIssue:
    contract = _load_contract(contract_path)
    if isinstance(contract, ConformanceIssue):
        return contract
    manifest = _load_manifest(manifest_path)
    if isinstance(manifest, ConformanceIssue):
        return manifest
    source = _load_dispatcher_source(contract)
    if isinstance(source, ConformanceIssue):
        return source
    return ConformanceContext(contract, manifest, source)


def _load_contract(path: Path) -> syscall_table_contract.SyscallTableContract | ConformanceIssue:
    try:
        return syscall_table_contract.load_syscall_table_contract(path)
    except (OSError, TypeError, ValueError) as exc:
        return _issue("contract_unavailable", "contract", f"Syscall table contract could not be loaded: {exc}")


def _load_manifest(path: Path) -> abi_manifest.AbiManifest | ConformanceIssue:
    try:
        return abi_manifest.load_abi_manifest(path)
    except (OSError, TypeError, ValueError) as exc:
        return _issue("abi_manifest_unavailable", "relationships.abi_manifest", f"ABI manifest could not be loaded: {exc}")


def _load_dispatcher_source(
    contract: syscall_table_contract.SyscallTableContract,
) -> str | ConformanceIssue:
    source_path = syscall_table_contract.contract_repo_path(contract.dispatcher.source_path)
    if not source_path.is_file():
        return _issue("missing_dispatcher_source", "dispatcher.source_path", f"Dispatcher source does not exist: {contract.dispatcher.source_path}")
    try:
        return source_path.read_text()
    except OSError as exc:
        return _issue("missing_dispatcher_source", "dispatcher.source_path", f"Dispatcher source could not be read: {exc}")


def _extract_dispatcher(context: ConformanceContext) -> DispatcherSource | ConformanceIssue:
    declaration = _braced_declaration_block(
        context.dispatcher_source,
        rf"\b{re.escape(context.contract.dispatcher.symbol)}\s*::\s*proc\b",
    )
    if declaration is None:
        return _issue("missing_dispatcher_symbol", "dispatcher.symbol", f"Dispatcher symbol {context.contract.dispatcher.symbol} is missing")
    switch_body = _switch_body(declaration, "id")
    if switch_body is None:
        return _issue("missing_unknown_branch", "unknown_syscall_behavior.return_status", "Dispatcher switch over syscall id is missing")
    return DispatcherSource(declaration, switch_body, _after_switch_body(declaration, switch_body))


def _dispatcher_signature_issue(
    context: ConformanceContext,
    dispatcher: DispatcherSource,
) -> ConformanceIssue | None:
    contract = context.contract.dispatcher
    return _first_issue(
        _text_issue(dispatcher.declaration, f"id: abi.{contract.syscall_id_type}", "syscall_id_type_mismatch", "dispatcher.syscall_id_type"),
        _text_issue(dispatcher.declaration, f"-> abi.{contract.return_type}", "return_type_mismatch", "dispatcher.return_type"),
    )


def _valid_syscall_issue(
    context: ConformanceContext,
    dispatcher: DispatcherSource,
) -> ConformanceIssue | None:
    for syscall in context.contract.valid_syscalls:
        issue = _single_syscall_issue(context, dispatcher, syscall)
        if issue is not None:
            return issue
    return None


def _single_syscall_issue(
    context: ConformanceContext,
    dispatcher: DispatcherSource,
    syscall: syscall_table_contract.PayloadSyscall | syscall_table_contract.NoPayloadSyscall,
) -> ConformanceIssue | None:
    branch = _branch_for_syscall(dispatcher, syscall)
    if isinstance(syscall, syscall_table_contract.NoPayloadSyscall):
        return _no_payload_syscall_issue(context, dispatcher, syscall, branch)
    return _payload_syscall_issue(context, dispatcher, syscall, branch)


def _payload_syscall_issue(
    context: ConformanceContext,
    dispatcher: DispatcherSource,
    syscall: syscall_table_contract.PayloadSyscall,
    branch: DispatcherBranch | None,
) -> ConformanceIssue | None:
    return _first_issue(
        _abi_syscall_constant_issue(context, syscall),
        _abi_payload_layout_issue(context, syscall),
        _branch_selector_issue(context, dispatcher, syscall, branch),
        _payload_layout_issue(context, dispatcher),
        _branch_body_issue(branch, syscall),
    )


def _no_payload_syscall_issue(
    context: ConformanceContext,
    dispatcher: DispatcherSource,
    syscall: syscall_table_contract.NoPayloadSyscall,
    branch: DispatcherBranch | None,
) -> ConformanceIssue | None:
    return _first_issue(
        _abi_syscall_constant_issue(context, syscall),
        _branch_selector_issue(context, dispatcher, syscall, branch),
        _no_payload_return_issue(branch, syscall),
        _no_payload_mutation_issue(branch, syscall),
        _no_payload_heartbeat_layout_issue(branch, syscall),
        _status_constant_issue(context, syscall),
    )


def _abi_syscall_constant_issue(
    context: ConformanceContext,
    syscall: syscall_table_contract.PayloadSyscall | syscall_table_contract.NoPayloadSyscall,
) -> ConformanceIssue | None:
    if syscall.constant in context.manifest.constants.syscalls:
        return None
    return _issue("missing_abi_syscall_constant", f"valid_syscalls.{syscall.name}.constant", f"{syscall.constant} is not declared in ABI manifest syscalls")


def _abi_payload_layout_issue(
    context: ConformanceContext,
    syscall: syscall_table_contract.PayloadSyscall,
) -> ConformanceIssue | None:
    if syscall.payload_layout == "heartbeat_payload":
        return None
    return _issue("missing_abi_payload_layout", f"valid_syscalls.{syscall.name}.payload_layout", f"{syscall.payload_layout} is not declared in ABI manifest layouts")


def _branch_selector_issue(
    context: ConformanceContext,
    dispatcher: DispatcherSource,
    syscall: syscall_table_contract.PayloadSyscall | syscall_table_contract.NoPayloadSyscall,
    branch: DispatcherBranch | None,
) -> ConformanceIssue | None:
    if not syscall.branch_selector.startswith("abi."):
        return _issue("hardcoded_branch_selector", f"valid_syscalls.{syscall.name}.branch_selector", f"{syscall.branch_selector} is not ABI namespaced")
    if _has_hardcoded_case_for_syscall(context, dispatcher.switch_body, syscall):
        return _issue("hardcoded_branch_selector", f"valid_syscalls.{syscall.name}.branch_selector", "Dispatcher contains a numeric syscall case")
    if branch is not None:
        return None
    return _issue("missing_valid_syscall_branch", f"valid_syscalls.{syscall.name}.branch_selector", f"Dispatcher is missing {syscall.branch_selector}")


def _payload_layout_issue(
    context: ConformanceContext,
    dispatcher: DispatcherSource,
) -> ConformanceIssue | None:
    expected_type = context.manifest.heartbeat_payload.odin_name
    if f"payload: ^abi.{expected_type}" in dispatcher.declaration:
        return None
    return _issue("payload_layout_mismatch", "valid_syscalls.debug_heartbeat.payload_layout", f"Dispatcher payload type must use abi.{expected_type}")


def _branch_body_issue(
    branch: DispatcherBranch | None,
    syscall: syscall_table_contract.PayloadSyscall,
) -> ConformanceIssue | None:
    if branch is None:
        return None
    if _is_heartbeat_body(branch.body):
        return None
    return _issue("wrong_branch_body", f"valid_syscalls.{syscall.name}.branch_selector", f"{syscall.branch_selector} does not map to the heartbeat body")


def _extra_branch_issue(
    context: ConformanceContext,
    dispatcher: DispatcherSource,
) -> ConformanceIssue | None:
    allowed = {
        *(syscall.branch_selector for syscall in context.contract.valid_syscalls),
    }
    for selector in _case_selectors(dispatcher.switch_body):
        if selector not in allowed:
            return _issue("extra_uncontracted_branch", "valid_syscalls", f"{selector} is handled but not declared or allowed by the table contract")
    return None


def _unknown_behavior_issue(
    context: ConformanceContext,
    dispatcher: DispatcherSource,
) -> ConformanceIssue | None:
    behavior = context.contract.unknown_syscall_behavior
    return _first_issue(
        _unknown_branch_issue(dispatcher),
        _unknown_return_issue(dispatcher.default_path, behavior.return_status),
        _unknown_mutation_issue(dispatcher.default_path, behavior.must_not_mutate_payload),
        _unknown_heartbeat_logic_issue(dispatcher.default_path),
        _unknown_reachability_issue(dispatcher.default_path),
        _unknown_status_manifest_issue(context, behavior.return_status),
    )


def _unknown_branch_issue(dispatcher: DispatcherSource) -> ConformanceIssue | None:
    if re.search(r"\breturn\s+abi\.\w+", dispatcher.default_path) is not None:
        return None
    return _issue("missing_unknown_branch", "unknown_syscall_behavior.return_status", "Dispatcher has no default unknown-syscall return after the switch")


def _unknown_return_issue(default_path: str, status: str) -> ConformanceIssue | None:
    if f"return abi.{status}" in default_path:
        return None
    return _issue("wrong_unknown_return_status", "unknown_syscall_behavior.return_status", f"Unknown syscall path must return abi.{status}")


def _unknown_mutation_issue(default_path: str, must_not_mutate: bool) -> ConformanceIssue | None:
    if not must_not_mutate or re.search(r"\bpayload\.[a-z_][a-z0-9_]*\s*=(?!=)", default_path) is None:
        return None
    return _issue("unknown_path_mutates_payload", "unknown_syscall_behavior.must_not_mutate_payload", "Unknown syscall path mutates payload state")


def _unknown_heartbeat_logic_issue(default_path: str) -> ConformanceIssue | None:
    if "serial_log_debug_heartbeat" not in default_path and "0xCAFEFEEE" not in default_path and "u32(abi.K_OK)" not in default_path:
        return None
    return _issue("unknown_path_calls_heartbeat_logic", "unknown_syscall_behavior", "Unknown syscall path calls heartbeat mutation or observation logic")


def _unknown_reachability_issue(default_path: str) -> ConformanceIssue | None:
    if "unreachable" not in default_path:
        return None
    return _issue("unknown_path_unreachable", "unknown_syscall_behavior.return_status", "Unknown syscall path is marked unreachable")


def _unknown_status_manifest_issue(context: ConformanceContext, status: str) -> ConformanceIssue | None:
    if status in context.manifest.constants.status:
        return None
    return _issue("missing_abi_status_constant", "unknown_syscall_behavior.return_status", f"{status} is not declared in ABI manifest status constants")


def _status_constant_issue(
    context: ConformanceContext,
    syscall: syscall_table_contract.NoPayloadSyscall,
) -> ConformanceIssue | None:
    if syscall.return_status in context.manifest.constants.status:
        return None
    return _issue("missing_abi_status_constant", f"valid_syscalls.{syscall.name}.return_status", f"{syscall.return_status} is not declared in ABI manifest status constants")


def _no_payload_return_issue(
    branch: DispatcherBranch | None,
    syscall: syscall_table_contract.NoPayloadSyscall,
) -> ConformanceIssue | None:
    if branch is not None and f"return abi.{syscall.return_status}" in branch.body:
        return None
    return _issue("wrong_no_payload_return_status", f"valid_syscalls.{syscall.name}.return_status", f"{syscall.name} must return abi.{syscall.return_status}")


def _no_payload_mutation_issue(
    branch: DispatcherBranch | None,
    syscall: syscall_table_contract.NoPayloadSyscall,
) -> ConformanceIssue | None:
    if branch is None or not syscall.must_not_mutate_payload or re.search(r"\bpayload\.[a-z_][a-z0-9_]*\s*=(?!=)", branch.body) is None:
        return None
    return _issue("no_payload_mutates_payload", f"valid_syscalls.{syscall.name}.must_not_mutate_payload", f"{syscall.name} must not mutate payload")


def _no_payload_heartbeat_layout_issue(
    branch: DispatcherBranch | None,
    syscall: syscall_table_contract.NoPayloadSyscall,
) -> ConformanceIssue | None:
    if branch is None:
        return None
    if "payload" not in branch.body and "Heartbeat_Payload" not in branch.body and "0xCAFE" not in branch.body:
        return None
    return _issue("no_payload_uses_payload_layout", f"valid_syscalls.{syscall.name}", f"{syscall.name} must not use heartbeat payload layout or sentinels")


def _branch_for_syscall(
    dispatcher: DispatcherSource,
    syscall: syscall_table_contract.PayloadSyscall | syscall_table_contract.NoPayloadSyscall,
) -> DispatcherBranch | None:
    body = _case_block(dispatcher.switch_body, f"case {syscall.branch_selector}:")
    if body is None:
        return None
    return DispatcherBranch(syscall.branch_selector, body)


def _is_heartbeat_body(branch: str) -> bool:
    return (
        "if payload == nil" in branch
        and "payload.sequence != 0xCAFEFEED" in branch
        and "payload.sequence = 0xCAFEFEEE" in branch
        and "payload.status_bits = u32(abi.K_OK)" in branch
    )


def _has_hardcoded_case_for_syscall(
    context: ConformanceContext,
    switch_body: str,
    syscall: syscall_table_contract.PayloadSyscall | syscall_table_contract.NoPayloadSyscall,
) -> bool:
    expected_value = context.manifest.constants.syscalls.get(syscall.constant)
    return expected_value is not None and str(expected_value) in _numeric_case_selectors(switch_body)


def _numeric_case_selectors(switch_body: str) -> tuple[str, ...]:
    return tuple(selector for selector in _case_selectors(switch_body) if re.fullmatch(r"\d+", selector))


def _case_selectors(switch_body: str) -> tuple[str, ...]:
    return tuple(
        line.removeprefix("case ").removesuffix(":").strip()
        for line in (line.strip() for line in switch_body.splitlines())
        if line.startswith("case ") and line.endswith(":")
    )


def _text_issue(source: str, needle: str, reason: str, contract_field: str) -> ConformanceIssue | None:
    if needle in source:
        return None
    return _issue(reason, contract_field, f"Missing {needle!r}")


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


def _first_issue(*issues: ConformanceIssue | None) -> ConformanceIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, contract_field: str, detail: str) -> ConformanceIssue:
    return ConformanceIssue(reason, contract_field, detail)


def _failure_result(issue: ConformanceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=SYSCALL_TABLE_CONFORMANCE_INVALID,
        detail=f"Syscall table conformance invalid: {issue.reason}: {issue.contract_field}: {issue.detail}",
        action="Keep the live Odin dispatcher source conformant with contracts/syscall_table_contract.v0.json",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
