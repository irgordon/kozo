# KOZO Kernel: Agent Protocol

This directory contains the **KOZO microkernel implementation**.

The kernel must remain small, deterministic, and isolated from userspace logic.

Agents modifying kernel code must follow the rules below.

---

# 1. Language

The kernel is written in **Odin only**.

Rules:

- Do not introduce Zig, C++, Go, Python, or other languages into the kernel.
- Assembly is allowed only when required for architecture primitives.
- Kernel code must compile with:

```

odin check

```

---

# 2. Kernel Scope

The kernel must implement only the following responsibilities:

- hardware abstraction
- scheduler
- capability enforcement
- virtual memory management
- IPC primitives
- syscall dispatch

Everything else belongs in **userspace services**.

The kernel must not implement:

- filesystems
- networking stacks
- device policy
- application logic

---

# 3. Memory Discipline

Memory ownership must always be explicit.

Rules:

- Kernel procedures must accept **allocators as parameters** when allocation is required.
- Global allocators are prohibited unless explicitly documented.
- Memory lifetimes must be visible in the call graph.

Implicit allocation is forbidden.

---

# 4. Error Handling

Kernel errors must be explicit.

Rules:

- Use return values for failure states.
- Do not use panic for recoverable conditions.
- Panics are allowed only for **irrecoverable kernel invariants**.

Kernel paths must never rely on exception-style control flow.

---

# 5. Capability Security

All resource access must be capability-based.

Rules:

- Kernel objects are never exposed directly to userspace.
- Userspace must interact through **capability handles**.
- Capabilities must be validated on every syscall boundary.

Pointer-based authority is forbidden.

---

# 6. ABI Discipline

Kernel ABI must remain stable and explicit.

Rules:

- ABI definitions originate from `contracts/`.
- Generated bindings appear in:

```

bindings/odin/
bindings/rust/

```

Agents must not modify generated bindings manually.

All kernel/user boundaries must use **C ABI compatible types**.

---

# 7. Deterministic Behavior

Kernel behavior must be predictable.

Rules:

- No hidden global state.
- No random values.
- No time-based logic outside scheduler primitives.
- No environment-dependent behavior.

Kernel logic must be reproducible.

---

# 8. Function Design

Kernel functions must follow strict design rules.

Rules:

- Maintain **single level of abstraction** within a function.
- Prefer small composable procedures.
- Avoid deeply nested control flow.
- Keep functions short and explicit.

---

# 9. Synchronization

Concurrency must be explicit.

Rules:

- Do not introduce implicit shared state.
- All synchronization primitives must be documented.
- Lock ordering must be deterministic.

Deadlock-prone patterns must be avoided.

---

# 10. Fail Closed

If kernel invariants cannot be guaranteed, the kernel must stop.

Do not silently recover from corrupted state.

A controlled halt is safer than undefined behavior.
```

---

### After adding this file your repo hierarchy will look like:

```
KOZO/
├─ AGENTS.md
├─ harness/
│  └─ AGENTS.md
├─ kernel/
│  └─ AGENTS.md
```

This gives the agent **three layers of discipline**:

| Scope   | Controls                 |
| ------- | ------------------------ |
| Global  | architecture + workflow  |
| Harness | deterministic protocol   |
| Kernel  | microkernel safety rules |

---

### One final small recommendation

Add **one more rule** to the root `AGENTS.md` later:

```
Never modify generated files directly.
Always modify the source generator instead.
```

That single rule prevents **~50% of agent mistakes in real projects**.
