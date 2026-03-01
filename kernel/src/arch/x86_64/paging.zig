// File Path: kernel/src/arch/x86_64/paging.zig
// Last Modified: 2026-02-28, 22:50:04.125
const std = @import("std");

/// Recursive Paging Index
/// If we map the last entry of the PML4 to itself, 
/// the page tables appear at this virtual address.
pub const RECURSIVE_SLOT = 510;
pub const RECURSIVE_BASE: u64 = 0xFFFF000000000000 | (RECURSIVE_SLOT << 39);

pub fn getCurrentPml4() *[512]u64 {
    var cr3: u64 = undefined;
    asm volatile ("mov %%cr3, %[cr3]" : [cr3] "=r" (cr3));
    // Note: In a higher-half kernel, you'd return the virtual mapping
    return @ptrFromInt(cr3 & 0xFFFFFFFFFFFFF000);
}

pub fn invlpg(addr: u64) void {
    asm volatile ("invlpg (%[addr])" : : [addr] "r" (addr) : "memory");
}