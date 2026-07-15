from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import runtime_halt_contract
from harness.codes import OK, RUNTIME_HALT_CONTRACT_INVALID
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = runtime_halt_contract.CONTRACT_PATH
_EXPECTED_ARCHITECTURE = "x86_64"
_EXPECTED_ENTRY_SYMBOL = "_start"
_EXPECTED_MARKER_TEXT = "KOZO_RUNTIME_RETURN_OK"
_EXPECTED_TERMINAL_KIND = "halt_loop"
_REQUIRED_NON_GOALS = (
    "hardware trap execution",
    "interrupt handling",
    "scheduler behavior",
    "userspace execution",
    "process model behavior",
    "VFS behavior",
    "file descriptor behavior",
    "production readiness",
)


@dataclass(frozen=True)
class RuntimeHaltIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class RuntimeHaltContext:
    contract: runtime_halt_contract.RuntimeHaltContract
    source_text: str
    entry_lines: tuple[str, ...]


class RuntimeHaltContractValidator(BaseValidator):
    name = "runtime_halt_contract"
    subsystem = "runtime_halt_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _runtime_halt_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Runtime halt contract proves the post-smoke assembly path enters a terminal halt loop",
        )


def _runtime_halt_issue(contract_path: Path) -> RuntimeHaltIssue | None:
    context = _load_context(contract_path)
    if isinstance(context, RuntimeHaltIssue):
        return context
    return _first_issue(
        _contract_value_issue(context.contract),
        _non_goal_issue(context.contract),
        _marker_definition_issue(context),
        _terminal_behavior_issue(context),
    )


def _load_context(contract_path: Path) -> RuntimeHaltContext | RuntimeHaltIssue:
    contract = _load_contract(contract_path)
    if isinstance(contract, RuntimeHaltIssue):
        return contract
    source_text = _load_source(contract)
    if isinstance(source_text, RuntimeHaltIssue):
        return source_text
    entry_lines = _entry_lines(source_text, contract.source.entry_symbol)
    if entry_lines is None:
        return _issue("missing_entry_symbol", "source.entry_symbol", f"Entry symbol {contract.source.entry_symbol} is missing")
    return RuntimeHaltContext(contract, source_text, entry_lines)


def _load_contract(path: Path) -> runtime_halt_contract.RuntimeHaltContract | RuntimeHaltIssue:
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Runtime halt contract is missing: {path}")
    try:
        return runtime_halt_contract.load_runtime_halt_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Runtime halt contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Runtime halt contract schema violation: {exc}")


def _load_source(contract: runtime_halt_contract.RuntimeHaltContract) -> str | RuntimeHaltIssue:
    source_path = runtime_halt_contract.contract_repo_path(contract.source.path)
    if not source_path.is_file():
        return _issue("missing_source_file", "source.path", f"Runtime halt source is missing: {contract.source.path}")
    return source_path.read_text()


def _contract_value_issue(contract: runtime_halt_contract.RuntimeHaltContract) -> RuntimeHaltIssue | None:
    return _first_issue(
        _expected_value_issue(contract.architecture, _EXPECTED_ARCHITECTURE, "wrong_architecture", "architecture"),
        _expected_value_issue(contract.source.entry_symbol, _EXPECTED_ENTRY_SYMBOL, "wrong_entry_symbol", "source.entry_symbol"),
        _expected_value_issue(contract.final_smoke_marker.text, _EXPECTED_MARKER_TEXT, "wrong_final_marker", "final_smoke_marker.text"),
        _expected_value_issue(contract.terminal_behavior.kind, _EXPECTED_TERMINAL_KIND, "wrong_terminal_kind", "terminal_behavior.kind"),
        _fallthrough_contract_issue(contract),
    )


def _non_goal_issue(contract: runtime_halt_contract.RuntimeHaltContract) -> RuntimeHaltIssue | None:
    for non_goal in _REQUIRED_NON_GOALS:
        if non_goal not in contract.non_goals:
            return _issue("missing_non_goal", f"non_goals.{non_goal}", f"Runtime halt contract must preserve non-goal: {non_goal}")
    return None


def _marker_definition_issue(context: RuntimeHaltContext) -> RuntimeHaltIssue | None:
    marker = context.contract.final_smoke_marker
    if f'{marker.symbol}:' not in context.source_text:
        return _issue("missing_marker", "final_smoke_marker.symbol", f"Marker symbol {marker.symbol} is missing")
    if marker.text not in context.source_text:
        return _issue("missing_marker", "final_smoke_marker.text", f"Marker text {marker.text} is missing")
    return None


