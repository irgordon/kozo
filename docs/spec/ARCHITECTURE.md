# KOZO: High-Level Architectural Specification

**Project Philosophy:** A capability-oriented microkernel leveraging Zig's low-level precision for the trusted computing base (TCB) and Rust's safety for high-layer logic and application platforms.

---

## 1. Core Architectural Pillars
* **Microkernel Architecture:** Minimal mechanisms in kernel-space; policy in user-space.
* **Security Models:** Defense in Depth, Zero Trust, and Capability-Based Access Control (CBAC).
* **Memory Model:** Pure "Untyped" memory retyping (seL4-style). The kernel has no dynamic heap.
* **Orchestration:** Integrated Zig/Rust build system with strict ABI lockstep verification.
* **Design Patterns:** Strict adherence to **SOLID** principles and **Single Layer Abstraction (SLA)**.

---

## 2. Design Model Comparison

| Model | Kernel Role | Performance | Security / Isolation | Ease of Adding Services |
| :--- | :--- | :--- | :--- | :--- |
| **Microkernel (KOZO)** | Minimal mechanisms only | High (Direct Switch IPC) | **Very High** (Zero-heap TCB) | **High** (Userspace servers) |
| **Hybrid** | Kernel + select servers | High | Medium | Medium |
| **Monolithic** | Drivers & services in kernel | Highest | Lower (Large TCB) | Low (Kernel changes req.) |

---

## 3. Kernel Layer (Zig)
**Role:** The lowest, most-trusted layer providing fundamental mechanisms.

### Core Responsibilities
* **Hardware Abstraction:** CPU bring-up, exception/interrupt handling, x2APIC/GICv3 routing.
* **Memory Primitives:** Fixed-memory management. Initial RAM is wrapped in "Untyped" capabilities.
* **Retyping Logic:** Atomic conversion of Untyped memory into Kernel Objects (CNodes, Threads, IPC Endpoints).
* **Communication:** Optimized **Direct-Switch IPC**. Context switching occurs during the syscall without entering the scheduler loop for `IPC_CALL` operations.
* **Security:** Capability store (CNodes) with strict, unforgeable 64-bit handles.

### Rationale for Zig
* **Explicitness:** No hidden allocations. Perfect for a zero-heap kernel.
* **Orchestration:** Zig acts as the master build system for the entire multi-language stack.

---

## 4. Userspace Layer (Rust)
**Role:** Policy, high-level logic, and the application execution platform.

### Service Decomposition
* **Init (Service Manager):** The "Genesis" task. Receives initial Untyped caps and partitions system resources.
* **Driver Servers:** Each device (NVMe, NIC) runs in an isolated address space with specific hardware capabilities.
* **Filesystem Servers (FSD):** Modular VFS implementations (e.g., RAMFS, Native KOZO) communicating via IPC.
* **Linux Compatibility Shim:** Intercepts standard Linux syscalls and translates them to KOZO capability-checked IPC.

### Rationale for Rust
* **Safety:** Eliminates use-after-free and data races in complex system services.
* **Ecosystem:** Leverages `no_std` crates for specialized logic like filesystem parsing or network stacks.

---

## 5. System Integration & Toolchain
KOZO employs a **Single Source of Truth** for its ABI.

* **ABI Lockstep:** The build system automatically generates synchronized C and Rust modules for syscall numbers and capability types.
* **Reproducible Pipeline:** Deterministic binary generation via `SOURCE_DATE_EPOCH`.
* **Integrated Fuzzing:** Continuous fuzzing of the IPC boundary and the Linux Shim during the build/CI phase.

---

## 6. Security & Defense in Depth
* **Zero-Heap TCB:** By removing the kernel heap, we eliminate an entire class of resource exhaustion attacks.
* **Clear-Name Capabilities:** User-facing permissions (e.g., `wifi.configure`) map to narrow kernel capability handles.
* **Privacy-Preserving Telemetry:** Anonymized, hashed error reporting that separates diagnostic data from user identity.

---

## 7. Development Roadmap (Updated)
1.  **Phase 1: Genesis Block (Current):** Bootable Zig kernel, ABI lockstep, Rust `Init` bootstrap, and Smoke Test IPC.
2.  **Phase 2: Capability Refinement:** Full implementation of `RETYPE`, `REVOKE`, and CNode depth management.
3.  **Phase 3: Service Foundations:** Virtual Memory Manager (VMM) and basic Driver Framework in Rust.
4.  **Phase 4: Compatibility:** Implementation of the first 50 core Linux syscalls via the Shim.
5.  **Phase 5: User Interface:** Integration of COSMIC services and the "Clear-Name" permission prompt system.
