from __future__ import annotations

import re
from pathlib import Path

from harness.codes import OK, PROTOCOL_MISMATCH
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_HEADER_PATH = _ROOT / "contracts" / "kozo_abi.h"
_KERNEL_PATH = _ROOT / "kernel" / "main.odin"
_SERVICE_PATH = _ROOT / "userspace" / "core_service" / "src" / "main.rs"
_SYSCALL_PATTERN = re.compile(r"(K_SYSCALL_[A-Z0-9_]+)\s*=\s*(\d+)")
_KERNEL_CASE_PATTERN = re.compile(r"case\s+abi\.(K_SYSCALL_[A-Z0-9_]+):")
_RUST_SYSCALL_PATTERN = re.compile(r"abi::(K_SYSCALL_[A-Z0-9_]+)")


def _declared_syscalls() -> list[str]:
    return [name for name, _ in _SYSCALL_PATTERN.findall(_HEADER_PATH.read_text())]


def _kernel_dispatch_cases() -> set[str]:
    return set(_KERNEL_CASE_PATTERN.findall(_KERNEL_PATH.read_text()))


def _service_uses() -> tuple[bool, set[str]]:
    source = _SERVICE_PATH.read_text()
    return "abi::K_SYSCALL_ID" in source, set(_RUST_SYSCALL_PATTERN.findall(source))


class ProtocolValidator(BaseValidator):
    name = "protocol_alignment"
    subsystem = "protocol_alignment"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        declared = _declared_syscalls()
        kernel_cases = _kernel_dispatch_cases()
        uses_type, rust_syscalls = _service_uses()

        missing_cases = [name for name in declared if name not in kernel_cases]
        if missing_cases:
            return ValidationResult.fail(
                code=PROTOCOL_MISMATCH,
                detail=f"Protocol mismatch: kernel dispatcher is missing {missing_cases}",
                action="Add abi-prefixed syscall cases to kernel/main.odin",
            )

        if not uses_type or not rust_syscalls:
            return ValidationResult.fail(
                code=PROTOCOL_MISMATCH,
                detail="Protocol mismatch: core_service does not import and use an ABI syscall identifier",
                action="Use abi::K_SYSCALL_ID and at least one abi::K_SYSCALL_* constant in the Rust service",
            )

        return ValidationResult.pass_(code=OK, detail="Kernel and Rust protocol usage align with the ABI contract")
