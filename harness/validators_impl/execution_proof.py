from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness.codes import EXECUTION_PROOF_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_KERNEL_MAIN = _ROOT / "kernel" / "main.odin"
_SERIAL = _ROOT / "kernel" / "arch" / "x86_64" / "serial.odin"

_HEARTBEAT_CASE_LABEL = "case abi.K_SYSCALL_DEBUG_HEARTBEAT:"

@dataclass(frozen=True)
class ExecutionSources:
    kernel: str
    serial: str


@dataclass(frozen=True)
class OrderedAnchor:
    name: str
    needle: str
    detail: str
    missing_reason: str


@dataclass(frozen=True)
class ObservationAnchor:
    name: str
    needle: str
    detail: str


@dataclass(frozen=True)
class ContractCheck:
    name: str
    ok: bool
    detail: str
    reason: str = ""
    contract_field: str = ""


_HEARTBEAT_EXECUTION_ANCHORS = (
    OrderedAnchor(
        "nil_payload_guard",
        "if payload == nil",
        "heartbeat branch must reject nil payloads before reading request fields",
        "missing_nil_guard",
    ),
    OrderedAnchor(
        "nil_payload_failure",
        "return abi.K_INVALID",
        "nil payload guard must fail closed with abi.K_INVALID",
        "missing_nil_guard",
    ),
    OrderedAnchor(
        "request_sequence_guard",
        "if payload.sequence != 0xCAFEFEED",
        "heartbeat branch must validate the incoming request sequence sentinel",
        "missing_request_guard",
    ),
    OrderedAnchor(
        "request_sequence_failure",
        "return abi.K_INVALID",
        "request sequence guard must fail closed with abi.K_INVALID",
        "missing_request_guard",
    ),
    OrderedAnchor(
        "ingress_observation_call",
        "x86_64.serial_log_debug_heartbeat_recv(payload.sequence)",
        "heartbeat branch must emit the ingress execution observation",
        "missing_observation_call",
    ),
    OrderedAnchor(
        "returned_sequence_write",
        "payload.sequence = 0xCAFEFEEE",
        "heartbeat branch must write the returned sequence sentinel",
        "missing_mutation",
    ),
    OrderedAnchor(
        "returned_timestamp_write",
        "payload.timestamp = 0xDEADBEEF",
        "heartbeat branch must write the returned timestamp sentinel",
        "missing_mutation",
    ),
    OrderedAnchor(
        "returned_status_bits_write",
        "payload.status_bits = u32(abi.K_OK)",
        "heartbeat branch must write successful returned status_bits",
        "missing_mutation",
    ),
    OrderedAnchor(
        "egress_observation_call",
        "x86_64.serial_log_debug_heartbeat_time(payload.timestamp)",
        "heartbeat branch must emit the egress execution observation",
        "missing_observation_call",
    ),
    OrderedAnchor(
        "success_return",
        "return abi.K_OK",
        "heartbeat branch must return abi.K_OK after observations and mutations",
        "missing_success_return",
    ),
)

_SERIAL_OBSERVATION_ANCHORS = (
    ObservationAnchor(
        "serial_recv_observation",
        'serial_write("SYSCALL[DEBUG_HEARTBEAT] Recv Seq: 0x")',
        "serial source must keep the stable ingress heartbeat observation string",
    ),
    ObservationAnchor(
        "serial_time_observation",
        'serial_write("SYSCALL[DEBUG_HEARTBEAT] New Time: 0x")',
        "serial source must keep the stable egress heartbeat observation string",
    ),
)


class ExecutionProofValidator(BaseValidator):
    name = "execution_proof"
    subsystem = "execution_proof"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        return _execution_proof_result(_read_execution_sources())


def _read_execution_sources() -> ExecutionSources:
    return ExecutionSources(
        kernel=_KERNEL_MAIN.read_text(),
        serial=_SERIAL.read_text(),
    )


