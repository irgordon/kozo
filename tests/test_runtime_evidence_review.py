from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, RUNTIME_EVIDENCE_REVIEW_INVALID
from harness.validators_impl import runtime_evidence_review as validator_module
from harness.validators_impl.runtime_evidence_review import RuntimeEvidenceReviewValidator

KOZO_NEGATIVE_COVERAGE = {
    "runtime_evidence_review": {
        "missing_review_document": "test_fails_when_review_document_is_missing",
        "missing_evidence_type": "test_fails_when_evidence_type_is_missing",
        "missing_live_log_path": "test_fails_when_live_log_path_is_missing",
        "missing_live_metadata_path": "test_fails_when_live_metadata_path_is_missing",
        "missing_release_bundle_path": "test_fails_when_release_bundle_path_is_missing",
        "missing_validator_reference": "test_fails_when_validator_reference_is_missing",
        "missing_qemu_boot_non_goal": "test_fails_when_qemu_boot_non_goal_is_missing",
        "missing_hardware_trap_non_goal": "test_fails_when_hardware_trap_non_goal_is_missing",
        "missing_linux_non_goal": "test_fails_when_linux_non_goal_is_missing",
        "missing_userspace_non_goal": "test_fails_when_userspace_non_goal_is_missing",
        "missing_process_vfs_scheduler_elf_fd_non_goals": "test_fails_when_process_vfs_scheduler_elf_fd_non_goals_are_missing",
        "missing_production_non_goal": "test_fails_when_production_non_goal_is_missing",
        "missing_release_evidence_link": "test_fails_when_release_evidence_link_is_missing",
        "missing_release_checklist_gate": "test_fails_when_release_checklist_gate_is_missing",
        "metadata_review_non_goal_mismatch": "test_fails_when_metadata_and_review_non_goals_mismatch",
        "diagnostic_names_review_field": "test_failure_diagnostic_names_review_field",
    }
}


