const std = @import("std");
const thread = @import("../thread.zig");
const capability = @import("../capability.zig");
const scheduler = @import("../scheduler.zig");
const abi = @import("../abi.zig");

const arch_syscall = @import("../arch/x86_64/syscall.zig");

/// sys_call: Send a message and block until a reply is received.
/// The kernel moves data directly between the caller's frame and the receiver's frame.
pub fn sys_call(frame: *arch_syscall.SyscallFrame) isize {
    const caller = thread.getCurrent() orelse return -1;
    const ep_idx = frame.rdi; // Client RDI = Target Endpoint Index
    
    // 1. Lookup the Endpoint capability
    const ep_cap = caller.getCapability(ep_idx) orelse return abi.KOZO_ERR_NO_CAP;
    const ep = ep_cap.getEndpoint() orelse return abi.KOZO_ERR_INVALID;

    // 2. Direct Transfer Path (Server is already waiting)
    if (ep.recv_queue.dequeue()) |server| {
        // Find the server's saved SyscallFrame on its own stack
        const server_frame = @as(*arch_syscall.SyscallFrame, @ptrFromInt(@intFromPtr(server.getSyscallFrame())));
        
        // DATA TRANSFER: Move 3 words directly register-to-register (M0, M1, M2)
        server_frame.rax = 0;           // KOZO_OK
        server_frame.rsi = frame.rsi;   // New Msg Word 0
        server_frame.rdx = frame.rdx;   // New Msg Word 1
        server_frame.r10 = frame.r10;   // New Msg Word 2
        
        // IDENTITY: Inject the caller's secure badge into server's RDI
        server_frame.rdi = ep_cap.badge; 
        
        // SUCCESS: Receiver is now runnable
        server.state = .RUNNABLE;
        scheduler.enqueue(server);

        // BLOCK: Caller waits for the reply
        caller.state = .BLOCKED_REPLY;
        frame.rax = 0; // Success for the sys_call invocation itself
        
        // SWITCH: Direct handover to server to minimize latency
        scheduler.switchTo(server);
        return 0; 
    } else {
        // No receiver: Block caller on send queue
        caller.state = .BLOCKED_SEND;
        ep.send_queue.enqueue(caller);
        
        // The message (RSI, RDX, R10) and badge (RBX) stay in the caller's SyscallFrame.
        frame.rbx = ep_cap.badge; 

        scheduler.yield();
        return 0;
    }
}

/// sys_reply_wait: Atomic Reply-then-Receive
pub fn sys_reply_wait(frame: *arch_syscall.SyscallFrame) isize {
    const server = thread.getCurrent() orelse return -1;
    const client_tid: u32 = @intCast(frame.rdi); // In: Client TID to reply to
    const ep_idx = frame.rsi;                   // In: Endpoint index to wait on
    
    // --- STEP 1: THE REPLY ---
    if (client_tid != 0) {
        if (thread.getTCBByTid(client_tid)) |client| {
            if (client.state == .BLOCKED_REPLY) {
                const client_frame = @as(*arch_syscall.SyscallFrame, @ptrFromInt(@intFromPtr(client.getSyscallFrame())));
                
                // DATA TRANSFER: 2-word reply back to client (from server's RDX, R10)
                client_frame.rax = 0;           // KOZO_OK
                client_frame.rsi = frame.rdx;   // Reply Word 0 -> Client RSI
                client_frame.rdx = frame.r10;   // Reply Word 1 -> Client RDX
                
                client.state = .RUNNABLE;
                scheduler.enqueue(client);
            }
        }
    }

    // --- STEP 2: THE WAIT ---
    const ep_cap = server.getCapability(ep_idx) orelse return abi.KOZO_ERR_NO_CAP;
    const ep = ep_cap.getEndpoint() orelse return abi.KOZO_ERR_INVALID;

    if (ep.send_queue.dequeue()) |next_client| {
        // FAST PATH: A new client is already waiting!
        const next_frame = @as(*arch_syscall.SyscallFrame, @ptrFromInt(@intFromPtr(next_client.getSyscallFrame())));
        
        // DATA TRANSFER: 3-word transfer into server context (M0, M1, M2)
        frame.rax = 0;               // KOZO_OK
        frame.rsi = next_frame.rsi;   // New Msg Word 0
        frame.rdx = next_frame.rdx;   // New Msg Word 1
        frame.r10 = next_frame.r10;   // New Msg Word 2
        
        // IDENTITY: Inject secure Badge into Server's RDI
        frame.rdi = ep_cap.badge;

        // Block the client for its reply later
        next_client.state = .BLOCKED_REPLY;
        return 0; // Direct return to server in user-space
    } else {
        // No client: Block server on recv queue
        server.state = .BLOCKED_RECV;
        ep.recv_queue.enqueue(server);

        // Scrub server's message registers while waiting
        frame.rsi = 0;
        frame.rdx = 0;
        frame.r10 = 0;

        scheduler.yield();
        return 0;
    }
}
