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
_STUB_MODE_MARKER = "// KOZO: STUB MODE — no real syscall boundary"
_HEARTBEAT_REF = "abi::K_SYSCALL_DEBUG_HEARTBEAT"
_STUB_SIGNATURE = "fn invoke_heartbeat_stub("
_STUB_CALL = "invoke_heartbeat_stub(syscall, &mut payload)"
_EXTERN_BLOCK = re.compile(r'extern\s*"C"\s*\{(?P<body>.*?)\}', re.DOTALL)
_EXTERN_SYSCALL_FN = re.compile(r"fn\s+syscall_entry\s*\(")
_EXTERN_SYSCALL_CALL = re.compile(r"syscall_entry\s*\(")


def _declared_syscalls() -> list[str]:
    return [name for name, _ in _SYSCALL_PATTERN.findall(_HEADER_PATH.read_text())]


def _kernel_dispatch_cases() -> set[str]:
    return set(_KERNEL_CASE_PATTERN.findall(_KERNEL_PATH.read_text()))


def _service_mode() -> dict[str, bool]:
    source = _SERVICE_PATH.read_text()
    extern_block = _EXTERN_BLOCK.search(source)
    has_extern_decl = extern_block is not None and _EXTERN_SYSCALL_FN.search(extern_block.group("body")) is not None
    extern_call_count = len(_EXTERN_SYSCALL_CALL.findall(source))

    return {
        "has_heartbeat_ref": _HEARTBEAT_REF in source,
        "has_stub_marker": _STUB_MODE_MARKER in source,
        "has_stub": _STUB_SIGNATURE in source,
        "has_stub_call": _STUB_CALL in source,
        "has_extern_decl": has_extern_decl,
        "has_extern_call": extern_call_count > (1 if has_extern_decl else 0),
    }


class ProtocolContractValidator(BaseValidator):
    name = "protocol_contract_alignment"
    subsystem = "protocol_contract_alignment"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        declared = _declared_syscalls()
        kernel_cases = _kernel_dispatch_cases()
        service_mode = _service_mode()

        missing_cases = [name for name in declared if name not in kernel_cases]
        if missing_cases:
            return ValidationResult.fail(
                code=PROTOCOL_MISMATCH,
                detail=f"Protocol mismatch: kernel dispatcher is missing {missing_cases}",
                action="Add abi-prefixed syscall cases to kernel/main.odin",
            )

        if not service_mode["has_heartbeat_ref"]:
            return ValidationResult.fail(
                code=PROTOCOL_MISMATCH,
                detail="Protocol mismatch: core_service does not reference abi::K_SYSCALL_DEBUG_HEARTBEAT",
                action="Use the generated heartbeat syscall constant in the Rust service",
            )

        if service_mode["has_stub"] and not service_mode["has_stub_marker"]:
            return ValidationResult.fail(
                code=PROTOCOL_MISMATCH,
                detail="Protocol mismatch: core_service defines a local syscall stub without the required explicit STUB MODE marker",
                action="Add the KOZO STUB MODE marker or replace the stub with a real extern syscall entry call",
            )

        if service_mode["has_stub"] and service_mode["has_extern_decl"]:
            return ValidationResult.fail(
                code=PROTOCOL_MISMATCH,
                detail="Protocol mismatch: core_service mixes stub mode and extern syscall mode",
                action="Keep exactly one syscall integration mode active in the Rust service",
            )

        if service_mode["has_stub_marker"]:
            if not service_mode["has_stub"] or not service_mode["has_stub_call"]:
                return ValidationResult.fail(
                    code=PROTOCOL_MISMATCH,
                    detail="Protocol mismatch: STUB MODE is declared but the Rust service does not route the heartbeat through the marked local stub",
                    action="Keep the explicit stub marker paired with the local heartbeat stub implementation and call site",
                )

            return ValidationResult.pass_(
                code=OK,
                detail="Kernel and Rust protocol contracts align in explicit STUB MODE",
            )

        if not service_mode["has_extern_decl"] or not service_mode["has_extern_call"]:
            return ValidationResult.fail(
                code=PROTOCOL_MISMATCH,
                detail="Protocol mismatch: core_service does not call an extern syscall entry and is not explicitly marked as stub mode",
                action='Either declare STUB MODE for the local stub or call the exported syscall entry via extern "C"',
            )

        return ValidationResult.pass_(
            code=OK,
            detail="Kernel and Rust protocol contracts align across the real syscall boundary",
        )
