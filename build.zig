//! KOZO OS Build System - Genesis Block 0.0.1-dev
//! File Path: kozo/build.zig
//! Responsibility: Orchestrate ABI lockstep, kernel build, Rust services, and CI pipeline
//! Generates: zig-out/include/kozo_abi.h, services/kozo-sys/src/abi.rs, zig-out/kozo.img

const std = @import("std");
const Builder = std.Build;
const CrossTarget = std.zig.CrossTarget;

// KOZO 0.0.1-dev - Genesis Block Configuration
const KOZO_VERSION = "0.0.1-dev";
const SOURCE_DATE_EPOCH = "1704067200"; // For reproducible builds

// Toolchain Version Constraints (SaoLOD - Fail Fast)
const REQUIRED_ZIG_VERSION = "0.13.0";
const REQUIRED_RUST_VERSION = "1.77.0";

pub fn build(b: *Builder) void {
    // === STEP 0: TOOLCHAIN VALIDATION ===
    checkZigVersion();
    checkRustVersion(b);
    
    // Build configuration options
    const target = resolveTarget(b, .x86_64);
    const optimize = b.standardOptimizeOption(.{ 
        .preferred_optimize_mode = .Debug // Debug for genesis development
    });
    
    const arch = b.option(Arch, "arch", "Target architecture (x86_64)") orelse .x86_64;
    const reproducible = b.option(bool, "reproducible", "Deterministic build (CI/CD)") orelse false;
    const enable_telemetry = b.option(bool, "telemetry", "Enable error reporting") orelse true;
    
    // === STEP 1: PREFLIGHT CHECKS ===
    const preflight = b.step("preflight", "Validate build environment");
    addPreflightChecks(b, preflight);
    
    // === STEP 2: ABI LOCKSTEP (Critical - all else depends on this) ===
    // Generates: zig-out/include/kozo_abi.h (for Zig kernel)
    // Generates: services/kozo-sys/src/abi.rs (for Rust services)
    const abi_gen = generateAbi(b);
    abi_gen.step.dependOn(preflight);
    
    const abi_step = b.step("abi", "Generate synchronized ABI headers");
    abi_step.dependOn(&abi_gen.step);
    
    // === STEP 3: LAYER 0 - ZIG KERNEL ===
    // Output: zig-out/kozo-kernel
    const kernel = buildKernel(b, target, optimize, arch, reproducible, enable_telemetry);
    kernel.step.dependOn(&abi_gen.step);
    b.installArtifact(kernel);
    
    // === STEP 4: LAYER 1 - RUST SERVICES ===
    // Build order: Tier 1 (privileged) first, then Tier 2
    
    // Policy Service - The "Brain" (Tier 1 privileged)
    // Consumes: services/kozo-sys/src/abi.rs
    // Output: services/target/x86_64-kozo-none/release/policy
    const policy = buildPolicyService(b, target, optimize, abi_gen, reproducible);
    
    // Init Service - Bootstrap (Tier 1)
    // Consumes: services/kozo-sys/src/abi.rs  
    // Output: services/target/x86_64-kozo-none/release/init
    const init = buildInit(b, target, optimize, abi_gen, reproducible);
    
    // FSD - Filesystem Daemon (Tier 2 unprivileged)
    // Consumes: services/kozo-sys/src/abi.rs
    // Output: services/target/x86_64-kozo-none/release/fsd
    const fsd = buildFsd(b, target, optimize, abi_gen, reproducible);
    
    // === STEP 5: BOOT IMAGE CREATION ===
    // Uses: scripts/mkinitrd.sh (generates zig-out/initrd.cpio)
    // Uses: scripts/mkimage.sh (generates zig-out/kozo.img)
    const boot_image = buildBootImage(b, kernel, init, policy, fsd);
    const image_step = b.step("image", "Create bootable disk image");
    image_step.dependOn(boot_image);
    
    // === STEP 6: DEBUG SYMBOLS ===
    // Output: zig-out/kozo-kernel-x86_64.debug
    const debug_symbols = generateDebugSymbols(b, kernel, arch);
    b.getInstallStep().dependOn(debug_symbols);
    
    // === STEP 7: QEMU SMOKE TEST ===
    // Uses: scripts/integration-test.sh
    const qemu = addQemuStep(b, boot_image, enable_telemetry);
    const run_step = b.step("run", "Boot KOZO in QEMU and run smoke tests");
    run_step.dependOn(qemu);
    
    // === STEP 8: CI PIPELINE (Default) ===
    // Full pipeline: abi → kernel → services → image → test
    const ci = b.step("ci", "Full CI: abi → kernel → policy → init → fsd → image → qemu");
    ci.dependOn(abi_step);
    ci.dependOn(b.getInstallStep());
    ci.dependOn(image_step);
    ci.dependOn(qemu);
    
    b.default_step = ci;
    
    // Print configuration summary
    const summary = b.addSystemCommand(&[_][]const u8{
        "echo", b.fmt(
            \\KOZO Build Configuration:
            \\  Version: {s}
            \\  Architecture: {s}
            \\  Mode: {s}
            \\  Reproducible: {s}
            \\  Telemetry: {s}
            \\
        , .{
            KOZO_VERSION,
            @tagName(arch),
            @tagName(optimize),
            if (reproducible) "yes" else "no",
            if (enable_telemetry) "enabled" else "disabled",
        }),
    });
    b.getInstallStep().dependOn(&summary.step);
}

