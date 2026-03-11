# KOZO Operating System Architecture

Version: 1  
Status: Authoritative  
Scope: Kernel structure, system boundaries, and runtime interaction model

---

# 1. Overview

KOZO is a **capability-oriented microkernel operating system** designed for high integrity, deterministic behavior, and strict interface boundaries.

The system is divided into **three primary layers**:

1. **Kernel Layer (Odin)**
2. **Userspace Services Layer (Rust)**
3. **Harness and Validation Layer (Python)**

Each layer has clearly defined responsibilities and communicates through explicit contracts.

The design goal is to keep the **trusted computing base minimal**, while enforcing correctness through deterministic validation.

---

# 2. System Layers

## 2.1 Kernel Layer

Location:

```

/kernel

```

Language:

```

Odin

```

Responsibilities:

- hardware abstraction
- scheduler
- capability enforcement
- virtual memory management
- interprocess communication
- syscall dispatch

The kernel must remain **small and deterministic**.

The kernel must not implement:

- filesystems
- network stacks
- device policy
- application logic

These belong in userspace services.

---

## 2.2 Userspace Services Layer

Location:

```

/userspace

```

Language:

```

Rust

```

Responsibilities:

- system services
- device drivers
- runtime libraries
- higher-level system components

Userspace services interact with the kernel exclusively through the **KOZO ABI contract**.

Rust is used to provide **memory-safe implementations** of system services.

All kernel-facing Rust code must be compatible with:

```

no_std

```

---

## 2.3 Harness Layer

Location:

```

/harness
/scripts

```

Language:

```

Python

```

Responsibilities:

- validation of repository changes
- artifact schema validation
- deterministic verification pipeline
- agent execution control

The harness is **not part of the operating system runtime**.  
It exists to enforce correctness during development.

---

# 3. Interface Contracts

All system boundaries are defined through **explicit contracts**.

Contracts live in:

```

/contracts

```

The authoritative ABI contract file is:

```

contracts/kozo_abi.h

```

Bindings are generated from this contract into:

```

bindings/odin/
bindings/rust/

```

Agents must **never modify generated bindings directly**.

---

# 4. Capability Model

KOZO uses a **capability-based security model**.

Capabilities represent permission to interact with kernel objects.

Examples:

- memory regions
- IPC endpoints
- scheduling rights
- device handles

Rules:

- capabilities are opaque to userspace
- kernel object pointers are never exposed
- capability validation occurs at every syscall boundary

Capabilities prevent pointer forgery and enforce isolation.

---

# 5. System Call Interface

Userspace communicates with the kernel through **syscalls**.

Syscalls follow these principles:

- fixed ABI signatures
- explicit parameter validation
- capability verification
- deterministic return values

Kernel functions must never trust userspace pointers without validation.

---

# 6. Memory Model

KOZO uses explicit memory ownership.

Kernel rules:

- memory allocators must be passed explicitly
- global allocators are prohibited unless documented
- ownership and lifetime must be visible

Userspace memory must be validated before kernel access.

---

# 7. Scheduling Model

The kernel scheduler is responsible for:

- thread execution
- CPU time allocation
- context switching

Scheduling decisions must remain deterministic.

Policy-level scheduling behavior may be implemented in userspace services.

---

# 8. Interprocess Communication

IPC is a core microkernel primitive.

IPC mechanisms provide:

- message passing
- synchronization
- capability transfer

IPC must remain:

- deterministic
- bounded
- capability-controlled

---

# 9. Determinism Guarantees

KOZO prioritizes deterministic behavior.

The kernel must avoid:

- hidden global state
- implicit allocation
- unpredictable scheduling behavior
- environment-dependent execution

Every kernel path must be auditable and reproducible.

---

# 10. Build and Verification Pipeline

Development changes are validated by the **KOZO harness**.

Validation includes:

- schema verification
- protocol compliance
- validator execution
- toolchain checks

Changes must pass verification before integration.

---

# 11. Development Principles

KOZO development follows these principles:

- minimal trusted computing base
- strict interface boundaries
- explicit resource ownership
- deterministic system behavior
- capability-based security

Architecture changes require documentation through an **Architecture Decision Record (ADR)**.

---

# 12. Future Extensions

The architecture supports extension through userspace services.

Examples:

- filesystem servers
- networking stacks
- device management services
- userland runtime environments

These services remain outside the kernel to preserve microkernel integrity.

---

# 13. Architectural Summary

KOZO enforces separation of concerns across three domains:

| Layer | Language | Responsibility |
|------|---------|---------------|
| Kernel | Odin | hardware + core primitives |
| Services | Rust | system services |
| Harness | Python | validation and control |

The kernel remains minimal while the harness guarantees correctness during development.

This architecture ensures that KOZO can evolve while maintaining strict system integrity.
