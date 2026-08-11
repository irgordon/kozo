# KOZO Host Portability Matrix

Status: KOZO-TRIAGE-003 correction pending hosted validation
Evidence date: 2026-08-09
Workflow: `portability`
Run: [31291100568](https://github.com/irgordon/kozo/actions/runs/31291100568)
Commit: `249eb0f0f5871421140a4c0cbd982d0b5769cffd`

## Purpose

This report records hosted execution of the build contract defined by ADR
0017. It keeps required-job results, accepted compatibility claims, and guest
runtime evidence separate. It does not change the current release, v1.0.1.

## Host Matrix

| Host | Pinned runner | Required job | Accepted compatibility | Runtime contract |
| --- | --- | --- | --- | --- |
| Linux | `ubuntu-24.04` | `PASS` | `VALIDATED_RUNTIME` | `PASS` |
| Windows | `windows-2025` | `PASS` | `UNSUPPORTED` pending correction | `NOT_EXECUTED` |
| macOS | `macos-15` | `PASS` | `VALIDATED_BUILD` | `NOT_EXECUTED` |

All required jobs passed their implemented per-host contract. Windows is not
promoted to `VALIDATED_BUILD`: independent artifact review found a cross-host
release-input checksum mismatch that the per-host round-trip check did not
detect. This is `KOZO-TRIAGE-003`.

Linux runtime evidence is owned by CI run
[31291100579](https://github.com/irgordon/kozo/actions/runs/31291100579).
That run passed 67 checks with no failures and booted KOZO through all 41
markers, ending at `KOZO_RUNTIME_RETURN_OK`. Windows and macOS did not run a
guest runtime contract.

## Runner and Tool Evidence

| Host | Architecture and image | Python | Odin | Rust/Cargo | Git | Odin output |
| --- | --- | --- | --- | --- | --- | --- |
| Linux | X64, `ubuntu24` `20260720.247.2` | 3.13.14 | `dev-2026-08-nightly:902106f` | 1.96.0 | 2.54.0 | exact |
| Windows | X64, `win25-vs2026` `20260803.193.1` | 3.13.14 | `dev-2026-08-nightly:902106f` | 1.96.0 | 2.55.0.windows.3 | exact |
| macOS | ARM64, `macos15` `20260727.0256.1` | 3.13.14 | `dev-2026-08-nightly:902106f` | 1.96.0 | 2.55.0 | exact |

Windows used Git Bash as its declared shell contract. The captured shell path
field resolves to `cmd.exe` through the runner environment, but the workflow
step itself executed under Git Bash. This does not claim native PowerShell or
`cmd.exe` compatibility.

## KOZO-TRIAGE-001 Regression

| Host | Exact | `.o` | `.obj` | Stale | Spaces | Result |
| --- | --- | --- | --- | --- | --- | --- |
| Linux | PASS | PASS | PASS | PASS | PASS | 34/34 |
| Windows | PASS | PASS | PASS | PASS | PASS | 34/34 |
| macOS | PASS | PASS | PASS | PASS | PASS | 34/34 |

Each host also passed all 1,117 Python tests and a real Odin object build.

## KOZO-TRIAGE-002 Resolution

Run `31291100568` resolves the authorized correction on all three pinned
runners. Canonical repository-path evidence no longer leaks native separators,
QEMU textual fixtures serialize deterministic UTF-8/LF bytes while raw byte
fields retain their meaning, and failed host artifacts capture tools and
contract stage early. No tests were skipped and no OS-specific expected value
was introduced.

## Release-Build Contract

| Host | Staging/inventory | Licenses | Metadata | Per-host checksum | Final archive |
| --- | --- | --- | --- | --- | --- |
| Linux | PASS, 49 entries and 87 files | PASS | PASS | PASS | `NOT_EXECUTED` |
| Windows | PASS, 49 entries and 87 files | PASS | PASS | PASS | `NOT_EXECUTED` |
| macOS | PASS, 49 entries and 87 files | PASS | PASS | PASS | `NOT_EXECUTED` |

Per-host checksum validation is byte exact and passed. Cross-host comparison
then found Linux and macOS had identical license hashes while Windows had the
exact hashes produced by converting those three tracked files from LF to
CRLF. The files were therefore not identical release inputs across hosts.

This independent defect is `KOZO-TRIAGE-003`. SHA-256 semantics are not
weakened, and raw staged artifacts are not normalized after the fact.

The correction candidate uses committed Git blob bytes as authority, applies
LF checkout policy only to the three licenses, verifies worktree/blob and
source/staged identity, and adds a required aggregate path/size/SHA-256 gate.
The historical hashes and compatibility states above remain authoritative
until a new pinned run proves the candidate.

## Phase Status

ADR 0017 and the portability invariant remain adopted. Linux is
`VALIDATED_RUNTIME`; macOS is `VALIDATED_BUILD`; Windows retains a known
blocking incompatibility in the complete release-build contract.

v1.1.0 Phase 0 remains blocked. Product capability work remains unauthorized
until `KOZO-TRIAGE-003` is hosted-proven and the required aggregate job proves
cross-host release-input determinism. No runtime or published release changed.
