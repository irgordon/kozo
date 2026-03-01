# KOZO OS Changelog

All notable changes to the KOZO operating system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to the following versioning scheme:

* **Release versions:** `x.0.0` - Production releases (1.0.0, 2.0.0, etc.)
* **Major versions:** `0.x.0` - Significant milestones (0.1.0, 0.2.0, etc.)
* **Minor versions:** `0.0.x` - Development iterations (0.0.1, 0.0.2, etc.)

---

## [0.0.4] - 2026-03-01

### Status

Development pre-alpha - Preemptive Scheduling & VMM Integration

### Overview

Successfully implemented the Virtual Memory Manager (VMM) and established the foundation for preemptive multitasking. This version integrates the Local APIC timer, refines the context-switching mechanism for stack-based safety, and optimizes TCB management with O(1) allocation.

### Added

#### Memory Management

* **Virtual Memory Manager (VMM)**: Implemented recursive paging in `kernel/src/memory/vmm.zig`, enabling the kernel to manage page tables within a virtual window.
* **Dynamic Page Table Allocation**: Integrated on-demand allocation of intermediate page tables from the PMM.
* **Physical Reclamation**: Enhanced `sys_revoke` to traverse the capability derivation tree and return physical frames to the PMM.

#### Scheduling & Threading

* **Stack-based Context Switching**: Rewrote `switch_context` in `context.S` to save/restore registers directly on thread stacks, improving safety and supporting preemption.
* **O(1) TCB Allocation**: Implemented a Free List for the static TCB pool, eliminating O(N) allocation overhead.
* **APIC Timer Preemption**: Integrated the Local APIC timer (Vector 32) to trigger the scheduler's `yield` primitive, enabling preemptive multitasking.
* **Refined TCB**: Updated TCB structure to track `stack_ptr`, `cr3`, and `priority`.
* **Interrupt Dispatcher**: Created `kernel/src/arch/x86_64/traps.zig` to bridge assembly stubs to high-level Zig logic.

### Changed

* **Bootstrap Logic**: Refined the `switchTo` mechanism to safely bootstrap the first system thread.
* **IDT Configuration**: Updated `idt.zig` to use the assembly `trap_table` for robust exception and interrupt handling.
* **`spawnThread` API**: Added `priority` support to the thread creation interface.

### Next Steps (0.0.5 Target)

1. Implement the Idle Thread for background execution.
2. Setup user-mode stack and segment registers.
3. Switch from Genesis identity-mapping to a full higher-half kernel design.
4. Begin loading the `init` service from the CPIO initrd into its own address space.

---

## [0.0.3] - 2026-02-28

### Status

Development pre-alpha - UEFI & PMM Foundation

### Overview

Transitioned to a pure 64-bit UEFI boot architecture and implemented the foundational Physical Memory Manager (PMM). This version establishes spec-compliant memory map parsing and restores critical ABI synchronization between Zig and Rust layers. This version focuses on establishing a robust memory management foundation and transitioning the boot process to a more modern UEFI-compatible approach. The Physical Memory Manager (PMM) is introduced, providing a critical layer for dynamic memory allocation, and the boot process is refined to handle memory maps from UEFI.

### Added

#### Boot Process

* **UEFI Boot Support**: Implemented `kernel/arch/x86_64/boot.S` to parse UEFI memory map and boot information.
* **Multiboot2 Compatibility**: Ensured continued compatibility with Multiboot2 for broader bootloader support.
* **Early Console**: Integrated a basic VGA text mode driver for early boot debugging.
* **UEFI Loader Logic**: Integrated GOP, memory map, and ELF64 loading into the `boot/uefi` layer.

#### Memory Management

* **Physical Memory Manager (PMM)**: Implemented a bitmap-based frame allocator in `kernel/src/memory/pmm.zig`. Introduced `kernel/src/memory/pmm.zig` with a bitmap allocator for managing physical pages.
* `allocate_frame()`: Allocates a single 4KB physical page.
* `free_frame()`: Returns a physical page to the allocator.
* `allocate_contiguous()`: Allocates a block of contiguous physical pages.


