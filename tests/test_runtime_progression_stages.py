from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness import runtime_progression_stages as contract_module
from harness.codes import OK, RUNTIME_PROGRESSION_STAGES_INVALID
from harness.validators_impl import runtime_progression_stages as validator_module
from harness.validators_impl.runtime_progression_stages import RuntimeProgressionStagesValidator

KOZO_NEGATIVE_COVERAGE = {
    "runtime_progression_stages": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_contract_schema_is_violated",
        "missing_stage": "test_fails_when_stage_is_missing",
        "duplicate_stage": "test_fails_when_stage_identifier_is_duplicated",
        "missing_prerequisite": "test_fails_when_stage_prerequisite_is_missing",
        "invalid_transition": "test_fails_when_allowed_transition_is_invalid",
        "missing_forbidden_shortcut": "test_fails_when_forbidden_shortcut_is_missing",
        "missing_evidence_requirement": "test_fails_when_stage_evidence_is_missing",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class RuntimeProgressionStagesValidatorTests(unittest.TestCase):
    def test_passes_when_progression_stages_contract_matches_governance(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_contract_is_missing(self):
        self.assertEqual("runtime_progression_stages", RuntimeProgressionStagesValidator.name)
        result = self.validate_fixture(remove_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        self.assertEqual("runtime_progression_stages", RuntimeProgressionStagesValidator.name)
        result = self.validate_fixture(mutate_contract_text=lambda _: "{not json")

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_violated(self):
        self.assertEqual("runtime_progression_stages", RuntimeProgressionStagesValidator.name)
        result = self.validate_fixture(mutate_contract=lambda contract: contract | {"version": 1})

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_stage_is_missing(self):
        self.assertEqual("runtime_progression_stages", RuntimeProgressionStagesValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "stages": [
                    stage for stage in contract["stages"]
                    if stage["stage_name"] != "STACK_INITIALIZATION_EVIDENCE"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "missing_stage", "stages")

    def test_fails_when_stage_identifier_is_duplicated(self):
        self.assertEqual("runtime_progression_stages", RuntimeProgressionStagesValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "stages": [
                    stage if stage["stage_name"] != "STACK_INITIALIZATION_EVIDENCE"
                    else stage | {"stage_id": 1}
                    for stage in contract["stages"]
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "duplicate_stage", "stages.stage_id")

    def test_fails_when_stage_prerequisite_is_missing(self):
        self.assertEqual("runtime_progression_stages", RuntimeProgressionStagesValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "stages": [
                    stage if stage["stage_name"] != "BOOT_SMOKE"
                    else stage | {
                        "required_prerequisites": ["wrong prerequisite"]
                    }
                    for stage in contract["stages"]
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "missing_prerequisite",
            "stages.BOOT_SMOKE.required_prerequisites.runtime halt contract",
        )

    def test_fails_when_stage_evidence_is_missing(self):
        self.assertEqual("runtime_progression_stages", RuntimeProgressionStagesValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "stages": [
                    stage if stage["stage_name"] != "BOOT_SMOKE"
                    else stage | {
                        "required_evidence": ["wrong evidence"]
                    }
                    for stage in contract["stages"]
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "missing_evidence_requirement",
            "stages.BOOT_SMOKE.required_evidence.artifacts/runtime/qemu_smoke.metadata.json",
        )

    def test_fails_when_allowed_transition_is_invalid(self):
        self.assertEqual("runtime_progression_stages", RuntimeProgressionStagesValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "stages": [
                    stage if stage["stage_name"] != "BOOT_SMOKE"
                    else stage | {"allowed_next_stages": ["USERSPACE_PLANNING"]}
                    for stage in contract["stages"]
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "invalid_transition", "stages.BOOT_SMOKE.allowed_next_stages")

    def test_fails_when_forbidden_shortcut_is_missing(self):
        self.assertEqual("runtime_progression_stages", RuntimeProgressionStagesValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "forbidden_global_shortcuts": [
                    value for value in contract["forbidden_global_shortcuts"]
                    if value != "delete halt loop without progression evidence"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "missing_forbidden_shortcut",
            "forbidden_global_shortcuts.delete halt loop without progression evidence",
        )

    def test_fails_when_non_goal_is_missing(self):
        self.assertEqual("runtime_progression_stages", RuntimeProgressionStagesValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "non_goals": [
                    value for value in contract["non_goals"]
                    if value != "userspace execution"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "missing_non_goal", "non_goals.userspace execution")

    def test_failure_diagnostic_names_field(self):
        self.assertEqual("runtime_progression_stages", RuntimeProgressionStagesValidator.name)
        result = self.validate_fixture(mutate_contract=lambda contract: contract | {"architecture": "aarch64"})

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_PROGRESSION_STAGES_INVALID)
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
            paths = write_fixture_files(root)
            if remove_contract:
                paths["contract"].unlink()
            elif mutate_contract_text is not None:
                paths["contract"].write_text(mutate_contract_text(paths["contract"].read_text()))
            elif mutate_contract is not None:
                contract = json.loads(paths["contract"].read_text())
                paths["contract"].write_text(json.dumps(mutate_contract(contract), indent=2) + "\n")

            old_paths = patch_validator_paths(root, paths["contract"])
            try:
                return RuntimeProgressionStagesValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_stages_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_PROGRESSION_STAGES_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> dict[str, Path]:
    contract_path = root / "contracts" / "runtime_progression_stages.v0.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(json.dumps(valid_contract(), indent=2) + "\n")
    for contract_name in (
        "runtime_halt_contract.v0.json",
        "runtime_progression_contract.v0.json",
        "runtime_progression_entry_contract.v0.json",
    ):
        (contract_path.parent / contract_name).write_text("{}\n")
    return {"contract": contract_path}


def valid_contract() -> dict[str, object]:
    return {
        "version": 0,
        "architecture": "x86_64",
        "current_state": {
            "path": "boot_smoke_to_halt",
            "halt_contract": "contracts/runtime_halt_contract.v0.json",
            "progression_contract": "contracts/runtime_progression_contract.v0.json",
            "progression_entry_contract": "contracts/runtime_progression_entry_contract.v0.json",
            "terminal_behavior": "halt_loop",
        },
        "stages": valid_stages(),
        "transition_requirements": [
            "runtime_halt_contract remains authoritative until runtime progression evidence exists",
            "stages must advance in declared order unless a later contract explicitly supersedes this stage model",
            "halt replacement requires contract-backed progression evidence",
            "planning stages do not constitute runtime evidence",
        ],
        "forbidden_global_shortcuts": [
            "delete halt loop without progression evidence",
            "replace halt loop without progression evidence",
            "bypass halt loop without progression evidence",
            "jump around halt loop without progression evidence",
            "claim userspace execution from planning evidence",
            "claim production readiness from planning evidence",
        ],
        "non_goals": [
            "runtime progression execution",
            "halt loop replacement",
            "stack initialization",
            "memory initialization",
            "Odin runtime execution",
            "interrupt handling",
            "scheduler behavior",
            "userspace execution",
            "process model behavior",
            "VFS behavior",
            "device driver behavior",
            "Linux compatibility",
            "POSIX compatibility",
            "production readiness",
        ],
    }


def valid_stages() -> list[dict[str, object]]:
    names = [
        "BOOT_SMOKE",
        "RUNTIME_PROGRESSION_ENTRY",
        "STACK_INITIALIZATION_EVIDENCE",
        "MEMORY_INITIALIZATION_EVIDENCE",
        "RUNTIME_INITIALIZATION_EVIDENCE",
        "CONTROLLED_RUNTIME_LOOP",
        "FIRST_GOVERNED_RUNTIME_CAPABILITY",
        "USERSPACE_PLANNING",
    ]
    prerequisites = {
        "BOOT_SMOKE": "runtime halt contract",
        "RUNTIME_PROGRESSION_ENTRY": "runtime progression entry contract",
        "STACK_INITIALIZATION_EVIDENCE": "stack initialization evidence contract",
        "MEMORY_INITIALIZATION_EVIDENCE": "memory initialization contract",
        "RUNTIME_INITIALIZATION_EVIDENCE": "runtime initialization contract",
        "CONTROLLED_RUNTIME_LOOP": "halt replacement evidence",
        "FIRST_GOVERNED_RUNTIME_CAPABILITY": "first runtime capability contract",
        "USERSPACE_PLANNING": "userspace planning contract",
    }
    evidence = {
        "BOOT_SMOKE": "artifacts/runtime/qemu_smoke.metadata.json",
        "RUNTIME_PROGRESSION_ENTRY": "QEMU evidence for KOZO_RUNTIME_PROGRESS_ENTRY",
        "STACK_INITIALIZATION_EVIDENCE": "QEMU evidence for KOZO_STACK_INIT_OK",
        "MEMORY_INITIALIZATION_EVIDENCE": "QEMU evidence for memory initialization marker",
        "RUNTIME_INITIALIZATION_EVIDENCE": "QEMU evidence for runtime initialization marker",
        "CONTROLLED_RUNTIME_LOOP": "QEMU evidence for controlled runtime loop",
        "FIRST_GOVERNED_RUNTIME_CAPABILITY": "QEMU evidence for first governed runtime capability",
        "USERSPACE_PLANNING": "userspace planning evidence",
    }
    return [
        {
            "stage_id": index,
            "stage_name": name,
            "description": f"{name} stage",
            "status": "proven" if index == 0 else "planned",
            "required_prerequisites": [prerequisites[name]],
            "required_evidence": [evidence[name]],
            "required_contracts": [f"{name} contract"],
            "required_validators": [f"{name} validator"],
            "allowed_next_stages": names[index + 1:index + 2],
            "forbidden_shortcuts": [f"{name} shortcut"],
        }
        for index, name in enumerate(names)
    ]


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
