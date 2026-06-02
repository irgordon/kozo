from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness import abi_surface_report
from harness.codes import ABI_SURFACE_REPORT_INVALID, OK
from harness.validators_impl import abi_surface_report as report_validator
from harness.validators_impl.abi_surface_report import AbiSurfaceReportValidator

KOZO_NEGATIVE_COVERAGE = {
    "abi_surface_report": {
        "missing_report_file": "test_fails_when_report_file_is_missing",
        "stale_report_content": "test_fails_when_report_content_is_stale",
        "manual_edit_detected": "test_fails_when_manual_edit_changes_generated_notice",
        "missing_status_constant": "test_fails_when_report_is_missing_status_constant",
        "missing_syscall_constant": "test_fails_when_report_is_missing_syscall_constant",
        "missing_binding_path": "test_fails_when_report_is_missing_binding_path",
        "missing_layout_field": "test_fails_when_report_is_missing_layout_field",
        "missing_layout_size_alignment": "test_fails_when_report_is_missing_layout_size",
        "missing_request_sentinel": "test_fails_when_report_is_missing_request_sentinel",
        "missing_response_sentinel": "test_fails_when_report_is_missing_response_sentinel",
        "manifest_change_updates_report": "test_fails_when_manifest_change_makes_report_stale",
        "diagnostic_names_report_field": "test_failure_diagnostic_names_report_field",
    }
}


class AbiSurfaceReportTests(unittest.TestCase):
    def test_renderer_emits_deterministic_markdown(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.write_fixture(Path(temporary_directory))

            first = abi_surface_report.expected_report_text(root)
            second = abi_surface_report.expected_report_text(root)

        self.assertEqual(first, second)
        self.assertIn("# KOZO ABI surface", first)
        self.assertIn("| K_SYSCALL_STATUS | 2 |", first)
        self.assertIn("| status_bits | 4 | 16 |", first)

    def test_current_checked_in_report_matches_generated_output(self):
        result = AbiSurfaceReportValidator().validate({})

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_report_file_is_missing(self):
        result = self.validate_report(remove_report=True)

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "missing_report_file", "docs/generated/abi_surface.md")

    def test_fails_when_report_content_is_stale(self):
        result = self.validate_report(
            mutate_report=lambda text: text + "\nStale trailing text.\n"
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "stale_report_content", "docs/generated/abi_surface.md")

    def test_fails_when_manual_edit_changes_generated_notice(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace(
                "This document is generated. Do not edit manually.",
                "This document was edited manually.",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "manual_edit_detected", "generated_notice")

    def test_fails_when_report_is_missing_status_constant(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("| K_DENIED | 2 |\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "missing_status_constant", "constants.status.K_DENIED")

    def test_fails_when_report_is_missing_syscall_constant(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("| K_SYSCALL_STATUS | 2 |\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "missing_syscall_constant", "constants.syscalls.K_SYSCALL_STATUS")

    def test_fails_when_report_is_missing_binding_path(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("`bindings/rust/kozo_abi.rs`", "`missing_rust_binding`")
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "missing_binding_path", "generated_bindings.rust")

    def test_fails_when_report_is_missing_layout_field(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("| status_bits | 4 | 16 |\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "missing_layout_field", "layouts.heartbeat_payload.fields.status_bits")

    def test_fails_when_report_is_missing_layout_size(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("Struct size: 24\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "missing_layout_size_alignment", "layouts.heartbeat_payload.size")

    def test_fails_when_report_is_missing_request_sentinel(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("| sequence | `0xCAFEFEED` |\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "missing_request_sentinel", "heartbeat.request.sequence")

    def test_fails_when_report_is_missing_response_sentinel(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("| timestamp | `0xDEADBEEF` |\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "missing_response_sentinel", "heartbeat.response.timestamp")

    def test_fails_when_manifest_change_makes_report_stale(self):
        result = self.validate_report(
            mutate_manifest=lambda manifest: self.set_value(
                manifest,
                ("layouts", "heartbeat_payload", "c_name"),
                "k_changed_payload_t",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_report_failure(result, "stale_report_content", "docs/generated/abi_surface.md")

    def test_failure_diagnostic_names_report_field(self):
        result = self.validate_report(
            mutate_report=lambda text: text.replace("| K_DENIED | 2 |\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, ABI_SURFACE_REPORT_INVALID)
        self.assertEqual(result.meta["reason"], "missing_status_constant")
        self.assertEqual(result.meta["contract_field"], "constants.status.K_DENIED")

    def validate_report(
        self,
        mutate_report=None,
        mutate_manifest=None,
        remove_report: bool = False,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.write_fixture(Path(temporary_directory))
            report_path = root / "docs" / "generated" / "abi_surface.md"
            if mutate_report is not None and report_path.is_file():
                report_path.write_text(mutate_report(report_path.read_text()))
            if mutate_manifest is not None:
                manifest_path = root / abi_surface_report.MANIFEST_REFERENCE
                manifest = json.loads(manifest_path.read_text())
                mutate_manifest(manifest)
                manifest_path.write_text(json.dumps(manifest))
            if remove_report and report_path.is_file():
                report_path.unlink()
            original_paths = self.patch_validator_paths(root, report_path)
            try:
                return AbiSurfaceReportValidator().validate({})
            finally:
                self.restore_validator_paths(original_paths)

    def write_fixture(self, root: Path) -> Path:
        contracts_dir = root / "contracts"
        contracts_dir.mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / abi_surface_report.MANIFEST_REFERENCE
        (contracts_dir / "kozo_abi_manifest.json").write_text(source.read_text())
        abi_surface_report.write_report(root, root / "docs" / "generated" / "abi_surface.md")
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

    def set_value(self, data: dict, path: tuple[str, ...], value) -> None:
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    def assert_report_failure(self, result, reason: str, contract_field: str) -> None:
        self.assertEqual(result.code, ABI_SURFACE_REPORT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


if __name__ == "__main__":
    unittest.main()
