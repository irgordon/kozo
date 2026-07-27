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
CPU_EXTENDED_STATE_SYMBOLS = (
    "initialize_cpu_extended_state",
    "required_cpu_features_available",
    "configure_extended_state_controls",
    "verify_extended_state_controls",
    "initialize_x87_state",
    "initialize_sse_state",
    "run_simd_survival_probe",
    "observed_x87_control_word",
    "observed_mxcsr",
    "simd_probe_result",
    "simd_probe_result_end",
)
RUNTIME_STATE_TRANSITION_SYMBOLS = (
    "runtime_state_transition_cell",
    "initialize_runtime_state_transition_cell",
    "execute_second_governed_capability",
    "dispatch_runtime_capability",
    "dispatch_runtime_state_transition",
    "transition_runtime_state",
    "runtime_state_cell_store",
    "runtime_state_cell_state",
    "runtime_state_cell_reserved",
    "runtime_state_cell_generation",
    "runtime_serial_write_state_update_enter_marker",
    "runtime_serial_write_state_update_ok_marker",
    "runtime_serial_write_second_capability_marker",
)
FIXED_USER_MAPPING_SYMBOLS = (
    "initialize_fixed_user_mapping_tables",
    "validate_fixed_user_mapping_policy",
    "activate_fixed_user_mapping_root",
    "run_fixed_user_mapping_survival_probe",
    "walk_page_mapping",
    "governed_pml4",
    "governed_kernel_pdpt",
    "governed_kernel_pd",
    "governed_kernel_pt",
    "governed_user_pdpt",
    "governed_user_pd",
    "governed_user_pt",
    "governed_page_tables_start",
    "governed_page_tables_end",
    "governed_page_table_root_physical",
    "observed_governed_cr3",
    "user_probe_code_start",
    "user_probe_code_end",
    "user_probe_data_start",
    "user_probe_data_end",
    "user_probe_stack",
    "user_probe_stack_top",
)
PRIVILEGE_TRANSITION_SYMBOLS = (
    "initialize_privilege_transition",
    "clear_privilege_transition_storage",
    "initialize_governed_tss",
    "initialize_governed_gdt",
    "populate_tss_descriptor",
    "load_governed_tss",
    "initialize_governed_idt",
    "set_idt_gate",
    "validate_privilege_transition_tables",
    "validate_privilege_return_gate",
    "validate_user_probe_entry",
    "enter_bounded_ring3_probe",
    "governed_gdt",
    "governed_gdt_end",
    "governed_tss",
    "governed_tss_end",
    "governed_idt",
    "governed_idt_end",
    "privilege_return_stack",
    "privilege_return_stack_top",
    "double_fault_stack",
    "double_fault_stack_top",
    "user_privilege_probe_start",
    "user_privilege_probe_end",
    "privilege_return_handler",
    "handle_fixed_user_request",
    "handle_fixed_user_response_consumption",
    "validate_ring3_request_frame",
    "validate_ring3_response_frame",
    "privilege_ring0_continuation",
    "privilege_fault_sink",
    "privilege_double_fault_sink",
    "observed_governed_gdtr",
    "observed_governed_idtr",
    "observed_task_register",
    "boot_terminal_halt",
)
FIXED_USER_REQUEST_SYMBOLS = (
    "user_privilege_probe_start",
    "privilege_return_handler",
    "handle_fixed_user_request",
    "handle_fixed_user_response_consumption",
    "validate_ring3_request_frame",
    "validate_fixed_user_buffer_ranges",
    "copy_fixed_user_request_in",
    "validate_fixed_user_request",
    "execute_fixed_user_boundary_service",
    "validate_fixed_user_response",
    "copy_fixed_user_response_out",
    "validate_fixed_user_response_readback",
    "clear_fixed_user_request_buffers",
    "fixed_user_buffers_are_zero",
    "privilege_ring0_continuation",
    "runtime_serial_write_user_request_copy_in_marker",
    "runtime_serial_write_user_request_service_marker",
    "runtime_serial_write_user_response_copy_out_marker",
    "runtime_serial_write_fixed_user_request_marker",
    "runtime_serial_write_ring3_probe_marker",
    "fixed_user_request_shadow",
    "fixed_user_request_shadow_end",
    "fixed_user_response_shadow",
    "fixed_user_response_shadow_end",
    "fixed_user_response_verify",
    "fixed_user_response_verify_end",
    "fixed_user_request_success_state",
)
BOUNDED_USER_RESPONSE_SYMBOLS = (
    "user_response_consumer_start",
    "user_response_consumer_interrupt_return",
    "user_response_consumer_end",
    "privilege_return_handler",
    "handle_fixed_user_request",
    "handle_fixed_user_response_consumption",
    "validate_ring3_response_frame",
    "prepare_user_response_resume",
    "resume_fixed_user_response_consumer",
    "validate_user_visible_response",
    "copy_fixed_user_consumption_record",
    "validate_fixed_user_consumption_record",
    "clear_fixed_user_response_transaction",
    "fixed_user_response_matches_shadow",
    "fixed_user_transaction_phase",
    "fixed_user_transaction_phase_end",
    "fixed_user_consumption_shadow",
    "fixed_user_consumption_shadow_end",
    "runtime_serial_write_ring3_response_resume_marker",
    "runtime_serial_write_user_response_consumed_marker",
    "runtime_serial_write_fixed_user_response_marker",
    "privilege_ring0_continuation",
)
FIXED_MAPPING_TRANSITION_MNEMONICS = {
    "iretq",
    "syscall",
    "sysret",
    "sysretq",
    "lgdt",
    "lidt",
    "ltr",
    "wrmsr",
}
AVX_MNEMONIC_PREFIXES = (
    "vadd",
    "vsub",
    "vmul",
    "vdiv",
    "vmov",
    "vxor",
    "vpxor",
    "vand",
    "vor",
    "vblend",
    "vbroadcast",
    "vextract",
    "vinsert",
    "vperm",
    "vshuf",
    "vzero",
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
            *CPU_EXTENDED_STATE_SYMBOLS,
            *RUNTIME_STATE_TRANSITION_SYMBOLS,
            *FIXED_USER_MAPPING_SYMBOLS,
            *PRIVILEGE_TRANSITION_SYMBOLS,
            *FIXED_USER_REQUEST_SYMBOLS,
            *BOUNDED_USER_RESPONSE_SYMBOLS,
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
        "cpu_extended_state_initialization": cpu_extended_state_record(kernel_elf, symbols),
        "runtime_state_transition_capability": runtime_state_transition_record(kernel_elf, symbols),
        "fixed_user_mapping_foundation": fixed_user_mapping_record(kernel_elf, symbols),
        "bounded_privilege_transition_probe": bounded_privilege_transition_record(kernel_elf, symbols),
        "fixed_user_request_boundary": fixed_user_request_boundary_record(kernel_elf, symbols),
        "bounded_user_response_consumption": bounded_user_response_consumption_record(kernel_elf, symbols),
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


def symbol_sizes(kernel_elf: Path, symbol_names: tuple[str, ...]) -> dict[str, int]:
    try:
        result = subprocess.run(["nm", "-S", str(kernel_elf)], check=False, capture_output=True, text=True)
    except OSError:
        return {}
    if result.returncode != 0:
        return {}
    return parse_symbol_sizes(result.stdout, set(symbol_names))


def parse_symbol_sizes(nm_output: str, symbol_names: set[str]) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for line in nm_output.splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[-1] not in symbol_names:
            continue
        try:
            sizes[parts[-1]] = int(parts[1], 16)
        except ValueError:
            continue
    return sizes


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


def cpu_extended_state_record(
    kernel_elf: Path,
    symbols: dict[str, int],
) -> dict[str, object]:
    all_instructions = parse_disassembly_instructions(run_text_command(["objdump", "-d", str(kernel_elf)]))
    instruction_sets = _cpu_instruction_sets(all_instructions, symbols)
    prohibited = prohibited_extended_state_instructions(all_instructions)
    return {
        "symbols": symbol_record(symbols, CPU_EXTENDED_STATE_SYMBOLS),
        "probe_buffer": _cpu_probe_buffer_record(symbols),
        "pre_odin_call_order_valid": _pre_odin_call_order_valid(instruction_sets["_start"], symbols),
        "initialization_call_chain_valid": _initialization_call_chain_valid(
            instruction_sets["initialize_cpu_extended_state"],
            symbols,
        ),
        "cpuid_present": _mnemonic_present(instruction_sets["required_cpu_features_available"], "cpuid"),
        "cr0_access_count": _register_access_count(instruction_sets, "cr0"),
        "cr4_access_count": _register_access_count(instruction_sets, "cr4"),
        "fninit_present": _mnemonic_present(instruction_sets["initialize_x87_state"], "fninit"),
        "fnstcw_present": _mnemonic_present(instruction_sets["initialize_x87_state"], "fnstcw"),
        "ldmxcsr_present": _mnemonic_present(instruction_sets["initialize_sse_state"], "ldmxcsr"),
        "stmxcsr_present": _mnemonic_present(instruction_sets["initialize_sse_state"], "stmxcsr"),
        "simd_probe_instruction_present": _mnemonic_present(
            instruction_sets["run_simd_survival_probe"],
            "pxor",
        ),
        "simd_probe_comparison_count": _mnemonic_count(
            instruction_sets["run_simd_survival_probe"],
            "cmp",
        ),
        "avx_prohibited_instruction_present": bool(prohibited),
        "prohibited_instructions": prohibited,
    }


def runtime_state_transition_record(
    kernel_elf: Path,
    symbols: dict[str, int],
) -> dict[str, object]:
    instruction_sets = {
        symbol: parse_disassembly_instructions(disassemble_symbol(kernel_elf, symbol))
        for symbol in RUNTIME_STATE_TRANSITION_SYMBOLS
        if symbol in symbols
    }
    progression = parse_disassembly_instructions(
        disassemble_symbol(kernel_elf, "runtime_progression_entry")
    )
    dispatcher = instruction_sets.get("dispatch_runtime_capability", [])
    handler = instruction_sets.get("transition_runtime_state", [])
    accessors = _state_accessor_instructions(instruction_sets)
    sizes = symbol_sizes(kernel_elf, ("runtime_state_transition_cell",))
    return {
        "symbols": symbol_record(symbols, RUNTIME_STATE_TRANSITION_SYMBOLS),
        "progression_call_present": _calls_address(
            progression,
            symbols.get("execute_second_governed_capability"),
        ),
        "dispatcher_route_present": _calls_address(
            dispatcher,
            symbols.get("dispatch_runtime_state_transition"),
        ),
        "handler_comparison_count": _mnemonic_count(handler, "cmp"),
        "volatile_memory_access_count": _memory_move_count(accessors),
        "state_cell_address": _hex(symbols["runtime_state_transition_cell"])
        if "runtime_state_transition_cell" in symbols
        else "",
        "state_cell_size_bytes": sizes.get("runtime_state_transition_cell", -1),
        "state_cell_required_size_bytes": 16,
        "state_cell_required_alignment_bytes": 8,
        "state_cell_aligned": (
            "runtime_state_transition_cell" in symbols
            and symbols["runtime_state_transition_cell"] % 8 == 0
        ),
    }


def fixed_user_mapping_record(
    kernel_elf: Path,
    symbols: dict[str, int],
) -> dict[str, object]:
    paging_instructions = [
        instruction
        for symbol in FIXED_USER_MAPPING_SYMBOLS[:5]
        for instruction in parse_disassembly_instructions(disassemble_symbol(kernel_elf, symbol))
    ]
    return {
        "symbols": symbol_record(symbols, FIXED_USER_MAPPING_SYMBOLS),
        "page_table_storage": _symbol_range_record(
            symbols,
            "governed_page_tables_start",
            "governed_page_tables_end",
            7 * 4096,
            4096,
        ),
        "user_regions": {
            "code": _symbol_range_record(
                symbols,
                "user_probe_code_start",
                "user_probe_code_end",
                4096,
                4096,
            ),
            "data": _symbol_range_record(
                symbols,
                "user_probe_data_start",
                "user_probe_data_end",
                4096,
                4096,
            ),
            "stack": _symbol_range_record(
                symbols,
                "user_probe_stack",
                "user_probe_stack_top",
                4096,
                4096,
            ),
        },
        "pre_odin_call_order_valid": _fixed_mapping_call_order_valid(kernel_elf, symbols),
        "cr3_read_present": any("cr3" in operands for _, _, operands in paging_instructions),
        "cr3_write_present": any(
            mnemonic.startswith("mov")
            and operands.replace(" ", "").startswith("%rax,%cr3")
            for _, mnemonic, operands in paging_instructions
        ),
        "software_walk_present": "walk_page_mapping" in symbols,
        "paging_module_transition_instructions": sorted(
            {
                mnemonic
                for _, mnemonic, _ in paging_instructions
                if mnemonic in FIXED_MAPPING_TRANSITION_MNEMONICS
            }
        ),
    }


def bounded_privilege_transition_record(
    kernel_elf: Path,
    symbols: dict[str, int],
) -> dict[str, object]:
    instruction_sets = {
        symbol: parse_disassembly_instructions(disassemble_symbol(kernel_elf, symbol))
        for symbol in PRIVILEGE_TRANSITION_SYMBOLS
        if symbol in symbols
    }
    return {
        "symbols": symbol_record(symbols, PRIVILEGE_TRANSITION_SYMBOLS),
        "gdt": _symbol_range_record(symbols, "governed_gdt", "governed_gdt_end", 56, 16),
        "tss": _symbol_range_record(symbols, "governed_tss", "governed_tss_end", 104, 16),
        "idt": _symbol_range_record(symbols, "governed_idt", "governed_idt_end", 4096, 4096),
        "return_stack": _symbol_range_record(
            symbols, "privilege_return_stack", "privilege_return_stack_top", 4096, 4096
        ),
        "double_fault_stack": _symbol_range_record(
            symbols, "double_fault_stack", "double_fault_stack_top", 4096, 4096
        ),
        "user_probe": _symbol_range_record(
            symbols,
            "user_privilege_probe_start",
            "user_privilege_probe_end",
            _symbol_delta(symbols, "user_privilege_probe_start", "user_privilege_probe_end"),
            1,
        ),
        "pre_odin_call_order_valid": _privilege_call_order_valid(kernel_elf, symbols),
        "lgdt_present": _instruction_present(instruction_sets, "lgdt"),
        "sgdt_present": _instruction_present(instruction_sets, "sgdt"),
        "ltr_present": _instruction_present(instruction_sets, "ltr"),
        "str_present": _instruction_present(instruction_sets, "str"),
        "lidt_present": _instruction_present(instruction_sets, "lidt"),
        "sidt_present": _instruction_present(instruction_sets, "sidt"),
        "iretq_present": _instruction_present(instruction_sets, "iretq"),
        "int_0x81_present": _int_vector_present(
            instruction_sets.get("user_privilege_probe_start", []),
            0x81,
        ),
        "handler_continuation_jump_present": _jumps_address(
            instruction_sets.get("handle_fixed_user_response_consumption", []),
            symbols.get("privilege_ring0_continuation"),
        ),
        "fault_halt_paths_present": _fault_halt_paths_present(instruction_sets, symbols),
        "prohibited_instructions": _privilege_prohibited_instructions(instruction_sets),
    }


def fixed_user_request_boundary_record(
    kernel_elf: Path,
    symbols: dict[str, int],
) -> dict[str, object]:
    instruction_sets = {
        symbol: parse_disassembly_instructions(disassemble_symbol(kernel_elf, symbol))
        for symbol in (
            "user_privilege_probe_start",
            "handle_fixed_user_request",
            "handle_fixed_user_response_consumption",
            "copy_fixed_user_request_in",
            "validate_fixed_user_request",
            "execute_fixed_user_boundary_service",
            "validate_fixed_user_response",
            "copy_fixed_user_response_out",
            "validate_fixed_user_response_readback",
            "clear_fixed_user_request_buffers",
        )
        if symbol in symbols
    }
    handler = instruction_sets.get("handle_fixed_user_request", [])
    response_handler = instruction_sets.get("handle_fixed_user_response_consumption", [])
    ring3_probe = instruction_sets.get("user_privilege_probe_start", [])
    return {
        "symbols": symbol_record(symbols, FIXED_USER_REQUEST_SYMBOLS),
        "request_shadow": _symbol_range_record(
            symbols,
            "fixed_user_request_shadow",
            "fixed_user_request_shadow_end",
            40,
            8,
        ),
        "response_shadow": _symbol_range_record(
            symbols,
            "fixed_user_response_shadow",
            "fixed_user_response_shadow_end",
            48,
            8,
        ),
        "response_verify": _symbol_range_record(
            symbols,
            "fixed_user_response_verify",
            "fixed_user_response_verify_end",
            48,
            8,
        ),
        "ring3_request_store_count": _memory_store_count(ring3_probe),
        "ring3_return_interrupt_present": _int_vector_present(ring3_probe, 0x81),
        "handler_call_order_valid": _ordered_call_targets_present(
            handler,
            tuple(
                symbols.get(name)
                for name in (
                    "validate_ring3_request_frame",
                    "validate_fixed_user_buffer_ranges",
                    "copy_fixed_user_request_in",
                    "validate_fixed_user_request",
                    "runtime_serial_write_user_request_copy_in_marker",
                    "execute_fixed_user_boundary_service",
                    "validate_fixed_user_response",
                    "runtime_serial_write_user_request_service_marker",
                    "copy_fixed_user_response_out",
                    "validate_fixed_user_response_readback",
                    "runtime_serial_write_user_response_copy_out_marker",
                    "prepare_user_response_resume",
                    "runtime_serial_write_ring3_response_resume_marker",
                )
            ),
        ),
        "copy_in_memory_move_count": _memory_move_count(
            instruction_sets.get("copy_fixed_user_request_in", [])
        ),
        "copy_out_memory_move_count": _memory_move_count(
            instruction_sets.get("copy_fixed_user_response_out", [])
        ),
        "readback_memory_move_count": _memory_move_count(
            instruction_sets.get("validate_fixed_user_response_readback", [])
        ),
        "clear_memory_move_count": _memory_move_count(
            instruction_sets.get("clear_fixed_user_request_buffers", [])
        ),
        "clear_stosq_count": _rep_stosq_count(
            instruction_sets.get("clear_fixed_user_request_buffers", [])
        ),
        "post_clear_zero_validation_present": _calls_address(
            instruction_sets.get("clear_fixed_user_request_buffers", []),
            symbols.get("fixed_user_buffers_are_zero"),
        ),
        "fixed_continuation_jump_present": _jumps_address(
            response_handler,
            symbols.get("privilege_ring0_continuation"),
        ),
        "prohibited_boundary_instructions": _fixed_user_request_prohibited_instructions(
            instruction_sets
        ),
    }


def bounded_user_response_consumption_record(
    kernel_elf: Path,
    symbols: dict[str, int],
) -> dict[str, object]:
    all_instructions = parse_disassembly_instructions(
        run_text_command(["objdump", "-d", str(kernel_elf)])
    )
    instruction_sets = {
        symbol: _instructions_for_symbol(all_instructions, symbol, symbols)
        for symbol in BOUNDED_USER_RESPONSE_SYMBOLS
        if symbol in symbols
    }
    consumer = instruction_sets.get("user_response_consumer_start", [])
    first_handler = instruction_sets.get("handle_fixed_user_request", [])
    second_handler = instruction_sets.get("handle_fixed_user_response_consumption", [])
    resume = instruction_sets.get("resume_fixed_user_response_consumer", [])
    record_copy = instruction_sets.get("copy_fixed_user_consumption_record", [])
    clearing = instruction_sets.get("clear_fixed_user_response_transaction", [])
    return {
        "symbols": symbol_record(symbols, BOUNDED_USER_RESPONSE_SYMBOLS),
        "transaction_phase": _symbol_range_record(
            symbols,
            "fixed_user_transaction_phase",
            "fixed_user_transaction_phase_end",
            8,
            8,
        ),
        "consumption_shadow": _symbol_range_record(
            symbols,
            "fixed_user_consumption_shadow",
            "fixed_user_consumption_shadow_end",
            48,
            8,
        ),
        "consumer_inside_user_page": _symbol_range_contains(
            symbols,
            "user_probe_code_start",
            "user_probe_code_end",
            "user_response_consumer_start",
            "user_response_consumer_end",
        ),
        "consumer_response_compare_count": _comparison_count(consumer),
        "consumer_record_store_count": _memory_store_count(consumer),
        "consumer_second_interrupt_present": _int_vector_present(consumer, 0x81),
        "resume_iretq_present": _mnemonic_present(resume, "iretq"),
        "total_iretq_count": _mnemonic_count(all_instructions, "iretq"),
        "initial_interrupt_present": _int_vector_present(
            _instructions_for_symbol(all_instructions, "user_privilege_probe_start", symbols),
            0x81,
        ),
        "first_handler_resume_call_order_valid": _ordered_call_targets_present(
            first_handler,
            tuple(
                symbols.get(name)
                for name in (
                    "prepare_user_response_resume",
                    "runtime_serial_write_ring3_response_resume_marker",
                )
            ),
        ),
        "second_handler_call_order_valid": _ordered_call_targets_present(
            second_handler,
            tuple(
                symbols.get(name)
                for name in (
                    "validate_ring3_response_frame",
                    "validate_user_visible_response",
                    "copy_fixed_user_consumption_record",
                    "validate_fixed_user_consumption_record",
                    "runtime_serial_write_user_response_consumed_marker",
                    "clear_fixed_user_response_transaction",
                    "runtime_serial_write_fixed_user_response_marker",
                    "runtime_serial_write_fixed_user_request_marker",
                    "runtime_serial_write_ring3_probe_marker",
                )
            ),
        ),
        "record_copy_memory_move_count": _memory_move_count(record_copy),
        "response_revalidation_compare_count": _comparison_count(
            instruction_sets.get("fixed_user_response_matches_shadow", [])
        ),
        "response_clear_stosq_count": _rep_stosq_count(clearing),
        "response_clear_zero_validation_present": _calls_address(
            clearing,
            symbols.get("fixed_user_buffers_are_zero"),
        ),
        "fixed_continuation_jump_present": _jumps_address(
            second_handler,
            symbols.get("privilege_ring0_continuation"),
        ),
        "prohibited_instructions": _fixed_user_request_prohibited_instructions(
            instruction_sets
        ),
    }
def _symbol_delta(symbols: dict[str, int], start_name: str, end_name: str) -> int:
    start = symbols.get(start_name)
    end = symbols.get(end_name)
    return end - start if start is not None and end is not None else -1


def _symbol_range_contains(
    symbols: dict[str, int],
    outer_start_name: str,
    outer_end_name: str,
    inner_start_name: str,
    inner_end_name: str,
) -> bool:
    values = tuple(
        symbols.get(name)
        for name in (
            outer_start_name,
            outer_end_name,
            inner_start_name,
            inner_end_name,
        )
    )
    if any(value is None for value in values):
        return False
    outer_start, outer_end, inner_start, inner_end = values
    return outer_start <= inner_start < inner_end <= outer_end


def _comparison_count(instructions) -> int:
    return sum(
        mnemonic.startswith("cmp") or mnemonic.startswith("test")
        for _, mnemonic, _ in instructions
    )


def _privilege_call_order_valid(kernel_elf: Path, symbols: dict[str, int]) -> bool:
    all_instructions = parse_disassembly_instructions(
        run_text_command(["objdump", "-d", str(kernel_elf)])
    )
    instructions = _instructions_for_symbol(all_instructions, "_start", symbols)
    required = (
        symbols.get("initialize_privilege_transition"),
        symbols.get("enter_bounded_ring3_probe"),
        symbols.get("runtime_progression_entry"),
    )
    return _ordered_call_targets_present(instructions, required)


def _instruction_present(instruction_sets, mnemonic: str) -> bool:
    return any(
        candidate.startswith(mnemonic)
        for instructions in instruction_sets.values()
        for _, candidate, _ in instructions
    )


def _int_vector_present(instructions, vector: int) -> bool:
    return any(
        mnemonic == "int" and f"0x{vector:x}" in operands.lower()
        for _, mnemonic, operands in instructions
    )


def _jumps_address(instructions, target_address: int | None) -> bool:
    if target_address is None:
        return False
    return any(
        mnemonic.startswith("jmp") and instruction_target(operands) == target_address
        for _, mnemonic, operands in instructions
    )


def _fault_halt_paths_present(instruction_sets, symbols: dict[str, int]) -> bool:
    target = symbols.get("boot_terminal_halt")
    return all(
        _jumps_address(instruction_sets.get(name, []), target)
        for name in ("privilege_fault_sink", "privilege_double_fault_sink")
    )


def _privilege_prohibited_instructions(instruction_sets) -> list[str]:
    prohibited = {"syscall", "sysret", "sysretq", "swapgs", "sti", "wrmsr"}
    return sorted(
        {
            mnemonic
            for instructions in instruction_sets.values()
            for _, mnemonic, _ in instructions
            if mnemonic in prohibited
        }
    )


def _symbol_range_record(
    symbols: dict[str, int],
    start_symbol: str,
    end_symbol: str,
    required_size: int,
    required_alignment: int,
) -> dict[str, object]:
    start = symbols.get(start_symbol)
    end = symbols.get(end_symbol)
    size = end - start if start is not None and end is not None else -1
    return {
        "start_symbol": start_symbol,
        "end_symbol": end_symbol,
        "start_address": _hex(start) if start is not None else "",
        "end_address": _hex(end) if end is not None else "",
        "size_bytes": size,
        "required_size_bytes": required_size,
        "required_alignment_bytes": required_alignment,
        "start_aligned": start is not None and start % required_alignment == 0,
    }


def _fixed_mapping_call_order_valid(
    kernel_elf: Path,
    symbols: dict[str, int],
) -> bool:
    all_instructions = parse_disassembly_instructions(
        run_text_command(["objdump", "-d", str(kernel_elf)])
    )
    instructions = _instructions_for_symbol(all_instructions, "_start", symbols)
    targets = [
        instruction_target(operands)
        for _, mnemonic, operands in instructions
        if mnemonic.startswith("call")
    ]
    required = (
        symbols.get("initialize_fixed_user_mapping_tables"),
        symbols.get("validate_fixed_user_mapping_policy"),
        symbols.get("activate_fixed_user_mapping_root"),
        symbols.get("run_fixed_user_mapping_survival_probe"),
        symbols.get("runtime_progression_entry"),
    )
    if any(target is None for target in required):
        return False
    position = -1
    for target in required:
        try:
            position = targets.index(target, position + 1)
        except ValueError:
            return False
    return True


def _state_accessor_instructions(instruction_sets):
    names = (
        "runtime_state_cell_store",
        "runtime_state_cell_state",
        "runtime_state_cell_reserved",
        "runtime_state_cell_generation",
    )
    return [
        instruction
        for name in names
        for instruction in instruction_sets.get(name, [])
    ]


def _memory_move_count(instructions) -> int:
    return sum(
        mnemonic.startswith("mov") and ("(" in operands or "[" in operands)
        for _, mnemonic, operands in instructions
    )


def _memory_store_count(instructions) -> int:
    return sum(
        mnemonic.startswith("mov")
        and "," in operands
        and ("(" in operands.rsplit(",", 1)[-1] or "[" in operands.rsplit(",", 1)[-1])
        for _, mnemonic, operands in instructions
    )


def _rep_stosq_count(instructions) -> int:
    return sum(
        mnemonic == "rep" and _is_qword_stos(operands)
        for _, mnemonic, operands in instructions
    )


def _is_qword_stos(operands: str) -> bool:
    normalized = operands.lstrip()
    if normalized.startswith("stosq"):
        return True
    return (
        normalized.startswith("stos ")
        and "%rax" in normalized
        and "%rdi" in normalized
    )


def _fixed_user_request_prohibited_instructions(instruction_sets) -> list[str]:
    prohibited = {"syscall", "sysret", "sysretq", "swapgs", "sti", "wrmsr"}
    return sorted(
        {
            mnemonic
            for instructions in instruction_sets.values()
            for _, mnemonic, _ in instructions
            if mnemonic in prohibited
        }
    )


def _cpu_instruction_sets(all_instructions, symbol_addresses) -> dict[str, list[tuple[int, str, str]]]:
    symbol_names = ("_start", *CPU_EXTENDED_STATE_SYMBOLS[:7])
    return {
        symbol: _instructions_for_symbol(all_instructions, symbol, symbol_addresses)
        for symbol in symbol_names
        if symbol in symbol_addresses
    }


def _instructions_for_symbol(all_instructions, symbol: str, symbol_addresses):
    start = symbol_addresses[symbol]
    later = [address for address in symbol_addresses.values() if address > start]
    end = min(later) if later else None
    return [
        instruction
        for instruction in all_instructions
        if instruction[0] >= start and (end is None or instruction[0] < end)
    ]


def _cpu_probe_buffer_record(symbols: dict[str, int]) -> dict[str, object]:
    start = symbols.get("simd_probe_result")
    end = symbols.get("simd_probe_result_end")
    size = end - start if start is not None and end is not None else -1
    return {
        "start_address": _hex(start) if start is not None else "",
        "end_address": _hex(end) if end is not None else "",
        "size_bytes": size,
        "required_alignment_bytes": 16,
        "start_aligned": start is not None and start % 16 == 0,
    }


def _pre_odin_call_order_valid(instructions, symbols: dict[str, int]) -> bool:
    targets = (
        symbols.get("initialize_cpu_extended_state"),
        symbols.get("run_simd_survival_probe"),
        symbols.get("runtime_progression_entry"),
    )
    return _ordered_call_targets_present(instructions, targets)


def _initialization_call_chain_valid(instructions, symbols: dict[str, int]) -> bool:
    targets = tuple(symbols.get(name) for name in CPU_EXTENDED_STATE_SYMBOLS[1:6])
    return _ordered_call_targets_present(instructions, targets)


def _ordered_call_targets_present(instructions, targets: tuple[int | None, ...]) -> bool:
    if any(target is None for target in targets):
        return False
    calls = [
        instruction_target(operands)
        for _, mnemonic, operands in instructions
        if mnemonic.startswith("call")
    ]
    position = -1
    for target in targets:
        try:
            position = calls.index(target, position + 1)
        except ValueError:
            return False
    return True


def _register_access_count(instruction_sets, register: str) -> int:
    return sum(
        register in operands.lower()
        for instructions in instruction_sets.values()
        for _, mnemonic, operands in instructions
        if mnemonic.startswith("mov")
    )


def _mnemonic_present(instructions, mnemonic: str) -> bool:
    return _mnemonic_count(instructions, mnemonic) > 0


def _mnemonic_count(instructions, mnemonic: str) -> int:
    return sum(candidate.startswith(mnemonic) for _, candidate, _ in instructions)


def prohibited_extended_state_instructions(
    instructions: list[tuple[int, str, str]],
) -> list[dict[str, str]]:
    return [
        {"address": _hex(address), "mnemonic": mnemonic, "operands": operands.strip()}
        for address, mnemonic, operands in instructions
        if _is_prohibited_extended_state_instruction(mnemonic, operands)
    ]


def _is_prohibited_extended_state_instruction(mnemonic: str, operands: str) -> bool:
    lowered_operands = operands.lower()
    if mnemonic == "xsetbv":
        return True
    if re.search(r"\b(?:ymm|zmm)[0-9]+\b", lowered_operands):
        return True
    return mnemonic.startswith(AVX_MNEMONIC_PREFIXES)


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
        "cpu_extended_state_initialization": cpu_extended_state_record(kernel_elf, {}),
        "runtime_state_transition_capability": runtime_state_transition_record(kernel_elf, {}),
        "fixed_user_mapping_foundation": fixed_user_mapping_record(kernel_elf, {}),
        "bounded_privilege_transition_probe": bounded_privilege_transition_record(kernel_elf, {}),
        "fixed_user_request_boundary": fixed_user_request_boundary_record(kernel_elf, {}),
        "bounded_user_response_consumption": bounded_user_response_consumption_record(kernel_elf, {}),
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
