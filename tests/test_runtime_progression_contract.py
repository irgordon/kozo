from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness import runtime_progression_contract as contract_module
from harness.codes import OK, RUNTIME_PROGRESSION_CONTRACT_INVALID
from harness.validators_impl import runtime_progression_contract as validator_module
from harness.validators_impl.runtime_progression_contract import RuntimeProgressionContractValidator

KOZO_NEGATIVE_COVERAGE = {
    "runtime_progression_contract": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_contract_schema_is_violated",
        "missing_prerequisite": "test_fails_when_prerequisite_is_missing",
        "missing_halt_reference": "test_fails_when_halt_reference_is_missing",
        "missing_transition_requirement": "test_fails_when_transition_requirement_is_missing",
        "missing_forbidden_shortcut": "test_fails_when_forbidden_shortcut_is_missing",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class RuntimeProgressionContractValidatorTests(unittest.TestCase):
    def test_passes_when_runtime_progression_contract_matches_governance(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_contract_is_missing(self):
        self.assertEqual("runtime_progression_contract", RuntimeProgressionContractValidator.name)
        result = self.validate_fixture(remove_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_progression_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        self.assertEqual("runtime_progression_contract", RuntimeProgressionContractValidator.name)
        result = self.validate_fixture(mutate_contract_text=lambda _: "{not json")

        self.assertEqual(result.status, "fail")
        self.assert_progression_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_violated(self):
        self.assertEqual("runtime_progression_contract", RuntimeProgressionContractValidator.name)
        result = self.validate_fixture(mutate_contract=lambda contract: contract | {"version": 1})

        self.assertEqual(result.status, "fail")
        self.assert_progression_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_prerequisite_is_missing(self):
        self.assertEqual("runtime_progression_contract", RuntimeProgressionContractValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "progression_prerequisites": [
                    value for value in contract["progression_prerequisites"]
                    if value != "stack initialization evidence"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_progression_failure(
            result,
            "missing_prerequisite",
            "progression_prerequisites.stack initialization evidence",
        )

    def test_fails_when_halt_reference_is_missing(self):
        self.assertEqual("runtime_progression_contract", RuntimeProgressionContractValidator.name)
        result = self.validate_fixture(remove_halt_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_progression_failure(result, "missing_halt_reference", "current_state.halt_contract")

    def test_fails_when_transition_requirement_is_missing(self):
        self.assertEqual("runtime_progression_contract", RuntimeProgressionContractValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "transition_requirements": [
                    value for value in contract["transition_requirements"]
                    if value != "halt loop remains authoritative until runtime progression is separately proven"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_progression_failure(
            result,
            "missing_transition_requirement",
            "transition_requirements.halt loop remains authoritative until runtime progression is separately proven",
        )

    def test_fails_when_forbidden_shortcut_is_missing(self):
        self.assertEqual("runtime_progression_contract", RuntimeProgressionContractValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "forbidden_shortcuts": [
                    value for value in contract["forbidden_shortcuts"]
                    if value != "delete halt loop"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_progression_failure(
            result,
            "missing_forbidden_shortcut",
            "forbidden_shortcuts.delete halt loop",
        )

    def test_fails_when_non_goal_is_missing(self):
        self.assertEqual("runtime_progression_contract", RuntimeProgressionContractValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "non_goals": [
                    value for value in contract["non_goals"]
                    if value != "userspace execution"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_progression_failure(result, "missing_non_goal", "non_goals.userspace execution")

    def test_failure_diagnostic_names_field(self):
        self.assertEqual("runtime_progression_contract", RuntimeProgressionContractValidator.name)
        result = self.validate_fixture(mutate_contract=lambda contract: contract | {"architecture": "aarch64"})

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_PROGRESSION_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], "wrong_architecture")
        self.assertEqual(result.meta["contract_field"], "architecture")

    def validate_fixture(
        self,
        *,
        remove_contract: bool = False,
        remove_halt_contract: bool = False,
        mutate_contract=None,
        mutate_contract_text=None,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture_files(root)
            if remove_contract:
                paths["contract"].unlink()
            elif mutate_contract_text is not None:
                paths["contract"].write_text(mutate_contract_text(paths["contract"].read_text()))
            elif mutate_contract is not None:
                contract = json.loads(paths["contract"].read_text())
                paths["contract"].write_text(json.dumps(mutate_contract(contract), indent=2) + "\n")
            if remove_halt_contract:
                paths["halt_contract"].unlink()

            old_paths = patch_validator_paths(root, paths["contract"])
            try:
                return RuntimeProgressionContractValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_progression_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_PROGRESSION_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> dict[str, Path]:
    contract_path = root / "contracts" / "runtime_progression_contract.v0.json"
    halt_contract_path = root / "contracts" / "runtime_halt_contract.v0.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(json.dumps(valid_contract(), indent=2) + "\n")
    halt_contract_path.write_text("{}\n")
    return {
        "contract": contract_path,
        "halt_contract": halt_contract_path,
    }


def valid_contract() -> dict[str, object]:
    return {
        "version": 0,
        "architecture": "x86_64",
        "current_state": {
            "path": "boot_smoke_to_halt",
            "halt_contract": "contracts/runtime_halt_contract.v0.json",
            "final_smoke_marker": "KOZO_BOOT_SMOKE_OK",
            "terminal_behavior": "halt_loop",
        },
        "progression_prerequisites": [
            "stack initialization evidence",
            "stack initialization evidence contract",
            "runtime initialization evidence",
            "memory initialization evidence",
            "progression path evidence",
        ],
        "transition_requirements": [
            "halt loop remains authoritative until runtime progression is separately proven",
            "runtime progression must have contract-backed evidence before halt behavior changes",
            "runtime progression must preserve the existing QEMU smoke marker sequence until a successor evidence path is accepted",
            "runtime progression must update release evidence and validation before claims expand",
        ],
        "forbidden_shortcuts": [
            "delete halt loop",
            "replace halt loop",
            "bypass halt loop",
            "jump around halt loop",
        ],
        "future_runtime_milestones": [
            {"stage": 0, "name": "Boot smoke", "status": "proven"},
            {"stage": 1, "name": "Runtime progression entry", "status": "planned"},
            {"stage": 2, "name": "Stack initialization evidence", "status": "proven"},
            {"stage": 3, "name": "Runtime initialization evidence", "status": "planned"},
            {"stage": 4, "name": "Controlled runtime loop", "status": "planned"},
            {"stage": 5, "name": "First governed runtime capability", "status": "planned"},
            {"stage": 6, "name": "Userspace planning", "status": "planned"},
        ],
        "evidence_requirements": [
            "runtime progression contract",
            "stack initialization evidence contract",
            "focused validator coverage",
            "QEMU evidence for progression entry",
            "release evidence update",
            "planning document update",
        ],
        "non_goals": [
            "Odin runtime execution",
            "userspace execution",
            "interrupt handling",
            "scheduler behavior",
            "VFS behavior",
            "process model behavior",
            "syscall dispatch during boot",
            "memory manager behavior",
            "hardware trap handling",
            "device driver behavior",
            "Linux compatibility",
            "POSIX compatibility",
            "production readiness",
        ],
    }


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
