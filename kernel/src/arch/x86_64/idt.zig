// File Path: kernel/src/arch/x86_64/idt.zig
// Last Modified: 2026-02-28, 22:50:04.115
const std = @import("std");

pub const IdtEntry = packed struct(u128) {
    offset_low: u16,
    selector: u16 = 0x08, // Kernel Code Segment
    ist: u8 = 0,
    type_attr: u8,
    offset_mid: u16,
    offset_high: u32,
    reserved: u32 = 0,

    pub fn init(handler: u64, dpl: u2) IdtEntry {
        return .{
            .offset_low = @as(u16, @truncate(handler)),
            .offset_mid = @as(u16, @truncate(handler >> 16)),
            .offset_high = @as(u32, @truncate(handler >> 32)),
            .type_attr = 0x8E | (@as(u8, dpl) << 5), // Present + Interrupt Gate
        };
    }
};

extern var trap_table: [256]?*const anyopaque;
extern fn idt_install() void;
extern fn idt_set_gate(vector: u8, handler: u64, selector: u16, type_attr: u8) void;

pub fn init() void {
    // 1. Initialize all gates to the default handler first
    const default_handler = @intFromPtr(trap_table[5]); // Using trap_default from table
    var i: u8 = 0;
    while (true) {
        idt_set_gate(i, default_handler, 0x08, 0x8E);
        if (i == 255) break;
        i += 1;
    }

    // 2. Install specific exception handlers (0-31)
    for (trap_table[0..32], 0..) |handler, vector| {
        if (handler) |h| {
            idt_set_gate(@intCast(vector), @intFromPtr(h), 0x08, 0x8E);
        }
    }

    // 3. Install Timer IRQ (Vector 32)
    if (trap_table[32]) |handler| {
        idt_set_gate(32, @intFromPtr(handler), 0x08, 0x8E);
    }

    // 4. Load LIDT
    idt_install();

    // 5. Enable Interrupts
    asm volatile ("sti");
}