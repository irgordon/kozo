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

    // Generate ABI files
    const abi_step = b.step("abi", "Generate ABI headers");
    const generate_abi = b.addSystemCommand(&.{
        "sh", "-c",
        "mkdir -p zig-out/include services/kozo-sys/src"
    });
    abi_step.dependOn(&generate_abi.step);

    // Kernel executable
    const kernel = b.addExecutable(.{
        .name = "kozo-kernel",
        .root_source_file = b.path("kernel/src/main.zig"),
        .target = target,
        .optimize = optimize,
        .code_model = .kernel,
    });

    // Assembly files
    kernel.addAssemblyFile(b.path("kernel/arch/x86_64/boot.S"));
    kernel.addAssemblyFile(b.path("kernel/arch/x86_64/trap.S"));
    kernel.addAssemblyFile(b.path("kernel/arch/x86_64/context.S"));
    kernel.addAssemblyFile(b.path("kernel/arch/x86_64/ipc.S"));

    // Linker script
    kernel.setLinkerScriptPath(b.path("kernel/arch/x86_64/linker.ld"));
    
    // Include path for generated ABI header
    kernel.addIncludePath(b.path("zig-out/include"));

    // Install kernel
    b.installArtifact(kernel);

    // Run in QEMU
    const run_cmd = b.addSystemCommand(&.{
        "qemu-system-x86_64",
        "-machine", "q35",
        "-cpu", "qemu64,-smap",
        "-m", "128M",
        "-kernel", "zig-out/bin/kozo-kernel",
        "-no-reboot",
        "-display", "none",
    });
    run_cmd.step.dependOn(b.getInstallStep());
    
    const run_step = b.step("run", "Run kernel in QEMU");
    run_step.dependOn(&run_cmd.step);
}
