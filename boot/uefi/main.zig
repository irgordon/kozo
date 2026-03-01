// File Path: boot/uefi/main.zig
// Last Modified: 2026-02-28, 21:48:12.515
// Note: Pure 64-bit UEFI Loader. Handles GOP, Memory Map, ELF loading, and Paging setup.
//
const std = @import("std");
const uefi = std.os.uefi;
const elf = @import("elf.zig");
const rsdp = @import("rsdp.zig");
const BootInfo = @import("../../common/boot_info.zig").BootInfo;

const L = std.unicode.utf8ToUtf16LeStringLiteral;

pub fn main() void {
    const st = uefi.system_table;
    const bs = st.boot_services.?;
    const con_out = st.con_out.?;

    _ = con_out.clearScreen();
    _ = con_out.outputString(L("KOZO UEFI Genesis Loader\r\n"));

    // 1. Locate Graphics (GOP)
    var gop: *uefi.protocol.GraphicsOutput = undefined;
    if (bs.locateProtocol(&uefi.protocol.GraphicsOutput.guid, null, @as(*?*anyopaque, @ptrCast(&gop))) != .Success) {
        _ = con_out.outputString(L("Error: GOP not found\r\n"));
        hang();
    }

    // 2. Load Kernel ELF from Disk
    // Note: loadKernelFile is a helper that uses uefi.protocol.SimpleFileSystem
    const kernel_data = loadKernelFile(bs) catch |err| {
        _ = con_out.outputString(L("Error: Could not load kernel file\r\n"));
        // Print error code for debugging
        hang();
    };

    // 3. Parse and Load ELF Segments into Physical Memory
    // This places the kernel at the LMA specified in the linker script (4MB)
    const entry_point = elf.loadElf(kernel_data) catch {
        _ = con_out.outputString(L("Error: ELF Loading Failed\r\n"));
        hang();
    };

    // 4. Prepare Memory Map
    var mmap_size: usize = 0;
    var map_key: usize = 0;
    var desc_size: usize = 0;
    var desc_ver: u32 = 0;

    // Get size first
    _ = bs.getMemoryMap(&mmap_size, null, &map_key, &desc_size, &desc_ver);
    mmap_size += 2 * desc_size; // Headroom

    var mmap_buf: [*]uefi.tables.MemoryDescriptor = undefined;
    if (bs.allocatePool(.LoaderData, mmap_size, @as(*?*anyopaque, @ptrCast(&mmap_buf))) != .Success) {
        _ = con_out.outputString(L("Error: Mmap Allocation Failed\r\n"));
        hang();
    }

    if (bs.getMemoryMap(&mmap_size, mmap_buf, &map_key, &desc_size, &desc_ver) != .Success) {
        _ = con_out.outputString(L("Error: Mmap Fetch Failed\r\n"));
        hang();
    }

    // 5. Build Handover Info
    const info = BootInfo{
        .fb_base = gop.mode.frame_buffer_base,
        .fb_size = gop.mode.frame_buffer_size,
        .width = gop.mode.info.horizontal_resolution,
        .height = gop.mode.info.vertical_resolution,
        .pitch = gop.mode.info.pixels_per_scan_line * 4,
        .memory_map_addr = @intFromPtr(mmap_buf),
        .memory_map_size = mmap_size,
        .descriptor_size = desc_size,
        .rsdp_phys = rsdp.findRsdp(st) orelse 0,
    };

    // 6. Setup Kernel Page Tables (Identity + Higher-Half)
    const cr3_val = setupKernelPaging(bs) catch {
        _ = con_out.outputString(L("Error: Paging Setup Failed\r\n"));
        hang();
    };

    // 7. EXIT BOOT SERVICES
    // The point of no return. We own the CPU now.
    if (bs.exitBootServices(uefi.handle, map_key) != .Success) {
        _ = con_out.outputString(L("Error: ExitBootServices Failed (Map changed)\r\n"));
        hang();
    }

    // 8. Load the new Page Tables
    asm volatile ("mov %[ptr], %%cr3" : : [ptr] "r" (cr3_val));

    // 9. JUMP TO KERNEL
    // We pass the pointer to BootInfo in RSI (standard SysV ABI for first arg)
    const kernel_entry: *const fn (*const BootInfo) noreturn = @ptrFromInt(entry_point);
    kernel_entry(&info);
}

fn setupKernelPaging(bs: *uefi.tables.BootServices) !u64 {
    var pml4_phys: u64 = undefined;
    // Allocate 3 pages: PML4, PDP, PD
    if (bs.allocatePages(.AllocateAnyPages, .LoaderData, 3, &pml4_phys) != .Success) return error.PageAllocFailed;

    const pml4: [*]u64 = @ptrFromInt(pml4_phys);
    @memset(pml4[0 .. 3 * 512], 0);

    const pdp_phys = pml4_phys + 4096;
    const pd_phys = pml4_phys + 8192;

    const pdp: [*]u64 = @ptrFromInt(pdp_phys);
    const pd: [*]u64 = @ptrFromInt(pd_phys);

    // PML4[0] (Identity) and PML4[511] (Higher-Half)
    pml4[0] = pdp_phys | 0x3;
    pml4[511] = pdp_phys | 0x3;

    // PDP[0] (Low) and PDP[510] (-2GB range)
    pdp[0] = pd_phys | 0x3;
    pdp[510] = pd_phys | 0x3;

    // PD[0..1] -> Map to Physical 4MB (where ELF was loaded)
    // We map 4MB of space starting at physical 4MB.
    pd[0] = 0x400000 | 0x83; // 4MB to 6MB
    pd[1] = 0x600000 | 0x83; // 6MB to 8MB

    return pml4_phys;
}

fn hang() noreturn {
    while (true) asm volatile ("hlt");
}

// Minimal file loader implementation for UEFI
fn loadKernelFile(bs: *uefi.tables.BootServices) ![]u8 {
    var fs: *uefi.protocol.SimpleFileSystem = undefined;
    if (bs.locateProtocol(&uefi.protocol.SimpleFileSystem.guid, null, @as(*?*anyopaque, @ptrCast(&fs))) != .Success) return error.NoFS;

    var root: *uefi.protocol.File = undefined;
    if (fs.openVolume(&root) != .Success) return error.OpenVolumeFailed;

    var file: *uefi.protocol.File = undefined;
    // Note: Assuming path is /boot/kozo-kernel
    if (root.open(&file, L("boot\\kozo-kernel"), uefi.protocol.File.mode_read, 0) != .Success) return error.FileNotFound;

    // Get file size
    var info_buf: [256]u8 = undefined;
    var info_size: usize = info_buf.len;
    if (file.getInfo(&uefi.protocol.FileInfo.guid, &info_size, &info_buf) != .Success) return error.GetInfoFailed;
    const file_info = @as(*uefi.protocol.FileInfo, @ptrCast(&info_buf));
    const size = file_info.file_size;

    // Allocate buffer
    var buffer: [*]u8 = undefined;
    if (bs.allocatePool(.LoaderData, size, @as(*?*anyopaque, @ptrCast(&buffer))) != .Success) return error.AllocFailed;

    var read_size = size;
    if (file.read(&read_size, buffer) != .Success) return error.ReadFailed;

    return buffer[0..size];
}