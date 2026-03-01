//! KOZO Policy Service - Delegation & Mechanism
//! File Path: services/policy/src/delegation.rs
//! Responsibility: Execute mechanical transfer of capabilities from system pool to apps
//! Security: This is the ONLY module in Policy Service that directly manipulates
//!           kernel capabilities via syscalls. All transfers are logged and audited.

use crate::auth::AppID;
use crate::ui::{RiskLevel, assess_risk};
use kozo_sys::{syscall, Syscall, CapType, Rights, Error};

/// System capability slot assignments (Policy Service's own CNode)
/// These are the "master" capabilities that Policy Service can delegate.
const SYSTEM_CAMERA_CAP: usize = 10;
const SYSTEM_NET_OUTBOUND_CAP: usize = 11;
const SYSTEM_NET_LOCAL_CAP: usize = 12;
const SYSTEM_FS_HOME_CAP: usize = 20;
const SYSTEM_FS_SYSTEM_CAP: usize = 21;
const SYSTEM_PROCESS_SPAWN_CAP: usize = 30;
const SYSTEM_PROCESS_SIGNAL_CAP: usize = 31;
const SYSTEM_AUDIO_OUT_CAP: usize = 40;
const SYSTEM_AUDIO_IN_CAP: usize = 41;
const SYSTEM_GPU_RENDER_CAP: usize = 50;

/// Standard destination slot in app CNodes for delegated capabilities
/// Apps expect to find their granted caps at this location
const APP_DELEGATION_SLOT: usize = 5;

/// Delegate capability from system pool to target application
/// 
/// # Process
/// 1. Resolve Clear-Name to system capability handle
/// 2. Attenuate rights based on capability type and risk
/// 3. Find or allocate slot in app's CNode
/// 4. Execute kernel transfer
/// 5. Verify transfer succeeded
/// 
/// # Safety
/// Policy Service must hold GRANT right on source capability
/// (enforced by kernel in sys_cap_transfer)
pub fn delegate_capability(app_id: AppID, cap_name: &str) -> Result<(), Error> {
    // 1. Resolve Clear-Name to system capability handle
    let src_handle = resolve_system_capability(cap_name)?;
    
    // 2. Determine appropriate rights attenuation
    let rights = calculate_attenuated_rights(cap_name);
    
    // 3. Identify target CNode (app_id is the badge/CNode identifier)
    let dest_cnode = app_id.0 as usize;
    
    // 4. For path-scoped capabilities (files), mint restricted child first
    let transfer_handle = if is_path_scoped(cap_name) {
        mint_path_restricted(src_handle, cap_name, rights)?
    } else {
        src_handle
    };
    
    // 5. Execute kernel transfer
    let result = unsafe {
        syscall::syscall4(
            Syscall::CapTransfer as usize,
            transfer_handle,
            dest_cnode,
            APP_DELEGATION_SLOT,
            rights.bits() as usize,
        )
    };
    
    if result < 0 {
        return Err(Error::from_raw(result));
    }
    
    // 6. Log successful delegation
    log_delegation(app_id, cap_name, rights);
    
    Ok(())
}

/// Revoke capability from application
/// 
/// Immediately invalidates the capability in the app's CNode.
/// App will receive errors on next use attempt.
pub fn revoke_capability(app_id: AppID, cap_name: &str) -> Result<(), Error> {
    let dest_cnode = app_id.0 as usize;
    
    // Revoke at the delegation slot
    let result = unsafe {
        syscall::syscall2(
            Syscall::CapRevoke as usize,
            dest_cnode,
            APP_DELEGATION_SLOT,
        )
    };
    
    if result < 0 {
        // Might already be revoked, which is fine
        if result != -2 { // Not NoCap error
            return Err(Error::from_raw(result));
        }
    }
    
    log_revocation(app_id, cap_name);
    Ok(())
}

/// Mint path-restricted child capability
/// 
/// For filesystem capabilities, we create a derived capability
/// restricted to specific paths (e.g., /home/user/Documents).
fn mint_path_restricted(parent: usize, cap_name: &str, rights: Rights) -> Result<usize, Error> {
    // Extract path from cap_name (e.g., "files.home.read" -> /home/user)
    let _path = extract_path(cap_name);
    
    // Mint child with same rights but path constraint
    // Path constraint stored in kernel capability metadata
    let result = unsafe {
        syscall::syscall3(
            Syscall::CapMint as usize,
            parent,
            rights.bits() as usize,
            0, // path descriptor (would be pointer in production)
        )
    };
    
    if result < 0 {
        Err(Error::from_raw(result))
    } else {
        Ok(result as usize) // New capability slot in Policy Service CNode
    }
}

