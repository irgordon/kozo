from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import BOUNDED_PRIVILEGE_TRANSITION_PROBE_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.validators_impl import bounded_privilege_transition_probe_evidence as validator_module
from harness.validators_impl.bounded_privilege_transition_probe_evidence import (
    BoundedPrivilegeTransitionProbeEvidenceValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "bounded_privilege_transition_probe_evidence": {
        "transition_sequence_invalid": "test_fails_when_runtime_entry_precedes_ring0_return",
        "descriptor_setup_invalid": "test_fails_when_ltr_is_missing",
        "entry_frame_invalid": "test_fails_when_iretq_is_missing",
        "entry_geometry_invalid": "test_fails_when_return_vector_changes",
        "user_probe_invalid": "test_fails_when_cpl_check_is_missing",
        "ring3_serial_io_present": "test_fails_when_ring3_uses_port_io",
        "return_validation_invalid": "test_fails_when_saved_frame_validation_is_missing",
        "fault_halt_missing": "test_fails_when_fault_does_not_halt",
        "interrupts_enabled": "test_fails_when_sti_is_present",
        "linker_geometry_invalid": "test_fails_when_tss_assertion_is_missing",
        "missing_elf_symbol": "test_fails_when_return_handler_symbol_is_missing",
        "elf_geometry_invalid": "test_fails_when_return_stack_geometry_is_wrong",
        "missing_elf_evidence": "test_fails_when_iretq_is_missing_from_elf",
        "prohibited_instruction_present": "test_fails_when_syscall_is_present",
        "runtime_outcome_invalid": "test_fails_when_qemu_is_blocked",
        "metadata_log_mismatch": "test_fails_when_metadata_omits_ring3_marker",
        "runtime_marker_missing": "test_fails_when_serial_omits_ring0_marker",
        "runtime_marker_duplicate": "test_fails_when_ring3_marker_is_duplicated",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class BoundedPrivilegeTransitionProbeEvidenceTests(unittest.TestCase):
    def test_valid_evidence_passes(self):
        result = self.validate_fixture()
        self.assertEqual((result.status, result.code), ("pass", OK))

    def test_fails_when_runtime_entry_precedes_ring0_return(self):
        mutation = lambda text: text.replace(
            "    WRITE_COM1_MARKER ring0_return_ok_marker, ring0_return_ok_marker_end\n",
            "",
        )
        result = self.validate_fixture(mutate_boot=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "transition_sequence_invalid")

    def test_fails_when_ltr_is_missing(self):
        result = self.validate_fixture(mutate_privilege=lambda text: text.replace("    ltr ax\n", ""))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "descriptor_setup_invalid")

    def test_fails_when_iretq_is_missing(self):
        result = self.validate_fixture(mutate_privilege=lambda text: text.replace("    iretq\n", ""))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "entry_frame_invalid")

    def test_fails_when_return_vector_changes(self):
        result = self.validate_fixture(mutate_layout=lambda text: text.replace("0x81", "0x82"))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "entry_geometry_invalid")

    def test_fails_when_cpl_check_is_missing(self):
        result = self.validate_fixture(mutate_privilege=lambda text: text.replace("    mov ax, cs\n", "", 1))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "user_probe_invalid")

    def test_fails_when_ring3_uses_port_io(self):
        mutation = lambda text: text.replace("user_privilege_probe_start:\n", "user_privilege_probe_start:\n    out dx, al\n")
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "ring3_serial_io_present")

    def test_fails_when_saved_frame_validation_is_missing(self):
        mutation = lambda text: text.replace("    call validate_ring3_return_frame\n", "")
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "return_validation_invalid")

    def test_fails_when_fault_does_not_halt(self):
        mutation = lambda text: text.replace("    jmp boot_terminal_halt\n", "    ret\n", 1)
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "fault_halt_missing")

    def test_fails_when_sti_is_present(self):
        mutation = lambda text: text.replace("initialize_privilege_transition:\n", "initialize_privilege_transition:\n    sti\n")
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "interrupts_enabled")

    def test_fails_when_tss_assertion_is_missing(self):
        mutation = lambda text: text.replace("governed TSS must be exactly 104 bytes", "removed")
        result = self.validate_fixture(mutate_linker=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "linker_geometry_invalid")

    def test_fails_when_return_handler_symbol_is_missing(self):
        mutation = lambda report: mutate_symbol(report, "privilege_return_handler")
        result = self.validate_fixture(mutate_report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_elf_symbol")

    def test_fails_when_return_stack_geometry_is_wrong(self):
        def mutation(report):
            report["bounded_privilege_transition_probe"]["return_stack"]["size_bytes"] = 2048
            return report
        result = self.validate_fixture(mutate_report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "elf_geometry_invalid")

    def test_fails_when_iretq_is_missing_from_elf(self):
        def mutation(report):
            report["bounded_privilege_transition_probe"]["iretq_present"] = False
            return report
        result = self.validate_fixture(mutate_report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_elf_evidence")

    def test_fails_when_syscall_is_present(self):
        def mutation(report):
            report["bounded_privilege_transition_probe"]["prohibited_instructions"] = ["syscall"]
            return report
        result = self.validate_fixture(mutate_report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "prohibited_instruction_present")

    def test_fails_when_qemu_is_blocked(self):
        result = self.validate_fixture(mutate_metadata=lambda data: data | {"outcome": "blocked"})
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "runtime_outcome_invalid")

    def test_fails_when_metadata_omits_ring3_marker(self):
        marker = "KOZO_RING3_PROBE_OK"
        mutation = lambda data: data | {"observed_markers": [value for value in data["observed_markers"] if value != marker]}
        result = self.validate_fixture(mutate_metadata=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "metadata_log_mismatch")

    def test_fails_when_serial_omits_ring0_marker(self):
        mutation = lambda text: text.replace("KOZO_RING0_RETURN_OK\n", "")
        result = self.validate_fixture(mutate_serial=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "runtime_marker_missing")

    def test_fails_when_ring3_marker_is_duplicated(self):
        mutation = lambda text: text.replace("KOZO_RING3_PROBE_OK\n", "KOZO_RING3_PROBE_OK\nKOZO_RING3_PROBE_OK\n")
        result = self.validate_fixture(mutate_serial=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "runtime_marker_duplicate")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(mutate_privilege=lambda text: text.replace("    ltr ax\n", ""))
        self.assertEqual(result.code, BOUNDED_PRIVILEGE_TRANSITION_PROBE_EVIDENCE_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def assert_reason(self, result, reason):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], reason)

    def validate_fixture(
        self,
        mutate_boot=None,
        mutate_privilege=None,
        mutate_layout=None,
        mutate_linker=None,
        mutate_report=None,
        mutate_metadata=None,
        mutate_serial=None,
    ):
        with tempfile.TemporaryDirectory() as directory:
            paths = write_fixture(
                Path(directory),
                mutate_boot,
                mutate_privilege,
                mutate_layout,
                mutate_linker,
                mutate_report,
                mutate_metadata,
                mutate_serial,
            )
            original = patch_paths(paths)
            try:
                return BoundedPrivilegeTransitionProbeEvidenceValidator().validate({})
            finally:
                restore_paths(original)


