// File Path: kernel/src/arch/x86_64/lapic.zig
// Last Modified: 2026-03-01, 10:45:10.110
// Note: Local APIC (LAPIC) driver for prehistoric and modern x86_64 systems.

const std = @import("std");

/// Standard Local APIC Physical Base Address (default)
pub const DEFAULT_LAPIC_BASE: u64 = 0xFEE00000;

// LAPIC Registers (offsets from base)
const REG_ID: u32 = 0x20;
const REG_VER: u32 = 0x30;
const REG_TPR: u32 = 0x80;
const REG_EOI: u32 = 0xB0;
const REG_SVR: u32 = 0xF0;
const REG_LVT_TIMER: u32 = 0x320;
const REG_TIC_INIT: u32 = 0x380;
const REG_TIC_CUR: u32 = 0x390;
const REG_TDCR: u32 = 0x3E0;

var lapic_base: u64 = 0;

/// Initialize the Local APIC
/// Note: In a pure Genesis setup, we assume the physical address is 0xFEE00000.
/// For professional kernels, this is discovered via MADT.
pub fn init(base_virt: u64) void {
    lapic_base = base_virt;

    // Enable LAPIC by setting bit 8 in the Spurious Vector Register
    // Also set the spurious interrupt vector to 0xFF (standard)
    write(REG_SVR, read(REG_SVR) | 0x1FF);
}

/// Send End of Interrupt
pub fn eoi() void {
    write(REG_EOI, 0);
}

/// Configure the LAPIC timer for periodic interrupts.
/// @param vector: The interrupt vector to trigger (e.g., 32).
/// @param count: Initial count (determines the frequency).
pub fn enableTimer(vector: u8, count: u32) void {
    // 1. Set Divider to 16
    write(REG_TDCR, 0x03);

    // 2. Set LVT Timer: Periodic mode (bit 17) + the vector
    write(REG_LVT_TIMER, (1 << 17) | @as(u32, vector));

    // 3. Set Initial Count
    write(REG_TIC_INIT, count);
}

fn read(reg: u32) u32 {
    const ptr: *volatile u32 = @ptrFromInt(lapic_base + reg);
    return ptr.*;
}

fn write(reg: u32, value: u32) void {
    const ptr: *volatile u32 = @ptrFromInt(lapic_base + reg);
    ptr.* = value;
}
