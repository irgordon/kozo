from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import EXECUTION_FOUNDATION_INVALID
from harness.validators_impl import entrypoint_validator
from harness.validators_impl.entrypoint_validator import ExecutionFoundationValidator

KOZO_NEGATIVE_COVERAGE = {
    "execution_foundation": {
        "missing_boot_start_symbol": "test_fails_when_boot_start_symbol_is_missing",
    }
}


class ExecutionFoundationValidatorTests(unittest.TestCase):
    def test_fails_when_boot_start_symbol_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            boot_path = root / "boot.asm"
            syscall_path = root / "syscall.asm"
            odin_path = root / "main.odin"
            boot_path.write_text("extern kernel_entry\n")
            syscall_path.write_text("global syscall_entry\ncall syscall_dispatch\n")
            odin_path.write_text('@(export)\nkernel_entry :: proc "c" () {}\n')

            original_boot = entrypoint_validator._BOOT_ASM
            original_syscall = entrypoint_validator._SYSCALL_ASM
            original_odin = entrypoint_validator._MAIN_ODIN
            entrypoint_validator._BOOT_ASM = boot_path
            entrypoint_validator._SYSCALL_ASM = syscall_path
            entrypoint_validator._MAIN_ODIN = odin_path
            try:
                result = ExecutionFoundationValidator().validate({})
            finally:
                entrypoint_validator._BOOT_ASM = original_boot
                entrypoint_validator._SYSCALL_ASM = original_syscall
                entrypoint_validator._MAIN_ODIN = original_odin

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, EXECUTION_FOUNDATION_INVALID)


if __name__ == "__main__":
    unittest.main()
