from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import BRIDGE_ALIGNMENT_INVALID, OK
from harness.validators_impl import bridge_validator
from harness.validators_impl.bridge_validator import BridgeAlignmentValidator

KOZO_NEGATIVE_COVERAGE = {
    "bridge_alignment": {
        "dead_snippets_outside_entry": "test_fails_when_anchors_exist_only_outside_syscall_entry",
        "out_of_order_anchors": "test_fails_when_required_anchors_are_out_of_order",
        "missing_dispatcher_handoff": "test_fails_when_dispatcher_handoff_is_missing_from_live_block",
        "missing_odin_dispatcher_signature": "test_fails_when_odin_dispatcher_signature_is_missing",
        "missing_entry_block": "test_missing_entry_block_diagnostic_names_entry_contract",
    }
}


class BridgeAlignmentValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.asm_source = bridge_validator._SYSCALL_ASM.read_text()
        self.odin_source = bridge_validator._MAIN_ODIN.read_text()

    def validate_sources(self, asm_source: str, odin_source: str):
        with tempfile.TemporaryDirectory() as temporary_directory:
            asm_path = Path(temporary_directory) / "syscall.asm"
            odin_path = Path(temporary_directory) / "main.odin"
            asm_path.write_text(asm_source)
            odin_path.write_text(odin_source)

            original_asm_path = bridge_validator._SYSCALL_ASM
            original_odin_path = bridge_validator._MAIN_ODIN
            bridge_validator._SYSCALL_ASM = asm_path
            bridge_validator._MAIN_ODIN = odin_path
            try:
                return BridgeAlignmentValidator().validate({})
            finally:
                bridge_validator._SYSCALL_ASM = original_asm_path
                bridge_validator._MAIN_ODIN = original_odin_path

    def test_passes_when_live_entry_block_has_ordered_bridge_anchors(self):
        result = self.validate_sources(self.asm_source, self.odin_source)

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_anchors_exist_only_outside_syscall_entry(self):
        asm_source = (
            "bits 64\n"
            "extern syscall_dispatch\n"
            "global syscall_entry\n"
            "section .text\n"
            "syscall_entry:\n"
            "    ret\n"
            "dead_bridge:\n"
            "    push rbx\n"
            "    push r11\n"
            "    push rcx\n"
            "    sub rsp, 8\n"
            "    mov rax, rdi\n"
            "    mov rbx, rsi\n"
            "    mov rdi, rax\n"
            "    mov rsi, rbx\n"
            "    call syscall_dispatch\n"
            "    add rsp, 8\n"
            "    pop rcx\n"
            "    pop r11\n"
            "    pop rbx\n"
            "    ret\n"
        )

        result = self.validate_sources(asm_source, self.odin_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, BRIDGE_ALIGNMENT_INVALID)
        self.assertEqual(result.meta["reason"], "dead_snippet_outside_entry_block")
        self.assertEqual(result.meta["contract_field"], "preserve_rbx")

    def test_fails_when_required_anchors_are_out_of_order(self):
        asm_source = self.asm_source.replace(
            "    push r11\n    push rcx\n",
            "    push rcx\n    push r11\n",
        )

        result = self.validate_sources(asm_source, self.odin_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "out_of_order_assembly_anchor")
        self.assertEqual(result.meta["contract_field"], "preserve_rcx")

    def test_fails_when_dispatcher_handoff_is_missing_from_live_block(self):
        asm_source = self.asm_source.replace(
            "    call syscall_dispatch\n",
            "",
        )

        result = self.validate_sources(asm_source, self.odin_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_assembly_anchor")
        self.assertEqual(result.meta["contract_field"], "dispatcher_handoff")

    def test_fails_when_odin_dispatcher_signature_is_missing(self):
        odin_source = self.odin_source.replace(
            '@(export)\nsyscall_dispatch :: proc "c"',
            'syscall_dispatch :: proc "odin"',
        )

        result = self.validate_sources(self.asm_source, odin_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_odin_dispatcher_contract")
        self.assertEqual(result.meta["contract_field"], "odin_dispatcher_signature")

    def test_missing_entry_block_diagnostic_names_entry_contract(self):
        asm_source = self.asm_source.replace("syscall_entry:", "not_syscall_entry:")

        result = self.validate_sources(asm_source, self.odin_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_entry_block")
        self.assertEqual(result.meta["contract_field"], "syscall_entry_block")


if __name__ == "__main__":
    unittest.main()
