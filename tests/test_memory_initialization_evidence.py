from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness import memory_initialization_evidence_contract as contract_module
from harness.codes import MEMORY_INITIALIZATION_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validators_impl import memory_initialization_evidence as validator_module
from harness.validators_impl.memory_initialization_evidence import MemoryInitializationEvidenceValidator

KOZO_NEGATIVE_COVERAGE = {
    "memory_initialization_evidence": {
        "missing_region_symbol": "test_fails_when_region_symbol_is_missing",
        "wrong_region_size": "test_fails_when_region_size_is_wrong",
        "wrong_region_alignment": "test_fails_when_region_alignment_is_wrong",
        "binary_region_mismatch": "test_fails_when_binary_region_size_mismatches_contract",
        "partial_zero_fill": "test_fails_when_zero_fill_is_partial",
        "probe_out_of_bounds": "test_fails_when_probe_is_out_of_bounds",
        "wrong_probe_width": "test_fails_when_probe_width_is_wrong",
        "missing_readback_comparison": "test_fails_when_readback_comparison_is_missing",
        "missing_restore": "test_fails_when_restore_is_missing",
        "marker_before_probe": "test_fails_when_marker_precedes_probe",
        "missing_marker": "test_fails_when_marker_is_missing",
        "halt_before_marker": "test_fails_when_halt_precedes_marker",
        "fallthrough_after_marker": "test_fails_when_fallthrough_follows_halt",
        "qemu_evidence_mismatch": "test_fails_when_qemu_metadata_omits_memory_marker",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class MemoryInitializationEvidenceValidatorTests(unittest.TestCase):
    def test_valid_implementation_passes(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_region_symbol_is_missing(self):
        result = self.validate_fixture(mutate_source=remove_text("global boot_memory_region\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_region_symbol", "controlled_region.start_symbol")

    def test_fails_when_region_size_is_wrong(self):
        result = self.validate_fixture(mutate_source=replace_text("resb 4096", "resb 2048"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_region_geometry", "controlled_region")

    def test_fails_when_region_alignment_is_wrong(self):
        result = self.validate_fixture(mutate_source=replace_text("align 4096", "align 2048"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_region_geometry", "controlled_region")

    def test_fails_when_binary_region_size_mismatches_contract(self):
        result = self.validate_fixture(
            mutate_report=lambda report: report | {
                "memory_evidence_region": report["memory_evidence_region"] | {"size_bytes": 2048}
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "binary_region_mismatch", "controlled_region")

    def test_fails_when_zero_fill_is_partial(self):
        result = self.validate_fixture(mutate_source=replace_text("mov ecx, 512", "mov ecx, 511"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "partial_zero_fill", "initialization_operation.coverage")

    def test_fails_when_probe_is_out_of_bounds(self):
        result = self.validate_fixture(
            mutate_source=replace_text(
                "cmp qword [rel boot_memory_region], 0",
                "cmp qword [rel boot_memory_region + 4096], 0",
                count=1,
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_probe_sequence", "survival_probe.required_steps")

    def test_fails_when_probe_width_is_wrong(self):
        result = self.validate_fixture(mutate_source=replace_text("mov qword [rel boot_memory_region], rax", "mov dword [rel boot_memory_region], eax"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_probe_sequence", "survival_probe.required_steps")

    def test_fails_when_readback_comparison_is_missing(self):
        result = self.validate_fixture(mutate_source=remove_text("    cmp rdx, rax\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_probe_sequence", "survival_probe.required_steps")

    def test_fails_when_restore_is_missing(self):
        result = self.validate_fixture(mutate_source=remove_text("    mov qword [rel boot_memory_region], 0\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_probe_sequence", "survival_probe.required_steps")

    def test_fails_when_marker_precedes_probe(self):
        result = self.validate_fixture(mutate_source=move_marker_after_stack)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "marker_order_mismatch", "marker_placement")

    def test_fails_when_marker_is_missing(self):
        result = self.validate_fixture(mutate_source=remove_memory_marker)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_marker", "marker_placement.reserved_marker")

    def test_fails_when_halt_precedes_marker(self):
        result = self.validate_fixture(mutate_source=move_halt_before_marker)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "halt_before_marker", "marker_placement.required_before")

    def test_fails_when_fallthrough_follows_halt(self):
        result = self.validate_fixture(mutate_source=insert_instruction_after_halt_loop)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "fallthrough_after_marker", "marker_placement.required_before")

    def test_fails_when_qemu_metadata_omits_memory_marker(self):
        result = self.validate_fixture(mutate_metadata=lambda metadata: metadata | {"observed_markers": list(get_smoke_marker_order()[:-1])})

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "qemu_evidence_mismatch", "qemu_smoke.observed_markers")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(mutate_source=remove_text("global boot_memory_region_end\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_region_symbol", "controlled_region.end_symbol")
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(self, *, mutate_source=None, mutate_metadata=None, mutate_report=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture(root, mutate_source, mutate_metadata, mutate_report)
            old_paths = patch_paths(root, paths)
            try:
                return MemoryInitializationEvidenceValidator().validate({})
            finally:
                restore_paths(old_paths)

    def assert_failure(self, result, reason: str, field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, MEMORY_INITIALIZATION_EVIDENCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def write_fixture(root: Path, mutate_source, mutate_metadata, mutate_report) -> dict[str, Path]:
    contract_path = root / "contracts" / "memory_initialization_evidence_contract.v0.json"
    source_path = root / "kernel" / "arch" / "x86_64" / "boot.asm"
    report_path = root / "artifacts" / "runtime" / "kernel_elf_report.json"
    metadata_path = root / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
    serial_path = root / "artifacts" / "runtime" / "qemu_smoke.log"
    for path in (contract_path, source_path, report_path, metadata_path, serial_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(contract_module.CONTRACT_PATH.read_text())
    source = validator_module._BOOT_ASM_PATH.read_text()
    source_path.write_text(mutate_source(source) if mutate_source else source)
    report = valid_elf_report()
    report_path.write_text(json.dumps(mutate_report(report) if mutate_report else report))
    metadata = valid_metadata()
    metadata_path.write_text(json.dumps(mutate_metadata(metadata) if mutate_metadata else metadata))
    serial_path.write_text("\n".join(get_smoke_marker_order()) + "\n")
    return {"contract": contract_path, "report": report_path, "metadata": metadata_path, "serial": serial_path}


def valid_elf_report() -> dict[str, object]:
    return {
        "memory_evidence_region": {
            "start_symbol": "boot_memory_region",
            "end_symbol": "boot_memory_region_end",
            "start_address": "0xffffffff8020a000",
            "end_address": "0xffffffff8020b000",
            "size_bytes": 4096,
            "required_alignment_bytes": 4096,
            "start_aligned": True,
        }
    }


def valid_metadata() -> dict[str, object]:
    return {
        "outcome": "pass",
        "blocker_category": "none",
        "expected_marker": get_expected_smoke_marker(),
        "observed_markers": list(get_smoke_marker_order()),
    }


def patch_paths(root: Path, paths: dict[str, Path]):
    old = (
        validator_module._CONTRACT_PATH,
        validator_module._ELF_REPORT_PATH,
        validator_module._METADATA_PATH,
        validator_module._SERIAL_LOG_PATH,
        contract_module.ROOT,
    )
    validator_module._CONTRACT_PATH = paths["contract"]
    validator_module._ELF_REPORT_PATH = paths["report"]
    validator_module._METADATA_PATH = paths["metadata"]
    validator_module._SERIAL_LOG_PATH = paths["serial"]
    contract_module.ROOT = root
    return old


def restore_paths(old):
    (
        validator_module._CONTRACT_PATH,
        validator_module._ELF_REPORT_PATH,
        validator_module._METADATA_PATH,
        validator_module._SERIAL_LOG_PATH,
        contract_module.ROOT,
    ) = old


def replace_text(old: str, new: str, count: int = -1):
    return lambda source: source.replace(old, new, count)


def remove_text(value: str):
    return replace_text(value, "")


def move_marker_after_stack(source: str) -> str:
    marker = "    WRITE_COM1_MARKER memory_init_marker, memory_init_marker_end\n"
    source = source.replace(marker, "")
    stack = "    WRITE_COM1_MARKER stack_init_marker, stack_init_marker_end\n"
    return source.replace(stack, stack + marker)


def remove_memory_marker(source: str) -> str:
    source = source.replace('memory_init_marker:\n    db "KOZO_MEMORY_INIT_OK", 13, 10\nmemory_init_marker_end:\n\n', "")
    return source.replace("    WRITE_COM1_MARKER memory_init_marker, memory_init_marker_end\n", "")


def move_halt_before_marker(source: str) -> str:
    marker = "    WRITE_COM1_MARKER memory_init_marker, memory_init_marker_end\n"
    return source.replace(marker, "    hlt\n" + marker, 1)


def insert_instruction_after_halt_loop(source: str) -> str:
    boundary = "    jmp .halt\n\nruntime_serial_write_init_marker:"
    replacement = "    jmp .halt\n    nop\n\nruntime_serial_write_init_marker:"
    return source.replace(boundary, replacement)


if __name__ == "__main__":
    unittest.main()
