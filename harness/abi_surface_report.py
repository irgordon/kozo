from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness import abi_manifest

REPORT_PATH = abi_manifest.ROOT / "docs" / "generated" / "abi_surface.md"
MANIFEST_REFERENCE = "contracts/kozo_abi_manifest.json"


@dataclass(frozen=True)
class AbiSurfaceInputs:
    manifest: abi_manifest.AbiManifest


def load_report_inputs(root: Path = abi_manifest.ROOT) -> AbiSurfaceInputs:
    return AbiSurfaceInputs(
        abi_manifest.load_abi_manifest(root / MANIFEST_REFERENCE)
    )


def render_abi_surface_report(inputs: AbiSurfaceInputs) -> str:
    return "\n".join(_report_lines(inputs.manifest))


def expected_report_text(root: Path = abi_manifest.ROOT) -> str:
    return render_abi_surface_report(load_report_inputs(root))


def write_report(root: Path = abi_manifest.ROOT, output_path: Path = REPORT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(expected_report_text(root))


def _report_lines(manifest: abi_manifest.AbiManifest) -> list[str]:
    return [
        "# KOZO ABI surface",
        "",
        *_generated_from_lines(),
        *_scope_lines(),
        *_source_file_lines(manifest),
        *_status_constant_lines(manifest),
        *_syscall_constant_lines(manifest),
        *_layout_lines(manifest),
        *_heartbeat_sentinel_lines(manifest),
        *_note_lines(),
    ]


def _generated_from_lines() -> list[str]:
    return [
        "Generated from:",
        "",
        f"* `{MANIFEST_REFERENCE}`",
        "",
        "This document is generated. Do not edit manually.",
        "",
    ]


def _scope_lines() -> list[str]:
    return [
        "## Scope",
        "",
        "This report summarizes the currently governed KOZO ABI surface. It does not declare a stable public ABI, Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness.",
        "",
    ]


def _source_file_lines(manifest: abi_manifest.AbiManifest) -> list[str]:
    return [
        "## Source files",
        "",
        *_source_file_table_lines(manifest),
        "",
    ]


def _status_constant_lines(manifest: abi_manifest.AbiManifest) -> list[str]:
    return [
        "## Status constants",
        "",
        *_constant_table_lines(manifest.constants.status),
        "",
    ]


def _syscall_constant_lines(manifest: abi_manifest.AbiManifest) -> list[str]:
    return [
        "## Syscall constants",
        "",
        *_constant_table_lines(manifest.constants.syscalls),
        "",
    ]


def _layout_lines(manifest: abi_manifest.AbiManifest) -> list[str]:
    return [
        "## Layouts",
        "",
        *_heartbeat_layout_lines(manifest.heartbeat_payload),
    ]


def _heartbeat_sentinel_lines(manifest: abi_manifest.AbiManifest) -> list[str]:
    return [
        "## Heartbeat sentinels",
        "",
        "### Request",
        "",
        *_sentinel_table_lines(manifest.heartbeat.request),
        "",
        "### Response",
        "",
        *_sentinel_table_lines(manifest.heartbeat.response),
        "",
    ]


def _note_lines() -> list[str]:
    return [
        "## Notes",
        "",
        "* This report is generated from the ABI manifest.",
        "* The ABI manifest, checked-in ABI files, and validators remain authoritative.",
        "* This report is for review and operator readability only.",
        "",
    ]


def _source_file_table_lines(manifest: abi_manifest.AbiManifest) -> list[str]:
    return [
        "| Source | Path |",
        "| --- | --- |",
        f"| Canonical C header | `{manifest.canonical_header}` |",
        f"| Generated Rust binding | `{manifest.generated_bindings.rust}` |",
        f"| Generated Odin binding | `{manifest.generated_bindings.odin}` |",
    ]


def _constant_table_lines(constants: dict[str, int]) -> list[str]:
    return [
        "| Constant | Value |",
        "| --- | --: |",
        *[
            f"| {name} | {value} |"
            for name, value in _ordered_constants(constants)
        ],
    ]


def _heartbeat_layout_lines(layout: abi_manifest.ManifestLayout) -> list[str]:
    return [
        "### heartbeat_payload",
        "",
        "| Field | Width | Offset |",
        "| --- | --: | --: |",
        *[
            f"| {field.name} | {field.width} | {field.offset} |"
            for field in layout.fields
        ],
        "",
        f"Struct size: {layout.size}",
        f"Struct alignment: {layout.alignment}",
        "",
        "Names:",
        "",
        f"* C: `{layout.c_name}`",
        f"* Rust: `{layout.rust_name}`",
        f"* Odin: `{layout.odin_name}`",
        "",
    ]


def _sentinel_table_lines(sentinels: abi_manifest.HeartbeatSentinels) -> list[str]:
    return [
        "| Field | Value |",
        "| --- | --- |",
        f"| sequence | `{sentinels.sequence}` |",
        f"| timestamp | `{sentinels.timestamp}` |",
        f"| status_bits | `{sentinels.status_bits}` |",
    ]


def _ordered_constants(constants: dict[str, int]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(constants.items(), key=lambda item: (item[1], item[0])))
