# ADR-0016: Kernel Entry and Syscall Bridge

## Status

Accepted

## Context

KOZO needs an explicit x86_64 execution bridge from assembly into the Odin kernel.
That bridge must establish a known stack state before the first Odin procedure runs
and must also define the first syscall trap handoff contract.

## Decision

- Canonical status statement: “KOZO executes a function-call trap path: Rust extern call → asm bridge → Odin dispatcher. This is not a hardware `syscall`/interrupt path and does not perform a privilege transition.”
- Entry point flow: `_start` (ASM) -> `kernel_entry` (Odin)
- Stack size: 16KB bootstrap stack
- Stack alignment: 16-byte aligned before calling `kernel_entry`
- Trap ingress registers:
  - `rax` carries the syscall identifier
  - `rbx` carries the heartbeat payload pointer
- Odin dispatcher signature: `syscall_dispatch(id, payload)`
- Bridge register mapping:
  - `mov rdi, rax`
  - `mov rsi, rbx`
- Preservation rules:
  - `rcx` and `r11` are saved and restored because the `syscall` instruction clobbers them
- Trap stack alignment: `rsp` is adjusted to remain 16-byte aligned before calling `syscall_dispatch`

The assembly side owns the raw machine entry symbols. The Odin side owns the
exported kernel entry and syscall dispatch procedures that the assembly bridge
targets.

## Consequences

- The assembly bridge can validate symbol presence independently of runtime boot.
- The kernel has a deterministic top-level entry path with an explicit calling convention.
- Future syscall expansion can build on the `rax`/`rbx` ingress rule without changing the bridge shape.
- Any future hardware trap work must be introduced as a new phase with separate verification before this canonical wording is changed.