* **UEFI Memory Map Parsing**: Added spec-compliant stride indexing using `descriptor_size` for robust memory map traversal.
* **BootInfo Contract**: Restored `common/boot_info.zig` as the "Sacred Contract" between the UEFI loader and the kernel.
* **BootInfo Parsing**: Enhanced `kernel/src/main.zig` to parse memory regions from the bootloader (UEFI/Multiboot2) and initialize the PMM.
* **Memory Region Tracking**: Implemented data structures to track available, reserved, and used physical memory regions.

#### ABI Synchronization

* **ABI Generator**: Created `scripts/gen_abi.zig` to automatically sync syscall numbers and constants to Rust.
* **Extended syscalls**: Added `SYS_MAP_MEMORY` syscall constant for future VMM integration.
* **Build System**: Restored the `abi` step in `build.zig` to ensure kernel/service lockstep.

#### Architecture Refinements

* **Pure 64-bit Trap Table**: Updated `trap.S` to prune the legacy `BOUND` instruction and implement a reserved trap table.
* **`kernel/src/memory/mod.zig`**: Centralized memory management module.
* **`kernel/src/arch/x86_64/idt.zig`**: Initial IDT setup for basic exception handling.

### Changed

* **Linker Script**: Updated `kernel/arch/x86_64/linker.ld` to support higher-half kernel mapping and proper section alignment for UEFI.
* **Boot Sequence**: Refactored `boot.S` to handle both UEFI and Multiboot2 entry points, passing a unified `BootInfo` structure to the Zig kernel.
* **Error Handling**: Improved early boot error reporting via VGA console.

### Removed

* **Redundant Code**: Deleted misplaced `kernel/src/syscall.zig.rs`.
* **Legacy Assembly**: Removed `trap_bound_range` (obsolete in long mode).

### Next Steps (0.0.4 Target)

1. Implement Virtual Memory Manager (VMM) with page table walking and recursive paging.
2. Wire up the first userspace capability from the PMM untyped pool.
3. Establish the higher-half kernel mapping using the new PMM frames.
4. Integrate APIC timer for preemptive scheduling.
5. Refine context switching for stack-based safety.
6. Implement O(1) TCB allocation using a free list.
7. Create an interrupt dispatcher to bridge assembly traps to Zig handlers.

---

## [0.0.2] - 2026-02-28

### Status

Development pre-alpha - Surgical Genesis Block

### Overview

Completed minimal x86_64 bring-up with higher-half kernel mapping. The kernel now successfully boots via PVH ELF Note, enters long mode, and executes Zig code in the higher-half virtual address space (0xffffffff80000000). This version marks a significant leap from mere placeholders to a functional, albeit minimal, kernel. The core x86_64 architecture components are now implemented, enabling a full boot sequence, basic trap handling, and the foundation for context switching. The memory layout has been refined for a higher-half kernel, and the build system has been hardened.

### Added

#### x86_64 Boot Architecture

* **PVH ELF Note**: Official Xen-compliant PVH entry point (type 18) for QEMU direct boot
* **Long Mode Entry**: Complete 32-bit to 64-bit transition with identity paging
* **Higher-Half Mapping**: Kernel mapped to 0xffffffff80000000 with proper PHDRS
* **Page Tables**: Identity map first 2MB using huge pages (2MB pages)
* **GDT Setup**: 64-bit code and data segments for long mode
* **Stack Pivot**: Transition from boot stack to higher-half kernel stack
* **BSS Zeroing**: Assembly routine to zero BSS before entering Zig

#### Assembly Implementation

* `kernel/arch/x86_64/boot.S`: Complete boot sequence with VGA heartbeat debugging
* `kernel/arch/x86_64/trap.S`: IDT setup, trap handlers, syscall entry point
* `kernel/arch/x86_64/context.S`: Context save/restore for callee-saved registers
* `kernel/arch/x86_64/linker.ld`: Surgical linker script with PT_NOTE/PT_LOAD PHDRS

#### Kernel Core (Zig)

