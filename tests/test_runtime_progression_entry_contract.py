from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness import runtime_progression_entry_contract as contract_module
from harness.codes import OK, RUNTIME_PROGRESSION_ENTRY_CONTRACT_INVALID
from harness.validators_impl import runtime_progression_entry_contract as validator_module
from harness.validators_impl.runtime_progression_entry_contract import RuntimeProgressionEntryContractValidator

KOZO_NEGATIVE_COVERAGE = {
    "runtime_progression_entry_contract": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_contract_schema_is_violated",
        "missing_prerequisite": "test_fails_when_prerequisite_is_missing",
        "missing_halt_reference": "test_fails_when_halt_reference_is_missing",
        "missing_progression_marker": "test_fails_when_progression_marker_is_missing",
        "wrong_calling_convention": "test_fails_when_calling_convention_is_wrong",
        "invalid_context_layout": "test_fails_when_context_field_order_is_wrong",
        "missing_transition_requirement": "test_fails_when_transition_requirement_is_missing",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class RuntimeProgressionEntryContractValidatorTests(unittest.TestCase):
    def test_valid_contract_passes(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_contract_is_missing(self):
        result = self.validate_fixture(remove_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        result = self.validate_fixture(mutate_text=lambda _: "{not json")

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_violated(self):
        result = self.validate_fixture(mutate_contract=lambda value: value | {"version": 1})

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_prerequisite_is_missing(self):
        result = self.validate_fixture(mutate_contract=remove_list_value("required_prerequisites", "memory initialization evidence"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_prerequisite", "required_prerequisites.memory initialization evidence")

    def test_fails_when_halt_reference_is_missing(self):
        result = self.validate_fixture(remove_halt_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_contract_reference", "current_state.halt_contract")

    def test_fails_when_progression_marker_is_missing(self):
        result = self.validate_fixture(mutate_contract=mutate_nested("progression_entry", "marker", "KOZO_WRONG_MARKER"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "progression_entry_mismatch", "progression_entry.marker")

    def test_fails_when_calling_convention_is_wrong(self):
        result = self.validate_fixture(mutate_contract=mutate_nested("calling_convention", "name", "Odin"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "calling_convention_mismatch", "calling_convention.name")

    def test_fails_when_context_field_order_is_wrong(self):
        def swap_fields(contract):
            fields = list(contract["bootstrap_context"]["fields"])
            fields[2], fields[3] = fields[3], fields[2]
            return contract | {"bootstrap_context": contract["bootstrap_context"] | {"fields": fields}}

        result = self.validate_fixture(mutate_contract=swap_fields)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "bootstrap_context_mismatch", "bootstrap_context.fields")

    def test_fails_when_transition_requirement_is_missing(self):
        requirement = "KOZO_RUNTIME_INIT_OK must originate from executed Odin code"
        result = self.validate_fixture(mutate_contract=remove_list_value("transition_requirements", requirement))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_transition_requirement", f"transition_requirements.{requirement}")

    def test_fails_when_non_goal_is_missing(self):
        result = self.validate_fixture(mutate_contract=remove_list_value("non_goals", "userspace execution"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_non_goal", "non_goals.userspace execution")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(mutate_contract=lambda value: value | {"architecture": "aarch64"})

        self.assertEqual(result.status, "fail")
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(self, **changes):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture(root)
            apply_changes(paths, changes)
            old = patch_paths(root, paths["contract"])
            try:
                return RuntimeProgressionEntryContractValidator().validate({})
            finally:
                restore_paths(old)

    def assert_failure(self, result, reason: str, field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_PROGRESSION_ENTRY_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def write_fixture(root: Path) -> dict[str, Path]:
    contracts = root / "contracts"
    contracts.mkdir(parents=True)
    paths = {
        "contract": contracts / "runtime_progression_entry_contract.v0.json",
        "halt": contracts / "runtime_halt_contract.v0.json",
        "progression": contracts / "runtime_progression_contract.v0.json",
        "stages": contracts / "runtime_progression_stages.v0.json",
    }
    paths["contract"].write_text(contract_module.CONTRACT_PATH.read_text())
    for name in ("halt", "progression", "stages"):
        paths[name].write_text("{}\n")
    return paths


def apply_changes(paths: dict[str, Path], changes: dict[str, object]) -> None:
    if changes.get("remove_contract"):
        paths["contract"].unlink()
        return
    if changes.get("mutate_text"):
        paths["contract"].write_text(changes["mutate_text"](paths["contract"].read_text()))
    if changes.get("mutate_contract"):
        contract = json.loads(paths["contract"].read_text())
        paths["contract"].write_text(json.dumps(changes["mutate_contract"](contract), indent=2) + "\n")
    if changes.get("remove_halt_contract"):
        paths["halt"].unlink()


def mutate_nested(section: str, field: str, value: object):
    return lambda contract: contract | {section: contract[section] | {field: value}}


def remove_list_value(field: str, removed: str):
    return lambda contract: contract | {field: [value for value in contract[field] if value != removed]}


def patch_paths(root: Path, path: Path):
    old = validator_module._CONTRACT_PATH, contract_module.ROOT
    validator_module._CONTRACT_PATH = path
    contract_module.ROOT = root
    return old


def restore_paths(old) -> None:
    validator_module._CONTRACT_PATH, contract_module.ROOT = old


if __name__ == "__main__":
    unittest.main()
