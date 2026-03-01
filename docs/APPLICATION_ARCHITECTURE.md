---
title: KOZO OS Application Architecture Specification
version: 0.0.1-dev
status: PRE-ALPHA
date: 2026-03-01
scope: User Application Stack & Service Architecture
kernel: Zig (Microkernel)
user-space: Rust (Services) + Linux Compatibility (Binaries)
---

# KOZO: OS Clear-Name Application Specification

## 1. Architectural Alignment

This specification maps the KOZO capability-microkernel architecture to concrete user-facing applications. It bridges:
- **Layer 0 (Zig Kernel)**: Capability enforcement, IPC, scheduling
- **Layer 1 (Rust Services)**: Drivers, filesystems, network stack, Linux compatibility shim
- **Layer 2 (Linux Binaries)**: Unmodified open-source applications (Firefox, COSMIC, etc.)

**Core Principle**: Users interact with clear, descriptive applications. Underneath, these run as sandboxed Linux binaries mediated by Rust services, enforced by the Zig kernel capability model.

---

## 2. The Service Model

Each application category runs atop specific Rust system services that hold capabilities on their behalf:

| User Sees | Rust Service (Layer 1) | Kernel Capability | Role |
|-----------|----------------------|-------------------|------|
| **Settings** | Settings Service | `system.configure` | Manages hardware configuration via privileged IPC to drivers |
| **Files** | Filesystem Service | `storage.manage` | VFS implementation, directory capabilities |
| **Browser** | Network Service + Graphics Service | `network.outbound`, `graphics.render` | Mediates internet and GPU access |
| **Terminal** | Shell Service | `process.spawn`, `terminal.pty` | PTY management, process isolation |
| All Apps | Linux Compatibility Shim | `compat.execute` | Syscall translation, sandbox enforcement |

---

## 3. Application Tiers & Specifications

### Tier 1 — System Foundation
*These manage the computer itself. They communicate directly with Rust system services and require explicit user consent for privileged operations.*

#### Settings
**Purpose**: Configure network, display, users, and security  
**Implementation**: COSMIC Settings (unmodified Linux binary)  
**Service Backend**: Settings Service (Rust)  
**Clear-name Capabilities**:
- `wifi.configure` → Connect to wireless networks
- `display.adjust` → Change resolution, brightness, orientation  
- `users.manage` → Add, remove, or modify user accounts
- `software.sources` → Configure system update sources

**Security Flow**: When adjusting network settings, Settings app → Linux shim → Settings Service validates `wifi.configure` capability → Zig kernel authorizes → Change applied via Network Driver (Rust).

#### Files
**Purpose**: Browse and organize documents  
**Implementation**: COSMIC Files (unmodified)  
**Service Backend**: Filesystem Service (Rust) + VFS drivers  
**Clear-name Capabilities**:
- `files.home.read` → Access Home directory
- `files.home.write` → Modify files in Home
- `files.system.read` (scoped) → Access specific system directories for configuration

**Isolation**: Each file operation passes through the capability-checked VFS. The app sees a standard Linux filesystem; the kernel sees capability-validated object accesses.

#### Software (App Store)
**Purpose**: Install, update, and remove applications safely  
**Implementation**: Custom Rust GUI + PackageKit compatibility  
**Service Backend**: Package Manager Service (Rust)  
**Clear-name Capabilities**:
- `software.install` → Add new applications to system
- `software.verify` → Validate cryptographic signatures
- `system.rollback` → Restore previous system state

**Atomic Updates**: The Package Manager Service uses Zig kernel's untyped memory objects to create atomic system snapshots before installation, enabling one-click rollback via Recovery.

#### Recovery
**Purpose**: Repair disks, restore factory settings, recover data  
**Implementation**: COSMIC Disk Utility + custom Rust recovery tools  
**Service Backend**: Recovery Service (Rust)  
**Clear-name Capabilities**:
- `disk.repair` → Fix filesystem errors
- `system.restore` → Factory reset with user confirmation
- `backup.access` → Read system backup images

**Safety**: Recovery operations require physical presence confirmation (button press) or multi-factor authentication to prevent remote exploitation.

---

### Tier 2 — Daily Productivity
*Standard user applications running in capability sandboxes. They believe they are on Linux; the Compatibility Shim enforces restrictions.*

#### Browser
**Purpose**: Access the internet securely  
**Implementation**: Mozilla Firefox (unmodified binary) + Arkenfox user.js  
**Service Backend**: Network Service + Graphics Service + Audio Service  
**Clear-name Capabilities**:
- `network.outbound` → Access the internet (no LAN access by default)
- `files.downloads.write` → Save to Downloads folder only
- `camera.use` → Access webcam (per-site prompt)
- `microphone.use` → Access microphone (per-site prompt)
- `graphics.accelerate` → Hardware video decoding

**Privacy Model**: Arkenfox hardening applied system-wide. The browser runs in a sandbox that cannot access files outside Downloads, cannot see other processes, and all network traffic is routed through the Rust Network Service (enabling system-wide VPN/DoH).

#### Text Editor
**Purpose**: Write and edit documents  
**Implementation**: COSMIC Text Editor or Helix (GUI wrapper)  
**Clear-name Capabilities**:
- `files.documents.write` → Edit text files in user directories
- `scripts.execute` (optional) → Run scripts being edited (explicit grant per file)

#### Documents
**Purpose**: View PDFs and office files  
**Implementation**: Evince (Document Viewer)  
**Clear-name Capabilities**:
- `files.documents.read` → Read-only access to documents
- `print.submit` → Send jobs to print service (optional)

#### Calculator
**Purpose**: Mathematical calculations  
**Implementation**: GNOME Calculator or COSMIC Calculator  
**Clear-name Capabilities**: None (runs fully isolated, no filesystem access unless saving history explicitly)

