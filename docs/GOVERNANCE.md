# KOZO Governance

Version: 1
Status: Authoritative
Scope: Documentation authority, conflict resolution, amendment rules, decision records, and generated artifact authority

---

# 1. Purpose

This document defines how KOZO governance documents relate to each other.

Its job is to prevent authority conflicts.

A governance document must answer one question clearly:

What does this document own?

No document should silently define rules that belong to another document.

---

# 2. Authority

This document is the highest documentation authority in the KOZO repository.

It owns:

* document precedence
* conflict resolution
* amendment rules
* decision-record requirements
* authority boundaries between governance documents
* generated report authority
* diagram authority

It does not own:

* kernel architecture details
* ABI field values
* syscall behavior
* coding style
* validation implementation details
* compatibility claims
* security mechanism details

Those topics are owned by narrower governance documents.

---

# 3. Non-Goals

This document does not define runtime behavior.

This document does not define ABI values.

This document does not define syscall semantics.

This document does not define coding style, compatibility claims, or security mechanisms.

This document does not make diagrams, generated reports, changelog entries, or README summaries authoritative.

---

# 4. Rules

Higher-authority documents override lower-authority documents.

Lower-authority documents may explain higher rules, but they must not weaken, redefine, or bypass them.

Diagrams are descriptive only.

Generated reports are non-authoritative.

`CHANGELOG.md` records completed changes but does not govern.

`README.md` introduces the project but does not govern.

---

# 5. Document Precedence

When governance documents disagree, the higher document in this list wins.

1. `docs/GOVERNANCE.md`
2. `docs/INVARIANTS.md`
3. `docs/ARCHITECTURE.md`
4. `docs/CONTRACTS.md`
5. `docs/CODING_STYLE.md`
6. `docs/VALIDATION.md`
7. `docs/GENERATED_ARTIFACTS.md`
8. `docs/COMPATIBILITY.md`
9. `docs/SECURITY_MODEL.md`
10. `docs/ADR_POLICY.md`
11. `docs/ARCHITECTURE_DIAGRAM.md`
12. `CHANGELOG.md`
13. `README.md`

The order protects the project from accidental contradiction.

A lower document may explain a higher rule, but it must not weaken, redefine, or bypass it.

---

# 6. Authority Boundaries

## 6.1 `GOVERNANCE.md`

Owns document authority.

It defines:

* precedence
* conflict handling
* amendment rules
* generated report authority
* diagram authority
* when an Architecture Decision Record is required

It does not define technical implementation rules.

---

## 6.2 `INVARIANTS.md`

Owns non-negotiable technical truths.

It defines what must always remain true.

Examples:

* harness code is not runtime code
* generated reports are non-authoritative
* generated bindings must not be edited directly
* validators must have marker-level negative coverage

It does not define file organization or code style.

---

## 6.3 `ARCHITECTURE.md`

Owns system structure and responsibility boundaries.

It defines:

* KOZO’s architectural model
* kernel, userspace, and harness responsibilities
* major system boundaries
* runtime interaction model

It does not define coding style, generated artifact policy, or validator implementation rules.

---

## 6.4 `CONTRACTS.md`

Owns contract purpose and contract authority.

It defines:

* what a contract is
* which files are contracts
* what each contract protects
* how contracts relate to generated reports and validators

It does not define runtime implementation behavior unless a contract explicitly owns that behavior.

---

## 6.5 `CODING_STYLE.md`

Owns code construction rules.

It defines how code should be written.

It does not define architecture, ABI truth, syscall semantics, compatibility claims, or generated artifact authority.

---

## 6.6 `VALIDATION.md`

Owns harness and verification process rules.

It defines:

* `scripts/verify.sh`
* validator registry behavior
* artifact verification
* validator coverage governance
* coverage-depth governance
* generated report drift validation

It does not define kernel architecture or ABI values.

---

## 6.7 `GENERATED_ARTIFACTS.md`

Owns generated-file edit policy.

It defines:

* which files are generated
* which files humans may not edit directly
* what generator produces each artifact
* what validator protects each artifact
* how stale artifacts are refreshed

It does not define the source truth that generated files summarize.

---

## 6.8 `COMPATIBILITY.md`

Owns compatibility claims and non-goals.

It defines:

* allowed compatibility claim format
* forbidden broad claims
* evidence required before compatibility claims
* current compatibility non-goals

It does not implement compatibility.

---

## 6.9 `SECURITY_MODEL.md`

Owns security boundary rules.

It defines:

* capability model
* opaque handles
* pointer exposure rules
* userspace pointer distrust
* syscall boundary validation
* harness file-scope enforcement

It does not define code style or validator registration mechanics.

---

## 6.10 `ADR_POLICY.md`

Owns Architecture Decision Record rules.

It defines:

* when an ADR is required
* ADR format
* decision lifecycle
* supersession rules
* relationship to changelog and governance docs

---

## 6.11 `ARCHITECTURE_DIAGRAM.md`

Owns visual explanation only.

It is descriptive and non-authoritative.

It may show the system shape, but it must not define rules.

If the diagram conflicts with an authoritative governance document, the authoritative document wins.

---

# 7. Conflict Resolution

A conflict exists when two documents make incompatible claims.

Examples:

