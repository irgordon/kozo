from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from harness import abi_manifest
from harness.codes import LAYOUT_PARITY_MISMATCH, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_ABI_MANIFEST_PATH = abi_manifest.MANIFEST_PATH

_C_STRUCT_TEMPLATE = r"typedef\s+struct\s+{name}\s*\{{(?P<body>.*?)\}}\s*{name}\s*;"
_C_FIELD_PATTERN = re.compile(r"(uint64_t|uint32_t)\s+([a-z_][a-z0-9_]*)\s*;")
_ODIN_STRUCT_TEMPLATE = r"{name}\s*::\s*struct(?:\s+#align\((\d+)\))?\s*\{{(?P<body>.*?)\}}"
_ODIN_FIELD_PATTERN = re.compile(r"([a-z_][a-z0-9_]*)\s*:\s*(u64|u32),")
_RUST_STRUCT_TEMPLATE = r"#\[repr\(C\)\]\s*pub\s+struct\s+{name}\s*\{{(?P<body>.*?)\}}"
_RUST_FIELD_PATTERN = re.compile(r"pub\s+([a-z_][a-z0-9_]*)\s*:\s*(u64|u32),")


@dataclass(frozen=True)
class LayoutField:
    name: str
    c_type: str
    rust_type: str
    odin_type: str
    width: int
    alignment: int
    offset: int


@dataclass(frozen=True)
class LayoutContract:
    c_name: str
    rust_name: str
    odin_name: str
    fields: tuple[LayoutField, ...]
    size: int
    alignment: int


@dataclass(frozen=True)
class ParsedField:
    name: str
    scalar_type: str
    width: int
    alignment: int
    offset: int


@dataclass(frozen=True)
class LanguageLayout:
    language: str
    struct_name: str
    fields: tuple[ParsedField, ...]
    size: int
    alignment: int


@dataclass(frozen=True)
class LayoutIssue:
    reason: str
    layout_field: str
    detail: str
    action: str


_C_TYPE_LAYOUT = {"uint64_t": (8, 8), "uint32_t": (4, 4)}
_RUST_TYPE_LAYOUT = {"u64": (8, 8), "u32": (4, 4)}
_ODIN_TYPE_LAYOUT = {"u64": (8, 8), "u32": (4, 4)}


class LayoutParityValidator(BaseValidator):
    name = "layout_parity"
    subsystem = "structural_integrity"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _layout_validation_issue()
        if issue is not None:
            return _failure_result(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Heartbeat payload layout matches across the C contract, Odin bindings, and Rust bindings",
        )


def _layout_validation_issue() -> LayoutIssue | None:
    manifest = _load_layout_manifest()
    if isinstance(manifest, LayoutIssue):
        return manifest
    contract = _layout_contract_from_manifest(manifest)
    if isinstance(contract, LayoutIssue):
        return contract
    sources = _load_layout_sources(manifest)
    if isinstance(sources, LayoutIssue):
        return sources
    return _first_layout_issue(contract, sources)


def _load_layout_manifest() -> abi_manifest.AbiManifest | LayoutIssue:
    try:
        return abi_manifest.load_abi_manifest(_ABI_MANIFEST_PATH)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return _issue("manifest_unavailable", "manifest", f"ABI manifest could not be loaded: {exc}")


def _layout_contract_from_manifest(
    manifest: abi_manifest.AbiManifest,
) -> LayoutContract | LayoutIssue:
    manifest_layout = manifest.heartbeat_payload
    fields = tuple(_layout_field_from_manifest(field) for field in manifest_layout.fields)
    issue = _manifest_contract_field_issue(fields)
    if issue is not None:
        return issue
    return LayoutContract(
        c_name=manifest_layout.c_name,
        rust_name=manifest_layout.rust_name,
        odin_name=manifest_layout.odin_name,
        fields=fields,
        size=manifest_layout.size,
        alignment=manifest_layout.alignment,
    )


def _layout_field_from_manifest(field: abi_manifest.ManifestLayoutField) -> LayoutField:
    return LayoutField(
        name=field.name,
        c_type=_c_type_for_width(field.width),
        rust_type=_rust_type_for_width(field.width),
        odin_type=_odin_type_for_width(field.width),
        width=field.width,
        alignment=field.width,
        offset=field.offset,
    )


def _manifest_contract_field_issue(fields: tuple[LayoutField, ...]) -> LayoutIssue | None:
    actual_names = tuple(field.name for field in fields)
    for name in ("sequence", "timestamp", "status_bits"):
        if name not in actual_names:
            return _issue("manifest_missing_layout_field", f"manifest.layouts.heartbeat_payload.fields.{name}", f"ABI manifest is missing heartbeat payload field {name}")
    return None


