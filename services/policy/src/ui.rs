//! KOZO Policy Service - User Interface (Clear-Name Prompts)
//! File Path: services/policy/src/ui.rs
//! Responsibility: Translate technical capabilities into human-readable,
//!                 un-hijackable security prompts via Compositor Service
//! Security: Policy Service DECIDES to prompt; Compositor Service RENDERS it
//!           (separation prevents UI spoofing by compromised Policy Service)

use crate::auth::AppID;
use kozo_sys::{syscall, Syscall, Error};

/// Risk assessment levels determine prompt severity and timeout defaults
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RiskLevel {
    /// Low risk: File reading, non-sensitive operations
    /// Default: 1 hour duration, single-click approval
    Low,
    /// Medium risk: Network access, external communication
    /// Default: 5 minute JIT, explicit approval required
    Medium,
    /// High risk: Camera, microphone, location access
    /// Default: 1 minute JIT, persistent notification shown
    High,
    /// Critical risk: System configuration, disk modification, admin elevation
    /// Requires: Hardware presence proof (YubiKey, chassis button, secure enclave)
    Critical,
}

impl RiskLevel {
    /// Get default JIT duration in seconds for this risk level
    pub fn default_duration(&self) -> u64 {
        match self {
            RiskLevel::Low => 3600,      // 1 hour
            RiskLevel::Medium => 300,    // 5 minutes
            RiskLevel::High => 60,       // 1 minute
            RiskLevel::Critical => 0,    // One-time use only
        }
    }

    /// Get human-readable description of risk
    pub fn description(&self) -> &'static str {
        match self {
            RiskLevel::Low => "Low risk - Read-only or confined operation",
            RiskLevel::Medium => "Medium risk - Network or external communication",
            RiskLevel::High => "High risk - Privacy-sensitive hardware access",
            RiskLevel::Critical => "CRITICAL - System modification or admin access",
        }
    }
}

/// Assess risk level from Clear-Name capability string
/// 
/// This mapping defines the security posture for each capability type.
/// Policy administrators can customize this without changing kernel code.
pub fn assess_risk(cap_name: &str) -> RiskLevel {
    // System-critical capabilities
    if cap_name.starts_with("system.") 
        || cap_name.starts_with("disk.")
        || cap_name.starts_with("admin.")
        || cap_name.contains("restore")
        || cap_name.contains("configure") {
        return RiskLevel::Critical;
    }
    
    // Privacy-sensitive hardware
    if cap_name.starts_with("camera.")
        || cap_name.starts_with("microphone.")
        || cap_name.starts_with("location.")
        || cap_name.starts_with("biometric.") {
        return RiskLevel::High;
    }
    
    // Network access (external only)
    if cap_name.starts_with("network.") {
        // Distinguish external vs local network
        if cap_name.contains("local") || cap_name.contains("lan") {
            return RiskLevel::High; // Local network is sensitive
        }
        return RiskLevel::Medium;
    }
    
    // File system access
    if cap_name.starts_with("files.") {
        if cap_name.contains("system") || cap_name.contains("etc") {
            return RiskLevel::High;
        }
        if cap_name.contains("home") || cap_name.contains("documents") {
            return RiskLevel::Medium;
        }
        if cap_name.contains("download") || cap_name.contains("temp") {
            return RiskLevel::Low;
        }
        return RiskLevel::Medium;
    }
    
    // Process management
    if cap_name.starts_with("process.") {
        if cap_name.contains("kill") || cap_name.contains("debug") {
            return RiskLevel::High;
        }
        return RiskLevel::Medium;
    }
    
    // Graphics/GPU (can be used for side-channel attacks)
    if cap_name.starts_with("graphics.") || cap_name.starts_with("gpu.") {
        return RiskLevel::Medium;
    }
    
    // Audio output (lower risk than input)
    if cap_name.starts_with("audio.out") {
        return RiskLevel::Low;
    }
    if cap_name.starts_with("audio.in") {
        return RiskLevel::High;
    }
    
    // Default for unknown capabilities
    RiskLevel::Medium
}

/// Context information for the user about why this capability is requested
pub struct PromptContext {
    /// Which application is requesting (human-readable name)
    pub app_name: &'static str,
    /// What specific action the app is trying to perform
    pub action_description: &'static str,
    /// URL or context if applicable (e.g., website requesting camera)
    pub context: Option<&'static str>,
}

