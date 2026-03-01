//! KOZO-SYS: Safe Syscall Wrappers
//! File Path: services/kozo-sys/src/syscall.rs
//! Responsibility: x86_64 syscall ABI implementation, mapping Rust to Zig kernel
//! Security: DID Principle - All unsafe assembly isolated in this audited module
//! ABI: rax=num, rdi=a0, rsi=a1, rdx=a2, r10=a3, r8=a4, r9=a5

use crate::abi::{CapType, Error, Rights, Syscall};
use core::arch::asm;

// =============================================================================
// RAW SYSCALL PRIMITIVES (Unsafe - use wrapped versions below)
// =============================================================================

/// Raw syscall with 0 arguments
/// 
/// # Safety
/// Direct kernel call. Must be valid syscall number.
#[inline(always)]
pub unsafe fn syscall0(n: Syscall) -> isize {
    let ret: isize;
    asm!(
        "syscall",
        in("rax") n as usize,
        lateout("rax") ret,
        out("rcx") _, out("r11") _,
        options(nostack, preserves_flags)
    );
    ret
}

/// Raw syscall with 1 argument
#[inline(always)]
pub unsafe fn syscall1(n: Syscall, a0: usize) -> isize {
    let ret: isize;
    asm!(
        "syscall",
        in("rax") n as usize,
        in("rdi") a0,
        lateout("rax") ret,
        out("rcx") _, out("r11") _,
        options(nostack, preserves_flags)
    );
    ret
}

/// Raw syscall with 2 arguments
#[inline(always)]
pub unsafe fn syscall2(n: Syscall, a0: usize, a1: usize) -> isize {
    let ret: isize;
    asm!(
        "syscall",
        in("rax") n as usize,
        in("rdi") a0,
        in("rsi") a1,
        lateout("rax") ret,
        out("rcx") _, out("r11") _,
        options(nostack, preserves_flags)
    );
    ret
}

/// Raw syscall with 3 arguments
#[inline(always)]
pub unsafe fn syscall3(n: Syscall, a0: usize, a1: usize, a2: usize) -> isize {
    let ret: isize;
    asm!(
        "syscall",
        in("rax") n as usize,
        in("rdi") a0,
        in("rsi") a1,
        in("rdx") a2,
        lateout("rax") ret,
        out("rcx") _, out("r11") _,
        options(nostack, preserves_flags)
    );
    ret
}

/// Raw syscall with 4 arguments
/// 
/// Note: a3 goes in r10 (not rcx) per x86_64 syscall ABI
#[inline(always)]
pub unsafe fn syscall4(n: Syscall, a0: usize, a1: usize, a2: usize, a3: usize) -> isize {
    let ret: isize;
    asm!(
        "syscall",
        in("rax") n as usize,
        in("rdi") a0,
        in("rsi") a1,
        in("rdx") a2,
        in("r10") a3, // r10, not rcx!
        lateout("rax") ret,
        out("rcx") _, out("r11") _,
        options(nostack, preserves_flags)
    );
    ret
}

/// Raw syscall with 6 arguments (full register set)
#[inline(always)]
pub unsafe fn syscall6(n: Syscall, a0: usize, a1: usize, a2: usize, a3: usize, a4: usize, a5: usize) -> isize {
    let ret: isize;
    asm!(
        "syscall",
        in("rax") n as usize,
        in("rdi") a0,
        in("rsi") a1,
        in("rdx") a2,
        in("r10") a3,
        in("r8") a4,
        in("r9") a5,
        lateout("rax") ret,
        out("rcx") _, out("r11") _,
        options(nostack, preserves_flags)
    );
    ret
}

// =============================================================================
// CAPABILITY MANAGEMENT (Safe Wrappers)
// =============================================================================

