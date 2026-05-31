from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import LAYOUT_PARITY_MISMATCH
from harness.validators_impl import layout_parity
from harness.validators_impl.layout_parity import LayoutParityValidator

KOZO_NEGATIVE_COVERAGE = {
    "layout_parity": {
        "missing_field": "test_fails_when_canonical_field_is_missing",
        "wrong_field_order": "test_fails_when_rust_field_order_is_wrong",
        "wrong_rust_field_width": "test_fails_when_rust_field_width_is_wrong",
        "wrong_odin_field_width": "test_fails_when_odin_field_width_is_wrong",
        "wrong_rust_offset": "test_fails_when_rust_field_offset_is_wrong",
        "wrong_odin_offset": "test_fails_when_odin_field_offset_is_wrong",
        "wrong_struct_size": "test_fails_when_canonical_struct_size_is_wrong",
        "dead_or_stale_struct": "test_fails_when_dead_struct_definition_is_duplicated",
        "diagnostic_names_layout_field": "test_failure_diagnostic_names_layout_field",
    }
}


class LayoutParityValidatorTests(unittest.TestCase):
    def test_passes_when_heartbeat_layout_matches_contract(self):
        result = self.validate_layout()

        self.assertEqual(result.status, "pass")

    def test_fails_when_canonical_field_is_missing(self):
        result = self.validate_layout(
            header=self.valid_header().replace("\tuint32_t status_bits;\n", "")
        )

        self.assertEqual(result.status, "fail")

        self.assert_layout_failure(result, "canonical_missing_field", "canonical.status_bits")

    def test_fails_when_rust_field_order_is_wrong(self):
        result = self.validate_layout(
            rust=self.valid_rust().replace(
                "    pub sequence: u64,\n    pub timestamp: u64,\n",
                "    pub timestamp: u64,\n    pub sequence: u64,\n",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_layout_failure(result, "rust_wrong_field_order", "rust.k_heartbeat_payload_t")

    def test_fails_when_rust_field_width_is_wrong(self):
        result = self.validate_layout(
            rust=self.valid_rust().replace("    pub timestamp: u64,\n", "    pub timestamp: u32,\n")
        )

        self.assertEqual(result.status, "fail")

        self.assert_layout_failure(result, "rust_wrong_field_width", "rust.timestamp")

    def test_fails_when_odin_field_width_is_wrong(self):
        result = self.validate_layout(
            odin=self.valid_odin().replace("\ttimestamp: u64,\n", "\ttimestamp: u32,\n")
        )

        self.assertEqual(result.status, "fail")

        self.assert_layout_failure(result, "odin_wrong_field_width", "odin.timestamp")

    def test_fails_when_rust_field_offset_is_wrong(self):
        result = self.validate_layout(
            rust=self.valid_rust().replace(
                "    pub timestamp: u64,\n",
                "    pub padding: u32,\n    pub timestamp: u64,\n",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_layout_failure(result, "rust_wrong_field_offset", "rust.timestamp")

    def test_fails_when_odin_field_offset_is_wrong(self):
        result = self.validate_layout(
            odin=self.valid_odin().replace(
                "\ttimestamp: u64,\n",
                "\tpadding: u32,\n\ttimestamp: u64,\n",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_layout_failure(result, "odin_wrong_field_offset", "odin.timestamp")

    def test_fails_when_canonical_struct_size_is_wrong(self):
        result = self.validate_layout(
            header=self.valid_header().replace(
                "\tuint32_t status_bits;\n",
                "\tuint32_t status_bits;\n\tuint64_t trailing;\n",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_layout_failure(result, "canonical_wrong_struct_size", "canonical.k_heartbeat_payload_t")

    def test_fails_when_dead_struct_definition_is_duplicated(self):
        result = self.validate_layout(rust=self.valid_rust() + "\n" + self.valid_rust())

        self.assertEqual(result.status, "fail")

        self.assert_layout_failure(result, "rust_wrong_struct_definition_count", "rust.HeartbeatPayload")

    def test_failure_diagnostic_names_layout_field(self):
        result = self.validate_layout(
            odin=self.valid_odin().replace("\tstatus_bits: u32,\n", "")
        )

        self.assertEqual(result.status, "fail")

        self.assert_layout_failure(result, "odin_missing_field", "odin.status_bits")

    def validate_layout(
        self,
        *,
        header: str | None = None,
        rust: str | None = None,
        odin: str | None = None,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = self.write_layout_sources(
                Path(temporary_directory),
                header or self.valid_header(),
                rust or self.valid_rust(),
                odin or self.valid_odin(),
            )
            original_paths = self.capture_layout_paths()
            self.install_layout_paths(paths)
            try:
                return LayoutParityValidator().validate({})
            finally:
                self.restore_layout_paths(original_paths)

    def write_layout_sources(
        self,
        root: Path,
        header: str,
        rust: str,
        odin: str,
    ) -> dict[str, Path]:
        paths = {
            "header": root / "kozo_abi.h",
            "rust": root / "kozo_abi.rs",
            "odin": root / "kozo_abi.odin",
        }
        paths["header"].write_text(header)
        paths["rust"].write_text(rust)
        paths["odin"].write_text(odin)
        return paths

    def capture_layout_paths(self) -> dict[str, Path]:
        return {
            "header": layout_parity._HEADER_PATH,
            "rust": layout_parity._RUST_BINDINGS,
            "odin": layout_parity._ODIN_BINDINGS,
        }

    def install_layout_paths(self, paths: dict[str, Path]) -> None:
        layout_parity._HEADER_PATH = paths["header"]
        layout_parity._RUST_BINDINGS = paths["rust"]
        layout_parity._ODIN_BINDINGS = paths["odin"]

    def restore_layout_paths(self, paths: dict[str, Path]) -> None:
        layout_parity._HEADER_PATH = paths["header"]
        layout_parity._RUST_BINDINGS = paths["rust"]
        layout_parity._ODIN_BINDINGS = paths["odin"]

    def assert_layout_failure(self, result, reason: str, layout_field: str) -> None:
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, LAYOUT_PARITY_MISMATCH)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["layout_field"], layout_field)

    def valid_header(self) -> str:
        return (
            "typedef struct k_heartbeat_payload_t {\n"
            "\tuint64_t sequence;\n"
            "\tuint64_t timestamp;\n"
            "\tuint32_t status_bits;\n"
            "} k_heartbeat_payload_t;\n"
        )

    def valid_rust(self) -> str:
        return (
            "#[repr(C)]\n"
            "pub struct HeartbeatPayload {\n"
            "    pub sequence: u64,\n"
            "    pub timestamp: u64,\n"
            "    pub status_bits: u32,\n"
            "}\n"
        )

    def valid_odin(self) -> str:
        return (
            "Heartbeat_Payload :: struct #align(8) {\n"
            "\tsequence: u64,\n"
            "\ttimestamp: u64,\n"
            "\tstatus_bits: u32,\n"
            "}\n"
        )


if __name__ == "__main__":
    unittest.main()
