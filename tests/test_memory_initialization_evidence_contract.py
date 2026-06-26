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
        "missing_marker": "test_fails_when_memory_marker_is_missing",
        "missing_prerequisite": "test_fails_when_prerequisite_is_missing",
        "missing_assumption_mapping": "test_fails_when_assumption_mapping_is_missing",
        "missing_evidence_requirement": "test_fails_when_evidence_requirement_is_missing",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "marker_claimed": "test_fails_when_memory_marker_is_marked_emitted",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class MemoryInitializationEvidenceContractValidatorTests(unittest.TestCase):
    def test_passes_when_memory_evidence_contract_matches_governance(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_contract_is_missing(self):
        self.assertEqual(
            "memory_initialization_evidence_contract",
            MemoryInitializationEvidenceContractValidator.name,
        )
        result = self.validate_fixture(remove_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        self.assertEqual(
            "memory_initialization_evidence_contract",
            MemoryInitializationEvidenceContractValidator.name,
        )
        result = self.validate_fixture(mutate_contract_text=lambda _: "{not json")

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_violated(self):
        self.assertEqual(
            "memory_initialization_evidence_contract",
            MemoryInitializationEvidenceContractValidator.name,
        )
        result = self.validate_fixture(mutate_contract=lambda contract: contract | {"version": 1})

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_memory_marker_is_missing(self):
        self.assertEqual(
            "memory_initialization_evidence_contract",
            MemoryInitializationEvidenceContractValidator.name,
        )
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "memory_definition": contract["memory_definition"] | {
                    "reserved_marker": "KOZO_WRONG_MEMORY_MARKER"
                }
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "missing_marker", "memory_definition.reserved_marker")

    def test_fails_when_memory_marker_is_marked_emitted(self):
        self.assertEqual(
            "memory_initialization_evidence_contract",
            MemoryInitializationEvidenceContractValidator.name,
        )
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "memory_definition": contract["memory_definition"] | {
                    "marker_emitted": True
                }
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "marker_claimed", "memory_definition.marker_emitted")

    def test_fails_when_prerequisite_is_missing(self):
        self.assertEqual(
            "memory_initialization_evidence_contract",
            MemoryInitializationEvidenceContractValidator.name,
        )
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "prerequisites": [
                    value for value in contract["prerequisites"]
                    if value != "stack initialization evidence"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "missing_prerequisite",
            "prerequisites.stack initialization evidence",
        )

    def test_fails_when_evidence_requirement_is_missing(self):
        self.assertEqual(
            "memory_initialization_evidence_contract",
            MemoryInitializationEvidenceContractValidator.name,
        )
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "evidence_requirements": [
                    value for value in contract["evidence_requirements"]
                    if value != "memory structures initialized"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "missing_evidence_requirement",
            "evidence_requirements.memory structures initialized",
        )

    def test_fails_when_assumption_mapping_is_missing(self):
        self.assertEqual(
            "memory_initialization_evidence_contract",
            MemoryInitializationEvidenceContractValidator.name,
        )
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "assumptions_enabled": [
                    value for value in contract["assumptions_enabled"]
                    if value != "controlled memory access after the proven memory marker"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(
            result,
            "missing_assumption_mapping",
            "assumptions_enabled.controlled memory access after the proven memory marker",
        )

    def test_fails_when_non_goal_is_missing(self):
        self.assertEqual(
            "memory_initialization_evidence_contract",
            MemoryInitializationEvidenceContractValidator.name,
        )
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "non_goals": [
                    value for value in contract["non_goals"]
                    if value != "userspace execution"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_memory_failure(result, "missing_non_goal", "non_goals.userspace execution")

    def test_failure_diagnostic_names_field(self):
        self.assertEqual(
            "memory_initialization_evidence_contract",
            MemoryInitializationEvidenceContractValidator.name,
        )
        result = self.validate_fixture(mutate_contract=lambda contract: contract | {"architecture": "aarch64"})

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
                return MemoryInitializationEvidenceContractValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_memory_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, MEMORY_INITIALIZATION_EVIDENCE_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> dict[str, Path]:
    contract_path = root / "contracts" / "memory_initialization_evidence_contract.v0.json"
    halt_contract_path = root / "contracts" / "runtime_halt_contract.v0.json"
    stages_contract_path = root / "contracts" / "runtime_progression_stages.v0.json"
    stack_contract_path = root / "contracts" / "stack_initialization_evidence_contract.v0.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(json.dumps(valid_contract(), indent=2) + "\n")
    halt_contract_path.write_text("{}\n")
    stages_contract_path.write_text("{}\n")
    stack_contract_path.write_text("{}\n")
    return {
        "contract": contract_path,
        "halt_contract": halt_contract_path,
        "stages_contract": stages_contract_path,
        "stack_contract": stack_contract_path,
    }


def valid_contract() -> dict[str, object]:
    return {
        "version": 0,
        "architecture": "x86_64",
        "current_state": {
            "runtime_path": "boot_smoke_to_stack_evidence_to_halt",
            "halt_contract": "contracts/runtime_halt_contract.v0.json",
            "progression_stages_contract": "contracts/runtime_progression_stages.v0.json",
            "stack_initialization_evidence_contract": "contracts/stack_initialization_evidence_contract.v0.json",
            "stage": "MEMORY_INITIALIZATION_EVIDENCE",
            "implemented": False,
        },
        "memory_definition": {
            "description": "Memory initialization means future runtime code has a governed memory boundary.",
            "reserved_marker": "KOZO_MEMORY_INIT_OK",
            "marker_status": "reserved",
            "marker_emitted": False,
        },
        "prerequisites": [
            "QEMU serial smoke evidence",
            "runtime halt contract",
            "runtime progression contract",
            "runtime progression entry contract",
            "runtime progression stages contract",
            "stack initialization evidence",
            "stack initialization evidence contract",
        ],
        "evidence_requirements": [
            "memory structures initialized",
            "ownership documented",
            "controlled memory region",
            "KOZO_MEMORY_INIT_OK marker captured from runtime code",
            "memory initialization validator proof",
        ],
        "proof_boundary": [
            "evidence must come from runtime code, not scripts",
            "evidence must not replace the halt loop until runtime progression evidence permits it",
        ],
        "assumptions_enabled": [
            "controlled memory access after the proven memory marker",
            "runtime progression beyond stack evidence after the proven memory marker",
            "future runtime initialization after the proven memory marker",
        ],
        "assumptions_not_enabled": [
            "paging enabled",
            "allocator behavior",
            "heap allocation",
            "Odin runtime execution",
            "interrupt handling",
            "scheduler behavior",
            "userspace execution",
            "process model behavior",
            "VFS behavior",
            "device driver behavior",
            "syscall dispatch during boot",
            "production readiness",
        ],
        "future_validators": [
            "memory_initialization_evidence",
        ],
        "non_goals": [
            "memory initialization implementation",
            "paging implementation",
            "allocator behavior",
            "heap allocation",
            "Odin runtime execution",
            "runtime progression execution",
            "halt loop replacement",
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
