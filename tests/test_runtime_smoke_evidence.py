from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, RUNTIME_SMOKE_EVIDENCE_INVALID
from harness.validators_impl import runtime_smoke_evidence as validator_module
from harness.validators_impl.runtime_smoke_evidence import RuntimeSmokeEvidenceValidator

KOZO_NEGATIVE_COVERAGE = {
    "runtime_smoke_evidence": {
        "missing_runtime_artifact": "test_fails_when_runtime_smoke_artifact_is_missing",
        "empty_runtime_artifact": "test_fails_when_runtime_smoke_artifact_is_empty",
        "missing_expected_marker": "test_fails_when_expected_runtime_marker_is_missing",
        "failure_marker_present": "test_fails_when_failure_marker_is_present",
        "malformed_runtime_metadata": "test_fails_when_runtime_metadata_is_malformed",
        "missing_release_evidence_reference": "test_fails_when_release_evidence_reference_is_missing",
        "diagnostic_names_runtime_field": "test_failure_diagnostic_names_runtime_field",
    }
}


class RuntimeSmokeEvidenceValidatorTests(unittest.TestCase):
    def test_passes_when_runtime_smoke_evidence_is_valid(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_runtime_smoke_artifact_is_missing(self):
        self.assertEqual("runtime_smoke_evidence", RuntimeSmokeEvidenceValidator.name)
        result = self.validate_fixture(remove_log=True)

        self.assertEqual(result.status, "fail")
        self.assert_runtime_failure(result, "missing_runtime_artifact", "artifacts.runtime.runtime_smoke_log")

    def test_fails_when_runtime_smoke_artifact_is_empty(self):
        self.assertEqual("runtime_smoke_evidence", RuntimeSmokeEvidenceValidator.name)
        result = self.validate_fixture(mutate_log=lambda _: "")

        self.assertEqual(result.status, "fail")
        self.assert_runtime_failure(result, "empty_runtime_artifact", "artifacts.runtime.runtime_smoke_log")

    def test_fails_when_expected_runtime_marker_is_missing(self):
        self.assertEqual("runtime_smoke_evidence", RuntimeSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            mutate_log=lambda text: text.replace("KOZO_RUNTIME_SMOKE_MARKER=syscall_entry\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assert_runtime_failure(result, "missing_expected_marker", "runtime_smoke.marker.syscall_entry")

    def test_fails_when_failure_marker_is_present(self):
        self.assertEqual("runtime_smoke_evidence", RuntimeSmokeEvidenceValidator.name)
        result = self.validate_fixture(mutate_log=lambda text: text + "KOZO_RUNTIME_SMOKE_RESULT=fail\n")

        self.assertEqual(result.status, "fail")
        self.assert_runtime_failure(result, "failure_marker_present", "runtime_smoke.failure_marker.KOZO_RUNTIME_SMOKE_RESULT=fail")

    def test_fails_when_runtime_metadata_is_malformed(self):
        self.assertEqual("runtime_smoke_evidence", RuntimeSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            mutate_log=lambda text: text.replace("KOZO_RUNTIME_SMOKE_VERSION=1", "KOZO_RUNTIME_SMOKE_VERSION=zero")
        )

        self.assertEqual(result.status, "fail")
        self.assert_runtime_failure(result, "malformed_runtime_metadata", "runtime_smoke.version")

    def test_fails_when_release_evidence_reference_is_missing(self):
        self.assertEqual("runtime_smoke_evidence", RuntimeSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            mutate_release_evidence=lambda text: text.replace("artifacts/runtime/runtime_smoke.log", "artifacts/runtime/missing.log")
        )

        self.assertEqual(result.status, "fail")
        self.assert_runtime_failure(result, "missing_release_evidence_reference", "release_evidence.runtime_smoke_log")

    def test_failure_diagnostic_names_runtime_field(self):
        self.assertEqual("runtime_smoke_evidence", RuntimeSmokeEvidenceValidator.name)
        result = self.validate_fixture(
            mutate_log=lambda text: text.replace("KOZO_RUNTIME_SMOKE_MARKER=_start\n", "")
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_SMOKE_EVIDENCE_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)
        self.assertEqual(result.meta["reason"], "missing_expected_marker")
        self.assertEqual(result.meta["contract_field"], "runtime_smoke.marker._start")

    def validate_fixture(self, mutate_log=None, mutate_release_evidence=None, remove_log=False):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            log_path = root / "artifacts" / "runtime" / "runtime_smoke.log"
            release_path = root / "docs" / "RELEASE_EVIDENCE.md"
            log_path.parent.mkdir(parents=True)
            release_path.parent.mkdir(parents=True)

            log_path.write_text(_valid_runtime_log())
            release_path.write_text(_valid_release_evidence())

            if mutate_log is not None:
                log_path.write_text(mutate_log(log_path.read_text()))
            if mutate_release_evidence is not None:
                release_path.write_text(mutate_release_evidence(release_path.read_text()))
            if remove_log:
                log_path.unlink()

            original_log_path = validator_module._RUNTIME_LOG_PATH
            original_release_path = validator_module._RELEASE_EVIDENCE_PATH
            try:
                validator_module._RUNTIME_LOG_PATH = log_path
                validator_module._RELEASE_EVIDENCE_PATH = release_path
                return RuntimeSmokeEvidenceValidator().validate({})
            finally:
                validator_module._RUNTIME_LOG_PATH = original_log_path
                validator_module._RELEASE_EVIDENCE_PATH = original_release_path

    def assert_runtime_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_SMOKE_EVIDENCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def _valid_runtime_log() -> str:
    return "\n".join(
        (
            "KOZO_RUNTIME_SMOKE_VERSION=1",
            "KOZO_RUNTIME_SMOKE_KIND=runtime-adjacent-object-symbol-smoke",
            "KOZO_RUNTIME_SMOKE_SCOPE=freestanding_amd64_sysv_object",
            "KOZO_RUNTIME_SMOKE_LIMITATION=not_boot_or_hardware_trap_execution",
            "KOZO_RUNTIME_SMOKE_MARKER=_start",
            "KOZO_RUNTIME_SMOKE_MARKER=kernel_entry",
            "KOZO_RUNTIME_SMOKE_MARKER=syscall_entry",
            "KOZO_RUNTIME_SMOKE_MARKER=syscall_dispatch",
            "KOZO_RUNTIME_SMOKE_MARKER=SYSCALL[DEBUG_HEARTBEAT] Recv Seq: 0x",
            "KOZO_RUNTIME_SMOKE_MARKER=SYSCALL[DEBUG_HEARTBEAT] New Time: 0x",
            "KOZO_RUNTIME_SMOKE_RESULT=pass",
            "",
        )
    )


def _valid_release_evidence() -> str:
    return "Required artifact: artifacts/runtime/runtime_smoke.log\n"


if __name__ == "__main__":
    unittest.main()
