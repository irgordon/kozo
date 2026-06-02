from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, SYSCALL_CATALOG_INVALID
from harness.validators_impl import syscall_catalog
from harness.validators_impl.syscall_catalog import SyscallCatalogValidator

KOZO_NEGATIVE_COVERAGE = {
    "syscall_catalog": {
        "missing_catalog_file": "test_fails_when_catalog_file_is_missing",
        "invalid_json": "test_fails_when_catalog_json_is_invalid",
        "schema_violation": "test_fails_when_catalog_schema_is_invalid",
        "missing_table_entry": "test_fails_when_catalog_is_missing_table_entry",
        "unknown_catalog_syscall": "test_fails_when_catalog_includes_unknown_syscall",
        "constant_mismatch": "test_fails_when_catalog_constant_mismatches_table",
        "numeric_id_mismatch": "test_fails_when_catalog_numeric_id_mismatches_manifest",
        "kind_mismatch": "test_fails_when_catalog_kind_mismatches_table",
        "class_mismatch": "test_fails_when_catalog_class_mismatches_table",
        "payload_behavior_mismatch": "test_fails_when_catalog_payload_behavior_mismatches_contracts",
        "return_status_mismatch": "test_fails_when_catalog_return_status_mismatches_table",
        "mutation_behavior_mismatch": "test_fails_when_catalog_mutation_behavior_mismatches_table",
        "branch_selector_mismatch": "test_fails_when_catalog_branch_selector_mismatches_table",
        "unknown_proof_validator": "test_fails_when_catalog_references_unknown_proof_validator",
        "missing_required_class_proof": "test_fails_when_catalog_omits_required_class_proof",
        "runtime_probe_true_but_missing": "test_fails_when_runtime_probe_is_true_but_source_probe_is_missing",
        "runtime_probe_false_but_present": "test_fails_when_runtime_probe_is_false_but_source_probe_exists",
        "diagnostic_names_catalog_field": "test_failure_diagnostic_names_catalog_field",
    }
}


