//! KOZO Kernel - ABI Constants
//! File Path: kernel/src/abi.zig
//! Responsibility: Syscall numbers and capability types (Zig version)
//! Note: Duplicates zig-out/include/kozo_abi.h for Zig consumption

// Syscall numbers
pub const SYS_CAP_CREATE = 1;
pub const SYS_CAP_DELETE = 2;
pub const SYS_CAP_REVOKE = 3;
pub const SYS_CAP_TRANSFER = 4;
pub const SYS_CAP_MINT = 5;
pub const SYS_CAP_VERIFY = 6;

pub const SYS_IPC_SEND = 10;
pub const SYS_IPC_RECV = 11;
pub const SYS_IPC_CALL = 12;
pub const SYS_IPC_REPLY = 13;

pub const SYS_RETYPE = 20;
pub const SYS_MAP_FRAME = 21;
pub const SYS_UNMAP_FRAME = 22;

pub const SYS_THREAD_CREATE = 30;
pub const SYS_THREAD_RESUME = 31;
pub const SYS_THREAD_SUSPEND = 32;
pub const SYS_THREAD_SET_PRIORITY = 33;

pub const SYS_ENDPOINT_CREATE = 40;
pub const SYS_ENDPOINT_DELETE = 41;
pub const SYS_NAMESPACE_REGISTER = 42;

pub const SYS_DEBUG_PUTCHAR = 99;
pub const SYS_DEBUG_DUMP_CAPS = 98;

// Capability types
pub const kozo_cap_type_t = enum(u8) {
    CAP_NULL = 0,
    CAP_UNTYPED = 1,
    CAP_CNODE = 2,
    CAP_ENDPOINT = 3,
    CAP_THREAD = 4,
    CAP_ADDRESS_SPACE = 5,
    CAP_FRAME = 6,
    CAP_PAGE_TABLE = 7,
    CAP_IRQ_HANDLER = 8,
};

// Rights bitmask
pub const kozo_rights_t = u64;
pub const RIGHT_READ: u64 = 1 << 0;
pub const RIGHT_WRITE: u64 = 1 << 1;
pub const RIGHT_GRANT: u64 = 1 << 2;
pub const RIGHT_MAP: u64 = 1 << 3;

// Error codes
pub const KOZO_OK: isize = 0;
pub const KOZO_ERR_INVALID: isize = -1;
pub const KOZO_ERR_NO_CAP: isize = -2;
pub const KOZO_ERR_NO_MEM: isize = -3;
pub const KOZO_ERR_ACCESS_DENIED: isize = -4;
pub const KOZO_ERR_NO_SPACE: isize = -5;

// Constants
pub const INIT_UNTYPED_SIZE: usize = 0x1000000;  // 16MB
pub const ROOT_CNODE_SIZE_BITS: usize = 12;       // 4096 slots
pub const IPC_BUFFER_SIZE: usize = 512;
