# KOZO Documentation Audit

Version: 1
Status: Current maintainer record
Scope: v0.8.9 user, maintainer, engineering, and source-comment review

## Scope

This audit reviews the root README, every Markdown file under `docs`, the
commands presented to new users, local Markdown links, current evidence claims,
and comments in runtime, harness, script, userspace, and linker sources.

Generated files were inspected but not edited manually.

## Audience Model

KOZO uses three primary reading paths:

1. **User:** purpose, current value, setup, operation, expected results, limits.
2. **Maintainer:** authority, safe changes, validation, generated files, release
   workflow.
3. **Engineer:** exact boot, CPU, memory, privilege, request, evidence, and
   failure behavior.

The user is the first audience. User and maintainer guidance begins in
`docs/wiki`. Detailed engineering and governance records remain in `docs`.

## Document Inventory

| Document | Primary audience | Purpose | Authority | Current or historical | Action |
| --- | --- | --- | --- | --- | --- |
| `README.md` | User | Project front door | Descriptive | Current | Rewritten around purpose, use, result, limits, and wiki navigation |
| `docs/wiki/README.md` | User | Guided documentation entry | Descriptive | Current | Added |
| `docs/wiki/WHY_KOZO.md` | User | Problem and value | Descriptive | Current | Added |
| `docs/wiki/GETTING_STARTED.md` | User | Tested setup and run path | Descriptive | Current | Added |
| `docs/wiki/USER_GUIDE.md` | User | Current runtime behavior | Descriptive | Current | Added |
| `docs/wiki/MAINTAINER_GUIDE.md` | Maintainer | Safe change and verification path | Descriptive | Current | Added |
| `docs/wiki/TROUBLESHOOTING.md` | Maintainer | Failure diagnosis | Descriptive | Current | Added |
| `docs/wiki/TERMS.md` | User | Plain-language translation | Descriptive | Current | Added |
| `docs/wiki/ENGINEERING_OVERVIEW.md` | Engineer | Bridge to exact documents | Descriptive | Current | Added |
| `docs/GOVERNANCE.md` | Governance | Document precedence | Authoritative | Current | Retained |
| `docs/INVARIANTS.md` | Governance | Non-negotiable truths | Authoritative | Current | Retained |
| `docs/ARCHITECTURE.md` | Engineer | System boundaries | Authoritative | Current | Linked from wiki |
| `docs/ARCHITECTURE_DIAGRAM.md` | Engineer | Visual system summary | Descriptive | Current | Retained |
| `docs/CONTRACTS.md` | Engineer | Contract authority | Authoritative | Current | Linked from wiki |
| `docs/CODING_STYLE.md` | Maintainer | Code construction rules | Authoritative | Current | Minimal-comment rule clarified |
| `docs/DOCUMENTATION_STANDARD.md` | Maintainer | Documentation rules | Authoritative | Current | Three-audience and wiki policy added |
| `docs/VALIDATION.md` | Maintainer | Verification policy | Authoritative | Current | Linked from wiki |
| `docs/GENERATED_ARTIFACTS.md` | Maintainer | Generated-file policy | Authoritative | Current | Linked from wiki |
| `docs/COMPATIBILITY.md` | Governance | Claim limits | Authoritative | Current | Retained |
| `docs/SECURITY_MODEL.md` | Engineer | Trust boundaries | Authoritative | Current | Linked from wiki |
| `docs/ADR_POLICY.md` | Governance | Decision-record policy | Authoritative | Current | Retained |
| `docs/BOOT.md` | Engineer | Boot baseline and timeline | Authoritative | Current with history | Stale opening corrected; history retained |
| `docs/BOOT_BLOCKERS.md` | Release evidence | Boot failure vocabulary | Authoritative | Current with history | Retained |
| `docs/BOOT_IMAGE.md` | Engineer | Initial image shape | Authoritative | Historical phase with current structure | Retained and classified |
| `docs/BOOT_PROTOCOL.md` | Engineer | Limine decision | Authoritative | Current decision with history | Retained |
| `docs/BOOT_TOOLING.md` | Maintainer | Tool acquisition | Authoritative | Current | Linked from setup |
| `docs/CPU_EXTENDED_STATE.md` | Engineer | x87/SSE initialization | Contract explanation | Current | Linked from overview |
| `docs/PAGING.md` | Engineer | Fixed page tables | Contract explanation | Current | Linked from overview |
| `docs/PRIVILEGE_TRANSITION.md` | Engineer | Fixed Ring 3 round trip | Contract explanation | Current | Linked from overview |
| `docs/USER_REQUEST_BOUNDARY.md` | Engineer | Fixed request copy path | Contract explanation | Current | Hosted status corrected |
| `docs/USER_RESPONSE_CONSUMPTION.md` | Engineer | Fixed response consumption | Contract explanation | Current | Retained |
| `docs/USER_RUNTIME_STATUS_SERVICE.md` | Engineer | Shared status service | Contract explanation | Current | Hosted status corrected |
| `docs/RUNTIME_CAPABILITIES.md` | Engineer | Two internal operations | Contract explanation | Current | Linked from overview |
| `docs/RUNTIME_EVIDENCE.md` | Release evidence | Runtime proof path | Authoritative | Current with history | Linked from wiki |
| `docs/RUNTIME_EVIDENCE_REVIEW.md` | Release evidence | Claim review gate | Authoritative | Current | Retained |
| `docs/RELEASE_CHECKLIST.md` | Release evidence | Release approval | Authoritative | Current | Linked from maintainer guide |
| `docs/RELEASE_EVIDENCE.md` | Release evidence | Required proof | Authoritative | Current | Linked from maintainer guide |
| `docs/REQUIRED_CHECKS.md` | Release evidence | Required local and CI checks | Authoritative | Current | Linked from maintainer guide |
| `docs/PHASEMAP.md` | Governance | Phase sequence | Planning | Current with historical rows | v0.8.8/v0.8.9 alignment added |
| `docs/ROADMAP.md` | Governance | Product direction | Planning | Current with historical rows | v0.8.8/v0.8.9 alignment added |
| `docs/CODEBASE_AUDIT.md` | Historical record | Append-only structural findings | Authoritative record | Historical sections plus current append | New v0.8.9 findings appended |
| `docs/adr/0016-kernel-entry-and-syscall-bridge.md` | Historical record | Original function-call bridge decision | Accepted decision | Historical for current runtime | Historical label and current links added |
| `docs/decisions/0001-boot-protocol.md` | Historical record | Limine selection | Accepted decision | Historical context, active decision | Retained |
| `docs/generated/abi_surface.md` | Generated | ABI review surface | Non-authoritative | Current generated output | Inspected only |
| `docs/generated/syscall_surface.md` | Generated | Syscall review surface | Non-authoritative | Current generated output | Inspected only |
| `docs/generated/governance_index.md` | Generated | Governance review surface | Non-authoritative | Current generated output | Refreshed through generator |

