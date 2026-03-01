//! KOZO Policy Service - Main Entry Point
//! File Path: services/policy/src/main.rs
//! Responsibility: Orchestrate authentication, authorization, and capability delegation
//! Architecture: Triple Check (Request -> Validation -> Consent -> Delegation)

#![no_std]
#![no_main]

mod auth;      // File Path: services/policy/src/auth.rs
mod db;        // File Path: services/policy/src/db.rs
mod ui;        // File Path: services/policy/src/ui.rs
mod delegation; // File Path: services/policy/src/delegation.rs

use auth::AppID;
use db::{PolicyDB, AuditAction};
use ui::{assess_risk, trigger_secure_prompt, require_hardware_presence, RiskLevel};
use delegation::{delegate_capability, revoke_capability};
use kozo_sys::{syscall, Syscall, Error, IPCBuffer, Endpoint};

/// IPC message types from Linux Compatibility Shim
#[derive(Debug)]
enum Request {
    Capability { name: [u8; 32], thread_cap: usize },
    Revoke { name: [u8; 32] },
    Query,
}

/// IPC response types to Linux Compatibility Shim
#[derive(Debug)]
enum Response {
    Granted,
    Denied,
    Revoked,
    List([u8; 256]), // Serialized capability list
    Error(Error),
}

#[no_mangle]
pub extern "C" fn _start() -> ! {
    main();
}

fn main() -> ! {
    // Initialize policy database
    let mut db = match PolicyDB::new() {
        Ok(d) => d,
        Err(e) => {
            kozo_sys::debug_print("FATAL: PolicyDB init failed\n");
            loop {} // Halt - cannot recover
        }
    };

    // Register system-wide endpoint for capability requests
    let endpoint = match register_policy_endpoint() {
        Ok(ep) => ep,
        Err(e) => {
            kozo_sys::debug_print("FATAL: Failed to register Policy endpoint\n");
            loop {}
        }
    };

    kozo_sys::debug_print("Policy: ready\n");

    // Main event loop: Process capability requests
    loop {
        // 1. RECEIVE: Wait for IPC from Linux Compatibility Shim
        // Kernel stamps message with sender's unforgeable badge (AppID)
        let (badge, request) = match receive_request(&endpoint) {
            Ok((b, r)) => (b, r),
            Err(e) => {
                log_error("IPC receive failed", e);
                continue;
            }
        };

        let app_id = AppID::from_badge(badge);

        // 2. AUTHENTICATE: Verify AppID authenticity with kernel
        if let Err(e) = app_id.verify(request.thread_cap()) {
            log_security_event(app_id, "AUTH_FAILURE", &request);
            send_response(&endpoint, badge, Response::Error(Error::AccessDenied));
            continue;
        }

        // 3. AUTHORIZE: Process based on request type
        let response = match request {
            Request::Capability { name, thread_cap } => {
                handle_capability_request(&mut db, app_id, &name)
            }
            Request::Revoke { name } => {
                handle_revocation(&mut db, app_id, &name)
            }
            Request::Query => {
                handle_query(&db, app_id)
            }
        };

        // 4. RESPOND: Send result back to Shim
        if let Err(e) = send_response(&endpoint, badge, response) {
            log_error("IPC send failed", e);
        }
    }
}

/// Handle new capability request (Triple Check)
fn handle_capability_request(db: &mut PolicyDB, app_id: AppID, cap_name_bytes: &[u8; 32]) -> Response {
    // Convert bytes to string (null-terminated)
    let cap_name = null_terminated_str(cap_name_bytes);
    
    // CHECK 1: Database lookup (previously granted?)
    match db.is_granted(app_id, cap_name) {
        Ok(true) => {
            // Valid existing grant - delegate immediately
            match delegate_capability(app_id, cap_name) {
                Ok(_) => Response::Granted,
                Err(e) => Response::Error(e),
            }
        }
        Ok(false) | Err(_) => {
            // Not granted or error - need user consent
            
            // CHECK 2: Risk assessment and user consent
            let risk = assess_risk(cap_name);
            
            // Critical operations require hardware presence proof
            let approved = match risk {
                RiskLevel::Critical => {
                    require_hardware_presence() && 
                    trigger_secure_prompt(app_id, cap_name, risk, None)
                }
                _ => trigger_secure_prompt(app_id, cap_name, risk, None),
            };

            if approved {
                // Determine JIT duration based on risk
                let duration = risk.default_duration();
                
                // Record in database
                if let Err(e) = db.grant(app_id, cap_name, Some(duration)) {
                    return Response::Error(e);
                }

                // CHECK 3: Delegate actual capability
                match delegate_capability(app_id, cap_name) {
                    Ok(_) => Response::Granted,
                    Err(e) => {
                        // Rollback database on delegation failure
                        db.revoke(app_id, cap_name).ok();
                        Response::Error(e)
                    }
                }
            } else {
                // User denied - log for audit
                db.log_denial(app_id, cap_name);
                Response::Denied
            }
        }
    }
}

