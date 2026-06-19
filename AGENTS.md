# KOZO Agent Policy

## Purpose

This file defines how AI agents, coding agents, and automated contributors must operate within the KOZO repository.

This file does not replace repository governance.

The authoritative rules live under `docs/`.

---

## Rule 1: Governance Is Authoritative

Before making any change, read and follow the applicable documents under `docs/`.

At minimum:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/CONTRACTS.md`
* `docs/CODING_STYLE.md`
* `docs/DOCUMENTATION_STANDARD.md`
* `docs/VALIDATION.md`
* `docs/GENERATED_ARTIFACTS.md`
* `docs/COMPATIBILITY.md`
* `docs/SECURITY_MODEL.md`
* `docs/ADR_POLICY.md`

If two documents appear to conflict:

1. Stop.
2. Use the precedence order defined in `docs/GOVERNANCE.md`.
3. If the conflict cannot be resolved confidently, do not proceed.

---

## Rule 2: Stop On Ambiguity

If a task is unclear, contradictory, underspecified, or requires assumptions that are not explicitly supported by repository governance:

Stop.

Do not invent requirements.

Do not infer missing architecture.

Do not silently broaden scope.

Do not implement speculative behavior.

Report:

```text
BLOCKED: ambiguous requirement
```

and identify:

* missing information
* conflicting information
* governing documents consulted

---

## Rule 3: Preserve Repository Truth

Agents must treat the following as authoritative:

* `contracts/`
* `schemas/`
* `docs/`

Generated files are not authoritative.

Generated reports summarize repository truth.

They do not define repository truth.

---

## Rule 4: Do Not Overclaim

Agents must not claim:

* Linux compatibility
* POSIX compatibility
* general userspace execution
* process model support
* VFS support
* scheduler maturity
* ELF loading support
* file descriptor support
* production readiness

unless the repository governance and evidence explicitly support those claims.

---

## Rule 5: Follow Existing Governance

Changes must preserve:

* document authority
* invariants
* contracts
* validation rules
* compatibility boundaries
* security boundaries
* release evidence requirements

Do not weaken governance without an explicit task.

---

## Rule 6: Fail Closed

When unsure:

* stop
* explain the uncertainty
* request clarification

Never guess.

Never continue through ambiguity.

---

## Rule 7: Respect Scope

Only modify files required for the current task.

Do not expand scope.

Do not perform opportunistic refactors unless explicitly requested.

Do not rewrite unrelated governance documents.

---

## Rule 8: Generated Artifacts

Do not manually edit generated files unless the task explicitly targets the generator.

When generated output changes:

1. Change the generator.
2. Regenerate the artifact.
3. Validate the artifact.

---

## Rule 9: Validation Before Completion

Before declaring work complete:

* run required validation
* review repository governance impact
* verify no authority conflicts were introduced
* verify no unsupported claims were added

---

## Rule 10: Honesty Over Progress

If the repository cannot honestly support a claim:

Do not make the claim.

Document the blocker instead.

A documented blocker is preferred over a false success.
