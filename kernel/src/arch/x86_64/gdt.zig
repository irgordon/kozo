// File Path: kernel/src/arch/x86_64/gdt.zig
// Last Modified: 2026-02-28, 22:50:04.110
const std = @import("std");

pub const GdtEntry = packed struct(u64) {
    limit_low: u16 = 0xFFFF,
    base_low: u24 = 0,
    access: u8,
    limit_high: u4 = 0xF,
    flags: u4,
    base_high: u8 = 0,

    pub fn kernelCode() GdtEntry { return .{ .access = 0x9A, .flags = 0xA }; }
    pub fn kernelData() GdtEntry { return .{ .access = 0x92, .flags = 0xA }; }
    pub fn userCode() GdtEntry   { return .{ .access = 0xFA, .flags = 0xA }; }
    pub fn userData() GdtEntry   { return .{ .access = 0xF2, .flags = 0xA }; }
};

const Gdt = struct {
    null_ptr: u64 = 0,
    k_code: GdtEntry = GdtEntry.kernelCode(),
    k_data: GdtEntry = GdtEntry.kernelData(),
    u_code: GdtEntry = GdtEntry.userCode(),
    u_data: GdtEntry = GdtEntry.userData(),
};

var gdt: Gdt = .{};

pub fn init() void {
    const ptr = packed struct { limit: u16, base: u64 }{
        .limit = @sizeOf(Gdt) - 1,
        .base = @intFromPtr(&gdt),
    };

    asm volatile (
        \\lgdt (%[ptr])
        \\pushq $0x08
        \\leaq 1f(%%rip), %%rax
        \\pushq %%rax
        \\lretq
        \\1:
        \\movw $0x10, %%ax
        \\movw %%ax, %%ds
        \\movw %%ax, %%es
        \\movw %%ax, %%ss
        : : [ptr] "r" (&ptr) : "rax", "memory"
    );
}