#![no_std]

pub const KOZO_ABI_VERSION: u32 = 1;

pub type K_HANDLE = u64;
pub type K_STATUS = u32;
pub const K_OK: K_STATUS = 0;
pub const K_INVALID: K_STATUS = 1;
pub const K_DENIED: K_STATUS = 2;

pub type K_SYSCALL_ID = u32;
pub const K_SYSCALL_NOP: K_SYSCALL_ID = 0;
pub const K_SYSCALL_DEBUG_HEARTBEAT: K_SYSCALL_ID = 1;
