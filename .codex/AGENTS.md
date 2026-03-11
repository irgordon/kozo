# Global Agent Directives: Systems Engineering

## 1. Core Competencies
- Primary Languages: Odin (Kernel/Low-level), Rust (System Logic/High-level).
- Architecture: Microkernel, Clean Architecture, and Data-Oriented Design.
- Framework: Harness Engineering (Deterministic verification over generative guesswork).

## 2. Operational Protocol
- Procedural Integrity: Never modify source code without subsequent verification via the project harness (e.g., `./harness/verify.sh`).
- Documentation: Documentation is a technical debt and must be paid in the same commit as the code. ADRs and TSDoc/Docstrings are mandatory.
- Language Transitions: When bridging Odin and Rust, strictly adhere to the C-ABI and the project's FFI Manifest.

## 3. Engineering Rigor
- Memory: In Odin, avoid global state; use explicit allocators. In Rust, use `no_std` for core services.
- Safety: All `unsafe` blocks require a formal "SAFETY:" justification.
- Error Handling: No panics or silent failures. Use explicit error codes (Odin) or Result types (Rust).

## 4. Context Management
- State Preservation: Always update the "Current System State" in the project README.md before concluding a task.
- Information Gathering: If architectural intent is ambiguous, request clarification before proceeding with implementation.