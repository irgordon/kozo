//! KOZO Policy Service - Policy Database
//! File Path: services/policy/src/db.rs
//! Responsibility: Store, query, and audit granted Clear-Name capabilities
//! Note: Genesis Block uses fixed-size arrays (no_std). Production uses SQLite.

use crate::auth::AppID;
use kozo_sys::Error;
use core::time::Duration;

/// Maximum stored grants per AppID (Genesis Block limit)
const MAX_GRANTS_PER_APP: usize = 32;
/// Maximum total applications tracked
const MAX_APPS: usize = 128;

/// Policy entry with expiration (JIT delegation support)
#[derive(Clone, Copy, Debug)]
pub struct Grant {
    /// Clear-Name capability (e.g., "camera.use", "files.home.read")
    pub cap_name: [u8; 32],
    /// Timestamp when granted (kernel ticks)
    pub granted_at: u64,
    /// Expiration timestamp (0 = permanent, >0 = JIT timeout)
    pub expires_at: u64,
    /// Whether this grant is currently active
    pub active: bool,
}

/// Fixed-size database for no_std environment (Genesis Block)
pub struct PolicyDB {
    /// AppID -> Grant array mapping (sparse array)
    apps: [Option<AppEntry>; MAX_APPS],
    /// Current kernel timestamp (updated each query)
    current_time: u64,
    /// Audit log (circular buffer of recent events)
    audit_log: [AuditEvent; 64],
    audit_head: usize, // Next write position
}

#[derive(Clone, Copy, Debug)]
struct AppEntry {
    app_id: AppID,
    grants: [Grant; MAX_GRANTS_PER_APP],
    grant_count: usize,
}

#[derive(Clone, Copy, Debug)]
struct AuditEvent {
    timestamp: u64,
    app_id: AppID,
    action: AuditAction,
    cap_name: [u8; 32],
    success: bool,
}

#[derive(Clone, Copy, Debug)]
pub enum AuditAction {
    Grant,
    Revoke,
    Deny,
    Query,
}

impl PolicyDB {
    /// Initialize empty database
    pub fn new() -> Result<Self, Error> {
        Ok(PolicyDB {
            apps: [None; MAX_APPS],
            current_time: 0,
            audit_log: [AuditEvent {
                timestamp: 0,
                app_id: AppID(0),
                action: AuditAction::Query,
                cap_name: [0; 32],
                success: false,
            }; 64],
            audit_head: 0,
        })
    }

    /// Check if capability is granted and not expired
    /// 
    /// # Arguments
    /// * `app_id` - The application identity
    /// * `cap` - Clear-Name capability string (e.g., "camera.use")
    /// 
    /// # Returns
    /// * `Ok(true)` - Valid grant exists
    /// * `Ok(false)` - Not granted or expired
    /// * `Err` - Database error
    pub fn is_granted(&mut self, app_id: AppID, cap: &str) -> Result<bool, Error> {
        self.update_time();
        self.audit(app_id, AuditAction::Query, cap, true);

        let entry = self.find_app(app_id);
        if entry.is_none() {
            return Ok(false);
        }

        let entry = entry.unwrap();
        let cap_bytes = cap.as_bytes();
        
        for grant in &entry.grants[0..entry.grant_count] {
            if !grant.active {
                continue;
            }
            
            // Check capability name match (prefix match for efficiency)
            if Self::cap_match(&grant.cap_name, cap_bytes) {
                // Check expiration (0 = permanent)
                if grant.expires_at == 0 || self.current_time < grant.expires_at {
                    return Ok(true);
                } else {
                    // Expired - log it
                    self.audit(app_id, AuditAction::Query, cap, false);
                    return Ok(false);
                }
            }
        }

        Ok(false)
    }

    /// Grant capability with optional JIT expiration
    /// 
    /// # Arguments
    /// * `app_id` - Target application
    /// * `cap` - Clear-Name capability
    /// * `duration_secs` - None for permanent, Some for JIT timeout
    pub fn grant(&mut self, app_id: AppID, cap: &str, duration_secs: Option<u64>) -> Result<(), Error> {
        self.update_time();
        
        let expires = match duration_secs {
            None => 0, // Permanent
            Some(secs) => self.current_time.saturating_add(secs * 1000), // Convert to ms
        };

        // Find or create app entry
        let idx = self.find_or_create_app(app_id)?;
        let entry = self.apps[idx].as_mut().unwrap();

        // Check for existing grant (update expiration) or find free slot
        let cap_bytes = cap.as_bytes();
        
        for i in 0..entry.grant_count {
            if Self::cap_match(&entry.grants[i].cap_name, cap_bytes) {
                // Update existing
                entry.grants[i].expires_at = expires;
                entry.grants[i].active = true;
                self.audit(app_id, AuditAction::Grant, cap, true);
                return Ok(());
            }
        }

        // New grant
        if entry.grant_count >= MAX_GRANTS_PER_APP {
            return Err(Error::NoMem); // No space for more grants
        }

        let mut new_grant = Grant {
            cap_name: [0; 32],
            granted_at: self.current_time,
            expires_at: expires,
            active: true,
        };
        
        // Copy capability name (truncate if needed)
        let len = cap_bytes.len().min(31);
        new_grant.cap_name[0..len].copy_from_slice(&cap_bytes[0..len]);
        
        entry.grants[entry.grant_count] = new_grant;
        entry.grant_count += 1;
        
        self.audit(app_id, AuditAction::Grant, cap, true);
        Ok(())
    }

