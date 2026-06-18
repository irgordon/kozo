# KOZO Documentation Standard

Version: 1
Status: Authoritative
Scope: Documentation clarity, audience separation, claim discipline, structure, onboarding, and review standards

---

# 1. Purpose

This document defines how KOZO documentation is written and reviewed.

Documentation should reduce effort.

A reader should not need to decode internal language before understanding what KOZO is, what it does, what is proven, and what is not yet proven.

Good documentation helps a reader answer:

1. What is this?
2. What problem does it solve?
3. Why does it matter?
4. How do I start?
5. What happens next?

If a new reader cannot answer those questions quickly, the documentation should be simplified.

---

# 2. Authority

This document owns documentation construction rules.

It governs:

* documentation clarity
* audience separation
* claim discipline
* terminology consistency
* onboarding structure
* documentation review criteria
* documentation audit rules

This document does not own:

* architecture truth
* ABI truth
* syscall behavior
* compatibility claims
* generated artifact authority
* validator behavior
* release evidence requirements
* runtime behavior

Those topics are owned by their respective governance documents.

If this document conflicts with `GOVERNANCE.md`, `INVARIANTS.md`, `ARCHITECTURE.md`, `CONTRACTS.md`, or `COMPATIBILITY.md`, the higher-authority document wins.

---

# 3. Non-Goals

This document does not make KOZO production ready.

This document does not declare Linux compatibility.

This document does not define syscall semantics.

This document does not define ABI layouts.

This document does not make generated reports authoritative.

This document does not replace tests, validators, or contracts.

This document does not require user-facing language in every file. Developer, operator, and maintainer documents may use technical terms when those terms are needed and defined.

---

# 4. Audience Model

Each document must be written for a clear audience.

KOZO documentation uses these audience categories:

| Audience | Needs |
| --- | --- |
| New user | Understand what KOZO is and what it can currently do |
| Contributor | Understand how to safely change the repo |
| Maintainer | Understand governance, validation, release gates, and authority |
| Operator | Understand how to run checks and review evidence |
| Release reviewer | Understand whether release evidence supports the claimed scope |

A document should not switch audiences without warning.

Beginner-facing documentation should not require architecture knowledge before explaining the product.

Maintainer-facing documentation may be more technical, but it must still be clear.

---

# 5. Required Document Headers

Governance documents should include:

```text
Version:
Status:
Scope:
```

Recommended sections:

```text
Purpose
Authority
Non-goals
Rules
Relationship to other documents
```

Generated reports must include:

* generated warning
* source inputs
* non-authoritative status
* scope statement
* non-goal statement where relevant

---

# 6. First Impression Standard

The first section of an introductory document must explain the concrete object first.

A new reader should understand the basic purpose within 10-15 seconds.

The opening should answer:

* What is KOZO?
* What problem does this document solve?
* What can the reader do after reading it?
* What is not being claimed?

Avoid starting user-facing documents with internal architecture unless the document is explicitly architectural.

Preferred order:

1. State the problem.
2. State the benefit.
3. Describe the product or document.
4. Explain implementation details later.

Poor opening:

```text
KOZO provides deterministic validation through schema-backed agentic governance artifacts and ABI proof surfaces.
```

Better opening:

```text
KOZO is an experimental operating-system project with a strict verification harness. The harness checks that contracts, generated reports, and source files agree before changes are accepted.
```

---

# 7. Language Simplicity Standard

Use the simplest accurate word.

Avoid complex words when ordinary words work.

| Prefer | Avoid when simpler wording works |
| --- | --- |
| use | utilize, leverage |
| help | facilitate |
| run | execute |
| set up | provision |
| create | instantiate |
| file, report, result | artifact |
| rules, review process | governance |
| settings | configuration |
| permission, feature, access | capability |

Technical words are allowed when they are necessary.

When using a technical term, define it near first use.

Example:

```text
A validator is a Python check that returns pass or fail for one governed rule.
```

---

# 8. Outcome-First Standard

Explain what a feature protects, connects, or prevents.

Do not describe implementation before value.

Poor:

```text
The repo provides marker-level negative coverage.
```

Better:

```text
Every validator must have tests that prove it fails when an important rule is broken. This prevents a validator from passing just because a file or function name exists.
```

Poor:

```text
The syscall catalog summarizes ABI and syscall metadata.
```

Better:

```text
The syscall catalog gives reviewers one readable list of governed syscalls, their payload behavior, return behavior, and proof coverage.
```

