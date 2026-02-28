---
title: KOZO OS Application Architecture Specification
version: 0.0.1-dev
status: PRE-ALPHA
date: 2026-03-01
scope: User Application Stack & Service Architecture
kernel: Zig (Microkernel)
user-space: Rust (Services) + Linux Compatibility (Binaries)
---

# KOZO: OS Application Specification & Service Mapping

## 1. Architectural Alignment
This specification defines how the **KOZO** capability-microkernel architecture maps to user-facing applications. It establishes a three-layer hierarchy:

* **Layer 0 (Zig Kernel):** Fundamental capability enforcement, IPC, and scheduling primitives.
* **Layer 1 (Rust Services):** Drivers, filesystems, network stack, and the **Linux Compatibility Shim**.
* **Layer 2 (Linux Binaries):** Unmodified applications (e.g., Firefox, COSMIC) running in restricted environments.

**Core Principle:** Users interact with "Clear-Name" descriptive permissions. Under the hood, these are translated into granular kernel capabilities enforced by the Zig TCB.

---

## 2. The Service & Capability Model

Applications operate via Rust system services that hold specific kernel capabilities on their behalf.

| User-Facing App | Rust Service (Layer 1) | Kernel Capability | Primary Role |
| :--- | :--- | :--- | :--- |
| **Settings** | Settings Service | `system.configure` | Hardware/User configuration via IPC |
| **Files** | Filesystem Service | `storage.manage` | VFS implementation & CNode scoping |
| **Browser** | Network/Graphics | `network.outbound` | Mediated internet/GPU access |
| **Terminal** | Shell Service | `process.spawn` | PTY management & isolation |
| **All Apps** | Linux Shim | `compat.execute` | Syscall translation & sandboxing |

---

## 3. Application Tiers

### Tier 1: System Foundation (Privileged)
*Critical system tools that communicate directly with Rust services.*

#### Settings & Software
* **Implementation:** COSMIC Settings / Custom Rust GUI.
* **Key Capabilities:** `wifi.configure`, `users.manage`, `software.install`.
* **Security Flow:** App Request → Linux Shim → Settings Service (Validation) → Zig Kernel (Authorization) → Driver.

#### Recovery & Disk Utility
* **Capability:** `disk.repair`, `system.restore`.
* **Requirement:** Physical presence confirmation (Hardware-level "Safety Button" or MFA).

### Tier 2: Daily Productivity (Sandboxed)
*Standard apps running via the Linux Compatibility Shim.*

#### Browser (Firefox + Arkenfox)
* **Capabilities:** `network.outbound`, `files.downloads.write`, `camera.use` (per-site prompt).
* **Privacy Model:** Routed through the Rust Network Service; no LAN access by default.

#### Text Editor & Documents
* **Capabilities:** `files.documents.read/write`.
* **Isolation:** The app sees a standard Linux FS; the Shim translates this to capability-checked object accesses.

### Tier 5: Power Tools
#### Terminal (Ghostty + Zsh)
* **Capability:** `shell.access`, `admin.elevate`.
* **Elevation UX:** Intercepts `sudo`. The Shell Service requests a temporary, narrow capability delegation (e.g., `files.etc.write`) rather than a global UID 0.

---

## 4. Capability Delegation Flow
1.  **Intent:** User clicks "Save File" in a Linux binary.
2.  **Intercept:** Linux Shim catches the `write()` syscall.
3.  **Translation:** Shim converts request to KOZO IPC: `files.home.write`.
4.  **Validation:** Rust Filesystem Service checks if the app's CNode contains the required capability handle.
5.  **Enforcement:** Zig Kernel verifies the token's validity/expiry.
6.  **Audit:** Action is logged to an immutable, append-only kernel audit buffer.

---

## 5. Security & Isolation Matrix

| Threat | KOZO Mitigation Strategy |
| :--- | :--- |
| **Browser Exploit** | No `process.spawn` capability; Network Service can sever `network.outbound` instantly. |
| **Malicious Plugin** | Services validate all config changes against a strict policy schema before kernel execution. |
| **Terminal Escape** | Shell Service monitors all child PIDs; elevation is per-command, not persistent. |
| **Keylogger** | Apps lack `input.capture` unless explicitly granted (per-window focus logic). |

---

## 6. Implementation Verification
* **Human-Readable Audit:** `kozo-cap list` shows "Clear-Name" permissions, not raw hex.
* **Boundary Test:** Unauthorized access to `/etc/passwd` triggers a Shim-level block and user notification.
* **Resiliency:** Killing a Rust service (e.g., Graphics) results in a graceful service restart without a Kernel Panic.
