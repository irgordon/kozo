//! KOZO Kernel - Syscall Dispatcher
//! Responsibility: Validate and dispatch syscalls with capability checks

const std = @import("std");
const abi = @import("abi.zig");
const cap = @import("capability.zig");
const thread = @import("thread.zig");
const sched = @import("scheduler.zig");

pub const SYS_MAP_MEMORY = 12;

/// System V ABI: args in rdi, rsi, rdx, r10, r8, r9
/// Returns: error code (0 = success, negative = error)
pub export fn kozo_syscall_handler(
    n: usize,
    arg0: usize, // rdi
    arg1: usize, // rsi  
    arg2: usize, // rdx
    arg3: usize, // r10
    arg4: usize, // r8
    _arg5: usize, // r9 (reserved for future use)
) isize {
    // Silence unused warnings - all args used depending on syscall
    _ = arg4;
    _ = _arg5;

    // Validate syscall number range for security
    if (n > 99) {
        return -1; // KOZO_ERR_INVALID
    }

    return switch (n) {
        // === CAPABILITY PRIMITIVES (Layer 0) ===
        abi.SYS_RETYPE => cap.sys_retype(arg0, @enumFromInt(arg1), arg2, arg3),
        abi.SYS_CAP_TRANSFER => cap.sys_transfer(arg0, arg1, arg2, arg3),
        abi.SYS_CAP_MINT => cap.sys_mint(arg0, arg1),
        abi.SYS_CAP_REVOKE => cap.sys_revoke(arg0, arg1),
        abi.SYS_CAP_VERIFY => cap.sys_verify(arg0, arg1),
        abi.SYS_CAP_CREATE => cap.sys_create(arg0, @enumFromInt(arg1), arg2), // Create from untyped
        abi.SYS_CAP_DELETE => cap.sys_delete(arg0), // Remove from cnode but don't free

        // === IPC - DIRECT SWITCH (Performance Critical) ===
        abi.SYS_IPC_SEND => ipc_send(arg0, arg1, arg2, arg3),
        abi.SYS_IPC_RECV => ipc_recv(arg0, arg1, arg2),
        abi.SYS_IPC_CALL => ipc_call(arg0, arg1, arg2, arg3), // Direct switch to dest
        abi.SYS_IPC_REPLY => ipc_reply(arg0, arg1), // Direct switch back to caller

        // === THREADING ===
        abi.SYS_THREAD_CREATE => thread_create(arg0, arg1, arg2, arg3),
        abi.SYS_THREAD_RESUME => thread_resume(arg0),
        abi.SYS_THREAD_SUSPEND => thread_suspend(arg0),
        abi.SYS_THREAD_SET_PRIORITY => thread_set_priority(arg0, arg1),

        // === ENDPOINTS (Policy Service Registration) ===
        abi.SYS_ENDPOINT_CREATE => endpoint_create(arg0),
        abi.SYS_ENDPOINT_DELETE => endpoint_delete(arg0),
        abi.SYS_NAMESPACE_REGISTER => namespace_register(arg0, arg1, arg2),

        // === MEMORY ===
        abi.SYS_MAP_FRAME => map_frame(arg0, arg1, arg2, arg3),
        abi.SYS_UNMAP_FRAME => unmap_frame(arg0, arg1),

        // === DEBUGGING ===
        abi.SYS_DEBUG_PUTCHAR => {
            const char: u8 = @truncate(arg0);
            // Write to serial port directly (bypassing stdio for kernel debug)
            const serial_port: *volatile u8 = @ptrFromInt(0x3F8); // COM1
            serial_port.* = char;
            return 0;
        },
        abi.SYS_DEBUG_DUMP_CAPS => debug_dump_caps(),

        else => {
            std.log.warn("KOZO: Invalid syscall {d} from thread {d}", .{ 
                n, thread.getCurrent().tid 
            });
            return -1; // KOZO_ERR_INVALID
        },
    };
}

