# Changelog

## v0.0.9 - 2026-05-31

- Hardened `bridge_alignment` so the harness validates the ordered live `syscall_entry` block instead of accepting bridge snippets that merely appear somewhere in `syscall.asm`.
- Added named immutable bridge contracts for the assembly symbols, Odin dispatcher signature, ordered register moves, stack alignment, dispatcher handoff, restore path, and return instruction.
- Added focused negative tests for dead snippets outside `syscall_entry`, out-of-order anchors, missing dispatcher handoff, missing Odin dispatcher signature, and missing entry block diagnostics.
- Hardened `runtime_trap_path` so the harness validates the live Rust `heartbeat_request` path and bridge helper instead of accepting unrelated extern bridge snippets.
- Added focused `runtime_trap_path` tests for missing live anchors, wrong request sentinels, out-of-order request construction, dead extern calls, and missing heartbeat request diagnostics.
- Hardened `execution_proof` as the high-level observable heartbeat execution proof by validating the live Odin `DEBUG_HEARTBEAT` branch and stable serial observation strings.
- Added focused `execution_proof` tests for missing nil guards, missing heartbeat branch, dead mutation snippets, out-of-order mutations, missing `status_bits` mutation, and missing serial observations.
- Regenerated the verification artifact so `latest_verify.json` records `bridge_alignment`, `runtime_trap_path`, `return_path_proof`, and `execution_proof` passing with the hardened proof details.
- Added `validator_coverage` governance so every registered validator must declare a focused test file with behavioral negative-path coverage.
- Added AST-based coverage checks that reject placeholder negative tests unless they invoke the validator or approved harness/helper path, assert failure behavior, and tie the negative test body to the configured validator token.
- Added focused negative tests for previously uncovered validators and regression coverage for missing files, missing mappings, missing validator invocation, missing failure assertions, and token-only false passes.
- Extended `validator_coverage` with marker-depth governance so each validator declares required negative coverage markers that must map to behavioral negative tests.
- Added `KOZO_NEGATIVE_COVERAGE` metadata to focused validator tests and regression coverage for missing metadata, missing required markers, unknown markers, missing mapped functions, and mapped tests without behavior.
- Added ABI manifest v0 as the machine-readable contract for currently proven syscall constants, status constants, heartbeat payload layout, generated binding paths, and heartbeat request/response sentinels.
- Added an `abi_manifest` validator with schema-backed manifest loading and focused negative coverage for missing files, invalid JSON, schema violations, missing binding paths, constant drift, layout drift, and diagnostic quality.
- Rewired `protocol_contract_alignment` and `layout_parity` to read proven ABI values from the manifest instead of duplicating local validator constants.
- Documented ABI manifest v0 as a current proof artifact only; it does not declare a stable public ABI, Linux compatibility, additional syscalls, or runtime behavior changes.
- Added syscall boundary contract v0 for the currently proven x86_64 heartbeat/debug syscall path.
- Added a schema-backed syscall boundary loader and `syscall_boundary_contract` validator.
- Added focused negative coverage for boundary contract failures, including register drift, missing ABI manifest references, sentinel mismatches, invalid payload retention, unknown mutable fields, and unknown proof validator references.
- Documented syscall boundary contract v0 as a current heartbeat/debug proof artifact only; it does not add new syscalls, Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, or runtime behavior changes.

## v0.0.8 - 2026-05-30

- Replaced Rust-side debug assertions with explicit post-call return-path validation so the caller checks `abi::K_OK`, `payload.sequence == 0xCAFEFEEE`, `payload.timestamp == 0xDEADBEEF`, and `payload.status_bits == abi::K_OK` after `syscall_entry` returns.
- Added a heavy failure helper on the Rust side so return-path contract violations fail closed instead of relying on debug-only assertions.
- Added `return_path_proof` validation so the harness fails if Rust stops inspecting the returned payload, checks the wrong constants, removes sequence/timestamp/status-bits checks, reintroduces a local stub, or if Odin stops writing the full response through the payload pointer.
- Added focused negative tests so the proof fails when the Rust status-bits check or Odin status-bits success write is removed, including cases where `status_bits` appears only in unrelated text.
- Regenerated the verification artifact so `latest_verify.json` records `return_path_proof: pass` as part of the current proof surface.

## v0.0.7 - 2026-03-19

- Replaced the Rust heartbeat local stub with an extern `syscall_entry` bridge call so the implemented request path becomes `Rust -> syscall_entry (asm) -> syscall_dispatch (Odin)`.
- Updated `kernel/arch/x86_64/syscall.asm` to accept the normal function-call ABI, map ingress values into the bridge registers, preserve `rbx`, and then forward the request into the unchanged Odin dispatcher contract.
- Added `runtime_trap_path` validation so the harness fails closed if a local stub reappears, the extern bridge call is missing, or the syscall bridge symbol/mapping drifts.
- Updated repository status, task metadata, and verification artifacts to describe the boundary as an exercised assembly bridge rather than a simulated stub path.

