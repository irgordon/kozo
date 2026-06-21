from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, RUNTIME_HALT_CONTRACT_INVALID
from harness import runtime_halt_contract as contract_module
from harness.validators_impl import runtime_halt_contract as validator_module
from harness.validators_impl.runtime_halt_contract import RuntimeHaltContractValidator

KOZO_NEGATIVE_COVERAGE = {
    "runtime_halt_contract": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_contract_schema_is_violated",
        "missing_marker": "test_fails_when_marker_write_is_missing",
        "marker_after_halt": "test_fails_when_marker_is_after_halt_loop",
        "missing_halt_instruction": "test_fails_when_hlt_instruction_is_missing",
        "missing_loop_back_edge": "test_fails_when_loop_back_edge_is_missing",
        "fallthrough_allowed": "test_fails_when_fallthrough_instruction_exists",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class RuntimeHaltContractValidatorTests(unittest.TestCase):
    def test_passes_when_runtime_halt_contract_matches_boot_source(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_contract_is_missing(self):
        self.assertEqual("runtime_halt_contract", RuntimeHaltContractValidator.name)
        result = self.validate_fixture(remove_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_halt_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        self.assertEqual("runtime_halt_contract", RuntimeHaltContractValidator.name)
        result = self.validate_fixture(mutate_contract_text=lambda _: "{not json")

        self.assertEqual(result.status, "fail")
        self.assert_halt_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_violated(self):
        self.assertEqual("runtime_halt_contract", RuntimeHaltContractValidator.name)
        result = self.validate_fixture(mutate_contract=lambda contract: contract | {"version": 1})

        self.assertEqual(result.status, "fail")
        self.assert_halt_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_marker_write_is_missing(self):
        self.assertEqual("runtime_halt_contract", RuntimeHaltContractValidator.name)
        result = self.validate_fixture(
            mutate_source=lambda source: source.replace(
                "    WRITE_COM1_MARKER boot_smoke_marker, boot_smoke_marker_end\n",
                "",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_halt_failure(result, "missing_marker", "final_smoke_marker.write_macro")

    def test_fails_when_marker_is_after_halt_loop(self):
        self.assertEqual("runtime_halt_contract", RuntimeHaltContractValidator.name)
        result = self.validate_fixture(mutate_source=lambda _: source_with_marker_after_halt())

        self.assertEqual(result.status, "fail")
        self.assert_halt_failure(result, "marker_after_halt", "final_smoke_marker.write_macro")

    def test_fails_when_hlt_instruction_is_missing(self):
        self.assertEqual("runtime_halt_contract", RuntimeHaltContractValidator.name)
        result = self.validate_fixture(mutate_source=lambda source: source.replace("    hlt\n", "    pause\n"))

        self.assertEqual(result.status, "fail")
        self.assert_halt_failure(result, "missing_halt_instruction", "terminal_behavior.instructions.hlt")

    def test_fails_when_loop_back_edge_is_missing(self):
        self.assertEqual("runtime_halt_contract", RuntimeHaltContractValidator.name)
        result = self.validate_fixture(mutate_source=lambda source: source.replace("    jmp .halt\n", "    ret\n"))

        self.assertEqual(result.status, "fail")
        self.assert_halt_failure(result, "missing_loop_back_edge", "terminal_behavior.instructions.jmp")

    def test_fails_when_fallthrough_instruction_exists(self):
        self.assertEqual("runtime_halt_contract", RuntimeHaltContractValidator.name)
        result = self.validate_fixture(mutate_source=lambda source: source + "    nop\n")

        self.assertEqual(result.status, "fail")
        self.assert_halt_failure(result, "fallthrough_allowed", "terminal_behavior.fallthrough_forbidden")

    def test_fails_when_non_goal_is_missing(self):
        self.assertEqual("runtime_halt_contract", RuntimeHaltContractValidator.name)
        result = self.validate_fixture(
            mutate_contract=lambda contract: contract | {
                "non_goals": [
                    value for value in contract["non_goals"]
                    if value != "interrupt handling"
                ]
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_halt_failure(result, "missing_non_goal", "non_goals.interrupt handling")

    def test_failure_diagnostic_names_field(self):
        self.assertEqual("runtime_halt_contract", RuntimeHaltContractValidator.name)
        result = self.validate_fixture(mutate_contract=lambda contract: contract | {"architecture": "aarch64"})

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_HALT_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], "wrong_architecture")
        self.assertEqual(result.meta["contract_field"], "architecture")

    def validate_fixture(
        self,
        *,
        remove_contract: bool = False,
        mutate_contract=None,
        mutate_contract_text=None,
        mutate_source=None,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture_files(root)
            if remove_contract:
                paths["contract"].unlink()
            elif mutate_contract_text is not None:
                paths["contract"].write_text(mutate_contract_text(paths["contract"].read_text()))
            elif mutate_contract is not None:
                contract = json.loads(paths["contract"].read_text())
                paths["contract"].write_text(json.dumps(mutate_contract(contract), indent=2) + "\n")
            if mutate_source is not None:
                paths["source"].write_text(mutate_source(paths["source"].read_text()))

            old_paths = patch_validator_paths(root, paths["contract"])
            try:
                return RuntimeHaltContractValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_halt_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_HALT_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> dict[str, Path]:
    contract_path = root / "contracts" / "runtime_halt_contract.v0.json"
    source_path = root / "kernel" / "arch" / "x86_64" / "boot.asm"
    contract_path.parent.mkdir(parents=True)
    source_path.parent.mkdir(parents=True)
    contract_path.write_text(json.dumps(valid_contract(), indent=2) + "\n")
    source_path.write_text(valid_source())
    return {
        "contract": contract_path,
        "source": source_path,
    }


def valid_contract() -> dict[str, object]:
    return {
        "version": 0,
        "architecture": "x86_64",
        "source": {
            "path": "kernel/arch/x86_64/boot.asm",
            "entry_symbol": "_start",
        },
        "final_smoke_marker": {
            "symbol": "boot_smoke_marker",
            "text": "KOZO_BOOT_SMOKE_OK",
            "write_macro": "WRITE_COM1_MARKER",
        },
        "terminal_behavior": {
            "kind": "halt_loop",
            "label": ".halt",
            "disable_interrupts": True,
            "instructions": [
                "cli",
                "hlt",
                "jmp .halt",
            ],
            "fallthrough_forbidden": True,
        },
        "non_goals": [
            "hardware trap execution",
            "interrupt handling",
            "scheduler behavior",
            "userspace execution",
            "process model behavior",
            "VFS behavior",
            "file descriptor behavior",
            "production readiness",
        ],
    }


def valid_source() -> str:
    return "\n".join(
        (
            "global _start",
            "section .rodata",
            "boot_smoke_marker:",
            "    db \"KOZO_BOOT_SMOKE_OK\", 13, 10",
            "boot_smoke_marker_end:",
            "section .text",
            "_start:",
            "    WRITE_COM1_MARKER early_entry_marker, early_entry_marker_end",
            "    WRITE_COM1_MARKER boot_smoke_marker, boot_smoke_marker_end",
            "    cli",
            ".halt:",
            "    hlt",
            "    jmp .halt",
            "",
        )
    )


def source_with_marker_after_halt() -> str:
    return "\n".join(
        (
            "global _start",
            "section .rodata",
            "boot_smoke_marker:",
            "    db \"KOZO_BOOT_SMOKE_OK\", 13, 10",
            "boot_smoke_marker_end:",
            "section .text",
            "_start:",
            "    cli",
            ".halt:",
            "    hlt",
            "    jmp .halt",
            "    WRITE_COM1_MARKER boot_smoke_marker, boot_smoke_marker_end",
            "",
        )
    )


def patch_validator_paths(root: Path, contract_path: Path):
    old_paths = (
        validator_module._CONTRACT_PATH,
        contract_module.ROOT,
    )
    validator_module._CONTRACT_PATH = contract_path
    contract_module.ROOT = root
    return old_paths


def restore_validator_paths(old_paths) -> None:
    validator_module._CONTRACT_PATH, contract_module.ROOT = old_paths


if __name__ == "__main__":
    unittest.main()
