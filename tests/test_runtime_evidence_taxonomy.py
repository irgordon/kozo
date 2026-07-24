from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness import runtime_evidence_taxonomy as contract_module
from harness.codes import OK, RUNTIME_EVIDENCE_TAXONOMY_INVALID
from harness.validators_impl import runtime_evidence_taxonomy as validator_module
from harness.validators_impl.runtime_evidence_taxonomy import RuntimeEvidenceTaxonomyValidator

KOZO_NEGATIVE_COVERAGE = {
    "runtime_evidence_taxonomy": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_contract_schema_is_violated",
        "missing_marker": "test_fails_when_marker_is_missing",
        "wrong_marker_order": "test_fails_when_marker_order_is_wrong",
        "expected_marker_not_final": "test_fails_when_expected_marker_is_not_final",
        "missing_outcome": "test_fails_when_outcome_is_missing",
        "missing_blocker_category": "test_fails_when_blocker_category_is_missing",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class RuntimeEvidenceTaxonomyValidatorTests(unittest.TestCase):
    def test_passes_when_taxonomy_matches_governed_vocabulary(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_helper_reports_complete_ordered_marker_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture_files(root)
            old_paths = patch_validator_paths(root, paths["contract"])
            try:
                self.assertTrue(contract_module.is_complete_ordered_marker_sequence(valid_contract()["smoke_marker_order"]))
                self.assertFalse(contract_module.is_complete_ordered_marker_sequence(["KOZO_BOOT_SMOKE_OK"]))
            finally:
                restore_validator_paths(old_paths)

    def test_fails_when_contract_is_missing(self):
        self.assertEqual("runtime_evidence_taxonomy", RuntimeEvidenceTaxonomyValidator.name)
        result = self.validate_fixture(remove_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_taxonomy_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        self.assertEqual("runtime_evidence_taxonomy", RuntimeEvidenceTaxonomyValidator.name)
        result = self.validate_fixture(mutate_contract_text=lambda _: "{not json")

        self.assertEqual(result.status, "fail")
        self.assert_taxonomy_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_violated(self):
        self.assertEqual("runtime_evidence_taxonomy", RuntimeEvidenceTaxonomyValidator.name)
        result = self.validate_fixture(mutate_contract=lambda contract: contract | {"version": 1})

        self.assertEqual(result.status, "fail")
        self.assert_taxonomy_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_marker_is_missing(self):
        self.assertEqual("runtime_evidence_taxonomy", RuntimeEvidenceTaxonomyValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "smoke_markers": [
                    marker for marker in contract["smoke_markers"]
                    if marker != "KOZO_EARLY_0_ENTRY"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_taxonomy_failure(result, "missing_marker", "smoke_markers.KOZO_EARLY_0_ENTRY")

    def test_fails_when_marker_order_is_wrong(self):
        self.assertEqual("runtime_evidence_taxonomy", RuntimeEvidenceTaxonomyValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "smoke_marker_order": list(reversed(contract["smoke_marker_order"]))
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_taxonomy_failure(result, "wrong_marker_order", "smoke_marker_order")

    def test_fails_when_expected_marker_is_not_final(self):
        self.assertEqual("runtime_evidence_taxonomy", RuntimeEvidenceTaxonomyValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "expected_smoke_marker": "KOZO_EARLY_2_SERIAL_INIT_OK"
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_taxonomy_failure(result, "expected_marker_not_final", "expected_smoke_marker")

    def test_fails_when_outcome_is_missing(self):
        self.assertEqual("runtime_evidence_taxonomy", RuntimeEvidenceTaxonomyValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "smoke_outcomes": [
                    outcome for outcome in contract["smoke_outcomes"]
                    if outcome != "blocked"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_taxonomy_failure(result, "missing_outcome", "smoke_outcomes.blocked")

    def test_fails_when_blocker_category_is_missing(self):
        self.assertEqual("runtime_evidence_taxonomy", RuntimeEvidenceTaxonomyValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "blocker_categories": {
                    key: value
                    for key, value in contract["blocker_categories"].items()
                    if key != "kernel_not_loaded"
                }
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_taxonomy_failure(result, "missing_blocker_category", "blocker_categories.kernel_not_loaded")

    def test_fails_when_non_goal_is_missing(self):
        self.assertEqual("runtime_evidence_taxonomy", RuntimeEvidenceTaxonomyValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "non_goals": [
                    non_goal for non_goal in contract["non_goals"]
                    if non_goal != "production readiness"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_taxonomy_failure(result, "missing_non_goal", "non_goals.production readiness")

    def test_failure_diagnostic_names_field(self):
        self.assertEqual("runtime_evidence_taxonomy", RuntimeEvidenceTaxonomyValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "pass_condition": contract["pass_condition"] | {
                    "outcome": "blocked"
                }
            }
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_EVIDENCE_TAXONOMY_INVALID)
        self.assertEqual(result.meta["reason"], "missing_outcome")
        self.assertEqual(result.meta["contract_field"], "pass_condition.outcome")

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
                return RuntimeEvidenceTaxonomyValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_taxonomy_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_EVIDENCE_TAXONOMY_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> dict[str, Path]:
    contract_path = root / "contracts" / "runtime_evidence_taxonomy.v0.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(json.dumps(valid_contract(), indent=2) + "\n")
    return {"contract": contract_path}


def valid_contract() -> dict[str, object]:
    return {
        "version": 0,
        "smoke_markers": [
            "KOZO_EARLY_0_ENTRY",
            "KOZO_EARLY_1_SERIAL_INIT_START",
            "KOZO_EARLY_2_SERIAL_INIT_OK",
            "KOZO_BOOT_SMOKE_OK",
            "KOZO_STACK_INIT_OK",
            "KOZO_MEMORY_INIT_OK",
            "KOZO_RUNTIME_PROGRESS_ENTRY",
            "KOZO_RUNTIME_INIT_OK",
            "KOZO_RUNTIME_LOOP_ENTER",
            "KOZO_RUNTIME_LOOP_ITER_1",
            "KOZO_RUNTIME_LOOP_ITER_2",
            "KOZO_RUNTIME_LOOP_ITER_3",
            "KOZO_RUNTIME_LOOP_EXIT_OK",
            "KOZO_RUNTIME_RETURN_OK",
        ],
        "smoke_marker_order": [
            "KOZO_EARLY_0_ENTRY",
            "KOZO_EARLY_1_SERIAL_INIT_START",
            "KOZO_EARLY_2_SERIAL_INIT_OK",
            "KOZO_BOOT_SMOKE_OK",
            "KOZO_STACK_INIT_OK",
            "KOZO_MEMORY_INIT_OK",
            "KOZO_RUNTIME_PROGRESS_ENTRY",
            "KOZO_RUNTIME_INIT_OK",
            "KOZO_RUNTIME_LOOP_ENTER",
            "KOZO_RUNTIME_LOOP_ITER_1",
            "KOZO_RUNTIME_LOOP_ITER_2",
            "KOZO_RUNTIME_LOOP_ITER_3",
            "KOZO_RUNTIME_LOOP_EXIT_OK",
            "KOZO_RUNTIME_RETURN_OK",
        ],
        "expected_smoke_marker": "KOZO_RUNTIME_RETURN_OK",
        "smoke_outcomes": ["pass", "blocked"],
        "blocker_categories": {
            "none": "No active QEMU serial smoke blocker remains.",
            "limine_not_reached": "QEMU serial evidence did not show Limine reachability.",
            "kernel_not_loaded": "Limine did not load the KOZO kernel ELF.",
            "kernel_entry_not_reached": "Limine reported kernel entry evidence but KOZO entry marker was absent.",
            "serial_not_initialized": "KOZO entry was observed but serial initialization completion was absent.",
            "marker_not_emitted": "Early serial initialization was observed but the boot smoke marker was absent.",
            "stack_marker_not_emitted": "The boot smoke marker was observed but the stack initialization marker was absent.",
            "memory_marker_not_emitted": "The stack initialization marker was observed but the memory initialization marker was absent.",
            "runtime_progression_entry_not_reached": "Memory initialization evidence was observed but runtime progression entry was absent.",
            "runtime_initialization_not_proven": "Runtime progression entry was observed but Odin runtime initialization evidence was absent.",
            "runtime_loop_entry_not_reached": "Odin runtime initialization evidence was observed but controlled loop entry was absent.",
            "runtime_loop_iteration_incomplete": "Controlled loop entry was observed but the three ordered iteration markers were incomplete.",
            "runtime_loop_exit_not_reached": "All controlled loop iteration markers were observed but loop exit evidence was absent.",
            "runtime_return_not_reached": "Controlled loop exit evidence was observed but the governed return marker was absent.",
            "qemu_timeout": "QEMU execution timed out before a passing smoke sequence was observed.",
            "missing_qemu_tooling": "QEMU tooling is unavailable.",
            "missing_boot_image": "The QEMU smoke script cannot find the boot image.",
            "qemu_launch_failed": "QEMU launch failed.",
            "missing_iso_generation_tooling": "Local Limine or ISO generation tooling is unavailable.",
            "missing_qemu_serial_evidence": "QEMU serial evidence has not been captured.",
            "invalid_kernel_elf": "Kernel ELF structure is invalid.",
            "missing_load_segments": "Kernel ELF load segments are missing.",
            "invalid_kernel_entry": "Kernel ELF entry point is invalid.",
            "linker_output_invalid": "Kernel linker output is invalid.",
            "limine_lower_half_phdr": "Limine rejected lower-half kernel ELF program headers.",
        },
        "qemu_smoke_blockers": [
            "limine_not_reached",
            "kernel_not_loaded",
            "kernel_entry_not_reached",
            "serial_not_initialized",
            "marker_not_emitted",
            "stack_marker_not_emitted",
            "memory_marker_not_emitted",
            "runtime_progression_entry_not_reached",
            "runtime_initialization_not_proven",
            "runtime_loop_entry_not_reached",
            "runtime_loop_iteration_incomplete",
            "runtime_loop_exit_not_reached",
            "runtime_return_not_reached",
            "qemu_timeout",
            "missing_qemu_tooling",
            "missing_boot_image",
            "qemu_launch_failed",
            "missing_iso_generation_tooling",
            "limine_lower_half_phdr",
        ],
        "boot_blocker_categories": [
            "none",
            "missing_iso_generation_tooling",
            "missing_qemu_serial_evidence",
            "limine_not_reached",
            "kernel_not_loaded",
            "kernel_entry_not_reached",
            "serial_not_initialized",
            "marker_not_emitted",
            "stack_marker_not_emitted",
            "memory_marker_not_emitted",
            "runtime_progression_entry_not_reached",
            "runtime_initialization_not_proven",
            "runtime_loop_entry_not_reached",
            "runtime_loop_iteration_incomplete",
            "runtime_loop_exit_not_reached",
            "runtime_return_not_reached",
            "qemu_timeout",
            "missing_qemu_tooling",
            "missing_boot_image",
            "qemu_launch_failed",
            "invalid_kernel_elf",
            "missing_load_segments",
            "invalid_kernel_entry",
            "linker_output_invalid",
            "limine_lower_half_phdr",
        ],
        "kernel_elf_blockers": [
            "invalid_kernel_elf",
            "missing_load_segments",
            "invalid_kernel_entry",
            "linker_output_invalid",
            "limine_lower_half_phdr",
        ],
        "pass_condition": {
            "outcome": "pass",
            "required_marker_sequence": "full_ordered_smoke_marker_sequence",
            "expected_marker": "KOZO_RUNTIME_RETURN_OK",
        },
        "blocked_condition": {
            "outcome": "blocked",
            "required_blocker_category": "one governed blocker category",
        },
        "non_goals": [
            "hardware trap execution",
            "interrupt handling",
            "complete Odin runtime readiness",
            "dynamic initialization",
            "general stack readiness",
            "general memory management",
            "syscall dispatch",
            "userspace execution",
            "process model behavior",
            "VFS behavior",
            "scheduler behavior",
            "file descriptor behavior",
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
