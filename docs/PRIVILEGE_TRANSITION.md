# KOZO Bounded Privilege Transition

Version: 1
Status: Authoritative
Scope: One fixed x86_64 CPL0-to-CPL3 probe and governed CPL0 return

---

# 1. Purpose

This document defines the v0.8.4 bounded privilege-transition boundary.

The authoritative machine-readable policy is
`contracts/bounded_privilege_transition_probe_contract.v0.json`. This
document explains that policy; it does not replace it.

# 2. Architecture

KOZO uses one transition mechanism:

```text
CPL0
-> fixed iretq frame
-> fixed CPL3 probe
-> int 0x81 DPL3 interrupt gate
-> TSS.RSP0 CPL0 stack
-> fixed CPL0 continuation
```

No alternative transition, arbitrary target, dynamic selector, or
caller-selected continuation is accepted.

# 3. Descriptor Geometry

The fixed GDT contains seven entries: null, kernel code, kernel data, user
data, user code, and the two-entry TSS descriptor. The selectors are:

| Role | Selector |
| --- | ---: |
| Kernel code | `0x08` |
| Kernel data | `0x10` |
| User data | `0x1b` |
| User code | `0x23` |
| TSS | `0x28` |

The GDT is 56 bytes and 16-byte aligned. The 104-byte TSS is 16-byte aligned,
sets `RSP0` to `privilege_return_stack_top`, sets IST1 to
`double_fault_stack_top`, and leaves its I/O bitmap outside the TSS limit.
The task register and descriptor-table registers are read back before entry.

The fixed 4096-byte IDT is 4096-byte aligned. Vector `0x81` is the only DPL3
gate and targets `privilege_return_handler`. Consequential architectural
fault vectors target non-returning halt sinks; this is fault containment, not
general exception recovery.

# 4. Stack Ownership

The accepted fixed user stack remains:

```text
0x0000400000002000
through
0x0000400000003000
```

The initial user RSP is `0x0000400000002ff0`. The privilege return stack and
double-fault stack are separate 4096-byte, 4096-byte-aligned,
supervisor-only RW-NX regions. None overlaps the boot stack, user stack,
fixed page tables, or user data.

# 5. Fixed Probe

The linked `user_privilege_probe_start` symbol is the only permitted CPL3
target. Before `iretq`, Ring 0 validates its fixed RX mapping, the fixed RW-NX
user data and stack mappings, the supervisor-only return structures, and the
sanitized frame.

The CPL3 stub validates the RPL bits read from CS, performs a bounded stack
push/pop probe, writes and reads the fixed token `0x4b4f5a4f50524956` at the
governed user-data address, and invokes `int 0x81`. It performs no serial I/O.

# 6. Return Boundary

The interrupt gate switches to `privilege_return_stack_top` through TSS.RSP0.
The handler validates the saved CPL3 CS, SS, RIP, RSP, and RFLAGS; validates
the probe token; clears and reads back the token; emits
`KOZO_RING3_PROBE_OK` only after those checks; restores the saved kernel RSP;
and jumps to `privilege_ring0_continuation`.

The continuation validates CPL0, the kernel data selector, the exact restored
stack, the success state, and the cleared token. It returns only exact status
zero to `_start`. Unknown or malformed state converges on
`boot_terminal_halt`.

# 7. Evidence

The ordered boundary is:

```text
KOZO_USER_MAPPING_SURVIVAL_OK
KOZO_PRIVILEGE_TRANSITION_INIT_START
KOZO_PRIVILEGE_TABLES_OK
KOZO_RING3_ENTER
KOZO_RING3_PROBE_OK
KOZO_RING0_RETURN_OK
KOZO_RUNTIME_PROGRESS_ENTRY
```

`KOZO_RING3_ENTER` records that the fixed frame is validated and the next
instruction transfers with `iretq`. `KOZO_RING3_PROBE_OK` is emitted by the
CPL0 handler only after it validates the hardware-saved CPL3 frame and the
CPL3-written probe state. It is not a Ring 0 substitute for unexecuted Ring 3
work.

Source, contract, ELF, and QEMU evidence are all required for final
acceptance. Generated reports remain evidence and are not authority.

# 8. Failure Behavior

The implementation distinguishes GDT, TSS, IDT, user-entry, user-stack,
return-frame, user-probe, and Ring0-continuation failures. Failures do not emit
later success markers, do not enter Odin, do not return to Ring 3, and do not
fall through. Every failure converges on the terminal halt path.

# 9. Claim Boundary

This phase proves one fixed CPL0-to-CPL3 `iretq` transition, one fixed CPL3
stack and data probe, one DPL3 interrupt-gate return using TSS.RSP0, validation
of the saved CPL3 frame, restoration of the fixed CPL0 continuation, and
continued execution of the accepted Odin capability path.

It does not prove general userspace execution, arbitrary user code, process or
address-space isolation, a public syscall ABI, `syscall`/`sysret`, return to
Ring 3, general interrupt handling, exception recovery, scheduling, user ELF
loading, Linux or POSIX compatibility, or production readiness.
