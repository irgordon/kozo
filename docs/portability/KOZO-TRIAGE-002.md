# KOZO-TRIAGE-002: Windows Evidence Normalization

Status: REPRODUCED
Report date: 2026-08-08
Surface: BUILD_TOOLING

## Case Record

| Field | Evidence |
| --- | --- |
| Source | GitHub Actions portability run [31270131685](https://github.com/irgordon/kozo/actions/runs/31270131685), Windows job `93134557878` |
| Reporter environment | GitHub-hosted `windows-2025`, X64, image `win25-vs2026` `20260803.193.1`, Git Bash |
| Affected source | Phase 0 commit `dac61571363569146beaa2e4e23eeb42ccf65bc6` |
| Affected surface | Host-dependency diagnostic paths and QEMU evidence byte-count validation under Windows |
| Expected behavior | Repository-relative diagnostics are host-independent and committed text evidence has the same governed byte interpretation on every required host |
| Reported behavior | The full 1,097-test suite reports 57 failures on Windows after task/schema validation and the 34-case Odin object regression pass |
| Reproduction status | `REPRODUCED` in the first required Windows matrix execution |
| User impact | `U1`: the published v1.0.1 ISO and Linux runtime are unaffected, but Windows cannot satisfy the newly declared source-validation contract |
| Release severity | `R2`: blocks v1.1.0 Phase 0 and later capability work; it does not justify modifying an immutable release |
| Security concern | None observed; the failure is in host validation and evidence interpretation, not the guest runtime |
| Disposition | Require a separately authorized, bounded portability correction; do not skip Windows tests or weaken the contract |

## Reproduction

The required Windows job runs:

```text
python scripts/host_portability_contract.py --output artifacts/portability/windows.json
```

The contract passes task and schema validation. Its focused Odin object suite
also passes. Full discovery then runs 1,097 tests and fails 57.

Three failures compare canonical contract fields such as
`host_dependency_portability.scripts/rust.sh...` with values containing native
Windows separators such as `host_dependency_portability.scripts\rust.sh...`.

The other 54 failures are in QEMU smoke evidence tests. Their fixtures are
rejected first as `byte_count_mismatch`, so positive evidence and intended
negative-path diagnostics cannot be evaluated. The failure is consistent with
Windows checkout or text-mode line-ending conversion changing byte counts.

## Boundary

The accepted runtime remains unchanged:

* Linux CI run `31270131715` passed 67 checks with no failures.
* QEMU passed with blocker `none`.
* All 41 markers were ordered and the final marker was
  `KOZO_RUNTIME_RETURN_OK`.

Windows runtime was not executed. Linux and macOS host build contracts passed.
The current release remains v1.0.1, and all published releases remain
immutable.

## Required Follow-Up

A correction task must normalize repository-relative diagnostics independent
of the host path separator and define byte accounting for committed text
evidence independent of checkout line endings. It must retain all existing
negative tests and rerun the same pinned three-host matrix.

Until that correction is separately authorized and hosted-proven:

* Windows build status is `FAIL`;
* Windows runtime is `NOT_EXECUTED`;
* v1.1.0 Phase 0 is blocked; and
* v1.1.0 capability work is unauthorized.

## Correction Candidate On Main

The authorized correction preserves the existing evidence definitions. QEMU
`serial_log_bytes` and `stderr_log_bytes` remain raw file-byte counts because
the producer and validator both define them through file size. Governed text
serialization now emits UTF-8 with LF line endings, so equivalent LF, CRLF,
and CR semantic inputs produce the same deterministic text bytes before raw
accounting. Binary files and SHA-256 behavior remain unchanged.

Repository diagnostics now derive a validated repository-relative path from
the native path and serialize only that path with POSIX separators. Root
escape and unrelated absolute roots are rejected. Non-path backslash content
is not rewritten.

The host contract now writes a `PENDING` artifact immediately after capturing
runner, shell, workflow, run, Python, Odin, Rust, Cargo, and Git evidence. If a
later stage fails, the artifact records `FAIL` and the exact stage while the
required job remains failed.

Focused path, text, host-evidence, QEMU, and Odin regression tests pass
locally. Full local discovery passes 1,117 tests. This is correction-candidate
evidence only: `KOZO-TRIAGE-002` remains `REPRODUCED`, Windows remains
unvalidated, and Phase 0 remains blocked until the unchanged pinned matrix
passes on a new commit.
