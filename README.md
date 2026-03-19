<p align="center">
  <a href="https://kozo.page"><img src="kozo-logo.svg" width="240" alt="KOZO: Made Simple, Designed Secure."></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Built_with-Odin-3882D2?style=for-the-badge&logo=odin&logoColor=white" />
  <img src="https://img.shields.io/badge/Built_with-Rust-B7410E?style=for-the-badge&logo=rust&logoColor=white" />
  <img src="https://img.shields.io/badge/Platform-KOZO_Native-000000?style=for-the-badge&logo=linux&logoColor=white" />
  <img src="https://img.shields.io/badge/License-FOSS-000000?style=for-the-badge&logo=opensourceinitiative&logoColor=white" />
  <img src="https://img.shields.io/badge/Architectures-x86__64%20%7C%20ARM64-000000?style=for-the-badge" />
</p>

---

**KOZO** is a new kind of operating system—purpose‑built for people who want their computers to feel fast, private, and trustworthy. By pairing the precision of Zig with the safety of Rust, it creates an environment that’s secure from the moment you turn it on, without slowing you down or locking you into a walled garden.

Instead of patching over decades of legacy design, KOZO starts fresh. Its microkernel foundation is clean, modern, and engineered for today’s hardware and expectations, giving you a system that feels lighter, safer, and more dependable from the inside out.

---

Current Status: “KOZO executes a function-call trap path: Rust extern call → asm bridge → Odin dispatcher. This is not a hardware `syscall`/interrupt path and does not perform a privilege transition.”
The current tree exercises the assembly bridge boundary in source and verification, while the kernel bootstrap self-check remains a direct internal dispatcher call.

### Verification Artifacts

Artifacts in `/artifacts` are:
- Reproducible outputs of `scripts/verify.sh`
- NOT authoritative unless `verify.sh` passes on the current tree

Current Status:
- Harness: Active
- Kernel Build: PASS
- Syscall Path: ASM BRIDGE
