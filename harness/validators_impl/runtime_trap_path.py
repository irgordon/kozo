from __future__ import annotations

import re
from pathlib import Path

from harness.codes import OK, RUNTIME_TRAP_PATH_INVALID
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_SERVICE_PATH = _ROOT / "userspace" / "core_service" / "src" / "main.rs"
_SYSCALL_ASM = _ROOT / "kernel" / "arch" / "x86_64" / "syscall.asm"

_LOCAL_STUB_SIGNATURE = "fn invoke_heartbeat_stub("
_STUB_MODE_MARKER = "STUB MODE"
_EXTERN_BLOCK = re.compile(r'extern\s*"C"\s*\{(?P<body>.*?)\}', re.DOTALL)
_EXTERN_SYSCALL_FN = re.compile(
    r"fn\s+syscall_entry\s*\(\s*id\s*:\s*u64\s*,\s*payload\s*:\s*\*mut\s+abi::HeartbeatPayload\s*\)\s*->\s*u64\s*;",
)
_EXTERN_SYSCALL_CALL = re.compile(r"syscall_entry\s*\(")
_ASM_GLOBAL = re.compile(r"global\s+syscall_entry")
_ASM_LABEL = re.compile(r"^syscall_entry:\s*$", re.MULTILINE)
_ASM_CALL_DISPATCH = re.compile(r"call\s+syscall_dispatch")
_ASM_MOVE_ID_IN = re.compile(r"mov\s+rax,\s*rdi")
_ASM_MOVE_PAYLOAD_IN = re.compile(r"mov\s+rbx,\s*rsi")
_ASM_MOVE_ID_OUT = re.compile(r"mov\s+rdi,\s*rax")
_ASM_MOVE_PAYLOAD_OUT = re.compile(r"mov\s+rsi,\s*rbx")


def runtime_trap_path_observations(rust_source: str, asm_source: str | None = None) -> dict[str, bool]:
    extern_block = _EXTERN_BLOCK.search(rust_source)
    has_extern_decl = extern_block is not None and _EXTERN_SYSCALL_FN.search(extern_block.group("body")) is not None
    call_count = len(_EXTERN_SYSCALL_CALL.findall(rust_source))
    observations = {
        "has_local_stub": _LOCAL_STUB_SIGNATURE in rust_source,
        "has_stub_marker": _STUB_MODE_MARKER in rust_source,
        "has_extern_decl": has_extern_decl,
        "has_extern_call": call_count > (1 if has_extern_decl else 0),
    }

    if asm_source is None:
        return observations

    observations.update(
        {
            "has_bridge_global": _ASM_GLOBAL.search(asm_source) is not None,
            "has_bridge_label": _ASM_LABEL.search(asm_source) is not None,
            "has_dispatch_call": _ASM_CALL_DISPATCH.search(asm_source) is not None,
            "maps_c_abi_id_to_trap": _ASM_MOVE_ID_IN.search(asm_source) is not None,
            "maps_c_abi_payload_to_trap": _ASM_MOVE_PAYLOAD_IN.search(asm_source) is not None,
            "maps_trap_id_to_dispatch": _ASM_MOVE_ID_OUT.search(asm_source) is not None,
            "maps_trap_payload_to_dispatch": _ASM_MOVE_PAYLOAD_OUT.search(asm_source) is not None,
        }
    )
    return observations


class RuntimeTrapPathValidator(BaseValidator):
    name = "runtime_trap_path"
    subsystem = "runtime_trap_path"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        observations = runtime_trap_path_observations(
            _SERVICE_PATH.read_text(),
            _SYSCALL_ASM.read_text(),
        )

        if observations["has_local_stub"]:
            return ValidationResult.fail(
                code=RUNTIME_TRAP_PATH_INVALID,
                detail="Runtime trap path invalid: core_service still defines a local heartbeat syscall stub",
                action="Remove the local Rust stub and route the heartbeat through syscall_entry",
            )

        if observations["has_stub_marker"]:
            return ValidationResult.fail(
                code=RUNTIME_TRAP_PATH_INVALID,
                detail="Runtime trap path invalid: core_service still advertises STUB MODE after the runtime trap path phase",
                action="Remove the stub-mode classification once the extern bridge call is in place",
            )

        if not observations["has_extern_decl"] or not observations["has_extern_call"]:
            return ValidationResult.fail(
                code=RUNTIME_TRAP_PATH_INVALID,
                detail="Runtime trap path invalid: core_service must declare and call extern syscall_entry(id: u64, payload: *mut abi::HeartbeatPayload) -> u64",
                action='Declare extern "C" syscall_entry and route the heartbeat request through it',
            )

        asm_requirements = (
            ("has_bridge_global", "syscall.asm must declare global syscall_entry"),
            ("has_bridge_label", "syscall.asm must define the syscall_entry label"),
            ("has_dispatch_call", "syscall.asm must call syscall_dispatch"),
            ("maps_c_abi_id_to_trap", "syscall.asm must map the incoming C-ABI id from rdi into rax"),
            ("maps_c_abi_payload_to_trap", "syscall.asm must map the incoming C-ABI payload pointer from rsi into rbx"),
            ("maps_trap_id_to_dispatch", "syscall.asm must map the trap id from rax into rdi before calling syscall_dispatch"),
            ("maps_trap_payload_to_dispatch", "syscall.asm must map the trap payload pointer from rbx into rsi before calling syscall_dispatch"),
        )

        for field_name, detail in asm_requirements:
            if not observations[field_name]:
                return ValidationResult.fail(
                    code=RUNTIME_TRAP_PATH_INVALID,
                    detail=f"Runtime trap path invalid: {detail}",
                    action="Keep the Rust call site and assembly bridge aligned with the runtime trap contract",
                )

        return ValidationResult.pass_(
            code=OK,
            detail="Rust calls extern syscall_entry and the assembly bridge routes the request into syscall_dispatch",
        )