class RuntimeEvidenceReviewValidatorTests(unittest.TestCase):
    def test_passes_when_runtime_evidence_review_gate_is_complete(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_review_document_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(remove_review=True)

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_review_document", "docs.RUNTIME_EVIDENCE_REVIEW")

    def test_fails_when_evidence_type_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_review=lambda text: text.replace("Evidence type: `runtime-adjacent-object-symbol-smoke`", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_evidence_type", "runtime_evidence_review.evidence_type")

    def test_fails_when_live_log_path_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_review=lambda text: text.replace("Live evidence log: `artifacts/runtime/runtime_smoke.log`", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_live_log_path", "runtime_evidence_review.live_log")

    def test_fails_when_live_metadata_path_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_review=lambda text: text.replace("Live metadata: `artifacts/runtime/runtime_smoke.metadata.json`", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_live_metadata_path", "runtime_evidence_review.live_metadata")

    def test_fails_when_release_bundle_path_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_review=lambda text: text.replace("artifacts/release/runtime/runtime_smoke.log", "artifacts/release/runtime/missing.log")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_release_bundle_path", "runtime_evidence_review.release_log")

    def test_fails_when_validator_reference_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_review=lambda text: text.replace("Validator: `runtime_smoke_evidence`", "Validator: `missing`")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_validator_reference", "runtime_evidence_review.validator")

    def test_fails_when_qemu_boot_non_goal_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_review=lambda text: text.replace("This evidence does not prove QEMU boot.", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_qemu_boot_non_goal", "runtime_evidence_review.non_goals.qemu_boot")

    def test_fails_when_hardware_trap_non_goal_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_review=lambda text: text.replace("This evidence does not prove hardware syscall/trap execution.", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_hardware_trap_non_goal", "runtime_evidence_review.non_goals.hardware_trap")

    def test_fails_when_linux_non_goal_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_review=lambda text: text.replace("This evidence does not prove Linux compatibility.", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_linux_non_goal", "runtime_evidence_review.non_goals.linux_compatibility")

    def test_fails_when_userspace_non_goal_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_review=lambda text: text.replace("This evidence does not prove userspace execution.", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_userspace_non_goal", "runtime_evidence_review.non_goals.userspace_execution")

    def test_fails_when_process_vfs_scheduler_elf_fd_non_goals_are_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_review=lambda text: text.replace("This evidence does not prove VFS behavior.", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_process_vfs_scheduler_elf_fd_non_goals", "runtime_evidence_review.non_goals.vfs_behavior")

    def test_fails_when_production_non_goal_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_review=lambda text: text.replace("This evidence does not prove production readiness.", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_production_non_goal", "runtime_evidence_review.non_goals.production_readiness")

    def test_fails_when_release_evidence_link_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_release_evidence=lambda text: text.replace("docs/RUNTIME_EVIDENCE_REVIEW.md", "docs/RUNTIME_EVIDENCE.md")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_release_evidence_link", "release_evidence.runtime_evidence_review")

    def test_fails_when_release_checklist_gate_is_missing(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_release_checklist=lambda text: text.replace("Runtime evidence review is complete.", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "missing_release_checklist_gate", "release_checklist.runtime_evidence_review")

    def test_fails_when_metadata_and_review_non_goals_mismatch(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_metadata=lambda text: text.replace('    "QEMU boot",\n', "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_review_failure(result, "metadata_review_non_goal_mismatch", "runtime_smoke.metadata.does_not_prove.QEMU boot")

    def test_failure_diagnostic_names_review_field(self):
        self.assertEqual("runtime_evidence_review", RuntimeEvidenceReviewValidator.name)
        result = self.validate_fixture(
            mutate_review=lambda text: text.replace("KOZO currently has runtime-adjacent object/symbol smoke evidence for the current kernel build path.", "")
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_EVIDENCE_REVIEW_INVALID)
        self.assertEqual(result.meta["reason"], "missing_acceptable_claim")
        self.assertEqual(result.meta["contract_field"], "runtime_evidence_review.acceptable_claim")

    def validate_fixture(
        self,
        mutate_review=None,
        mutate_release_evidence=None,
        mutate_release_checklist=None,
        mutate_required_checks=None,
        mutate_metadata=None,
        remove_review=False,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            review_path = root / "docs" / "RUNTIME_EVIDENCE_REVIEW.md"
            release_evidence_path = root / "docs" / "RELEASE_EVIDENCE.md"
            release_checklist_path = root / "docs" / "RELEASE_CHECKLIST.md"
            required_checks_path = root / "docs" / "REQUIRED_CHECKS.md"
            metadata_path = root / "artifacts" / "runtime" / "runtime_smoke.metadata.json"
            review_path.parent.mkdir(parents=True)
            metadata_path.parent.mkdir(parents=True)

            review_path.write_text(_valid_review())
            release_evidence_path.write_text(_valid_release_evidence())
            release_checklist_path.write_text(_valid_release_checklist())
            required_checks_path.write_text(_valid_required_checks())
            metadata_path.write_text(_valid_metadata())

            if mutate_review is not None:
                review_path.write_text(mutate_review(review_path.read_text()))
            if mutate_release_evidence is not None:
                release_evidence_path.write_text(mutate_release_evidence(release_evidence_path.read_text()))
            if mutate_release_checklist is not None:
                release_checklist_path.write_text(mutate_release_checklist(release_checklist_path.read_text()))
            if mutate_required_checks is not None:
                required_checks_path.write_text(mutate_required_checks(required_checks_path.read_text()))
            if mutate_metadata is not None:
                metadata_path.write_text(mutate_metadata(metadata_path.read_text()))
            if remove_review:
                review_path.unlink()

            originals = _replace_validator_paths(
                review_path,
                release_evidence_path,
                release_checklist_path,
                required_checks_path,
                metadata_path,
            )
            try:
                return RuntimeEvidenceReviewValidator().validate({})
            finally:
                _restore_validator_paths(originals)

    def assert_review_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_EVIDENCE_REVIEW_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def _replace_validator_paths(review_path, release_evidence_path, release_checklist_path, required_checks_path, metadata_path):
    originals = (
        validator_module._REVIEW_PATH,
        validator_module._RELEASE_EVIDENCE_PATH,
        validator_module._RELEASE_CHECKLIST_PATH,
        validator_module._REQUIRED_CHECKS_PATH,
        validator_module._METADATA_PATH,
    )
    validator_module._REVIEW_PATH = review_path
    validator_module._RELEASE_EVIDENCE_PATH = release_evidence_path
    validator_module._RELEASE_CHECKLIST_PATH = release_checklist_path
    validator_module._REQUIRED_CHECKS_PATH = required_checks_path
    validator_module._METADATA_PATH = metadata_path
    return originals


def _restore_validator_paths(originals):
    (
        validator_module._REVIEW_PATH,
        validator_module._RELEASE_EVIDENCE_PATH,
        validator_module._RELEASE_CHECKLIST_PATH,
        validator_module._REQUIRED_CHECKS_PATH,
        validator_module._METADATA_PATH,
    ) = originals


def _valid_review() -> str:
    return "\n".join(
        (
            "Evidence type: `runtime-adjacent-object-symbol-smoke`",
            "Live evidence log: `artifacts/runtime/runtime_smoke.log`",
            "Live metadata: `artifacts/runtime/runtime_smoke.metadata.json`",
            "`artifacts/release/runtime/runtime_smoke.log`",
            "`artifacts/release/runtime/runtime_smoke.metadata.json`",
            "Validator: `runtime_smoke_evidence`",
            "This evidence does not prove QEMU boot.",
            "This evidence does not prove hardware syscall/trap execution.",
            "This evidence does not prove Linux compatibility.",
            "This evidence does not prove POSIX compatibility.",
            "This evidence does not prove userspace execution.",
            "This evidence does not prove process model behavior.",
            "This evidence does not prove VFS behavior.",
            "This evidence does not prove scheduler maturity.",
            "This evidence does not prove ELF loading.",
            "This evidence does not prove file descriptor behavior.",
            "This evidence does not prove production readiness.",
            "KOZO currently has runtime-adjacent object/symbol smoke evidence for the current kernel build path.",
            "KOZO boots.",
            "KOZO has runtime execution.",
            "KOZO supports userspace.",
            "KOZO supports Linux apps.",
            "KOZO is production ready.",
            "",
        )
    )


def _valid_release_evidence() -> str:
    return "Runtime evidence review is governed by docs/RUNTIME_EVIDENCE_REVIEW.md.\n"


def _valid_release_checklist() -> str:
    return "\n".join(
        (
            "Runtime evidence review is complete.",
            "Release is blocked if runtime evidence is overclaimed or missing required non-goals.",
            "",
        )
    )


def _valid_required_checks() -> str:
    return "Runtime evidence review uses runtime_evidence_review as a release-only review gate.\n"


def _valid_metadata() -> str:
    return """{
  "does_not_prove": [
    "QEMU boot",
    "hardware trap execution",
    "Linux compatibility",
    "userspace execution",
    "process model",
    "VFS behavior",
    "scheduler maturity",
    "ELF loading",
    "file descriptor behavior",
    "production readiness"
  ]
}
"""


if __name__ == "__main__":
    unittest.main()
