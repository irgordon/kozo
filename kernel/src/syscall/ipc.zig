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
    const ep_idx = frame.rdi; // First arg: Endpoint Capability Index
    
    // 1. Lookup the Endpoint capability
    const ep_cap = caller.getCapability(ep_idx) orelse return abi.KOZO_ERR_NO_CAP;
    const ep = ep_cap.getEndpoint() orelse return abi.KOZO_ERR_INVALID;

    // 2. Direct Transfer Path (Server is already waiting)
    if (ep.recv_queue.dequeue()) |server| {
        // Find the server's saved SyscallFrame on its own stack
        const server_frame = @as(*arch_syscall.SyscallFrame, @ptrFromInt(@intFromPtr(server.getSyscallFrame())));
        
        // DATA TRANSFER: Move 3 words directly register-to-register
        server_frame.rax = 0;           // KOZO_OK
        server_frame.rsi = frame.rsi;   // Message Word 0
        server_frame.rdx = frame.rdx;   // Message Word 1
        server_frame.r10 = frame.r10;   // Message Word 2
        
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
        
        // The message and badge stay in the caller's SyscallFrame on their kernel stack.
        // We temporarily store the badge in RBX (scrubbed on return anyway)
        frame.rbx = ep_cap.badge; 

        scheduler.yield();
        return 0;
    }
}

/// sys_reply_wait: Atomic Reply-then-Receive
pub fn sys_reply_wait(frame: *arch_syscall.SyscallFrame) isize {
    const server = thread.getCurrent() orelse return -1;
    const client_tid: u32 = @intCast(frame.rdi);
    const ep_idx = frame.r10; // In reply_wait, R10 is the endpoint to wait on
    
    // 1. Reply to Client
    if (thread.getTCBByTid(client_tid)) |client| {
        if (client.state == .BLOCKED_REPLY) {
            const client_frame = @as(*arch_syscall.SyscallFrame, @ptrFromInt(@intFromPtr(client.getSyscallFrame())));
            
            // Transfer 3 words back to client (RSI, RDX, R10 from server's frame)
            client_frame.rax = 0; // KOZO_OK
            client_frame.rsi = frame.rsi;
            client_frame.rdx = frame.rdx;
            client_frame.r10 = frame.r8; // Note: using R8 for reply2 to avoid collision with ep_idx
            
            client.state = .RUNNABLE;
            scheduler.enqueue(client);
        }
    }

    // 2. Wait for next request
    const ep_cap = server.getCapability(ep_idx) orelse return abi.KOZO_ERR_NO_CAP;
    const ep = ep_cap.getEndpoint() orelse return abi.KOZO_ERR_INVALID;

    if (ep.send_queue.dequeue()) |next_client| {
        // Immediate next message (Fast path)
        const client_frame = @as(*arch_syscall.SyscallFrame, @ptrFromInt(@intFromPtr(next_client.getSyscallFrame())));
        
        // Transfer into server's frame
        frame.rax = 0; // KOZO_OK
        frame.rsi = client_frame.rsi; // msg0
        frame.rdx = client_frame.rdx; // msg1
        frame.r10 = client_frame.r10; // msg2
        frame.rdi = client_frame.rbx; // Secure Badge
        
        next_client.state = .BLOCKED_REPLY;
        return 0; // Server continues directly in user-space
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
