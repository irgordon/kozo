# Maintainer Guide

## Maintainer Responsibilities

A maintainer keeps repository claims aligned with authoritative source,
contracts, generated evidence, and published release records. The job is not
only to make a command pass. A safe change preserves scope, diagnoses failures,
and records what the repository can honestly prove.

## Repository Layout

| Path | Responsibility |
| --- | --- |
| `kernel/` | Odin kernel and x86-64 assembly runtime |
| `userspace/` | Rust services and generated ABI consumers |
| `contracts/` | Machine-readable behavior and evidence rules |
| `schemas/` | JSON shapes for contracts and reports |
| `harness/` | Deterministic validators and report generators |
| `tests/` | Focused positive and negative validation |
| `scripts/` | Build, QEMU, evidence, and verification entry points |
| `docs/` | Engineering, governance, security, and release records |
| `docs/wiki/` | User and maintainer entry path |
| `artifacts/` | Generated evidence; never a source of truth |
| `tasks/` | Governed task and verification state |

## Authority and Generated Files

| Area | Source of truth | Generated or supporting files |
| --- | --- | --- |
| Runtime behavior | `kernel/` and `kernel/arch/x86_64/` | ELF and QEMU reports |
| Marker order | `contracts/runtime_evidence_taxonomy.v0.json` | QEMU metadata and summaries |
| Contract shape | Contract JSON and matching schema | Generated verification records |
| Release state | Release notes, checklist, evidence, and task state | Governance index |
| User guidance | `docs/wiki/` | Links to detailed `docs/` pages |

Read [Governance](../GOVERNANCE.md) for precedence. Generated reports never
override source, contracts, schemas, or validators.

Generated reports include `artifacts/latest_verify.json`,
`artifacts/runtime/*.json`, and `docs/generated/*.md`. Change the authoritative
input or generator, then run the governed generator. Do not edit generated
output by hand. See [Generated Artifacts](../GENERATED_ARTIFACTS.md).

## Safe Change Workflow

1. Identify the authority that owns the behavior.
2. Read its contract, schema, validator, and focused tests.
3. Keep the patch inside the requested boundary.
4. Run focused tests before full discovery.
5. Run `scripts/verify.sh`.
6. Review generated changes separately.
7. Keep source and generated-proof commits separate when practical.

Do not weaken a validator because a fixture or generated report is stale.

## Runtime-Change Workflow

1. Confirm the requested behavior is inside the declared product boundary.
2. Update runtime code and the authoritative contract together.
3. Preserve failure paths and marker ownership.
4. Add focused positive and consequential negative tests.
5. Inspect source, linked ELF, and QEMU evidence as required.
6. Run full verification before refreshing checked-in proof.

Runtime changes require a separately scoped feature or defect task. They must
not be hidden inside documentation, release, or generated-proof work.

## Documentation-Only Workflow

1. Verify claims against source, contracts, and current release evidence.
2. Keep user, maintainer, and engineering audiences separate.
3. Test every changed command and local link.
4. Confirm no runtime, ABI, contract, schema, or release artifact changed.
5. Commit documentation before generated proof.

## Contracts and Schemas

Change a contract only when the governed behavior changes or its metadata is
wrong. Update the matching schema, loader, validator, and focused negative
tests together. The contract owns the rule; the validator checks it.

See [Contracts](../CONTRACTS.md) and [Validation](../VALIDATION.md).

## Tests and Validators

Run focused tests with:

```bash
python3 -m unittest tests/test_runtime_evidence_taxonomy.py
python3 -m unittest tests/test_qemu_smoke_evidence.py
python3 -m unittest tests/test_validator_coverage.py
```

Run all Python tests with:

```bash
python3 -m unittest discover -s tests
```

Every validator needs consequential negative coverage and diagnostics that name
the failed field.

The governance index is refreshed from the repository root with:

```bash
python3 -c 'from pathlib import Path; from harness.governance_index_report import write_report; root=Path.cwd(); write_report(root, root / "docs/generated/governance_index.md")'
```

## Runtime Markers

Add or change a marker only through the runtime evidence taxonomy contract.
Update runtime emission, blocker classification, QEMU evidence validation, and
negative tests together. A marker in source is not proof that it executed.

## Verification Expectations

```bash
scripts/verify.sh
python3 -m json.tool artifacts/latest_verify.json
jq '{status, summary}' artifacts/latest_verify.json
git diff --check
```

If a marker is missing, inspect:

```bash
cat artifacts/runtime/qemu_smoke.summary.txt
jq '{outcome, blocker_category, observed_markers}' artifacts/runtime/qemu_smoke.metadata.json
```

## Fail-Closed Behavior

KOZO stops when required evidence is missing. A missing marker, checksum
mismatch, stale generated report, or unknown runtime status is a failure to
diagnose, not a reason to weaken the gate. Preserve the last trustworthy
evidence and fix the owning source.

## Release Immutability

Use [Required Checks](../REQUIRED_CHECKS.md), the
[Release Checklist](../RELEASE_CHECKLIST.md), and
[Release Evidence](../RELEASE_EVIDENCE.md). Record the release commit, current
generated proof, CI status, limits, and explicit non-goals.

The repository states are distinct:

| State | Meaning |
| --- | --- |
| `v1.0.1` tag | Immutable current patch source and artifact record |
| `v1.0.0` tag | Immutable previous final source and artifact record |
| `main` | May contain later documentation or development commits |
| `v1.0.0-rc.1` tag | Immutable accepted prerelease record |

The current patch tag targets
`02f1b0113458b988562b7e03362ec9ae716cebd0`. The post-publication
documentation commit is later on `main` and is not part of the tagged release.
The prior final tag remains fixed at
`1586089415a98a11d2024d606ce6301f568b7d6e`.

Do not move a published tag. Do not replace published assets. Do not rewrite
hosted notes to hide a defect.

## Patch-Release Process

A reproduced product defect requires a new patch version such as `v1.0.2`.
Record the defect, fix it in a scoped task, rebuild and verify new artifacts,
and obtain explicit release authorization. Never repair `v1.0.1` in place.

## Current Warning Policy

Warnings remain visible. Classify each as a product failure, governed
non-blocking warning, or local tooling limitation. Examples include generated
Rust ABI naming warnings, xorriso portability warnings, and known Taplo macOS
panics. Do not suppress a warning merely to make output quiet, and do not call
a failed tool successful.

## Common Maintenance Mistakes

- treating generated output as authority;
- changing marker strings in only one file;
- reporting planned behavior as proven;
- editing fixtures instead of fixing a real contract mismatch;
- mixing runtime work with broad cleanup;
- using local tool paths as portable policy;
- confusing current `main` with a published tag target;
- replacing a release artifact instead of issuing a patch release;
- removing a hardware or fail-closed comment without understanding it.