// === TOOLCHAIN VALIDATION ===

fn checkZigVersion() void {
    const required = std.SemanticVersion.parse(REQUIRED_ZIG_VERSION) catch unreachable;
    const actual = std.SemanticVersion.parse(std.builtin.zig_version_string) catch unreachable;
    
    if (actual.order(required) != .eq) {
        std.debug.print(
            "KOZO ERROR: Requires Zig {s}, found {s}\n",
            .{ REQUIRED_ZIG_VERSION, std.builtin.zig_version_string },
        );
        @panic("Toolchain version mismatch");
    }
}

fn checkRustVersion(b: *Builder) void {
    const result = std.ChildProcess.run(.{
        .allocator = b.allocator,
        .argv = &[_][]const u8{ "rustc", "--version" },
    }) catch |err| {
        std.debug.print("KOZO ERROR: Failed to run rustc: {any}\n", .{err});
        @panic("Rust not installed");
    };
    
    defer {
        b.allocator.free(result.stdout);
        b.allocator.free(result.stderr);
    }
    
    // Parse "rustc 1.77.0 (aedd173a2 2024-03-17)" -> "1.77.0"
    var parts = std.mem.split(u8, result.stdout, " ");
    _ = parts.next(); // skip "rustc"
    const version_str = parts.next() orelse {
        std.debug.print("KOZO ERROR: Unexpected rustc output: {s}\n", .{result.stdout});
        @panic("Cannot parse Rust version");
    };
    
    const trimmed = std.mem.trim(u8, version_str, " \n\r");
    const required = std.SemanticVersion.parse(REQUIRED_RUST_VERSION) catch unreachable;
    const actual = std.SemanticVersion.parse(trimmed) catch {
        std.debug.print("KOZO ERROR: Requires Rust {s}, found unparsable '{s}'\n", 
            .{ REQUIRED_RUST_VERSION, trimmed });
        @panic("Toolchain version mismatch");
    };
    
    if (actual.order(required) != .eq) {
        std.debug.print("KOZO ERROR: Requires Rust {s}, found {s}\n", 
            .{ REQUIRED_RUST_VERSION, trimmed });
        @panic("Toolchain version mismatch");
    }
    
    std.log.info("Toolchain OK: Zig {s}, Rust {s}", .{ 
        REQUIRED_ZIG_VERSION, trimmed 
    });
}

// === PREFLIGHT CHECKS ===

fn addPreflightChecks(b: *Builder, step: *std.Build.Step) void {
    // Check directory structure exists
    const tree_check = b.addSystemCommand(&[_][]const u8{
        "sh", "-c",
        \\[ -d kernel/src ] && [ -d services/init ] && [ -d services/policy ] && [ -d services/fsd ] || 
        \\(echo 'ERROR: Missing required directories' && exit 1)
    });
    step.dependOn(&tree_check.step);
    
    // Check required tools available
    const tools_check = b.addSystemCommand(&[_][]const u8{
        "sh", "-c",
        "which ld.lld qemu-system-x86_64 cpio objcopy || (echo 'ERROR: Missing tools' && exit 1)"
    });
    step.dependOn(&tools_check.step);
}

