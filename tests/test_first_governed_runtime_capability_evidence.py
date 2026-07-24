from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import FIRST_GOVERNED_RUNTIME_CAPABILITY_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validators_impl import first_governed_runtime_capability_evidence as validator_module
from harness.validators_impl.first_governed_runtime_capability_evidence import (
    FirstGovernedRuntimeCapabilityEvidenceValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "first_governed_runtime_capability_evidence": {
        "capability_path_missing": "test_fails_when_progression_does_not_call_capability",
        "source_layout_mismatch": "test_fails_when_response_layout_assertion_is_missing",
        "request_validation_missing": "test_fails_when_request_version_validation_is_missing",
        "dispatcher_sequence_mismatch": "test_fails_when_response_is_not_cleared_before_dispatch",
        "handler_sequence_mismatch": "test_fails_when_controlled_loop_state_is_not_validated",
        "response_population_missing": "test_fails_when_response_field_is_missing",
        "response_validation_missing": "test_fails_when_response_stage_validation_is_missing",
        "success_marker_before_validation": "test_fails_when_response_validation_is_missing",
        "success_marker_duplicated": "test_fails_when_success_marker_has_multiple_call_sites",
        "marker_bridge_missing": "test_fails_when_fixed_marker_bridge_is_missing",
        "binary_capability_missing": "test_fails_when_binary_record_is_missing",
        "binary_symbol_missing": "test_fails_when_binary_symbol_is_missing",
        "binary_call_missing": "test_fails_when_binary_call_is_missing",
        "stage_status_mismatch": "test_fails_when_stage_status_is_wrong",
        "capability_evidence_missing": "test_fails_when_qemu_does_not_pass",
        "metadata_log_mismatch": "test_fails_when_metadata_and_log_disagree",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class FirstGovernedRuntimeCapabilityEvidenceValidatorTests(unittest.TestCase):
    def test_passes_with_ordered_capability_evidence(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_progression_does_not_call_capability(self):
        result = self.validate_fixture(
            mutate_progression=lambda text: text.replace(
                "return execute_first_governed_capability()",
                "return RUNTIME_PROGRESSION_OK",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "capability_path_missing", "execution_order")

    def test_fails_when_response_layout_assertion_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=remove_source_line(
                "#assert(size_of(Runtime_Status_Response) == RUNTIME_STATUS_RESPONSE_SIZE)"
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "source_layout_mismatch", "request_response_layout")

    def test_fails_when_request_version_validation_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=lambda text: text.replace(
                "if request.version != RUNTIME_STATUS_REQUEST_VERSION {",
                "if false {",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "request_validation_missing", "request")

    def test_fails_when_unknown_capability_validation_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=lambda text: text.replace(
                "if request.capability_id != RUNTIME_STATUS_QUERY_CAPABILITY_ID {",
                "if false {",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "request_validation_missing", "request")

    def test_fails_when_unsupported_flags_validation_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=lambda text: text.replace(
                "if request.flags != RUNTIME_STATUS_SUPPORTED_FLAGS {",
                "if false {",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "request_validation_missing", "request")

    def test_fails_when_reserved_field_validation_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=lambda text: text.replace(
                "if request.reserved != 0 {",
                "if false {",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "request_validation_missing", "request")

    def test_fails_when_response_is_not_cleared_before_dispatch(self):
        result = self.validate_fixture(
            mutate_capability=lambda text: text.replace(
                "clear_runtime_status_response(response)",
                "",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "dispatcher_sequence_mismatch", "execution_order")

    def test_fails_when_controlled_loop_state_is_not_validated(self):
        result = self.validate_fixture(
            mutate_capability=lambda text: text.replace(
                "if !controlled_runtime_loop_state_is_complete() {",
                "if false {",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "handler_sequence_mismatch", "execution_order")

    def test_fails_when_response_field_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=lambda text: text.replace(
                "response.proven_stage_mask = RUNTIME_PROVEN_STAGE_MASK",
                "",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "response_population_missing", "response.fields")

    def test_fails_when_response_stage_validation_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=remove_source_line(
                "response.current_progression_stage == RUNTIME_STAGE_CONTROLLED_RUNTIME_LOOP &&"
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "response_validation_missing", "response.validation")

    def test_fails_when_response_stage_mask_validation_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=remove_source_line(
                "response.proven_stage_mask == RUNTIME_PROVEN_STAGE_MASK &&"
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "response_validation_missing", "response.validation")

    def test_fails_when_response_loop_value_validation_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=remove_source_line(
                "response.controlled_loop_accumulator == RUNTIME_LOOP_EXPECTED_ACCUMULATOR &&"
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "response_validation_missing", "response.validation")

    def test_fails_when_response_reserved_validation_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=remove_source_line("response.reserved == 0")
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "response_validation_missing", "response.validation")

    def test_fails_when_response_validation_is_missing(self):
        result = self.validate_fixture(
            mutate_capability=lambda text: text.replace(
                "if !validate_runtime_status_response(&response) {",
                "if false {",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "success_marker_before_validation", "markers")

    def test_fails_when_success_marker_has_multiple_call_sites(self):
        result = self.validate_fixture(
            mutate_capability=lambda text: text + "\nruntime_serial_write_first_capability_marker()\n"
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "success_marker_duplicated", "markers.emission_owner")

    def test_fails_when_fixed_marker_bridge_is_missing(self):
        result = self.validate_fixture(
            mutate_boot=lambda text: text.replace(
                "WRITE_COM1_MARKER runtime_status_query_marker, runtime_status_query_marker_end",
                "nop",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "marker_bridge_missing",
            "markers.runtime_serial_write_status_query_marker",
        )

    def test_fails_when_binary_record_is_missing(self):
        result = self.validate_fixture(
            mutate_report=lambda value: {
                key: item
                for key, item in value.items()
                if key != "first_governed_runtime_capability"
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "binary_capability_missing",
            "kernel_elf_report.first_governed_runtime_capability",
        )

    def test_fails_when_binary_symbol_is_missing(self):
        def mutate(value):
            record = dict(value["first_governed_runtime_capability"])
            symbols = dict(record["symbols"])
            symbols["query_runtime_status"] = {"present": False, "address": ""}
            record["symbols"] = symbols
            return value | {"first_governed_runtime_capability": record}

        result = self.validate_fixture(mutate_report=mutate)

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "binary_symbol_missing",
            "kernel_elf_report.first_governed_runtime_capability.symbols.query_runtime_status",
        )

    def test_fails_when_binary_call_is_missing(self):
        result = self.validate_fixture(
            mutate_report=replace_report_field("progression_call_present", False)
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "binary_call_missing",
            "kernel_elf_report.first_governed_runtime_capability.progression_call_present",
        )

    def test_fails_when_stage_status_is_wrong(self):
        result = self.validate_fixture(
            mutate_stages=replace_stage_status(
                "FIRST_GOVERNED_RUNTIME_CAPABILITY",
                "planned",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "stage_status_mismatch",
            "runtime_progression_stages.FIRST_GOVERNED_RUNTIME_CAPABILITY.status",
        )

    def test_fails_when_qemu_does_not_pass(self):
        result = self.validate_fixture(
            mutate_metadata=lambda value: value | {
                "outcome": "blocked",
                "blocker_category": "first_governed_capability_not_proven",
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "capability_evidence_missing", "qemu_smoke.outcome")

    def test_fails_when_metadata_and_log_disagree(self):
        result = self.validate_fixture(
            mutate_log=lambda text: text.replace("KOZO_RUNTIME_STATUS_QUERY_OK\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "metadata_log_mismatch", "qemu_smoke.serial_log")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(
            mutate_report=replace_report_field("progression_call_present", False)
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, FIRST_GOVERNED_RUNTIME_CAPABILITY_EVIDENCE_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(
        self,
        *,
        mutate_capability=None,
        mutate_progression=None,
        mutate_boot=None,
        mutate_report=None,
        mutate_stages=None,
        mutate_metadata=None,
        mutate_log=None,
    ):
        with tempfile.TemporaryDirectory() as directory:
            paths = fixture_paths(Path(directory))
            write_fixture(paths)
            mutate_text_file(paths["capability"], mutate_capability)
            mutate_text_file(paths["progression"], mutate_progression)
            mutate_text_file(paths["boot"], mutate_boot)
            mutate_json_file(paths["report"], mutate_report)
            mutate_json_file(paths["stages"], mutate_stages)
            mutate_json_file(paths["metadata"], mutate_metadata)
            mutate_text_file(paths["log"], mutate_log)
            originals = patch_paths(paths)
            try:
                return FirstGovernedRuntimeCapabilityEvidenceValidator().validate({})
            finally:
                restore_paths(originals)

    def assert_failure(self, result, reason, field):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, FIRST_GOVERNED_RUNTIME_CAPABILITY_EVIDENCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def fixture_paths(root: Path) -> dict[str, Path]:
    return {
        "contract": root / "contract.json",
        "capability": root / "runtime_capability.odin",
        "progression": root / "runtime_progression.odin",
        "boot": root / "boot.asm",
        "report": root / "kernel_elf_report.json",
        "stages": root / "runtime_progression_stages.json",
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
        "_CAPABILITY_SOURCE_PATH": paths["capability"],
        "_PROGRESSION_SOURCE_PATH": paths["progression"],
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
        record = document["first_governed_runtime_capability"] | {field: value}
        return document | {"first_governed_runtime_capability": record}

    return mutate


def replace_stage_status(stage_name, status):
    def mutate(document):
        stages = [
            stage | {"status": status} if stage["stage_name"] == stage_name else stage
            for stage in document["stages"]
        ]
        return document | {"stages": stages}

    return mutate


def remove_source_line(target):
    def mutate(source):
        return source.replace(target, "")

    return mutate