/// SYS_RETYPE: Convert untyped memory into kernel object
/// 
/// # Arguments
/// * `untyped_slot` - Slot index of untyped capability in current CNode
/// * `obj_type` - Type to create (CNode, Endpoint, Thread, etc.)
/// * `dest_slot` - Slot to place new capability
/// * `size_bits` - log2(size) for variable-sized objects (CNodes)
/// 
/// # Safety
/// Destroys information in memory region (zeros it). Irreversible.
pub fn sys_retype(untyped_slot: usize, obj_type: CapType, dest_slot: usize, size_bits: usize) -> Result<(), Error> {
    let res = unsafe { syscall4(Syscall::Retype, untyped_slot, obj_type as usize, dest_slot, size_bits) };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

/// SYS_CAP_TRANSFER: Move/Copy capability between CNodies
/// 
/// Used by Policy Service to delegate capabilities to apps.
/// Requires GRANT right on source capability.
/// 
/// # Arguments
/// * `src_slot` - Source capability in current CNode
/// * `dest_cnode` - Target CNode badge (usually app_id.0)
/// * `dest_slot` - Slot in target CNode
/// * `rights` - Attenuated rights for destination (subset of source)
pub fn sys_cap_transfer(src_slot: usize, dest_cnode: u64, dest_slot: usize, rights: Rights) -> Result<(), Error> {
    let res = unsafe { 
        syscall4(
            Syscall::CapTransfer, 
            src_slot, 
            dest_cnode as usize, 
            dest_slot, 
            rights.bits() as usize
        ) 
    };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

/// SYS_CAP_MINT: Create attenuated child capability
/// 
/// Derives new capability with subset of parent rights.
/// Returns new slot index on success.
/// 
/// # Arguments
/// * `parent_slot` - Source capability (must have GRANT right)
/// * `new_rights` - Rights for child (subset of parent)
pub fn sys_cap_mint(parent_slot: usize, new_rights: Rights) -> Result<usize, Error> {
    let res = unsafe { syscall2(Syscall::CapMint, parent_slot, new_rights.bits() as usize) };
    if res < 0 { 
        Err(Error::from_raw(res)) 
    } else { 
        Ok(res as usize) 
    }
}

/// SYS_CAP_REVOKE: Destroy capability and all derivatives
/// 
/// Immediate invalidation. Apps using this capability will fault.
/// Used for JIT delegation timeout enforcement.
pub fn sys_cap_revoke(cnode: usize, slot: usize) -> Result<(), Error> {
    let res = unsafe { syscall2(Syscall::CapRevoke, cnode, slot) };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

/// SYS_CAP_VERIFY: Verify badge authenticity (anti-spoofing)
/// 
/// Policy Service uses this to confirm AppID claims.
/// Validates that badge matches kernel's records for thread.
pub fn sys_cap_verify(badge: u64, thread_cap: usize) -> Result<(), Error> {
    let res = unsafe { syscall2(Syscall::CapVerify, badge as usize, thread_cap) };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

/// SYS_CAP_CREATE: Create capability from untyped (legacy alias for retype)
pub fn sys_cap_create(untyped: usize, obj_type: CapType, slot: usize) -> Result<(), Error> {
    sys_retype(untyped, obj_type, slot, 0)
}

/// SYS_CAP_DELETE: Remove capability from CNode (don't free memory)
/// 
/// Safer than revoke - doesn't cascade. Use for cleanup.
pub fn sys_cap_delete(slot: usize) -> Result<(), Error> {
    let res = unsafe { syscall1(Syscall::CapDelete, slot) };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

// =============================================================================
// IPC (INTER-PROCESS COMMUNICATION)
// =============================================================================

/// SYS_IPC_SEND: Asynchronous message send
/// 
/// Non-blocking if timeout is 0. Use for notifications.
/// 
/// # Arguments
/// * `endpoint` - Endpoint capability slot
/// * `buf` - Message buffer pointer
/// * `len` - Message length (max IPC_BUFFER_SIZE)
/// * `timeout` - 0=non-blocking, >0=blocking with timeout
pub unsafe fn sys_ipc_send(endpoint: usize, buf: *const u8, len: usize, timeout: usize) -> Result<(), Error> {
    let res = syscall4(Syscall::IpcSend, endpoint, buf as usize, len, timeout);
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

/// SYS_IPC_RECV: Blocking message receive
/// 
/// Returns badge (sender identity) on success.
/// 
/// # Arguments
/// * `endpoint` - Endpoint to listen on
/// * `buf` - Buffer to receive message (must be writable)
/// * `buf_size` - Buffer capacity (should be IPC_BUFFER_SIZE)
/// 
/// # Returns
/// Badge (u64 as usize) identifying sender
pub unsafe fn sys_ipc_recv(endpoint: usize, buf: *mut u8, buf_size: usize) -> Result<u64, Error> {
    let res = syscall3(Syscall::IpcRecv, endpoint, buf as usize, buf_size);
    if res < 0 { 
        Err(Error::from_raw(res)) 
    } else { 
        Ok(res as u64) 
    }
}

/// SYS_IPC_CALL: Synchronous call with direct context switch
/// 
/// Fast path: switches directly to recipient without scheduler.
/// Blocks until recipient calls ipc_reply.
/// 
/// # Performance
/// ~300 cycles vs ~1000 for separate send/recv/schedule
pub unsafe fn sys_ipc_call(endpoint: usize, msg: *const u8, msg_len: usize, timeout: usize) -> Result<(), Error> {
    let res = syscall4(Syscall::IpcCall, endpoint, msg as usize, msg_len, timeout);
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

/// SYS_IPC_REPLY: Reply to call with direct switch back
/// 
/// Must be called while handling a call. Returns to caller.
pub unsafe fn sys_ipc_reply(reply: *const u8, reply_len: usize) -> Result<(), Error> {
    let res = syscall2(Syscall::IpcReply, reply as usize, reply_len);
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

// =============================================================================
// THREADING
// =============================================================================

/// SYS_THREAD_CREATE: Create new thread in address space
/// 
/// # Arguments
/// * `vspace` - Address space (page table root) capability
/// * `entry` - Entry point virtual address
/// * `stack` - Stack pointer virtual address
/// * `cnode` - Root CNode for new thread
/// 
/// # Returns
/// Thread capability slot index
pub fn sys_thread_create(vspace: usize, entry: usize, stack: usize, cnode: usize) -> Result<usize, Error> {
    let res = unsafe { syscall4(Syscall::ThreadCreate, vspace, entry, stack, cnode) };
    if res < 0 { 
        Err(Error::from_raw(res)) 
    } else { 
        Ok(res as usize) 
    }
}

/// SYS_THREAD_RESUME: Start suspended thread
/// 
/// Thread begins execution at entry point specified in create.
pub fn sys_thread_resume(thread_cap: usize) -> Result<(), Error> {
    let res = unsafe { syscall1(Syscall::ThreadResume, thread_cap) };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

/// SYS_THREAD_SUSPEND: Pause thread
/// 
/// Thread can be resumed later. Use for debugging.
pub fn sys_thread_suspend(thread_cap: usize) -> Result<(), Error> {
    let res = unsafe { syscall1(Syscall::ThreadSuspend, thread_cap) };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

/// SYS_THREAD_SET_PRIORITY: Adjust scheduling priority
/// 
/// Cannot increase above own priority (prevents escalation).
pub fn sys_thread_set_priority(thread_cap: usize, priority: u8) -> Result<(), Error> {
    let res = unsafe { syscall2(Syscall::ThreadSetPriority, thread_cap, priority as usize) };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

// =============================================================================
// ENDPOINTS & NAMESPACE
// =============================================================================

/// SYS_ENDPOINT_CREATE: Create new IPC endpoint
/// 
/// Endpoints are unidirectional message queues.
pub fn sys_endpoint_create(slot: usize) -> Result<(), Error> {
    let res = unsafe { syscall1(Syscall::EndpointCreate, slot) };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

/// SYS_ENDPOINT_DELETE: Destroy endpoint and wake blocked threads
pub fn sys_endpoint_delete(slot: usize) -> Result<(), Error> {
    let res = unsafe { syscall1(Syscall::EndpointDelete, slot) };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

/// SYS_NAMESPACE_REGISTER: Register endpoint in system namespace
/// 
/// Allows other processes to find this endpoint by name.
/// Critical for Policy Service ("system.policy").
/// 
/// # Safety
/// Name must be valid UTF-8, null-terminated.
pub unsafe fn sys_namespace_register(endpoint: usize, name: *const u8, name_len: usize) -> Result<(), Error> {
    let res = syscall3(Syscall::NamespaceRegister, endpoint, name as usize, name_len);
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

// =============================================================================
// MEMORY
// =============================================================================

/// SYS_MAP_FRAME: Map physical page into address space
/// 
/// # Arguments
/// * `frame_cap` - Frame capability slot
/// * `vaddr` - Virtual address to map (must be page-aligned)
/// * `rights` - Mapping rights (READ/WRITE/EXEC)
/// * `attrs` - Cache attributes, etc.
pub fn sys_map_frame(frame_cap: usize, vaddr: usize, rights: Rights, attrs: usize) -> Result<(), Error> {
    let res = unsafe { syscall4(Syscall::MapFrame, frame_cap, vaddr, rights.bits() as usize, attrs) };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

/// SYS_UNMAP_FRAME: Remove mapping
/// 
/// Frame can be remapped elsewhere after unmap.
pub fn sys_unmap_frame(frame_cap: usize, vaddr: usize) -> Result<(), Error> {
    let res = unsafe { syscall2(Syscall::UnmapFrame, frame_cap, vaddr) };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

// =============================================================================
// DEBUGGING
// =============================================================================

/// SYS_DEBUG_PUTCHAR: Output character to kernel debug console
/// 
/// Safe to call anytime. Used for early boot debugging.
pub fn sys_debug_putchar(c: u8) {
    unsafe { 
        syscall1(Syscall::DebugPutchar, c as usize); 
    }
}

/// SYS_DEBUG_PRINT: Output string to kernel debug console
/// 
/// Convenience function (not a real syscall, loops over putchar).
pub fn sys_debug_print(s: &str) {
    for c in s.bytes() {
        sys_debug_putchar(c);
    }
}

/// SYS_DEBUG_DUMP_CAPS: Print capability table to debug console
/// 
/// Useful for debugging capability issues.
pub fn sys_debug_dump_caps() -> Result<(), Error> {
    let res = unsafe { syscall0(Syscall::DebugDumpCaps) };
    if res == 0 { Ok(()) } else { Err(Error::from_raw(res)) }
}

// =============================================================================
// CONVENIENCE MODULES
// =============================================================================

/// Safe IPC helpers using IPCBuffer type
pub mod ipc {
    use super::*;
    use crate::ipc::IPCBuffer;

    /// Send using IPCBuffer
    pub fn send(endpoint: usize, buf: &IPCBuffer, timeout: usize) -> Result<(), Error> {
        unsafe { sys_ipc_send(endpoint, buf.as_ptr(), buf.len(), timeout) }
    }

    /// Receive into IPCBuffer
    pub fn recv(endpoint: usize, buf: &mut IPCBuffer) -> Result<u64, Error> {
        let badge = unsafe { sys_ipc_recv(endpoint, buf.as_mut_ptr(), buf.capacity())? };
        buf.set_len(512); // Max received - TODO: get actual from kernel
        Ok(badge)
    }

    /// Call with IPCBuffer
    pub fn call(endpoint: usize, request: &IPCBuffer, reply: &mut IPCBuffer) -> Result<(), Error> {
        unsafe {
            sys_ipc_call(endpoint, request.as_ptr(), request.len(), 0)?;
            // Reply comes back in same buffer or different? Depends on kernel impl
            Ok(())
        }
    }
}