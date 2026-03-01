// File Path: kernel/src/memory/vmm.zig
// Last Modified: 2026-02-28, 23:15:10.402
// Note: Virtual Memory Manager - Implements Recursive Paging & Capability Mapping.

const std = @import("std");
const pmm = @import("pmm.zig");

/// Recursive Slot 510. This gives us a virtual address range to manage tables.
/// The PML4[510] points back to the PML4's physical address.
pub const RECURSIVE_SLOT: u64 = 510;

/// Virtual base address for accessing the page tables via recursive mapping.
pub const VMM_BASE: u64 = 0xFFFF000000000000 | (RECURSIVE_SLOT << 39);

pub const PageFlags = struct {
    pub const Present: u64 = 1 << 0;
    pub const Write: u64 = 1 << 1;
    pub const User: u64 = 1 << 2;
    pub const WriteThrough: u64 = 1 << 3;
    pub const CacheDisable: u64 = 1 << 4;
    pub const Accessed: u64 = 1 << 5;
    pub const Dirty: u64 = 1 << 6;
    pub const HugePage: u64 = 1 << 7;
    pub const Global: u64 = 1 << 8;
    pub const NoExecute: u64 = 1 << 63;
};

pub const VMM_ERROR_FAILED = error{MappingFailed, TableAllocationFailed};

/// Map a physical frame to a virtual address in the current address space.
pub fn mapPage(virt: u64, phys: u64, flags: u64) !void {
    const l4_idx = (virt >> 39) & 0x1FF;
    const l3_idx = (virt >> 30) & 0x1FF;
    const l2_idx = (virt >> 21) & 0x1FF;
    const l1_idx = (virt >> 12) & 0x1FF;

    // Ensure the tree structure exists by allocating missing tables.
    try ensureTable(l4_idx, l3_idx, l2_idx);

    // Get a pointer to the level 1 page table using recursive addresses.
    const pt: [*]u64 = @ptrFromInt(getTableAddress(l4_idx, l3_idx, l2_idx));
    
    // Set the entry
    pt[l1_idx] = (phys & 0x000FFFFFFFFFF000) | flags | PageFlags.Present;
    
    // Invalidate the TLB for this specific address
    asm volatile ("invlpg (%[addr])" : : [addr] "r" (virt) : "memory");
}

/// Ensure that the intermediate page tables (PDPT, PD) exist for a given virtual path.
/// If they don't exist, we allocate frames from PMM and map them into the hierarchy.
fn ensureTable(l4: u64, l3: u64, l2: u64) !void {
    // 1. Check PML4 entry for PDPT
    const pml4: [*]u64 = @ptrFromInt(VMM_BASE + (RECURSIVE_SLOT << 30) + (RECURSIVE_SLOT << 21) + (RECURSIVE_SLOT << 12));
    if (pml4[l4] & PageFlags.Present == 0) {
        const frame = try pmm.allocFrame();
        pml4[l4] = frame | PageFlags.Present | PageFlags.Write | PageFlags.User;
        // Zero the new table. We access it via the recursive PT address for this specific slot.
        const new_table: [*]u64 = @ptrFromInt(getTableAddress(RECURSIVE_SLOT, RECURSIVE_SLOT, l4));
        @memset(@as([*]u8, @ptrCast(new_table))[0..4096], 0);
    }

    // 2. Check PDPT entry for PD
    const pdpt: [*]u64 = @ptrFromInt(getTableAddress(RECURSIVE_SLOT, RECURSIVE_SLOT, l4));
    if (pdpt[l3] & PageFlags.Present == 0) {
        const frame = try pmm.allocFrame();
        pdpt[l3] = frame | PageFlags.Present | PageFlags.Write | PageFlags.User;
        const new_table: [*]u64 = @ptrFromInt(getTableAddress(RECURSIVE_SLOT, l4, l3));
        @memset(@as([*]u8, @ptrCast(new_table))[0..4096], 0);
    }

    // 3. Check PD entry for PT
    const pd: [*]u64 = @ptrFromInt(getTableAddress(RECURSIVE_SLOT, l4, l3));
    if (pd[l2] & PageFlags.Present == 0) {
        const frame = try pmm.allocFrame();
        pd[l2] = frame | PageFlags.Present | PageFlags.Write | PageFlags.User;
        const new_table: [*]u64 = @ptrFromInt(getTableAddress(l4, l3, l2));
        @memset(@as([*]u8, @ptrCast(new_table))[0..4096], 0);
    }
}

/// Calculate the virtual address used to access a specific page table (Level 1)
/// based on the recursive mapping logic.
fn getTableAddress(l4: u64, l3: u64, l2: u64) u64 {
    // Correct recursive addressing for x86_64:
    // To reach a level 1 page table, we use the recursive slot as the PML4 index.
    return VMM_BASE | (l4 << 30) | (l3 << 21) | (l2 << 12);
}

/// Initialize the VMM. 
/// In Genesis, this involves taking over the PML4 set up by the loader
/// and installing the recursive slot.
pub fn init(pml4_phys: u64) void {
    // The loader should have already mapped the kernel and set up a basic PML4.
    // We access the current PML4 (physically) and write the recursive entry.
    // NOTE: This assumes we are still identity mapped or have a way to 
    // access physical memory directly temporarily.
    const pml4: [*]u64 = @ptrFromInt(pml4_phys);
    pml4[RECURSIVE_SLOT] = pml4_phys | PageFlags.Present | PageFlags.Write;
}
