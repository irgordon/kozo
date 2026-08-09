# KOZO-TRIAGE-003: Cross-Host License Bytes

Status: REPRODUCED
Report date: 2026-08-09
Surface: BUILD_TOOLING

## Case Record

| Field | Evidence |
| --- | --- |
| Source | GitHub Actions portability run [31291100568](https://github.com/irgordon/kozo/actions/runs/31291100568) |
| Hosts compared | `ubuntu-24.04`, `windows-2025`, and `macos-15` |
| Affected source | `249eb0f0f5871421140a4c0cbd982d0b5769cffd` |
| Affected surface | Portable release staging and cross-host SHA-256 determinism for tracked license texts |
| Expected behavior | The same tracked release inputs have the same bytes and SHA-256 values on every required build host |
| Reported behavior | Linux and macOS staged LF bytes; Windows staged CRLF bytes and reported three different hashes |
| Reproduction status | `REPRODUCED` by independent comparison of all three downloaded host artifacts |
| User impact | `U1`: published v1.0.1 artifacts and runtime are unchanged; Windows cannot satisfy the complete Phase 0 release-build contract |
| Release severity | `R2`: blocks Phase 0 and later capability work; no release correction is authorized |
| Security concern | None observed; cryptographic validation remained byte exact and exposed the mismatch |
| Disposition | Requires a separately authorized correction; do not weaken hashes or normalize raw release artifacts after staging |

## Reproduction

All three required jobs report `PASS` because each host validates checksums
against the files staged on that same host. Cross-host artifact inspection
shows different license inputs:

| File | Linux and macOS SHA-256 | Windows SHA-256 |
| --- | --- | --- |
| `LICENSE` | `ad64bbbebae629ed91c7554213ef5267e397bae1acd8b034ad62a2b2fadab43b` | `240bf2acda9af0af31bdf76246e2a0c9f18fc761bb7cb3b5414efdb4f1156d88` |
| `LICENSE-APACHE` | `649d45a505bdaf0b54f8c29fa352a8df17c6355da13de19befbb94fa5f19b3a8` | `d9cc87dfb97538ef693dba0336cdbf5e33c136454013aeb0e736aa59db2d544d` |
| `LICENSE-MIT` | `fae289de6b8d166b66b7129216b9a00db2f76033767dc93b80b1f340dbf9c943` | `12ab12b0f8374113257069be5cd8967b122fba8ff068e29ec3c72e9aac202166` |

Applying a pure LF-to-CRLF transform to each repository license file locally
reproduces the corresponding Windows hash exactly. The failure is therefore
line-ending conversion at the tracked release-input boundary, not a SHA-256
algorithm difference.

## Contract Gap

The per-host contract proves inventory, metadata, license presence, and
checksum round-trip validity. It does not compare supposedly identical staged
input hashes across hosts. A green job therefore did not detect this Phase 0
invariant violation by itself.

The required correction must keep SHA-256 and staged artifact validation byte
exact. It must govern the tracked release-input representation before staging
and add a cross-host equality check or equivalent evidence comparison. The
exact correction is outside the TRIAGE-002 authorization.

## Boundary

The Linux runtime remains accepted in CI run `31291100579`: 67 checks, no
failures, QEMU pass, blocker none, 41 ordered markers, and final marker
`KOZO_RUNTIME_RETURN_OK`. Windows and macOS runtime remain `NOT_EXECUTED`.

No published tag, note, or asset changed. The current release remains v1.0.1,
`release/version.txt` remains `1.0.1`, and no CPU, RAM, or storage assumption
was introduced.

## Phase Effect

Until a separately authorized correction is hosted-proven:

* the Windows required job result is recorded as `PASS` but its complete Phase
  0 build claim is not accepted;
* Windows remains below `VALIDATED_BUILD`;
* v1.1.0 Phase 0 remains blocked; and
* v1.1.0 capability work remains unauthorized.
