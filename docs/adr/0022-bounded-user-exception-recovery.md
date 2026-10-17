# ADR-0022: Bounded User Exception Recovery

## Status

Accepted

## Context

The fixed Rust transaction can fail through its normal return boundary, but
cannot return supervisor control after a Rust instruction fault. The existing
generic #PF/#GP sinks halt without clearing the live context. This is a
pre-existing discrepancy with the formerly unconditional clearing language in
INVARIANTS section 21, not evidence that those sinks performed cleanup.

## Decision

Authorize one exact Rust-owned CPL3 UD2 anchor in compile-time fixtures only.
The new bounded exception contract owns the complete authorization predicate,
record, stages, rejection precedence and executable controls. The linker
derives the authorized RIP; pinned compiler output determines the exact stack.
Production has no enabled fault site or fixture hook and retains identical
user-code page bytes. The vector-6 DPL0 gate uses the same handler in both.

The fixture normalizes live flags to 0x2 immediately before UD2. The processor
sets RF in its saved fault frame; exact exception-frame flags are 0x10002.
Existing USER_RFLAGS and int 0x81 frame checks remain exactly 0x2. No RF mask
or alternative saved value is accepted.

An authorized exception restores trusted supervisor control, commits and
clears through the existing failure wrapper once, verifies cleanup, and
returns failure to Odin. A separate 64-byte supervisor evidence record advances
through five validated stages. Only Odin's validated observation permits the
recovery-complete diagnostic. Faulting Rust never resumes.

Rejected exceptions do not return through a saved continuation or commit a
trusted lifecycle result. Where supervisor execution and fixed context memory
are usable, a stack-independent fixed-address sequence clears authority,
retains version 1/size 128/lifecycle CLEARED, verifies readback and halts.
A specifically demonstrated unsafe supervisor condition permits emergency
halt without claiming cleanup. This is a limitation, never recovery success.

## Consequences

INVARIANTS sections 17 and 21 distinguish this bounded failure return from
ordinary transaction success and distinguish verified rejection clearing from
emergency halt. Generic #PF/#GP sinks remain historical terminal behavior;
their existing cleanup discrepancy is not repaired or concealed by this task.
No general exception framework, resumed Rust, new mapping, public ABI,
scheduler, extended-state switching or release is authorized. Normal runtime
remains two sessions, four int 0x81 returns and 52 success occurrences.

## Affected Governance, Contracts and Validators

INVARIANTS, ARCHITECTURE, SECURITY_MODEL, CONTRACTS, VALIDATION and
GENERATED_ARTIFACTS describe the new boundary. Source, linked-machine-code,
compiled stack, hardware frame, recovery stages and downloaded hosted fixture
evidence must agree. Missing evidence fails closed; the aggregate remains 67.

## Superseded Decisions

Only unconditional terminal handling of the precisely authorized vector-6
fixture fault changes. ADRs 0017, 0018, 0020 and 0021 otherwise remain in force.
