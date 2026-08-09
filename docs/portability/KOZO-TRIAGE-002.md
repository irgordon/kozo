# KOZO-TRIAGE-002: Windows Evidence Normalization

Status: RESOLVED_ON_MAIN
Report date: 2026-08-08
Resolution date: 2026-08-09
Surface: BUILD_TOOLING

## Case Record

| Field | Evidence |
| --- | --- |
| Original source | GitHub Actions portability run [31270131685](https://github.com/irgordon/kozo/actions/runs/31270131685), Windows job `93134557878` |
| Correction source | GitHub Actions portability run [31291100568](https://github.com/irgordon/kozo/actions/runs/31291100568), Windows job `93188306690` |
| Reporter environment | GitHub-hosted `windows-2025`, X64, image `win25-vs2026` `20260803.193.1`, Git Bash |
| Failing source | Phase 0 commit `dac61571363569146beaa2e4e23eeb42ccf65bc6` |
| Corrected source | `249eb0f0f5871421140a4c0cbd982d0b5769cffd` |
| Affected surface | Host-dependency diagnostic paths and QEMU textual evidence serialization under Windows |
| Original result | 57 full-suite failures: three path-separator failures and 54 QEMU byte-count failures |
| Corrected result | All 1,117 Python tests and the complete Windows job passed without skips or host-specific expected values |
| User impact | `U1`: the published v1.0.1 runtime was unaffected |
| Release severity | `R2`: the case blocked Phase 0 but did not justify changing an immutable release |
| Security concern | None observed |
| Disposition | `RESOLVED_ON_MAIN`; Phase 0 remains blocked by the independent `KOZO-TRIAGE-003` release-input checksum case |

## Original Reproduction

The first required Windows job passed task/schema validation and the 34-case
Odin object suite, then failed 57 tests. Three diagnostics leaked native
Windows backslashes into canonical repository-relative fields. The other 54
tests wrote textual QEMU fixtures through host text mode, so checkout line
endings changed the raw byte counts before the intended evidence assertions.

## Correction

Repository diagnostics now derive a validated repository-relative path from
the native filesystem path and serialize only that field with POSIX
separators. Root escapes and unrelated absolute roots remain rejected.
Arbitrary non-path backslashes are not rewritten.

QEMU `serial_log_bytes` and `stderr_log_bytes` remain raw file-byte counts.
Governed textual producers serialize UTF-8 with LF line endings before raw
accounting, while binary files and SHA-256 inputs remain byte exact.

The host contract writes a `PENDING` artifact after capturing the runner,
shell, workflow, run, Python, Odin, Rust, Cargo, and Git evidence. A later
failure changes the result to `FAIL` and retains the failed stage.

## Hosted Resolution

Required run `31291100568` passed on `ubuntu-24.04`, `windows-2025`, and
`macos-15`. Each host passed 34 Odin object regressions, 1,117 Python tests,
real Odin object normalization, release staging, inventory, metadata, and
per-host checksum validation. The Windows artifact captured Odin
`dev-2026-08-nightly:902106f`, Rust/Cargo 1.96.0, and Git
2.55.0.windows.3 before completing the contract.

The original three path assertions and 54 QEMU assertions are therefore
resolved on `main`. No runtime, ABI, contract, schema, marker, product version,
or immutable release changed.

## Separate Finding

Independent artifact comparison found that Windows staged `LICENSE`,
`LICENSE-APACHE`, and `LICENSE-MIT` with CRLF bytes while Linux and macOS
staged LF bytes. Each host's internal checksum round trip passed, but the
supposedly identical release inputs had different cross-host SHA-256 values.

That finding is not part of the authorized QEMU text correction because
release artifact bytes and SHA-256 inputs were explicitly excluded. It is
recorded as `KOZO-TRIAGE-003`. Phase 0 remains blocked, Windows is not promoted
to `VALIDATED_BUILD`, and v1.1.0 capability work remains unauthorized.
