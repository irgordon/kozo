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

pub const TssDescriptor = packed struct(u128) {
    limit_low: u16,
    base_low: u24,
    access: u8 = 0x89, // Present, Type 9 (64-bit TSS Available)
    limit_high: u4,
    flags: u4 = 0,
    base_mid: u8,
    base_high: u32,
    reserved: u32 = 0,

    pub fn init(base: u64, limit: u32) TssDescriptor {
        return .{
            .limit_low = @as(u16, @intCast(limit & 0xFFFF)),
            .base_low = @as(u24, @intCast(base & 0xFFFFFF)),
            .limit_high = @as(u4, @intCast((limit >> 16) & 0xF)),
            .base_mid = @as(u8, @intCast((base >> 24) & 0xFF)),
            .base_high = @as(u32, @intCast(base >> 32)),
        };
    }
};

pub const Tss = extern struct {
    reserved0: u32 = 0,
    rsp0: u64 = 0,
    rsp1: u64 = 0,
    rsp2: u64 = 0,
    reserved1: u64 = 0,
    ist1: u64 = 0,
    ist2: u64 = 0,
    ist3: u64 = 0,
    ist4: u64 = 0,
    ist5: u64 = 0,
    ist6: u64 = 0,
    ist7: u64 = 0,
    reserved2: u64 = 0,
    reserved3: u16 = 0,
    iopb_offset: u16 = @sizeOf(Tss),
};

const Gdt = extern struct {
    null_ptr: u64 = 0,
    k_code: GdtEntry = GdtEntry.kernelCode(), // 0x08
    k_data: GdtEntry = GdtEntry.kernelData(), // 0x10
    u_data: GdtEntry = GdtEntry.userData(),   // 0x18
    u_code: GdtEntry = GdtEntry.userCode(),   // 0x20
    tss: TssDescriptor = undefined,           // 0x28
};

var gdt: Gdt = .{};
var tss: Tss = .{};

pub fn setKernelStack(stack: u64) void {
    tss.rsp0 = stack;
}

pub fn setInterruptStack(stack: u64, index: u8) void {
    if (index == 0 or index > 7) return;
    const ist_ptr: [*]u64 = @ptrCast(&tss.ist1);
    ist_ptr[index - 1] = stack;
}

pub fn init() void {
    gdt.tss = TssDescriptor.init(@intFromPtr(&tss), @sizeOf(Tss) - 1);

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
        \\movw %%ax, %%fs
        \\movw %%ax, %%gs
        \\movw %%ax, %%ss
        \\movw $0x28, %%ax
        \\ltr %%ax
        : : [ptr] "r" (&ptr) : "rax", "memory"
    );
}