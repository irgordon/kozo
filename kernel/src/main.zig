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
const elf = @import("memory/elf.zig");
const cpio = @import("memory/cpio.zig");
const lapic = @import("arch/x86_64/lapic.zig");
const syscall = @import("arch/x86_64/syscall.zig");
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
    // idt.init(); - Moved below pmm.init to allow IST allocation

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

    // 2.5 Initialize Emergency Stacks (IST)
    // Double Fault (IST1)
    const df_stack = pmm.allocFrame() catch @panic("Failed to allocate DF stack");
    gdt.setInterruptStack(df_stack + 4096, 1);
    // Machine Check (IST2)
    const mc_stack = pmm.allocFrame() catch @panic("Failed to allocate MC stack");
    gdt.setInterruptStack(mc_stack + 4096, 2);

    // 4. Initialize the IDT and specific handlers
    idt.init();

    // 3. Map and initialize the Local APIC

    // 5. Initialize Scheduler and System Threads
    scheduler.init();
    
    // Pulse: Success Indicator
    draw_success_pixel(screen);

    // 6. Enable the APIC Timer (Vector 32, every 10ms-ish for Genesis)
    lapic.enableTimer(32, 0x1000000);

    // 7. Initialize Syscall Architecture
    syscall.init();

    // --- Phase 4: The Multitasking Era ---
    
    // 1. Launch the Init Service
    // We search for the "init" file in the CPIO archive passed by the loader
    const initrd_ptr: [*]u8 = @ptrFromInt(info.initrd_addr);
    const init_data = cpio.findFile(initrd_ptr[0..info.initrd_size], "init") 
        orelse @panic("Init service not found in initrd");
    
    // 2. Create a new Address Space (Isolates Init from Kernel)
    const init_cr3 = vmm.createAddressSpace() catch @panic("Failed to create Init address space");
    
    // Switch to target address space so ELF memcpy works as intended
    asm volatile ("mov %[cr3], %%cr3" : : [cr3] "r" (init_cr3) : "memory");

    // 3. Load ELF and get entry point
    const entry = elf.loadElf(init_data) catch @panic("Failed to load Init ELF");
    
    // 4. Create Init Thread (TID 1)
    const init_tcb = thread.allocTCB() orelse @panic("Failed to allocate Init TCB");
    init_tcb.tid = 1;
    init_tcb.priority = 10; // High priority for init
    init_tcb.cr3 = init_cr3;
    
    // 5. Allocate and Map User Stack
    // We use a fixed virtual address for the user stack in Genesis
    const USER_STACK_VADDR: u64 = 0x0000700000000000;
    const u_stack_phys = pmm.allocFrame() catch @panic("Failed to allocate user stack");
    vmm.mapPage(USER_STACK_VADDR - 4096, u_stack_phys, vmm.PageFlags.User | vmm.PageFlags.Write | vmm.PageFlags.NoExecute) catch @panic("Failed to map user stack");

    const k_stack_phys = pmm.allocFrame() catch @panic("Failed to allocate kernel stack");
    // Kernel stack doesn't need to be mapped in user space, TCB uses physical/higher-half pointer
    const k_stack_top = 0xFFFFFFFF90000000; // Example fixed window or dynamic
    vmm.mapPage(k_stack_top - 4096, k_stack_phys, vmm.PageFlags.Write | vmm.PageFlags.NoExecute) catch @panic("Failed to map kernel stack");
    
    // 6. Set up TCB (Ring 3)
    init_tcb.root_cnode = null; // Explicitly null for now
    init_tcb.setupThread(entry, USER_STACK_VADDR, k_stack_top, true);
    
    // 7. Enqueue and Start
    scheduler.enqueue(init_tcb);
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