## Duplicate Content

The previous README repeated old architecture claims and a function-call trap
status that no longer described the accepted fixed Ring 3 path. It now
summarizes current behavior and links to owning documents.

The wiki does not copy contract geometry or the 41-marker taxonomy. It explains
their purpose and gives commands or links for the authoritative values.

## Stale Content

Corrected current-facing statements include:

- the README's ARM64, broad security, and obsolete no-privilege-transition
  claims;
- the boot document's opening statement that the current result was blocked;
- hosted-CI-pending wording for the accepted fixed request and runtime-status
  service;
- phase-map and roadmap text that stopped at v0.8.7;
- the original bridge ADR's lack of a historical label.

Historical check counts and blockers remain where they describe a named phase
or CI run.

## Missing Content

The repository had no user-first path, copyable getting-started guide,
plain-language glossary, maintainer workflow, or consolidated troubleshooting
guide. The required wiki pages now provide those entry points.

## Broken Links

The initial local-link scan found no relative Markdown links to validate because
the documentation mostly used unlinked code paths. The v0.8.9 pages add local
navigation. A repository-relative link scan validates every new target.

External links are not treated as local authority.

## Command Validation

Every executable command in the wiki was run during v0.8.9. Commands that
inspect a working tree or generated artifact were run from the repository root.
The clone sequence was run in a temporary directory. The governed build, QEMU,
and verification commands used explicit local tool variables.

Expected no-match and known local-tool failures are recorded in the final phase
report rather than described as successful commands.

## Terminology Issues

The old README assumed familiarity with microkernels, trap paths, and security
architecture. User pages now introduce behavior first and use plain terms such
as progress marker, startup sequence, fixed request path, memory map, user mode,
kernel mode, and final safe stop.

`docs/wiki/TERMS.md` retains the engineering term beside each translation so a
reader can move into detailed documents without losing precision.

## Readability Issues

Long historical timelines remain difficult to read but are preserved as
engineering and release records. The wiki provides a short current path rather
than rewriting those records into introductory material.

## Historical Versus Current Claims

Historical records keep phase-specific counts, blockers, and decisions.
Current pages name the accepted baseline: 67 checks, no failures, QEMU pass,
and 41 ordered markers. Generated evidence remains the source for the result of
an individual run.

## Source Comment Audit

The audit reviewed 123 non-generated `.odin`, `.asm`, `.inc`, `.rs`, `.py`,
`.sh`, and `.ld` files under `kernel`, `userspace`, `harness`, `scripts`, and
`linker`.

- **Comments removed:** 176 lines of templated function headers and comments
  that repeated clear function names or control flow.
- **Comments shortened:** five long assembly or GNU/LLVM parsing explanations
  became compact boundary notes.
- **Comments retained:** register inputs and clobbers, stack alignment,
  direction-flag handling, fixed copy sizes, volatile evidence, fail-closed
  behavior, tool discovery, GNU/LLVM differences, generated-file ownership,
  and the stable ABI validator shim.
- **TODOs removed:** none; no vague TODO, FIXME, XXX, or HACK marker exists in
  the audited source set.
- **TODOs retained:** none.
- **Commented-out code removed:** none was present in the audited source set.

The source changes remove comments only. They do not change instructions,
control flow, data layout, ABI, markers, or validator behavior.

## Recommended Changes

Use `docs/wiki` for future user or maintainer onboarding. Keep exact contract
fields and implementation geometry in their owning documents. Add a wiki page
only when the information cannot be placed clearly in the existing eight-page
structure.

## Completed Changes

- added the user and maintainer wiki;
- rewrote the README;
- added the term translation table;
- added tested setup and troubleshooting paths;
- clarified documentation and comment standards;
- corrected current hosted-status drift;
- aligned planning records through v0.8.9;
- removed redundant source comments without changing behavior.

## Deferred Items

- Historical boot and audit timelines remain long by design.
- A general Markdown or website framework was not added.
- External URL availability is not treated as a repository proof.
- Release-candidate packaging and publication remain v1.0.0-rc.1 work.