/// Handle capability revocation
fn handle_revocation(db: &mut PolicyDB, app_id: AppID, cap_name_bytes: &[u8; 32]) -> Response {
    let cap_name = null_terminated_str(cap_name_bytes);
    
    // Revoke from kernel (immediate effect)
    if let Err(e) = revoke_capability(app_id, cap_name) {
        return Response::Error(e);
    }
    
    // Remove from database
    if let Err(e) = db.revoke(app_id, cap_name) {
        return Response::Error(e);
    }
    
    Response::Revoked
}

/// Handle capability query (list granted caps)
fn handle_query(db: &PolicyDB, app_id: AppID) -> Response {
    // For genesis: simplified response
    // Production: serialize capability list
    Response::List([0u8; 256])
}

/// Register "system.policy" endpoint in kernel namespace
fn register_policy_endpoint() -> Result<Endpoint, Error> {
    unsafe {
        // Create endpoint capability
        let ep_handle = syscall::syscall0(Syscall::EndpointCreate as usize)?;
        if ep_handle < 0 {
            return Err(Error::from_raw(ep_handle));
        }

        // Register in namespace
        let name = b"system.policy\0";
        let result = syscall::syscall3(
            Syscall::NamespaceRegister as usize,
            ep_handle as usize,
            name.as_ptr() as usize,
            name.len(),
        );
        
        if result < 0 {
            return Err(Error::from_raw(result));
        }

        Ok(Endpoint::from_raw(ep_handle as usize))
    }
}

/// Receive and parse IPC request
fn receive_request(endpoint: &Endpoint) -> Result<(u64, Request), Error> {
    let mut buf = IPCBuffer::new();
    
    unsafe {
        // Blocking receive
        let result = syscall::syscall3(
            Syscall::IpcRecv as usize,
            endpoint.raw(),
            buf.as_mut_ptr(),
            buf.capacity(),
        );
        
        if result < 0 {
            return Err(Error::from_raw(result));
        }
        
        let badge = result as u64;
        
        // Parse request type
        let req_type = buf.read_u8().ok_or(Error::Invalid)?;
        
        let request = match req_type {
            0 => { // Capability request
                let mut name = [0u8; 32];
                for i in 0..32 {
                    name[i] = buf.read_u8().unwrap_or(0);
                }
                let thread_cap = buf.read_usize().ok_or(Error::Invalid)?;
                Request::Capability { name, thread_cap }
            }
            1 => { // Revoke
                let mut name = [0u8; 32];
                for i in 0..32 {
                    name[i] = buf.read_u8().unwrap_or(0);
                }
                Request::Revoke { name }
            }
            2 => { // Query
                Request::Query
            }
            _ => return Err(Error::Invalid),
        };
        
        Ok((badge, request))
    }
}

/// Send IPC response
fn send_response(endpoint: &Endpoint, badge: u64, response: Response) -> Result<(), Error> {
    let mut buf = IPCBuffer::new();
    
    // Serialize response
    match response {
        Response::Granted => buf.write_u8(0).map_err(|_| Error::NoMem)?,
        Response::Denied => buf.write_u8(1).map_err(|_| Error::NoMem)?,
        Response::Revoked => buf.write_u8(2).map_err(|_| Error::NoMem)?,
        Response::List(data) => {
            buf.write_u8(3).map_err(|_| Error::NoMem)?;
            for byte in data.iter() {
                buf.write_u8(*byte).map_err(|_| Error::NoMem)?;
            }
        }
        Response::Error(e) => {
            buf.write_u8(4).map_err(|_| Error::NoMem)?;
            buf.write_u8(e as u8).map_err(|_| Error::NoMem)?;
        }
    }
    
    unsafe {
        syscall::syscall3(
            Syscall::IpcReply as usize,
            buf.as_ptr(),
            buf.len(),
            0,
        );
    }
    
    Ok(())
}

/// Convert null-terminated byte array to &str
fn null_terminated_str(bytes: &[u8; 32]) -> &str {
    let len = bytes.iter().position(|&b| b == 0).unwrap_or(32);
    core::str::from_utf8(&bytes[0..len]).unwrap_or("invalid")
}

/// Request helper for thread_cap extraction
impl Request {
    fn thread_cap(&self) -> usize {
        match self {
            Request::Capability { thread_cap, .. } => *thread_cap,
            _ => 0,
        }
    }
}

/// Logging helpers
fn log_error(msg: &str, e: Error) {
    kozo_sys::debug_print("[POLICY ERROR] ");
    kozo_sys::debug_print(msg);
    kozo_sys::debug_print(": ");
    // Print error code
    kozo_sys::debug_print("\n");
}

fn log_security_event(app_id: AppID, event: &str, req: &Request) {
    kozo_sys::debug_print("[SECURITY] ");
    kozo_sys::debug_print(event);
    kozo_sys::debug_print(" app=");
    kozo_sys::debug_print_hex(app_id.raw());
    kozo_sys::debug_print("\n");
}

// === kozo-sys stubs ===
mod kozo_sys {
    pub use kozo_sys::{Error, Syscall, IPCBuffer, Endpoint};
    
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
            unsafe {
                core::arch::asm!(
                    "syscall",
                    in("rax") 99,
                    in("rdi") HEX[digit as usize] as usize,
                    options(nostack, preserves_flags)
                );
            }
        }
    }
}

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    kozo_sys::debug_print("POLICY PANIC\n");
    loop {}
}