---

# 9. Cognitive Load Standard

Use short sentences.

Present one idea at a time.

Avoid dense paragraphs.

A paragraph should usually stay under 6-8 lines.

Avoid introducing several concepts at once.

Poor:

```text
The generated governance index aggregates registered validators, schema-backed contracts, proof artifacts, generated reports, and release metadata to facilitate deterministic review workflows across the repository control plane.
```

Better:

```text
The generated governance index gives reviewers one page to inspect. It lists validators, contracts, schemas, generated reports, and the latest verification result. It is generated and non-authoritative.
```

---

# 10. New User Onboarding Standard

Introductory documentation must help a reader reach a small success quickly.

A new user should be able to find:

* what KOZO is
* what is currently proven
* what is not currently proven
* how to run verification
* what success looks like
* where to go next

Do not bury setup or verification instructions behind architecture detail.

A good quick-start path should include:

```text
1. Install required tools.
2. Run tests.
3. Run verification.
4. Inspect generated reports.
5. Read current limitations.
```

---

# 11. Terminology Consistency Standard

Use one term for one concept.

Do not use several names for the same thing.

Preferred KOZO terms:

| Concept | Preferred term |
| --- | --- |
| Python proof checks | validators |
| `artifacts/latest_verify.json` | latest verification artifact |
| Markdown generated from contracts | generated report |
| `contracts/*.json` and ABI header files | contracts |
| Rust no-payload syscall caller | runtime probe |
| Object/symbol smoke evidence | runtime-adjacent evidence |
| Non-authoritative Markdown summary | report |

Avoid switching between "proof," "check," "validation," and "test" unless the difference matters.

---

# 12. Audience Alignment Standard

Write for the audience of the document.

User-facing documents should explain outcomes before architecture.

Contributor documents should explain safe change process.

Maintainer documents should explain authority and release gates.

Operator documents should explain commands, expected output, and what failure means.

Release documents should explain evidence, blockers, and decisions.

Do not mix beginner explanation and internal implementation detail in the same section unless the transition is explicit.

---

# 13. Actionability Standard

Documentation should lead to action.

Instructions should include:

* command
* expected result
* failure meaning
* next step

Poor:

```text
Run the verification process.
```

Better:

```text
Run:

scripts/verify.sh

Success means `VERIFY: PASS` and `failed_check_count` is `0` in `artifacts/latest_verify.json`.
```

Avoid vague phrases such as:

* configure appropriately
* validate as needed
* use the correct process
* update documentation accordingly

Say exactly what to do.

---

# 14. Trust and Limitation Standard

Clear limitations increase trust.

Every document that describes capability must also describe limits.

Required limitation language for KOZO:

* no Linux compatibility claim
* no POSIX completeness claim
* no general userspace execution claim
* no process model claim
* no VFS claim
* no scheduler maturity claim
* no ELF loading claim
* no file descriptor behavior claim
* no production readiness claim

Use precise wording.

Good:

```text
This evidence proves object and symbol generation for the current kernel path. It does not prove QEMU boot or hardware syscall execution.
```

Bad:

```text
KOZO runtime execution is verified.
```

---

# 15. Claim Discipline

A documentation claim must be supported by evidence.

A good claim names:

* what is proven
* where it is proven
* what is not proven

Good:

```text
KOZO currently has governed source-level proof for `NOP`, `STATUS`, and `DEBUG_HEARTBEAT` syscalls through contracts, validators, and generated reports.
```

Bad:

```text
KOZO supports syscalls.
```

Good:

```text
The runtime smoke evidence is runtime-adjacent object/symbol evidence. It is not QEMU boot evidence.
```

Bad:

```text
KOZO has runtime execution.
```

Forbidden broad claims unless separately proven and scoped:

* production-ready
* Linux compatible
* POSIX compatible
* supports userspace
* secure
* complete
* stable ABI
* full syscall support

---

# 16. Generated Report Wording

Generated reports must say they are generated.

Generated reports must say they are non-authoritative.

Generated reports must identify their source inputs.

Generated reports must not define source truth.

Required wording pattern:

```text
This document is generated. Do not edit manually.

This report is non-authoritative. The source of truth remains the checked-in contracts, validators, and generated proof artifacts.
```

Generated reports may summarize values, but they must not silently become authority.

---

# 17. Duplication Rules

Do not copy source truth into prose unless the prose names the source of truth.