def _first_layout_issue(
    contract: LayoutContract,
    sources: dict[str, str],
) -> LayoutIssue | None:
    canonical = _parse_c_layout(sources["header"], contract)
    rust = _parse_rust_layout(sources["rust"], contract)
    odin = _parse_odin_layout(sources["odin"], contract)
    return _first_issue(
        _layout_parse_issue(canonical),
        _layout_parse_issue(rust),
        _layout_parse_issue(odin),
        _language_layout_issue(canonical, contract),
        _language_layout_issue(rust, contract),
        _language_layout_issue(odin, contract),
    )


def _load_layout_sources(manifest: abi_manifest.AbiManifest) -> dict[str, str]:
    try:
        return {
            "header": abi_manifest.manifest_repo_path(manifest.canonical_header).read_text(),
            "rust": abi_manifest.manifest_repo_path(manifest.generated_bindings.rust).read_text(),
            "odin": abi_manifest.manifest_repo_path(manifest.generated_bindings.odin).read_text(),
        }
    except OSError as exc:
        return _issue("manifest_source_unavailable", "manifest.generated_bindings", f"ABI manifest source path could not be read: {exc}")


def _parse_c_layout(source: str, contract: LayoutContract) -> LanguageLayout | LayoutIssue:
    matches = tuple(_c_struct_pattern(contract.c_name).finditer(source))
    if len(matches) != 1:
        return _struct_count_issue("canonical", contract.c_name, len(matches))
    fields = tuple((name, scalar_type) for scalar_type, name in _C_FIELD_PATTERN.findall(matches[0].group("body")))
    return _build_language_layout("canonical", contract.c_name, fields, _C_TYPE_LAYOUT, None)


def _parse_rust_layout(source: str, contract: LayoutContract) -> LanguageLayout | LayoutIssue:
    matches = tuple(_rust_struct_pattern(contract.rust_name).finditer(source))
    if len(matches) != 1:
        return _struct_count_issue("rust", contract.rust_name, len(matches))
    fields = tuple(_RUST_FIELD_PATTERN.findall(matches[0].group("body")))
    return _build_language_layout("rust", contract.rust_name, fields, _RUST_TYPE_LAYOUT, None)


def _parse_odin_layout(source: str, contract: LayoutContract) -> LanguageLayout | LayoutIssue:
    matches = tuple(_odin_struct_pattern(contract.odin_name).finditer(source))
    if len(matches) != 1:
        return _struct_count_issue("odin", contract.odin_name, len(matches))
    forced_alignment = int(matches[0].group(1)) if matches[0].group(1) else None
    fields = tuple(_ODIN_FIELD_PATTERN.findall(matches[0].group("body")))
    return _build_language_layout("odin", contract.odin_name, fields, _ODIN_TYPE_LAYOUT, forced_alignment)


def _c_struct_pattern(struct_name: str) -> re.Pattern[str]:
    return re.compile(_C_STRUCT_TEMPLATE.format(name=re.escape(struct_name)), re.DOTALL)


def _rust_struct_pattern(struct_name: str) -> re.Pattern[str]:
    return re.compile(_RUST_STRUCT_TEMPLATE.format(name=re.escape(struct_name)), re.DOTALL)


def _odin_struct_pattern(struct_name: str) -> re.Pattern[str]:
    return re.compile(_ODIN_STRUCT_TEMPLATE.format(name=re.escape(struct_name)), re.DOTALL)


def _build_language_layout(
    language: str,
    struct_name: str,
    fields: tuple[tuple[str, str], ...],
    scalar_layout: dict[str, tuple[int, int]],
    forced_alignment: int | None,
) -> LanguageLayout | LayoutIssue:
    parsed_fields = _parsed_fields(fields, scalar_layout)
    if isinstance(parsed_fields, LayoutIssue):
        return parsed_fields
    size, alignment = _struct_size(parsed_fields, forced_alignment)
    return LanguageLayout(language, struct_name, parsed_fields, size, alignment)


def _parsed_fields(
    fields: tuple[tuple[str, str], ...],
    scalar_layout: dict[str, tuple[int, int]],
) -> tuple[ParsedField, ...] | LayoutIssue:
    offset = 0
    parsed: list[ParsedField] = []
    for name, scalar_type in fields:
        if scalar_type not in scalar_layout:
            return _issue("unsupported_field_type", name, f"Unsupported layout scalar type {scalar_type!r}")
        width, alignment = scalar_layout[scalar_type]
        offset = _align_to(offset, alignment)
        parsed.append(ParsedField(name, scalar_type, width, alignment, offset))
        offset += width
    return tuple(parsed)


def _struct_size(fields: tuple[ParsedField, ...], forced_alignment: int | None) -> tuple[int, int]:
    alignment = max((field.alignment for field in fields), default=1)
    alignment = max(alignment, forced_alignment or 1)
    raw_size = 0 if not fields else fields[-1].offset + fields[-1].width
    return _align_to(raw_size, alignment), alignment


