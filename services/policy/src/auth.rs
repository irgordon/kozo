//! KOZO Policy Service - Authentication Module
//! File Path: services/policy/src/auth.rs
//! Responsibility: Verify sender identity via unforgeable kernel badges (Anti-spoofing)
//! Depends on: services/kozo-sys/src/lib.rs (syscall interface)

use kozo_sys::{syscall, Syscall, Error};

/// AppID represents a unique, unforgeable application identity.
/// 
/// The underlying u64 is the "badge" - a kernel-generated unforgeable token
/// that identifies the sender's CNode (capability root). This prevents 
/// applications from claiming false identities.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct AppID(pub u64);

impl AppID {
    /// Extract AppID from kernel-provided badge.
    /// 
    /// The badge is stamped on every IPC message by the Zig kernel (Layer 0)
    /// based on the sender's CNode root address. It cannot be forged by
    /// user-space because capability addresses are kernel-controlled.
    pub fn from_badge(badge: u64) -> Self {
        AppID(badge)
    }

    /// Verify this AppID matches the kernel's records for the calling thread.
    /// 
    /// # Defense in Depth
    /// Even though the badge comes from the kernel on IPC, we double-check
    /// against the thread capability to ensure the sender hasn't been 
    /// revoked or the capability hasn't been delegated unexpectedly.
    /// 
    /// # Safety
    /// This performs a syscall to the kernel (Layer 0) which validates
    /// the badge against its internal capability tables.
    pub fn verify(&self, thread_cap: usize) -> Result<(), Error> {
        unsafe {
            let res = syscall::do_syscall(
                Syscall::CapVerify as usize,
                self.0 as usize,      // The badge (claimed AppID)
                thread_cap,            // The thread capability to verify against
                0, 
                0
            );
            
            if res == 0 { 
                Ok(()) 
            } else { 
                Err(Error::AccessDenied) 
            }
        }
    }
    
    /// Get raw badge value (for logging, display)
    pub fn raw(&self) -> u64 {
        self.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_appid_from_badge() {
        let app_id = AppID::from_badge(0xDEADBEEF);
        assert_eq!(app_id.raw(), 0xDEADBEEF);
    }
}