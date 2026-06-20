#!/usr/bin/env python3
from __future__ import annotations

import json
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PT_LOAD = 1
EM_X86_64 = 62
ET_EXEC = 2
ELF_MAGIC = b"\x7fELF"
LOWER_HALF_LIMIT = 0x0000800000000000
LOWER_HALF_PHDR_BLOCKER = "limine_lower_half_phdr"

ARCHITECTURES = {
    EM_X86_64: "x86_64",
}

ELF_TYPES = {
    ET_EXEC: "EXEC",
}

REQUIRED_NON_CLAIMS = [
    "QEMU boot",
    "kernel entry execution",
    "serial initialization",
    "hardware trap execution",
    "Linux compatibility",
    "POSIX compatibility",
    "general userspace execution",
    "process model behavior",
    "VFS behavior",
    "scheduler maturity",
    "ELF loading by Limine",
    "file descriptor behavior",
    "production readiness",
]


@dataclass(frozen=True)
class ElfHeader:
    elf_type: int
    machine: int
    entry: int
    program_header_offset: int
    section_header_offset: int
    program_header_entry_size: int
    program_header_count: int
    section_header_count: int


@dataclass(frozen=True)
class ProgramHeader:
    header_type: int
    flags: int
    offset: int
    virtual_address: int
    physical_address: int
    file_size: int
    memory_size: int
    alignment: int


@dataclass(frozen=True)
class LoadLayout:
    minimum_load_virtual_address: int | None
    has_lower_half_load_segment: bool
    entry_is_lower_half: bool
    blocker_category: str


def main() -> int:
    kernel_elf, linker_script, report_path = _parse_args(sys.argv)
    report = build_report(kernel_elf, linker_script)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Kernel ELF report written to {report_path}")
    return 0


def _parse_args(argv: list[str]) -> tuple[Path, Path, Path]:
    if len(argv) != 4:
        raise SystemExit("usage: kernel_elf_report.py <kernel-elf> <linker-script> <report-json>")
    return Path(argv[1]), Path(argv[2]), Path(argv[3])


def build_report(kernel_elf: Path, linker_script: Path) -> dict[str, object]:
    elf_bytes = kernel_elf.read_bytes() if kernel_elf.is_file() else b""
    parse_result = parse_elf(elf_bytes)
    if isinstance(parse_result, str):
        return malformed_report(kernel_elf, linker_script, parse_result)

    header, program_headers = parse_result
    load_segments = [segment for segment in program_headers if segment.header_type == PT_LOAD]
    symbol_address = entry_symbol_address(kernel_elf, "_start")
    layout = load_layout(header, load_segments)
    issues = detected_issues(header, load_segments, symbol_address, layout)

    return {
        "version": 0,
        "phase": "v0.4.2",
        "evidence_type": "kernel-elf-loadability",
        "generated_by": "scripts/kernel_elf_report.py",
        "kernel_elf": "artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf",
        "linker_script": _repo_path(linker_script),
        "architecture": ARCHITECTURES.get(header.machine, f"machine-{header.machine}"),
        "elf_class": "ELF64",
        "endianness": "little",
        "elf_type": ELF_TYPES.get(header.elf_type, f"type-{header.elf_type}"),
        "entry_symbol": "_start",
        "entry_address": _hex(header.entry),
        "entry_symbol_address": _hex(symbol_address) if symbol_address is not None else "",
        "entry_symbol_matches_entry": symbol_address == header.entry,
        "entry_is_lower_half": layout.entry_is_lower_half,
        "program_header_count": header.program_header_count,
        "section_count": header.section_header_count,
        "load_segments": [segment_record(segment) for segment in load_segments],
        "minimum_load_virtual_address": _hex(layout.minimum_load_virtual_address)
        if layout.minimum_load_virtual_address is not None
        else "",
        "has_lower_half_load_segment": layout.has_lower_half_load_segment,
        "load_layout_blocker": layout.blocker_category,
        "detected_issues": issues,
        "blocker_category": blocker_category(issues),
        "proves": proves_for(issues),
        "does_not_prove": REQUIRED_NON_CLAIMS,
    }


def parse_elf(elf_bytes: bytes) -> tuple[ElfHeader, list[ProgramHeader]] | str:
    header_issue = elf_header_issue(elf_bytes)
    if header_issue is not None:
        return header_issue

    header = read_elf_header(elf_bytes)
    program_headers = read_program_headers(elf_bytes, header)
    return header, program_headers


def elf_header_issue(elf_bytes: bytes) -> str | None:
    if len(elf_bytes) < 64:
        return "kernel ELF is missing or too small"
    if elf_bytes[:4] != ELF_MAGIC:
        return "kernel file is not an ELF image"
    if elf_bytes[4] != 2:
        return "kernel ELF is not ELF64"
    if elf_bytes[5] != 1:
        return "kernel ELF is not little-endian"
    return None


def read_elf_header(elf_bytes: bytes) -> ElfHeader:
    values = struct.unpack_from("<16sHHIQQQIHHHHHH", elf_bytes, 0)
    return ElfHeader(
        elf_type=values[1],
        machine=values[2],
        entry=values[4],
        program_header_offset=values[5],
        section_header_offset=values[6],
        program_header_entry_size=values[9],
        program_header_count=values[10],
        section_header_count=values[12],
    )


def read_program_headers(elf_bytes: bytes, header: ElfHeader) -> list[ProgramHeader]:
    return [
        read_program_header(elf_bytes, header.program_header_offset + index * header.program_header_entry_size)
        for index in range(header.program_header_count)
        if _has_program_header(elf_bytes, header.program_header_offset + index * header.program_header_entry_size)
    ]


