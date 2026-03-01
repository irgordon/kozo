// File Path: kernel/src/arch/x86_64/syscall.zig
// Last Modified: 2026-03-01, 12:45:10.120
// Note: Fast Syscall Configuration using SYSCALL/SYSRET.

const std = @import("std");

const IA32_EFER = 0xC0000080;
const IA32_STAR = 0xC0000081;
const IA32_LSTAR = 0xC0000082;
const IA32_FMASK = 0xC0000084;

extern fn syscall_entry() void;

pub fn init() void {
    // 1. Enable SCE (System Call Enable) and NXE (No-Execute Enable)
    var efer = readMsr(IA32_EFER);
    efer |= (1 << 0);  // SCE
    efer |= (1 << 11); // NXE
    writeMsr(IA32_EFER, efer);

    // 2. Configure Segment Selectors in STAR
    // Bits 47:32: Kernel CS (0x08) -> Kernel SS will be 0x10
    // Bits 63:48: User CS base (0x10) -> User SS will be 0x18, User CS will be 0x20
    const star = (@as(u64, 0x10) << 48) | (@as(u64, 0x08) << 32);
    writeMsr(IA32_STAR, star);

    // 3. Set LSTAR (Target RIP)
    writeMsr(IA32_LSTAR, @intFromPtr(&syscall_entry));

    // 4. Set SFMASK (RFLAGS mask)
    // Clear Interrupts (bit 9), Trap (bit 8), and Direction (bit 10)
    writeMsr(IA32_FMASK, @as(u64, 0x200 | 0x100 | 0x400));
}

pub const SyscallFrame = extern struct {
    r15: u64, r14: u64, r13: u64, r12: u64,
    r11: u64, r10: u64, r9: u64, r8: u64,
    rbp: u64, rdi: u64, rsi: u64, rdx: u64,
    rcx: u64, rbx: u64, rax: u64, // Syscall number / Return value
    
    // The following match the iretq-like frame pushed in trap.S
    rip: u64,
    cs: u64,
    rflags: u64,
    rsp: u64,
    ss: u64,
};

const ipc = @import("../../syscall/ipc.zig");
const abi = @import("../../abi.zig");

/// The high-level syscall dispatcher called from assembly.
pub export fn syscall_dispatch(frame: *SyscallFrame) void {
    const num = frame.rax;
    
    frame.rax = switch (num) {
        abi.SYS_IPC_CALL => @intCast(ipc.sys_call(frame.rdi, frame.rsi, frame.rdx, frame.r10)),
        abi.SYS_IPC_REPLY => @intCast(ipc.sys_reply_wait(@as(u32, @intCast(frame.rdi)), frame.rsi, frame.rdx, frame.r10)),
        abi.SYS_DEBUG_PUTCHAR => {
            // Simple debug out for now
            std.debug.print("{c}", .{@as(u8, @intCast(frame.rdi))});
            0;
        },
        else => @as(u64, @intCast(abi.KOZO_ERR_INVALID)),
    };

    // --- SECURITY: Register Cleansing ---
    // Zero out registers not part of the ABI return contract to prevent side-channels
    // rbx, rbp, r8-r10, r12-r15. Note: r11 is RFLAGS, rcx is RIP, rdi/rsi/rdx are often scratch.
    frame.rbx = 0;
    frame.rbp = 0;
    frame.r8  = 0;
    frame.r9  = 0;
    frame.r10 = 0;
    frame.r12 = 0;
    frame.r13 = 0;
    frame.r14 = 0;
    frame.r15 = 0;
}

fn readMsr(msr: u32) u64 {
    var low: u32 = undefined;
    var high: u32 = undefined;
    asm volatile ("rdmsr" : [low] "={ax}" (low), [high] "={dx}" (high) : [msr] "{cx}" (msr));
    return (@as(u64, high) << 32) | low;
}

fn writeMsr(msr: u32, value: u64) void {
    const low = @as(u32, @intCast(value & 0xFFFFFFFF));
    const high = @as(u32, @intCast(value >> 32));
    asm volatile ("wrmsr" : : [msr] "{cx}" (msr), [low] "{ax}" (low), [high] "{dx}" (high) : "memory");
}
