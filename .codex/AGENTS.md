# .codex/AGENTS.md

## KOZO Global Agent Directives

- Languages: **Odin** for kernel/system code, **Rust** for bindings/tooling/services.
- Design: follow **SOLID**, keep a **single level of abstraction** per function/module, prefer small deterministic changes.
- Kernel rules: no Zig, no hidden allocation, no implicit global state, no panics in system-critical paths.
- FFI rules: all Odin/Rust boundaries must follow the **C ABI**; never edit generated bindings manually.
- Source of truth: do not duplicate protocol or structural rules; derive from `harness/registry.py` and `harness/invariants.py`.
- Harness: keep pure logic in `harness/`, I/O in `scripts/`; preserve canonical validator coverage and order.
- Validation: run the project verification flow before commit/push; at minimum use relevant `odin check`, `cargo fmt --check`, `cargo clippy`, and `cargo test`.
- Safety: every Rust `unsafe` block requires a `SAFETY:` justification.
- Errors: use explicit error handling; no silent failure paths.
- Scope: do not modify files outside the active task scope.
- Docs: update documentation needed to keep the architecture and current state accurate in the same change.
- Ambiguity: fail closed—surface unclear protocol or architecture before proceeding.