from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import ABI_MANIFEST_INVALID
from harness.validators_impl import abi_manifest as abi_manifest_validator
from harness.validators_impl.abi_manifest import AbiManifestValidator

KOZO_NEGATIVE_COVERAGE = {
    "abi_manifest": {
        "missing_manifest_file": "test_fails_when_manifest_file_is_missing",
        "invalid_json": "test_fails_when_manifest_json_is_invalid",
        "schema_violation": "test_fails_when_manifest_schema_is_invalid",
        "missing_generated_binding_path": "test_fails_when_generated_binding_path_is_missing",
        "syscall_constant_mismatch": "test_fails_when_manifest_syscall_constant_mismatches_header",
        "layout_field_offset_mismatch": "test_fails_when_manifest_layout_field_offset_mismatches_header",
        "diagnostic_names_manifest_field": "test_failure_diagnostic_names_manifest_field",
    }
}


class AbiManifestValidatorTests(unittest.TestCase):
    def test_fails_when_manifest_file_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = self.validate_manifest(Path(temporary_directory) / "missing.json")

        self.assertEqual(result.status, "fail")

        self.assert_manifest_failure(result, "missing_manifest_file", "manifest")

    def test_fails_when_manifest_json_is_invalid(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            manifest_path = Path(temporary_directory) / "manifest.json"
            manifest_path.write_text("{")

            result = self.validate_manifest(manifest_path)

        self.assertEqual(result.status, "fail")

        self.assert_manifest_failure(result, "invalid_manifest_json", "manifest")

    def test_fails_when_manifest_schema_is_invalid(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            manifest_path = Path(temporary_directory) / "manifest.json"
            manifest_path.write_text(json.dumps({"version": 0}))

            result = self.validate_manifest(manifest_path)

        self.assertEqual(result.status, "fail")

        self.assert_manifest_failure(result, "manifest_schema_violation", "manifest")

    def test_fails_when_generated_binding_path_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_manifest_fixture(root)
            manifest = self.valid_manifest(paths)
            manifest["generated_bindings"]["rust"] = str(root / "missing.rs")
            manifest_path = self.write_manifest(root, manifest)

            result = self.validate_manifest(manifest_path)

        self.assertEqual(result.status, "fail")

        self.assert_manifest_failure(result, "manifest_path_missing", "generated_bindings.rust")

    def test_fails_when_manifest_syscall_constant_mismatches_header(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_manifest_fixture(root)
            manifest = self.valid_manifest(paths)
            manifest["constants"]["syscalls"]["K_SYSCALL_DEBUG_HEARTBEAT"] = 2
            manifest_path = self.write_manifest(root, manifest)

            result = self.validate_manifest(manifest_path)

        self.assertEqual(result.status, "fail")

        self.assert_manifest_failure(result, "manifest_constant_mismatch", "constants.syscalls.K_SYSCALL_DEBUG_HEARTBEAT")

    def test_fails_when_header_is_missing_nop_syscall_constant(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_manifest_fixture(root)
            paths["header"].write_text(self.valid_header().replace("\tK_SYSCALL_NOP = 0,\n", ""))
            manifest_path = self.write_manifest(root, self.valid_manifest(paths))

            result = self.validate_manifest(manifest_path)

        self.assertEqual(result.status, "fail")

        self.assert_manifest_failure(result, "manifest_constant_missing_in_header", "constants.syscalls.K_SYSCALL_NOP")

    def test_fails_when_manifest_layout_field_offset_mismatches_header(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_manifest_fixture(root)
            manifest = self.valid_manifest(paths)
            manifest["layouts"]["heartbeat_payload"]["fields"][1]["offset"] = 12
            manifest_path = self.write_manifest(root, manifest)

            result = self.validate_manifest(manifest_path)

        self.assertEqual(result.status, "fail")

        self.assert_manifest_failure(result, "manifest_layout_field_offset_mismatch", "layouts.heartbeat_payload.fields.timestamp.offset")

    def test_failure_diagnostic_names_manifest_field(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_manifest_fixture(root)
            manifest = self.valid_manifest(paths)
            manifest["constants"]["status"]["K_OK"] = 9
            manifest_path = self.write_manifest(root, manifest)

            result = self.validate_manifest(manifest_path)

        self.assertEqual(result.status, "fail")

        self.assert_manifest_failure(result, "manifest_constant_mismatch", "constants.status.K_OK")

    def validate_manifest(self, manifest_path: Path):
        original_manifest_path = abi_manifest_validator._MANIFEST_PATH
        abi_manifest_validator._MANIFEST_PATH = manifest_path
        try:
            return AbiManifestValidator().validate({})
        finally:
            abi_manifest_validator._MANIFEST_PATH = original_manifest_path

    def assert_manifest_failure(self, result, reason: str, manifest_field: str) -> None:
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, ABI_MANIFEST_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["manifest_field"], manifest_field)

    def write_manifest_fixture(self, root: Path) -> dict[str, Path]:
        paths = {
            "header": root / "kozo_abi.h",
            "rust": root / "kozo_abi.rs",
            "odin": root / "kozo_abi.odin",
        }
        paths["header"].write_text(self.valid_header())
        paths["rust"].write_text(
            "pub const K_SYSCALL_NOP: K_SYSCALL_ID = 0;\n"
            "pub const K_SYSCALL_DEBUG_HEARTBEAT: K_SYSCALL_ID = 1;\n"
        )
        paths["odin"].write_text(
            "K_SYSCALL_NOP : K_SYSCALL_ID : 0\n"
            "K_SYSCALL_DEBUG_HEARTBEAT : K_SYSCALL_ID : 1\n"
        )
        return paths

    def write_manifest(self, root: Path, manifest: dict[str, object]) -> Path:
        manifest_path = root / "kozo_abi_manifest.json"
        manifest_path.write_text(json.dumps(manifest))
        return manifest_path

    def valid_manifest(self, paths: dict[str, Path]) -> dict[str, object]:
        return {
            "version": 0,
            "canonical_header": str(paths["header"]),
            "generated_bindings": {
                "rust": str(paths["rust"]),
                "odin": str(paths["odin"]),
            },
            "constants": {
                "status": {
                    "K_OK": 0,
                    "K_INVALID": 1,
                },
                "syscalls": {
                    "K_SYSCALL_NOP": 0,
                    "K_SYSCALL_DEBUG_HEARTBEAT": 1,
                },
            },
            "layouts": {
                "heartbeat_payload": {
                    "c_name": "k_heartbeat_payload_t",
                    "rust_name": "HeartbeatPayload",
                    "odin_name": "Heartbeat_Payload",
                    "size": 24,
                    "alignment": 8,
                    "fields": [
                        {"name": "sequence", "width": 8, "offset": 0},
                        {"name": "timestamp", "width": 8, "offset": 8},
                        {"name": "status_bits", "width": 4, "offset": 16},
                    ],
                }
            },
            "heartbeat": {
                "request": {
                    "sequence": "0xCAFEFEED",
                    "timestamp": 0,
                    "status_bits": "K_INVALID",
                },
                "response": {
                    "sequence": "0xCAFEFEEE",
                    "timestamp": "0xDEADBEEF",
                    "status_bits": "K_OK",
                },
            },
        }

    def valid_header(self) -> str:
        return (
            "typedef enum k_status_t {\n"
            "\tK_OK = 0,\n"
            "\tK_INVALID = 1,\n"
            "} k_status_t;\n"
            "typedef enum k_syscall_id_t {\n"
            "\tK_SYSCALL_NOP = 0,\n"
            "\tK_SYSCALL_DEBUG_HEARTBEAT = 1,\n"
            "} k_syscall_id_t;\n"
            "typedef struct k_heartbeat_payload_t {\n"
            "\tuint64_t sequence;\n"
            "\tuint64_t timestamp;\n"
            "\tuint32_t status_bits;\n"
            "} k_heartbeat_payload_t;\n"
        )


if __name__ == "__main__":
    unittest.main()
