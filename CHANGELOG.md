# Changelog

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
