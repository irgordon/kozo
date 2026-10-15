# ADR-0021: Fixed Rust User Execution

## Status

Accepted

## Context

The accepted two-session argument transaction executes a linked NASM user
program. Rust code must now own request and response behavior at CPL3 while
the exact interrupt frames, wire version 2, mappings, and lifecycle remain
governed by their existing contracts. ADR 0019 remains reserved.

## Decision

Compile one no_std Rust object with pinned Rust 1.96.0 for
x86_64-unknown-none. Two assembly entry adapters call its fixed C entrypoints
with RSP aligned to 16 before call (8 modulo 16 on Rust entry). Each adapter
requires the returned stack to equal USER_INITIAL_RSP before the fixed
interrupt instruction; saved RIP, RSP, selectors and RFLAGS remain exact.
Unexpected or failed Rust completion deliberately produces an invalid fixed
transaction and converges on existing kernel rejection.

The linker owns final page padding. The Rust object's text and read-only data
join the existing assembly adapters inside one 4096-byte RX backing page.
Only PC-relative relocations to the object's own allocated read-only sections
are permitted. Undefined symbols, writable/TLS storage, absolute relocations,
unwind data and capacity overflow fail the build. This makes the higher-half
linked image valid under its fixed lower-half user alias.

Rust constructs the unchanged request and validates the full response and
digest. Odin retains all arithmetic and session policy. A bounded failure
diagnostic reports kernel rejection codes without adding success markers.

## Consequences

The same compiled Rust code runs twice at CPL3. The existing context, pages,
two-return budget, 52 marker occurrences, and terminal halt remain unchanged.
Source, object closure, linked bytes, exact frames, and hosted QEMU controls
must agree before acceptance. This introduces no process, loader, allocator,
general ABI, new interrupt, or runtime claim for Windows or macOS.

## Affected Governance and Contracts

ARCHITECTURE, SECURITY_MODEL, CONTRACTS and VALIDATION describe the ownership
change. fixed_rust_user_execution_contract.v0.json defines the bounded build,
placement, entry and failure evidence. Existing transport contracts remain
historical authorities and current runtime validators enforce the composed
Rust implementation. The invariant's fixed frame and memory rules are not
weakened.

## Superseded Decisions

Only assembly ownership of the user request and response program is replaced.
ADR 0017, ADR 0018, and ADR 0020 remain in effect.
