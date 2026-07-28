from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import FIXED_USER_RUNTIME_STATUS_SERVICE_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.validators_impl import fixed_user_runtime_status_service_evidence as validator_module
from harness.validators_impl.fixed_user_runtime_status_service_evidence import (
    FixedUserRuntimeStatusServiceEvidenceValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "fixed_user_runtime_status_service_evidence": {
        "boot_executes_transaction": "test_fails_when_boot_calls_transaction",
        "boot_preparation_invalid": "test_fails_when_boot_skips_privilege_preparation",
        "runtime_order_invalid": "test_fails_when_transaction_is_not_post_loop",
        "shared_status_missing": "test_fails_when_shared_snapshot_is_missing",
        "pre_runtime_status_substitute": "test_fails_when_collector_skips_loop_state",
        "internal_status_source_diverged": "test_fails_when_internal_builder_diverges",
        "bridge_order_invalid": "test_fails_when_bridge_alignment_is_missing",
        "odin_return_invalid": "test_fails_when_odin_return_marker_is_missing",
        "response_geometry_invalid": "test_fails_when_response_size_changes",
        "service_order_invalid": "test_fails_when_service_success_precedes_validation",
        "partial_ring3_validation": "test_fails_when_ring3_field_check_is_missing",
        "response_digest_invalid": "test_fails_when_digest_omits_final_qword",
        "capability_after_failed_transaction": "test_fails_when_failure_can_reach_capability",
        "failure_emits_success": "test_fails_when_failure_emits_service_success",
        "missing_elf_evidence": "test_fails_when_elf_record_is_missing",
        "missing_elf_symbol": "test_fails_when_snapshot_symbol_is_missing",
        "snapshot_elf_geometry_invalid": "test_fails_when_snapshot_size_is_wrong",
        "elf_call_order_invalid": "test_fails_when_elf_call_order_is_wrong",
        "elf_response_stores_missing": "test_fails_when_elf_response_store_is_missing",
        "elf_response_comparisons_missing": "test_fails_when_elf_response_comparison_is_missing",
        "elf_digest_incomplete": "test_fails_when_elf_digest_is_incomplete",
        "runtime_outcome_invalid": "test_fails_when_qemu_is_blocked",
        "metadata_log_mismatch": "test_fails_when_metadata_is_stale",
        "runtime_marker_missing": "test_fails_when_serial_marker_is_missing",
        "runtime_marker_duplicate": "test_fails_when_serial_marker_is_duplicated",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class FixedUserRuntimeStatusServiceEvidenceTests(unittest.TestCase):
    def test_valid_evidence_passes(self):
        result = self.validate_fixture()
        self.assertEqual((result.status, result.code), ("pass", OK))

    def test_fails_when_boot_calls_transaction(self):
        result = self.validate_fixture(
            boot=lambda text: text.replace(
                "    call initialize_privilege_transition\n",
                "    call execute_fixed_user_runtime_status_transaction\n"
                "    call initialize_privilege_transition\n",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "boot_executes_transaction")

    def test_fails_when_boot_skips_privilege_preparation(self):
        result = self.validate_fixture(
            boot=lambda text: text.replace(
                "    call initialize_privilege_transition\n",
                "",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "boot_preparation_invalid")

    def test_fails_when_transaction_is_not_post_loop(self):
        result = self.validate_fixture(
            runtime=lambda text: text.replace(
                "transaction_status := execute_fixed_user_runtime_status_transaction()",
                "transaction_status := RUNTIME_PROGRESSION_OK",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "runtime_order_invalid")

    def test_fails_when_shared_snapshot_is_missing(self):
        result = self.validate_fixture(
            capability=lambda text: text.replace(
                "runtime_status_snapshot: Runtime_Status_Snapshot",
                "other_snapshot: Runtime_Status_Snapshot",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "shared_status_missing")

    def test_fails_when_collector_skips_loop_state(self):
        result = self.validate_fixture(
            capability=lambda text: text.replace(
                "if !controlled_runtime_loop_state_is_complete() {",
                "if false {",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "pre_runtime_status_substitute")

    def test_fails_when_internal_builder_diverges(self):
        result = self.validate_fixture(
            capability=lambda text: text.replace(
                "build_internal_runtime_status_response(response)",
                "clear_runtime_status_response(response)",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "internal_status_source_diverged")

    def test_fails_when_bridge_alignment_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace("    sub rsp, 8\n", "", 1)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "bridge_order_invalid")

    def test_fails_when_odin_return_marker_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace(
                "    call runtime_serial_write_ring0_return_marker\n",
                "",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "odin_return_invalid")

    def test_fails_when_response_size_changes(self):
        result = self.validate_fixture(
            layout=lambda text: text.replace(
                "%define FIXED_USER_RESPONSE_SIZE 88",
                "%define FIXED_USER_RESPONSE_SIZE 96",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "response_geometry_invalid")

    def test_fails_when_service_success_precedes_validation(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace(
                "    call validate_fixed_user_response\n",
                "",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "service_order_invalid")

    def test_fails_when_ring3_field_check_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace(
                "    cmp qword [rdi + 80], 0\n",
                "",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "partial_ring3_validation")

    def test_fails_when_digest_omits_final_qword(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace(
                "    xor rax, [rdi + 80]\n",
                "",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "response_digest_invalid")

    def test_fails_when_failure_can_reach_capability(self):
        def mutation(text):
            old = (
                "\tif transaction_status != RUNTIME_PROGRESSION_OK {\n"
                "\t\tclear_runtime_status_snapshot()\n"
                "\t\treturn transaction_status\n"
                "\t}\n"
            )
            return text.replace(old, "", 1)

        result = self.validate_fixture(runtime=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "capability_after_failed_transaction")

    def test_fails_when_failure_emits_service_success(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace(
                "privilege_return_failure:\n",
                "privilege_return_failure:\n"
                "    call runtime_serial_write_user_runtime_status_service_ok_marker\n",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "failure_emits_success")

    def test_fails_when_elf_record_is_missing(self):
        def mutation(report):
            del report["fixed_user_runtime_status_service"]
            return report

        result = self.validate_fixture(report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_elf_evidence")

    def test_fails_when_snapshot_symbol_is_missing(self):
        def mutation(report):
            report["fixed_user_runtime_status_service"]["symbols"][
                "runtime_status_snapshot"
            ]["present"] = False
            return report

        result = self.validate_fixture(report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_elf_symbol")

    def test_fails_when_snapshot_size_is_wrong(self):
        def mutation(report):
            report["fixed_user_runtime_status_service"]["snapshot"]["size_bytes"] = 56
            return report

        result = self.validate_fixture(report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "snapshot_elf_geometry_invalid")

    def test_fails_when_elf_call_order_is_wrong(self):
        def mutation(report):
            report["fixed_user_runtime_status_service"][
                "status_boundary_call_order_valid"
            ] = False
            return report

        result = self.validate_fixture(report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "elf_call_order_invalid")

    def test_fails_when_elf_response_store_is_missing(self):
        def mutation(report):
            report["fixed_user_runtime_status_service"][
                "response_builder_store_count"
            ] = 10
            return report

        result = self.validate_fixture(report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "elf_response_stores_missing")

    def test_fails_when_elf_response_comparison_is_missing(self):
        def mutation(report):
            report["fixed_user_runtime_status_service"][
                "ring3_response_compare_count"
            ] = 13
            return report

        result = self.validate_fixture(report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "elf_response_comparisons_missing")

    def test_fails_when_elf_digest_is_incomplete(self):
        def mutation(report):
            report["fixed_user_runtime_status_service"]["digest_xor_count"] = 9
            return report

        result = self.validate_fixture(report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "elf_digest_incomplete")

    def test_fails_when_qemu_is_blocked(self):
        result = self.validate_fixture(
            metadata=lambda value: value | {"outcome": "blocked"}
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "runtime_outcome_invalid")

    def test_fails_when_metadata_is_stale(self):
        def mutation(value):
            value["observed_markers"] = value["observed_markers"][:-1]
            return value

        result = self.validate_fixture(metadata=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "metadata_log_mismatch")

    def test_fails_when_serial_marker_is_missing(self):
        result = self.validate_fixture(
            serial=lambda text: text.replace(
                "KOZO_USER_RUNTIME_STATUS_SERVICE_OK\n",
                "",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "runtime_marker_missing")

    def test_fails_when_serial_marker_is_duplicated(self):
        result = self.validate_fixture(
            serial=lambda text: text
            + "KOZO_USER_RUNTIME_STATUS_SERVICE_ENTER\n"
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "runtime_marker_duplicate")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(
            layout=lambda text: text.replace(
                "%define FIXED_USER_RESPONSE_SIZE 88",
                "%define FIXED_USER_RESPONSE_SIZE 96",
                1,
            )
        )
        self.assertEqual(
            result.code,
            FIXED_USER_RUNTIME_STATUS_SERVICE_EVIDENCE_INVALID,
        )
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(
        self,
        *,
        boot=None,
        privilege=None,
        layout=None,
        runtime=None,
        capability=None,
        report=None,
        metadata=None,
        serial=None,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.fixture_paths(root)
            text_sources = {
                "contract": validator_module._CONTRACT_PATH,
                "boot": validator_module._BOOT_PATH,
                "privilege": validator_module._PRIVILEGE_PATH,
                "layout": validator_module._LAYOUT_PATH,
                "runtime": validator_module._RUNTIME_PATH,
                "capability": validator_module._CAPABILITY_PATH,
            }
            mutations = {
                "boot": boot,
                "privilege": privilege,
                "layout": layout,
                "runtime": runtime,
                "capability": capability,
            }
            for name, source in text_sources.items():
                text = source.read_text()
                mutate = mutations.get(name)
                paths[name].write_text(mutate(text) if mutate else text)
            self.write_json_fixture(
                paths["report"],
                validator_module._ELF_REPORT_PATH,
                report,
            )
            self.write_json_fixture(
                paths["metadata"],
                validator_module._METADATA_PATH,
                metadata,
            )
            markers = "\n".join(get_smoke_marker_order()) + "\n"
            paths["serial"].write_text(serial(markers) if serial else markers)
            original = self.patch_paths(paths)
            try:
                return FixedUserRuntimeStatusServiceEvidenceValidator().validate({})
            finally:
                self.restore_paths(original)

    def fixture_paths(self, root):
        return {
            "contract": root / "contract.json",
            "boot": root / "boot.asm",
            "privilege": root / "privilege.asm",
            "layout": root / "layout.inc",
            "runtime": root / "runtime_progression.odin",
            "capability": root / "runtime_capability.odin",
            "report": root / "kernel_elf_report.json",
            "metadata": root / "qemu_smoke.metadata.json",
            "serial": root / "qemu_smoke.log",
        }

    def write_json_fixture(self, target, source, mutate):
        value = json.loads(source.read_text())
        target.write_text(json.dumps(mutate(value) if mutate else value))

    def patch_paths(self, paths):
        mapping = {
            "_CONTRACT_PATH": paths["contract"],
            "_BOOT_PATH": paths["boot"],
            "_PRIVILEGE_PATH": paths["privilege"],
            "_LAYOUT_PATH": paths["layout"],
            "_RUNTIME_PATH": paths["runtime"],
            "_CAPABILITY_PATH": paths["capability"],
            "_ELF_REPORT_PATH": paths["report"],
            "_METADATA_PATH": paths["metadata"],
            "_SERIAL_PATH": paths["serial"],
        }
        original = {
            name: getattr(validator_module, name)
            for name in mapping
        }
        for name, path in mapping.items():
            setattr(validator_module, name, path)
        return original

    def restore_paths(self, original):
        for name, path in original.items():
            setattr(validator_module, name, path)

    def assert_failure(self, result, reason):
        self.assertEqual(result.status, "fail")
        self.assertEqual(
            result.code,
            FIXED_USER_RUNTIME_STATUS_SERVICE_EVIDENCE_INVALID,
        )
        self.assertEqual(result.meta["reason"], reason)
        self.assertIn("contract_field", result.meta)


if __name__ == "__main__":
    unittest.main()
