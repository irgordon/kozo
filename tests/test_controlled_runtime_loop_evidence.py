from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import CONTROLLED_RUNTIME_LOOP_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validators_impl import controlled_runtime_loop_evidence as validator_module
from harness.validators_impl.controlled_runtime_loop_evidence import (
    ControlledRuntimeLoopEvidenceValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "controlled_runtime_loop_evidence": {
        "loop_entry_mismatch": "test_fails_when_loop_entry_is_missing",
        "volatile_state_missing": "test_fails_when_state_access_is_not_volatile",
        "loop_sequence_mismatch": "test_fails_when_loop_sequence_is_incomplete",
        "loop_completion_mismatch": "test_fails_when_terminal_validation_is_missing",
        "marker_bridge_missing": "test_fails_when_marker_bridge_is_missing",
        "binary_loop_missing": "test_fails_when_binary_loop_record_is_missing",
        "binary_symbol_missing": "test_fails_when_binary_symbol_is_missing",
        "binary_backward_edge_missing": "test_fails_when_binary_backward_edge_is_missing",
        "binary_terminal_comparison_missing": "test_fails_when_binary_terminal_comparison_is_missing",
        "stage_status_mismatch": "test_fails_when_stage_status_is_wrong",
        "runtime_loop_evidence_missing": "test_fails_when_qemu_does_not_pass",
        "metadata_log_mismatch": "test_fails_when_metadata_and_log_disagree",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class ControlledRuntimeLoopEvidenceValidatorTests(unittest.TestCase):
    def test_passes_with_ordered_runtime_loop_evidence(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_loop_entry_is_missing(self):
        result = self.validate_fixture(
            mutate_runtime=lambda text: text.replace(
                "loop_status := controlled_runtime_loop()",
                "loop_status := RUNTIME_PROGRESSION_OK",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "loop_entry_mismatch", "loop.entry")

    def test_fails_when_state_access_is_not_volatile(self):
        result = self.validate_fixture(
            mutate_runtime=lambda text: text.replace(
                "intrinsics.volatile_store(&runtime_loop_state.iteration_limit, RUNTIME_LOOP_ITERATION_LIMIT)",
                "runtime_loop_state.iteration_limit = RUNTIME_LOOP_ITERATION_LIMIT",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "volatile_state_missing", "state")

    def test_fails_when_loop_sequence_is_incomplete(self):
        result = self.validate_fixture(
            mutate_runtime=lambda text: text.replace(
                "next_accumulator := runtime_loop_accumulator() + next_count",
                "next_accumulator := next_count",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "loop_sequence_mismatch", "loop")

    def test_fails_when_terminal_validation_is_missing(self):
        result = self.validate_fixture(
            mutate_runtime=lambda text: text.replace(
                "if runtime_loop_iteration_count() != runtime_loop_limit() {",
                "if false {",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "loop_completion_mismatch", "terminal_behavior")

    def test_fails_when_marker_bridge_is_missing(self):
        result = self.validate_fixture(
            mutate_boot=lambda text: text.replace(
                "WRITE_COM1_MARKER runtime_loop_exit_marker, runtime_loop_exit_marker_end",
                "nop",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "marker_bridge_missing", "markers.runtime_serial_write_loop_exit_marker")

    def test_fails_when_binary_loop_record_is_missing(self):
        result = self.validate_fixture(
            mutate_report=lambda value: {key: item for key, item in value.items() if key != "controlled_runtime_loop"}
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "binary_loop_missing", "kernel_elf_report.controlled_runtime_loop")

    def test_fails_when_binary_symbol_is_missing(self):
        def mutate(value):
            record = dict(value["controlled_runtime_loop"])
            symbols = dict(record["symbols"])
            symbols["runtime_loop_state"] = {"present": False, "address": ""}
            record["symbols"] = symbols
            return value | {"controlled_runtime_loop": record}

        result = self.validate_fixture(mutate_report=mutate)

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "binary_symbol_missing",
            "kernel_elf_report.controlled_runtime_loop.symbols.runtime_loop_state",
        )

    def test_fails_when_binary_backward_edge_is_missing(self):
        result = self.validate_fixture(
            mutate_report=replace_report_field("backward_branch_present", False)
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "binary_backward_edge_missing",
            "kernel_elf_report.controlled_runtime_loop.backward_branch_present",
        )

    def test_fails_when_binary_terminal_comparison_is_missing(self):
        result = self.validate_fixture(
            mutate_report=replace_report_field("terminal_comparison_present", False)
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "binary_terminal_comparison_missing",
            "kernel_elf_report.controlled_runtime_loop.terminal_comparison_present",
        )

    def test_fails_when_stage_status_is_wrong(self):
        result = self.validate_fixture(
            mutate_stages=replace_stage_status("CONTROLLED_RUNTIME_LOOP", "planned")
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "stage_status_mismatch",
            "runtime_progression_stages.CONTROLLED_RUNTIME_LOOP.status",
        )

    def test_fails_when_qemu_does_not_pass(self):
        result = self.validate_fixture(
            mutate_metadata=lambda value: value | {
                "outcome": "blocked",
                "blocker_category": "runtime_loop_iteration_incomplete",
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "runtime_loop_evidence_missing", "qemu_smoke.outcome")

    def test_fails_when_metadata_and_log_disagree(self):
        result = self.validate_fixture(
            mutate_log=lambda text: text.replace("KOZO_RUNTIME_LOOP_ITER_2\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "metadata_log_mismatch", "qemu_smoke.serial_log")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(
            mutate_report=replace_report_field("backward_branch_present", False)
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, CONTROLLED_RUNTIME_LOOP_EVIDENCE_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(
        self,
        *,
        mutate_runtime=None,
        mutate_boot=None,
        mutate_report=None,
        mutate_stages=None,
        mutate_metadata=None,
        mutate_log=None,
    ):
        with tempfile.TemporaryDirectory() as directory:
            paths = fixture_paths(Path(directory))
            write_fixture(paths)
            mutate_text_file(paths["runtime"], mutate_runtime)
            mutate_text_file(paths["boot"], mutate_boot)
            mutate_json_file(paths["report"], mutate_report)
            mutate_json_file(paths["stages"], mutate_stages)
            mutate_json_file(paths["metadata"], mutate_metadata)
            mutate_text_file(paths["log"], mutate_log)
            originals = patch_paths(paths)
            try:
                return ControlledRuntimeLoopEvidenceValidator().validate({})
            finally:
                restore_paths(originals)

    def assert_failure(self, result, reason, field):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, CONTROLLED_RUNTIME_LOOP_EVIDENCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def fixture_paths(root: Path) -> dict[str, Path]:
    return {
        "contract": root / "contract.json",
        "runtime": root / "runtime_progression.odin",
        "boot": root / "boot.asm",
        "report": root / "kernel_elf_report.json",
        "stages": root / "runtime_progression_stages.json",
        "metadata": root / "qemu_smoke.metadata.json",
        "log": root / "qemu_smoke.log",
    }


def write_fixture(paths: dict[str, Path]) -> None:
    copy_map = {
        "contract": validator_module._CONTRACT_PATH,
        "runtime": validator_module._RUNTIME_SOURCE_PATH,
        "boot": validator_module._BOOT_SOURCE_PATH,
        "report": validator_module._ELF_REPORT_PATH,
        "stages": validator_module._STAGES_PATH,
    }
    for name, source in copy_map.items():
        paths[name].write_text(source.read_text())
    markers = get_smoke_marker_order()
    paths["metadata"].write_text(json.dumps({
        "outcome": "pass",
        "blocker_category": "",
        "expected_marker": get_expected_smoke_marker(),
        "observed_markers": list(markers),
    }))
    paths["log"].write_text("\n".join(markers) + "\n")


def patch_paths(paths: dict[str, Path]) -> dict[str, Path]:
    mapping = {
        "_CONTRACT_PATH": paths["contract"],
        "_RUNTIME_SOURCE_PATH": paths["runtime"],
        "_BOOT_SOURCE_PATH": paths["boot"],
        "_ELF_REPORT_PATH": paths["report"],
        "_STAGES_PATH": paths["stages"],
        "_METADATA_PATH": paths["metadata"],
        "_SERIAL_LOG_PATH": paths["log"],
    }
    originals = {name: getattr(validator_module, name) for name in mapping}
    for name, value in mapping.items():
        setattr(validator_module, name, value)
    return originals


def restore_paths(originals: dict[str, Path]) -> None:
    for name, value in originals.items():
        setattr(validator_module, name, value)


def mutate_text_file(path: Path, mutate) -> None:
    if mutate is not None:
        path.write_text(mutate(path.read_text()))


def mutate_json_file(path: Path, mutate) -> None:
    if mutate is not None:
        path.write_text(json.dumps(mutate(json.loads(path.read_text()))))


def replace_report_field(field, value):
    def mutate(document):
        return document | {
            "controlled_runtime_loop": document["controlled_runtime_loop"] | {field: value}
        }

    return mutate


def replace_stage_status(stage_name, status):
    def mutate(document):
        stages = [
            stage | {"status": status} if stage["stage_name"] == stage_name else stage
            for stage in document["stages"]
        ]
        return document | {"stages": stages}

    return mutate
