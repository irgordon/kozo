#!/usr/bin/env python3
from __future__ import annotations

import json
import re
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
MEMORY_REGION_START_SYMBOL = "boot_memory_region"
MEMORY_REGION_END_SYMBOL = "boot_memory_region_end"
MEMORY_REGION_ALIGNMENT = 4096
RUNTIME_PROGRESSION_SYMBOLS = (
    "runtime_progression_entry",
    "runtime_bootstrap_context",
    "runtime_progression_state",
    "runtime_serial_write_init_marker",
)
CONTROLLED_RUNTIME_LOOP_SYMBOLS = (
    "controlled_runtime_loop",
    "runtime_loop_state",
    "runtime_serial_write_loop_enter_marker",
    "runtime_serial_write_loop_iter_1_marker",
    "runtime_serial_write_loop_iter_2_marker",
    "runtime_serial_write_loop_iter_3_marker",
    "runtime_serial_write_loop_exit_marker",
)
FIRST_CAPABILITY_SYMBOLS = (
    "execute_first_governed_capability",
    "dispatch_runtime_capability",
    "query_runtime_status",
    "runtime_serial_write_capability_dispatch_marker",
    "runtime_serial_write_status_query_marker",
    "runtime_serial_write_first_capability_marker",
)
BRANCH_MNEMONIC = re.compile(r"^j[a-z]+$")
INSTRUCTION_LINE = re.compile(
    r"^\s*([0-9a-fA-F]+):\s+(?:(?:[0-9a-fA-F]{2})\s+)+([a-zA-Z][a-zA-Z0-9.]*)\s*(.*)$"
)
HEX_OPERAND = re.compile(r"(?:0x)?([0-9a-fA-F]{6,16})")

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
    minimum_load_physical_address: int | None
    has_lower_half_load_segment: bool
    all_load_segments_higher_half: bool
    entry_is_lower_half: bool
    entry_address_class: str
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
    symbols = symbol_addresses(
        kernel_elf,
        (
            "_start",
            MEMORY_REGION_START_SYMBOL,
            MEMORY_REGION_END_SYMBOL,
            *RUNTIME_PROGRESSION_SYMBOLS,
            *CONTROLLED_RUNTIME_LOOP_SYMBOLS,
            *FIRST_CAPABILITY_SYMBOLS,
        ),
    )
    symbol_address = symbols.get("_start")
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
        "entry_address_class": layout.entry_address_class,
        "memory_evidence_region": memory_evidence_region_record(symbols),
        "runtime_progression_symbols": runtime_progression_symbol_record(symbols),
        "controlled_runtime_loop": controlled_runtime_loop_record(kernel_elf, symbols),
        "first_governed_runtime_capability": first_capability_record(kernel_elf, symbols),
        "program_header_count": header.program_header_count,
        "section_count": header.section_header_count,
        "load_segments": [segment_record(segment) for segment in load_segments],
        "virtual_base": _hex(layout.minimum_load_virtual_address)
        if layout.minimum_load_virtual_address is not None
        else "",
        "physical_load_base": _hex(layout.minimum_load_physical_address)
        if layout.minimum_load_physical_address is not None
        else "",
        "minimum_load_virtual_address": _hex(layout.minimum_load_virtual_address)
        if layout.minimum_load_virtual_address is not None
        else "",
        "minimum_load_physical_address": _hex(layout.minimum_load_physical_address)
        if layout.minimum_load_physical_address is not None
        else "",
        "has_lower_half_load_segment": layout.has_lower_half_load_segment,
        "all_load_segments_higher_half": layout.all_load_segments_higher_half,
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
    return symbol_addresses(kernel_elf, (symbol_name,)).get(symbol_name)


def symbol_addresses(kernel_elf: Path, symbol_names: tuple[str, ...]) -> dict[str, int]:
    try:
        result = subprocess.run(["nm", str(kernel_elf)], check=False, capture_output=True, text=True)
    except OSError:
        return {}
    if result.returncode != 0:
        return {}
    return parse_symbol_addresses(result.stdout, set(symbol_names))


def parse_symbol_addresses(nm_output: str, symbol_names: set[str]) -> dict[str, int]:
    return {
        symbol_name: address
        for symbol_name in symbol_names
        if (address := parse_symbol_address(nm_output, symbol_name)) is not None
    }


def parse_symbol_address(nm_output: str, symbol_name: str) -> int | None:
    for line in nm_output.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[-1] == symbol_name:
            try:
                return int(parts[0], 16)
            except ValueError:
                return None
    return None


def memory_evidence_region_record(symbols: dict[str, int]) -> dict[str, object]:
    start = symbols.get(MEMORY_REGION_START_SYMBOL)
    end = symbols.get(MEMORY_REGION_END_SYMBOL)
    size = end - start if start is not None and end is not None else None
    return {
        "start_symbol": MEMORY_REGION_START_SYMBOL,
        "end_symbol": MEMORY_REGION_END_SYMBOL,
        "start_address": _hex(start) if start is not None else "",
        "end_address": _hex(end) if end is not None else "",
        "size_bytes": size if size is not None and size >= 0 else -1,
        "required_alignment_bytes": MEMORY_REGION_ALIGNMENT,
        "start_aligned": start is not None and start % MEMORY_REGION_ALIGNMENT == 0,
    }


