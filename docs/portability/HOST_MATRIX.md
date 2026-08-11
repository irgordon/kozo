# KOZO Host Portability Matrix

Status: Phase 0 accepted; KOZO-TRIAGE-003 resolved on main
Evidence date: 2026-08-11
Workflow: `portability`
Run: [31458972010](https://github.com/irgordon/kozo/actions/runs/31458972010)
Commit: `5dc255f2cc4f440137344354328ca0c77c319236`

## Purpose

This report records hosted execution of the build contract defined by ADR
0017. It keeps required-job results, accepted compatibility claims, and guest
runtime evidence separate. It does not change the current release, v1.0.1.

## Host Matrix

| Host | Pinned runner | Required job | Accepted compatibility | Runtime contract |
| --- | --- | --- | --- | --- |
| Linux | `ubuntu-24.04` | `PASS` | `VALIDATED_RUNTIME` | `PASS` |
| Windows | `windows-2025` | `PASS` | `VALIDATED_BUILD` | `NOT_EXECUTED` |
| macOS | `macos-15` | `PASS` | `VALIDATED_BUILD` | `NOT_EXECUTED` |

All required jobs passed their per-host contract. The required aggregate job
also proved that the three governed license inputs have identical paths,
sizes, and SHA-256 values on Linux, Windows, and macOS. Windows therefore
meets the complete Phase 0 `VALIDATED_BUILD` gate.

Linux runtime evidence is owned by CI run
[31458972015](https://github.com/irgordon/kozo/actions/runs/31458972015).
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

Each host also passed all 1,136 Python tests and a real Odin object build.

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

The correction uses committed Git blob bytes as authority, applies LF checkout
policy only to the three licenses, verifies worktree/blob and source/staged
identity, and requires aggregate path/size/SHA-256 comparison. Run
`31458972010` proved identical records on all three hosts:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `LICENSE` | 335 | `ad64bbbebae629ed91c7554213ef5267e397bae1acd8b034ad62a2b2fadab43b` |
| `LICENSE-APACHE` | 567 | `649d45a505bdaf0b54f8c29fa352a8df17c6355da13de19befbb94fa5f19b3a8` |
| `LICENSE-MIT` | 1066 | `fae289de6b8d166b66b7129216b9a00db2f76033767dc93b80b1f340dbf9c943` |

The complete 49-entry manifest remains path-governed. This result does not
claim cross-host reproducibility for generated archives, ISO images, ELF
files, or timestamped evidence.

## Phase Status

ADR 0017 and the portability invariant remain adopted. Linux is
`VALIDATED_RUNTIME`; Windows and macOS are `VALIDATED_BUILD`; Windows and
macOS runtime remain `NOT_EXECUTED`.

v1.1.0 Phase 0 is accepted. `KOZO-TRIAGE-002` and `KOZO-TRIAGE-003` are
`RESOLVED_ON_MAIN`. Product capability work still requires separate
authorization. No runtime or published release changed.