## v0.0.6 - 2026-03-19

- Fixed `scripts/verify.sh` so an empty changed-file set no longer aborts the run under `set -euo pipefail`, and updated the script to emit the generated verification artifact JSON directly.
- Added fresh verification evidence generation for `odin check`, `odin build`, `cargo check`, and host object inspection so `artifacts/latest_verify.json` is reproducible from the current tree.
- Replaced the broken default serial port inline assembly path with a build-safe stub and gated architecture-specific kernel behavior so `odin build kernel` and `odin build kernel -build-mode:obj -out:artifacts/kernel.o` succeed on the host.
- Marked the Rust heartbeat path as explicit `STUB MODE`, documented that the syscall boundary is still simulated, and renamed `protocol_alignment` to `protocol_contract_alignment` so the harness reports the current system truthfully.
- Hardened protocol validation to reject unlabeled local syscall stubs and strengthened execution-foundation proof by checking freestanding amd64 bridge symbols and NASM-assembled trap objects.

## v0.0.5 - 2026-03-15

- Added source-level execution proof validation for the heartbeat syscall path across Odin, Rust, and the verification harness.
- Implemented the ordered Odin arbiter sequence with nil guard, magic-value guard, stable ingress/egress trace strings, ordered pointer mutation, and ABI-backed return values.
- Updated the Rust core service to initialize the normative magic payload, branch explicitly on `abi::K_OK`, assert postconditions, and enter a heavy failure path on error.
- Extended the verify artifact format to carry granular `sub_results` for `execution_proof`, making field-level proof status visible in `latest_verify.json`.
- Verified the negative proof by changing the Rust-side magic value and confirming `execution_proof` fails before restoring the correct contract.

## v0.0.4 - 2026-03-14

- Added the x86_64 boot foundation bridge with `_start`, a 16KB aligned bootstrap stack, and exported Odin `kernel_entry` / `syscall_dispatch` entry symbols.
- Added ADR-0016 to document the assembly-to-Odin entry flow, trap ingress registers, preservation rules, and stack alignment expectations.
- Added execution foundation validation so the harness proves the presence of the required boot and syscall bridge symbols even when full object-symbol inspection is environment-dependent.
- Added semantic trap-path validation so the harness proves the normative `rax -> rdi` and `rbx -> rsi` register bridge into the exported Odin dispatcher signature.
- Verified the negative proof for trap drift by swapping the ingress register moves and confirming `bridge_alignment` fails before restoring the correct mapping.
- Regenerated `latest_verify.json` and `agent_context.json` from the passing boot/trap verification flow.

## v0.0.3 - 2026-03-13

- Added ABI-backed protocol alignment between the Odin kernel dispatcher and the Rust core service heartbeat request path.
- Added semantic harness validation for protocol alignment so missing syscall cases or missing Rust syscall usage fail closed.
- Extended the ABI with `k_heartbeat_payload_t` and projected the struct deterministically into Odin and Rust bindings.
- Added full layout parity validation for the heartbeat payload, covering size, alignment, and field offsets across the generated projections.
- Updated the kernel heartbeat path to populate and log the structured payload, and updated the Rust service to initialize and pass the same typed payload.
- Verified the current state with `python3 scripts/gen_abi.py`, `odin check kernel/`, `cargo check --manifest-path userspace/core_service/Cargo.toml --target x86_64-unknown-none`, `./scripts/verify.sh`, and `./scripts/agent_context.sh`.

## v0.0.2 - 2026-03-12

- Completed the harness bootstrap and aligned the verify/control-plane loop with active task packets.
- Added the first Odin kernel heartbeat slice in `kernel/main.odin`, `kernel/arch/x86_64/serial.odin`, and `kernel/arch/x86_64/arch.odin`.
- Established KOZO ABI V1 in `contracts/kozo_abi.h` with deterministic generated bindings for Odin and Rust.
- Added `scripts/gen_abi.py` and checked in generated projections under `bindings/odin/` and `bindings/rust/`.
- Integrated the generated ABI into the Odin kernel heartbeat path and a `no_std` Rust service scaffold at `userspace/core_service/`.
- Added ABI sync validation so `verify.sh` fails closed if checked-in bindings drift from the normative header.
- Verified the current state with `odin check kernel/`, `cargo check --manifest-path userspace/core_service/Cargo.toml --target x86_64-unknown-none`, `./scripts/verify.sh`, and `./scripts/agent_context.sh`.

## v0.0.1 - 2026-03-11

- Bootstrap the minimum KOZO harness and control-plane loop.
- Add canonical registry-ordered validators and schema-backed artifacts.
- Add `verify.sh` and `agent_context.sh` to generate the first working verification outputs.
- Harden `aggregator.py` and `summarize.py` so verification runs in canonical order and agent context resolves the next required commands.