---

### Tier 3 — Media & Entertainment

#### Images
**Purpose**: View photos and screenshots  
**Implementation**: Eye of GNOME / COSMIC Image Viewer  
**Clear-name Capabilities**: `files.photos.read`, `graphics.view`

#### Music
**Purpose**: Audio playback  
**Implementation**: Rhythmbox / COSMIC Music  
**Service Backend**: Audio Service (Rust) + PipeWire compatibility  
**Clear-name Capabilities**: `audio.play`, `files.music.read`

**Mediation**: Audio Service holds the hardware capability; apps receive session handles. Apps cannot access raw audio devices directly.

#### Video
**Purpose**: Video playback  
**Implementation**: VLC (restricted) or COSMIC Video  
**Service Backend**: Video Service (Rust) + hardware decoders  
**Clear-name Capabilities**: `video.play`, `files.videos.read`, `hardware.video.decode`

---

### Tier 5 — Power Tools

#### Terminal
**Purpose**: Command-line interface  
**Implementation**: Ghostty (terminal emulator) + Zsh (shell)  
**Service Backend**: Shell Service + PTY Service  
**Clear-name Capabilities**:
- `shell.access` → Open terminal interface
- `files.user.manage` → Full user directory access
- `admin.elevate` → Request administrator privileges (per-command basis)

**Elevation UX**: When typing `sudo`, the user sees:  
*"Terminal requests administrator access to edit system files"*  
Not: *"Authentication required for uid 0"*

The Shell Service intercepts the elevation request, validates against Policy Service, and temporarily delegates the specific capability needed (e.g., `files.etc.write` for editing config files), not blanket root access.

#### System Monitor
**Purpose**: View and manage running programs  
**Implementation**: btop (beautified system monitor)  
**Clear-name Capabilities**:
- `processes.view` → See all running processes
- `processes.stop` → Terminate specific applications (per-process grant)

---

## 4. Capability Delegation Flow

The path from user action to kernel enforcement:

1. **User Action**: Clicks "Connect to WiFi" in Settings
2. **App Request**: Settings app (Linux binary) calls `ioctl()` on network interface
3. **Shim Intercept**: Linux Compatibility Shim (Rust) catches syscall, translates to KOZO IPC: `wifi.configure` request
4. **Service Validation**: Settings Service (Rust) checks if app holds `wifi.configure` capability handle
5. **Kernel Enforcement**: Zig kernel verifies capability token is valid and unexpired
6. **Execution**: Settings Service forwards to Network Driver (Rust), which configures hardware
7. **Audit**: Zig kernel logs capability use to immutable audit log

---

## 5. Installation & Lifecycle

### Factory Image (Pre-installed)
All Tier 1 and Tier 2 applications ship in the base image with default capability profiles:
- **Settings**: `system.configure` (user-scoped), `software.sources`
- **Browser**: `network.outbound`, `files.downloads`, `graphics.accelerate`
- **Terminal**: `shell.access`, `files.user.manage`

### User Installation (via Software)
When installing new apps (e.g., installing GIMP via Software):
1. Package Manager downloads Linux binary to sandboxed store
2. User grants initial capabilities via clear-name prompts:
   - "Allow GIMP to access your Pictures folder? [Allow] [Deny]"
3. Package Manager registers app with Service Manager, issuing attenuated capability handles
4. App launches via Compatibility Shim with restricted capability set

### Updates
- **System**: Atomic updates via Package Manager Service, rollback capability always maintained
- **Apps**: Standard Linux app updates (Firefox auto-update disabled in favor of system-managed updates for consistency)

---

## 6. Security Guarantees

| Threat | Mitigation |
|--------|------------|
| **Firefox exploit** | Sandbox prevents access to files outside Downloads; no `process.spawn` capability prevents malware execution; Network Service can cut off `network.outbound` instantly |
| **Malicious Settings plugin** | Settings Service validates all configuration changes against policy schema; Zig kernel enforces capability boundaries even if Settings app is compromised |
| **Terminal escape** | Shell Service monitors all spawned processes; `admin.elevate` requires explicit user confirmation per command, not persistent root |
| **Keylogger in btop** | System Monitor has `processes.view` but no `input.capture` or `network.outbound`; cannot exfiltrate data |

---

## 7. Clarity Requirements (User Interface)

All user-facing elements must pass the "Clarity Test":

**Capability Prompts**:
- ❌ "Grant cap-fs-home-rw?"
- ✅ "Allow Text Editor to save files in your Home folder?"

**Application Names**:
- ❌ "cosmic-settings"
- ✅ "Settings"

**Function Descriptions**:
- ❌ "Execute privileged syscall"
- ✅ "Install system updates"

---

## 8. Implementation Verification

To verify this specification is correctly implemented:

1. **Capability Audit**: Run `kozo-cap list` in Terminal → shows human-readable capabilities like `wifi.configure`, not hex codes
2. **Sandbox Test**: Browser attempt to access `/etc/passwd` → denied by shim, user sees "Browser tried to access system files (blocked)"
3. **Service Isolation**: Kill Settings Service process → Settings app freezes but system remains stable; service restarts automatically with same capability set
4. **Linux Compatibility**: Run `htop` (unmodified) → sees processes but cannot kill them without `processes.stop` grant confirmed via UI dialog

---

## 9. Summary

KOZO OS delivers a modern capability-security microkernel (Zig) running standard Linux applications (Firefox, COSMIC, btop, Ghostty) mediated by Rust system services. Users interact with clear, descriptive applications while the underlying architecture enforces strict least-privilege isolation—each app receives only the specific permissions it needs, described in plain English, enforced by the kernel, and revocable at any time.

**No application runs with ambient authority. Every permission is explicit, auditable, and human-readable.**