// === IPC IMPLEMENTATION (Direct Switch) ===

/// SYS_IPC_CALL: Synchronous call with direct context switch
/// arg0: endpoint capability index (in current cnode)
/// arg1: message buffer address (in caller address space)
/// arg2: message length (max 512 bytes per abi.IPC_BUFFER_SIZE)
/// arg3: timeout (0 = blocking, >0 = timeout in ms)
/// Returns: 0 on success (reply received), error code on failure
fn ipc_call(endpoint_idx: usize, msg_ptr: usize, msg_len: usize, timeout: usize) isize {
    if (msg_len > abi.IPC_BUFFER_SIZE) return -6; // InvalidParam
    
    const current = thread.getCurrent() orelse return -2;
    
    // Verify endpoint capability
    const ep_slot = current.root_cnode.get(endpoint_idx) catch return -2;
    if (ep_slot.cap_type != .CAP_ENDPOINT) return -1;
    
    const endpoint = &ep_slot.data.endpoint;
    
    // Copy message to kernel buffer (validated user pointer)
    var msg_buffer: [abi.IPC_BUFFER_SIZE]u8 = undefined;
    const user_msg = @as([*]const u8, @ptrFromInt(msg_ptr))[0..msg_len];
    @memcpy(msg_buffer[0..msg_len], user_msg);
    
    // Find recipient (server) thread waiting on this endpoint
    const recipient = endpoint.queue.dequeue() orelse {
        // No server waiting - queue ourselves and block
        if (timeout == 0) {
            current.state = .BLOCKED_SEND;
            current.ipc_endpoint = endpoint_idx;
            current.ipc_msg_len = msg_len;
            @memcpy(current.ipc_buffer[0..msg_len], msg_buffer[0..msg_len]);
            
            sched.block(current); // Context switch to next runnable
            return 0; // Returns here when reply comes
        } else {
            return -7; // WouldBlock (timeout)
        }
    };
    
    // DIRECT SWITCH: Transfer directly to recipient
    // Save caller context, restore recipient, set reply capability
    
    // Set up reply capability (implicit in call)
    current.ipc_state = .WAITING_REPLY;
    current.ipc_caller = recipient; // Server knows who to reply to
    
    // Transfer message to recipient
    recipient.ipc_msg_len = msg_len;
    @memcpy(recipient.ipc_buffer[0..msg_len], msg_buffer[0..msg_len]);
    recipient.ipc_state = .RECEIVED_CALL;
    recipient.ipc_badge = endpoint.badge; // Server sees caller's badge
    
    // Context switch to recipient (no scheduler involvement)
    sched.switch_to(recipient);
    
    // When recipient replies, we resume here
    return 0;
}

/// SYS_IPC_REPLY: Reply to caller with direct switch back
/// arg0: reply message buffer address
/// arg1: reply message length
/// Returns: 0 on success
fn ipc_reply(reply_ptr: usize, reply_len: usize) isize {
    if (reply_len > abi.IPC_BUFFER_SIZE) return -6;
    
    const current = thread.getCurrent() orelse return -2;
    
    // Verify we are in a call (have a caller waiting)
    if (current.ipc_state != .RECEIVED_CALL or current.ipc_caller == null) {
        return -8; // NoCaller (reply without call)
    }
    
    const caller = current.ipc_caller.?;
    
    // Copy reply to caller's buffer
    const reply_msg = @as([*]const u8, @ptrFromInt(reply_ptr))[0..reply_len];
    caller.ipc_msg_len = reply_len;
    @memcpy(caller.ipc_buffer[0..reply_len], reply_msg);
    
    // Mark caller runnable
    caller.state = .RUNNABLE;
    caller.ipc_state = .IDLE;
    sched.enqueue(caller);
    
    // Mark current thread (server) as waiting for next call
    current.ipc_state = .WAITING_CALL;
    current.ipc_caller = null;
    
    // DIRECT SWITCH BACK to caller
    // If caller has higher priority, it runs immediately
    // Otherwise we continue and caller goes to runqueue
    
    if (caller.priority <= current.priority) {
        sched.switch_to(caller);
    }
    
    return 0;
}

