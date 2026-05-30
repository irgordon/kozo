from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness.codes import OK, RETURN_PATH_PROOF_INVALID
from harness.validator import BaseValidator, ValidationResult
from harness.validators_impl.runtime_trap_path import runtime_trap_path_observations

_ROOT = Path(__file__).resolve().parents[2]
_KERNEL_MAIN = _ROOT / "kernel" / "main.odin"
_RUST_MAIN = _ROOT / "userspace" / "core_service" / "src" / "main.rs"


@dataclass(frozen=True)
class RequiredAnchor:
    name: str
    needle: str
    detail: str
    source_path: Path


def _line_index(lines: list[str], needle: str) -> int:
    for index, line in enumerate(lines):
        if needle in line:
            return index
    return -1


def _rust_return_path_anchors() -> tuple[RequiredAnchor, ...]:
    return (
        RequiredAnchor(
            "rust_failure_helper",
            "fn fail_heartbeat_contract() -> !",
            "Rust must provide a heavy failure path for return-path violations",
            _RUST_MAIN,
        ),
        RequiredAnchor(
            "rust_returned_status_check",
            "if status != abi::K_OK",
            "Rust must explicitly check the returned status against abi::K_OK",
            _RUST_MAIN,
        ),
        RequiredAnchor(
            "rust_returned_sequence_check",
            "if payload.sequence != 0xCAFEFEEE",
            "Rust must validate the returned payload sequence against 0xCAFEFEEE",
            _RUST_MAIN,
        ),
        RequiredAnchor(
            "rust_returned_timestamp_check",
            "if payload.timestamp != 0xDEADBEEF",
            "Rust must validate the returned payload timestamp against 0xDEADBEEF",
            _RUST_MAIN,
        ),
        RequiredAnchor(
            "rust_returned_status_bits_check",
            "if payload.status_bits != abi::K_OK",
            "Rust must validate returned status_bits against abi::K_OK",
            _RUST_MAIN,
        ),
        RequiredAnchor(
            "rust_failure_panic",
            'panic!("heartbeat return path contract violated")',
            "Rust must make return-path violations fail closed",
            _RUST_MAIN,
        ),
        RequiredAnchor(
            "rust_failure_call",
            "fail_heartbeat_contract();",
            "Rust must call the heavy failure path when the return-path contract is violated",
            _RUST_MAIN,
        ),
    )


def _odin_return_path_anchors() -> tuple[RequiredAnchor, ...]:
    return (
        RequiredAnchor(
            "odin_returned_sequence_write",
            "payload.sequence = 0xCAFEFEEE",
            "Odin must write the returned heartbeat sequence through the payload pointer",
            _KERNEL_MAIN,
        ),
        RequiredAnchor(
            "odin_returned_timestamp_write",
            "payload.timestamp = 0xDEADBEEF",
            "Odin must update the payload timestamp through the payload pointer",
            _KERNEL_MAIN,
        ),
        RequiredAnchor(
            "odin_returned_status_bits_write",
            "payload.status_bits = u32(abi.K_OK)",
            "Odin must write successful status_bits through the payload pointer",
            _KERNEL_MAIN,
        ),
    )


def _missing_required_anchors(source: str, anchors: tuple[RequiredAnchor, ...]) -> tuple[RequiredAnchor, ...]:
    return tuple(anchor for anchor in anchors if anchor.needle not in source)


def _missing_anchor_result(anchor: RequiredAnchor) -> ValidationResult:
    return ValidationResult.fail(
        code=RETURN_PATH_PROOF_INVALID,
        detail=f"Return path proof invalid: missing {anchor.name}: {anchor.detail}",
        action="Keep the Rust and Odin sources explicit about the returned heartbeat payload contract",
        meta={"missing_anchor": anchor.name, "source_path": str(anchor.source_path)},
    )


def _validate_trap_path(rust_source: str) -> ValidationResult | None:
    trap_path = runtime_trap_path_observations(rust_source)
    if trap_path["has_local_stub"]:
        return ValidationResult.fail(
            code=RETURN_PATH_PROOF_INVALID,
            detail="Return path proof invalid: core_service still defines a local heartbeat syscall stub",
            action="Remove the local Rust stub before proving the return path",
        )
    if not trap_path["has_extern_decl"] or not trap_path["has_extern_call"]:
        return ValidationResult.fail(
            code=RETURN_PATH_PROOF_INVALID,
            detail="Return path proof invalid: core_service must declare and call extern syscall_entry before proving returned payload mutations",
            action='Keep the Rust side on the exercised extern "C" syscall_entry bridge path',
        )
    return None


def _validate_post_call_order(rust_source: str) -> ValidationResult | None:
    rust_lines = rust_source.splitlines()
    status_call_index = _line_index(rust_lines, "let status = invoke_heartbeat_bridge(syscall, &mut payload);")
    validation_call_index = _line_index(rust_lines, "return validate_heartbeat_return_path(status, &payload);")
    if status_call_index >= 0 and validation_call_index > status_call_index:
        return None
    return ValidationResult.fail(
        code=RETURN_PATH_PROOF_INVALID,
        detail="Return path proof invalid: Rust does not validate the payload after syscall_entry returns",
        action="Validate the returned payload after the bridge call completes",
    )


def _validate_required_anchors(source: str, anchors: tuple[RequiredAnchor, ...]) -> ValidationResult | None:
    missing = _missing_required_anchors(source, anchors)
    if not missing:
        return None
    return _missing_anchor_result(missing[0])


class ReturnPathProofValidator(BaseValidator):
    name = "return_path_proof"
    subsystem = "return_path_proof"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        rust_source = _RUST_MAIN.read_text()
        kernel_source = _KERNEL_MAIN.read_text()

        for result in (
            _validate_trap_path(rust_source),
            _validate_post_call_order(rust_source),
            _validate_required_anchors(rust_source, _rust_return_path_anchors()),
            _validate_required_anchors(kernel_source, _odin_return_path_anchors()),
        ):
            if result is not None:
                return result

        return ValidationResult.pass_(
            code=OK,
            detail="Rust validates returned payload mutations after syscall_entry and Odin writes those mutations through the payload pointer",
        )
