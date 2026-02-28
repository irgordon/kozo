---
title: KOZO OS Build System & Integration Specification
version: 0.0.1-dev
status: PRE-ALPHA
date: 2026-03-01
scope: Build Orchestration & Toolchain Integration
kernel: Zig (Microkernel)
user-space: Rust (Services)
---

# KOZO: OS Build System Specification

## 1. Architectural Alignment
The build system serves as the integration point for the **Layer 0 (Zig)** and **Layer 1 (Rust)** components. It ensures that the security invariants (like `ReleaseSafe` optimization levels) are applied consistently across the entire TCB.

* **Orchestrator:** Zig Build System (`build.zig`)
* **Sub-Orchestrator:** Cargo (invoked by Zig for the Rust Service Layer)
* **Artifacts:** Freestanding kernel ELF, Rust service binaries, CPIO initrd, and a bootable UEFI GPT image.

---

## 2. Dependency Graph & Lifecycle

The build process follows a strict linear dependency to ensure the **Single Layer Abstraction** is maintained during the construction of the boot image.



1.  **ABI Generation:** Zig generates the `kozo_abi.h` which defines the syscall constants and capability bitflags.
2.  **Rust Build:** Cargo builds the Service Layer using the generated ABI for FFI.
3.  **Kernel Build:** Zig builds the microkernel, incorporating architecture-specific assembly.
4.  **Image Assembly:** Scripts bundle the kernel and the Rust `initrd` into a UEFI-compatible disk image.

---

## 3. Security-Hardened Build Flags

To support **Defense in Depth**, the following build-time constraints are enforced:

| Layer | Language | Optimization Mode | Security Feature |
| :--- | :--- | :--- | :--- |
| **Kernel** | Zig | `ReleaseSafe` | Runtime bounds checks, no-FPU, Stack probes |
| **Services** | Rust | `release` | LTO (Thin), Panic=Abort, Stack protection |
| **Common** | ASM | N/A | NX (No-Execute) stack, PIE (Position Independent) |

---

## 4. Hardware Targets

| Architecture | CPU Features Enabled | Code Model |
| :--- | :--- | :--- |
| **x86_64** | x2APIC, NX, PAE | Kernel (Higher Half) |
| **aarch64** | V8A, GICv3 | Small/Kernel |

---

## 5. Verification & Testing
* **Unit Tests:** Logic testing of capability management (CNode logic) on host.
* **Integration Tests:** Automated QEMU execution with serial output monitoring.
* **Auditability:** `build.zig` emits full DWARF symbols for debugging, though the production image is stripped to reduce TCB surface.