def _language_layout_issue(
    layout: LanguageLayout | LayoutIssue,
    contract: LayoutContract,
) -> LayoutIssue | None:
    if isinstance(layout, LayoutIssue):
        return layout
    return _first_issue(
        _missing_field_issue(layout, contract),
        _field_order_issue(layout, contract),
        _field_width_issue(layout, contract),
        _field_offset_issue(layout, contract),
        _struct_size_issue(layout, contract),
        _struct_alignment_issue(layout, contract),
        _extra_field_issue(layout, contract),
    )


def _missing_field_issue(layout: LanguageLayout, contract: LayoutContract) -> LayoutIssue | None:
    expected = _contract_field_names(contract)
    actual = tuple(field.name for field in layout.fields)
    missing = tuple(name for name in expected if name not in actual)
    if missing:
        return _language_issue(layout.language, "missing_field", missing[0], f"{layout.struct_name} is missing field {missing[0]}")
    return None


def _field_order_issue(layout: LanguageLayout, contract: LayoutContract) -> LayoutIssue | None:
    expected = _contract_field_names(contract)
    actual = tuple(field.name for field in layout.fields if field.name in expected)
    if actual == expected:
        return None
    return _language_issue(layout.language, "wrong_field_order", contract.c_name, f"{layout.struct_name} field order is {actual}, expected {expected}")


def _field_width_issue(layout: LanguageLayout, contract: LayoutContract) -> LayoutIssue | None:
    for expected in contract.fields:
        actual = _parsed_field_named(layout, expected.name)
        if actual is None:
            continue
        if actual.width != expected.width:
            return _language_issue(layout.language, "wrong_field_width", actual.name, f"{actual.name} width is {actual.width}, expected {expected.width}")
    return None


def _field_offset_issue(layout: LanguageLayout, contract: LayoutContract) -> LayoutIssue | None:
    for expected in contract.fields:
        actual = _parsed_field_named(layout, expected.name)
        if actual is None:
            continue
        if actual.offset != expected.offset:
            return _language_issue(layout.language, "wrong_field_offset", actual.name, f"{actual.name} offset is {actual.offset}, expected {expected.offset}")
    return None


def _struct_size_issue(layout: LanguageLayout, contract: LayoutContract) -> LayoutIssue | None:
    if layout.size == contract.size:
        return None
    return _language_issue(layout.language, "wrong_struct_size", layout.struct_name, f"{layout.struct_name} size is {layout.size}, expected {contract.size}")


def _struct_alignment_issue(layout: LanguageLayout, contract: LayoutContract) -> LayoutIssue | None:
    if layout.alignment == contract.alignment:
        return None
    return _language_issue(layout.language, "wrong_struct_alignment", layout.struct_name, f"{layout.struct_name} alignment is {layout.alignment}, expected {contract.alignment}")


def _extra_field_issue(layout: LanguageLayout, contract: LayoutContract) -> LayoutIssue | None:
    expected = _contract_field_names(contract)
    actual = tuple(field.name for field in layout.fields)
    extras = tuple(name for name in actual if name not in expected)
    if not extras:
        return None
    return _language_issue(layout.language, "unexpected_field", extras[0], f"{layout.struct_name} has unexpected field {extras[0]}")


def _layout_parse_issue(layout: LanguageLayout | LayoutIssue) -> LayoutIssue | None:
    return layout if isinstance(layout, LayoutIssue) else None


def _contract_field_names(contract: LayoutContract) -> tuple[str, ...]:
    return tuple(field.name for field in contract.fields)


def _c_type_for_width(width: int) -> str:
    return {8: "uint64_t", 4: "uint32_t"}.get(width, f"unsupported_width_{width}")


def _rust_type_for_width(width: int) -> str:
    return {8: "u64", 4: "u32"}.get(width, f"unsupported_width_{width}")


def _odin_type_for_width(width: int) -> str:
    return {8: "u64", 4: "u32"}.get(width, f"unsupported_width_{width}")


def _parsed_field_named(layout: LanguageLayout, name: str) -> ParsedField | None:
    return next((field for field in layout.fields if field.name == name), None)


def _align_to(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def _first_issue(*issues: LayoutIssue | None) -> LayoutIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _struct_count_issue(language: str, struct_name: str, count: int) -> LayoutIssue:
    return _language_issue(language, "wrong_struct_definition_count", struct_name, f"Expected exactly one {struct_name} definition, found {count}")


def _language_issue(
    language: str,
    reason: str,
    layout_field: str,
    detail: str,
) -> LayoutIssue:
    return _issue(
        f"{language}_{reason}",
        f"{language}.{layout_field}",
        f"{language} layout mismatch: {detail}",
    )


def _issue(reason: str, layout_field: str, detail: str) -> LayoutIssue:
    return LayoutIssue(
        reason,
        layout_field,
        detail,
        "Regenerate bindings and keep the heartbeat payload layout aligned with contracts/kozo_abi.h",
    )


def _failure_result(issue: LayoutIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=LAYOUT_PARITY_MISMATCH,
        detail=issue.detail,
        action=issue.action,
        meta={
            "reason": issue.reason,
            "layout_field": issue.layout_field,
        },
    )