def runtime_progression_symbol_record(symbols: dict[str, int]) -> dict[str, object]:
    return {
        symbol: {
            "present": symbol in symbols,
            "address": _hex(symbols[symbol]) if symbol in symbols else "",
        }
        for symbol in RUNTIME_PROGRESSION_SYMBOLS
    }


def controlled_runtime_loop_record(
    kernel_elf: Path,
    symbols: dict[str, int],
) -> dict[str, object]:
    disassembly = disassemble_symbol(kernel_elf, "controlled_runtime_loop")
    instructions = parse_disassembly_instructions(disassembly)
    back_edges = backward_branch_records(instructions)
    return {
        "symbols": symbol_record(symbols, CONTROLLED_RUNTIME_LOOP_SYMBOLS),
        "disassembly_available": bool(instructions),
        "backward_branch_present": bool(back_edges),
        "backward_branches": back_edges,
        "terminal_comparison_present": any(mnemonic.startswith("cmp") for _, mnemonic, _ in instructions),
    }


def first_capability_record(
    kernel_elf: Path,
    symbols: dict[str, int],
) -> dict[str, object]:
    instructions = parse_disassembly_instructions(
        disassemble_symbol(kernel_elf, "runtime_progression_entry")
    )
    entry_address = symbols.get("execute_first_governed_capability")
    return {
        "symbols": symbol_record(symbols, FIRST_CAPABILITY_SYMBOLS),
        "progression_call_present": _calls_address(instructions, entry_address),
    }


def _calls_address(
    instructions: list[tuple[int, str, str]],
    target_address: int | None,
) -> bool:
    if target_address is None:
        return False
    return any(
        mnemonic.startswith("call") and instruction_target(operands) == target_address
        for _, mnemonic, operands in instructions
    )


def symbol_record(
    symbols: dict[str, int],
    names: tuple[str, ...],
) -> dict[str, object]:
    return {
        symbol: {
            "present": symbol in symbols,
            "address": _hex(symbols[symbol]) if symbol in symbols else "",
        }
        for symbol in names
    }


def disassemble_symbol(kernel_elf: Path, symbol: str) -> str:
    commands = (
        ["objdump", f"--disassemble-symbols={symbol}", str(kernel_elf)],
        ["objdump", f"--disassemble={symbol}", str(kernel_elf)],
    )
    for command in commands:
        output = run_text_command(command)
        if output:
            return output
    return ""


def run_text_command(command: list[str]) -> str:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError:
        return ""
    return result.stdout if result.returncode == 0 else ""


def parse_disassembly_instructions(text: str) -> list[tuple[int, str, str]]:
    instructions = []
    for line in text.splitlines():
        match = INSTRUCTION_LINE.match(line)
        if match is not None:
            instructions.append((int(match.group(1), 16), match.group(2).lower(), match.group(3)))
    return instructions


def backward_branch_records(
    instructions: list[tuple[int, str, str]],
) -> list[dict[str, str]]:
    records = []
    for address, mnemonic, operands in instructions:
        target = branch_target(mnemonic, operands)
        if target is not None and target < address:
            records.append({"instruction_address": _hex(address), "target_address": _hex(target)})
    return records


def branch_target(mnemonic: str, operands: str) -> int | None:
    if BRANCH_MNEMONIC.fullmatch(mnemonic) is None:
        return None
    return instruction_target(operands)


def instruction_target(operands: str) -> int | None:
    match = HEX_OPERAND.search(operands)
    return int(match.group(1), 16) if match is not None else None


def load_layout(header: ElfHeader, load_segments: list[ProgramHeader]) -> LoadLayout:
    minimum_vaddr = minimum_load_virtual_address(load_segments)
    minimum_paddr = minimum_load_physical_address(load_segments)
    has_lower_load = any(is_lower_half(segment.virtual_address) for segment in load_segments)
    all_higher_load = bool(load_segments) and not has_lower_load
    entry_is_lower = is_lower_half(header.entry)
    blocker = LOWER_HALF_PHDR_BLOCKER if has_lower_load else "none"
    return LoadLayout(
        minimum_load_virtual_address=minimum_vaddr,
        minimum_load_physical_address=minimum_paddr,
        has_lower_half_load_segment=has_lower_load,
        all_load_segments_higher_half=all_higher_load,
        entry_is_lower_half=entry_is_lower,
        entry_address_class=address_class(header.entry),
        blocker_category=blocker,
    )


def minimum_load_virtual_address(load_segments: list[ProgramHeader]) -> int | None:
    if not load_segments:
        return None
    return min(segment.virtual_address for segment in load_segments)


def minimum_load_physical_address(load_segments: list[ProgramHeader]) -> int | None:
    if not load_segments:
        return None
    return min(segment.physical_address for segment in load_segments)


def address_class(address: int) -> str:
    if address == 0:
        return "zero"
    if is_lower_half(address):
        return "lower-half"
    return "higher-half"


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
        "entry_address_class": "zero",
        "memory_evidence_region": memory_evidence_region_record({}),
        "runtime_progression_symbols": runtime_progression_symbol_record({}),
        "controlled_runtime_loop": controlled_runtime_loop_record(kernel_elf, {}),
        "first_governed_runtime_capability": first_capability_record(kernel_elf, {}),
        "program_header_count": 0,
        "section_count": 0,
        "load_segments": [],
        "virtual_base": "",
        "physical_load_base": "",
        "minimum_load_virtual_address": "",
        "minimum_load_physical_address": "",
        "has_lower_half_load_segment": False,
        "all_load_segments_higher_half": False,
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
