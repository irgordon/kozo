---
title: KOZO OS Integrated Toolchain Specification
version: 0.0.1-dev
status: PRE-ALPHA
date: 2026-03-01
scope: Build System, ABI Generation, and Cross-Compilation
kernel: Zig (Microkernel)
user-space: Rust (Services)
---

# KOZO: OS Integrated Toolchain & ABI Specification

## 1. Architectural Alignment
The build system serves as the "Master Architect," enforcing the **Single Layer Abstraction** by generating language-agnostic interfaces for both Layer 0 (Kernel) and Layer 1 (Services).

* **ABI Synchronization:** Automatic generation of `kozo_abi.h` (C) and `abi.rs` (Rust).
* **Target Enforcement:** Custom JSON specs ensure Rust binaries are built with `-mmx,-sse` (Soft-float) to prevent kernel FPU state corruption.
* **Performance:** IPC is optimized via a 6-register fast-path, falling back to a 512-byte buffer only for bulk data or capability transfers.

---

## 2. IPC & Capability Lifecycle

KOZO uses a **Capability-Based Access Control** model. Every syscall requires a valid capability handle stored in the process's CNode.



### Syscall Mechanics
1.  **Fast Path:** Arguments 1-6 are passed in registers (`rdi`, `rsi`, `rdx`, `r10`, `r8`, `r9` on x86_64).
2.  **Slow Path:** Larger payloads use the `IPC_BUFFER_SIZE` (512 bytes) mapped in the thread's IPC buffer.
3.  **Validation:** The Zig kernel checks the capability index against the caller's CNode before allowing the operation.

---

## 3. Toolchain Matrix

| Component | Toolchain | Target Spec | Features |
| :--- | :--- | :--- | :--- |
| **Kernel** | Zig 0.12.0+ | `freestanding-none` | Stack Probes, No-FPU, x2APIC |
| **Services** | Rust Nightly | `kozo-none.json` | `build-std=core,alloc`, `-Z build-std-features` |
| **ABI** | Zig Custom Step | N/A | Generates C & Rust constants |

---

## 4. Boot & Initialization Flow

1.  **Zig Build:** Compiles kernel and generates ABI.
2.  **Cargo Build:** Compiles Rust services using `abi.rs`.
3.  **CPIO Pack:** `scripts/mkinitrd.sh` bundles Rust binaries into a RAM disk.
4.  **UEFI Wrap:** Kernel + Initrd are wrapped into a GPT disk image with an EFI System Partition (ESP).



---

## 5. Implementation Verification
* **ABI Consistency:** Verify `SYS_CAP_CREATE` is identical in `kozo_abi.h` and `abi.rs`.
* **Cross-Check:** Run `qemu-system-x86_64 -d int` to verify syscall traps hit the `ipc_fastpath.S` entry point.
