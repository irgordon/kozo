// File Path: kernel/src/main.zig
// Last Modified: 2026-02-28, 22:15:42.105
// Note: Pure 64-bit Microkernel Entry Point. Single Layer Abstraction (SLA) compliant.
const std = @import("std");

// Import the "Sacred Contract" shared with the UEFI loader
const BootInfo = @import("common/boot_info.zig").BootInfo;

// Import Architecture-Specific Initializers
const gdt = @import("arch/x86_64/gdt.zig");
const idt = @import("arch/x86_64/idt.zig");
const vga = @import("arch/x86_64/vga.zig");
const pmm = @import("memory/pmm.zig");
const vmm = @import("memory/vmm.zig");
const lapic = @import("arch/x86_64/lapic.zig");
const scheduler = @import("scheduler.zig");
const thread = @import("thread.zig");

/// The kernel's panic handler. 
/// In Genesis, we just hang, but eventually, this will dump state to the screen.
pub fn panic(msg: []const u8, error_return_trace: ?*std.builtin.StackTrace, ret_addr: ?usize) noreturn {
    _ = error_return_trace;
    _ = ret_addr;
    _ = msg;
    // TODO: Implement a panic screen using VgaWriter
    while (true) {
        asm volatile ("hlt");
    }
}

/// The "Pure 64" Entry Point.
/// Called by the UEFI loader after switching to KOZO Page Tables.
/// @param info: Pointer to the Handover struct (passed in RSI/RDI depending on ABI).
export fn _kernel_start(info: *const BootInfo) noreturn {
    // --- Phase 1: CPU Ownership ---
    // Transition from UEFI-owned GDT to Kernel-owned GDT.
    // This defines our Code and Data segments for Ring 0 and eventually Ring 3.
    gdt.init();

    // Initialize the IDT. 
    // Currently, this just loads the LIDT instruction. 
    // Handlers in trap.S will be wired up in Phase 3.
    idt.init();

    // --- Phase 2: Hardware Visualization ---
    // Initialize the Framebuffer writer using info provided by UEFI.
    const screen = vga.VgaWriter.init(info);

    // Pulse: Clear the screen to a "KOZO Deep Blue" to verify we own the pixels.
    // Color: 0x001A2B3C (Classic Microkernel aesthetics)
    screen.clear(0x001A2B3C);

    // --- Phase 3: Memory & Logic ---
    // At this point, the kernel can begin higher-level initialization.
    
    // 1. Initialize the Physical Memory Manager (PMM) using info handover
    pmm.init(info);

    // 2. Initialize the Virtual Memory Manager (VMM) using recursive paging
    vmm.init(info.pml4_phys);

    // 3. Map and initialize the Local APIC
    const lapic_virt: u64 = 0xFFFFFFFF40000000; // Example HAL window
    vmm.mapPage(lapic_virt, lapic.DEFAULT_LAPIC_BASE, vmm.PageFlags.Present | vmm.PageFlags.Write | vmm.PageFlags.CacheDisable) catch @panic("LAPIC Mapping Failed");
    lapic.init(lapic_virt);

    // 4. Initialize the IDT and specific handlers
    idt.init();

    // 5. Initialize Scheduler and System Threads
    scheduler.init();
    
    // Pulse: Success Indicator
    draw_success_pixel(screen);

    // 6. Enable the APIC Timer (Vector 32, every 10ms-ish for Genesis)
    lapic.enableTimer(32, 0x1000000);

    // --- Phase 4: The Multitasking Era ---
    // Start the first thread by yielding.
    // In Genesis, the scheduler will pick the first thread we enqueued.
    // For now, we'll just idle until an interrupt or thread is ready.
    scheduler.yield();

    while (true) {
        asm volatile ("hlt");
    }
}

fn draw_success_pixel(screen: vga.VgaWriter) void {
    const color_green: u32 = 0x0000FF00;
    var y: u32 = 20;
    while (y < 40) : (y += 1) {
        var x: u32 = 20;
        while (x < 40) : (x += 1) {
            const index = (y * (screen.pitch / 4)) + x;
            screen.fb[index] = color_green;
        }
    }
}