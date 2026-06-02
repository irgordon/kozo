from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness import syscall_surface_report
from harness.codes import OK, SYSCALL_SURFACE_REPORT_INVALID
from harness.validators_impl import syscall_surface_report as surface_validator
from harness.validators_impl.syscall_surface_report import SyscallSurfaceReportValidator

KOZO_NEGATIVE_COVERAGE = {
    "syscall_surface_report": {
        "missing_report_file": "test_fails_when_report_file_is_missing",
        "stale_report_content": "test_fails_when_report_content_is_stale",
        "manual_edit_detected": "test_fails_when_manual_edit_changes_generated_notice",
        "missing_syscall": "test_fails_when_report_is_missing_syscall_section",
        "missing_syscall_class": "test_fails_when_report_is_missing_syscall_class",
        "missing_source_reference": "test_fails_when_report_is_missing_source_reference",
        "catalog_change_updates_report": "test_fails_when_catalog_change_makes_report_stale",
        "diagnostic_names_report_field": "test_failure_diagnostic_names_report_field",
    }
}


class SyscallSurfaceReportTests(unittest.TestCase):
    def test_renderer_emits_deterministic_markdown(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.write_fixture(Path(temporary_directory))

            first = syscall_surface_report.expected_report_text(root)
            second = syscall_surface_report.expected_report_text(root)

        self.assertEqual(first, second)
        self.assertIn("# KOZO syscall surface", first)
        self.assertIn("| status | K_SYSCALL_STATUS | 2 | no_payload | no_payload_status | null | K_OK | no | yes |", first)

    def test_current_checked_in_report_matches_generated_output(self):
        result = SyscallSurfaceReportValidator().validate({})

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_report_file_is_missing(self):
        result = self.validate_report(remove_report=True)

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "missing_report_file", "docs/generated/syscall_surface.md")

    def test_fails_when_report_content_is_stale(self):
        result = self.validate_report(
            mutate_report=lambda text: text + "\nStale trailing text.\n"
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "stale_report_content", "docs/generated/syscall_surface.md")

    def test_fails_when_manual_edit_changes_generated_notice(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace(
                "This document is generated. Do not edit manually.",
                "This document was edited manually.",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "manual_edit_detected", "generated_notice")

    def test_fails_when_report_is_missing_syscall_section(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("### status", "### removed_status")
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "missing_syscall", "syscalls.status")

    def test_fails_when_report_is_missing_syscall_class(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("`no_payload_status`", "no_payload_status")
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "missing_syscall_class", "classes.no_payload_status")

    def test_fails_when_report_is_missing_source_reference(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("* `contracts/syscall_catalog.v0.json`\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "missing_source_reference", "generated_from")

    def test_fails_when_catalog_change_makes_report_stale(self):
        result = self.validate_report(
            mutate_catalog=lambda catalog: self.set_value(
                catalog,
                ("syscalls", "status", "numeric_id"),
                7,
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "stale_report_content", "docs/generated/syscall_surface.md")

    def test_failure_diagnostic_names_report_field(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("* `contracts/syscall_catalog.v0.json`\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, SYSCALL_SURFACE_REPORT_INVALID)
        self.assertEqual(result.meta["reason"], "missing_source_reference")
        self.assertEqual(result.meta["contract_field"], "generated_from")

    def validate_report(
        self,
        mutate_report=None,
        mutate_catalog=None,
        remove_report: bool = False,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.write_fixture(Path(temporary_directory))
            report_path = root / "docs" / "generated" / "syscall_surface.md"
            if mutate_report is not None and report_path.is_file():
                report_path.write_text(mutate_report(report_path.read_text()))
            if mutate_catalog is not None:
                catalog_path = root / "contracts" / "syscall_catalog.v0.json"
                catalog = json.loads(catalog_path.read_text())
                mutate_catalog(catalog)
                catalog_path.write_text(json.dumps(catalog))
            if remove_report and report_path.is_file():
                report_path.unlink()
            original_paths = self.patch_validator_paths(root, report_path)
            try:
                return SyscallSurfaceReportValidator().validate({})
            finally:
                self.restore_validator_paths(original_paths)

    def write_fixture(self, root: Path) -> Path:
        contracts_dir = root / "contracts"
        contracts_dir.mkdir(parents=True)
        for name in (
            "syscall_catalog.v0.json",
            "syscall_table_contract.v0.json",
            "syscall_class_contract.v0.json",
            "kozo_abi_manifest.json",
        ):
            source = Path(__file__).resolve().parents[1] / "contracts" / name
            (contracts_dir / name).write_text(source.read_text())
        syscall_surface_report.write_report(root, root / "docs" / "generated" / "syscall_surface.md")
        return root

    def patch_validator_paths(self, root: Path, report_path: Path) -> dict[str, Path]:
        original = {
            "root": surface_validator._REPORT_ROOT,
            "path": surface_validator._REPORT_PATH,
        }
        surface_validator._REPORT_ROOT = root
        surface_validator._REPORT_PATH = report_path
        return original

    def restore_validator_paths(self, paths: dict[str, Path]) -> None:
        surface_validator._REPORT_ROOT = paths["root"]
        surface_validator._REPORT_PATH = paths["path"]

    def set_value(self, data: dict, path: tuple[str, ...], value) -> None:
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    def assert_report_failure(self, result, reason: str, contract_field: str) -> None:
        self.assertEqual(result.code, SYSCALL_SURFACE_REPORT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


if __name__ == "__main__":
    unittest.main()
