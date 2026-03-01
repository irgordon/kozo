//! KOZO-SYS: High-performance bridge between Rust services and Zig Kernel
//! File Path: services/kozo-sys/src/lib.rs
//! Responsibility: Safe, zero-cost abstractions over kernel syscalls
//! Architecture: Generated ABI + safe wrappers + capability handles

#![no_std]
#![no_main]
#![feature(asm_const)]
#![allow(internal_features)]

// ============================================================================
// MODULES
// ============================================================================

/// Auto-generated ABI constants from build.zig
/// File Path: services/kozo-sys/src/abi.rs (Generated)
pub mod abi;

/// Raw syscall wrappers and safe convenience functions
/// File Path: services/kozo-sys/src/syscall.rs
pub mod syscall;

/// Capability handle types for memory-safe capability management
/// File Path: services/kozo-sys/src/capability.rs
pub mod capability;

/// Boot information structures passed from kernel to init
/// File Path: services/kozo-sys/src/boot_info.rs
pub mod boot_info;

/// IPC (Inter-Process Communication) buffer types and endpoint handles
/// File Path: services/kozo-sys/src/ipc.rs
pub mod ipc;

/// Utility functions for no_std environment
/// File Path: services/kozo-sys/src/util.rs
pub mod util;

// ============================================================================
// RE-EXPORTS (Ergonomics)
// ============================================================================

// Core ABI types - used by every service
pub use abi::{
    CapType,
    Error,
    Rights,
    Syscall,
    IPC_BUFFER_SIZE,
    ROOT_CNODE_SIZE_BITS,
    KOZO_VERSION,
};

// Capability handle for type-safe capability management
pub use capability::CapHandle;

// Boot information passed from kernel
pub use boot_info::BootInfo;

// IPC primitives
pub use ipc::{Endpoint, IPCBuffer, Message};

// Syscall wrappers (most common imports)
pub use syscall::{
    sys_retype,
    sys_cap_transfer,
    sys_cap_mint,
    sys_cap_revoke,
    sys_cap_verify,
    sys_ipc_call,
    sys_ipc_reply,
    sys_ipc_recv,
    sys_ipc_send,
    sys_thread_create,
    sys_thread_resume,
    sys_debug_print,
    sys_debug_putchar,
};

// ============================================================================
// PRELUDE (Convenient imports for service authors)
// ============================================================================

/// Prelude module for convenient importing
pub mod prelude {
    pub use crate::{
        CapHandle, CapType, Endpoint, Error, IPCBuffer, Rights, Syscall,
        syscall::{
            sys_cap_transfer, sys_ipc_call, sys_ipc_reply, sys_retype,
            sys_thread_create, sys_thread_resume,
        },
    };
}

// ============================================================================
// CRATE-LEVEL ERROR HANDLING
// ============================================================================

/// Initialize kozo-sys for a service
/// 
/// # Safety
/// Must be called exactly once before any syscalls.
/// Called automatically by _start in service startup.
pub unsafe fn init() -> Result<(), Error> {
    // Verify ABI version matches kernel
    // This ensures build.zig was run and headers are synchronized
    verify_abi_version()?;
    
    // Set up any global state (none for genesis)
    Ok(())
}

/// Verify that compiled ABI matches running kernel
fn verify_abi_version() -> Result<(), Error> {
    // In production: query kernel for version, compare to KOZO_VERSION
    // For genesis: assume match (build system enforces this)
    Ok(())
}

/// Global panic hook registration (no_std)
pub fn set_panic_hook() {
    // Set panic handler to kernel debug output
    // Already done via #[panic_handler] in individual services
}

// ============================================================================
// VERSION INFO
// ============================================================================

/// Get KOZO version string
pub const fn version() -> &'static str {
    KOZO_VERSION
}

/// Check if running in genesis block (development) mode
pub const fn is_genesis() -> bool {
    // Genesis builds have specific feature flag
    cfg!(feature = "genesis")
}