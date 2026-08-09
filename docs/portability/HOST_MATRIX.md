# KOZO Host Portability Matrix

Status: Blocked
Evidence date: 2026-08-08
Workflow: `portability`
Run: [31270131685](https://github.com/irgordon/kozo/actions/runs/31270131685)
Commit: `dac61571363569146beaa2e4e23eeb42ccf65bc6`

## Purpose

This report records the first hosted execution of the build contract defined
by ADR 0017. It keeps host build evidence separate from guest runtime evidence.
It does not change the current published release, v1.0.1.

## Host Matrix

| Host | Pinned runner | Build contract | Runtime contract | Required job |
| --- | --- | --- | --- | --- |
| Linux | `ubuntu-24.04` | `PASS` | `PASS` | `required build contract (linux, ubuntu-24.04)` |
| Windows | `windows-2025` | `FAIL` | `NOT_EXECUTED` | `required build contract (windows, windows-2025)` |
| macOS | `macos-15` | `PASS` | `NOT_EXECUTED` | `required build contract (macos, macos-15)` |

Linux runtime evidence is owned by the separate `ci` workflow run
[31270131715](https://github.com/irgordon/kozo/actions/runs/31270131715).
That run passed 67 checks with no failures and booted KOZO through all 41
markers, ending at `KOZO_RUNTIME_RETURN_OK`. Neither Windows nor macOS ran a
guest runtime contract in this phase.

## Runner and Tool Evidence

| Host | Runner architecture | Runner image | Python | Odin | Rust and Cargo | Odin object result |
| --- | --- | --- | --- | --- | --- | --- |
| Linux | X64 | `ubuntu24` `20260720.247.2` | 3.13.14 | `dev-2026-08-nightly:902106f` | 1.96.0 | exact output normalized to the requested `.o` path |
| Windows | X64 | `win25-vs2026` `20260803.193.1` | 3.13.14 | installed by the pinned setup step; contract stopped before version capture | 1.96.0 | focused 34-case normalization suite passed; real build not reached |
| macOS | ARM64 | `macos15` `20260727.0256.1` | 3.13.14 | `dev-2026-08-nightly:902106f` | 1.96.0 | exact output normalized to the requested `.o` path |

Windows used Git Bash as its declared shell environment. This is hosted
Windows build evidence for that environment; it is not a claim of native
PowerShell or `cmd.exe` compatibility.

## KOZO-TRIAGE-001 Regression

| Host | Exact | `.o` | `.obj` | Stale output | Paths with spaces | Result |
| --- | --- | --- | --- | --- | --- | --- |
| Linux | PASS | PASS | PASS | PASS | PASS | 34 focused tests passed |
| Windows | PASS | PASS | PASS | PASS | PASS | 34 focused tests passed before the full suite failed |
| macOS | PASS | PASS | PASS | PASS | PASS | 34 focused tests passed |

The cross-host object boundary itself passed on all required hosts. The
Windows failure occurred later in the full Python suite.

## Release-Build Contract

| Host | Portable staging and inventory | Licenses | Metadata | Checksums | Final archive |
| --- | --- | --- | --- | --- | --- |
| Linux | PASS | PASS | PASS | PASS | `NOT_EXECUTED` |
| Windows | `NOT_EXECUTED` | `NOT_EXECUTED` | `NOT_EXECUTED` | `NOT_EXECUTED` | `NOT_EXECUTED` |
| macOS | PASS | PASS | PASS | PASS | `NOT_EXECUTED` |

Linux and macOS each validated 49 release-manifest entries, staged 87 files,
validated the required license set and metadata, and reproduced identical
SHA-256 values for the three license files. Final `.tar.xz`, ISO, and kernel
artifact creation remains owned by Linux full CI and was not part of the
common host contract.

## Blocking Result

Windows ran 1,097 tests and reported 57 failures:

* Three host-dependency validator tests exposed native backslashes in
  repository-relative diagnostic fields that are required to use canonical
  forward slashes.
* Fifty-four QEMU evidence tests reached `byte_count_mismatch` because text
  byte accounting changed under the Windows checkout and text-mode boundary.

This is recorded as `KOZO-TRIAGE-002`. The failure is deterministic, so the
run was not rerun. No test was skipped, no platform exception was added, and
the portability contract was not narrowed.

## Phase Status

ADR 0017 and the portability invariant are adopted. Linux is
`VALIDATED_RUNTIME`; macOS is `VALIDATED_BUILD`; Windows has a known blocking
incompatibility and cannot be promoted to `VALIDATED_BUILD`.

v1.1.0 Phase 0 is blocked. Product capability work remains unauthorized until
a separately authorized correction resolves `KOZO-TRIAGE-002` and all three
required build jobs pass.

## Correction Candidate

The authorized correction is implemented and passes 1,117 local Python tests,
including structured canonical-path, deterministic text-serialization,
raw-byte, byte-exact SHA-256, early environment-capture, and unchanged 34-case
Odin object regressions. It preserves the pinned matrix, Windows Git Bash
boundary, runtime separation, and all compatibility claim levels.

This section does not replace the hosted table above. The historical failed
run remains the authoritative current matrix result until a new run proves all
three required build contracts. Phase 0 therefore remains blocked.
