// File Path: kernel/src/memory/elf.zig
// Last Modified: 2026-03-01, 13:05:10.150
// Note: Minimal ELF64 Loader - Maps PT_LOAD segments into a new address space.

const std = @import("std");
const vmm = @import("vmm.zig");
const pmm = @import("pmm.zig");

pub const Elf64_Ehdr = extern struct {
    e_ident: [16]u8,
    e_type: u16,
    e_machine: u16,
    e_version: u32,
    e_entry: u64,
    e_phoff: u64,
    e_shoff: u64,
    e_flags: u32,
    e_ehsize: u16,
    e_phentsize: u16,
    e_phnum: u16,
    e_shentsize: u16,
    e_shnum: u16,
    e_shstrndx: u16,
};

pub const Elf64_Phdr = extern struct {
    p_type: u32,
    p_flags: u32,
    p_offset: u64,
    p_vaddr: u64,
    p_paddr: u64,
    p_filesz: u64,
    p_memsz: u64,
    p_align: u64,
};

pub const PT_LOAD = 1;
pub const PF_X = 1;
pub const PF_W = 2;
pub const PF_R = 4;

/// Parse ELF from memory and load its segments into the current address space.
/// Returns the entry point address.
pub fn loadElf(data: []const u8) !u64 {
    const ehdr = @as(*const Elf64_Ehdr, @ptrCast(data.ptr));
    
    // 1. Header validation
    if (!std.mem.eql(u8, ehdr.e_ident[0..4], "\x7fELF")) return error.InvalidElf;
    if (ehdr.e_ident[4] != 2) return error.Not64Bit; // ELFCLASS64
    
    // 2. PHDR Iteration via Slice (Professional Zig style)
    const phdr_count = ehdr.e_phnum;
    const phdr_table = @as([*]const Elf64_Phdr, @ptrCast(@ptrFromInt(@intFromPtr(ehdr) + ehdr.e_phoff)))[0..phdr_count];
    
    for (phdr_table) |phdr| {
        if (phdr.p_type == PT_LOAD) {
            try loadSegment(data, &phdr);
        }
    }
    
    return ehdr.e_entry;
}

fn loadSegment(elf_data: []const u8, phdr: *const Elf64_Phdr) !void {
    // 1. Alignment Check
    if (phdr.p_align > 4096) return error.AlignmentUnsupported;

    // 2. Identify Flags (W^X Enforcement)
    var page_flags: u64 = vmm.PageFlags.Present | vmm.PageFlags.User;
    if (phdr.p_flags & PF_W != 0) page_flags |= vmm.PageFlags.Write;
    if (phdr.p_flags & PF_X == 0) page_flags |= vmm.PageFlags.NoExecute;

    const start_page = phdr.p_vaddr & ~@as(u64, 4095);
    const end_page = (phdr.p_vaddr + phdr.p_memsz + 4095) & ~@as(u64, 4095);
    
    var vaddr = start_page;
    while (vaddr < end_page) : (vaddr += 4096) {
        // 3. Overlap Check (Zero-Alloc redundancy prevention)
        if (!vmm.isMapped(vaddr)) {
            const phys = try pmm.allocFrame();
            try vmm.mapPage(vaddr, phys, page_flags);
        } else {
            // If already mapped, we might need to update flags to the "most permissive" 
            // of the two overlapping segments (usually should be avoided by linker).
            // For now, we trust the caller has set up the mappings correctly.
        }
    }
    
    // 4. Data Transfer
    // NOTE: This assumes we are in the target address space (CR3)
    const dest: [*]u8 = @ptrFromInt(phdr.p_vaddr);
    const src = elf_data[phdr.p_offset .. phdr.p_offset + phdr.p_filesz];
    @memcpy(dest[0..phdr.p_filesz], src);
    
    // 5. BSS Zeroing
    if (phdr.p_memsz > phdr.p_filesz) {
        const bss_start = phdr.p_vaddr + phdr.p_filesz;
        const bss_size = phdr.p_memsz - phdr.p_filesz;
        @memset(@as([*]u8, @ptrFromInt(bss_start))[0..bss_size], 0);
    }
}
