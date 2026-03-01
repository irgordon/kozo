// Last Modified: 2026-02-28, 21:23:44.812
// Note: Fully removed legacy 32-bit bootstrap support. Kernel is now Pure 64-bit x86_64.
// Integrated UEFI bootloader build step to handle kernel handover.

const std = @import("std");

pub fn build(b: *std.Build) void {
const target = b.standardTargetOptions(.{
.default_target = .{
.cpu_arch = .x86_64,
.os_tag = .freestanding,
.abi = .none,
},
});
const optimize = b.standardOptimizeOption(.{});


// 1. Generate ABI files
const abi_step = b.step("abi", "Generate ABI headers for Rust services");
const generate_abi = b.addSystemCommand(&.{
    "sh", "-c", 
    "mkdir -p services/kozo-sys/src && zig run scripts/gen_abi.zig -- kernel/src/syscall.zig services/kozo-sys/src/abi.rs"
});
abi_step.dependOn(&generate_abi.step);

// 2. Kernel executable (Pure 64-bit)
const kernel = b.addExecutable(.{
    .name = "kozo-kernel",
    .root_source_file = b.path("kernel/src/main.zig"),
    .target = target,
    .optimize = optimize,
    .code_model = .kernel,
});

// Removed boot.S (legacy 32-bit entry). 
// Kept 64-bit architectural assembly.
kernel.addAssemblyFile(b.path("kernel/arch/x86_64/trap.S"));
kernel.addAssemblyFile(b.path("kernel/arch/x86_64/context.S"));
kernel.addAssemblyFile(b.path("kernel/arch/x86_64/ipc.S"));

kernel.setLinkerScriptPath(b.path("kernel/arch/x86_64/linker.ld"));
kernel.addIncludePath(b.path("zig-out/include"));

b.installArtifact(kernel);

// 3. UEFI Bootloader (bootx64.efi)
// UEFI target is specifically x86_64-uefi-msvc or x86_64-uefi-gnu
const uefi_target = b.resolveTargetQuery(.{
    .cpu_arch = .x86_64,
    .os_tag = .uefi,
    .abi = .msvc,
});

const loader = b.addExecutable(.{
    .name = "bootx64",
    .root_source_file = b.path("boot/uefi/main.zig"),
    .target = uefi_target,
    .optimize = optimize,
});

// Install loader to the standard UEFI path
const install_loader = b.addInstallArtifact(loader, .{
    .dest_dir = .{ .override = .{ .custom = "efi/boot" } },
});
b.getInstallStep().dependOn(&install_loader.step);

// 4. Run in QEMU (Updated for UEFI)
// Note: Requires OVMF.fd in the working directory or system path for UEFI support.
const run_cmd = b.addSystemCommand(&.{
    "qemu-system-x86_64",
    "-machine", "q35",
    "-cpu", "qemu64",
    "-m", "256M",
    "-bios", "OVMF.fd", // Standard UEFI Firmware
    "-drive", "format=raw,file=fat:rw:zig-out/efi", // Point QEMU to our EFI directory
    "-net", "none",
    "-no-reboot",
    "-display", "cocoa", // Set to 'sdl' or 'gtk' to see the framebuffer
    "-serial", "stdio", // Useful for future serial debugging
});

run_cmd.step.dependOn(b.getInstallStep());

const run_step = b.step("run", "Run KOZO in QEMU (UEFI)");
run_step.dependOn(&run_cmd.step);

}