def _has_program_header(elf_bytes: bytes, offset: int) -> bool:
    return offset >= 0 and offset + 56 <= len(elf_bytes)


def read_program_header(elf_bytes: bytes, offset: int) -> ProgramHeader:
    values = struct.unpack_from("<IIQQQQQQ", elf_bytes, offset)
    return ProgramHeader(
        header_type=values[0],
        flags=values[1],
        offset=values[2],
        virtual_address=values[3],
        physical_address=values[4],
        file_size=values[5],
        memory_size=values[6],
        alignment=values[7],
    )


def entry_symbol_address(kernel_elf: Path, symbol_name: str) -> int | None:
    try:
        result = subprocess.run(["nm", str(kernel_elf)], check=False, capture_output=True, text=True)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return parse_symbol_address(result.stdout, symbol_name)


def parse_symbol_address(nm_output: str, symbol_name: str) -> int | None:
    for line in nm_output.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[-1] == symbol_name:
            try:
                return int(parts[0], 16)
            except ValueError:
                return None
    return None


def load_layout(header: ElfHeader, load_segments: list[ProgramHeader]) -> LoadLayout:
    minimum_vaddr = minimum_load_virtual_address(load_segments)
    has_lower_load = any(is_lower_half(segment.virtual_address) for segment in load_segments)
    entry_is_lower = is_lower_half(header.entry)
    blocker = LOWER_HALF_PHDR_BLOCKER if has_lower_load else "none"
    return LoadLayout(
        minimum_load_virtual_address=minimum_vaddr,
        has_lower_half_load_segment=has_lower_load,
        entry_is_lower_half=entry_is_lower,
        blocker_category=blocker,
    )


def minimum_load_virtual_address(load_segments: list[ProgramHeader]) -> int | None:
    if not load_segments:
        return None
    return min(segment.virtual_address for segment in load_segments)


def is_lower_half(address: int) -> bool:
    return 0 < address < LOWER_HALF_LIMIT


def detected_issues(
    header: ElfHeader,
    load_segments: list[ProgramHeader],
    symbol_address: int | None,
    layout: LoadLayout,
) -> list[str]:
    issues: list[str] = []
    if header.elf_type != ET_EXEC:
        issues.append("linker_output_invalid")
    if header.machine != EM_X86_64:
        issues.append("wrong_architecture")
    if header.entry == 0:
        issues.append("invalid_kernel_entry")
    if not load_segments:
        issues.append("missing_load_segments")
    if symbol_address is None or symbol_address != header.entry:
        issues.append("invalid_kernel_entry")
    if layout.has_lower_half_load_segment:
        issues.append(LOWER_HALF_PHDR_BLOCKER)
    return sorted(set(issues))


def blocker_category(issues: list[str]) -> str:
    if LOWER_HALF_PHDR_BLOCKER in issues:
        return LOWER_HALF_PHDR_BLOCKER
    if "missing_load_segments" in issues:
        return "missing_load_segments"
    if "invalid_kernel_entry" in issues:
        return "invalid_kernel_entry"
    if "wrong_architecture" in issues:
        return "invalid_kernel_elf"
    if "linker_output_invalid" in issues:
        return "linker_output_invalid"
    return "none"


def proves_for(issues: list[str]) -> list[str]:
    if issues:
        return ["kernel ELF loadability was inspected"]
    return [
        "kernel ELF is an x86_64 executable",
        "kernel ELF has an entry point matching _start",
        "kernel ELF has PT_LOAD segments",
        "kernel ELF load layout was inspected for Limine lower-half PHDR rejection",
    ]


def malformed_report(kernel_elf: Path, linker_script: Path, issue: str) -> dict[str, object]:
    return {
        "version": 0,
        "phase": "v0.4.2",
        "evidence_type": "kernel-elf-loadability",
        "generated_by": "scripts/kernel_elf_report.py",
        "kernel_elf": "artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf",
        "linker_script": _repo_path(linker_script),
        "architecture": "",
        "elf_class": "",
        "endianness": "",
        "elf_type": "",
        "entry_symbol": "_start",
        "entry_address": "",
        "entry_symbol_address": "",
        "entry_symbol_matches_entry": False,
        "entry_is_lower_half": False,
        "program_header_count": 0,
        "section_count": 0,
        "load_segments": [],
        "minimum_load_virtual_address": "",
        "has_lower_half_load_segment": False,
        "load_layout_blocker": "invalid_kernel_elf",
        "detected_issues": ["invalid_kernel_elf"],
        "blocker_category": "invalid_kernel_elf",
        "proves": ["kernel ELF loadability was inspected"],
        "does_not_prove": REQUIRED_NON_CLAIMS,
        "detail": issue,
    }


def segment_record(segment: ProgramHeader) -> dict[str, object]:
    return {
        "type": "PT_LOAD",
        "flags": segment_flags(segment.flags),
        "offset": _hex(segment.offset),
        "virtual_address": _hex(segment.virtual_address),
        "physical_address": _hex(segment.physical_address),
        "file_size": _hex(segment.file_size),
        "memory_size": _hex(segment.memory_size),
        "alignment": _hex(segment.alignment),
    }


def segment_flags(flags: int) -> str:
    return "".join(
        (
            "r" if flags & 4 else "-",
            "w" if flags & 2 else "-",
            "x" if flags & 1 else "-",
        )
    )


def _hex(value: int) -> str:
    return f"0x{value:x}"


def _repo_path(path: Path) -> str:
    return str(path).removeprefix(str(Path.cwd()) + "/")


if __name__ == "__main__":
    raise SystemExit(main())
