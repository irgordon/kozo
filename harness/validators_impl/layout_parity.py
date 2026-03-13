from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

from harness.codes import LAYOUT_PARITY_MISMATCH, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_GENERATOR_PATH = _ROOT / "scripts" / "gen_abi.py"
_ODIN_BINDINGS = _ROOT / "bindings" / "odin" / "kozo_abi.odin"
_RUST_BINDINGS = _ROOT / "bindings" / "rust" / "kozo_abi.rs"
_ODIN_STRUCT_PATTERN = re.compile(
    r"Heartbeat_Payload\s*::\s*struct(?:\s+#align\((\d+)\))?\s*\{(?P<body>.*?)\}",
    re.DOTALL,
)
_ODIN_FIELD_PATTERN = re.compile(r"([a-z_][a-z0-9_]*)\s*:\s*(u64|u32),")
_RUST_STRUCT_PATTERN = re.compile(
    r"#\[repr\(C\)\]\s*pub struct HeartbeatPayload\s*\{(?P<body>.*?)\}",
    re.DOTALL,
)
_RUST_FIELD_PATTERN = re.compile(r"pub\s+([a-z_][a-z0-9_]*)\s*:\s*(u64|u32),")

_SCALAR_LAYOUT = {
    "u64": (8, 8),
    "u32": (4, 4),
}


def _load_generator_module():
    spec = importlib.util.spec_from_file_location("kozo_gen_abi", _GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load ABI generator from {_GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _align_to(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def _calculate_layout(fields: list[tuple[str, str]], forced_alignment: int | None = None) -> dict[str, object]:
    offset = 0
    alignment = forced_alignment or 1
    offsets: dict[str, int] = {}

    for name, scalar_type in fields:
        size, field_alignment = _SCALAR_LAYOUT[scalar_type]
        alignment = max(alignment, field_alignment)
        offset = _align_to(offset, field_alignment)
        offsets[name] = offset
        offset += size

    size = _align_to(offset, alignment)
    return {"size": size, "alignment": alignment, "offsets": offsets}


def _parse_odin_layout() -> dict[str, object]:
    match = _ODIN_STRUCT_PATTERN.search(_ODIN_BINDINGS.read_text())
    if match is None:
        raise ValueError("Heartbeat_Payload struct is missing from Odin bindings")
    fields = _ODIN_FIELD_PATTERN.findall(match.group("body"))
    return _calculate_layout(fields, int(match.group(1)) if match.group(1) else None)


def _parse_rust_layout() -> dict[str, object]:
    match = _RUST_STRUCT_PATTERN.search(_RUST_BINDINGS.read_text())
    if match is None:
        raise ValueError("HeartbeatPayload struct is missing from Rust bindings")
    fields = _RUST_FIELD_PATTERN.findall(match.group("body"))
    return _calculate_layout(fields)


class LayoutParityValidator(BaseValidator):
    name = "layout_parity"
    subsystem = "structural_integrity"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        generator = _load_generator_module()
        abi_spec = generator.load_abi_spec()
        heartbeat_struct = generator.get_struct(abi_spec, "k_heartbeat_payload_t")
        expected = generator.calculate_struct_layout(heartbeat_struct)
        expected_offsets = {
            "sequence": 0,
            "timestamp": 8,
            "status_bits": 16,
        }

        if expected["size"] != 24 or expected["alignment"] != 8 or expected["offsets"] != expected_offsets:
            return ValidationResult.fail(
                code=LAYOUT_PARITY_MISMATCH,
                detail=f"Normative heartbeat layout drifted: {expected}",
                action="Keep contracts/kozo_abi.h aligned with the LP64 heartbeat payload contract",
            )

        odin_layout = _parse_odin_layout()
        if odin_layout != expected:
            return ValidationResult.fail(
                code=LAYOUT_PARITY_MISMATCH,
                detail=f"Odin heartbeat layout mismatch: expected {expected}, got {odin_layout}",
                action="Regenerate bindings and keep the Odin projection naturally aligned with the ABI",
            )

        rust_layout = _parse_rust_layout()
        if rust_layout != expected:
            return ValidationResult.fail(
                code=LAYOUT_PARITY_MISMATCH,
                detail=f"Rust heartbeat layout mismatch: expected {expected}, got {rust_layout}",
                action="Regenerate bindings and keep the Rust projection naturally aligned with the ABI",
            )

        return ValidationResult.pass_(code=OK, detail="Heartbeat payload layout matches across the C contract, Odin bindings, and Rust bindings")
