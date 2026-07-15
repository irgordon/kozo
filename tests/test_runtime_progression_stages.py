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
        "duplicate_stage_id": "test_fails_when_stage_identifier_is_duplicated",
        "duplicate_stage_name": "test_fails_when_stage_name_is_duplicated",
        "non_monotonic_stage_id": "test_fails_when_stage_identifier_order_is_not_monotonic",
        "missing_prerequisite": "test_fails_when_mandatory_prerequisite_is_missing",
        "unknown_stage_reference": "test_fails_when_prerequisite_references_unknown_stage",
        "direct_cycle": "test_fails_when_prerequisite_has_direct_cycle",
        "indirect_cycle": "test_fails_when_prerequisites_have_indirect_cycle",
        "forward_prerequisite": "test_fails_when_prerequisite_points_forward",
        "unproven_prerequisite": "test_fails_when_proven_stage_has_planned_prerequisite",
        "backward_transition": "test_fails_when_allowed_transition_moves_backward",
        "skipped_mandatory_stage": "test_fails_when_allowed_transition_skips_stage",
        "duplicate_transition_ownership": "test_fails_when_transition_has_multiple_owners",
        "transition_ownership_mismatch": "test_fails_when_transition_ownership_is_missing",
        "unknown_required_contract": "test_fails_when_required_contract_is_unknown",
        "unknown_required_validator": "test_fails_when_required_validator_is_unknown",
        "missing_forbidden_shortcut": "test_fails_when_forbidden_shortcut_is_missing",
        "missing_evidence_requirement": "test_fails_when_stage_evidence_is_missing",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class RuntimeProgressionStagesValidatorTests(unittest.TestCase):
    def test_passes_when_reconciled_graph_matches_governance(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_contract_is_missing(self):
        result = self.validate_fixture(remove_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        result = self.validate_fixture(mutate_contract_text=lambda _: "{not json")

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_violated(self):
        result = self.validate_fixture(mutate_contract=lambda contract: contract | {"version": 1})

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_stage_is_missing(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "stages": [stage for stage in contract["stages"] if stage["stage_name"] != "STACK_INITIALIZATION_EVIDENCE"]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "missing_stage", "stages")

    def test_fails_when_stage_identifier_is_duplicated(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: update_stage(contract, "STACK_INITIALIZATION_EVIDENCE", stage_id=0)
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "duplicate_stage_id", "stages.stage_id")

    def test_fails_when_stage_name_is_duplicated(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: update_stage(contract, "STACK_INITIALIZATION_EVIDENCE", stage_name="BOOT_SMOKE")
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "duplicate_stage_name", "stages.stage_name")

    def test_fails_when_stage_identifier_order_is_not_monotonic(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: update_stage(contract, "STACK_INITIALIZATION_EVIDENCE", stage_id=8)
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "non_monotonic_stage_id", "stages.stage_id")

    def test_fails_when_mandatory_prerequisite_is_missing(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: update_stage(contract, "STACK_INITIALIZATION_EVIDENCE", required_prerequisites=[])
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "missing_prerequisite",
            "stages.STACK_INITIALIZATION_EVIDENCE.required_prerequisites",
        )

    def test_fails_when_prerequisite_references_unknown_stage(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: update_stage(contract, "STACK_INITIALIZATION_EVIDENCE", required_prerequisites=["UNKNOWN_STAGE"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "unknown_stage_reference",
            "stages.STACK_INITIALIZATION_EVIDENCE.required_prerequisites.UNKNOWN_STAGE",
        )

    def test_fails_when_prerequisite_has_direct_cycle(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: update_stage(contract, "STACK_INITIALIZATION_EVIDENCE", required_prerequisites=["STACK_INITIALIZATION_EVIDENCE"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "direct_cycle",
            "stages.STACK_INITIALIZATION_EVIDENCE.required_prerequisites.STACK_INITIALIZATION_EVIDENCE",
        )

    def test_fails_when_prerequisites_have_indirect_cycle(self):
        result = self.validate_fixture(mutate_contract=add_indirect_cycle)

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "indirect_cycle", "stages.BOOT_SMOKE.required_prerequisites")

    def test_fails_when_prerequisite_points_forward(self):
        result = self.validate_fixture(mutate_contract=add_acyclic_forward_prerequisite)

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "forward_prerequisite",
            "stages.STACK_INITIALIZATION_EVIDENCE.required_prerequisites.MEMORY_INITIALIZATION_EVIDENCE",
        )

    def test_fails_when_proven_stage_has_planned_prerequisite(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: update_stage(contract, "BOOT_SMOKE", status="planned")
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "unproven_prerequisite",
            "stages.STACK_INITIALIZATION_EVIDENCE.status",
        )

    def test_fails_when_allowed_transition_moves_backward(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: update_stage(contract, "MEMORY_INITIALIZATION_EVIDENCE", allowed_next_stages=["STACK_INITIALIZATION_EVIDENCE"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "backward_transition",
            "stages.MEMORY_INITIALIZATION_EVIDENCE.allowed_next_stages",
        )

    def test_fails_when_allowed_transition_skips_stage(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: update_stage(contract, "BOOT_SMOKE", allowed_next_stages=["MEMORY_INITIALIZATION_EVIDENCE"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "skipped_mandatory_stage",
            "stages.BOOT_SMOKE.allowed_next_stages",
        )

    def test_fails_when_transition_has_multiple_owners(self):
        result = self.validate_fixture(mutate_contract=duplicate_first_transition)

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "duplicate_transition_ownership",
            "transitions.BOOT_SMOKE.STACK_INITIALIZATION_EVIDENCE.owner_contract",
        )

    def test_fails_when_transition_ownership_is_missing(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {"transitions": contract["transitions"][1:]}
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(result, "transition_ownership_mismatch", "transitions")

    def test_fails_when_required_contract_is_unknown(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: update_stage(contract, "STACK_INITIALIZATION_EVIDENCE", required_contracts=["unknown_contract"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "unknown_required_contract",
            "stages.STACK_INITIALIZATION_EVIDENCE.required_contracts.unknown_contract",
        )

    def test_fails_when_required_validator_is_unknown(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: update_stage(contract, "STACK_INITIALIZATION_EVIDENCE", required_validators=["unknown_validator"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "unknown_required_validator",
            "stages.STACK_INITIALIZATION_EVIDENCE.required_validators.unknown_validator",
        )

    def test_fails_when_stage_evidence_is_missing(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: update_stage(contract, "BOOT_SMOKE", required_evidence=["wrong evidence"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_stages_failure(
            result,
            "missing_evidence_requirement",
            "stages.BOOT_SMOKE.required_evidence.artifacts/runtime/qemu_smoke.metadata.json",
        )

    def test_fails_when_forbidden_shortcut_is_missing(self):
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
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "non_goals": [value for value in contract["non_goals"] if value != "userspace execution"]
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

    def validate_fixture(self, *, remove_contract=False, mutate_contract=None, mutate_contract_text=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = write_fixture_files(root)
            mutate_fixture(contract_path, remove_contract, mutate_contract, mutate_contract_text)
            old_paths = patch_validator_paths(root, contract_path)
            try:
                return RuntimeProgressionStagesValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_stages_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_PROGRESSION_STAGES_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def mutate_fixture(contract_path, remove_contract, mutate_contract, mutate_contract_text):
    if remove_contract:
        contract_path.unlink()
    elif mutate_contract_text is not None:
        contract_path.write_text(mutate_contract_text(contract_path.read_text()))
    elif mutate_contract is not None:
        contract = json.loads(contract_path.read_text())
        contract_path.write_text(json.dumps(mutate_contract(contract), indent=2) + "\n")


def write_fixture_files(root: Path) -> Path:
    contract_path = root / "contracts" / "runtime_progression_stages.v0.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(json.dumps(valid_contract(), indent=2) + "\n")
    for contract_name in required_contract_files():
        (contract_path.parent / contract_name).write_text("{}\n")
    return contract_path


def required_contract_files() -> tuple[str, ...]:
    return (
        "runtime_halt_contract.v0.json",
        "runtime_evidence_taxonomy.v0.json",
        "runtime_progression_contract.v0.json",
        "runtime_progression_entry_contract.v0.json",
        "stack_initialization_evidence_contract.v0.json",
        "memory_initialization_evidence_contract.v0.json",
    )


def valid_contract() -> dict[str, object]:
    return {
        "version": 0,
        "architecture": "x86_64",
        "current_state": {
            "path": "boot_smoke_to_stack_evidence_to_halt",
            "halt_contract": "contracts/runtime_halt_contract.v0.json",
            "progression_contract": "contracts/runtime_progression_contract.v0.json",
            "progression_entry_contract": "contracts/runtime_progression_entry_contract.v0.json",
            "terminal_behavior": "halt_loop",
        },
        "stages": valid_stages(),
        "transitions": valid_transitions(),
        "transition_requirements": [
            "runtime_halt_contract remains authoritative until runtime progression entry evidence exists",
            "runtime_progression_stages contract owns canonical stage order and allowed transitions",
            "transition owner contracts own destination-stage proof boundaries",
            "evidence contracts must not redefine canonical stage order",
            "stages must advance in declared order unless a later contract explicitly supersedes this stage model",
            "halt replacement requires contract-backed progression entry evidence",
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
            "general stack readiness",
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
    names = stage_names()
    statuses = {"BOOT_SMOKE": "proven", "STACK_INITIALIZATION_EVIDENCE": "proven"}
    return [
        {
            "stage_id": index,
            "stage_name": name,
            "description": f"{name} stage",
            "status": statuses.get(name, "planned"),
            "required_prerequisites": names[index - 1:index] if index else [],
            "required_evidence": [required_evidence()[name]],
            "required_contracts": [required_contracts()[name]],
            "required_validators": [required_validators()[name]],
            "allowed_next_stages": names[index + 1:index + 2],
            "forbidden_shortcuts": [f"{name} shortcut"],
        }
        for index, name in enumerate(names)
    ]


def stage_names() -> list[str]:
    return [
        "BOOT_SMOKE",
        "STACK_INITIALIZATION_EVIDENCE",
        "MEMORY_INITIALIZATION_EVIDENCE",
        "RUNTIME_PROGRESSION_ENTRY",
        "RUNTIME_INITIALIZATION_EVIDENCE",
        "CONTROLLED_RUNTIME_LOOP",
        "FIRST_GOVERNED_RUNTIME_CAPABILITY",
        "USERSPACE_PLANNING",
    ]


def required_evidence() -> dict[str, str]:
    return {
        "BOOT_SMOKE": "artifacts/runtime/qemu_smoke.metadata.json",
        "STACK_INITIALIZATION_EVIDENCE": "QEMU evidence for KOZO_STACK_INIT_OK",
        "MEMORY_INITIALIZATION_EVIDENCE": "QEMU evidence for KOZO_MEMORY_INIT_OK",
        "RUNTIME_PROGRESSION_ENTRY": "QEMU evidence for KOZO_RUNTIME_PROGRESS_ENTRY",
        "RUNTIME_INITIALIZATION_EVIDENCE": "QEMU evidence for runtime initialization marker",
        "CONTROLLED_RUNTIME_LOOP": "QEMU evidence for controlled runtime loop",
        "FIRST_GOVERNED_RUNTIME_CAPABILITY": "QEMU evidence for first governed runtime capability",
        "USERSPACE_PLANNING": "userspace planning evidence",
    }


def required_contracts() -> dict[str, str]:
    return {
        "BOOT_SMOKE": "contracts/runtime_halt_contract.v0.json",
        "STACK_INITIALIZATION_EVIDENCE": "contracts/stack_initialization_evidence_contract.v0.json",
        "MEMORY_INITIALIZATION_EVIDENCE": "contracts/memory_initialization_evidence_contract.v0.json",
        "RUNTIME_PROGRESSION_ENTRY": "contracts/runtime_progression_entry_contract.v0.json",
        "RUNTIME_INITIALIZATION_EVIDENCE": "planned:runtime_initialization_contract",
        "CONTROLLED_RUNTIME_LOOP": "planned:controlled_runtime_loop_contract",
        "FIRST_GOVERNED_RUNTIME_CAPABILITY": "planned:first_governed_runtime_capability_contract",
        "USERSPACE_PLANNING": "planned:userspace_planning_contract",
    }


def required_validators() -> dict[str, str]:
    return {
        "BOOT_SMOKE": "qemu_smoke_evidence",
        "STACK_INITIALIZATION_EVIDENCE": "stack_initialization_evidence",
        "MEMORY_INITIALIZATION_EVIDENCE": "memory_initialization_evidence_contract",
        "RUNTIME_PROGRESSION_ENTRY": "runtime_progression_entry_contract",
        "RUNTIME_INITIALIZATION_EVIDENCE": "planned:runtime_initialization_evidence",
        "CONTROLLED_RUNTIME_LOOP": "planned:controlled_runtime_loop_evidence",
        "FIRST_GOVERNED_RUNTIME_CAPABILITY": "planned:first_governed_runtime_capability_evidence",
        "USERSPACE_PLANNING": "planned:userspace_planning",
    }


def valid_transitions() -> list[dict[str, str]]:
    owners = (
        "contracts/stack_initialization_evidence_contract.v0.json",
        "contracts/memory_initialization_evidence_contract.v0.json",
        "contracts/runtime_progression_entry_contract.v0.json",
        "planned:runtime_initialization_contract",
        "planned:controlled_runtime_loop_contract",
        "planned:first_governed_runtime_capability_contract",
        "planned:userspace_planning_contract",
    )
    names = stage_names()
    return [
        {"from_stage": names[index], "to_stage": names[index + 1], "owner_contract": owner}
        for index, owner in enumerate(owners)
    ]


def update_stage(contract: dict[str, object], target: str, **changes) -> dict[str, object]:
    return contract | {
        "stages": [
            stage | changes if stage["stage_name"] == target else stage
            for stage in contract["stages"]
        ]
    }


def add_indirect_cycle(contract: dict[str, object]) -> dict[str, object]:
    contract = update_stage(contract, "BOOT_SMOKE", required_prerequisites=["MEMORY_INITIALIZATION_EVIDENCE"])
    return update_stage(contract, "MEMORY_INITIALIZATION_EVIDENCE", required_prerequisites=["BOOT_SMOKE"])


def add_acyclic_forward_prerequisite(contract: dict[str, object]) -> dict[str, object]:
    contract = update_stage(contract, "MEMORY_INITIALIZATION_EVIDENCE", required_prerequisites=["BOOT_SMOKE"])
    return update_stage(contract, "STACK_INITIALIZATION_EVIDENCE", required_prerequisites=["MEMORY_INITIALIZATION_EVIDENCE"])


def duplicate_first_transition(contract: dict[str, object]) -> dict[str, object]:
    duplicate = contract["transitions"][0] | {"owner_contract": "contracts/runtime_progression_entry_contract.v0.json"}
    return contract | {"transitions": [*contract["transitions"], duplicate]}


def patch_validator_paths(root: Path, contract_path: Path):
    old_paths = {"validator_contract": validator_module._CONTRACT_PATH, "contract_root": contract_module.ROOT}
    validator_module._CONTRACT_PATH = contract_path
    contract_module.ROOT = root
    return old_paths


def restore_validator_paths(old_paths):
    validator_module._CONTRACT_PATH = old_paths["validator_contract"]
    contract_module.ROOT = old_paths["contract_root"]


if __name__ == "__main__":
    unittest.main()
