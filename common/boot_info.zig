// File Path: common/boot_info.zig
// Last Modified: 2026-02-28, 22:30:15.420
// Note: RESTORED - The "Sacred Contract" between UEFI Loader and KOZO Kernel.
const std = @import("std");

/// BootInfo: The immutable state passed from the UEFI environment to the Kernel.
/// Aligned for 64-bit access to prevent padding issues between Zig and Rust services.
pub const BootInfo = struct {
    // --- Graphics (GOP) ---
    fb_base: u64,
    fb_size: u64,
    width: u32,
    height: u32,
    pitch: u32,

    // --- Memory Map ---
    memory_map_addr: u64,
    memory_map_size: u64,
    descriptor_size: u64,

    // --- System Tables ---
    rsdp_phys: u64, // ACPI Root Pointer
};