from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness import memory_initialization_evidence_contract as contract_module
from harness.codes import MEMORY_INITIALIZATION_EVIDENCE_CONTRACT_INVALID, OK
from harness.validators_impl import memory_initialization_evidence_contract as validator_module
from harness.validators_impl.memory_initialization_evidence_contract import (
    MemoryInitializationEvidenceContractValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "memory_initialization_evidence_contract": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_contract_schema_is_violated",
        "wrong_region_start_symbol": "test_fails_when_region_start_symbol_is_wrong",
        "wrong_region_size": "test_fails_when_region_size_is_wrong",
        "invalid_region_geometry": "test_fails_when_region_alignment_is_not_power_of_two",
        "wrong_region_owner": "test_fails_when_region_owner_is_wrong",
        "wrong_initialization_operation": "test_fails_when_initialization_operation_is_wrong",
        "incomplete_initialization_coverage": "test_fails_when_initialization_does_not_cover_entire_region",
        "wrong_probe_steps": "test_fails_when_probe_steps_are_out_of_order",
        "probe_out_of_bounds": "test_fails_when_probe_is_out_of_bounds",
        "missing_marker": "test_fails_when_memory_marker_is_missing",
        "wrong_marker_predecessors": "test_fails_when_marker_predecessor_is_missing",
        "wrong_marker_successor": "test_fails_when_marker_is_not_before_progression_entry",
        "missing_prerequisite": "test_fails_when_prerequisite_is_missing",
        "missing_evidence_requirement": "test_fails_when_evidence_requirement_is_missing",
        "missing_assumption_mapping": "test_fails_when_assumption_mapping_is_missing",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "marker_not_emitted": "test_fails_when_memory_marker_is_not_marked_emitted",
        "memory_implementation_missing": "test_fails_when_memory_implementation_is_not_recorded",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class MemoryInitializationEvidenceContractValidatorTests(unittest.TestCase):
    def test_passes_when_memory_evidence_contract_matches_governance(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_contract_is_missing(self):
        result = self.validate_fixture(remove_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        result = self.validate_fixture(mutate_contract_text=lambda _: "{not json")

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_violated(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {"version": 1}
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_region_start_symbol_is_wrong(self):
        result = self.validate_fixture(
            mutate_contract=replace_section("controlled_region", start_symbol="wrong_region")
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "wrong_region_start_symbol",
            "controlled_region.start_symbol",
        )

    def test_fails_when_region_size_is_wrong(self):
        result = self.validate_fixture(
            mutate_contract=replace_section("controlled_region", size_bytes=8192)
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "wrong_region_size", "controlled_region.size_bytes")

    def test_fails_when_region_alignment_is_not_power_of_two(self):
        result = self.validate_fixture(
            mutate_contract=replace_section("controlled_region", alignment_bytes=3000)
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "invalid_region_geometry",
            "controlled_region.alignment_bytes",
        )

    def test_fails_when_region_owner_is_wrong(self):
        result = self.validate_fixture(
            mutate_contract=replace_section("controlled_region", owner="unowned")
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "wrong_region_owner", "controlled_region.owner")

    def test_fails_when_initialization_operation_is_wrong(self):
        result = self.validate_fixture(
            mutate_contract=replace_section("initialization_operation", operation="copy")
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "wrong_initialization_operation",
            "initialization_operation.operation",
        )

    def test_fails_when_initialization_does_not_cover_entire_region(self):
        result = self.validate_fixture(
            mutate_contract=replace_section("initialization_operation", coverage="probe_word_only")
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "incomplete_initialization_coverage",
            "initialization_operation.coverage",
        )

    def test_fails_when_probe_steps_are_out_of_order(self):
        result = self.validate_fixture(
            mutate_contract=replace_section(
                "survival_probe",
                required_steps=[
                    "read_sentinel",
                    "write_sentinel",
                    "compare_equal",
                    "restore_fill_value",
                ],
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "wrong_probe_steps", "survival_probe.required_steps")

    def test_fails_when_probe_is_out_of_bounds(self):
        result = self.validate_fixture(
            mutate_contract=replace_section("survival_probe", offset_bytes=4096)
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "probe_out_of_bounds", "survival_probe.offset_bytes")

    def test_fails_when_memory_marker_is_missing(self):
        result = self.validate_fixture(
            mutate_contract=replace_section(
                "marker_placement",
                reserved_marker="KOZO_WRONG_MEMORY_MARKER",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "missing_marker", "marker_placement.reserved_marker")

    def test_fails_when_marker_predecessor_is_missing(self):
        result = self.validate_fixture(
            mutate_contract=replace_section(
                "marker_placement",
                required_after=["controlled_region_zero_fill"],
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "wrong_marker_predecessors",
            "marker_placement.required_after",
        )

    def test_fails_when_marker_is_not_before_progression_entry(self):
        result = self.validate_fixture(
            mutate_contract=replace_section(
                "marker_placement",
                required_before="halt_loop",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "wrong_marker_successor",
            "marker_placement.required_before",
        )

    def test_fails_when_memory_marker_is_not_marked_emitted(self):
        result = self.validate_fixture(
            mutate_contract=replace_section("marker_placement", marker_emitted=False)
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "marker_not_emitted", "marker_placement.marker_emitted")

    def test_fails_when_memory_implementation_is_not_recorded(self):
        result = self.validate_fixture(
            mutate_contract=replace_section("current_state", implemented=False)
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "memory_implementation_missing", "current_state.implemented")

    def test_fails_when_prerequisite_is_missing(self):
        result = self.validate_fixture(
            mutate_contract=remove_list_value("prerequisites", "stack initialization evidence")
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "missing_prerequisite",
            "prerequisites.stack initialization evidence",
        )

    def test_fails_when_evidence_requirement_is_missing(self):
        value = "entire controlled region zero-filled by runtime code"
        result = self.validate_fixture(
            mutate_contract=remove_list_value("evidence_requirements", value)
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "missing_evidence_requirement",
            f"evidence_requirements.{value}",
        )

    def test_fails_when_assumption_mapping_is_missing(self):
        value = "bounded access to the contract-owned controlled region after the proven memory marker"
        result = self.validate_fixture(
            mutate_contract=remove_list_value("assumptions_enabled", value)
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "missing_assumption_mapping",
            f"assumptions_enabled.{value}",
        )

    def test_fails_when_non_goal_is_missing(self):
        result = self.validate_fixture(
            mutate_contract=remove_list_value("non_goals", "virtual memory management")
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "missing_non_goal",
            "non_goals.virtual memory management",
        )

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {"architecture": "aarch64"}
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, MEMORY_INITIALIZATION_EVIDENCE_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], "wrong_architecture")
        self.assertEqual(result.meta["contract_field"], "architecture")

    def validate_fixture(
        self,
        *,
        remove_contract: bool = False,
        mutate_contract=None,
        mutate_contract_text=None,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = write_fixture_files(root)
            mutate_fixture(contract_path, remove_contract, mutate_contract, mutate_contract_text)
            old_paths = patch_validator_paths(root, contract_path)
            try:
                return MemoryInitializationEvidenceContractValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_memory_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, MEMORY_INITIALIZATION_EVIDENCE_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> Path:
    contracts_dir = root / "contracts"
    contracts_dir.mkdir(parents=True)
    contract_path = contracts_dir / "memory_initialization_evidence_contract.v0.json"
    contract_path.write_text(json.dumps(valid_contract(), indent=2) + "\n")
    for name in referenced_contract_names():
        (contracts_dir / name).write_text("{}\n")
    return contract_path


def referenced_contract_names() -> tuple[str, ...]:
    return (
        "runtime_halt_contract.v0.json",
        "runtime_progression_stages.v0.json",
        "stack_initialization_evidence_contract.v0.json",
    )


def mutate_fixture(contract_path, remove_contract, mutate_contract, mutate_contract_text):
    if remove_contract:
        contract_path.unlink()
        return
    if mutate_contract_text is not None:
        contract_path.write_text(mutate_contract_text(contract_path.read_text()))
        return
    if mutate_contract is not None:
        contract = json.loads(contract_path.read_text())
        contract_path.write_text(json.dumps(mutate_contract(contract), indent=2) + "\n")


def replace_section(section: str, **updates):
    def mutate(contract):
        return contract | {section: contract[section] | updates}

    return mutate


def remove_list_value(field: str, value: str):
    def mutate(contract):
        return contract | {field: [item for item in contract[field] if item != value]}

    return mutate


def valid_contract() -> dict[str, object]:
    return json.loads(contract_module.CONTRACT_PATH.read_text())


def patch_validator_paths(root: Path, contract_path: Path):
    old_paths = {
        "validator_contract": validator_module._CONTRACT_PATH,
        "contract_root": contract_module.ROOT,
    }
    validator_module._CONTRACT_PATH = contract_path
    contract_module.ROOT = root
    return old_paths


def restore_validator_paths(old_paths):
    validator_module._CONTRACT_PATH = old_paths["validator_contract"]
    contract_module.ROOT = old_paths["contract_root"]


if __name__ == "__main__":
    unittest.main()
