# KOZO OS Changelog

All notable changes to the KOZO operating system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to the following versioning scheme:

- **Release versions:** `x.0.0` - Production releases (1.0.0, 2.0.0, etc.)
- **Major versions:** `0.x.0` - Significant milestones (0.1.0, 0.2.0, etc.)
- **Minor versions:** `0.0.x` - Development iterations (0.0.1, 0.0.2, etc.)

---

## [0.0.1] - 2026-02-28

### Status
Development pre-alpha - Genesis Block

### Overview
Initial project scaffolding and foundational architecture for the KOZO capability-based microkernel operating system. This version establishes the build system, kernel architecture, and service framework, with significant implementation work remaining.

### Added

#### Build System
- Zig-based master build system (`build.zig`) with ABI lockstep generation
- Automatic generation of synchronized ABI headers (`kozo_abi.h`) and Rust modules (`abi.rs`)
- Toolchain validation for Zig 0.13.0 and Rust 1.77.0
- Cargo workspace configuration for Rust services
- Custom target specification generation for `x86_64-kozo-none`
- Initrd creation via `scripts/mkinitrd.sh` (CPIO packaging)
- Bootable disk image creation via `scripts/mkimage.sh`
- QEMU smoke test integration with JUnit XML output
- Reproducible build support via `SOURCE_DATE_EPOCH`

#### Kernel (Layer 0 - Zig)
- Kernel main entry point (`kernel/src/main.zig`) with BootInfo handling
- Capability system foundation (`kernel/src/capability.zig`):
  - CNode (Capability Node) structure for capability tables
  - CapSlot structure with type, rights, and badge
  - SYS_RETYPE: Convert Untyped memory to kernel objects
  - SYS_CAP_TRANSFER: Move/copy capabilities between CNodies
  - SYS_CAP_MINT: Create attenuated child capabilities
  - SYS_CAP_REVOKE: Destroy capabilities recursively
  - SYS_CAP_VERIFY: Badge authenticity verification
  - Badge generation with anti-forgery mixing
- Syscall dispatcher (`kernel/src/syscall.zig`):
  - Syscall number validation (0-99)
  - Capability syscall routing
  - IPC architecture (CALL/REPLY/SEND/RECV) - architected
  - Thread lifecycle syscalls (create, resume, suspend, set_priority)
  - Endpoint management (create, delete, namespace_register)
  - Debug syscalls (DEBUG_PUTCHAR, DEBUG_DUMP_CAPS)
- Architecture placeholders:
  - `kernel/arch/x86_64/boot.S` (multiboot2 header stub)
  - `kernel/arch/x86_64/linker.ld` (higher half linker script stub)
  - `kernel/arch/x86_64/context.S` (context switch placeholder)
  - `kernel/arch/x86_64/ipc.S` (IPC fast path placeholder)
  - `kernel/arch/x86_64/trap.S` (IDT/syscall entry placeholder)

#### Services (Layer 1 - Rust)
- kozo-sys system interface library:
  - Complete syscall wrappers in inline assembly
  - Type-safe capability handles (CapHandle, CNodeHandle, EndpointHandle)
  - TypedCapability trait for zero-cost abstractions
  - no_std, no_main compatible
- Init Service (`services/init/src/main.rs`):
  - BootInfo parsing from kernel
  - Capability bootstrap demonstration
  - Policy CNode creation via RETYPE
  - Policy Endpoint creation and transfer
  - Serial debug output
- Policy Service architecture (`services/policy/src/main.rs`):
  - Event loop structure for capability requests
  - Triple-Check authorization flow (Request → Validate → Consent → Delegate)
  - Request/Response message types
  - Risk assessment framework structure
- FSD (Filesystem Daemon) stub (`services/fsd/src/main.rs`)

#### Documentation
- Project manifesto (`docs/MANIFESTO.md`) - Core principles and philosophy
- High-level architecture specification (`docs/spec/ARCHITECTURE.md`)
- Application architecture specification (`docs/spec/APPLICATION_ARCHITECTURE.md`)
- Build system specification (`docs/spec/BUILD_SYSTEM.md`)
- Infrastructure and reliability specification (`docs/spec/INFRASTRUCTURE.md`)
- Integrated toolchain specification (`docs/spec/INTEGRATED_TOOLCHAIN.md`)
- Project README with structure overview

#### ABI Definition
- 20 syscall numbers defined (capability, IPC, threading, endpoints, memory, debug)
- Capability types: Null, Untyped, CNode, Endpoint, Thread, AddressSpace, Frame, PageTable, IrqHandler
- Rights bitmask: READ, WRITE, GRANT, MAP
- Error codes: OK, Invalid, NoCap, NoMem, AccessDenied, NoSpace
- Constants: INIT_UNTYPED_SIZE (16MB), ROOT_CNODE_SIZE_BITS (12), IPC_BUFFER_SIZE (512)

### Known Limitations

#### Critical Blockers
- **Assembly stubs are empty**: boot.S, context.S, ipc.S, trap.S contain only file headers
- **Scheduler not implemented**: `kernel/src/scheduler.zig` is empty (3 lines)
- **Thread Control Blocks incomplete**: `kernel/src/thread.zig` has empty TCB struct
- **Memory mapping stubbed**: map_frame/unmap_frame not implemented
- **Cannot boot to user mode**: No path from kernel entry to Init service execution

#### Service Gaps
- Policy Service does not compile (references non-existent types: IPCBuffer, Endpoint)
- FSD missing Cargo.toml and implementation
- No actual binary loading from initrd
- No service manager functionality in Init

#### Hardware Support
- x86_64 assembly layer incomplete
- No interrupt controller (x2APIC) support
- No timer implementation
- No serial driver (only debug port access)
- aarch64 architecture defined but no implementation

### Security Notes
- Capability model properly designed with rights attenuation
- Badge generation uses simple mixing (not cryptographically secure for production)
- Memory zeroing on retype prevents information leakage
- Zero-heap kernel design eliminates resource exhaustion attacks

### Dependencies
- Zig 0.13.0 (strictly enforced)
- Rust 1.77.0 (strictly enforced)
- QEMU (for testing)
- ld.lld (linker)
- cpio (for initrd creation)
- objcopy (for debug symbols)

### Next Steps (0.0.2 Target)
1. Implement x86_64 assembly stubs (boot, context switch, IPC, traps)
2. Complete scheduler with round-robin queue
3. Implement Thread Control Block structure
4. Add memory mapping (page table walking)
5. Fix Policy Service compilation
6. Implement initrd binary loading
7. Pass QEMU smoke test

---

## Version History

| Version | Date | Status | Codename |
|---------|------|--------|----------|
| 0.0.1 | 2026-02-28 | Development pre-alpha | Genesis Block |

---

*This changelog is immutable. All entries are permanent records of the project's evolution.*
