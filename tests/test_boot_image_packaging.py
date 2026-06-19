from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import BOOT_IMAGE_PACKAGING_INVALID, OK
from harness.validators_impl import boot_image_packaging as validator_module
from harness.validators_impl.boot_image_packaging import BootImagePackagingValidator

KOZO_NEGATIVE_COVERAGE = {
    "boot_image_packaging": {
        "missing_image": "test_fails_when_success_metadata_has_no_image",
        "missing_metadata": "test_fails_when_package_metadata_is_missing",
        "invalid_metadata": "test_fails_when_package_metadata_is_invalid_json",
        "wrong_boot_protocol": "test_fails_when_boot_protocol_is_wrong",
        "wrong_architecture": "test_fails_when_architecture_is_wrong",
        "image_path_mismatch": "test_fails_when_image_path_mismatches_contract",
        "wrong_image_type": "test_fails_when_image_type_is_wrong",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "blocker_state_mismatch": "test_fails_when_blocker_state_mismatches_metadata",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class BootImagePackagingValidatorTests(unittest.TestCase):
    def test_passes_when_packaging_blocker_metadata_is_complete(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_success_metadata_has_no_image(self):
        self.assertEqual("boot_image_packaging", BootImagePackagingValidator.name)
        result = self.validate_fixture(
            mutate_metadata=lambda metadata: metadata | {
                "outcome": "packaged",
                "blocker_category": "missing_qemu_serial_evidence",
                "image_exists": True,
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_packaging_failure(result, "missing_image", "boot_image_packaging.image_path")

    def test_fails_when_package_metadata_is_missing(self):
        self.assertEqual("boot_image_packaging", BootImagePackagingValidator.name)
        result = self.validate_fixture(remove_metadata=True)

        self.assertEqual(result.status, "fail")
        self.assert_packaging_failure(result, "missing_file", "boot_image_packaging.metadata")

    def test_fails_when_package_metadata_is_invalid_json(self):
        self.assertEqual("boot_image_packaging", BootImagePackagingValidator.name)
        result = self.validate_fixture(mutate_metadata_text=lambda _: "{not json")

        self.assertEqual(result.status, "fail")
        self.assert_packaging_failure(result, "invalid_json", "boot_image_packaging.metadata")

    def test_fails_when_boot_protocol_is_wrong(self):
        self.assertEqual("boot_image_packaging", BootImagePackagingValidator.name)
        result = self.validate_fixture(mutate_metadata=lambda metadata: metadata | {"boot_protocol": "Multiboot2"})

        self.assertEqual(result.status, "fail")
        self.assert_packaging_failure(result, "field_mismatch", "boot_image_packaging.boot_protocol")

    def test_fails_when_image_type_is_wrong(self):
        self.assertEqual("boot_image_packaging", BootImagePackagingValidator.name)
        result = self.validate_fixture(mutate_metadata=lambda metadata: metadata | {"image_type": "disk"})

        self.assertEqual(result.status, "fail")
        self.assert_packaging_failure(result, "field_mismatch", "boot_image_packaging.image_type")

    def test_fails_when_architecture_is_wrong(self):
        self.assertEqual("boot_image_packaging", BootImagePackagingValidator.name)
        result = self.validate_fixture(mutate_metadata=lambda metadata: metadata | {"architecture": "aarch64"})

        self.assertEqual(result.status, "fail")
        self.assert_packaging_failure(result, "field_mismatch", "boot_image_packaging.architecture")

    def test_fails_when_image_path_mismatches_contract(self):
        self.assertEqual("boot_image_packaging", BootImagePackagingValidator.name)
        result = self.validate_fixture(mutate_metadata=lambda metadata: metadata | {"image_path": "artifacts/runtime/boot_image/other.iso"})

        self.assertEqual(result.status, "fail")
        self.assert_packaging_failure(result, "field_mismatch", "boot_image_packaging.image_path")

    def test_fails_when_non_goal_is_missing(self):
        self.assertEqual("boot_image_packaging", BootImagePackagingValidator.name)
        result = self.validate_fixture(
            mutate_metadata=lambda metadata: remove_list_value(metadata, "does_not_prove", "QEMU boot")
        )

        self.assertEqual(result.status, "fail")
        self.assert_packaging_failure(result, "missing_non_goal", "boot_image_packaging.does_not_prove.QEMU boot")

    def test_fails_when_blocker_state_mismatches_metadata(self):
        self.assertEqual("boot_image_packaging", BootImagePackagingValidator.name)
        result = self.validate_fixture(
            mutate_blocker=lambda blocker: blocker | {"blocker_category": "missing_qemu_serial_evidence"}
        )

        self.assertEqual(result.status, "fail")
        self.assert_packaging_failure(result, "blocker_state_mismatch", "boot_blocker.blocker_category")

    def test_failure_diagnostic_names_field(self):
        self.assertEqual("boot_image_packaging", BootImagePackagingValidator.name)
        result = self.validate_fixture(mutate_metadata=lambda metadata: metadata | {"generated_by": "manual"})

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, BOOT_IMAGE_PACKAGING_INVALID)
        self.assertEqual(result.meta["reason"], "field_mismatch")
        self.assertEqual(result.meta["contract_field"], "boot_image_packaging.generated_by")

    def validate_fixture(
        self,
        *,
        remove_metadata: bool = False,
        mutate_metadata=None,
        mutate_metadata_text=None,
        mutate_blocker=None,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture_files(root)

            if remove_metadata:
                paths["metadata"].unlink()
            elif mutate_metadata is not None:
                metadata = json.loads(paths["metadata"].read_text())
                paths["metadata"].write_text(json.dumps(mutate_metadata(metadata), indent=2) + "\n")
            elif mutate_metadata_text is not None:
                paths["metadata"].write_text(mutate_metadata_text(paths["metadata"].read_text()))

            if mutate_blocker is not None:
                blocker = json.loads(paths["blocker"].read_text())
                paths["blocker"].write_text(json.dumps(mutate_blocker(blocker), indent=2) + "\n")

            old_paths = patch_validator_paths(paths)
            try:
                return BootImagePackagingValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_packaging_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.code, BOOT_IMAGE_PACKAGING_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> dict[str, Path]:
    paths = {
        "metadata": root / "artifacts" / "runtime" / "boot_image" / "package_metadata.json",
        "blocker": root / "artifacts" / "runtime" / "boot_blocker_report.json",
        "image": root / "artifacts" / "runtime" / "boot_image" / "kozo.iso",
        "boot": root / "docs" / "BOOT.md",
        "image_doc": root / "docs" / "BOOT_IMAGE.md",
        "blockers": root / "docs" / "BOOT_BLOCKERS.md",
        "runtime": root / "docs" / "RUNTIME_EVIDENCE.md",
        "release": root / "docs" / "RELEASE_EVIDENCE.md",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    paths["metadata"].write_text(json.dumps(valid_metadata(), indent=2) + "\n")
    paths["blocker"].write_text(json.dumps(valid_blocker(), indent=2) + "\n")
    for key in ("boot", "image_doc", "blockers", "runtime", "release"):
        paths[key].write_text(valid_doc_text())
    return paths


def valid_metadata() -> dict[str, object]:
    return {
        "version": 0,
        "phase": "v0.3.6",
        "outcome": "blocked",
        "blocker_category": "missing_iso_generation_tooling",
        "image_type": "iso",
        "boot_protocol": "Limine",
        "architecture": "x86_64",
        "image_path": "artifacts/runtime/boot_image/kozo.iso",
        "image_exists": False,
        "generated_by": "scripts/build_boot_image.sh",
        "missing_components": [
            "Limine executable",
            "xorriso executable",
            "Limine bootloader artifacts",
        ],
        "proves": [
            "boot image skeleton packaging prerequisites were checked",
        ],
        "does_not_prove": [
            "QEMU boot",
            "serial output",
            "hardware trap execution",
            "Linux compatibility",
            "POSIX compatibility",
            "userspace execution",
            "process model behavior",
            "VFS behavior",
            "scheduler maturity",
            "ELF loading",
            "file descriptor behavior",
            "production readiness",
        ],
    }


def valid_blocker() -> dict[str, object]:
    return {
        "phase": "v0.3.8",
        "blocker_category": "missing_iso_generation_tooling",
    }


def valid_doc_text() -> str:
    return "\n".join(
        (
            "artifacts/runtime/boot_image/package_metadata.json",
            "artifacts/runtime/boot_image/kozo.iso",
            "missing_iso_generation_tooling",
        )
    )


def remove_list_value(metadata: dict[str, object], key: str, value: str) -> dict[str, object]:
    metadata[key] = [item for item in metadata[key] if item != value]
    return metadata


def patch_validator_paths(paths: dict[str, Path]):
    old_paths = (
        validator_module._METADATA_PATH,
        validator_module._BOOT_BLOCKER_REPORT_PATH,
        validator_module._BOOT_DOC_PATH,
        validator_module._BOOT_IMAGE_DOC_PATH,
        validator_module._BOOT_BLOCKERS_PATH,
        validator_module._RUNTIME_EVIDENCE_PATH,
        validator_module._RELEASE_EVIDENCE_PATH,
        validator_module._IMAGE_PATH,
    )
    validator_module._METADATA_PATH = paths["metadata"]
    validator_module._BOOT_BLOCKER_REPORT_PATH = paths["blocker"]
    validator_module._BOOT_DOC_PATH = paths["boot"]
    validator_module._BOOT_IMAGE_DOC_PATH = paths["image_doc"]
    validator_module._BOOT_BLOCKERS_PATH = paths["blockers"]
    validator_module._RUNTIME_EVIDENCE_PATH = paths["runtime"]
    validator_module._RELEASE_EVIDENCE_PATH = paths["release"]
    validator_module._IMAGE_PATH = paths["image"]
    return old_paths


def restore_validator_paths(old_paths) -> None:
    (
        validator_module._METADATA_PATH,
        validator_module._BOOT_BLOCKER_REPORT_PATH,
        validator_module._BOOT_DOC_PATH,
        validator_module._BOOT_IMAGE_DOC_PATH,
        validator_module._BOOT_BLOCKERS_PATH,
        validator_module._RUNTIME_EVIDENCE_PATH,
        validator_module._RELEASE_EVIDENCE_PATH,
        validator_module._IMAGE_PATH,
    ) = old_paths


if __name__ == "__main__":
    unittest.main()
