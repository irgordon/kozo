from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from harness.codes import EXECUTION_FOUNDATION_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_BOOT_ASM = _ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_SYSCALL_ASM = _ROOT / "kernel" / "arch" / "x86_64" / "syscall.asm"
_MAIN_ODIN = _ROOT / "kernel" / "main.odin"


def _contains(path: Path, needle: str) -> bool:
    return needle in path.read_text()


def _validate_sources() -> tuple[bool, str]:
    if not _contains(_BOOT_ASM, "global _start"):
        return False, "boot.asm must declare global _start"
    if not _contains(_BOOT_ASM, "extern kernel_entry"):
        return False, "boot.asm must reference kernel_entry"
    if not _contains(_SYSCALL_ASM, "global syscall_entry"):
        return False, "syscall.asm must declare global syscall_entry"
    if not _contains(_SYSCALL_ASM, "call syscall_dispatch"):
        return False, "syscall.asm must call syscall_dispatch"
    main_source = _MAIN_ODIN.read_text()
    if "@(export)" not in main_source or 'kernel_entry :: proc "c" ()' not in main_source:
        return False, "kernel/main.odin must export kernel_entry with the c calling convention"
    return True, "Source bridge declarations are present"


def _can_attempt_symbol_check() -> bool:
    return shutil.which("nasm") is not None and shutil.which("nm") is not None


def _symbol_check() -> tuple[bool, str]:
    if not _can_attempt_symbol_check():
        return True, "Source bridge declarations are present; symbol check skipped because nasm or nm is unavailable"

    with tempfile.TemporaryDirectory(prefix="kozo-entrypoint-") as tmp_dir:
        output_path = Path(tmp_dir) / "kernel.o"
        build_cmd = [
            "odin",
            "build",
            str(_ROOT / "kernel"),
            "-build-mode:obj",
            f"-out:{output_path}",
        ]
        build_run = subprocess.run(build_cmd, cwd=_ROOT, capture_output=True, text=True)
        if build_run.returncode != 0:
            return False, f"odin build kernel -build-mode:obj failed: {build_run.stderr.strip() or build_run.stdout.strip()}"

        nm_run = subprocess.run(["nm", "-g", str(output_path)], cwd=_ROOT, capture_output=True, text=True)
        if nm_run.returncode != 0:
            return False, f"nm -g failed: {nm_run.stderr.strip() or nm_run.stdout.strip()}"

        output = nm_run.stdout
        for symbol in ("_start", "kernel_entry", "syscall_entry"):
            if symbol not in output:
                return False, f"kernel object is missing required symbol {symbol!r}"
        return True, "Source bridge declarations and object symbols are present"


class ExecutionFoundationValidator(BaseValidator):
    name = "execution_foundation"
    subsystem = "execution_foundation"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        ok, detail = _validate_sources()
        if not ok:
            return ValidationResult.fail(
                code=EXECUTION_FOUNDATION_INVALID,
                detail=detail,
                action="Align the assembly bridge and exported Odin entry symbols with the boot foundation contract",
            )

        ok, detail = _symbol_check()
        if not ok:
            return ValidationResult.fail(
                code=EXECUTION_FOUNDATION_INVALID,
                detail=detail,
                action="Ensure the kernel object can expose _start, kernel_entry, and syscall_entry when the assembler is available",
            )

        return ValidationResult.pass_(code=OK, detail=detail)
