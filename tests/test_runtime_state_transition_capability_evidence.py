from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, RUNTIME_STATE_TRANSITION_CAPABILITY_EVIDENCE_INVALID
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validators_impl import runtime_state_transition_capability_evidence as validator_module
from harness.validators_impl.runtime_state_transition_capability_evidence import (
    RuntimeStateTransitionCapabilityEvidenceValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "runtime_state_transition_capability_evidence": {
        "capability_path_missing": "test_fails_when_second_capability_is_not_called",
        "source_layout_mismatch": "test_fails_when_response_size_assertion_is_missing",
        "state_initialization_missing": "test_fails_when_state_is_not_initialized_explicitly",
        "request_validation_missing": "test_fails_when_stale_generation_is_not_rejected",
        "dispatcher_sequence_mismatch": "test_fails_when_dispatcher_omits_capability_id_2",
        "generic_marker_duplicated": "test_fails_when_generic_dispatch_marker_is_repeated",
        "mutation_sequence_mismatch": "test_fails_when_readback_rollback_is_missing",
        "volatile_access_missing": "test_fails_when_state_write_is_not_volatile",
        "response_validation_missing": "test_fails_when_response_generation_is_not_validated",
        "coordinator_sequence_mismatch": "test_fails_when_second_success_precedes_response_validation",
        "success_marker_on_failure_path": "test_fails_when_update_success_has_multiple_call_sites",
        "marker_bridge_missing": "test_fails_when_fixed_marker_bridge_is_missing",
        "halt_path_missing": "test_fails_when_halt_loop_is_missing",
        "binary_capability_missing": "test_fails_when_binary_record_is_missing",
        "binary_symbol_missing": "test_fails_when_state_symbol_is_missing",
        "binary_call_missing": "test_fails_when_progression_call_is_missing",
        "binary_volatile_access_missing": "test_fails_when_binary_volatile_access_is_missing",
        "binary_comparison_missing": "test_fails_when_binary_comparison_is_missing",
        "binary_state_geometry_invalid": "test_fails_when_binary_state_size_is_wrong",
        "capability_evidence_missing": "test_fails_when_qemu_does_not_pass",
        "metadata_log_mismatch": "test_fails_when_metadata_and_log_disagree",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class RuntimeStateTransitionCapabilityEvidenceValidatorTests(unittest.TestCase):
    def test_complete_ordered_state_transition_evidence_passes(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_second_capability_is_not_called(self):
        result = self.validate_fixture(
            mutate_progression=replace_text(
                "return execute_second_governed_capability()",
                "return RUNTIME_PROGRESSION_OK",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "capability_path_missing", "execution_order")

    def test_fails_when_response_size_assertion_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=remove_text(
                "#assert(size_of(Runtime_State_Transition_Response) == RUNTIME_STATE_TRANSITION_RESPONSE_SIZE)"
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "source_layout_mismatch", "state_request_response_layout")

    def test_fails_when_state_is_not_initialized_explicitly(self):
        result = self.validate_fixture(
            mutate_capability=remove_text(
                "runtime_state_cell_store(RUNTIME_STATE_READY, RUNTIME_STATE_INITIAL_GENERATION)"
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "state_initialization_missing", "state.initial_values")

    def test_fails_when_stale_generation_is_not_rejected(self):
        result = self.validate_fixture(
            mutate_capability=replace_text(
                "if request.expected_generation != RUNTIME_STATE_INITIAL_GENERATION {",
                "if false {",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "request_validation_missing", "request")

    def test_fails_when_dispatcher_omits_capability_id_2(self):
        result = self.validate_fixture(
            mutate_capability=replace_text(
                "case RUNTIME_STATE_TRANSITION_CAPABILITY_ID:",
                "case 99:",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "dispatcher_sequence_mismatch", "execution_order")

    def test_fails_when_generic_dispatch_marker_is_repeated(self):
        result = self.validate_fixture(
            mutate_capability=lambda text: text + "\nruntime_serial_write_capability_dispatch_marker()\n"
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "generic_marker_duplicated",
            "markers.generic_dispatch_marker_repeated",
        )

    def test_fails_when_readback_rollback_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=remove_text(
                "runtime_state_cell_store(previous_state, previous_generation)"
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "mutation_sequence_mismatch", "transition")

    def test_fails_when_state_write_is_not_volatile(self):
        result = self.validate_fixture(
            mutate_capability=replace_text(
                "intrinsics.volatile_store(&runtime_state_transition_cell.state, state)",
                "runtime_state_transition_cell.state = state",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "volatile_access_missing", "state.volatile_access_required")

    def test_fails_when_response_generation_is_not_validated(self):
        result = self.validate_fixture(
            mutate_capability=remove_text(
                "response.current_generation == RUNTIME_STATE_TERMINAL_GENERATION &&"
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "response_validation_missing", "response")

    def test_fails_when_second_success_precedes_response_validation(self):
        result = self.validate_fixture(
            mutate_capability=move_second_marker_before_validation
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "coordinator_sequence_mismatch", "execution_order")

    def test_fails_when_update_success_has_multiple_call_sites(self):
        result = self.validate_fixture(
            mutate_capability=lambda text: text + "\nruntime_serial_write_state_update_ok_marker()\n"
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "success_marker_on_failure_path",
            "failure_behavior.success_markers_forbidden_on_failure",
        )

    def test_fails_when_fixed_marker_bridge_is_missing(self):
        result = self.validate_fixture(
            mutate_boot=replace_text(
                "WRITE_COM1_MARKER runtime_state_update_ok_marker, runtime_state_update_ok_marker_end",
                "nop",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "marker_bridge_missing",
            "markers.runtime_serial_write_state_update_ok_marker",
        )

    def test_fails_when_halt_loop_is_missing(self):
        result = self.validate_fixture(mutate_boot=remove_text("    jmp .halt\n"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "halt_path_missing", "failure_behavior.halt_contract")

    def test_fails_when_binary_record_is_missing(self):
        result = self.validate_fixture(
            mutate_report=lambda value: {
                key: item
                for key, item in value.items()
                if key != "runtime_state_transition_capability"
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "binary_capability_missing",
            "kernel_elf_report.runtime_state_transition_capability",
        )

    def test_fails_when_state_symbol_is_missing(self):
        def mutate(value):
            record = dict(value["runtime_state_transition_capability"])
            symbols = dict(record["symbols"])
            symbols["runtime_state_transition_cell"] = {"present": False, "address": ""}
            record["symbols"] = symbols
            return value | {"runtime_state_transition_capability": record}

        result = self.validate_fixture(mutate_report=mutate)

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "binary_symbol_missing",
            "kernel_elf_report.runtime_state_transition_capability.symbols.runtime_state_transition_cell",
        )

    def test_fails_when_progression_call_is_missing(self):
        result = self.validate_fixture(
            mutate_report=replace_report_field("progression_call_present", False)
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "binary_call_missing",
            "kernel_elf_report.runtime_state_transition_capability.progression_call_present",
        )

    def test_fails_when_binary_volatile_access_is_missing(self):
        result = self.validate_fixture(
            mutate_report=replace_report_field("volatile_memory_access_count", 0)
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "binary_volatile_access_missing",
            "kernel_elf_report.runtime_state_transition_capability.volatile_memory_access_count",
        )

    def test_fails_when_binary_comparison_is_missing(self):
        result = self.validate_fixture(
            mutate_report=replace_report_field("handler_comparison_count", 0)
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "binary_comparison_missing",
            "kernel_elf_report.runtime_state_transition_capability.handler_comparison_count",
        )

    def test_fails_when_binary_state_size_is_wrong(self):
        result = self.validate_fixture(
            mutate_report=replace_report_field("state_cell_size_bytes", 8)
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "binary_state_geometry_invalid",
            "kernel_elf_report.runtime_state_transition_capability.state_cell_geometry",
        )

    def test_fails_when_qemu_does_not_pass(self):
        result = self.validate_fixture(
            mutate_metadata=lambda value: value | {
                "outcome": "blocked",
                "blocker_category": "runtime_state_update_not_completed",
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "capability_evidence_missing", "qemu_smoke.outcome")

    def test_fails_when_metadata_and_log_disagree(self):
        result = self.validate_fixture(
            mutate_log=lambda text: text.replace("KOZO_RUNTIME_STATE_UPDATE_OK\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "metadata_log_mismatch", "qemu_smoke.serial_log")

    def test_fails_when_update_enter_precedes_first_capability(self):
        result = self.validate_fixture(
            mutate_log=swap_markers(
                "KOZO_FIRST_CAPABILITY_OK",
                "KOZO_RUNTIME_STATE_UPDATE_ENTER",
            )
        )

        self.assert_failure(result, "metadata_log_mismatch", "qemu_smoke.serial_log")

    def test_fails_when_update_enter_is_missing(self):
        result = self.validate_fixture(
            mutate_log=remove_text("KOZO_RUNTIME_STATE_UPDATE_ENTER\n")
        )

        self.assert_failure(result, "metadata_log_mismatch", "qemu_smoke.serial_log")

    def test_fails_when_update_success_is_missing(self):
        result = self.validate_fixture(
            mutate_log=remove_text("KOZO_RUNTIME_STATE_UPDATE_OK\n")
        )

        self.assert_failure(result, "metadata_log_mismatch", "qemu_smoke.serial_log")

    def test_fails_when_second_capability_precedes_update_success(self):
        result = self.validate_fixture(
            mutate_log=swap_markers(
                "KOZO_RUNTIME_STATE_UPDATE_OK",
                "KOZO_SECOND_CAPABILITY_OK",
            )
        )

        self.assert_failure(result, "metadata_log_mismatch", "qemu_smoke.serial_log")

    def test_fails_when_runtime_return_precedes_second_capability(self):
        result = self.validate_fixture(
            mutate_log=swap_markers(
                "KOZO_SECOND_CAPABILITY_OK",
                "KOZO_RUNTIME_RETURN_OK",
            )
        )

        self.assert_failure(result, "metadata_log_mismatch", "qemu_smoke.serial_log")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(
            mutate_report=replace_report_field("progression_call_present", False)
        )

        self.assertEqual(result.code, RUNTIME_STATE_TRANSITION_CAPABILITY_EVIDENCE_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(self, **mutations):
        with tempfile.TemporaryDirectory() as directory:
            paths = fixture_paths(Path(directory))
            write_fixture(paths)
            mutate_text(paths["capability"], mutations.get("mutate_capability"))
            mutate_text(paths["progression"], mutations.get("mutate_progression"))
            mutate_text(paths["boot"], mutations.get("mutate_boot"))
            mutate_json(paths["report"], mutations.get("mutate_report"))
            mutate_json(paths["metadata"], mutations.get("mutate_metadata"))
            mutate_text(paths["log"], mutations.get("mutate_log"))
            originals = patch_paths(paths)
            try:
                return RuntimeStateTransitionCapabilityEvidenceValidator().validate({})
            finally:
                restore_paths(originals)

    def assert_failure(self, result, reason, field):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_STATE_TRANSITION_CAPABILITY_EVIDENCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def fixture_paths(root: Path) -> dict[str, Path]:
    return {
        "contract": root / "contract.json",
        "capability": root / "runtime_capability.odin",
        "progression": root / "runtime_progression.odin",
        "boot": root / "boot.asm",
        "report": root / "kernel_elf_report.json",
        "metadata": root / "qemu_smoke.metadata.json",
        "log": root / "qemu_smoke.log",
    }


def write_fixture(paths: dict[str, Path]) -> None:
    copy_map = {
        "contract": validator_module._CONTRACT_PATH,
        "capability": validator_module._CAPABILITY_SOURCE_PATH,
        "progression": validator_module._PROGRESSION_SOURCE_PATH,
        "boot": validator_module._BOOT_SOURCE_PATH,
        "report": validator_module._ELF_REPORT_PATH,
    }
    for name, source in copy_map.items():
        paths[name].write_text(source.read_text())
    report = json.loads(paths["report"].read_text())
    report["runtime_state_transition_capability"] = valid_binary_record()
    paths["report"].write_text(json.dumps(report))
    markers = get_smoke_marker_order()
    paths["metadata"].write_text(json.dumps({
        "outcome": "pass",
        "blocker_category": "",
        "expected_marker": get_expected_smoke_marker(),
        "observed_markers": list(markers),
    }))
    paths["log"].write_text("\n".join(markers) + "\n")


def valid_binary_record() -> dict[str, object]:
    symbols = {
        symbol: {"present": True, "address": f"0x{index + 1:x}"}
        for index, symbol in enumerate(validator_module._REQUIRED_SYMBOLS)
    }
    return {
        "symbols": symbols,
        "progression_call_present": True,
        "dispatcher_route_present": True,
        "handler_comparison_count": 1,
        "volatile_memory_access_count": 6,
        "state_cell_address": "0x8",
        "state_cell_size_bytes": 16,
        "state_cell_required_size_bytes": 16,
        "state_cell_required_alignment_bytes": 8,
        "state_cell_aligned": True,
    }


def patch_paths(paths: dict[str, Path]) -> dict[str, Path]:
    mapping = {
        "_CONTRACT_PATH": paths["contract"],
        "_CAPABILITY_SOURCE_PATH": paths["capability"],
        "_PROGRESSION_SOURCE_PATH": paths["progression"],
        "_BOOT_SOURCE_PATH": paths["boot"],
        "_ELF_REPORT_PATH": paths["report"],
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


def mutate_text(path: Path, mutate) -> None:
    if mutate is not None:
        path.write_text(mutate(path.read_text()))


def mutate_json(path: Path, mutate) -> None:
    if mutate is not None:
        path.write_text(json.dumps(mutate(json.loads(path.read_text()))))


def replace_text(old: str, new: str):
    return lambda source: source.replace(old, new)


def remove_text(value: str):
    return replace_text(value, "")


def swap_markers(first: str, second: str):
    def mutate(source: str) -> str:
        placeholder = "__KOZO_MARKER_SWAP__"
        source = source.replace(first, placeholder, 1)
        source = source.replace(second, first, 1)
        return source.replace(placeholder, second, 1)

    return mutate


def replace_report_field(field, value):
    def mutate(document):
        record = document["runtime_state_transition_capability"] | {field: value}
        return document | {"runtime_state_transition_capability": record}

    return mutate


def move_second_marker_before_validation(source: str) -> str:
    marker = "\truntime_serial_write_second_capability_marker()\n"
    source = source.replace(marker, "")
    validation = "\tif !validate_runtime_state_transition_response(&response) {\n"
    return source.replace(validation, marker + validation, 1)


if __name__ == "__main__":
    unittest.main()