/// Trigger secure, un-hijackable prompt via Compositor Service
/// 
/// # Security Architecture
/// 1. Policy Service (this code) DECIDES to show prompt and WHAT to ask
/// 2. Sends IPC to Compositor Service with prompt data
/// 3. Compositor renders in "secure chrome" - hardware-backed overlay
///    that user applications cannot spoof or overlay
/// 4. User input captured by kernel input driver, bypassing user-space
/// 5. Result returned to Policy Service
/// 
/// # Genesis Block
/// For smoke testing, this prints to serial and auto-approves.
/// Production implementation IPCs to Compositor Service.
pub fn trigger_secure_prompt(
    app_id: AppID, 
    cap_name: &str, 
    risk: RiskLevel,
    context: Option<PromptContext>,
) -> bool {
    // GENESIS BLOCK: Simplified console output
    // Production: IPC to Compositor Service with secure rendering
    
    kozo_sys::debug_print("\n");
    kozo_sys::debug_print("╔══════════════════════════════════════════════════════════════╗\n");
    kozo_sys::debug_print("║              KOZO SECURITY PROMPT                            ║\n");
    kozo_sys::debug_print("╠══════════════════════════════════════════════════════════════╣\n");
    kozo_sys::debug_print("║  Application: ");
    if let Some(ctx) = &context {
        kozo_sys::debug_print(ctx.app_name);
    } else {
        kozo_sys::debug_print("Unknown App (");
        kozo_sys::debug_print_hex(app_id.raw());
        kozo_sys::debug_print(")");
    }
    kozo_sys::debug_print("\n");
    
    kozo_sys::debug_print("║                                                              ║\n");
    kozo_sys::debug_print("║  Requesting: ");
    kozo_sys::debug_print(cap_name);
    kozo_sys::debug_print("\n");
    
    kozo_sys::debug_print("║  Risk Level: ");
    kozo_sys::debug_print(risk.description());
    kozo_sys::debug_print("\n");
    
    if let Some(ctx) = &context {
        kozo_sys::debug_print("║  Context:    ");
        kozo_sys::debug_print(ctx.action_description);
        kozo_sys::debug_print("\n");
    }
    
    kozo_sys::debug_print("║                                                              ║\n");
    kozo_sys::debug_print("╚══════════════════════════════════════════════════════════════╝\n");
    
    // For genesis smoke test: auto-approve after delay
    // Production: Block here waiting for compositor IPC response
    match risk {
        RiskLevel::Critical => {
            kozo_sys::debug_print("[CRITICAL: Requires hardware presence - auto-approving for genesis test]\n");
            true
        }
        _ => {
            kozo_sys::debug_print("[Auto-approving for genesis smoke test]\n");
            true
        }
    }
}

/// Verify hardware presence for Critical risk operations
/// 
/// # Security
/// This prevents remote attackers from compromising Policy Service
/// and approving critical operations without physical access.
/// 
/// # Implementation
/// - TPM physical presence flag
/// - Chassis intrusion button
/// - YubiKey touch
/// - Secure Enclave biometric
pub fn require_hardware_presence() -> bool {
    kozo_sys::debug_print("[Verifying hardware presence...]\n");
    
    // GENESIS: Simulated success
    // Production: Syscall to kernel to check TPM/Secure Enclave
    
    unsafe {
        // Query kernel for hardware presence attestation
        let result = syscall::syscall1(
            Syscall::HardwareAttest as usize, // Would need to add to ABI
            0, // flags
        );
        
        // Genesis: always succeed for smoke test
        _ = result;
        true
    }
}

/// Format duration for human readability
pub fn format_duration(seconds: u64) -> &'static str {
    if seconds == 0 {
        "one-time use"
    } else if seconds < 60 {
        "briefly"
    } else if seconds < 300 {
        "for a few minutes"
    } else if seconds < 3600 {
        "for a while"
    } else {
        "for an extended period"
    }
}

// === kozo-sys stubs for no_std ===
mod kozo_sys {
    pub fn debug_print(s: &str) {
        for c in s.bytes() {
            unsafe {
                core::arch::asm!(
                    "syscall",
                    in("rax") 99, // SYS_DEBUG_PUTCHAR
                    in("rdi") c as usize,
                    options(nostack, preserves_flags)
                );
            }
        }
    }
    
    pub fn debug_print_hex(n: u64) {
        const HEX: &[u8] = b"0123456789ABCDEF";
        for i in (0..64).step_by(4).rev() {
            let digit = (n >> i) & 0xF;
            debug_print(&[(HEX[digit as usize] as char).to_string()]);
        }
    }
    
    pub mod syscall {
        use super::*;
        pub unsafe fn syscall1(n: usize, a0: usize) -> isize {
            let ret: isize;
            core::arch::asm!(
                "syscall",
                in("rax") n,
                in("rdi") a0,
                lateout("rax") ret,
                options(nostack, preserves_flags)
            );
            ret
        }
    }
    
    pub enum Syscall {
        HardwareAttest = 50, // Would need to add to ABI
    }
}