/// Resolve Clear-Name to system capability handle
fn resolve_system_capability(cap_name: &str) -> Result<usize, Error> {
    match cap_name {
        // Camera/Media
        "camera.use" => Ok(SYSTEM_CAMERA_CAP),
        "camera.record" => Ok(SYSTEM_CAMERA_CAP),
        
        // Network
        "network.outbound" => Ok(SYSTEM_NET_OUTBOUND_CAP),
        "network.local" => Ok(SYSTEM_NET_LOCAL_CAP),
        "network.inbound" => Err(Error::AccessDenied), // Policy: no inbound by default
        
        // Filesystem
        "files.home.read" => Ok(SYSTEM_FS_HOME_CAP),
        "files.home.write" => Ok(SYSTEM_FS_HOME_CAP),
        "files.system.read" => Ok(SYSTEM_FS_SYSTEM_CAP),
        "files.system.write" => Err(Error::AccessDenied), // Critical operation
        
        // Process
        "process.spawn" => Ok(SYSTEM_PROCESS_SPAWN_CAP),
        "process.signal" => Ok(SYSTEM_PROCESS_SIGNAL_CAP),
        
        // Audio
        "audio.out" => Ok(SYSTEM_AUDIO_OUT_CAP),
        "audio.in" => Ok(SYSTEM_AUDIO_IN_CAP),
        
        // Graphics
        "graphics.render" => Ok(SYSTEM_GPU_RENDER_CAP),
        "gpu.compute" => Ok(SYSTEM_GPU_RENDER_CAP),
        
        // Unknown
        _ => Err(Error::Invalid),
    }
}

/// Calculate attenuated rights based on Clear-Name
/// 
/// Even if we have GRANT right, we never delegate full rights.
/// Principle of Least Privilege: apps get minimum necessary.
fn calculate_attenuated_rights(cap_name: &str) -> Rights {
    let base = Rights::RIGHT_READ;
    
    if cap_name.contains(".write") || cap_name.contains(".use") {
        base | Rights::RIGHT_WRITE
    } else if cap_name.contains(".grant") {
        // Rarely grant GRANT right (allows further delegation)
        base | Rights::RIGHT_WRITE | Rights::RIGHT_GRANT
    } else if cap_name.contains(".map") {
        base | Rights::RIGHT_MAP
    } else {
        base
    }
}

/// Check if capability requires path-based restriction
fn is_path_scoped(cap_name: &str) -> bool {
    cap_name.starts_with("files.")
}

/// Extract filesystem path from Clear-Name
fn extract_path(cap_name: &str) -> &'static str {
    if cap_name.contains("home") {
        "/home/user"
    } else if cap_name.contains("system") {
        "/etc"
    } else if cap_name.contains("temp") {
        "/tmp"
    } else {
        "/"
    }
}

// === Audit Logging ===

fn log_delegation(app_id: AppID, cap_name: &str, rights: Rights) {
    kozo_sys::debug_print("[POLICY] Delegated ");
    kozo_sys::debug_print(cap_name);
    kozo_sys::debug_print(" to app ");
    kozo_sys::debug_print_hex(app_id.raw());
    kozo_sys::debug_print(" with rights ");
    kozo_sys::debug_print_hex(rights.bits());
    kozo_sys::debug_print("\n");
}

fn log_revocation(app_id: AppID, cap_name: &str) {
    kozo_sys::debug_print("[POLICY] Revoked ");
    kozo_sys::debug_print(cap_name);
    kozo_sys::debug_print(" from app ");
    kozo_sys::debug_print_hex(app_id.raw());
    kozo_sys::debug_print("\n");
}

// === kozo-sys interface ===

mod kozo_sys {
    pub use crate::{Error, Rights};
    
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
            let c = HEX[digit as usize] as usize;
            unsafe {
                core::arch::asm!(
                    "syscall",
                    in("rax") 99,
                    in("rdi") c,
                    options(nostack, preserves_flags)
                );
            }
        }
    }
}

impl Rights {
    pub fn bits(&self) -> u64 {
        *self as u64
    }
}

impl Error {
    pub fn from_raw(v: isize) -> Self {
        match v {
            -1 => Error::Invalid,
            -2 => Error::NoCap,
            -3 => Error::NoMem,
            -4 => Error::AccessDenied,
            _ => Error::Invalid,
        }
    }
}