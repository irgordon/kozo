from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, STACK_INITIALIZATION_EVIDENCE_INVALID
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validators_impl import stack_initialization_evidence as validator_module
from harness.validators_impl.stack_initialization_evidence import StackInitializationEvidenceValidator

KOZO_NEGATIVE_COVERAGE = {
    "stack_initialization_evidence": {
        "missing_marker": "test_fails_when_stack_marker_is_missing",
        "marker_order_mismatch": "test_fails_when_stack_marker_precedes_boot_marker",
        "contract_mismatch": "test_fails_when_contract_expected_marker_mismatches",
        "missing_stack_pointer_setup": "test_fails_when_stack_pointer_setup_is_missing",
        "missing_stack_use": "test_fails_when_stack_use_probe_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class StackInitializationEvidenceValidatorTests(unittest.TestCase):
    def test_passes_when_stack_marker_source_and_evidence_match(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_stack_marker_is_missing(self):
        result = self.validate_fixture(
            mutate_boot=lambda source: source.replace("stack_init_marker:\n", ""),
        )

        self.assertEqual(result.status, "fail")
        self.assert_stack_failure(result, "missing_marker", "kernel.boot.asm.stack_init_marker")

    def test_fails_when_stack_marker_precedes_boot_marker(self):
        markers = list(smoke_markers())
        markers[3], markers[4] = markers[4], markers[3]
        result = self.validate_fixture(
            mutate_serial=lambda _: "\n".join(markers) + "\n",
            mutate_metadata=lambda metadata: metadata | {"observed_markers": markers},
        )

        self.assertEqual(result.status, "fail")
        self.assert_stack_failure(result, "marker_order_mismatch", "qemu_smoke.observed_markers")

    def test_fails_when_contract_expected_marker_mismatches(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "stack_definition": contract["stack_definition"] | {"reserved_marker": "KOZO_WRONG_STACK_MARKER"}
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_stack_failure(result, "contract_mismatch", "stack_definition.reserved_marker")

    def test_fails_when_stack_pointer_setup_is_missing(self):
        result = self.validate_fixture(mutate_boot=lambda source: source.replace("    lea rsp, [rel boot_stack_top]\n", ""))

        self.assertEqual(result.status, "fail")
        self.assert_stack_failure(result, "missing_stack_pointer_setup", "stack_definition.stack_pointer_register")

    def test_fails_when_stack_use_probe_is_missing(self):
        result = self.validate_fixture(mutate_boot=lambda source: source.replace("    push rax\n", ""))

        self.assertEqual(result.status, "fail")
        self.assert_stack_failure(result, "missing_stack_use", "stack_definition.stack_pointer_register")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "stack_definition": contract["stack_definition"] | {"marker_emitted": False}
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_stack_failure(result, "contract_mismatch", "stack_definition.marker_emitted")
        self.assertEqual(result.code, STACK_INITIALIZATION_EVIDENCE_INVALID)

    def validate_fixture(
        self,
        *,
        mutate_contract=None,
        mutate_boot=None,
        mutate_metadata=None,
        mutate_serial=None,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture_files(root)
            if mutate_contract is not None:
                contract = json.loads(paths["contract"].read_text())
                paths["contract"].write_text(json.dumps(mutate_contract(contract), indent=2) + "\n")
            if mutate_boot is not None:
                paths["boot"].write_text(mutate_boot(paths["boot"].read_text()))
            if mutate_metadata is not None:
                metadata = json.loads(paths["metadata"].read_text())
                paths["metadata"].write_text(json.dumps(mutate_metadata(metadata), indent=2) + "\n")
            if mutate_serial is not None:
                paths["serial"].write_text(mutate_serial(paths["serial"].read_text()))

            old_paths = patch_validator_paths(paths)
            try:
                return StackInitializationEvidenceValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_stack_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, STACK_INITIALIZATION_EVIDENCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> dict[str, Path]:
    paths = {
        "contract": root / "contracts" / "stack_initialization_evidence_contract.v0.json",
        "boot": root / "kernel" / "arch" / "x86_64" / "boot.asm",
        "metadata": root / "artifacts" / "runtime" / "qemu_smoke.metadata.json",
        "serial": root / "artifacts" / "runtime" / "qemu_smoke.log",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    paths["contract"].write_text(json.dumps(valid_contract(), indent=2) + "\n")
    paths["boot"].write_text(valid_boot_source())
    paths["metadata"].write_text(json.dumps(valid_metadata(), indent=2) + "\n")
    paths["serial"].write_text(valid_serial_log())
    return paths


def valid_contract() -> dict[str, object]:
    return {
        "version": 0,
        "architecture": "x86_64",
        "current_state": {
            "runtime_path": "boot_smoke_to_halt",
            "halt_contract": "contracts/runtime_halt_contract.v0.json",
            "progression_stages_contract": "contracts/runtime_progression_stages.v0.json",
            "stage": "STACK_INITIALIZATION_EVIDENCE",
            "implemented": True,
        },
        "stack_definition": {
            "description": "Stack initialization means runtime code has selected and proven a controlled stack region.",
            "reserved_marker": "KOZO_STACK_INIT_OK",
            "marker_status": "emitted",
            "marker_emitted": True,
            "source_file": "kernel/arch/x86_64/boot.asm",
            "stack_symbol": "boot_stack",
            "stack_top_symbol": "boot_stack_top",
            "stack_size_bytes": 16384,
            "stack_pointer_register": "rsp",
        },
        "prerequisites": ["QEMU serial smoke evidence"],
        "evidence_requirements": ["KOZO_STACK_INIT_OK marker captured from runtime code"],
        "proof_boundary": ["evidence must come from runtime code, not scripts"],
        "assumptions_enabled": ["safe call instruction usage after the proven stack marker"],
        "assumptions_not_enabled": ["memory initialization"],
        "future_validators": ["stack_initialization_evidence"],
        "non_goals": ["memory initialization", "production readiness"],
    }


def valid_boot_source() -> str:
    return "\n".join(
        (
            "boot_stack:",
            "    resb 16384",
            "boot_stack_top:",
            "boot_smoke_marker:",
            "stack_init_marker:",
            "    WRITE_COM1_MARKER boot_smoke_marker, boot_smoke_marker_end",
            "    lea rsp, [rel boot_stack_top]",
            "    push rax",
            "    pop rax",
            "    WRITE_COM1_MARKER stack_init_marker, stack_init_marker_end",
            ".halt:",
        )
    )


def valid_metadata() -> dict[str, object]:
    return {
        "outcome": "pass",
        "expected_marker": get_expected_smoke_marker(),
        "observed_markers": list(smoke_markers()),
    }


def valid_serial_log() -> str:
    return "\n".join(smoke_markers()) + "\n"


def smoke_markers() -> tuple[str, ...]:
    return get_smoke_marker_order()


def patch_validator_paths(paths: dict[str, Path]):
    old_paths = (
        validator_module._CONTRACT_PATH,
        validator_module._BOOT_ASM_PATH,
        validator_module._METADATA_PATH,
        validator_module._SERIAL_LOG_PATH,
    )
    validator_module._CONTRACT_PATH = paths["contract"]
    validator_module._BOOT_ASM_PATH = paths["boot"]
    validator_module._METADATA_PATH = paths["metadata"]
    validator_module._SERIAL_LOG_PATH = paths["serial"]
    return old_paths


def restore_validator_paths(old_paths):
    (
        validator_module._CONTRACT_PATH,
        validator_module._BOOT_ASM_PATH,
        validator_module._METADATA_PATH,
        validator_module._SERIAL_LOG_PATH,
    ) = old_paths


if __name__ == "__main__":
    unittest.main()