def _execution_proof_result(sources: ExecutionSources) -> ValidationResult:
    checks = (
        _heartbeat_execution_check(sources.kernel),
        _serial_observation_check(sources.serial),
    )
    failing_check = _first_failing_check(checks)
    if failing_check is not None:
        return _failure_result(failing_check, checks)
    return ValidationResult(
        status="pass",
        code=OK,
        detail="Kernel sources prove the ordered heartbeat execution branch and stable serial observations",
        meta={"sub_results": _sub_results(checks)},
    )


def _heartbeat_execution_check(kernel_source: str) -> ContractCheck:
    branch = _extract_odin_case_block(kernel_source, _HEARTBEAT_CASE_LABEL)
    if branch is None:
        return ContractCheck(
            "heartbeat_execution_branch",
            False,
            "kernel/main.odin must define the live DEBUG_HEARTBEAT dispatch branch",
            "missing_odin_heartbeat_branch",
            "heartbeat_debug_branch",
        )
    return _ordered_branch_check(branch, kernel_source)


def _serial_observation_check(serial_source: str) -> ContractCheck:
    for anchor in _SERIAL_OBSERVATION_ANCHORS:
        if anchor.needle not in serial_source:
            return ContractCheck(
                "serial_observations",
                False,
                anchor.detail,
                "missing_serial_observation",
                anchor.name,
            )
    return ContractCheck(
        "serial_observations",
        True,
        "kernel/arch/x86_64/serial.odin provides stable heartbeat observation strings",
    )


def _first_failing_check(checks: tuple[ContractCheck, ...]) -> ContractCheck | None:
    for check in checks:
        if not check.ok:
            return check
    return None


def _sub_results(checks: tuple[ContractCheck, ...]) -> list[dict[str, str]]:
    return [
        {
            "name": check.name,
            "status": "pass" if check.ok else "fail",
            "detail": check.detail,
        }
        for check in checks
    ]


def _extract_odin_case_block(source: str, case_label: str) -> str | None:
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


def _line_indent(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def _case_block_end(lines: list[str], start: int, case_indent: str) -> int:
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        indent = _line_indent(lines[index])
        if len(indent) > len(case_indent):
            continue
        if indent == case_indent and (stripped.startswith("case ") or stripped == "}"):
            return index
    return len(lines)


def _ordered_branch_check(branch: str, source: str) -> ContractCheck:
    cursor = 0
    for anchor in _HEARTBEAT_EXECUTION_ANCHORS:
        index = branch.find(anchor.needle, cursor)
        if index < 0:
            return _execution_anchor_failure(branch, source, anchor)
        cursor = index + len(anchor.needle)
    return ContractCheck(
        "heartbeat_execution_branch",
        True,
        "kernel/main.odin executes guards, observations, ordered payload mutations, and success return in sequence",
    )


def _execution_anchor_failure(branch: str, source: str, anchor: OrderedAnchor) -> ContractCheck:
    if anchor.needle in branch:
        return ContractCheck(
            "heartbeat_execution_branch",
            False,
            anchor.detail,
            "out_of_order_execution_anchor",
            anchor.name,
        )
    if anchor.needle in source:
        return ContractCheck(
            "heartbeat_execution_branch",
            False,
            anchor.detail,
            "dead_snippet_outside_live_branch",
            anchor.name,
        )
    return ContractCheck(
        "heartbeat_execution_branch",
        False,
        anchor.detail,
        anchor.missing_reason,
        anchor.name,
    )


def _failure_result(failing_check: ContractCheck, checks: tuple[ContractCheck, ...]) -> ValidationResult:
    return ValidationResult.fail(
        code=EXECUTION_PROOF_INVALID,
        detail=(
            "Execution proof invalid: "
            f"{failing_check.reason}: {failing_check.contract_field}: {failing_check.detail}"
        ),
        action="Keep the live Odin heartbeat branch and stable serial observations aligned with the execution proof contract",
        meta={
            "reason": failing_check.reason,
            "contract_field": failing_check.contract_field,
            "sub_results": _sub_results(checks),
        },
    )
