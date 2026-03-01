//! File Path: kernel/src/memory/pmm.zig
//! Last Modified: 2026-02-28, 22:55:12.880
//! KOZO Kernel - Physical Memory Manager (PMM)
//! Responsibility: UEFI-integrated Bitmap PMM. Tracks 4KB frames across physical RAM.

const std = @import("std");
const BootInfo = @import("../../common/boot_info.zig").BootInfo;

/// Memory Descriptor from UEFI spec
pub const MemoryDescriptor = extern struct {
    type: u32,
    pad: u32,
    physical_start: u64,
    virtual_start: u64,
    number_of_pages: u64,
    attribute: u64,
};

pub const MemoryType = enum(u32) {
    ReservedMemoryType = 0,
    LoaderCode = 1,
    LoaderData = 2,
    BootServicesCode = 3,
    BootServicesData = 4,
    RuntimeServicesCode = 5,
    RuntimeServicesData = 6,
    ConventionalMemory = 7,
    UnusableMemory = 8,
    ACPIReclaimMemory = 9,
    ACPIMemoryNVS = 10,
    MemoryMappedIO = 11,
    MemoryMappedIOPortSpace = 12,
    PalCode = 13,
    PersistentMemory = 14,
    MaxMemoryType = 15,
};

pub const PMM_ERROR_NO_MEM = error{OutOfMemory};

var bitmap: []u8 = &[_]u8{};
var total_pages: usize = 0;
var free_pages: usize = 0;

/// Initialize the PMM using the UEFI Memory Map.
/// We find the largest ConventionalMemory region and place our bitmap there.
pub fn init(info: *const BootInfo) void {
    // Note: The descriptor_size is key here because UEFI descriptors 
    // can be larger than our struct due to future spec versions.
    const mmap_entries = info.memory_map_size / info.descriptor_size;
    
    // 1. Calculate max physical address to determine total pages needed.
    var max_addr: u64 = 0;
    var i: usize = 0;
    while (i < mmap_entries) : (i += 1) {
        const desc = getDescriptor(info, i);
        const end = desc.physical_start + (desc.number_of_pages * 4096);
        if (end > max_addr) max_addr = end;
    }
    
    total_pages = max_addr / 4096;
    const bitmap_size = (total_pages + 7) / 8;
    
    // 2. Find a suitable place for the bitmap.
    // We look for a ConventionalMemory block large enough to hold our bitmap.
    var bitmap_addr: u64 = 0;
    i = 0;
    while (i < mmap_entries) : (i += 1) {
        const desc = getDescriptor(info, i);
        if (desc.type == @intFromEnum(MemoryType.ConventionalMemory)) {
            const size = desc.number_of_pages * 4096;
            if (size >= bitmap_size) {
                bitmap_addr = desc.physical_start;
                break;
            }
        }
    }
    
    if (bitmap_addr == 0) {
        @panic("PMM: Could not find memory for bitmap");
    }

    // 3. Setup the bitmap slice
    bitmap = @as([*]u8, @ptrFromInt(bitmap_addr))[0..bitmap_size];
    @memset(bitmap, 0xFF); // Mark all as reserved initially

    // 4. Mark ConventionalMemory regions as FREE (0)
    i = 0;
    while (i < mmap_entries) : (i += 1) {
        const desc = getDescriptor(info, i);
        if (desc.type == @intFromEnum(MemoryType.ConventionalMemory)) {
            const start_page = desc.physical_start / 4096;
            var p: usize = 0;
            while (p < desc.number_of_pages) : (p += 1) {
                markFree(start_page + p);
                free_pages += 1;
            }
        }
    }

    // 5. Reserve pages used by the bitmap itself
    const bitmap_page_count = (bitmap_size + 4095) / 4096;
    const bitmap_start_page = bitmap_addr / 4096;
    var p: usize = 0;
    while (p < bitmap_page_count) : (p += 1) {
        markUsed(bitmap_start_page + p);
        free_pages -= 1;
    }
}

/// Helper to safely index the UEFI memory map using the provided descriptor size.
fn getDescriptor(info: *const BootInfo, index: usize) *const MemoryDescriptor {
    const ptr = info.memory_map_addr + (index * info.descriptor_size);
    return @ptrFromInt(ptr);
}

/// Allocate a single 4KB frame.
pub fn allocFrame() !u64 {
    var i: usize = 0;
    while (i < bitmap.len) : (i += 1) {
        if (bitmap[i] != 0xFF) {
            var b: u3 = 0;
            while (b < 8) : (b += 1) {
                const mask = @as(u8, 1) << b;
                if (bitmap[i] & mask == 0) {
                    const page = (i * 8) + b;
                    markUsed(page);
                    free_pages -= 1;
                    return @as(u64, page) * 4096;
                }
            }
        }
    }
    return PMM_ERROR_NO_MEM;
}

/// Free a previously allocated frame.
pub fn freeFrame(phys: u64) void {
    const page = phys / 4096;
    if (page >= total_pages) return;
    markFree(page);
    free_pages += 1;
}

fn markUsed(page: usize) void {
    bitmap[page / 8] |= @as(u8, 1) << @as(u3, @truncate(page % 8));
}

fn markFree(page: usize) void {
    bitmap[page / 8] &= ~(@as(u8, 1) << @as(u3, @truncate(page % 8)));
}

pub fn getFreePages() usize {
    return free_pages;
}