def write_fixture(root, mutate_boot, mutate_privilege, mutate_layout, mutate_linker, mutate_report, mutate_metadata, mutate_serial):
    paths = {name: root / filename for name, filename in {
        "contract": "contract.json",
        "boot": "boot.asm",
        "privilege": "privilege.asm",
        "layout": "layout.inc",
        "linker": "kernel.ld",
        "report": "kernel_elf_report.json",
        "metadata": "qemu_smoke.metadata.json",
        "serial": "qemu_smoke.log",
    }.items()}
    paths["contract"].write_text(validator_module._CONTRACT_PATH.read_text())
    write_mutated(paths["boot"], validator_module._BOOT_PATH.read_text(), mutate_boot)
    write_mutated(paths["privilege"], validator_module._PRIVILEGE_PATH.read_text(), mutate_privilege)
    write_mutated(paths["layout"], validator_module._LAYOUT_PATH.read_text(), mutate_layout)
    write_mutated(paths["linker"], validator_module._LINKER_PATH.read_text(), mutate_linker)
    report = valid_report()
    paths["report"].write_text(json.dumps(mutate_report(report) if mutate_report else report))
    markers = list(get_smoke_marker_order())
    metadata = {"outcome": "pass", "observed_markers": markers}
    paths["metadata"].write_text(json.dumps(mutate_metadata(metadata) if mutate_metadata else metadata))
    serial = "\n".join(markers) + "\n"
    paths["serial"].write_text(mutate_serial(serial) if mutate_serial else serial)
    return paths


def valid_report():
    symbols = {
        name: {"present": True, "address": f"0xffffffff802{index:05x}"}
        for index, name in enumerate(validator_module._REQUIRED_SYMBOLS, start=1)
    }
    record = {
        "symbols": symbols,
        **{
            name: {
                "size_bytes": size,
                "required_alignment_bytes": alignment,
                "start_aligned": True,
            }
            for name, (size, alignment) in validator_module._GEOMETRY.items()
        },
        **{
            field: True
            for field in (
                "pre_odin_call_order_valid",
                "lgdt_present",
                "sgdt_present",
                "ltr_present",
                "str_present",
                "lidt_present",
                "sidt_present",
                "iretq_present",
                "int_0x81_present",
                "handler_continuation_jump_present",
                "fault_halt_paths_present",
            )
        },
        "prohibited_instructions": [],
    }
    return {"bounded_privilege_transition_probe": record}


def mutate_symbol(report, symbol):
    report["bounded_privilege_transition_probe"]["symbols"][symbol]["present"] = False
    return report


def write_mutated(path, text, mutation):
    path.write_text(mutation(text) if mutation else text)


def patch_paths(paths):
    mapping = {
        "_CONTRACT_PATH": "contract",
        "_BOOT_PATH": "boot",
        "_PRIVILEGE_PATH": "privilege",
        "_LAYOUT_PATH": "layout",
        "_LINKER_PATH": "linker",
        "_ELF_REPORT_PATH": "report",
        "_METADATA_PATH": "metadata",
        "_SERIAL_PATH": "serial",
    }
    original = {}
    for attribute, name in mapping.items():
        original[attribute] = getattr(validator_module, attribute)
        setattr(validator_module, attribute, paths[name])
    return original


def restore_paths(original):
    for attribute, value in original.items():
        setattr(validator_module, attribute, value)


if __name__ == "__main__":
    unittest.main()
