from __future__ import annotations

import re
from pathlib import Path

from harness.codes import OK, PROTOCOL_MISMATCH
from harness.validator import BaseValidator, ValidationResult
from harness.validators_impl.runtime_trap_path import runtime_trap_path_observations

_ROOT = Path(__file__).resolve().parents[2]
_HEADER_PATH = _ROOT / "contracts" / "kozo_abi.h"
_KERNEL_PATH = _ROOT / "kernel" / "main.odin"
_SERVICE_PATH = _ROOT / "userspace" / "core_service" / "src" / "main.rs"
_SYSCALL_PATTERN = re.compile(r"(K_SYSCALL_[A-Z0-9_]+)\s*=\s*(\d+)")
_KERNEL_CASE_PATTERN = re.compile(r"case\s+abi\.(K_SYSCALL_[A-Z0-9_]+):")
_HEARTBEAT_REF = "abi::K_SYSCALL_DEBUG_HEARTBEAT"


def _declared_syscalls() -> list[str]:
    return [name for name, _ in _SYSCALL_PATTERN.findall(_HEADER_PATH.read_text())]


def _kernel_dispatch_cases() -> set[str]:
    return set(_KERNEL_CASE_PATTERN.findall(_KERNEL_PATH.read_text()))


class ProtocolContractValidator(BaseValidator):
    name = "protocol_contract_alignment"
    subsystem = "protocol_contract_alignment"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        declared = _declared_syscalls()
        kernel_cases = _kernel_dispatch_cases()
        service_source = _SERVICE_PATH.read_text()
        trap_path = runtime_trap_path_observations(service_source)

        missing_cases = [name for name in declared if name not in kernel_cases]
        if missing_cases:
            return ValidationResult.fail(
                code=PROTOCOL_MISMATCH,
                detail=f"Protocol mismatch: kernel dispatcher is missing {missing_cases}",
                action="Add abi-prefixed syscall cases to kernel/main.odin",
            )

        if _HEARTBEAT_REF not in service_source:
            return ValidationResult.fail(
                code=PROTOCOL_MISMATCH,
                detail="Protocol mismatch: core_service does not reference abi::K_SYSCALL_DEBUG_HEARTBEAT",
                action="Use the generated heartbeat syscall constant in the Rust service",
            )

        if trap_path["has_local_stub"]:
            return ValidationResult.fail(
                code=PROTOCOL_MISMATCH,
                detail="Protocol mismatch: core_service still defines a local syscall stub instead of crossing the assembly bridge",
                action="Remove the local Rust stub and route the heartbeat through syscall_entry",
            )

        if not trap_path["has_extern_decl"] or not trap_path["has_extern_call"]:
            return ValidationResult.fail(
                code=PROTOCOL_MISMATCH,
                detail="Protocol mismatch: core_service does not declare and call the extern syscall_entry bridge",
                action='Declare extern "C" fn syscall_entry(...) and route the heartbeat through it',
            )

        return ValidationResult.pass_(
            code=OK,
            detail="Kernel and Rust protocol contracts align across the assembly bridge boundary",
        )