// === ABI GENERATION (LOCKSTEP) ===

fn generateAbi(b: *Builder) *GenerateAbiStep {
    const abi = b.allocator.create(GenerateAbiStep) catch unreachable;
    abi.* = .{
        .step = std.Build.Step.init(.{
            .id = .custom,
            .name = "generate-abi",
            .owner = b,
            .makeFn = GenerateAbiStep.make,
        }),
    };
    return abi;
}

const GenerateAbiStep = struct {
    step: std.Build.Step,
    
    pub fn make(step: *std.Build.Step, _: *std.Progress.Node) !void {
        const cwd = std.fs.cwd();
        const b = step.owner;
        
        // Ensure output directories exist
        try cwd.makePath("zig-out/include");
        try cwd.makePath("services/kozo-sys/src");
        
        // Syscall numbers - MUST MATCH between Zig kernel and Rust services
        const syscalls = .{
            // Capability management (0-9)
            .{ "CAP_CREATE", 1 },
            .{ "CAP_DELETE", 2 },
            .{ "CAP_REVOKE", 3 },
            .{ "CAP_TRANSFER", 4 },
            .{ "CAP_MINT", 5 },
            .{ "CAP_VERIFY", 6 },
            
            // IPC (10-19)
            .{ "IPC_SEND", 10 },
            .{ "IPC_RECV", 11 },
            .{ "IPC_CALL", 12 },      // Direct switch
            .{ "IPC_REPLY", 13 },     // Direct switch back
            
            // Memory (20-29)
            .{ "RETYPE", 20 },
            .{ "MAP_FRAME", 21 },
            .{ "UNMAP_FRAME", 22 },
            
            // Threading (30-39)
            .{ "THREAD_CREATE", 30 },
            .{ "THREAD_RESUME", 31 },
            .{ "THREAD_SUSPEND", 32 },
            .{ "THREAD_SET_PRIORITY", 33 },
            
            // Endpoints/Namespace (40-49)
            .{ "ENDPOINT_CREATE", 40 },
            .{ "ENDPOINT_DELETE", 41 },
            .{ "NAMESPACE_REGISTER", 42 },
            
            // Debugging (90-99)
            .{ "DEBUG_PUTCHAR", 99 },
        };
        
        // Generate C header: zig-out/include/kozo_abi.h
        var c_buf = std.ArrayList(u8).init(b.allocator);
        defer c_buf.deinit();
        const c = c_buf.writer();
        
        try c.print(
            \\// KOZO ABI v{s} - GENESIS BLOCK
            \\// File Path: zig-out/include/kozo_abi.h
            \\// AUTO-GENERATED by build.zig - DO NOT EDIT
            \\// Sync with: services/kozo-sys/src/abi.rs
            \\
            \\#ifndef KOZO_ABI_H
            \\#define KOZO_ABI_H
            \\
            \\#define KOZO_VERSION "{s}"
            \\#define INIT_UNTYPED_SIZE 0x1000000  // 16MB
            \\#define ROOT_CNODE_SIZE_BITS 12      // 4096 slots
            \\#define IPC_BUFFER_SIZE 512
            \\
            \\// Syscall numbers (LOCKSTEP)
            \\
        , .{ KOZO_VERSION, KOZO_VERSION });
        
        inline for (syscalls) |sc| {
            try c.print("#define SYS_{s} {d}\n", .{ sc.@"0", sc.@"1" });
        }
        
        try c.writeAll(
            \\
            \\// Capability types
            \\typedef enum { 
            \\    CAP_NULL=0, CAP_UNTYPED, CAP_CNODE, CAP_ENDPOINT, 
            \\    CAP_THREAD, CAP_ADDRESS_SPACE, CAP_FRAME, CAP_PAGE_TABLE,
            \\    CAP_IRQ_HANDLER
            \\} kozo_cap_type_t;
            \\
            \\// Rights bitmask
            \\typedef unsigned long kozo_rights_t;
            \\#define RIGHT_READ  (1UL<<0)
            \\#define RIGHT_WRITE (1UL<<1)
            \\#define RIGHT_GRANT (1UL<<2)
            \\#define RIGHT_MAP   (1UL<<3)
            \\
            \\// Error codes
            \\#define KOZO_OK 0
            \\#define KOZO_ERR_INVALID -1
            \\#define KOZO_ERR_NO_CAP -2
            \\#define KOZO_ERR_NO_MEM -3
            \\#define KOZO_ERR_ACCESS_DENIED -4
            \\#define KOZO_ERR_NO_SPACE -5
            \\
            \\#endif // KOZO_ABI_H
            \\
        );
        
        try cwd.writeFile("zig-out/include/kozo_abi.h", c_buf.items);
        
        // Generate Rust module: services/kozo-sys/src/abi.rs
        var r_buf = std.ArrayList(u8).init(b.allocator);
        defer r_buf.deinit();
        const r = r_buf.writer();
        
        try r.print(
            \\//! KOZO ABI v{s} - GENESIS BLOCK
            \\//! File Path: services/kozo-sys/src/abi.rs
            \\//! AUTO-GENERATED by build.zig - DO NOT EDIT
            \\//! Sync with: zig-out/include/kozo_abi.h
            \\
            \\#![allow(dead_code)]
            \\
            \\pub const VERSION: &str = "{s}";
            \\pub const INIT_UNTYPED_SIZE: usize = 0x1000000;
            \\pub const ROOT_CNODE_SIZE_BITS: usize = 12;
            \\pub const IPC_BUFFER_SIZE: usize = 512;
            \\
            \\#[repr(usize)]
            \\#[derive(Debug, Clone, Copy, PartialEq, Eq)]
            \\pub enum Syscall {{
            \\
        , .{ KOZO_VERSION, KOZO_VERSION });
        
        inline for (syscalls) |sc| {
            try r.print("    {s} = {d},\n", .{ sc.@"0", sc.@"1" });
        }
        
        try r.writeAll(
            \\}
            \\
            \\#[repr(u8)]
            \\#[derive(Debug, Clone, Copy, PartialEq, Eq)]
            \\pub enum CapType {{
            \\    Null = 0, Untyped, Cnode, Endpoint, Thread, 
            \\    AddressSpace, Frame, PageTable, IrqHandler,
            \\}}
            \\
            \\pub type Rights = u64;
            \\pub const RIGHT_READ: Rights = 1 << 0;
            \\pub const RIGHT_WRITE: Rights = 1 << 1;
            \\pub const RIGHT_GRANT: Rights = 1 << 2;
            \\pub const RIGHT_MAP: Rights = 1 << 3;
            \\
            \\#[repr(isize)]
            \\#[derive(Debug, Clone, Copy, PartialEq, Eq)]
            \\pub enum Error {{
            \\    Ok = 0,
            \\    Invalid = -1,
            \\    NoCap = -2,
            \\    NoMem = -3,
            \\    AccessDenied = -4,
            \\    NoSpace = -5,
            \\}}
            \\
            \\impl Error {{
            \\    pub fn from_raw(v: isize) -> Result<(), Self> {{
            \\        match v {{
            \\            0 => Ok(()),
            \\            -1 => Err(Self::Invalid),
            \\            -2 => Err(Self::NoCap),
            \\            -3 => Err(Self::NoMem),
            \\            -4 => Err(Self::AccessDenied),
            \\            -5 => Err(Self::NoSpace),
            \\            _ => Err(Self::Invalid),
            \\        }}
            \\    }}
            \\}}
        );
        
        try cwd.writeFile("services/kozo-sys/src/abi.rs", r_buf.items);
        
        std.log.info("ABI lockstep generated: {} syscalls", .{syscalls.len});
    }
};

// === KERNEL BUILD ===

fn buildKernel(b: *Builder, target: CrossTarget, optimize: std.builtin.Mode, 
               arch: Arch, reproducible: bool, telemetry: bool) *std.Build.CompileStep {
    const kernel = b.addExecutable(.{
        .name = "kozo-kernel",
        .root_source_file = .{ .path = "kernel/src/main.zig" },
        .target = target,
        .optimize = optimize,
        .code_model = .kernel, // Higher half addressing
    });
    
    const opts = b.addOptions();
    opts.addOption([]const u8, "version", KOZO_VERSION);
    opts.addOption(bool, "reproducible_build", reproducible);
    opts.addOption(bool, "telemetry_enabled", telemetry);
    opts.addOption(usize, "init_untyped_size", 16 * 1024 * 1024);
    opts.addOption(usize, "root_cnode_bits", 12);
    opts.addOption(bool, "ipc_direct_switch", true);
    opts.addOption(bool, "fpu_enabled", false);
    
    kernel.addOptions("config", opts);
    
    // Assembly sources
    const asm_files = switch (arch) {
        .x86_64 => &[_][]const u8{
            "kernel/arch/x86_64/boot.S",
            "kernel/arch/x86_64/context.S",
            "kernel/arch/x86_64/ipc.S",
            "kernel/arch/x86_64/trap.S",
        },
        .aarch64 => &[_][]const u8{
            "kernel/arch/aarch64/boot.S",
            "kernel/arch/aarch64/context.S",
        },
    };
    
    for (asm_files) |file| {
        kernel.addAssemblyFile(.{ .path = file });
    }
    
    kernel.setLinkerScriptPath(.{ .path = "kernel/arch/x86_64/linker.ld" });
    kernel.addIncludePath(.{ .path = "zig-out/include" });
    kernel.root_module.strip = false; // Keep symbols for debugging
    
    return kernel;
}

// === RUST SERVICE BUILDS ===

const TargetSpec = struct {
    json: []const u8,
    path: []const u8,
};

fn getRustTargetSpec(b: *Builder, arch: Arch) TargetSpec {
    const json = switch (arch) {
        .x86_64 => 
            \\{"arch":"x86_64","cpu":"x86-64","data-layout":"e-m:e-i64:64-f80:128-n8:16:32:64-S128",
            \\"disable-redzone":true,"features":"-mmx,-sse,-sse2,+soft-float","linker":"ld.lld",
            \\"llvm-target":"x86_64-unknown-none","max-atomic-width":64,"os":"kozo",
            \\"panic-strategy":"abort","position-independent-executables":true,
            \\"pre-link-args":{"ld.lld":["-nostdlib","-static"]},"relro-level":"off",
            \\"target-c-int-width":"32","target-endian":"little","target-pointer-width":"64"}
        ,
    };
    
    const path = b.fmt("services/targets/{s}-kozo-none.json", .{@tagName(arch)});
    
    return .{ .json = json, .path = path };
}

fn buildPolicyService(b: *Builder, target: CrossTarget, optimize: std.builtin.Mode, 
                      abi: *GenerateAbiStep, reproducible: bool) *std.Build.Step {
    const step = b.step("policy", "Build Policy Service (Tier 1 - Privileged)");
    
    // Generate custom target spec
    const spec = getRustTargetSpec(b, .x86_64);
    const write_spec = b.addWriteFile(spec.path, spec.json);
    step.dependOn(&write_spec.step);
    
    // Tier 1 privileged build
    var cargo = b.addSystemCommand(&[_][]const u8{
        "cargo", "+" ++ REQUIRED_RUST_VERSION, "build",
        "-Z", "build-std=core,alloc",
        "-Z", "build-std-features=compiler-builtins-mem",
        "--manifest-path", "services/policy/Cargo.toml",
        "--target", spec.path,
        "--release",
        "--features", "tier1_privileged", // Enables cap.policy.grant
    });
    
    if (reproducible) {
        cargo.setEnvironmentVariable("CARGO_INCREMENTAL", "0");
        cargo.setEnvironmentVariable("SOURCE_DATE_EPOCH", SOURCE_DATE_EPOCH);
    }
    
    cargo.setEnvironmentVariable("KOZO_ABI_RS", "services/kozo-sys/src/abi.rs");
    cargo.step.dependOn(&abi.step);
    cargo.step.dependOn(&write_spec.step);
    
    step.dependOn(&cargo.step);
    return step;
}

fn buildInit(b: *Builder, target: CrossTarget, optimize: std.builtin.Mode, 
             abi: *GenerateAbiStep, reproducible: bool) *std.Build.Step {
    const step = b.step("init", "Build Init Service (Tier 1 - Bootstrap)");
    
    const spec = getRustTargetSpec(b, .x86_64);
    const write_spec = b.addWriteFile(spec.path, spec.json);
    step.dependOn(&write_spec.step);
    
    var cargo = b.addSystemCommand(&[_][]const u8{
        "cargo", "+" ++ REQUIRED_RUST_VERSION, "build",
        "-Z", "build-std=core,alloc",
        "-Z", "build-std-features=compiler-builtins-mem",
        "--manifest-path", "services/init/Cargo.toml",
        "--target", spec.path,
        "--release",
    });
    
    if (reproducible) {
        cargo.setEnvironmentVariable("CARGO_INCREMENTAL", "0");
        cargo.setEnvironmentVariable("SOURCE_DATE_EPOCH", SOURCE_DATE_EPOCH);
    }
    
    cargo.setEnvironmentVariable("KOZO_ABI_RS", "services/kozo-sys/src/abi.rs");
    cargo.step.dependOn(&abi.step);
    cargo.step.dependOn(&write_spec.step);
    
    step.dependOn(&cargo.step);
    return step;
}

fn buildFsd(b: *Builder, target: CrossTarget, optimize: std.builtin.Mode, 
            abi: *GenerateAbiStep, reproducible: bool) *std.Build.Step {
    const step = b.step("fsd", "Build FSD (Tier 2 - Unprivileged)");
    
    const spec = getRustTargetSpec(b, .x86_64);
    const write_spec = b.addWriteFile(spec.path, spec.json);
    step.dependOn(&write_spec.step);
    
    var cargo = b.addSystemCommand(&[_][]const u8{
        "cargo", "+" ++ REQUIRED_RUST_VERSION, "build",
        "-Z", "build-std=core,alloc",
        "--manifest-path", "services/fsd/Cargo.toml",
        "--target", spec.path,
        "--release",
    });
    
    if (reproducible) {
        cargo.setEnvironmentVariable("CARGO_INCREMENTAL", "0");
    }
    
    cargo.setEnvironmentVariable("KOZO_ABI_RS", "services/kozo-sys/src/abi.rs");
    cargo.step.dependOn(&abi.step);
    cargo.step.dependOn(&write_spec.step);
    
    step.dependOn(&cargo.step);
    return step;
}

// === BOOT IMAGE ===

fn buildBootImage(b: *Builder, kernel: *std.Build.CompileStep, 
                  init: *std.Build.Step, policy: *std.Build.Step, 
                  fsd: *std.Build.Step) *std.Build.Step {
    const step = b.step("image-internal", "Create bootable disk image");
    
    // Create initrd using mkinitrd.sh
    // Input: init, policy, fsd binaries
    // Output: zig-out/initrd.cpio
    const mkinitrd = b.addSystemCommand(&[_][]const u8{
        "sh", "scripts/mkinitrd.sh",
        "services/target/x86_64-kozo-none/release/init",
        "services/target/x86_64-kozo-none/release/policy",
        "services/target/x86_64-kozo-none/release/fsd",
        "zig-out/initrd.cpio",
    });
    mkinitrd.step.dependOn(init);
    mkinitrd.step.dependOn(policy);
    mkinitrd.step.dependOn(fsd);
    
    // Create bootable disk image using mkimage.sh
    // Input: kernel binary, initrd cpio
    // Output: zig-out/kozo.img
    const mkimage = b.addSystemCommand(&[_][]const u8{
        "sh", "scripts/mkimage.sh",
        kernel.getEmittedBin().?.path,
        "zig-out/initrd.cpio",
        "zig-out/kozo.img",
    });
    mkimage.step.dependOn(&mkinitrd.step);
    mkimage.step.dependOn(&kernel.step);
    
    step.dependOn(&mkimage.step);
    return step;
}

// === QEMU TESTING ===

fn addQemuStep(b: *Builder, image: *std.Build.Step, telemetry: bool) *std.Build.Step {
    const step = b.allocator.create(std.Build.Step) catch unreachable;
    step.* = std.Build.Step.init(.{
        .id = .custom,
        .name = "qemu-smoke",
        .owner = b,
        .makeFn = struct {
            fn make(s: *std.Build.Step, _: *std.Progress.Node) !void {
                const bld = s.owner;
                std.log.info("Booting KOZO {s} in QEMU...", .{KOZO_VERSION});
                
                var args = std.ArrayList([]const u8).init(bld.allocator);
                try args.appendSlice(&[_][]const u8{
                    "qemu-system-x86_64",
                    "-machine", "q35",
                    "-cpu", "host,-smap",
                    "-m", "128M",
                    "-drive", "format=raw,file=zig-out/kozo.img",
                    "-serial", "stdio",
                    "-no-reboot",
                    "-nographic",
                });
                
                if (telemetry) {
                    try args.appendSlice(&[_][]const u8{
                        "-chardev", "file,id=errors,path=zig-out/panic.log",
                        "-device", "isa-serial,chardev=errors,index=1",
                    });
                }
                
                var child = std.ChildProcess.init(args.items, bld.allocator);
                child.stdin_behavior = .Ignore;
                child.stdout_behavior = .Pipe;
                child.stderr_behavior = .Pipe;
                
                try child.spawn();
                
                var buf: [4096]u8 = undefined;
                var output = std.ArrayList(u8).init(bld.allocator);
                defer output.deinit();
                
                const stdout = child.stdout.?;
                var found_prompt = false;
                var found_policy = false;
                var found_ipc = false;
                
                const deadline = std.time.milliTimestamp() + 30000; // 30s timeout
                while (std.time.milliTimestamp() < deadline) {
                    const n = try stdout.read(&buf);
                    if (n == 0) break;
                    try output.appendSlice(buf[0..n]);
                    
                    const out = output.items;
                    
                    if (!found_prompt and std.mem.indexOf(u8, out, "Init>") != null) {
                        found_prompt = true;
                        std.log.info("✓ Init prompt reached", .{});
                    }
                    if (!found_policy and std.mem.indexOf(u8, out, "Policy: ready") != null) {
                        found_policy = true;
                        std.log.info("✓ Policy Service registered", .{});
                    }
                    if (!found_ipc and std.mem.indexOf(u8, out, "IPC_OK") != null) {
                        found_ipc = true;
                        std.log.info("✓ IPC test passed", .{});
                    }
                    if (found_prompt and found_ipc and found_policy) {
                        _ = std.os.kill(child.id, std.os.SIG.TERM) catch {};
                        break;
                    }
                    if (std.mem.indexOf(u8, out, "PANIC") != null) {
                        std.log.err("Kernel panic detected", .{});
                        _ = std.os.kill(child.id, std.os.SIG.KILL) catch {};
                        return error.KernelPanic;
                    }
                }
                
                _ = try child.wait();
                
                if (!found_prompt or !found_ipc or !found_policy) {
                    std.log.err("Smoke test failed (prompt={}, policy={}, ipc={})", 
                        .{ found_prompt, found_policy, found_ipc });
                    return error.SmokeTestFailed;
                }
                
                std.log.info("SUCCESS: KOZO {s} smoke test passed", .{KOZO_VERSION});
            }
        }.make,
    });
    
    step.dependOn(image);
    return step;
}

fn generateDebugSymbols(b: *Builder, kernel: *std.Build.CompileStep, arch: Arch) *std.Build.Step {
    const step = b.step("debug-symbols", "Extract debug symbols for CI");
    
    const objcopy = b.addSystemCommand(&[_][]const u8{
        "objcopy", "--only-keep-debug",
        kernel.getEmittedBin().?.path,
        b.fmt("zig-out/kozo-kernel-{s}.debug", .{@tagName(arch)}),
    });
    
    step.dependOn(&objcopy.step);
    return step;
}

// === UTILITIES ===

fn resolveTarget(b: *Builder, arch: Arch) CrossTarget {
    _ = b;
    _ = arch;
    return CrossTarget{
        .cpu_arch = .x86_64,
        .os_tag = .freestanding,
        .abi = .none,
    };
}

const Arch = enum { x86_64, aarch64 };