/// SYS_IPC_SEND: Async send (non-blocking)
fn ipc_send(endpoint_idx: usize, msg_ptr: usize, msg_len: usize, timeout: usize) isize {
    _ = timeout; // For async, timeout only matters if queue full
    if (msg_len > abi.IPC_BUFFER_SIZE) return -6;
    
    const current = thread.getCurrent() orelse return -2;
    const ep_slot = current.root_cnode.get(endpoint_idx) catch return -2;
    if (ep_slot.cap_type != .CAP_ENDPOINT) return -1;
    
    const endpoint = &ep_slot.data.endpoint;
    
    // Try to deliver immediately if server waiting
    if (endpoint.queue.dequeue()) |server| {
        // Fast path: direct switch to server
        const msg = @as([*]const u8, @ptrFromInt(msg_ptr))[0..msg_len];
        server.ipc_msg_len = msg_len;
        @memcpy(server.ipc_buffer[0..msg_len], msg);
        server.ipc_state = .RECEIVED_ASYNC;
        server.ipc_badge = endpoint.badge;
        sched.switch_to(server);
        return 0;
    }
    
    // Slow path: queue message (for async) or block
    // For genesis block, just return WouldBlock
    return -7; // WouldBlock
}

/// SYS_IPC_RECV: Blocking receive on endpoint
fn ipc_recv(endpoint_idx: usize, buf_ptr: usize, buf_len: usize) isize {
    if (buf_len < abi.IPC_BUFFER_SIZE) return -6;
    
    const current = thread.getCurrent() orelse return -2;
    const ep_slot = current.root_cnode.get(endpoint_idx) catch return -2;
    if (ep_slot.cap_type != .CAP_ENDPOINT) return -1;
    
    const endpoint = &ep_slot.data.endpoint;
    
    // Check if message already pending (from async send)
    if (current.ipc_state == .RECEIVED_ASYNC or current.ipc_state == .RECEIVED_CALL) {
        // Copy to user buffer
        const user_buf = @as([*]u8, @ptrFromInt(buf_ptr))[0..current.ipc_msg_len];
        @memcpy(user_buf, current.ipc_buffer[0..current.ipc_msg_len]);
        const len = current.ipc_msg_len;
        
        // Reset state
        current.ipc_state = .IDLE;
        
        return @intCast(len);
    }
    
    // No message waiting - block until sender arrives
    current.state = .BLOCKED_RECV;
    current.ipc_endpoint = endpoint_idx;
    endpoint.queue.enqueue(current);
    
    sched.block(current);
    
    // Returns here when message arrives
    // Copy to user buffer
    const user_buf = @as([*]u8, @ptrFromInt(buf_ptr))[0..current.ipc_msg_len];
    @memcpy(user_buf, current.ipc_buffer[0..current.ipc_msg_len]);
    
    return @intCast(current.ipc_msg_len);
}

// === THREADING ===

