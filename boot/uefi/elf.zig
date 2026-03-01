// File Path: boot/uefi/elf.zig
// Last Modified: 2026-02-28, 21:55:04.112
// Description: ELF64 Parser for UEFI Loader. Handles Physical LMA (AT) vs Virtual VMA mapping.
//
const std = @import("std");

/// ELF64 Header Constants
pub const ELF_MAGIC = "\x7fELF";
pub const PT_LOAD = 1;

/// Standard ELF64 Header
pub const Elf64_Ehdr = struct {
    ident: [16]u8,
    type: u16,
    machine: u16,
    version: u32,
    entry: u64,
    phoff: u64,
    shoff: u64,
    flags: u32,
    ehsize: u16,
    phentsize: u16,
    phnum: u16,
    shentsize: u16,
    shnum: u16,
    shstrndx: u16,
};

/// ELF64 Program Header (Segments)
pub const Elf64_Phdr = struct {
    type: u32,
    flags: u32,
    offset: u64,
    vaddr: u64,   // Virtual Memory Address (VMA) - e.g., 0xffffffff80000000
    paddr: u64,   // Physical Load Address (LMA) - e.g., 0x400000 (Set by 'AT' in linker)
    filesz: u64,  // Size in the file
    memsz: u64,   // Size in memory (includes BSS)
    align_val: u64,
};

/// Errors for ELF Loading
pub const ElfError = error{
    InvalidMagic,
    Not64Bit,
    NotExecutable,
    InvalidSegment,
};

/// loadElf parses the raw ELF data and copies PT_LOAD segments to their physical 
/// destinations (LMA). It returns the virtual entry point of the kernel.
pub fn loadElf(data: []const u8) ElfError!u64 {
    const header = @as(*const Elf64_Ehdr, @ptrCast(data.ptr));

    // 1. Sanity Checks
    if (!std.mem.eql(u8, header.ident[0..4], ELF_MAGIC)) return error.InvalidMagic;
    if (header.ident[4] != 2) return error.Not64Bit; // 2 = 64-bit
    if (header.type != 2) return error.NotExecutable; // 2 = ET_EXEC

    // 2. Iterate Program Headers
    var i: usize = 0;
    while (i < header.phnum) : (i += 1) {
        const offset = header.phoff + (i * header.phentsize);
        const phdr = @as(*const Elf64_Phdr, @ptrCast(&data[offset]));

        // We only care about Loadable segments
        if (phdr.type == PT_LOAD) {
            // The Physical Destination (LMA) is defined in phdr.paddr 
            // thanks to the 'AT' command in our linker script.
            const dest_phys: [*]u8 = @ptrFromInt(phdr.paddr);
            
            // The Source is inside the raw ELF file data we read from disk
            const src = data[phdr.offset .. phdr.offset + phdr.filesz];

            // Copy initialized data (.text, .data, .rodata)
            @memcpy(dest_phys[0..phdr.filesz], src);

            // Handle BSS: If memory size > file size, zero out the remainder
            if (phdr.memsz > phdr.filesz) {
                const bss_start = dest_phys + phdr.filesz;
                const bss_size = phdr.memsz - phdr.filesz;
                @memset(bss_start[0..bss_size], 0);
            }
        }
    }

    // 3. Return the Entry Point (VMA)
    // The UEFI loader will jump here after switching to the Higher-Half Page Tables.
    return header.entry;
}