    /// Revoke capability (immediate invalidation)
    pub fn revoke(&mut self, app_id: AppID, cap: &str) -> Result<(), Error> {
        self.update_time();
        
        let Some(idx) = self.find_app_index(app_id) else {
            return Ok(()); // Already gone / never had it
        };
        
        let entry = self.apps[idx].as_mut().unwrap();
        let cap_bytes = cap.as_bytes();
        
        for grant in &mut entry.grants[0..entry.grant_count] {
            if grant.active && Self::cap_match(&grant.cap_name, cap_bytes) {
                grant.active = false;
                self.audit(app_id, AuditAction::Revoke, cap, true);
                return Ok(());
            }
        }
        
        Ok(())
    }

    /// Check if specific grant is expired (for JIT cleanup)
    pub fn is_expired(&mut self, app_id: AppID, cap: &str) -> Result<bool, Error> {
        self.update_time();
        
        let Some(entry) = self.find_app(app_id) else {
            return Ok(true); // No app = expired
        };
        
        let cap_bytes = cap.as_bytes();
        
        for grant in &entry.grants[0..entry.grant_count] {
            if Self::cap_match(&grant.cap_name, cap_bytes) {
                if !grant.active {
                    return Ok(true);
                }
                if grant.expires_at == 0 {
                    return Ok(false); // Permanent
                }
                return Ok(self.current_time >= grant.expires_at);
            }
        }
        
        Ok(true) // Not found = expired
    }

    /// Log a denial for audit trail
    pub fn log_denial(&mut self, app_id: AppID, cap: &str) {
        self.audit(app_id, AuditAction::Deny, cap, false);
    }

    /// Get recent audit log entries (for System Monitor)
    pub fn get_recent_events(&self, count: usize) -> &[AuditEvent] {
        let start = if count > self.audit_log.len() {
            0
        } else {
            self.audit_log.len() - count
        };
        &self.audit_log[start..]
    }

    // === Internal Helpers ===

    fn find_app(&self, app_id: AppID) -> Option<&AppEntry> {
        for entry in &self.apps {
            if let Some(e) = entry {
                if e.app_id.0 == app_id.0 {
                    return Some(e);
                }
            }
        }
        None
    }

    fn find_app_index(&self, app_id: AppID) -> Option<usize> {
        for (i, entry) in self.apps.iter().enumerate() {
            if let Some(e) = entry {
                if e.app_id.0 == app_id.0 {
                    return Some(i);
                }
            }
        }
        None
    }

    fn find_or_create_app(&mut self, app_id: AppID) -> Result<usize, Error> {
        // Find existing
        if let Some(idx) = self.find_app_index(app_id) {
            return Ok(idx);
        }
        
        // Create new
        for (i, slot) in self.apps.iter_mut().enumerate() {
            if slot.is_none() {
                *slot = Some(AppEntry {
                    app_id,
                    grants: [Grant {
                        cap_name: [0; 32],
                        granted_at: 0,
                        expires_at: 0,
                        active: false,
                    }; MAX_GRANTS_PER_APP],
                    grant_count: 0,
                });
                return Ok(i);
            }
        }
        
        Err(Error::NoMem)
    }

    fn cap_match(stored: &[u8; 32], query: &[u8]) -> bool {
        let len = query.len().min(31);
        if stored[len] != 0 && stored[len] != query[0] {
            // Quick reject: stored string continues where query ends
        }
        stored[0..len] == query[0..len] && (stored[len] == 0 || len == 31)
    }

    fn update_time(&mut self) {
        // Query kernel for current timestamp
        // For genesis, simplified - would use syscall
        self.current_time = kozo_sys::get_timestamp();
    }

    fn audit(&mut self, app_id: AppID, action: AuditAction, cap: &str, success: bool) {
        let cap_bytes = cap.as_bytes();
        let mut name = [0u8; 32];
        let len = cap_bytes.len().min(31);
        name[0..len].copy_from_slice(&cap_bytes[0..len]);

        self.audit_log[self.audit_head] = AuditEvent {
            timestamp: self.current_time,
            app_id,
            action,
            cap_name: name,
            success,
        };
        
        self.audit_head = (self.audit_head + 1) % self.audit_log.len();
    }
}

// stub for no_std time
mod kozo_sys {
    pub fn get_timestamp() -> u64 {
        // TODO: Syscall to kernel for timer
        0
    }
    
    pub use crate::Error;
}