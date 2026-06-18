from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from harness import governance_index_report
from harness.codes import GOVERNANCE_INDEX_REPORT_INVALID, OK
from harness.validators_impl import governance_index_report as report_validator
from harness.validators_impl.governance_index_report import GovernanceIndexReportValidator

KOZO_NEGATIVE_COVERAGE = {
    "governance_index_report": {
        "missing_index_file": "test_fails_when_governance_index_file_is_missing",
        "stale_index_content": "test_fails_when_governance_index_content_is_stale",
        "manual_edit_detected": "test_fails_when_manual_edit_changes_generated_notice",
        "missing_current_version": "test_fails_when_current_version_is_missing",
        "missing_verification_status": "test_fails_when_verification_status_is_missing",
        "missing_registered_validator": "test_fails_when_registered_validator_is_missing",
        "missing_active_contract": "test_fails_when_active_contract_is_missing",
        "missing_schema": "test_fails_when_schema_is_missing",
        "missing_syscall_report_reference": "test_fails_when_syscall_surface_report_reference_is_missing",
        "missing_abi_report_reference": "test_fails_when_abi_surface_report_reference_is_missing",
        "missing_latest_proof_artifact": "test_fails_when_latest_proof_artifact_reference_is_missing",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "latest_verify_change_updates_report": "test_fails_when_latest_verify_change_makes_report_stale",
        "registry_change_updates_report": "test_fails_when_registry_change_makes_report_stale",
        "diagnostic_names_index_field": "test_failure_diagnostic_names_governance_index_field",
    }
}


