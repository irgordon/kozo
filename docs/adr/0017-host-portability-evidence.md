# ADR-0017: Host Portability Evidence

## Status

Accepted

## Context

`KOZO-TRIAGE-001` showed that a successful local macOS build did not prove
that the same Odin object boundary worked on hosted Linux. The failure was in
the development-host build path, not in the KOZO guest runtime. Treating one
developer workstation as the reference platform would leave the same class of
environmental dependency undiscovered on Windows and future hosts.

KOZO needs separate evidence for three questions:

1. **Host portability:** Can the governed build and tooling path operate on a
   claimed development host?
2. **Guest portability:** Does the KOZO guest boot and complete its governed
   runtime under a declared virtualization environment?
3. **Resource scaling:** What guest CPU, memory, and storage profile supports
   declared functionality, and how does additional capacity change behavior?

Only host portability changes in this decision. Linux QEMU remains the
authoritative hosted guest-runtime environment. Resource minimums remain
undefined until later guest capabilities make them meaningful.

## Decision

KOZO treats development-host portability as an evidence-backed invariant.
Local macOS development is one validation environment, not the reference
platform.

The canonical host evidence states are:

* `NOT_EXECUTED`: no governed hosted contract ran for the host.
* `DESIGNED`: no intentional blocker is known, but hosted evidence is absent.
* `VALIDATED_BUILD`: the required hosted build/tooling contract passed.
* `VALIDATED_RUNTIME`: both the build/tooling contract and the separately
  governed guest-runtime contract passed.
* `UNSUPPORTED`: the host is outside the declared contract or has a known
  blocking incompatibility.

Unqualified words such as "validated," "portable," and "supported" must map
to one of these states. A host cannot move from `DESIGNED` to
`VALIDATED_BUILD` without a passing required GitHub Actions job. It cannot move
from `VALIDATED_BUILD` to `VALIDATED_RUNTIME` without an actual passing guest
runtime job. No inference is allowed between the levels.

The required Phase 0 build matrix uses pinned GitHub-hosted runner generations:

* `ubuntu-24.04`
* `windows-2025`
* `macos-15`

Required cells use `fail-fast: false` and block acceptance. Separate latest or
nightly observation cells are informational and non-blocking until governance
explicitly promotes an environment.

The build contract covers repository checkout, tool discovery, task and JSON
validation, Python tests, the `KOZO-TRIAGE-001` Odin object regression, a real
Odin object build, path-with-spaces behavior, stale-output defense, release
inventory policy, portable SHA-256 generation and validation, and relevant
tool versions. The Windows contract uses the Git Bash environment supplied by
the GitHub-hosted Windows runner for existing Bash build helpers. It does not
claim native PowerShell or `cmd.exe` compatibility.

The runtime contract remains separate. A passing build matrix does not prove
QEMU, ISO boot, or guest runtime behavior. Linux full verification remains the
required runtime authority. Windows runtime begins as `NOT_EXECUTED`. macOS
runtime is reported only when a governed runtime job actually runs.

Firm tool requirements are allowed when they are explicit, documented,
validated, and governed. Correctness must not depend on incidental workstation
properties such as user-specific tool paths, CPU count, memory capacity,
storage capacity, filesystem behavior, or one compiler output filename.

Future KOZO releases that provide general userspace must define a minimum
usable guest profile. Additional CPU, memory, and storage should increase
capacity or performance without unlocking basic correctness. This decision
does not set any CPU, memory, or storage minimum.

## Consequences

* Linux, Windows, and macOS build claims require separate hosted evidence.
* Linux guest-runtime evidence remains distinct from cross-host build evidence.
* Windows build evidence may pass while Windows runtime remains
  `NOT_EXECUTED`.
* Build helpers must contain accepted host variation at explicit boundaries
  instead of branching around individual hosts or compiler versions.
* Required pinned runners protect acceptance from silent image migration.
* Non-blocking observation jobs expose upstream runner and toolchain drift.
* A required matrix failure is preserved and triaged; the failing cell is not
  skipped merely to restore a green workflow.
* No runtime behavior, release version, published artifact, or resource minimum
  changes through this decision.

## Affected Governance Documents

* `docs/INVARIANTS.md`
* `docs/VALIDATION.md`
* `docs/COMPATIBILITY.md`
* `docs/RELEASE_EVIDENCE.md`
* `docs/GENERATED_ARTIFACTS.md`
* `docs/ROADMAP.md`
* `docs/PHASEMAP.md`

## Affected Contracts or Validators

No runtime contract or schema changes. The GitHub Actions portability workflow,
focused Odin object regressions, portable release-policy check, task/schema
validation, workflow lint, and hosted evidence artifacts enforce this decision.

## Superseded Decisions

This decision replaces the narrower documentation statement that CI/Linux
alone is the portability authority for all build dependencies. Linux remains
the authoritative guest-runtime environment, while build portability now
requires host-specific evidence for every claimed development host.
