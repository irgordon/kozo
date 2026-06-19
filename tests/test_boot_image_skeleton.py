from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import BOOT_IMAGE_SKELETON_INVALID, OK
from harness.validators_impl import boot_image_skeleton as validator_module
from harness.validators_impl.boot_image_skeleton import BootImageSkeletonValidator

KOZO_NEGATIVE_COVERAGE = {
    "boot_image_skeleton": {
        "missing_linker_script": "test_fails_when_linker_script_is_missing",
        "missing_limine_config": "test_fails_when_limine_config_is_missing",
        "missing_build_script": "test_fails_when_build_script_is_missing",
        "missing_boot_image_doc": "test_fails_when_boot_image_doc_is_missing",
        "blocker_state_mismatch": "test_fails_when_blocker_state_is_not_qemu_evidence",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class BootImageSkeletonValidatorTests(unittest.TestCase):
    def test_passes_when_boot_image_skeleton_is_complete(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_passes_when_iso_exists_and_qemu_serial_evidence_is_missing(self):
        result = self.validate_fixture(mutate_report=lambda report: report | {
            "blocker_category": "missing_qemu_serial_evidence",
            "missing_components": ["validated QEMU serial smoke execution"],
        })

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_linker_script_is_missing(self):
        self.assertEqual("boot_image_skeleton", BootImageSkeletonValidator.name)
        result = self.validate_fixture(remove="linker")

        self.assertEqual(result.status, "fail")
        self.assert_skeleton_failure(result, "missing_file", "linker/kernel.ld")

    def test_fails_when_limine_config_is_missing(self):
        self.assertEqual("boot_image_skeleton", BootImageSkeletonValidator.name)
        result = self.validate_fixture(remove="limine")

        self.assertEqual(result.status, "fail")
        self.assert_skeleton_failure(result, "missing_file", "boot/limine.conf")

    def test_fails_when_build_script_is_missing(self):
        self.assertEqual("boot_image_skeleton", BootImageSkeletonValidator.name)
        result = self.validate_fixture(remove="script")

        self.assertEqual(result.status, "fail")
        self.assert_skeleton_failure(result, "missing_file", "scripts/build_boot_image.sh")

    def test_fails_when_boot_image_doc_is_missing(self):
        self.assertEqual("boot_image_skeleton", BootImageSkeletonValidator.name)
        result = self.validate_fixture(remove="doc")

        self.assertEqual(result.status, "fail")
        self.assert_skeleton_failure(result, "missing_file", "docs/BOOT_IMAGE.md")

    def test_fails_when_blocker_state_is_not_qemu_evidence(self):
        self.assertEqual("boot_image_skeleton", BootImageSkeletonValidator.name)
        result = self.validate_fixture(
            mutate_report=lambda report: report | {"blocker_category": "missing_boot_protocol_and_image_packaging"}
        )

        self.assertEqual(result.status, "fail")
        self.assert_skeleton_failure(result, "blocker_state_mismatch", "boot_blocker.blocker_category")

    def test_failure_diagnostic_names_field(self):
        self.assertEqual("boot_image_skeleton", BootImageSkeletonValidator.name)
        result = self.validate_fixture(mutate_linker=lambda text: text.replace("ENTRY(_start)", "ENTRY(other)"))

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, BOOT_IMAGE_SKELETON_INVALID)
        self.assertEqual(result.meta["reason"], "missing_entry_symbol")
        self.assertEqual(result.meta["contract_field"], "linker/kernel.ld.entry_symbol")

    def validate_fixture(self, *, remove: str | None = None, mutate_report=None, mutate_linker=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture_files(root)

            if remove is not None:
                paths[remove].unlink()
            if mutate_report is not None:
                report = json.loads(paths["report"].read_text())
                paths["report"].write_text(json.dumps(mutate_report(report), indent=2) + "\n")
            if mutate_linker is not None:
                paths["linker"].write_text(mutate_linker(paths["linker"].read_text()))

            old_paths = patch_validator_paths(paths)
            try:
                return BootImageSkeletonValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_skeleton_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.code, BOOT_IMAGE_SKELETON_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> dict[str, Path]:
    paths = {
        "linker": root / "linker" / "kernel.ld",
        "limine": root / "boot" / "limine.conf",
        "script": root / "scripts" / "build_boot_image.sh",
        "memory": root / "kernel" / "arch" / "x86_64" / "memory.asm",
        "doc": root / "docs" / "BOOT_IMAGE.md",
        "boot_doc": root / "docs" / "BOOT.md",
        "blockers": root / "docs" / "BOOT_BLOCKERS.md",
        "report": root / "artifacts" / "runtime" / "boot_blocker_report.json",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    paths["linker"].write_text("ENTRY(_start)\n.text\n.rodata\n.data\n.bss\n")
    paths["limine"].write_text("PROTOCOL=limine\nKERNEL_PATH=boot:///boot/kozo/kozo-kernel.elf\n")
    paths["script"].write_text("linker/kernel.ld\nboot/limine.conf\nartifacts/runtime/boot_image\n")
    paths["memory"].write_text("global memset\nglobal memmove\n")
    paths["doc"].write_text("This phase does not prove boot success.\nThis phase does not prove QEMU execution.\nartifacts/runtime/boot_image/\n")
    paths["boot_doc"].write_text("Remaining blocker: `missing_iso_generation_tooling`.\n")
    paths["blockers"].write_text("The remaining blocker is `missing_iso_generation_tooling`.\n")
    paths["report"].write_text(json.dumps(valid_report(), indent=2) + "\n")
    return paths


def valid_report() -> dict[str, object]:
    return {
        "blocker_category": "missing_iso_generation_tooling",
        "missing_components": ["Limine executable"],
    }


def patch_validator_paths(paths: dict[str, Path]):
    old_paths = (
        validator_module._LINKER_PATH,
        validator_module._LIMINE_CONFIG_PATH,
        validator_module._BUILD_SCRIPT_PATH,
        validator_module._MEMORY_ASM_PATH,
        validator_module._BOOT_IMAGE_DOC_PATH,
        validator_module._BOOT_DOC_PATH,
        validator_module._BOOT_BLOCKERS_PATH,
        validator_module._BOOT_BLOCKER_REPORT_PATH,
    )
    validator_module._LINKER_PATH = paths["linker"]
    validator_module._LIMINE_CONFIG_PATH = paths["limine"]
    validator_module._BUILD_SCRIPT_PATH = paths["script"]
    validator_module._MEMORY_ASM_PATH = paths["memory"]
    validator_module._BOOT_IMAGE_DOC_PATH = paths["doc"]
    validator_module._BOOT_DOC_PATH = paths["boot_doc"]
    validator_module._BOOT_BLOCKERS_PATH = paths["blockers"]
    validator_module._BOOT_BLOCKER_REPORT_PATH = paths["report"]
    return old_paths


def restore_validator_paths(old_paths) -> None:
    (
        validator_module._LINKER_PATH,
        validator_module._LIMINE_CONFIG_PATH,
        validator_module._BUILD_SCRIPT_PATH,
        validator_module._MEMORY_ASM_PATH,
        validator_module._BOOT_IMAGE_DOC_PATH,
        validator_module._BOOT_DOC_PATH,
        validator_module._BOOT_BLOCKERS_PATH,
        validator_module._BOOT_BLOCKER_REPORT_PATH,
    ) = old_paths


if __name__ == "__main__":
    unittest.main()
