# Changelog

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
