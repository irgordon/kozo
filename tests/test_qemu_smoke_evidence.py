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
        "missing_byte_count": "test_fails_when_byte_count_is_missing",
        "marker_consistency": "test_fails_when_observed_markers_do_not_match_log",
        "blocker_taxonomy_mismatch": "test_fails_when_blocker_does_not_match_log_taxonomy",
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

    def test_accepts_limine_not_reached_blocker(self):
        result = self.validate_blocked_fixture("limine_not_reached", "")

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_accepts_kernel_not_loaded_blocker(self):
        result = self.validate_blocked_fixture(
            "kernel_not_loaded",
            "limine: Loading executable `/boot/kozo/kozo-kernel.elf`\n"
            "PANIC: limine: Failed to open executable with path `/boot/kozo/kozo-kernel.elf`\n",
        )

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_accepts_kernel_entry_not_reached_blocker(self):
        result = self.validate_blocked_fixture("kernel_entry_not_reached", "Limine\nentry point: 0x200000\n")

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_accepts_serial_not_initialized_blocker(self):
        result = self.validate_blocked_fixture("serial_not_initialized", "KOZO_EARLY_0_ENTRY\n")

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_accepts_marker_not_emitted_blocker(self):
        result = self.validate_blocked_fixture(
            "marker_not_emitted",
            "KOZO_EARLY_0_ENTRY\nKOZO_EARLY_1_SERIAL_INIT_START\nKOZO_EARLY_2_SERIAL_INIT_OK\n",
        )

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_accepts_qemu_timeout_fallback_blocker(self):
        result = self.validate_blocked_fixture("qemu_timeout", "KOZO_EARLY_1_SERIAL_INIT_START\n")

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

    def test_fails_when_byte_count_is_missing(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(mutate_metadata=lambda metadata: metadata | {"serial_log_bytes": None})

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "field_mismatch", "qemu_smoke.serial_log_bytes")

    def test_fails_when_observed_markers_do_not_match_log(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(mutate_metadata=lambda metadata: metadata | {"observed_markers": []})

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "marker_consistency", "qemu_smoke.observed_markers")

    def test_fails_when_blocker_does_not_match_log_taxonomy(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            metadata_factory=lambda: valid_blocked_metadata("kernel_not_loaded", ""),
            blocker_factory=lambda: valid_blocker("kernel_not_loaded"),
            mutate_serial_log=lambda _: "",
        )

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "blocker_taxonomy_mismatch", "qemu_smoke.blocker_category")

    def test_fails_when_limine_open_failure_is_marked_as_kernel_entry(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        limine_open_failure = (
            "limine: Loading executable `/boot/kozo/kozo-kernel.elf`\n"
            "PANIC: limine: Failed to open executable with path `/boot/kozo/kozo-kernel.elf`\n"
        )
        result = self.validate_fixture(
            metadata_factory=lambda: valid_blocked_metadata("kernel_entry_not_reached", limine_open_failure),
            blocker_factory=lambda: valid_blocker("kernel_entry_not_reached"),
            mutate_serial_log=lambda _: limine_open_failure,
        )

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "blocker_taxonomy_mismatch", "qemu_smoke.blocker_category")

    def test_fails_when_blocker_category_is_unknown(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            metadata_factory=lambda: valid_blocked_metadata("mystery_blocker", ""),
            blocker_factory=lambda: valid_blocker("mystery_blocker"),
            mutate_metadata=lambda metadata: metadata | {"blocker_category": "mystery_blocker"},
            mutate_serial_log=lambda _: "",
        )

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "unknown_blocker_category", "qemu_smoke.blocker_category")

    def test_fails_when_blocker_report_mismatches_metadata(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            metadata_factory=lambda: valid_blocked_metadata("qemu_timeout", ""),
            blocker_factory=lambda: valid_blocker("qemu_timeout"),
            mutate_metadata=lambda metadata: metadata | {"blocker_category": "missing_qemu_tooling"},
            mutate_serial_log=lambda _: "",
        )

        self.assertEqual(result.status, "fail")
        self.assert_qemu_failure(result, "blocker_report_mismatch", "boot_blocker.blocker_category")

    def test_fails_when_blocked_metadata_has_marker_in_serial_log(self):
        self.assertEqual("qemu_smoke_evidence", QemuSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            metadata_factory=lambda: valid_blocked_metadata("qemu_timeout", default_serial_log_text()),
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

    def validate_blocked_fixture(self, blocker: str, serial_text: str):
        return self.validate_fixture(
            metadata_factory=lambda: valid_blocked_metadata(blocker, serial_text),
            blocker_factory=lambda: valid_blocker(blocker),
            mutate_serial_log=lambda _: serial_text,
        )

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
    paths["serial_log"].write_text(default_serial_log_text())
    paths["stderr_log"].write_text(default_stderr_log_text())
    paths["blocker"].write_text(json.dumps(blocker, indent=2) + "\n")
    paths["boot_image"].write_bytes(b"iso")
    paths["boot_doc"].write_text(valid_doc_text())
    paths["runtime_doc"].write_text(valid_doc_text())
    paths["release_doc"].write_text(valid_doc_text())
    return paths


def valid_pass_metadata() -> dict[str, object]:
    return valid_metadata("pass")


def valid_blocked_metadata(blocker: str, serial_text: str) -> dict[str, object]:
    metadata = valid_metadata("blocked", serial_text=serial_text)
    metadata["blocker_category"] = blocker
    metadata["qemu_exit_code"] = 124
    metadata["timed_out"] = True
    metadata["proves"] = [
        "QEMU serial smoke was attempted or checked",
        "QEMU boot evidence remains unclaimed",
    ]
    return metadata


def valid_metadata(outcome: str, *, serial_text: str | None = None, stderr_text: str | None = None) -> dict[str, object]:
    serial_text = default_serial_log_text() if serial_text is None else serial_text
    stderr_text = default_stderr_log_text() if stderr_text is None else stderr_text
    observed = observed_markers(serial_text, stderr_text)
    return {
        "version": 0,
        "phase": "v0.4.1",
        "evidence_type": "qemu-serial-smoke",
        "outcome": outcome,
        "boot_protocol": "Limine",
        "architecture": "x86_64",
        "generated_by": "scripts/qemu_smoke.sh",
        "boot_image": "artifacts/runtime/boot_image/kozo.iso",
        "serial_log": "artifacts/runtime/qemu_smoke.log",
        "stderr_log": "artifacts/runtime/qemu_smoke.stderr.log",
        "expected_marker": "KOZO_BOOT_SMOKE_OK",
        "early_markers": list(early_markers()),
        "observed_markers": observed,
        "earliest_observed_marker": observed[0] if observed else "",
        "qemu_exit_code": 0,
        "timed_out": False,
        "timeout_seconds": 20,
        "serial_log_bytes": len(serial_text.encode()),
        "stderr_log_bytes": len(stderr_text.encode()),
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
        "phase": "v0.4.1",
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


def default_serial_log_text() -> str:
    return "Limine\nKOZO_BOOT_SMOKE_OK\n"


def default_stderr_log_text() -> str:
    return "qemu stderr\n"


def early_markers() -> tuple[str, ...]:
    return (
        "KOZO_EARLY_0_ENTRY",
        "KOZO_EARLY_1_SERIAL_INIT_START",
        "KOZO_EARLY_2_SERIAL_INIT_OK",
        "KOZO_BOOT_SMOKE_OK",
    )


def observed_markers(serial_text: str, stderr_text: str) -> list[str]:
    combined = f"{serial_text}\n{stderr_text}"
    return [marker for marker in early_markers() if marker in combined]


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