* `kernel/src/abi.zig`: Zig-native ABI constants (syscall numbers, capability types)
* `kernel/src/spinlock.zig`: Minimal spinlock implementation with IRQ save/restore
* `kernel/src/thread.zig`: TCB structure with context, IPC state, capability roots
* `kernel/src/scheduler.zig`: Run queue with enqueue/dequeue/yield primitives
* `kernel/src/main.zig`: Hardened serial driver with LSR polling

#### Build System Fixes

* Zig 0.13.0 API compatibility updates
* Fixed `CompileStep` → `Step.Compile` naming
* Fixed `ChildProcess` → `process.Child` naming
* Added proper path handling with `b.path()`
* Simplified build.zig for kernel-only development

### Changed

#### Boot Process

* **Before**: Empty assembly stubs, no boot capability
* **After**: Full PVH boot chain from 32-bit entry to 64-bit Zig main

#### Memory Layout

* **Before**: Flat 1MB loading, no virtual memory
* **After**: Higher-half kernel at 0xffffffff80000000, identity-mapped boot

#### Linker Script

* **Before**: Basic section placement, overlapping sections
* **After**: Explicit PHDRS with PT_NOTE for PVH, PT_LOAD for segments

### Known Limitations

#### Remaining Blockers

* **Scheduler**: Basic structure present but not integrated with context switch
* **Threading**: TCB defined but thread creation not fully wired
* **IPC**: Architecture defined but fast path not implemented
* **Memory Mapping**: Page table walking not yet implemented
* **Serial Output**: VGA heartbeat works but serial port output pending verification

#### Next Steps (0.0.3 Target)

1. Integrate scheduler with context switch
2. Implement thread creation and management
3. Wire up IPC fast path
4. Implement page table walking for memory mapping
5. Verify serial output in QEMU
6. Begin Rust service integration

---

## [0.0.1] - 2026-02-28

### Status

Development pre-alpha - Genesis Block

### Overview

Initial project scaffolding and foundational architecture for the KOZO capability-based microkernel operating system. This version establishes the build system, kernel architecture, and service framework, with significant implementation work remaining.

### Added

#### Build System

* Zig-based master build system (`build.zig`) with ABI lockstep generation
* Automatic generation of synchronized ABI headers (`kozo_abi.h`) and Rust modules (`abi.rs`)
* Toolchain validation for Zig 0.13.0 and Rust 1.77.0
* Cargo workspace configuration for Rust services
* Custom target specification generation for `x86_64-kozo-none`
* Initrd creation via `scripts/mkinitrd.sh` (CPIO packaging)
* Bootable disk image creation via `scripts/mkimage.sh`
* QEMU smoke test integration with JUnit XML output
* Reproducible build support via `SOURCE_DATE_EPOCH`

#### Kernel (Layer 0 - Zig)

* Kernel main entry point (`kernel/src/main.zig`) with BootInfo handling
* Capability system foundation (`kernel/src/capability.zig`):
* CNode (Capability Node) structure for capability tables
* CapSlot structure with type, rights, and badge
* SYS_RETYPE: Convert Untyped memory to kernel objects
* SYS_CAP_TRANSFER: Move/copy capabilities between CNodies
* SYS_CAP_MINT: Create attenuated child capabilities
* SYS_CAP_REVOKE: Destroy capabilities recursively
* SYS_CAP_VERIFY: Badge authenticity verification
* Badge generation with anti-forgery mixing


* Syscall dispatcher (`kernel/src/syscall.zig`):
* Syscall number validation (0-99)
* Capability syscall routing
* IPC architecture (CALL/REPLY/SEND/RECV) - architected
* Thread lifecycle syscalls (create, resume, suspend, set_priority)
* Endpoint management (create, delete, namespace_register)
* Debug syscalls (DEBUG_PUTCHAR, DEBUG_DUMP_CAPS)


