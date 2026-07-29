# Maintainer Guide

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

## Sources of Truth

| Area | Source of truth | Generated or supporting files |
| --- | --- | --- |
| Runtime behavior | `kernel/` and `kernel/arch/x86_64/` | ELF and QEMU reports |
| Marker order | `contracts/runtime_evidence_taxonomy.v0.json` | QEMU metadata and summaries |
| Contract shape | Contract JSON and matching schema | Generated verification records |
| Release state | `docs/RELEASE_CHECKLIST.md` and `tasks/todo.json` | Governance index |
| User guidance | `docs/wiki/` | Links to detailed `docs/` pages |

Read [Governance](../GOVERNANCE.md) for precedence. Generated reports never
override source, contracts, schemas, or validators.

## Making a Safe Change

1. Identify the authority that owns the behavior.
2. Read its contract, schema, validator, and focused tests.
3. Keep the patch inside the requested boundary.
4. Run focused tests before full discovery.
5. Run `scripts/verify.sh`.
6. Review generated changes separately.
7. Keep source and generated-proof commits separate when practical.

Do not weaken a validator because a fixture or generated report is stale.

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

## Generated Files

Generated reports include `artifacts/latest_verify.json`,
`artifacts/runtime/*.json`, and `docs/generated/*.md`. Change the authoritative
input or generator, then run the governed command. Do not edit generated output
by hand.

The governance index is refreshed with:

```bash
python3 -c 'from harness.governance_index_report import write_report; write_report()'
```

See [Generated Artifacts](../GENERATED_ARTIFACTS.md).

## Runtime Markers

Add or change a marker only through the runtime evidence taxonomy contract.
Update runtime emission, blocker classification, QEMU evidence validation, and
negative tests together. A marker in source is not proof that it executed.

## Full Verification

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

## Release Workflow

Use [Required Checks](../REQUIRED_CHECKS.md), the
[Release Checklist](../RELEASE_CHECKLIST.md), and
[Release Evidence](../RELEASE_EVIDENCE.md). Record the release commit, current
generated proof, CI status, limits, and explicit non-goals.

The `v1.0.0-rc.1` annotated tag and its hosted prerelease assets are immutable.
Do not move the tag, replace an asset, or repair the release record in place.
Record a reproducible defect and prepare a new candidate such as
`v1.0.0-rc.2`.

The final `v1.0.0` tag, notes, and assets are published and immutable. A later
product defect requires a patch release instead of replacing the final release
in place.

## Common Maintenance Mistakes

- treating generated output as authority;
- changing marker strings in only one file;
- reporting planned behavior as proven;
- editing fixtures instead of fixing a real contract mismatch;
- mixing runtime work with broad cleanup;
- using local tool paths as portable policy;
- removing a hardware or fail-closed comment without understanding it.