def _terminal_behavior_issue(context: RuntimeHaltContext) -> RuntimeHaltIssue | None:
    marker_index = _marker_write_index(context.entry_lines, context.contract)
    terminal = _terminal_indexes(context.entry_lines, context.contract, marker_index)
    if marker_index is None:
        return _issue("missing_marker", "final_smoke_marker.write_macro", "Final smoke marker write is missing from entry path")
    if terminal.first_index is None:
        return _issue("missing_halt_loop", "terminal_behavior.instructions", "Runtime halt loop is missing from entry path")
    if marker_index > terminal.first_index:
        return _issue("marker_after_halt", "final_smoke_marker.write_macro", "Final smoke marker must be emitted before terminal halt behavior")
    if terminal.hlt_index is None:
        return _issue("missing_halt_instruction", "terminal_behavior.instructions.hlt", "Runtime halt loop must execute hlt")
    if terminal.jump_index is None:
        return _issue("missing_loop_back_edge", "terminal_behavior.instructions.jmp", "Runtime halt loop must jump back to its label")
    fallthrough_issue = _fallthrough_issue(context.entry_lines, terminal.jump_index)
    if fallthrough_issue is not None:
        return fallthrough_issue
    return None


@dataclass(frozen=True)
class TerminalIndexes:
    first_index: int | None
    hlt_index: int | None
    jump_index: int | None


def _terminal_indexes(
    lines: tuple[str, ...],
    contract: runtime_halt_contract.RuntimeHaltContract,
    marker_index: int | None,
) -> TerminalIndexes:
    label = contract.terminal_behavior.label
    cli_index = _line_index_after(lines, "cli", marker_index) if contract.terminal_behavior.disable_interrupts else None
    hlt_index = _line_index_after(lines, "hlt", cli_index)
    jump_index = _line_index_after(lines, f"jmp {label}", hlt_index)
    first_candidates = [index for index in (cli_index, hlt_index, jump_index) if index is not None]
    first_index = min(first_candidates) if first_candidates else None
    return TerminalIndexes(first_index, hlt_index, jump_index)


def _marker_write_index(
    lines: tuple[str, ...],
    contract: runtime_halt_contract.RuntimeHaltContract,
) -> int | None:
    expected_prefix = f"{contract.final_smoke_marker.write_macro} {contract.final_smoke_marker.symbol},"
    for index, line in enumerate(lines):
        if line.startswith(expected_prefix):
            return index
    return None


def _fallthrough_issue(lines: tuple[str, ...], jump_index: int | None) -> RuntimeHaltIssue | None:
    if jump_index is None:
        return None
    for line in lines[jump_index + 1:]:
        if _is_label(line):
            continue
        return _issue("fallthrough_allowed", "terminal_behavior.fallthrough_forbidden", "Executable instructions after the halt loop are forbidden")
    return None


def _fallthrough_contract_issue(contract: runtime_halt_contract.RuntimeHaltContract) -> RuntimeHaltIssue | None:
    if contract.terminal_behavior.fallthrough_forbidden:
        return None
    return _issue("fallthrough_allowed", "terminal_behavior.fallthrough_forbidden", "Runtime halt contract must forbid fallthrough")


def _entry_lines(source_text: str, entry_symbol: str) -> tuple[str, ...] | None:
    lines = tuple(_normalized_lines(source_text))
    entry_label = f"{entry_symbol}:"
    try:
        start_index = lines.index(entry_label)
    except ValueError:
        return None
    body = []
    for line in lines[start_index + 1:]:
        if _is_global_label(line):
            break
        body.append(line)
    return tuple(body)


def _normalized_lines(source_text: str) -> list[str]:
    normalized = []
    for raw_line in source_text.splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if line:
            normalized.append(" ".join(line.split()))
    return normalized


def _line_index(lines: tuple[str, ...], expected: str) -> int | None:
    return _line_index_after(lines, expected, None)


def _line_index_after(lines: tuple[str, ...], expected: str, after: int | None) -> int | None:
    start = 0 if after is None else after + 1
    for index in range(start, len(lines)):
        if lines[index] == expected:
            return index
    return None


def _expected_value_issue(
    actual: str,
    expected: str,
    reason: str,
    contract_field: str,
) -> RuntimeHaltIssue | None:
    if actual == expected:
        return None
    return _issue(reason, contract_field, f"Expected {contract_field} to be {expected}, got {actual}")


def _is_label(line: str) -> bool:
    return line.endswith(":")


def _is_global_label(line: str) -> bool:
    return _is_label(line) and not line.startswith(".")


def _first_issue(*issues: RuntimeHaltIssue | None) -> RuntimeHaltIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> RuntimeHaltIssue:
    return RuntimeHaltIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: RuntimeHaltIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_HALT_CONTRACT_INVALID,
        detail=issue.detail,
        action="Keep contracts/runtime_halt_contract.v0.json and kernel/arch/x86_64/boot.asm aligned with the post-smoke terminal path",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