* Architecture placeholders:
* `kernel/arch/x86_64/boot.S` (multiboot2 header stub)
* `kernel/arch/x86_64/linker.ld` (higher half linker script stub)
* `kernel/arch/x86_64/context.S` (context switch placeholder)
* `kernel/arch/x86_64/ipc.S` (IPC fast path placeholder)
* `kernel/arch/x86_64/trap.S` (IDT/syscall entry placeholder)



#### Services (Layer 1 - Rust)

* kozo-sys system interface library:
* Complete syscall wrappers in inline assembly
* Type-safe capability handles (CapHandle, CNodeHandle, EndpointHandle)
* TypedCapability trait for zero-cost abstractions
* no_std, no_main compatible


* Init Service (`services/init/src/main.rs`):
* BootInfo parsing from kernel
* Capability bootstrap demonstration
* Policy CNode creation via RETYPE
* Policy Endpoint creation and transfer
* Serial debug output


* Policy Service architecture (`services/policy/src/main.rs`):
* Event loop structure for capability requests
* Triple-Check authorization flow (Request → Validate → Consent → Delegate)
* Request/Response message types
* Risk assessment framework structure


* FSD (Filesystem Daemon) stub (`services/fsd/src/main.rs`)

#### Documentation

* Project manifesto (`docs/MANIFESTO.md`) - Core principles and philosophy
* High-level architecture specification (`docs/spec/ARCHITECTURE.md`)
* Application architecture specification (`docs/spec/APPLICATION_ARCHITECTURE.md`)
* Build system specification (`docs/spec/BUILD_SYSTEM.md`)
* Infrastructure and reliability specification (`docs/spec/INFRASTRUCTURE.md`)
* Integrated toolchain specification (`docs/spec/INTEGRATED_TOOLCHAIN.md`)
* Project README with structure overview

#### ABI Definition

* 20 syscall numbers defined (capability, IPC, threading, endpoints, memory, debug)
* Capability types: Null, Untyped, CNode, Endpoint, Thread, AddressSpace, Frame, PageTable, IrqHandler
* Rights bitmask: READ, WRITE, GRANT, MAP
* Error codes: OK, Invalid, NoCap, NoMem, AccessDenied, NoSpace
* Constants: INIT_UNTYPED_SIZE (16MB), ROOT_CNODE_SIZE_BITS (12), IPC_BUFFER_SIZE (512)

### Known Limitations

#### Critical Blockers

* **Assembly stubs are empty**: boot.S, context.S, ipc.S, trap.S contain only file headers
* **Scheduler not implemented**: `kernel/src/scheduler.zig` is empty (3 lines)
* **Thread Control Blocks incomplete**: `kernel/src/thread.zig` has empty TCB struct
* **Memory mapping stubbed**: map_frame/unmap_frame not implemented
* **Cannot boot to user mode**: No path from kernel entry to Init service execution

#### Service Gaps

* Policy Service does not compile (references non-existent types: IPCBuffer, Endpoint)
* FSD missing Cargo.toml and implementation
* No actual binary loading from initrd
* No service manager functionality in Init

#### Hardware Support

* x86_64 assembly layer incomplete
* No interrupt controller (x2APIC) support
* No timer implementation
* No serial driver (only debug port access)
* aarch64 architecture defined but no implementation

### Security Notes

* Capability model properly designed with rights attenuation
* Badge generation uses simple mixing (not cryptographically secure for production)
* Memory zeroing on retype prevents information leakage
* Zero-heap kernel design eliminates resource exhaustion attacks

### Dependencies

* Zig 0.13.0 (strictly enforced)
* Rust 1.77.0 (strictly enforced)
* QEMU (for testing)
* ld.lld (linker)
* cpio (for initrd creation)
* objcopy (for debug symbols)

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
| --- | --- | --- | --- |
| 0.0.4 | 2026-03-01 | Development pre-alpha | Preemptive VMM & Scheduling |
| 0.0.3 | 2026-02-28 | Development pre-alpha | UEFI & PMM Foundation |
| 0.0.2 | 2026-02-28 | Development pre-alpha | Surgical Genesis |
| 0.0.1 | 2026-02-28 | Development pre-alpha | Genesis Block |

---