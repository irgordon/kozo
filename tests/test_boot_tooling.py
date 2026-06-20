from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import BOOT_TOOLING_INVALID, OK
from harness.validators_impl import boot_tooling as validator_module
from harness.validators_impl.boot_tooling import BootToolingValidator

KOZO_NEGATIVE_COVERAGE = {
    "boot_tooling": {
        "missing_limine_doc": "test_fails_when_limine_documentation_is_missing",
        "missing_xorriso_doc": "test_fails_when_xorriso_documentation_is_missing",
        "missing_ci_install_path": "test_fails_when_ci_install_path_is_missing",
        "missing_local_install_path": "test_fails_when_local_install_path_is_missing",
        "missing_provenance": "test_fails_when_provenance_section_is_missing",
        "blocker_mismatch": "test_fails_when_blocker_state_is_not_iso_generation",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class BootToolingValidatorTests(unittest.TestCase):
    def test_passes_when_boot_tooling_policy_is_complete(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_passes_when_iso_exists_and_qemu_serial_evidence_is_missing(self):
        result = self.validate_fixture(
            mutate_report=lambda report: report | {"blocker_category": "missing_qemu_serial_evidence"}
        )

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_passes_when_limine_lower_half_phdr_is_current_qemu_blocker(self):
        result = self.validate_fixture(
            mutate_report=lambda report: report | {"blocker_category": "limine_lower_half_phdr"}
        )

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_limine_documentation_is_missing(self):
        self.assertEqual("boot_tooling", BootToolingValidator.name)
        result = self.validate_fixture(mutate_tooling=lambda text: text.replace("Limine purpose:", "Bootloader purpose:"))

        self.assertEqual(result.status, "fail")
        self.assert_tooling_failure(result, "missing_limine_doc", "docs/BOOT_TOOLING.md.limine_doc")

    def test_fails_when_xorriso_documentation_is_missing(self):
        self.assertEqual("boot_tooling", BootToolingValidator.name)
        result = self.validate_fixture(mutate_tooling=lambda text: text.replace("xorriso purpose:", "ISO tool purpose:"))

        self.assertEqual(result.status, "fail")
        self.assert_tooling_failure(result, "missing_xorriso_doc", "docs/BOOT_TOOLING.md.xorriso_doc")

    def test_fails_when_ci_install_path_is_missing(self):
        self.assertEqual("boot_tooling", BootToolingValidator.name)
        result = self.validate_fixture(mutate_tooling=lambda text: text.replace("CI installation path:", "CI path:"))

        self.assertEqual(result.status, "fail")
        self.assert_tooling_failure(result, "missing_ci_install_path", "docs/BOOT_TOOLING.md.ci_install_path")

    def test_fails_when_ci_workflow_limine_pin_is_missing(self):
        self.assertEqual("boot_tooling", BootToolingValidator.name)
        result = self.validate_fixture(mutate_ci=lambda text: text.replace("LIMINE_VERSION: v12.3.3", "LIMINE_VERSION: v12.3.2"))

        self.assertEqual(result.status, "fail")
        self.assert_tooling_failure(result, "missing_workflow_limine_pin", "workflows/ci.yml.workflow_limine_pin")

    def test_fails_when_local_install_path_is_missing(self):
        self.assertEqual("boot_tooling", BootToolingValidator.name)
        result = self.validate_fixture(mutate_tooling=lambda text: text.replace("Local development path:", "Developer path:"))

        self.assertEqual(result.status, "fail")
        self.assert_tooling_failure(result, "missing_local_install_path", "docs/BOOT_TOOLING.md.local_install_path")

    def test_fails_when_provenance_section_is_missing(self):
        self.assertEqual("boot_tooling", BootToolingValidator.name)
        result = self.validate_fixture(mutate_tooling=lambda text: text.replace("Tool Provenance", "Tool Sources"))

        self.assertEqual(result.status, "fail")
        self.assert_tooling_failure(result, "missing_provenance", "docs/BOOT_TOOLING.md.provenance")

    def test_fails_when_blocker_state_is_not_iso_generation(self):
        self.assertEqual("boot_tooling", BootToolingValidator.name)
        result = self.validate_fixture(mutate_report=lambda report: report | {"blocker_category": "missing_limine_iso_tooling"})

        self.assertEqual(result.status, "fail")
        self.assert_tooling_failure(result, "blocker_mismatch", "boot_blocker.blocker_category")

    def test_failure_diagnostic_names_field(self):
        self.assertEqual("boot_tooling", BootToolingValidator.name)
        result = self.validate_fixture(mutate_boot=lambda text: text.replace("docs/BOOT_TOOLING.md", "docs/BOOT_TOOLS.md"))

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, BOOT_TOOLING_INVALID)
        self.assertEqual(result.meta["reason"], "missing_boot_doc_tooling")
        self.assertEqual(result.meta["contract_field"], "docs/BOOT.md.boot_doc_tooling")

    def validate_fixture(self, *, mutate_tooling=None, mutate_report=None, mutate_boot=None, mutate_ci=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture_files(root)

            if mutate_tooling is not None:
                paths["tooling"].write_text(mutate_tooling(paths["tooling"].read_text()))
            if mutate_report is not None:
                report = json.loads(paths["report"].read_text())
                paths["report"].write_text(json.dumps(mutate_report(report), indent=2) + "\n")
            if mutate_boot is not None:
                paths["boot"].write_text(mutate_boot(paths["boot"].read_text()))
            if mutate_ci is not None:
                paths["ci"].write_text(mutate_ci(paths["ci"].read_text()))

            old_paths = patch_validator_paths(paths)
            try:
                return BootToolingValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_tooling_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.code, BOOT_TOOLING_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> dict[str, Path]:
    paths = {
        "tooling": root / "docs" / "BOOT_TOOLING.md",
        "boot": root / "docs" / "BOOT.md",
        "image": root / "docs" / "BOOT_IMAGE.md",
        "blockers": root / "docs" / "BOOT_BLOCKERS.md",
        "runtime": root / "docs" / "RUNTIME_EVIDENCE.md",
        "release": root / "docs" / "RELEASE_EVIDENCE.md",
        "ci": root / ".github" / "workflows" / "ci.yml",
        "build": root / "scripts" / "build_boot_image.sh",
        "report": root / "artifacts" / "runtime" / "boot_blocker_report.json",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    paths["tooling"].write_text(valid_tooling_text())
    for key in ("boot", "image", "blockers", "runtime", "release"):
        paths[key].write_text(valid_doc_text())
    paths["ci"].write_text(valid_ci_text())
    paths["build"].write_text(valid_build_script_text())
    paths["report"].write_text(json.dumps({"blocker_category": "missing_iso_generation_tooling"}, indent=2) + "\n")
    return paths


def valid_tooling_text() -> str:
    return "\n".join(
        (
            "Limine purpose:",
            "xorriso purpose:",
            "Local development path:",
            "CI installation path:",
            "v12.3.3",
            "9e97c9fedc714daa5d7fd2b66a32d85df6bcbf3452657fd26bebad7c8b423009",
            "Download Limine v12.3.3 from the upstream GitHub release source tarball.",
            "Install xorriso through apt.",
            "Tool Provenance",
            "Opaque vendored binaries are discouraged.",
            "artifacts/runtime/boot_image/kozo.iso",
            "missing_iso_generation_tooling",
        )
    )


def valid_doc_text() -> str:
    return "docs/BOOT_TOOLING.md\nmissing_iso_generation_tooling\n"


def valid_ci_text() -> str:
    return "\n".join(
        (
            "LIMINE_VERSION: v12.3.3",
            "LIMINE_TARBALL_SHA256: 9e97c9fedc714daa5d7fd2b66a32d85df6bcbf3452657fd26bebad7c8b423009",
            "xorriso",
            "scripts/build_boot_image.sh",
            "artifacts/runtime/boot_image/kozo.iso",
        )
    )


def valid_build_script_text() -> str:
    return "${LIMINE_DIR:-}\n${LIMINE_INSTALL:-}\n${LIMINE:-}\n${XORRISO:-}\n"


def patch_validator_paths(paths: dict[str, Path]):
    old_paths = (
        validator_module._BOOT_TOOLING_PATH,
        validator_module._BOOT_DOC_PATH,
        validator_module._BOOT_IMAGE_PATH,
        validator_module._BOOT_BLOCKERS_PATH,
        validator_module._RUNTIME_EVIDENCE_PATH,
        validator_module._RELEASE_EVIDENCE_PATH,
        validator_module._CI_WORKFLOW_PATH,
        validator_module._BUILD_SCRIPT_PATH,
        validator_module._REPORT_PATH,
    )
    validator_module._BOOT_TOOLING_PATH = paths["tooling"]
    validator_module._BOOT_DOC_PATH = paths["boot"]
    validator_module._BOOT_IMAGE_PATH = paths["image"]
    validator_module._BOOT_BLOCKERS_PATH = paths["blockers"]
    validator_module._RUNTIME_EVIDENCE_PATH = paths["runtime"]
    validator_module._RELEASE_EVIDENCE_PATH = paths["release"]
    validator_module._CI_WORKFLOW_PATH = paths["ci"]
    validator_module._BUILD_SCRIPT_PATH = paths["build"]
    validator_module._REPORT_PATH = paths["report"]
    return old_paths


def restore_validator_paths(old_paths) -> None:
    (
        validator_module._BOOT_TOOLING_PATH,
        validator_module._BOOT_DOC_PATH,
        validator_module._BOOT_IMAGE_PATH,
        validator_module._BOOT_BLOCKERS_PATH,
        validator_module._RUNTIME_EVIDENCE_PATH,
        validator_module._RELEASE_EVIDENCE_PATH,
        validator_module._CI_WORKFLOW_PATH,
        validator_module._BUILD_SCRIPT_PATH,
        validator_module._REPORT_PATH,
    ) = old_paths


if __name__ == "__main__":
    unittest.main()
