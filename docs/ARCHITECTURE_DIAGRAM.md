# KOZO Architecture Diagram

Version: 1
Status: Descriptive
Scope: Non-authoritative visual explanation of current repository structure, validation flow, and ABI binding flow

---

# 1. Purpose

This document provides a descriptive diagram of KOZO repository structure.

It helps reviewers understand the relationship between the harness pipeline, contracts, generated artifacts, kernel layer, Rust userspace layer, and ABI bindings.

---

# 2. Authority

This document is non-authoritative.

It does not govern architecture, invariants, contracts, validation rules, generated artifact policy, compatibility claims, security rules, or coding style.

Authoritative structure is defined in `docs/ARCHITECTURE.md`.

Document precedence and conflict rules are defined in `docs/GOVERNANCE.md`.

---

# 3. Non-Goals

This document does not define runtime behavior.

This document does not define ABI truth.

This document does not define syscall behavior.

This document does not make generated artifacts authoritative.

This document does not claim Linux compatibility, userspace execution, process model behavior, VFS behavior, file descriptor behavior, or production readiness.

---

# 4. Diagram Rules

This diagram must not override:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/CONTRACTS.md`
* validators
* schemas
* contracts
* generated artifact policy
* generated reports

If this document conflicts with an authoritative document, the authoritative document wins and this document must be corrected.

---

# 5. Repository Flow

```text
                                     KOZO SYSTEM
                         Descriptive Repository Structure
──────────────────────────────────────────────────────────────────────


                         ┌──────────────────────────────┐
                         │       Governance Docs        │
                         │                              │
                         │  docs/GOVERNANCE.md         │
                         │  docs/INVARIANTS.md         │
                         │  docs/ARCHITECTURE.md       │
                         │  docs/CONTRACTS.md          │
                         │  docs/VALIDATION.md         │
                         └──────────────┬───────────────┘
                                        │
                                        ▼

                         ┌──────────────────────────────┐
                         │          Contracts           │
                         │                              │
                         │  contracts/kozo_abi.h       │
                         │  contracts/*.json           │
                         └──────────────┬───────────────┘
                                        │
                ┌───────────────────────┼───────────────────────┐
                │                       │                       │
                ▼                       ▼                       ▼

      ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
      │  Odin Kernel     │    │ Rust Userspace   │    │ Python Harness   │
      │                  │    │                  │    │                  │
      │  kernel/         │    │ userspace/       │    │ harness/         │
      │                  │    │                  │    │ scripts/         │
      │ runtime authority│    │ kernel clients   │    │ dev validation   │
      └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
               │                       │                       │
               └───────────────┬───────┴───────────────────────┘
                               │
                               ▼

                     ┌──────────────────────┐
                     │ Generated Artifacts  │
                     │                      │
                     │ bindings/           │
                     │ docs/generated/     │
                     │ artifacts/          │
                     └──────────────────────┘
```

---

# 6. Harness Pipeline

```text
scripts/verify.sh
      │
      ▼
harness validators in canonical registry order
      │
      ▼
harness/aggregator.py
      │
      ▼
artifacts/latest_verify.json
```

The harness pipeline is a development-time proof mechanism.

It is not part of the operating system runtime.

---

# 7. ABI Binding Flow

```text
contracts/kozo_abi.h
      │
      ▼
governed ABI generation flow
      │
      ├── bindings/rust/kozo_abi.rs
      └── bindings/odin/kozo_abi.odin
```

Generated bindings are outputs.

They must not be edited directly.

ABI authority remains with checked-in contracts and governed manifests.

---

# 8. Generated Report Flow

```text
contracts and manifests
      │
      ▼
deterministic report renderers
      │
      ├── docs/generated/syscall_surface.md
      └── docs/generated/abi_surface.md
```

Generated reports are review surfaces.

They are non-authoritative.

---

# 9. Relationship to Other Governance Documents

`docs/GOVERNANCE.md` owns precedence and conflict rules.

`docs/ARCHITECTURE.md` owns system structure.

`docs/CONTRACTS.md` owns contract authority.

`docs/VALIDATION.md` owns harness validation rules.

`docs/GENERATED_ARTIFACTS.md` owns generated-file policy.

