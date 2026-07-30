# Engineering Overview

This page gives engineers a top-down map of v1.0.0. It explains why each
mechanism exists, where it is implemented, and how it is verified. Exact
addresses, structure layouts, and bit fields remain in the linked authoritative
documents.

## Architecture at a Glance

```text
boot image
-> assembly kernel entry
-> stack and memory initialization
-> CPU extended-state initialization
-> fixed page tables
-> descriptor and interrupt tables
-> Odin runtime initialization
-> controlled three-iteration loop
-> fixed Ring 3 entry
-> fixed request and runtime-status service
-> fixed response and Ring 3 consumption
-> governed Ring 0 return
-> two internal capabilities
-> terminal halt
```

## Runtime Progression

| Mechanism | What and why | Implementation | Verification |
| --- | --- | --- | --- |
| Boot image and entry | Limine loads the kernel; no later claim matters until `_start` and serial output execute | `scripts/build_boot_image.sh`, `linker/kernel.ld`, `kernel/arch/x86_64/boot.asm` | Boot-image metadata, ELF report, QEMU markers |
| Stack and memory | Establishes known storage before compiled code runs | `boot.asm`, `kernel/arch/x86_64/memory.asm` | Geometry validators and bounded write/read/restore evidence |
| CPU state | Enables x87 and SSE state required by generated Odin instructions | `boot.asm` | CPUID/control-state checks, ELF instruction evidence, SIMD marker |
| Odin runtime | Validates the bootstrap context and runs a bounded loop | `kernel/runtime_progression.odin` | Source, ELF call path, loop markers, exact return status |

## Memory Model

KOZO owns one fixed four-level page-table hierarchy. Kernel mappings remain
supervisor-only. Three fixed user pages provide executable code, writable data,
and a writable stack with write-or-execute protection.

This exists to support one controlled user-mode path without exposing kernel
leaves. It does not provide dynamic virtual memory, page-fault recovery, an
allocator, or separate process address spaces.

Implementation: `kernel/arch/x86_64/paging.asm` and `linker/kernel.ld`.
Verification: software page walks, effective-permission checks, CR3 readback,
ELF geometry, and QEMU survival markers. See [Paging](../PAGING.md).

## Privilege Boundary

Fixed GDT, TSS, and IDT state supports one `iretq` transition to Ring 3 and one
`int 0x81` return gate. The kernel validates the saved frame, fixed reason,
request geometry, response geometry, and continuation before proceeding.

This proves one bounded privilege round trip. It does not provide arbitrary
user code, a general syscall table, exception recovery, or hostile-code
containment.

Implementation: `kernel/arch/x86_64/privilege_transition.asm` and
`kernel/arch/x86_64/runtime_layout.inc`. Verification: descriptor geometry,
instruction and call-edge evidence, CPL checks, fixed marker order, and QEMU.
See [Privilege Transition](../PRIVILEGE_TRANSITION.md).

## Capability Model

The fixed user request asks for one runtime-status response. The kernel copies
and validates the request, formats a response from a shared Odin status
snapshot, copies it out, and validates its consumption after returning from
Ring 3.

After the user transaction, Odin runs two internal capabilities: a read-only
status query and one fixed READY-to-ACTIVE state transition. These operations
are explicit branches, not a general capability framework or public ABI.

Implementation: `kernel/runtime_progression.odin`,
`kernel/runtime_capability.odin`, and `privilege_transition.asm`. See
[User Request Boundary](../USER_REQUEST_BOUNDARY.md),
[User Response Consumption](../USER_RESPONSE_CONSUMPTION.md),
[User Runtime Status Service](../USER_RUNTIME_STATUS_SERVICE.md), and
[Runtime Capabilities](../RUNTIME_CAPABILITIES.md).

## Evidence Model

KOZO combines evidence because no single layer proves the complete behavior:

- contracts define required boundaries;
- source checks confirm ordering and failure structure;
- ELF checks confirm linked symbols, instructions, and geometry;
- QEMU serial markers confirm the ordered runtime path;
- generated reports record the reproducible result.

Generated proof is review evidence, not authority. See
[Validation](../VALIDATION.md), [Contracts](../CONTRACTS.md),
[Generated Artifacts](../GENERATED_ARTIFACTS.md), and
[Runtime Evidence](../RUNTIME_EVIDENCE.md).

## Fail-Closed Behavior

Every stage checks exact preconditions and status values. A failed check stops
before later success markers and converges on a fixed halt path. The terminal
halt also remains the normal end of the successful v1.0.0 demonstration.

This prevents partial work from being reported as success. It does not provide
general exception recovery or safe execution of arbitrary hostile code. See
[Security Model](../SECURITY_MODEL.md).

## Source Map

| Area | Primary source |
| --- | --- |
| Assembly entry, initialization, serial bridges, halt | `kernel/arch/x86_64/boot.asm` |
| Fixed page tables and user pages | `kernel/arch/x86_64/paging.asm` |
| GDT, TSS, IDT, Ring 3, request/response gate | `kernel/arch/x86_64/privilege_transition.asm` |
| Runtime ordering and controlled loop | `kernel/runtime_progression.odin` |
| Shared status and internal capabilities | `kernel/runtime_capability.odin` |
| Linker geometry | `linker/kernel.ld` |
| QEMU collection and classification | `scripts/qemu_smoke.sh` |
| Validators and generated proof | `harness/`, `contracts/`, `artifacts/` |

## Authoritative Documents

- [Architecture](../ARCHITECTURE.md)
- [Technical invariants](../INVARIANTS.md)
- [Contracts](../CONTRACTS.md)
- [Security model](../SECURITY_MODEL.md)
- [Compatibility limits](../COMPATIBILITY.md)
- [Validation](../VALIDATION.md)
- [Release evidence](../RELEASE_EVIDENCE.md)

## Current Architectural Limits

KOZO has no scheduler, persistent processes, preemption, general userspace,
general syscall interface, filesystem, drivers, networking, dynamic virtual
memory, executable loader, Linux or POSIX compatibility, hostile user-code
containment, stable public ABI, or production-ready application environment.
