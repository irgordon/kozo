from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness import abi_manifest
from harness.codes import ABI_MANIFEST_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_MANIFEST_PATH = abi_manifest.MANIFEST_PATH
_HEADER_STATUS_PATTERN = re.compile(r"\b(K_[A-Z0-9_]+)\s*=\s*(\d+)")
_HEADER_SYSCALL_PATTERN = re.compile(r"\b(K_SYSCALL_[A-Z0-9_]+)\s*=\s*(\d+)")
_HEADER_STRUCT_TEMPLATE = r"typedef\s+struct\s+{name}\s*\{{(?P<body>.*?)\}}\s*{name}\s*;"
_HEADER_FIELD_PATTERN = re.compile(r"(uint64_t|uint32_t)\s+([a-z_][a-z0-9_]*)\s*;")
_C_TYPE_LAYOUT = {"uint64_t": (8, 8), "uint32_t": (4, 4)}


@dataclass(frozen=True)
class ManifestIssue:
    reason: str
    manifest_field: str
    detail: str


@dataclass(frozen=True)
class HeaderField:
    name: str
    width: int
    alignment: int
    offset: int


@dataclass(frozen=True)
class HeaderLayout:
    fields: tuple[HeaderField, ...]
    size: int
    alignment: int


class AbiManifestValidator(BaseValidator):
    name = "abi_manifest"
    subsystem = "abi_manifest"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _first_manifest_issue(_MANIFEST_PATH)
        if issue is not None:
            return _failure_result(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="ABI manifest exists, is schema-valid, and matches the canonical header paths, constants, and heartbeat layout",
        )


def _first_manifest_issue(path: Path) -> ManifestIssue | None:
    raw_issue = _manifest_file_issue(path)
    if raw_issue is not None:
        return raw_issue
    data_or_issue = _load_manifest_data(path)
    if isinstance(data_or_issue, ManifestIssue):
        return data_or_issue
    manifest_or_issue = _parse_manifest(data_or_issue)
    if isinstance(manifest_or_issue, ManifestIssue):
        return manifest_or_issue
    return _manifest_content_issue(manifest_or_issue)


def _manifest_file_issue(path: Path) -> ManifestIssue | None:
    if path.is_file():
        return None
    return _issue("missing_manifest_file", "manifest", f"ABI manifest is missing: {path}")


