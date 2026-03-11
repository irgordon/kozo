# KOZO Contracts: Agent Protocol

This directory defines the **kernel ↔ userspace ABI contract**.

The contract is the authoritative interface between the kernel and all
external components. Changes here directly affect system compatibility.

Agents modifying files under `contracts/` must follow the rules below.

---

## 1. Authority

The ABI contract is defined by:

```

contracts/kozo_abi.h

```

This file is the **single source of truth** for:

- syscall signatures
- shared struct layouts
- numeric constants
- capability identifiers

Bindings in other languages are **generated from this contract**.

---

## 2. Generated Bindings

Bindings are produced from the contract into:

```

bindings/odin/
bindings/rust/

```

Rules:

- Generated files must **never be edited manually**.
- If a change is required, modify the contract or generator.
- Regenerate bindings after every contract change.

---

## 3. ABI Stability

The ABI must remain stable.

Agents must not:

- reorder struct fields
- change field sizes
- introduce implicit padding
- change constant values

These changes break compatibility.

If such changes are required, an **ABI version bump** must occur.

---

## 4. Allowed Types

The ABI must use **C ABI compatible types** only.

Allowed examples:

```

uint64_t
uint32_t
uint16_t
uint8_t
uintptr_t
int64_t

```

Do not introduce language-specific types.

---

## 5. Struct Layout

Structs must remain predictable.

Rules:

- field order must be explicit
- field types must be fixed-width
- layout must match across languages

Packed layout must only be used when explicitly required.

---

## 6. Capability Safety

Kernel object pointers must never cross the ABI boundary.

Userspace interacts with kernel objects through **capability handles only**.

The ABI must never expose:

- raw kernel pointers
- internal kernel structures
- scheduler internals

---

## 7. Fail Closed

If the contract cannot guarantee binary compatibility:

Stop.

Do not modify the contract until the ABI impact is fully understood.

Breaking the ABI can corrupt kernel/userspace interaction.