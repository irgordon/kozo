from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness import cpu_extended_state_initialization_contract as contract_module
from harness.codes import CPU_EXTENDED_STATE_INITIALIZATION_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validators_impl import cpu_extended_state_initialization_evidence as validator_module
from harness.validators_impl.cpu_extended_state_initialization_evidence import (
    CpuExtendedStateInitializationEvidenceValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "cpu_extended_state_initialization_evidence": {
        "initialization_order_invalid": "test_fails_when_odin_entry_precedes_cpu_initialization",
        "missing_cpuid_check": "test_fails_when_cpuid_check_is_missing",
        "missing_control_readback": "test_fails_when_cr0_readback_is_missing",
        "missing_x87_initialization": "test_fails_when_fninit_is_missing",
        "missing_sse_initialization": "test_fails_when_mxcsr_initialization_is_missing",
        "invalid_simd_probe": "test_fails_when_simd_result_comparison_is_missing",
        "failure_path_reaches_success": "test_fails_when_failure_branch_is_missing",
        "missing_halt_convergence": "test_fails_when_halt_back_edge_is_missing",
        "avx_instruction_present": "test_fails_when_avx_instruction_is_present",
        "missing_elf_symbol": "test_fails_when_initialization_symbol_is_missing",
        "missing_elf_evidence": "test_fails_when_cpuid_is_missing_from_elf_evidence",
        "invalid_probe_geometry": "test_fails_when_probe_buffer_geometry_is_wrong",
        "metadata_log_mismatch": "test_fails_when_runtime_metadata_omits_simd_marker",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class CpuExtendedStateInitializationEvidenceValidatorTests(unittest.TestCase):
    def test_valid_evidence_passes(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_odin_entry_precedes_cpu_initialization(self):
        result = self.validate_fixture(mutate_source=move_runtime_entry_before_cpu)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "initialization_order_invalid", "execution_point")

    def test_fails_when_cpuid_check_is_missing(self):
        result = self.validate_fixture(mutate_source=remove_text("    cpuid\n", count=1))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_cpuid_check", "required_cpu_features")

    def test_fails_when_cr0_readback_is_missing(self):
        result = self.validate_fixture(mutate_source=remove_second_occurrence("    mov rax, cr0\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_control_readback", "cr4_policy.readback_required")

    def test_fails_when_fninit_is_missing(self):
        result = self.validate_fixture(mutate_source=remove_text("    fninit\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_x87_initialization", "x87_initialization")

    def test_fails_when_mxcsr_initialization_is_missing(self):
        result = self.validate_fixture(mutate_source=remove_text("    ldmxcsr [rel default_mxcsr]\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_sse_initialization", "sse_initialization")

    def test_fails_when_simd_result_comparison_is_missing(self):
        result = self.validate_fixture(mutate_source=remove_text("    cmp qword [rel simd_probe_result + 8], rax\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_simd_probe", "simd_probe")

    def test_fails_when_probe_marker_precedes_comparison(self):
        result = self.validate_fixture(mutate_source=move_simd_marker_before_probe)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "initialization_order_invalid", "execution_point")

    def test_fails_when_failure_branch_is_missing(self):
        result = self.validate_fixture(mutate_source=remove_after_call_branch)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "initialization_order_invalid", "execution_point")

    def test_fails_when_halt_back_edge_is_missing(self):
        result = self.validate_fixture(mutate_source=remove_text("    jmp .halt\n", count=1))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_halt_convergence", "runtime_continuation.halt_label")

    def test_fails_when_avx_instruction_is_present(self):
        result = self.validate_fixture(mutate_source=insert_avx_instruction)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "avx_instruction_present", "avx_prohibition")

    def test_fails_when_initialization_symbol_is_missing(self):
        result = self.validate_fixture(mutate_report=remove_report_symbol("initialize_cpu_extended_state"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_elf_symbol", "kernel_elf_report.cpu_extended_state_initialization.symbols.initialize_cpu_extended_state")

    def test_fails_when_cpuid_is_missing_from_elf_evidence(self):
        result = self.validate_fixture(mutate_report=replace_report_value("cpuid_present", False))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_elf_evidence", "kernel_elf_report.cpu_extended_state_initialization.cpuid_present")

    def test_fails_when_probe_buffer_geometry_is_wrong(self):
        def mutate(report):
            record = report["cpu_extended_state_initialization"]
            return report | {
                "cpu_extended_state_initialization": record | {
                    "probe_buffer": record["probe_buffer"] | {"size_bytes": 8}
                }
            }

        result = self.validate_fixture(mutate_report=mutate)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_probe_geometry", "kernel_elf_report.cpu_extended_state_initialization.probe_buffer")

    def test_fails_when_avx_is_present_in_elf_evidence(self):
        result = self.validate_fixture(
            mutate_report=lambda report: report | {
                "cpu_extended_state_initialization": report["cpu_extended_state_initialization"] | {
                    "avx_prohibited_instruction_present": True,
                    "prohibited_instructions": [{"mnemonic": "vxorps"}],
                }
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "avx_instruction_present", "kernel_elf_report.cpu_extended_state_initialization.prohibited_instructions")

    def test_fails_when_runtime_metadata_omits_simd_marker(self):
        def mutate(metadata):
            markers = [marker for marker in metadata["observed_markers"] if marker != "KOZO_SIMD_PROBE_OK"]
            return metadata | {"observed_markers": markers}

        result = self.validate_fixture(mutate_metadata=mutate)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "metadata_log_mismatch", "qemu_smoke.observed_markers")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(mutate_source=remove_text("    fninit\n"))

        self.assertEqual(result.status, "fail")
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(self, *, mutate_source=None, mutate_report=None, mutate_metadata=None):
        with tempfile.TemporaryDirectory() as directory:
            paths = write_fixture(Path(directory), mutate_source, mutate_report, mutate_metadata)
            original = patch_paths(paths)
            try:
                return CpuExtendedStateInitializationEvidenceValidator().validate({})
            finally:
                restore_paths(original)

    def assert_failure(self, result, reason, field):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, CPU_EXTENDED_STATE_INITIALIZATION_EVIDENCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def write_fixture(root: Path, mutate_source, mutate_report, mutate_metadata):
    paths = {
        "contract": root / "contract.json",
        "source": root / "boot.asm",
        "report": root / "kernel_elf_report.json",
        "metadata": root / "qemu_smoke.metadata.json",
        "serial": root / "qemu_smoke.log",
    }
    paths["contract"].write_text(contract_module.CONTRACT_PATH.read_text())
    source = validator_module._BOOT_SOURCE_PATH.read_text()
    paths["source"].write_text(mutate_source(source) if mutate_source else source)
    report = valid_report()
    paths["report"].write_text(json.dumps(mutate_report(report) if mutate_report else report))
    metadata = valid_metadata()
    paths["metadata"].write_text(json.dumps(mutate_metadata(metadata) if mutate_metadata else metadata))
    paths["serial"].write_text("\n".join(get_smoke_marker_order()) + "\n")
    return paths


def valid_report():
    symbols = {
        name: {"present": True, "address": f"0xffffffff8020{index:04x}"}
        for index, name in enumerate(
            (
                "initialize_cpu_extended_state",
                "run_simd_survival_probe",
                "observed_x87_control_word",
                "observed_mxcsr",
                "simd_probe_result",
            ),
            start=1,
        )
    }
    return {
        "cpu_extended_state_initialization": {
            "symbols": symbols,
            "probe_buffer": {"size_bytes": 16, "start_aligned": True},
            "pre_odin_call_order_valid": True,
            "initialization_call_chain_valid": True,
            "cpuid_present": True,
            "cr0_access_count": 3,
            "cr4_access_count": 3,
            "fninit_present": True,
            "fnstcw_present": True,
            "ldmxcsr_present": True,
            "stmxcsr_present": True,
            "simd_probe_instruction_present": True,
            "simd_probe_comparison_count": 2,
            "avx_prohibited_instruction_present": False,
            "prohibited_instructions": [],
        }
    }


def valid_metadata():
    return {
        "outcome": "pass",
        "blocker_category": "none",
        "expected_marker": get_expected_smoke_marker(),
        "observed_markers": list(get_smoke_marker_order()),
    }


def patch_paths(paths):
    original = (
        validator_module._CONTRACT_PATH,
        validator_module._BOOT_SOURCE_PATH,
        validator_module._ELF_REPORT_PATH,
        validator_module._METADATA_PATH,
        validator_module._SERIAL_LOG_PATH,
    )
    validator_module._CONTRACT_PATH = paths["contract"]
    validator_module._BOOT_SOURCE_PATH = paths["source"]
    validator_module._ELF_REPORT_PATH = paths["report"]
    validator_module._METADATA_PATH = paths["metadata"]
    validator_module._SERIAL_LOG_PATH = paths["serial"]
    return original


def restore_paths(original):
    (
        validator_module._CONTRACT_PATH,
        validator_module._BOOT_SOURCE_PATH,
        validator_module._ELF_REPORT_PATH,
        validator_module._METADATA_PATH,
        validator_module._SERIAL_LOG_PATH,
    ) = original


def remove_text(text: str, count: int = -1):
    return lambda source: source.replace(text, "", count)


def remove_second_occurrence(text: str):
    def mutate(source):
        first = source.find(text)
        second = source.find(text, first + len(text))
        return source[:second] + source[second + len(text):]

    return mutate


def move_runtime_entry_before_cpu(source):
    line = "    call runtime_progression_entry\n"
    source = source.replace(line, "")
    marker = "    WRITE_COM1_MARKER cpu_ext_state_init_start_marker, cpu_ext_state_init_start_marker_end\n"
    return source.replace(marker, line + marker, 1)


def move_simd_marker_before_probe(source):
    line = "    WRITE_COM1_MARKER simd_probe_ok_marker, simd_probe_ok_marker_end\n"
    source = source.replace(line, "")
    call = "    call run_simd_survival_probe\n"
    return source.replace(call, line + call, 1)


def remove_after_call_branch(source):
    block = "    call initialize_cpu_extended_state\n    test eax, eax\n    jnz .halt\n"
    return source.replace(block, "    call initialize_cpu_extended_state\n", 1)


def insert_avx_instruction(source):
    return source.replace("run_simd_survival_probe:\n", "run_simd_survival_probe:\n    vxorps ymm0, ymm0, ymm0\n")


def remove_report_symbol(name):
    def mutate(report):
        record = report["cpu_extended_state_initialization"]
        symbols = dict(record["symbols"])
        symbols.pop(name)
        return report | {"cpu_extended_state_initialization": record | {"symbols": symbols}}

    return mutate


def replace_report_value(key, value):
    return lambda report: report | {
        "cpu_extended_state_initialization": report["cpu_extended_state_initialization"] | {key: value}
    }


if __name__ == "__main__":
    unittest.main()
