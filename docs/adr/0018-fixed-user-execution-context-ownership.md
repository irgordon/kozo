# ADR-0018: Fixed User Execution Context Ownership and Lifecycle

## Status

Accepted

## Context

KOZO already owns one fixed user code page, one fixed user data page, one
fixed user stack, one bounded Ring 3 entry, two `int 0x81` returns, one fixed
request and response transaction, and one governed Ring 0 continuation. Those
authorities are validated separately. No single kernel-owned record currently
binds them to one execution identity and one lifecycle.

Adding repeated execution, processes, or scheduling before defining that
ownership would make authority implicit in unrelated constants and mutable
transaction state. It would also leave cleanup and failure evidence without a
single governed boundary.

This decision defines governance prerequisites only. It does not implement the
context or claim new runtime evidence.

## Decision

KOZO will use exactly one statically allocated, supervisor-only Fixed User
Execution Context for the accepted one-shot user transaction.

Ring 0 exclusively creates, validates, activates, accounts, returns, and
clears the context. User mode cannot create, select, mutate, or clear the
identity, lifecycle, mappings, selectors, transition budget, transition
count, transaction phase, service identity, return target, or cleanup state.

The identity is a nonzero kernel-assigned opaque value. It is not a pointer,
PID, namespace member, reusable handle, or user-selected value. Its only
purpose is to prove that all lifecycle operations refer to the same bounded
execution authority.

The successful lifecycle is:

```text
UNINITIALIZED -> READY -> ACTIVE -> RETURNED -> CLEARED
```

`UNINITIALIZED` contains no authority. `READY` means every fixed binding and
reserved-zero rule has validated. `ACTIVE` owns the complete existing
two-return transaction. `RETURNED` means both governed returns and final
transaction state validated, but cleanup is still required. `CLEARED` means
the opaque identity and all authority-bearing bindings and counters have been
invalidated.

The permitted failure-cleanup edges are `READY -> CLEARED`,
`ACTIVE -> CLEARED`, and `RETURNED -> CLEARED`. Failure before `READY` remains
non-authoritative. No backward, skipped, or reuse transition is permitted.

Mutable authority and observable lifecycle result are separate structures.
The result contains only outcome, named failure, observed transition count,
terminal lifecycle point, and reserved-zero state. It contains no identity,
pointer, selector, mapping authority, or reusable handle. It survives context
cleanup only long enough for validation, governed evidence, and the existing
Odin continuation or terminal failure path. It must be reset before any future
initialization.

The transition budget is derived from the existing transaction rather than
chosen independently:

1. The request stub executes the first `int 0x81` while the kernel-owned phase
   is `REQUEST_PENDING`.
2. Ring 0 completes request/service/response work and changes the phase to
   `RESPONSE_READY` before resuming the fixed response consumer.
3. The response consumer executes the second `int 0x81`.
4. Ring 0 validates response consumption and changes the phase to `CONSUMED`.

The authorized transition budget is therefore two. Both phase and count must
match at each transition. A third transition is an invariant violation and
fails closed; it is not another request.

Context cleanup and result preservation are separate operations. Success
requires the result to be committed once, all authority-bearing context fields
to be invalidated, and the exact `CLEARED` representation to validate before
normal Odin continuation. Failure after authority exists must attempt the same
fail-closed invalidation and may not continue normally while authority remains.

The existing 41-marker taxonomy is sufficient. Future implementation evidence
must prove context source, contract, lifecycle, ELF ordering, and cleanup around
the existing markers. No marker is added or redefined by this decision.

## Why This Is Not a Process

The context has no PID, address-space ownership, scheduler state, concurrency,
resource allocation, executable loading, persistence, or multi-context
management. It binds one existing fixed transaction and cannot be reused in
this phase. Repeated sessions and process semantics require later decisions.

## Consequences

* Future implementation has one explicit supervisor-owned authority record.
* Every privilege return must validate identity, lifecycle, count, phase, and
  the already governed hardware frame.
* Cleanup cannot destroy the separate bounded result needed for evidence.
* Result data alone cannot authorize future execution.
* The implementation must measure context size, result size, ELF growth, stack
  impact, and bounded runtime impact.
* No CPU, RAM, storage, or development-workstation minimum changes.
* Linux remains the runtime-validation host. Windows and macOS remain build
  validation hosts with runtime `NOT_EXECUTED`.

## Affected Governance Documents

* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/CONTRACTS.md`
* `docs/VALIDATION.md`
* `docs/SECURITY_MODEL.md`
* `docs/ROADMAP.md`
* `docs/PHASEMAP.md`

## Affected Contracts or Validators

* `contracts/fixed_user_execution_context_contract.v0.json`
* `schemas/fixed_user_execution_context_contract.schema.json`
* `harness/fixed_user_execution_context_contract.py`
* `harness/validators_impl/fixed_user_execution_context_contract.py`
* focused governance tests

The governance validator is exercised directly. It is not a new
`scripts/verify.sh` aggregate check, so the accepted governed count remains 67.
A future implementation validator requires separate authorization.

## Superseded Decisions

None.
