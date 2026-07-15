from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, RUNTIME_PROGRESSION_EVIDENCE_INVALID
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validators_impl import runtime_progression_evidence as validator_module
from harness.validators_impl.runtime_progression_evidence import RuntimeProgressionEvidenceValidator

KOZO_NEGATIVE_COVERAGE = {
    "runtime_progression_evidence": {
        "missing_entry_symbol": "test_fails_when_entry_symbol_is_missing",
        "wrong_entry_signature": "test_fails_when_entry_signature_is_wrong",
        "wrong_calling_convention": "test_fails_when_calling_convention_is_wrong",
        "misaligned_call_site_stack": "test_fails_when_stack_alignment_check_is_missing",
        "missing_context_version": "test_fails_when_context_version_is_wrong",
        "invalid_context_field_order": "test_fails_when_context_field_order_is_wrong",
        "unknown_status_value": "test_fails_when_return_status_is_not_checked",
        "missing_progression_marker": "test_fails_when_progression_marker_is_missing",
        "missing_runtime_marker": "test_fails_when_odin_marker_call_is_missing",
        "return_marker_order": "test_fails_when_return_marker_precedes_runtime_call",
        "metadata_log_mismatch": "test_fails_when_metadata_and_log_disagree",
        "memory_prerequisite_absent": "test_fails_when_memory_prerequisite_is_not_proven",
        "halt_path_missing": "test_fails_when_halt_loop_is_missing",
        "binary_symbol_missing": "test_fails_when_binary_symbol_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class RuntimeProgressionEvidenceValidatorTests(unittest.TestCase):
    def test_valid_ordered_progression_evidence_passes(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_entry_symbol_is_missing(self):
        result = self.validate_fixture(mutate_runtime=remove_text("@(export)\nruntime_progression_entry"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_entry_symbol", "runtime_initialization.entry_symbol")

    def test_fails_when_entry_signature_is_wrong(self):
        result = self.validate_fixture(mutate_runtime=replace_text('proc "c" (bootstrap:', 'proc "odin" (bootstrap:'))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "wrong_entry_signature", "runtime_initialization.entry_symbol")

    def test_fails_when_calling_convention_is_wrong(self):
        result = self.validate_fixture(mutate_runtime=replace_text('proc "c" (bootstrap:', 'proc "odin" (bootstrap:'))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "wrong_entry_signature", "runtime_initialization.entry_symbol")

    def test_fails_when_stack_alignment_check_is_missing(self):
        result = self.validate_fixture(mutate_boot=remove_text("    test rsp, 0x0f\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "assembly_boundary_mismatch", "progression_entry")

    def test_fails_when_context_version_is_wrong(self):
        result = self.validate_fixture(mutate_boot=replace_text("runtime_bootstrap_context:\n    dq 1", "runtime_bootstrap_context:\n    dq 2"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_context_layout", "bootstrap_context.fields")

    def test_fails_when_context_field_order_is_wrong(self):
        result = self.validate_fixture(mutate_boot=swap_context_ranges)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_context_layout", "bootstrap_context.fields")

    def test_fails_when_return_status_is_not_checked(self):
        result = self.validate_fixture(mutate_boot=replace_text("    cmp eax, 0", "    cmp eax, 1"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "assembly_boundary_mismatch", "progression_entry")

    def test_fails_when_progression_marker_is_missing(self):
        result = self.validate_fixture(mutate_boot=remove_text("    WRITE_COM1_MARKER runtime_progress_entry_marker, runtime_progress_entry_marker_end\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "assembly_boundary_mismatch", "progression_entry")

    def test_fails_when_odin_marker_call_is_missing(self):
        result = self.validate_fixture(mutate_runtime=remove_text("\truntime_emit_init_marker()\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "runtime_marker_not_owned_by_odin", "runtime_initialization.marker_emission_owner")

    def test_fails_when_return_marker_precedes_runtime_call(self):
        result = self.validate_fixture(mutate_boot=move_return_marker_before_call)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "assembly_boundary_mismatch", "progression_entry")

    def test_fails_when_metadata_and_log_disagree(self):
        markers = list(get_smoke_marker_order()[:-1])
        result = self.validate_fixture(mutate_metadata=lambda value: value | {"observed_markers": markers})

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "metadata_log_mismatch", "qemu_smoke.observed_markers")

    def test_fails_when_memory_prerequisite_is_not_proven(self):
        result = self.validate_fixture(mutate_stages=set_stage_status("MEMORY_INITIALIZATION_EVIDENCE", "planned"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "stage_status_mismatch", "runtime_progression_stages.MEMORY_INITIALIZATION_EVIDENCE.status")

    def test_fails_when_halt_loop_is_missing(self):
        result = self.validate_fixture(mutate_boot=remove_text("    jmp .halt\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "assembly_boundary_mismatch", "progression_entry")

    def test_fails_when_binary_symbol_is_missing(self):
        def remove_symbol(report):
            symbols = dict(report["runtime_progression_symbols"])
            symbols["runtime_progression_entry"] = {"present": False, "address": ""}
            return report | {"runtime_progression_symbols": symbols}

        result = self.validate_fixture(mutate_report=remove_symbol)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "binary_symbol_missing", "kernel_elf_report.runtime_progression_symbols.runtime_progression_entry")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(mutate_boot=remove_text("    test rsp, 0x0f\n"))

        self.assertEqual(result.status, "fail")
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(self, **mutations):
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_fixture(Path(tmp), mutations)
            old = patch_paths(paths)
            try:
                return RuntimeProgressionEvidenceValidator().validate({})
            finally:
                restore_paths(old)

    def assert_failure(self, result, reason: str, field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_PROGRESSION_EVIDENCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def write_fixture(root: Path, mutations: dict[str, object]) -> dict[str, Path]:
    paths = fixture_paths(root)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    paths["contract"].write_text(validator_module._CONTRACT_PATH.read_text())
    write_mutated_text(paths["boot"], validator_module._BOOT_SOURCE_PATH.read_text(), mutations.get("mutate_boot"))
    write_mutated_text(paths["runtime"], validator_module._RUNTIME_SOURCE_PATH.read_text(), mutations.get("mutate_runtime"))
    write_json(paths["report"], valid_report(), mutations.get("mutate_report"))
    write_json(paths["metadata"], valid_metadata(), mutations.get("mutate_metadata"))
    write_json(paths["stages"], json.loads(validator_module._STAGES_PATH.read_text()), mutations.get("mutate_stages"))
    paths["serial"].write_text("\n".join(get_smoke_marker_order()) + "\n")
    return paths


def fixture_paths(root: Path) -> dict[str, Path]:
    return {
        "contract": root / "contracts/runtime_progression_entry_contract.v0.json",
        "boot": root / "kernel/arch/x86_64/boot.asm",
        "runtime": root / "kernel/runtime_progression.odin",
        "report": root / "artifacts/runtime/kernel_elf_report.json",
        "metadata": root / "artifacts/runtime/qemu_smoke.metadata.json",
        "serial": root / "artifacts/runtime/qemu_smoke.log",
        "stages": root / "contracts/runtime_progression_stages.v0.json",
    }


def valid_report() -> dict[str, object]:
    return {
        "runtime_progression_symbols": {
            symbol: {"present": True, "address": f"0xffffffff8020{index:04x}"}
            for index, symbol in enumerate(validator_module._REQUIRED_SYMBOLS)
        }
    }


def valid_metadata() -> dict[str, object]:
    return {
        "outcome": "pass",
        "expected_marker": get_expected_smoke_marker(),
        "observed_markers": list(get_smoke_marker_order()),
    }


def write_mutated_text(path: Path, text: str, mutation) -> None:
    path.write_text(mutation(text) if mutation else text)


def write_json(path: Path, value: dict[str, object], mutation) -> None:
    path.write_text(json.dumps(mutation(value) if mutation else value))


def patch_paths(paths: dict[str, Path]):
    names = ("_CONTRACT_PATH", "_BOOT_SOURCE_PATH", "_RUNTIME_SOURCE_PATH", "_ELF_REPORT_PATH", "_METADATA_PATH", "_SERIAL_LOG_PATH", "_STAGES_PATH")
    old = tuple(getattr(validator_module, name) for name in names)
    for name, key in zip(names, ("contract", "boot", "runtime", "report", "metadata", "serial", "stages")):
        setattr(validator_module, name, paths[key])
    return names, old


def restore_paths(state) -> None:
    names, old = state
    for name, value in zip(names, old):
        setattr(validator_module, name, value)


def replace_text(old: str, new: str):
    return lambda source: source.replace(old, new)


def remove_text(value: str):
    return replace_text(value, "")


def swap_context_ranges(source: str) -> str:
    old = "    dq boot_stack\n    dq boot_stack_top\n    dq boot_memory_region\n    dq boot_memory_region_end"
    new = "    dq boot_memory_region\n    dq boot_memory_region_end\n    dq boot_stack\n    dq boot_stack_top"
    return source.replace(old, new)


def move_return_marker_before_call(source: str) -> str:
    marker = "    WRITE_COM1_MARKER runtime_return_marker, runtime_return_marker_end\n"
    source = source.replace(marker, "")
    call = "    call runtime_progression_entry\n"
    return source.replace(call, marker + call)


def set_stage_status(stage_name: str, status: str):
    def mutate(document):
        stages = [stage | {"status": status} if stage["stage_name"] == stage_name else stage for stage in document["stages"]]
        return document | {"stages": stages}

    return mutate


if __name__ == "__main__":
    unittest.main()
