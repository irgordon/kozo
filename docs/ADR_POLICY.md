# KOZO ADR Policy

Version: 1
Status: Authoritative
Scope: Architecture Decision Record requirements, lifecycle, and relationships

---

# 1. Purpose

This document defines when KOZO requires an Architecture Decision Record and how ADRs relate to governance.

An ADR records why a decision was made. Governance documents record the current rule.

---

# 2. Authority

This document owns ADR requirements.

It is subordinate to `docs/GOVERNANCE.md`, `docs/INVARIANTS.md`, `docs/ARCHITECTURE.md`, and `docs/CONTRACTS.md`.

It does not own architecture content, ABI truth, syscall semantics, compatibility policy, or generated artifact authority.

---

# 3. Non-Goals

An ADR does not override governance documents.

An ADR does not replace contracts.

An ADR does not make generated reports authoritative.

An ADR does not record routine implementation details unless they change a governed decision.

---

# 4. When an ADR Is Required

An ADR is required when a change alters:

* architecture model
* document authority
* non-negotiable invariants
* ABI contract model
* syscall boundary semantics
* validator coverage governance
* generated artifact authority
* compatibility claim policy
* security boundary assumptions
* major subsystem responsibilities

---

# 5. Rules

An ADR records a decision; it does not override governance.

A governance document records the current rule.

Superseded ADRs remain historical, not current authority.

Conflicts between ADRs and governance documents must be resolved explicitly.

---

# 6. When an ADR Is Not Required

An ADR is not required for:

* typo fixes
* formatting changes
* generated artifact refreshes
* tests that do not change policy
* implementation changes that stay inside existing contracts
* wording clarifications that do not change authority or behavior

---

# 7. ADR Format

An ADR should include:

* title
* status
* context
* decision
* consequences
* affected governance documents
* affected contracts or validators
* superseded decisions, if any

---

# 8. Decision Lifecycle

ADR statuses should be explicit:

* `Proposed`
* `Accepted`
* `Superseded`
* `Deprecated`

Only accepted ADRs describe current decisions.

Superseded ADRs remain in history but no longer govern the current rule.

---

# 9. Supersession Rules

A superseding ADR must name the ADR it supersedes.

The superseding ADR must explain why the prior decision changed.

Governance documents must be updated if the current rule changes.

---

# 10. Relationship to Governance Documents

Governance documents define current authority.

ADRs explain decision history.

If an accepted ADR conflicts with a current governance document, update one of them. Do not leave the conflict unresolved.

---

# 11. Relationship to CHANGELOG

`CHANGELOG.md` records completed changes.

It may mention an ADR-related change, but it does not replace the ADR and does not govern future behavior.

---

# 12. Relationship to Contracts

Contract model changes usually require an ADR.

Contract value changes may require an ADR when they alter boundary semantics, ABI model, or compatibility/security assumptions.

Routine contract additions inside an accepted model may not require a new ADR.

---

# 13. Relationship to Generated Reports

Generated reports do not require ADRs for routine refresh.

Changing generated artifact authority, report source truth, or drift-validation policy requires an ADR.

---

# 14. Relationship to Other Governance Documents

`GOVERNANCE.md` owns document precedence.

`INVARIANTS.md` owns non-negotiable truths.

`ARCHITECTURE.md` owns system structure.

`CONTRACTS.md` owns contract authority.

`VALIDATION.md` owns proof process.