def _load_manifest_data(path: Path) -> dict[str, Any] | ManifestIssue:
    try:
        return abi_manifest.load_manifest_json(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_manifest_json", "manifest", f"ABI manifest is invalid JSON: {exc}")


def _parse_manifest(data: dict[str, Any]) -> abi_manifest.AbiManifest | ManifestIssue:
    try:
        abi_manifest.validate_manifest_shape(data)
        return abi_manifest.parse_abi_manifest(data)
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("manifest_schema_violation", "manifest", f"ABI manifest schema violation: {exc}")


def _manifest_content_issue(manifest: abi_manifest.AbiManifest) -> ManifestIssue | None:
    return _first_issue(
        _manifest_path_issue(manifest),
        _manifest_constant_issue(manifest),
        _manifest_layout_issue(manifest),
    )


def _manifest_path_issue(manifest: abi_manifest.AbiManifest) -> ManifestIssue | None:
    for field, path in _manifest_paths(manifest):
        if not abi_manifest.manifest_repo_path(path).is_file():
            return _issue("manifest_path_missing", field, f"ABI manifest path does not exist: {path}")
    return None


def _manifest_paths(manifest: abi_manifest.AbiManifest) -> tuple[tuple[str, str], ...]:
    return (
        ("canonical_header", manifest.canonical_header),
        ("generated_bindings.rust", manifest.generated_bindings.rust),
        ("generated_bindings.odin", manifest.generated_bindings.odin),
    )


def _manifest_constant_issue(manifest: abi_manifest.AbiManifest) -> ManifestIssue | None:
    header_source = abi_manifest.manifest_repo_path(manifest.canonical_header).read_text()
    return _first_issue(
        _constant_map_issue("constants.status", manifest.constants.status, _header_status_constants(header_source)),
        _constant_map_issue("constants.syscalls", manifest.constants.syscalls, _header_syscall_constants(header_source)),
    )


def _header_status_constants(source: str) -> dict[str, int]:
    return {
        name: int(value)
        for name, value in _HEADER_STATUS_PATTERN.findall(source)
        if not name.startswith("K_SYSCALL_")
    }


def _header_syscall_constants(source: str) -> dict[str, int]:
    return {name: int(value) for name, value in _HEADER_SYSCALL_PATTERN.findall(source)}


def _constant_map_issue(
    manifest_field: str,
    manifest_constants: dict[str, int],
    header_constants: dict[str, int],
) -> ManifestIssue | None:
    for name, value in manifest_constants.items():
        if name not in header_constants:
            return _issue("manifest_constant_missing_in_header", f"{manifest_field}.{name}", f"{name} is not declared in the canonical ABI header")
        if header_constants[name] != value:
            return _issue("manifest_constant_mismatch", f"{manifest_field}.{name}", f"{name} is {value} in the manifest but {header_constants[name]} in the canonical ABI header")
    for name in header_constants:
        if name not in manifest_constants:
            return _issue("manifest_constant_missing", f"{manifest_field}.{name}", f"{name} is declared in the canonical ABI header but missing from the manifest")
    return None


def _manifest_layout_issue(manifest: abi_manifest.AbiManifest) -> ManifestIssue | None:
    header_layout = _header_layout(manifest)
    if isinstance(header_layout, ManifestIssue):
        return header_layout
    manifest_layout = manifest.heartbeat_payload
    return _first_issue(
        _layout_field_issue(manifest_layout, header_layout),
        _layout_size_issue(manifest_layout, header_layout),
        _layout_alignment_issue(manifest_layout, header_layout),
    )


def _header_layout(manifest: abi_manifest.AbiManifest) -> HeaderLayout | ManifestIssue:
    header_source = abi_manifest.manifest_repo_path(manifest.canonical_header).read_text()
    match = _header_struct_pattern(manifest.heartbeat_payload.c_name).search(header_source)
    if match is None:
        return _issue("manifest_layout_missing_header_struct", "layouts.heartbeat_payload.c_name", "Canonical heartbeat payload struct is missing from the ABI header")
    return _calculate_header_layout(_HEADER_FIELD_PATTERN.findall(match.group("body")))


def _header_struct_pattern(struct_name: str) -> re.Pattern[str]:
    return re.compile(_HEADER_STRUCT_TEMPLATE.format(name=re.escape(struct_name)), re.DOTALL)


def _calculate_header_layout(fields: list[tuple[str, str]]) -> HeaderLayout | ManifestIssue:
    offset = 0
    parsed: list[HeaderField] = []
    for c_type, name in fields:
        if c_type not in _C_TYPE_LAYOUT:
            return _issue("manifest_layout_unsupported_type", f"layouts.heartbeat_payload.fields.{name}", f"Unsupported ABI field type {c_type}")
        width, alignment = _C_TYPE_LAYOUT[c_type]
        offset = _align_to(offset, alignment)
        parsed.append(HeaderField(name, width, alignment, offset))
        offset += width
    struct_alignment = max((field.alignment for field in parsed), default=1)
    return HeaderLayout(tuple(parsed), _align_to(offset, struct_alignment), struct_alignment)


def _layout_field_issue(
    manifest_layout: abi_manifest.ManifestLayout,
    header_layout: HeaderLayout,
) -> ManifestIssue | None:
    for manifest_field in manifest_layout.fields:
        header_field = _header_field_named(header_layout, manifest_field.name)
        if header_field is None:
            return _issue("manifest_layout_field_missing_in_header", f"layouts.heartbeat_payload.fields.{manifest_field.name}", f"{manifest_field.name} is not declared in the canonical ABI header")
        if manifest_field.width != header_field.width:
            return _issue("manifest_layout_field_width_mismatch", f"layouts.heartbeat_payload.fields.{manifest_field.name}.width", f"{manifest_field.name} width is {manifest_field.width} in the manifest but {header_field.width} in the canonical ABI header")
        if manifest_field.offset != header_field.offset:
            return _issue("manifest_layout_field_offset_mismatch", f"layouts.heartbeat_payload.fields.{manifest_field.name}.offset", f"{manifest_field.name} offset is {manifest_field.offset} in the manifest but {header_field.offset} in the canonical ABI header")
    return None


def _layout_size_issue(
    manifest_layout: abi_manifest.ManifestLayout,
    header_layout: HeaderLayout,
) -> ManifestIssue | None:
    if manifest_layout.size == header_layout.size:
        return None
    return _issue("manifest_layout_size_mismatch", "layouts.heartbeat_payload.size", f"Heartbeat payload size is {manifest_layout.size} in the manifest but {header_layout.size} in the canonical ABI header")


def _layout_alignment_issue(
    manifest_layout: abi_manifest.ManifestLayout,
    header_layout: HeaderLayout,
) -> ManifestIssue | None:
    if manifest_layout.alignment == header_layout.alignment:
        return None
    return _issue("manifest_layout_alignment_mismatch", "layouts.heartbeat_payload.alignment", f"Heartbeat payload alignment is {manifest_layout.alignment} in the manifest but {header_layout.alignment} in the canonical ABI header")


def _header_field_named(layout: HeaderLayout, name: str) -> HeaderField | None:
    return next((field for field in layout.fields if field.name == name), None)


def _align_to(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def _first_issue(*issues: ManifestIssue | None) -> ManifestIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, manifest_field: str, detail: str) -> ManifestIssue:
    return ManifestIssue(reason, manifest_field, detail)


def _failure_result(issue: ManifestIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=ABI_MANIFEST_INVALID,
        detail=f"ABI manifest invalid: {issue.detail}",
        action="Keep contracts/kozo_abi_manifest.json aligned with the canonical ABI header and generated bindings",
        meta={
            "reason": issue.reason,
            "manifest_field": issue.manifest_field,
        },
    )
