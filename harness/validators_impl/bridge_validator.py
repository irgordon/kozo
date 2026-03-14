from __future__ import annotations

import re
from pathlib import Path

from harness.codes import BRIDGE_ALIGNMENT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_SYSCALL_ASM = _ROOT / "kernel" / "arch" / "x86_64" / "syscall.asm"
_MAIN_ODIN = _ROOT / "kernel" / "main.odin"

_DISPATCH_SIGNATURE = re.compile(
    r'@\(export\)\s*syscall_dispatch\s*::\s*proc\s*"c"\s*\(\s*id:\s*abi\.K_SYSCALL_ID,\s*payload:\s*\^abi\.Heartbeat_Payload,\s*\)\s*->\s*abi\.K_STATUS',
    re.DOTALL,
)
_MOVE_RDI = re.compile(r"mov\s+rdi,\s*rax")
_MOVE_RSI = re.compile(r"mov\s+rsi,\s*rbx")
_CALL_TARGET = re.compile(r"call\s+syscall_dispatch")
_PUSH_RCX = re.compile(r"push\s+rcx")
_PUSH_R11 = re.compile(r"push\s+r11")
_POP_RCX = re.compile(r"pop\s+rcx")
_POP_R11 = re.compile(r"pop\s+r11")
_ALIGN_STACK = re.compile(r"sub\s+rsp,\s*8")


class BridgeAlignmentValidator(BaseValidator):
    name = "bridge_alignment"
    subsystem = "bridge_alignment"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        asm_source = _SYSCALL_ASM.read_text()
        odin_source = _MAIN_ODIN.read_text()

        if _DISPATCH_SIGNATURE.search(odin_source) is None:
            return ValidationResult.fail(
                code=BRIDGE_ALIGNMENT_INVALID,
                detail="Bridge alignment invalid: syscall_dispatch must export proc \"c\" (id: abi.K_SYSCALL_ID, payload: ^abi.Heartbeat_Payload) -> abi.K_STATUS",
                action="Align kernel/main.odin with the normative trap dispatcher signature",
            )

        checks = (
            (_MOVE_RDI, "syscall.asm must map rax into rdi before calling syscall_dispatch"),
            (_MOVE_RSI, "syscall.asm must map rbx into rsi before calling syscall_dispatch"),
            (_CALL_TARGET, "syscall.asm must call the exported syscall_dispatch symbol exactly"),
            (_PUSH_RCX, "syscall.asm must preserve rcx"),
            (_PUSH_R11, "syscall.asm must preserve r11"),
            (_POP_RCX, "syscall.asm must restore rcx"),
            (_POP_R11, "syscall.asm must restore r11"),
            (_ALIGN_STACK, "syscall.asm must realign rsp before the dispatcher call"),
        )

        for pattern, message in checks:
            if pattern.search(asm_source) is None:
                return ValidationResult.fail(
                    code=BRIDGE_ALIGNMENT_INVALID,
                    detail=f"Bridge alignment invalid: {message}",
                    action="Keep the assembly trap bridge aligned with ADR-0016 and the exported Odin signature",
                )

        return ValidationResult.pass_(code=OK, detail="Assembly ingress registers and the exported Odin dispatcher signature align with the trap-path contract")