class GovernanceIndexReportTests(unittest.TestCase):
    def test_renderer_emits_deterministic_markdown(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.write_fixture(Path(temporary_directory))

            first = governance_index_report.expected_report_text(root)
            second = governance_index_report.expected_report_text(root)

        self.assertEqual(first, second)
        self.assertIn("# KOZO governance index", first)
        self.assertIn("## Registered validators", first)
        self.assertIn("## Non-goals", first)

    def test_current_checked_in_governance_index_matches_generated_output(self):
        result = GovernanceIndexReportValidator().validate({})

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_governance_index_file_is_missing(self):
        result = self.validate_report(remove_report=True)

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "missing_index_file", "docs/generated/governance_index.md")

    def test_fails_when_governance_index_content_is_stale(self):
        result = self.validate_report(mutate_report=lambda text: text + "\nStale trailing text.\n")

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "stale_index_content", "docs/generated/governance_index.md")

    def test_fails_when_manual_edit_changes_generated_notice(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace(
                "This document is generated. Do not edit manually.",
                "This document was edited manually.",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "manual_edit_detected", "generated_notice")

    def test_fails_when_current_version_is_missing(self):
        result = self.validate_report(
            mutate_report=lambda text: self.remove_line_containing(text, "* Version:")
        )

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "missing_current_version", "current_version.version")

    def test_fails_when_verification_status_is_missing(self):
        result = self.validate_report(
            mutate_report=lambda text: self.remove_line_containing(text, "* Summary code:")
        )

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "missing_verification_status", "verification.summary_code")

    def test_fails_when_registered_validator_is_missing(self):
        result = self.validate_report(
            mutate_report=lambda text: self.remove_line_containing(text, "`schema`")
        )

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "missing_registered_validator", "validators.schema")

    def test_fails_when_active_contract_is_missing(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("`contracts/kozo_abi_manifest.json`", "`contracts/missing_manifest.json`")
        )

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "missing_active_contract", "contracts.contracts/kozo_abi_manifest.json")

    def test_fails_when_schema_is_missing(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("`schemas/latest_verify.schema.json`", "`schemas/missing.schema.json`")
        )

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "missing_schema", "schemas.schemas/latest_verify.schema.json")

    def test_fails_when_syscall_surface_report_reference_is_missing(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("`docs/generated/syscall_surface.md`", "`docs/generated/missing_syscalls.md`")
        )

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "missing_syscall_report_reference", "generated_reports.syscall_surface")

    def test_fails_when_abi_surface_report_reference_is_missing(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("`docs/generated/abi_surface.md`", "`docs/generated/missing_abi.md`")
        )

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "missing_abi_report_reference", "generated_reports.abi_surface")

    def test_fails_when_latest_proof_artifact_reference_is_missing(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("`artifacts/latest_verify.json`", "`artifacts/missing_verify.json`")
        )

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "missing_latest_proof_artifact", "latest_proof_artifact.path")

    def test_fails_when_non_goal_is_missing(self):
        result = self.validate_report(
            mutate_report=lambda text: self.remove_line_containing(text, "no Linux compatibility claim")
        )

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "missing_non_goal", "non_goals.no Linux compatibility claim")

    def test_fails_when_latest_verify_change_makes_report_stale(self):
        result = self.validate_report(
            mutate_latest_verify=lambda latest: self.set_value(latest, ("summary", "total_checks"), 99)
        )

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "missing_verification_status", "verification.total_checks")

    def test_fails_when_registry_change_makes_report_stale(self):
        result = self.validate_report(
            mutate_registry=lambda checks: {**checks, "future_validator": "future_validator"}
        )

        self.assertEqual(result.status, "fail")
        self.assert_index_failure(result, "missing_registered_validator", "validators.future_validator")

    def test_failure_diagnostic_names_governance_index_field(self):
        result = self.validate_report(
            mutate_report=lambda text: self.remove_line_containing(text, "* Summary code:")
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, GOVERNANCE_INDEX_REPORT_INVALID)
        self.assertEqual(result.meta["reason"], "missing_verification_status")
        self.assertEqual(result.meta["contract_field"], "verification.summary_code")

    def validate_report(
        self,
        mutate_report=None,
        mutate_latest_verify=None,
        mutate_registry=None,
        remove_report: bool = False,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.write_fixture(Path(temporary_directory))
            report_path = root / "docs" / "generated" / "governance_index.md"
            if mutate_report is not None and report_path.is_file():
                report_path.write_text(mutate_report(report_path.read_text()))
            if mutate_latest_verify is not None:
                latest_path = root / governance_index_report.LATEST_VERIFY_REFERENCE
                latest = json.loads(latest_path.read_text())
                mutate_latest_verify(latest)
                latest_path.write_text(json.dumps(latest))
            original_paths = self.patch_validator_paths(root, report_path)
            original_checks = governance_index_report.CHECKS
            if mutate_registry is not None:
                governance_index_report.CHECKS = mutate_registry(dict(original_checks))
            if remove_report and report_path.is_file():
                report_path.unlink()
            try:
                return GovernanceIndexReportValidator().validate({})
            finally:
                governance_index_report.CHECKS = original_checks
                self.restore_validator_paths(original_paths)

    def write_fixture(self, root: Path) -> Path:
        source_root = Path(__file__).resolve().parents[1]
        for directory in ("contracts", "schemas"):
            shutil.copytree(source_root / directory, root / directory)
        (root / "artifacts").mkdir()
        (root / "artifacts" / "latest_verify.json").write_text((source_root / "artifacts" / "latest_verify.json").read_text())
        (root / "CHANGELOG.md").write_text((source_root / "CHANGELOG.md").read_text())
        for report_name in ("syscall_surface.md", "abi_surface.md"):
            report_path = root / "docs" / "generated" / report_name
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text((source_root / "docs" / "generated" / report_name).read_text())
        governance_index_report.write_report(root, root / "docs" / "generated" / "governance_index.md")
        return root

    def patch_validator_paths(self, root: Path, report_path: Path) -> dict[str, Path]:
        original = {
            "root": report_validator._REPORT_ROOT,
            "path": report_validator._REPORT_PATH,
        }
        report_validator._REPORT_ROOT = root
        report_validator._REPORT_PATH = report_path
        return original

    def restore_validator_paths(self, paths: dict[str, Path]) -> None:
        report_validator._REPORT_ROOT = paths["root"]
        report_validator._REPORT_PATH = paths["path"]

    def remove_line_containing(self, text: str, needle: str) -> str:
        return "\n".join(line for line in text.splitlines() if needle not in line) + "\n"

    def set_value(self, data: dict, path: tuple[str, ...], value) -> None:
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    def assert_index_failure(self, result, reason: str, contract_field: str) -> None:
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, GOVERNANCE_INDEX_REPORT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


if __name__ == "__main__":
    unittest.main()