Do not duplicate compatibility policy across documents.

Do not duplicate ABI values across documents unless the value is generated or clearly marked as a summary.

Do not duplicate syscall behavior rules across documents unless the document owns that rule.

Prefer cross-references.

Example:

```text
For ABI layout authority, see `contracts/kozo_abi_manifest.json` and `docs/CONTRACTS.md`.
```

---

# 18. Cross-Reference Rules

When a document discusses a topic owned elsewhere, link to the owning document.

Examples:

* architecture -> `docs/ARCHITECTURE.md`
* invariants -> `docs/INVARIANTS.md`
* contracts -> `docs/CONTRACTS.md`
* generated artifacts -> `docs/GENERATED_ARTIFACTS.md`
* compatibility -> `docs/COMPATIBILITY.md`
* release evidence -> `docs/RELEASE_EVIDENCE.md`
* validation -> `docs/VALIDATION.md`

A lower-authority document must not redefine a higher-authority rule.

---

# 19. Documentation Clarity Audit

Use this audit when reviewing README files, governance documents, generated reports, release documents, and operator guides.

## 19.1 First Impression Test

Ask:

* Can a new reader understand what this document does within 10-15 seconds?
* Is the problem being solved obvious?
* Is the benefit clear?
* Are outcomes explained before implementation details?
* Would a non-expert understand the opening section?

Warning signs:

* jargon in the first section
* architecture before purpose
* long explanations before the benefit
* no clear statement of why the document exists

Required fix:

State the problem first.
State the benefit second.
Describe implementation later.

## 19.2 Language Simplicity Review

Ask:

* Can simpler words communicate the same meaning?
* Are acronyms introduced without explanation?
* Are specialized terms necessary?
* Is the document written for the intended audience?

Required fix:

Use the simplest accurate word.

## 19.3 Outcome-First Review

Ask:

* Does the document explain what the reader gains?
* Does it explain why a feature matters?
* Does it confuse implementation detail with value?

Required fix:

Translate every feature into a reader outcome.

## 19.4 Cognitive Load Review

Ask:

* Are sentences too long?
* Are multiple concepts introduced at once?
* Are there dense paragraphs?
* Does the reader need architecture knowledge before acting?

Required fix:

Use short sentences.
One idea per paragraph.
Break large concepts into smaller sections.

## 19.5 New User Onboarding Review

Ask:

* Can a new reader start quickly?
* Is there a small first success?
* Are advanced topics separated?
* Are setup and verification steps easy to find?

Required fix:

Give the reader a clear first action and expected result.

## 19.6 Terminology Consistency Review

Ask:

* Is the same concept called multiple names?
* Are abbreviations introduced and used consistently?
* Do documents contradict each other?

Required fix:

Use one term for one concept.

## 19.7 Audience Alignment Review

Ask:

* Is the intended audience clear?
* Does the language match that audience?
* Are beginner and expert concerns mixed?

Required fix:

Write for one audience per section.

## 19.8 Actionability Review

Ask:

* Can the reader identify the next step?
* Are commands specific?
* Are expected outcomes described?
* Are success conditions visible?

Required fix:

Say exactly what to do and what success looks like.

## 19.9 Trust and Credibility Review

Ask:

* Are limitations clearly stated?
* Are capabilities overstated?
* Are risks explained honestly?
* Are non-goals documented?

Required fix:

State limitations explicitly.

---

# 20. Documentation Success Criteria

A document is successful when the intended reader can answer:

1. What is this?
2. What problem does it solve?
3. Why should I use or read it?
4. How do I start?
5. What happens next?
6. What is not being claimed?

If the reader cannot answer those questions quickly, the document should be simplified.

---

# 21. Review Checklist

Reject or revise a documentation change if it:

* overclaims behavior
* omits scope
* omits non-goals
* conflicts with a higher-authority document
* duplicates source truth without attribution
* makes generated reports authoritative
* describes planned behavior as current behavior
* claims compatibility without evidence
* claims production readiness without release evidence
* uses jargon where ordinary language would work
* hides the reader's next action
* fails to define success conditions

---

# 22. Summary

Documentation should reduce effort, not demonstrate expertise.

Use simple words.

Start with outcomes.

Separate audiences.

State limits clearly.

Link to the owning document.

Do not overclaim.

Do not make generated reports authoritative.

The reader should spend effort understanding KOZO, not decoding the language used to describe it.
