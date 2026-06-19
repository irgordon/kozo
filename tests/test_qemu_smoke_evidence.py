from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, QEMU_SMOKE_EVIDENCE_INVALID
from harness.validators_impl import qemu_smoke_evidence as validator_module
from harness.validators_impl.qemu_smoke_evidence import QemuSmokeEvidenceValidator

KOZO_NEGATIVE_COVERAGE = {
    "qemu_smoke_evidence": {
        "missing_metadata": "test_fails_when_metadata_is_missing",
        "invalid_metadata": "test_fails_when_metadata_is_invalid_json",
        "missing_stderr_log": "test_fails_when_stderr_log_is_missing",
        "missing_serial_log": "test_fails_when_pass_metadata_has_no_serial_log",
        "marker_missing": "test_fails_when_marker_is_missing_from_serial_log",
        "wrong_evidence_type": "test_fails_when_evidence_type_is_wrong",
        "wrong_boot_protocol": "test_fails_when_boot_protocol_is_wrong",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "unknown_blocker_category": "test_fails_when_blocker_category_is_unknown",
        "blocker_report_mismatch": "test_fails_when_blocker_report_mismatches_metadata",
        "marker_present_but_blocked": "test_fails_when_blocked_metadata_has_marker_in_serial_log",
        "missing_release_evidence_reference": "test_fails_when_release_evidence_reference_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class QemuSmokeEvidenceValidatorTests(unittest.TestCase):
    def test_passes_when_qemu_smoke_evidence_is_valid(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_passes_when_marker_is_present_after_qemu_timeout(self):
        result = self.validate_fixture(mutate_metadata=lambda metadata: metadata | {"qemu_exit_code": 124})

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_metadata_is_missing(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(remove_metadata=True)

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "missing_metadata", "qemu_smoke.metadata")

    def test_fails_when_metadata_is_invalid_json(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(mutate_metadata_text=lambda _: "{not json")

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "invalid_metadata", "qemu_smoke.metadata")

    def test_fails_when_stderr_log_is_missing(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(remove_stderr_log=True)

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "missing_stderr_log", "qemu_smoke.stderr_log")

    def test_fails_when_pass_metadata_has_no_serial_log(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(remove_serial_log=True)

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "missing_serial_log", "qemu_smoke.serial_log")

    def test_fails_when_marker_is_missing_from_serial_log(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(mutate_serial_log=lambda _: "Limine output only\n")

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "marker_missing", "qemu_smoke.expected_marker")

    def test_fails_when_evidence_type_is_wrong(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(mutate_metadata=lambda metadata: metadata | {"evidence_type": "runtime-smoke"})

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "field_mismatch", "qemu_smoke.evidence_type")

    def test_fails_when_boot_protocol_is_wrong(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(mutate_metadata=lambda metadata: metadata | {"boot_protocol": "Multiboot2"})

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "field_mismatch", "qemu_smoke.boot_protocol")

    def test_fails_when_non_goal_is_missing(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            mutate_metadata=lambda metadata: remove_list_value(metadata, "does_not_prove", "production readiness")
        )

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "missing_non_goal", "qemu_smoke.does_not_prove.production readiness")

    def test_fails_when_blocker_category_is_unknown(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            metadata_factory=valid_blocked_metadata,
            blocker_factory=lambda: valid_blocker("mystery_blocker"),
            mutate_metadata=lambda metadata: metadata | {"blocker_category": "mystery_blocker"},
            mutate_serial_log=lambda _: "",
        )

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "unknown_blocker_category", "qemu_smoke.blocker_category")

    def test_fails_when_blocker_report_mismatches_metadata(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            metadata_factory=valid_blocked_metadata,
            blocker_factory=lambda: valid_blocker("qemu_timeout"),
            mutate_metadata=lambda metadata: metadata | {"blocker_category": "missing_qemu_tooling"},
            mutate_serial_log=lambda _: "",
        )

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "blocker_report_mismatch", "boot_blocker.blocker_category")

    def test_fails_when_blocked_metadata_has_marker_in_serial_log(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            metadata_factory=valid_blocked_metadata,
            blocker_factory=lambda: valid_blocker("qemu_timeout"),
        )

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "marker_present_but_blocked", "qemu_smoke.outcome")

    def test_fails_when_release_evidence_reference_is_missing(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            mutate_release_doc=lambda text: text.replace("artifacts/runtime/qemu_smoke.metadata.json", "artifacts/runtime/missing.json")
        )

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(
            result,
            "missing_documentation_reference",
            "docs/RELEASE_EVIDENCE.md.artifacts/runtime/qemu_smoke.metadata.json",
        )

    def test_failure_diagnostic_names_field(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(mutate_metadata=lambda metadata: metadata | {"validator": "other"})

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "field_mismatch", "qemu_smoke.validator")

    def validate_fixture(
        self,
        *,
        metadata_factory=None,
        blocker_factory=None,
        remove_metadata: bool = False,
        remove_serial_log: bool = False,
        remove_stderr_log: bool = False,
        mutate_metadata=None,
        mutate_metadata_text=None,
        mutate_serial_log=None,
        mutate_release_doc=None,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture_files(root, metadata_factory, blocker_factory)

            if remove_metadata:
                paths["metadata"].unlink()
            elif mutate_metadata is not None:
                metadata = json.loads(paths["metadata"].read_text())
                paths["metadata"].write_text(json.dumps(mutate_metadata(metadata), indent=2) + "\n")
            elif mutate_metadata_text is not None:
                paths["metadata"].write_text(mutate_metadata_text(paths["metadata"].read_text()))

            if remove_serial_log:
                paths["serial_log"].unlink()
            elif mutate_serial_log is not None:
                paths["serial_log"].write_text(mutate_serial_log(paths["serial_log"].read_text()))

            if remove_stderr_log:
                paths["stderr_log"].unlink()

            if mutate_release_doc is not None:
                paths["release_doc"].write_text(mutate_release_doc(paths["release_doc"].read_text()))

            old_paths = patch_validator_paths(paths)
            try:
                return QemuSmokeEvidenceValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_qemu_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, QEMU_SMOKE_EVIDENCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path, metadata_factory, blocker_factory) -> dict[str, Path]:
    paths = {
        "metadata": root / "artifacts" / "runtime" / "qemu_smoke.metadata.json",
        "serial_log": root / "artifacts" / "runtime" / "qemu_smoke.log",
        "stderr_log": root / "artifacts" / "runtime" / "qemu_smoke.stderr.log",
        "blocker": root / "artifacts" / "runtime" / "boot_blocker_report.json",
        "boot_image": root / "artifacts" / "runtime" / "boot_image" / "kozo.iso",
        "boot_doc": root / "docs" / "BOOT.md",
        "runtime_doc": root / "docs" / "RUNTIME_EVIDENCE.md",
        "release_doc": root / "docs" / "RELEASE_EVIDENCE.md",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    metadata = (metadata_factory or valid_pass_metadata)()
    blocker = (blocker_factory or (lambda: valid_blocker("none")))()
    metadata["boot_image"] = str(paths["boot_image"])

    paths["metadata"].write_text(json.dumps(metadata, indent=2) + "\n")
    paths["serial_log"].write_text("Limine\nKOZO_BOOT_SMOKE_OK\n")
    paths["stderr_log"].write_text("qemu stderr\n")
    paths["blocker"].write_text(json.dumps(blocker, indent=2) + "\n")
    paths["boot_image"].write_bytes(b"iso")
    paths["boot_doc"].write_text(valid_doc_text())
    paths["runtime_doc"].write_text(valid_doc_text())
    paths["release_doc"].write_text(valid_doc_text())
    return paths


def valid_pass_metadata() -> dict[str, object]:
    return valid_metadata("pass")


def valid_blocked_metadata() -> dict[str, object]:
    metadata = valid_metadata("blocked")
    metadata["blocker_category"] = "qemu_timeout"
    metadata["proves"] = [
        "QEMU serial smoke was attempted or checked",
        "QEMU boot evidence remains unclaimed",
    ]
    return metadata


def valid_metadata(outcome: str) -> dict[str, object]:
    return {
        "version": 0,
        "phase": "v0.3.9",
        "evidence_type": "qemu-serial-smoke",
        "outcome": outcome,
        "boot_protocol": "Limine",
        "architecture": "x86_64",
        "generated_by": "scripts/qemu_smoke.sh",
        "boot_image": "artifacts/runtime/boot_image/kozo.iso",
        "serial_log": "artifacts/runtime/qemu_smoke.log",
        "stderr_log": "artifacts/runtime/qemu_smoke.stderr.log",
        "expected_marker": "KOZO_BOOT_SMOKE_OK",
        "qemu_exit_code": 0,
        "qemu_timeout_seconds": 20,
        "serial_log_byte_count": 27,
        "validator": "qemu_smoke_evidence",
        "proves": [
            "QEMU launched the KOZO ISO",
            "serial output was captured",
            "the expected KOZO boot smoke marker was observed",
        ],
        "does_not_prove": [
            "hardware trap execution",
            "Linux compatibility",
            "POSIX compatibility",
            "general userspace execution",
            "process model behavior",
            "VFS behavior",
            "scheduler maturity",
            "ELF loading",
            "file descriptor behavior",
            "production readiness",
        ],
    }


def valid_blocker(category: str) -> dict[str, object]:
    return {
        "phase": "v0.3.9",
        "outcome": "pass" if category == "none" else "blocked",
        "blocker_category": category,
    }


def valid_doc_text() -> str:
    return "\n".join(
        (
            "artifacts/runtime/qemu_smoke.log",
            "artifacts/runtime/qemu_smoke.stderr.log",
            "artifacts/runtime/qemu_smoke.metadata.json",
            "qemu_smoke_evidence",
            "KOZO_BOOT_SMOKE_OK",
        )
    )


def remove_list_value(metadata: dict[str, object], key: str, value: str) -> dict[str, object]:
    metadata[key] = [item for item in metadata[key] if item != value]
    return metadata


def patch_validator_paths(paths: dict[str, Path]):
    old_paths = (
        validator_module._METADATA_PATH,
        validator_module._SERIAL_LOG_PATH,
        validator_module._STDERR_LOG_PATH,
        validator_module._BOOT_BLOCKER_REPORT_PATH,
        validator_module._BOOT_DOC_PATH,
        validator_module._RUNTIME_EVIDENCE_PATH,
        validator_module._RELEASE_EVIDENCE_PATH,
    )
    validator_module._METADATA_PATH = paths["metadata"]
    validator_module._SERIAL_LOG_PATH = paths["serial_log"]
    validator_module._STDERR_LOG_PATH = paths["stderr_log"]
    validator_module._BOOT_BLOCKER_REPORT_PATH = paths["blocker"]
    validator_module._BOOT_DOC_PATH = paths["boot_doc"]
    validator_module._RUNTIME_EVIDENCE_PATH = paths["runtime_doc"]
    validator_module._RELEASE_EVIDENCE_PATH = paths["release_doc"]
    return old_paths


def restore_validator_paths(old_paths) -> None:
    (
        validator_module._METADATA_PATH,
        validator_module._SERIAL_LOG_PATH,
        validator_module._STDERR_LOG_PATH,
        validator_module._BOOT_BLOCKER_REPORT_PATH,
        validator_module._BOOT_DOC_PATH,
        validator_module._RUNTIME_EVIDENCE_PATH,
        validator_module._RELEASE_EVIDENCE_PATH,
    ) = old_paths


if __name__ == "__main__":
    unittest.main()
