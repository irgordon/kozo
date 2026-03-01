// File Path: kernel/src/arch/x86_64/traps.zig
// Last Modified: 2026-03-01, 10:55:10.110
// Note: Interrupt Dispatcher - Bridges assembly stubs to Zig logic.

const std = @import("std");
const lapic = @import("lapic.zig");
const scheduler = @import("../../scheduler.zig");

/// trap_dispatch: The high-level entry for all interrupts and exceptions.
/// Called by assembly stubs in trap.S.
export fn trap_dispatch(num: u64) void {
    switch (num) {
        // --- Hardware IRQs ---
        32 => { // APIC Timer
            lapic.eoi();
            scheduler.yield();
        },

        // --- Exceptions ---
        14 => { // Page Fault
            // TODO: VMM fault handling
            @panic("Unhandled Page Fault");
        },

        0xFF => { // Default / Unhandled
            // Handle unknown interrupts
        },

        else => {
            // Log and hang
            @panic("Unhandled Trap");
        },
    }
}
