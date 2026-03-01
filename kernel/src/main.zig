//! KOZO Kernel - Genesis Main
//! File Path: kernel/src/main.zig

const std = @import("std");
const config = @import("config");
const arch = @import("arch/x86_64/boot.zig");
const cap = @import("capability.zig");

pub const BootInfo = struct {
    untyped_base: usize,
    untyped_size: usize,
    root_cnode_ptr: usize,
};

export fn kozo_kernel_main(boot_ptr: *BootInfo) noreturn {
    // 1. Initial Serial/Logging bring-up
    std.log.info("KOZO Genesis Block Initializing...", .{});

    // 2. Arch-specific CPU setup (Paging, IDT, Syscall MSRs)
    arch.init_cpu();

    // 3. Initialize Root CNode from bootloader memory
    const root_slots = @as([*]cap.CapSlot, @ptrFromInt(boot_ptr.root_cnode_ptr));
    var root_cnode = cap.CNode{
        .slots = root_slots[0..(1 << config.root_cnode_bits)],
        .parent = null,
        .next_sibling = null,
        .prev_sibling = null,
    };

    // 4. Register the initial Untyped Capability at Slot 0
    // This is the "Seed" from which all other memory will be retyped.
    root_cnode.insert(0, .{
        .cap_type = .CAP_UNTYPED,
        .rights = 0xFFFFFFFFFFFFFFFF, // Full Grant rights for Init
        .badge = 0x7FFFFFFFFFFFFFFF, // Genesis Badge
        .data = .{
            .untyped = .{
                .base = boot_ptr.untyped_base,
                .size = boot_ptr.untyped_size,
                .offset = 0,
                .parent = null,
            },
        },
    }) catch @panic("Failed to seed initial Untyped capability");

    std.log.info("Memory Seeded. Untyped Base: 0x{x}", .{boot_ptr.untyped_base});

    // 5. Jump to Layer 1 (Rust Init)
    // We pass the address of the boot_ptr so Init knows where its memory is.
    arch.jump_to_init(boot_ptr);
}