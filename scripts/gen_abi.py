#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER_PATH = ROOT / "contracts" / "kozo_abi.h"
ODIN_OUTPUT_PATH = ROOT / "bindings" / "odin" / "kozo_abi.odin"
RUST_OUTPUT_PATH = ROOT / "bindings" / "rust" / "kozo_abi.rs"

HANDLE_TYPE_PATTERN = re.compile(r"typedef\s+(uint64_t)\s+(kozo_handle_t);")
VERSION_PATTERN = re.compile(r"#define\s+KOZO_ABI_VERSION\s+(\d+)")
ENUM_BLOCK_PATTERN = re.compile(
    r"typedef enum\s+(k_[a-z_]+_t)\s*\{(?P<body>.*?)\}\s*(k_[a-z_]+_t);",
    re.DOTALL,
)
ENUM_ENTRY_PATTERN = re.compile(r"([A-Z0-9_]+)\s*=\s*(\d+)")


@dataclass(frozen=True)
class EnumSpec:
    name: str
    base_type: str
    entries: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class AbiSpec:
    version: int
    handle_name: str
    handle_c_type: str
    enums: tuple[EnumSpec, ...]


def _read_header(path: Path = HEADER_PATH) -> str:
    return path.read_text()


def _parse_handle(header: str) -> tuple[str, str]:
    match = HANDLE_TYPE_PATTERN.search(header)
    if match is None:
        raise ValueError("kozo_handle_t definition is missing or invalid")
    return match.group(2), match.group(1)


def _parse_version(header: str) -> int:
    match = VERSION_PATTERN.search(header)
    if match is None:
        raise ValueError("KOZO_ABI_VERSION definition is missing")
    return int(match.group(1))


def _base_type(name: str) -> str:
    if name in {"k_status_t", "k_syscall_id_t"}:
        return "uint32_t"
    raise ValueError(f"unsupported enum type: {name}")


def _parse_enums(header: str) -> tuple[EnumSpec, ...]:
    enums: list[EnumSpec] = []
    for match in ENUM_BLOCK_PATTERN.finditer(header):
        enum_name = match.group(1)
        typedef_name = match.group(3)
        if enum_name != typedef_name:
            raise ValueError(f"enum typedef mismatch: {enum_name} != {typedef_name}")
        entries = tuple(
            (name, int(value))
            for name, value in ENUM_ENTRY_PATTERN.findall(match.group("body"))
        )
        if not entries:
            raise ValueError(f"enum {enum_name} has no entries")
        enums.append(EnumSpec(enum_name, _base_type(enum_name), entries))
    if not enums:
        raise ValueError("no ABI enums found in header")
    return tuple(enums)


def load_abi_spec(path: Path = HEADER_PATH) -> AbiSpec:
    header = _read_header(path)
    handle_name, handle_c_type = _parse_handle(header)
    return AbiSpec(
        version=_parse_version(header),
        handle_name=handle_name,
        handle_c_type=handle_c_type,
        enums=_parse_enums(header),
    )


def _odin_type_name(c_name: str) -> str:
    mapping = {
        "kozo_handle_t": "K_HANDLE",
        "k_status_t": "K_STATUS",
        "k_syscall_id_t": "K_SYSCALL_ID",
    }
    return mapping[c_name]


def _odin_scalar_type(c_name: str) -> str:
    mapping = {
        "uint64_t": "u64",
        "uint32_t": "u32",
    }
    return mapping[c_name]


def generate_odin_bindings(spec: AbiSpec) -> str:
    lines = [
        "package kozo_abi",
        "",
        f"KOZO_ABI_VERSION :: {spec.version}",
        "",
        f"{_odin_type_name(spec.handle_name)} :: {_odin_scalar_type(spec.handle_c_type)}",
    ]
    for enum_spec in spec.enums:
        lines.append(f"{_odin_type_name(enum_spec.name)} :: {_odin_scalar_type(enum_spec.base_type)}")
        for constant_name, value in enum_spec.entries:
            lines.append(
                f"{constant_name} : {_odin_type_name(enum_spec.name)} : {value}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _rust_type_name(c_name: str) -> str:
    mapping = {
        "kozo_handle_t": "K_HANDLE",
        "k_status_t": "K_STATUS",
        "k_syscall_id_t": "K_SYSCALL_ID",
    }
    return mapping[c_name]


def _rust_scalar_type(c_name: str) -> str:
    mapping = {
        "uint64_t": "u64",
        "uint32_t": "u32",
    }
    return mapping[c_name]


def generate_rust_bindings(spec: AbiSpec) -> str:
    lines = [
        "#![no_std]",
        "",
        f"pub const KOZO_ABI_VERSION: u32 = {spec.version};",
        "",
        f"pub type {_rust_type_name(spec.handle_name)} = {_rust_scalar_type(spec.handle_c_type)};",
    ]
    for enum_spec in spec.enums:
        rust_type = _rust_type_name(enum_spec.name)
        lines.append(f"pub type {rust_type} = {_rust_scalar_type(enum_spec.base_type)};")
        for constant_name, value in enum_spec.entries:
            lines.append(f"pub const {constant_name}: {rust_type} = {value};")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_targets(spec: AbiSpec) -> dict[Path, str]:
    return {
        ODIN_OUTPUT_PATH: generate_odin_bindings(spec),
        RUST_OUTPUT_PATH: generate_rust_bindings(spec),
    }


def write_targets(spec: AbiSpec) -> None:
    for path, content in render_targets(spec).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate KOZO ABI bindings")
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print generated target metadata instead of writing files",
    )
    return parser


def main() -> int:
    args = _build_argument_parser().parse_args()
    spec = load_abi_spec()
    if args.print_json:
        rendered = {
            str(path.relative_to(ROOT)): content
            for path, content in render_targets(spec).items()
        }
        print(json.dumps(rendered, indent=2, sort_keys=True))
        return 0
    write_targets(spec)
    print("Generated bindings/odin/kozo_abi.odin")
    print("Generated bindings/rust/kozo_abi.rs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