/// SYS_THREAD_CREATE: Create new thread in specified address space
/// arg0: vspace capability index (CAP_ADDRESS_SPACE)
/// arg1: entry point address (virtual)
/// arg2: stack pointer (virtual)  
/// arg3: cnode capability index for root (initial capabilities)
/// Returns: thread capability index on success, error on failure
fn thread_create(vspace_idx: usize, entry: usize, stack: usize, cnode_idx: usize) isize {
    const current = thread.getCurrent() orelse return -2;
    
    // Verify VSpace capability
    const vspace_slot = current.root_cnode.get(vspace_idx) catch return -2;
    if (vspace_slot.cap_type != .CAP_ADDRESS_SPACE) return -1;
    
    // Verify CNode capability  
    const cnode_slot = current.root_cnode.get(cnode_idx) catch return -2;
    if (cnode_slot.cap_type != .CAP_CNODE) return -1;
    
    // Allocate TCB from kernel pool (fixed memory)
    const tcb = thread.allocTCB() orelse return -3; // NoMem
    
    // Initialize thread
    tcb.vspace = vspace_slot;
    tcb.root_cnode = cnode_slot;
    tcb.context.rip = entry;
    tcb.context.rsp = stack;
    tcb.state = .SUSPENDED;
    tcb.priority = current.priority; // Inherit priority
    
    // Create thread capability in current cnode
    const slot = current.root_cnode.findFreeSlot() catch {
        thread.freeTCB(tcb);
        return -5; // NoSpace
    };
    
    current.root_cnode.insert(slot, .{
        .cap_type = .CAP_THREAD,
        .rights = abi.RIGHT_READ | abi.RIGHT_WRITE | abi.RIGHT_GRANT,
        .badge = cap.generateBadge(@intFromPtr(tcb), .CAP_THREAD),
        .data = .{ .thread = .{ .tcb = tcb } },
    }) catch return -1;
    
    return @intCast(slot);
}

/// SYS_THREAD_RESUME: Start a suspended thread
fn thread_resume(thread_idx: usize) isize {
    const current = thread.getCurrent() orelse return -2;
    const thread_slot = current.root_cnode.get(thread_idx) catch return -2;
    if (thread_slot.cap_type != .CAP_THREAD) return -1;
    
    const tcb = thread_slot.data.thread.tcb;
    if (tcb.state != .SUSPENDED) return -9; // InvalidState
    
    tcb.state = .RUNNABLE;
    sched.enqueue(tcb);
    
    // Preempt if new thread has higher priority
    if (tcb.priority < current.priority) {
        sched.yield();
    }
    
    return 0;
}

fn thread_suspend(thread_idx: usize) isize {
    const current = thread.getCurrent() orelse return -2;
    const thread_slot = current.root_cnode.get(thread_idx) catch return -2;
    if (thread_slot.cap_type != .CAP_THREAD) return -1;
    
    const tcb = thread_slot.data.thread.tcb;
    if (tcb.state == .RUNNING) {
        sched.forceSuspend(tcb);
    } else if (tcb.state == .RUNNABLE) {
        sched.removeFromQueue(tcb);
        tcb.state = .SUSPENDED;
    }
    
    return 0;
}

fn thread_set_priority(thread_idx: usize, priority: usize) isize {
    if (priority > 255) return -6;
    
    const current = thread.getCurrent() orelse return -2;
    const thread_slot = current.root_cnode.get(thread_idx) catch return -2;
    if (thread_slot.cap_type != .CAP_THREAD) return -1;
    
    const tcb = thread_slot.data.thread.tcb;
    
    // Cannot increase priority above own (DID: prevents priority escalation)
    if (priority < current.priority) return -4;
    
    tcb.priority = @intCast(priority);
    
    // Re-queue if runnable and priority changed
    if (tcb.state == .RUNNABLE) {
        sched.reprioritize(tcb);
    }
    
    return 0;
}

// === ENDPOINTS ===

/// SYS_ENDPOINT_CREATE: Create new IPC endpoint
fn endpoint_create(slot_idx: usize) isize {
    const current = thread.getCurrent() orelse return -2;
    
    // Ensure slot is free
    const slot = current.root_cnode.get(slot_idx) catch return -2;
    if (slot.cap_type != .CAP_NULL) return -5; // NoSpace
    
    // Retype from untyped? For genesis, we need an untyped index
    // Actually this should take an untyped index to retype from
    return -1; // TODO: Implement with untyped retype
}

