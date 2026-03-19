from __future__ import annotations

from pathlib import Path

from harness.codes import EXECUTION_PROOF_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_KERNEL_MAIN = _ROOT / "kernel" / "main.odin"
_SERIAL = _ROOT / "kernel" / "arch" / "x86_64" / "serial.odin"
_RUST_MAIN = _ROOT / "userspace" / "core_service" / "src" / "main.rs"


def _line_index(lines: list[str], needle: str) -> int:
    for index, line in enumerate(lines):
        if needle in line:
            return index
    return -1


def _line_index_after(lines: list[str], needle: str, start: int) -> int:
    for index in range(start + 1, len(lines)):
        if needle in lines[index]:
            return index
    return -1


def _sub_result(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {
        "name": name,
        "status": "pass" if ok else "fail",
        "detail": detail,
    }


def _branch_lines(lines: list[str], case_label: str) -> list[str]:
    start = _line_index(lines, case_label)
    if start < 0:
        return []
    collected: list[str] = []
    for line in lines[start + 1:]:
        stripped = line.strip()
        if stripped.startswith("case "):
            break
        if line == "}":
            break
        collected.append(line)
    return collected


class ExecutionProofValidator(BaseValidator):
    name = "execution_proof"
    subsystem = "execution_proof"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        kernel_source = _KERNEL_MAIN.read_text()
        kernel_lines = kernel_source.splitlines()
        heartbeat_branch = _branch_lines(kernel_lines, "case abi.K_SYSCALL_DEBUG_HEARTBEAT:")
        serial_source = _SERIAL.read_text()
        rust_source = _RUST_MAIN.read_text()

        nil_guard_index = _line_index(heartbeat_branch, "if payload == nil")
        nil_return_index = _line_index_after(heartbeat_branch, "return abi.K_INVALID", nil_guard_index)
        magic_guard_index = _line_index(heartbeat_branch, "if payload.sequence != 0xCAFEFEED")
        magic_return_index = _line_index_after(heartbeat_branch, "return abi.K_INVALID", magic_guard_index)
        recv_log_index = _line_index(heartbeat_branch, "x86_64.serial_log_debug_heartbeat_recv")
        sequence_mutation_index = _line_index(heartbeat_branch, "payload.sequence += 1")
        timestamp_mutation_index = _line_index(heartbeat_branch, "payload.timestamp = 0xDEADBEEF")
        egress_log_index = _line_index(heartbeat_branch, "x86_64.serial_log_debug_heartbeat_time")
        success_return_index = _line_index(heartbeat_branch, "return abi.K_OK")

        sub_results = [
            _sub_result(
                "nil_guard",
                nil_guard_index >= 0 and nil_return_index > nil_guard_index,
                "kernel/main.odin guards nil payloads and returns the ABI error-equivalent constant first",
            ),
            _sub_result(
                "magic_guard",
                magic_guard_index >= 0 and "0xCAFEFEED" in kernel_source and magic_return_index > magic_guard_index,
                "kernel/main.odin validates the heartbeat magic before mutation",
            ),
            _sub_result(
                "mutation_order",
                all(index >= 0 for index in (
                    nil_guard_index,
                    magic_guard_index,
                    recv_log_index,
                    sequence_mutation_index,
                    timestamp_mutation_index,
                    egress_log_index,
                    success_return_index,
                ))
                and nil_guard_index < sequence_mutation_index
                and magic_guard_index < sequence_mutation_index
                and recv_log_index < sequence_mutation_index
                and sequence_mutation_index < timestamp_mutation_index
                and timestamp_mutation_index < egress_log_index
                and egress_log_index < success_return_index,
                "kernel/main.odin performs guards, ingress trace, ordered mutations, egress trace, and success return in sequence",
            ),
            _sub_result(
                "rust_failure_path",
                "sequence: 0xCAFEFEED" in rust_source
                and "timestamp: 0" in rust_source
                and "match status" in rust_source
                and "abi::K_OK" in rust_source
                and "panic!(" in rust_source,
                "userspace/core_service initializes the expected values, matches on K_OK, and has a heavy failure branch",
            ),
            _sub_result(
                "postcondition_asserts",
                "payload.sequence == 0xCAFEFEEE" in rust_source
                and "payload.timestamp == 0xDEADBEEF" in rust_source,
                "userspace/core_service documents the postconditions it expects after a successful heartbeat call",
            ),
            _sub_result(
                "serial_log_stability",
                'serial_write("SYSCALL[DEBUG_HEARTBEAT] Recv Seq: 0x")' in serial_source
                and 'serial_write("SYSCALL[DEBUG_HEARTBEAT] New Time: 0x")' in serial_source,
                "kernel/arch/x86_64/serial.odin provides the stable trace strings for future parsing",
            ),
        ]

        failing = [result["name"] for result in sub_results if result["status"] == "fail"]
        if failing:
            return ValidationResult.fail(
                code=EXECUTION_PROOF_INVALID,
                detail=f"Execution proof is incomplete: {failing}",
                action="Align the Odin arbiter order, Rust consumer checks, and stable serial log strings with the execution proof contract",
                meta={"sub_results": sub_results},
            )

        return ValidationResult(
            status="pass",
            code=OK,
            detail="Kernel and Rust sources prove the ordered heartbeat contract for the current runtime-trap implementation",
            meta={"sub_results": sub_results},
        )
