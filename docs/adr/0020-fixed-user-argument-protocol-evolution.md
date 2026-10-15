# ADR-0020: Fixed User Argument Protocol Evolution

## Status

Accepted

## Context

The published v1.1.0 status transaction has a 40-byte request with zero
payload and an 88-byte response. Its last field is reserved and must remain
zero. A bounded argument result therefore requires a successor protocol.
ADR 0019 remains reserved for a separate proposed third-session decision.

## Decision

Contract file version 1 defines wire format version 2, retaining fixed request
ID 2. The 40-byte request carries one u64 argument at offset 24. Odin rejects
values above 65535 before computing argument plus one. Assembly passes only
the validated supervisor shadow and a fixed supervisor result destination.

The 96-byte response retains offsets 0 through 87, including reserved-zero
offset 80, and appends the result at offset 88. Its exclusive end is
0x4000000010e0, leaving 32 bytes before the fixed 48-byte consumption record
at 0x400000001100. Twelve response qwords participate in copy, readback,
digest, and revalidation; the six-qword consumption record is unchanged.

The existing fixed service is extended without adding dispatch, pointers,
lengths, operations, mappings, or interrupt vectors. There are still exactly
two sessions and four total returns. This is not a general public ABI.

## Consequences

Historical v0 contracts and contract tests remain immutable. Current runtime
evidence must validate the successor, including actual Odin executable tests
with different operands and QEMU result consumption. All new bytes must be
cleared and read back before reuse. Existing markers retain their completed
stage meanings; service success additionally requires validated argument work
and complete response readback. No release version changes.

## Affected Governance Documents

INVARIANTS sections 18 through 20 explicitly authorize this successor while
retaining historical geometry. ARCHITECTURE, CONTRACTS, SECURITY_MODEL, and
VALIDATION describe its current ownership and proof requirements.

## Affected Contracts or Validators

The successor fixed_user_request_boundary_contract.v1.json and matching
schema own new geometry and operation rules. Existing request, status, and
consumption evidence validators enforce current runtime behavior. Historical
v0 contract validation remains enabled.

## Superseded Decisions

Only the current fixed status transaction wire format is superseded. ADR
0017 host portability and ADR 0018 execution-context ownership are unchanged.