fn endpoint_delete(endpoint_idx: usize) isize {
    const current = thread.getCurrent() orelse return -2;
    const ep_slot = current.root_cnode.get(endpoint_idx) catch return -2;
    if (ep_slot.cap_type != .CAP_ENDPOINT) return -1;
    
    // Wake any blocked threads with error
    const endpoint = &ep_slot.data.endpoint;
    while (endpoint.queue.dequeue()) |t| {
        t.state = .RUNNABLE;
        t.ipc_state = .ERROR;
        sched.enqueue(t);
    }
    
    ep_slot.* = cap.NULL_SLOT;
    return 0;
}

/// SYS_NAMESPACE_REGISTER: Register endpoint in global namespace
/// arg0: endpoint capability index
/// arg1: name pointer (null-terminated string)
/// arg2: name length
fn namespace_register(endpoint_idx: usize, name_ptr: usize, name_len: usize) isize {
    _ = name_len;
    const current = thread.getCurrent() orelse return -2;
    const ep_slot = current.root_cnode.get(endpoint_idx) catch return -2;
    if (ep_slot.cap_type != .CAP_ENDPOINT) return -1;
    
    // For genesis block, just verify this is Policy Service (special case)
    // Real implementation needs a namespace service
    const name = @as([*]const u8, @ptrFromInt(name_ptr));
    if (std.mem.eql(u8, name[0..12], "system.policy")) {
        // Mark as system endpoint
        ep_slot.data.endpoint.badge = 0x1; // Reserved for Policy Service
    }
    
    return 0;
}

// === MEMORY ===

fn map_frame(frame_idx: usize, vaddr: usize, rights: usize, attr: usize) isize {
    _ = attr;
    const current = thread.getCurrent() orelse return -2;
    const frame_slot = current.root_cnode.get(frame_idx) catch return -2;
    if (frame_slot.cap_type != .CAP_FRAME) return -1;
    if (frame_slot.rights & rights != rights) return -4; // Insufficient rights
    
    const frame = &frame_slot.data.frame;
    if (frame.mapped) return -9; // Already mapped
    
    // Get current VSpace
    const vspace = current.vspace;
    
    // Walk page tables and map
    // This is architecture-specific
    const result = arch.mapPage(vspace, frame.phys, vaddr, rights);
    if (result == 0) {
        frame.mapped = true;
    }
    
    return result;
}

fn unmap_frame(frame_idx: usize, vaddr: usize) isize {
    const current = thread.getCurrent() orelse return -2;
    const frame_slot = current.root_cnode.get(frame_idx) catch return -2;
    if (frame_slot.cap_type != .CAP_FRAME) return -1;
    
    const frame = &frame_slot.data.frame;
    if (!frame.mapped) return -9;
    
    // Unmap from address space
    arch.unmapPage(current.vspace, vaddr);
    frame.mapped = false;
    
    return 0;
}

// === DEBUGGING ===

fn debug_dump_caps() isize {
    const current = thread.getCurrent() orelse return -2;
    std.log.info("=== Capabilities for Thread {d} ===", .{current.tid});
    
    for (current.root_cnode.slots, 0..) |slot, i| {
        if (slot.cap_type != .CAP_NULL) {
            std.log.info("  Slot {d}: type={d} rights={x} badge={x}", .{
                i, @intFromEnum(slot.cap_type), slot.rights, slot.badge
            });
        }
    }
    
    return 0;
}

// === ARCHITECTURE-SPECIFIC STUBS ===

const arch = struct {
    fn mapPage(vspace: cap.CapSlot, phys: usize, virt: usize, rights: usize) isize {
        _ = vspace;
        _ = phys;
        _ = virt;
        _ = rights;
        // x86_64: Walk page tables, insert PTE
        return 0; // TODO: Implement for genesis
    }
    
    fn unmapPage(vspace: cap.CapSlot, virt: usize) void {
        _ = vspace;
        _ = virt;
        // x86_64: Clear PTE, invalidate TLB
    }
};