class SyscallCatalogValidatorTests(unittest.TestCase):
    def test_passes_when_catalog_summarizes_governed_syscalls(self):
        result = self.validate_syscall_catalog()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_catalog_file_is_missing(self):
        result = self.validate_syscall_catalog(remove_catalog=True)

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "missing_catalog_file", "catalog")

    def test_fails_when_catalog_json_is_invalid(self):
        result = self.validate_syscall_catalog(catalog_text="{")

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "invalid_catalog_json", "catalog")

    def test_fails_when_catalog_schema_is_invalid(self):
        result = self.validate_syscall_catalog(catalog={"version": 0})

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "catalog_schema_violation", "catalog")

    def test_fails_when_catalog_is_missing_table_entry(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: catalog["syscalls"].pop("status")
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "missing_table_entry", "syscalls.status")

    def test_fails_when_catalog_includes_unknown_syscall(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: self.add_unknown_syscall(catalog)
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "unknown_catalog_syscall", "syscalls.future")

    def test_fails_when_catalog_constant_mismatches_table(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: self.set_value(
                catalog,
                ("syscalls", "status", "constant"),
                "K_SYSCALL_NOP",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "constant_mismatch", "syscalls.status.constant")

    def test_fails_when_catalog_numeric_id_mismatches_manifest(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: self.set_value(
                catalog,
                ("syscalls", "status", "numeric_id"),
                99,
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "numeric_id_mismatch", "syscalls.status.numeric_id")

    def test_fails_when_catalog_kind_mismatches_table(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: self.set_value(
                catalog,
                ("syscalls", "status", "kind"),
                "payload",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "kind_mismatch", "syscalls.status.kind")

    def test_fails_when_catalog_class_mismatches_table(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: self.set_value(
                catalog,
                ("syscalls", "status", "class"),
                "payload_mutating_status",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "class_mismatch", "syscalls.status.class")

    def test_fails_when_catalog_payload_behavior_mismatches_contracts(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: self.set_value(
                catalog,
                ("syscalls", "debug_heartbeat", "payload_behavior", "layout"),
                None,
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "payload_behavior_mismatch", "syscalls.debug_heartbeat.payload_behavior")

    def test_fails_when_catalog_return_status_mismatches_table(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: self.set_value(
                catalog,
                ("syscalls", "status", "return_status"),
                "K_INVALID",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "return_status_mismatch", "syscalls.status.return_status")

    def test_fails_when_catalog_mutation_behavior_mismatches_table(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: self.set_value(
                catalog,
                ("syscalls", "debug_heartbeat", "mutation_behavior", "fields"),
                ["sequence"],
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "mutation_behavior_mismatch", "syscalls.debug_heartbeat.mutation_behavior")

    def test_fails_when_catalog_branch_selector_mismatches_table(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: self.set_value(
                catalog,
                ("syscalls", "status", "source_branch_selector"),
                "abi.K_SYSCALL_NOP",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "branch_selector_mismatch", "syscalls.status.source_branch_selector")

    def test_fails_when_catalog_references_unknown_proof_validator(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: catalog["syscalls"]["status"]["proof_validators"].append("future_validator")
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "unknown_proof_validator", "syscalls.status.proof_validators")

    def test_fails_when_catalog_omits_required_class_proof(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: catalog["syscalls"]["debug_heartbeat"]["proof_validators"].remove("return_path_proof")
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "missing_required_class_proof", "syscalls.debug_heartbeat.proof_validators")

    def test_fails_when_runtime_probe_is_true_but_source_probe_is_missing(self):
        result = self.validate_syscall_catalog(
            mutate_rust_source=lambda source: source.replace(
                "pub fn status_request() -> abi::K_STATUS {",
                "pub fn status_request_disabled() -> abi::K_STATUS {",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "runtime_probe_true_but_missing", "syscalls.status.runtime_probe_present")

    def test_fails_when_runtime_probe_is_false_but_source_probe_exists(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: self.set_value(
                catalog,
                ("syscalls", "status", "runtime_probe_present"),
                False,
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_catalog_failure(result, "runtime_probe_false_but_present", "syscalls.status.runtime_probe_present")

    def test_failure_diagnostic_names_catalog_field(self):
        result = self.validate_syscall_catalog(
            mutate_catalog=lambda catalog: self.set_value(
                catalog,
                ("syscalls", "status", "numeric_id"),
                99,
            )
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, SYSCALL_CATALOG_INVALID)
        self.assertEqual(result.meta["reason"], "numeric_id_mismatch")
        self.assertEqual(result.meta["catalog_field"], "syscalls.status.numeric_id")

    def validate_syscall_catalog(
        self,
        mutate_catalog=None,
        mutate_table=None,
        mutate_class=None,
        mutate_manifest=None,
        mutate_rust_source=None,
        catalog=None,
        catalog_text=None,
        remove_catalog=False,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_fixture(
                root,
                mutate_catalog,
                mutate_table,
                mutate_class,
                mutate_manifest,
                mutate_rust_source,
                catalog,
                catalog_text,
                remove_catalog,
            )
            original_paths = self.patch_validator_paths(paths)
            try:
                return SyscallCatalogValidator().validate({})
            finally:
                self.restore_validator_paths(original_paths)

    def write_fixture(
        self,
        root: Path,
        mutate_catalog,
        mutate_table,
        mutate_class,
        mutate_manifest,
        mutate_rust_source,
        catalog,
        catalog_text,
        remove_catalog,
    ) -> dict[str, Path]:
        paths = self.fixture_paths(root)
        catalog_data = self.catalog()
        table_data = self.table_contract()
        class_data = self.class_contract()
        manifest_data = self.abi_manifest()
        rust_source = self.rust_source()
        if catalog is not None:
            catalog_data = catalog
        if mutate_catalog is not None:
            mutate_catalog(catalog_data)
        if mutate_table is not None:
            mutate_table(table_data)
        if mutate_class is not None:
            mutate_class(class_data)
        if mutate_manifest is not None:
            mutate_manifest(manifest_data)
        if mutate_rust_source is not None:
            rust_source = mutate_rust_source(rust_source)
        self.write_json_or_text(paths["catalog"], catalog_data, catalog_text, remove_catalog)
        paths["table"].write_text(json.dumps(table_data))
        paths["class"].write_text(json.dumps(class_data))
        paths["manifest"].write_text(json.dumps(manifest_data))
        paths["rust_source"].write_text(rust_source)
        return paths

    def fixture_paths(self, root: Path) -> dict[str, Path]:
        return {
            "catalog": root / "syscall_catalog.v0.json",
            "table": root / "syscall_table_contract.v0.json",
            "class": root / "syscall_class_contract.v0.json",
            "manifest": root / "kozo_abi_manifest.json",
            "rust_source": root / "main.rs",
        }

    def patch_validator_paths(self, paths: dict[str, Path]) -> dict[str, Path]:
        original = {
            "catalog": syscall_catalog._CATALOG_PATH,
            "table": syscall_catalog._TABLE_CONTRACT_PATH,
            "class": syscall_catalog._CLASS_CONTRACT_PATH,
            "manifest": syscall_catalog._ABI_MANIFEST_PATH,
            "rust_source": syscall_catalog._RUST_SERVICE_PATH,
        }
        syscall_catalog._CATALOG_PATH = paths["catalog"]
        syscall_catalog._TABLE_CONTRACT_PATH = paths["table"]
        syscall_catalog._CLASS_CONTRACT_PATH = paths["class"]
        syscall_catalog._ABI_MANIFEST_PATH = paths["manifest"]
        syscall_catalog._RUST_SERVICE_PATH = paths["rust_source"]
        return original

    def restore_validator_paths(self, paths: dict[str, Path]) -> None:
        syscall_catalog._CATALOG_PATH = paths["catalog"]
        syscall_catalog._TABLE_CONTRACT_PATH = paths["table"]
        syscall_catalog._CLASS_CONTRACT_PATH = paths["class"]
        syscall_catalog._ABI_MANIFEST_PATH = paths["manifest"]
        syscall_catalog._RUST_SERVICE_PATH = paths["rust_source"]

    def write_json_or_text(self, path: Path, data: dict, text: str | None, remove: bool) -> None:
        if remove:
            return
        if text is not None:
            path.write_text(text)
            return
        path.write_text(json.dumps(data))

    def catalog(self) -> dict:
        return copy.deepcopy(json.loads((Path(__file__).resolve().parents[1] / "contracts" / "syscall_catalog.v0.json").read_text()))

    def table_contract(self) -> dict:
        return copy.deepcopy(json.loads((Path(__file__).resolve().parents[1] / "contracts" / "syscall_table_contract.v0.json").read_text()))

    def class_contract(self) -> dict:
        return copy.deepcopy(json.loads((Path(__file__).resolve().parents[1] / "contracts" / "syscall_class_contract.v0.json").read_text()))

    def abi_manifest(self) -> dict:
        return copy.deepcopy(json.loads((Path(__file__).resolve().parents[1] / "contracts" / "kozo_abi_manifest.json").read_text()))

    def rust_source(self) -> str:
        return (Path(__file__).resolve().parents[1] / "userspace" / "core_service" / "src" / "main.rs").read_text()

    def add_unknown_syscall(self, catalog: dict) -> None:
        future = copy.deepcopy(catalog["syscalls"]["status"])
        future["name"] = "future"
        catalog["syscalls"]["future"] = future

    def set_value(self, data: dict, path: tuple[str, ...], value) -> None:
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    def assert_catalog_failure(self, result, reason: str, catalog_field: str) -> None:
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, SYSCALL_CATALOG_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["catalog_field"], catalog_field)


if __name__ == "__main__":
    unittest.main()