* one document says generated reports are authoritative, while another says they are not
* one document claims Linux compatibility, while compatibility governance says no such claim is allowed
* one document permits manual generated binding edits, while generated artifact governance forbids them

When a conflict is found:

1. Identify the documents involved.
2. Apply the precedence order.
3. Keep the higher-authority rule.
4. Patch or remove the lower-authority conflicting text.
5. Add an Architecture Decision Record if the change alters architecture, contract authority, or validation policy.
6. Update the changelog if the correction changes repository governance state.

Do not resolve conflicts by leaving both claims in place.

---

# 8. Amendment Rules

Governance documents may change, but changes must be explicit.

A governance amendment must include:

* the document changed
* the rule changed
* why the change is needed
* whether any lower documents must be updated
* whether any validators or schemas must be updated
* whether an ADR is required

Changes to these files usually require an ADR:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/CONTRACTS.md`
* `docs/SECURITY_MODEL.md`
* contract files under `contracts/`

Small wording clarifications do not require an ADR if they do not alter authority, architecture, or behavior.

---

# 9. Architecture Decision Records

An ADR is required when a change does one or more of the following:

* changes the architecture model
* changes document authority order
* changes a non-negotiable invariant
* changes the ABI contract model
* changes syscall boundary semantics
* changes validator coverage governance
* changes generated artifact authority
* adds or removes a major subsystem
* changes compatibility claim policy
* changes security boundary assumptions

ADRs must not replace governance documents.

An ADR records why a decision was made.
A governance document records the current rule.

---

# 10. Generated Reports

Generated reports are non-authoritative.

Examples:

* `docs/generated/syscall_surface.md`
* `docs/generated/abi_surface.md`
* `docs/generated/governance_index.md`
* `artifacts/latest_verify.json`

Generated reports summarize source truth.

They do not define source truth.

A generated report must not override:

* contracts
* schemas
* validators
* architecture documents
* invariants
* source code behavior

If a generated report is stale, regenerate it.

Do not manually edit generated reports unless a specific generator workflow requires temporary local debugging. Such edits must not be committed.

---

# 11. Contracts

Contracts define system boundaries.

Contract files live under:

```text
contracts/
```

Contracts are more authoritative than generated reports.

Examples:

* `contracts/kozo_abi.h`
* `contracts/kozo_abi_manifest.json`
* `contracts/syscall_boundary_contract.v0.json`
* `contracts/syscall_table_contract.v0.json`
* `contracts/syscall_class_contract.v0.json`
* `contracts/syscall_catalog.v0.json`

Contract changes must be validated by focused tests and verification.

---

# 12. Validators

Validators enforce contracts, schemas, generated report freshness, and repository governance.

Validators must be deterministic.

Validators must fail closed.

Validators must have focused tests.

Every registered validator must have marker-level negative coverage.

A validator must not silently skip proof because a tool, file, or source path is missing.

If evidence is missing, the validator must fail unless a higher governance document explicitly allows a scoped exception.

---

# 13. Compatibility Claims

Compatibility claims must be scoped and evidence-backed.

Broad claims are forbidden unless specifically proven.

Forbidden broad claims include:

* KOZO is Linux compatible
* KOZO supports Linux applications
* KOZO is POSIX complete
* KOZO supports userspace execution
* KOZO supports a process model
* KOZO supports VFS behavior
* KOZO supports file descriptor behavior
* KOZO is production ready

Allowed scoped claims must name:

* tested behavior
* tested architecture
* tested command or artifact
* validator or evidence
* known limits

---

# 14. Diagrams

Diagrams are explanatory.

They may show:

* system structure
* data flow
* validation flow
* artifact flow
* agent loop flow

They must not define:

* architecture authority
* ABI truth
* syscall semantics
* compatibility claims
* validator policy
* generated artifact authority

A diagram must include a status header that says it is descriptive and non-authoritative.

---

# 15. Changelog Relationship

`CHANGELOG.md` records completed repository changes.

It does not define authority.

If the changelog conflicts with governance documents, governance documents win.

A changelog entry should not create future obligations.
Future plans belong in roadmap or task files.

---

# 16. README Relationship

`README.md` is an introduction.

It may summarize governance and architecture.

It must not override governance documents, invariants, contracts, or validation rules.

If the README conflicts with a governance document, update the README.

---

# 17. Required Document Headers

Each governance document should include:

```text
Version:
Status:
Scope:
```

Recommended statuses:

* `Authoritative`
* `Descriptive`
* `Generated`
* `Deprecated`

Only authoritative documents define rules.

Generated documents are never authoritative unless this governance document is amended to allow a specific exception.

---

# 18. Relationship to Other Governance Documents

This document defines how all governance documents relate to each other.

Each narrower document owns only its stated domain.

When relationships are unclear, this document decides the authority boundary.

---

# 19. Summary

`GOVERNANCE.md` owns authority.

`INVARIANTS.md` owns what must remain true.

`ARCHITECTURE.md` owns system structure.

`CONTRACTS.md` owns boundary contracts.

`CODING_STYLE.md` owns code construction.

`VALIDATION.md` owns verification.

`GENERATED_ARTIFACTS.md` owns generated-file rules.

`COMPATIBILITY.md` owns compatibility claims.

`SECURITY_MODEL.md` owns security boundaries.

`ARCHITECTURE_DIAGRAM.md` explains but does not govern.
