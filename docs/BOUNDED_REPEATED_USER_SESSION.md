# KOZO Bounded Repeated User Session

Version: 1
Status: Implemented and hosted accepted on main
Release target: v1.1.0; current published v1.0.1 does not contain this capability

## Problem Solved

The accepted Fixed User Execution Context proved one complete fixed Ring 3
transaction. It did not prove that the same static context and user pages could
be cleared, checked, and used again without inheriting authority from the prior
execution.

Current `main` now runs exactly two sequential fixed sessions. This is a
bounded reuse proof, not persistent userspace.

## Fixed Boundary

The kernel owns `REQUIRED_SESSION_COUNT = 2`. No user input, build option, or
configuration can change it. Each session:

1. starts from a validated non-authoritative context;
2. receives one nonzero kernel-owned opaque identity;
3. executes the existing fixed request and response transaction;
4. performs exactly two existing `int 0x81` returns;
5. commits and validates the existing context result;
6. clears all context authority and transaction storage; and
7. validates the cleared state.

The first result is reset and read back before the context returns to the
all-zero `UNINITIALIZED` form. Only then may session 2 receive its distinct
identity. The second result is also reset before later internal capabilities
run.

## Coordinator

One 32-byte, 8-byte-aligned supervisor RW-NX record coordinates the two
explicit calls. It stores only format, size, required and completed counts,
the active ordinal, the observed total transition count, a failure code, and a
reserved-zero field. It contains no identity, pointer, address, selector, or
capability handle.

Successful terminal state is:

```text
active session ordinal: 0
completed sessions: 2
observed transitions: 4
failure code: 0
reserved: 0
```

A third session or fifth transition fails closed.

## Evidence

The existing 11-marker fixed-transaction block now occurs twice. The marker
catalog remains unchanged; the ordered occurrence sequence increases from 41
to 52 entries. `KOZO_RUNTIME_RETURN_OK` remains the final marker.

Runtime metadata preserves duplicate occurrences and reports the expected and
observed counts, per-marker occurrence counts, completed-session count, and
the active or failed session ordinal. The focused contract and evidence
validators remain unregistered so the governed aggregate remains 67 checks.

## Limits

This capability adds no process, PID, scheduler, timer, allocator, concurrent
context, public syscall ABI, new interrupt vector, user-selected identity,
mapping, or persistent session. Windows and macOS remain build-validated only;
Linux remains the governed runtime host.

Hosted CI run `31899981058` passed 1,284 Python tests, 67 governed checks,
QEMU with no blocker, and all 52 ordered marker occurrences. Lint run
`31899981084` passed. Portability run `31899981072` passed the pinned Linux,
Windows, and macOS build contracts plus cross-host release-input identity;
only Linux executed the runtime contract.

Downloaded hosted development evidence independently confirmed two completed sessions,
active ordinal zero, matching packaged and runtime-tested ISO hashes, valid
package checksums, and the supervisor RW-NX coordinator ELF record. The
implementation is included in the authorized v1.1.0 release target; publication
remains pending exact-commit hosted qualification.
