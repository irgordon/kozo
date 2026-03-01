const std = @import("std");
const thread = @import("../thread.zig");
const capability = @import("../capability.zig");
const scheduler = @import("../scheduler.zig");
const abi = @import("../abi.zig");

const arch_syscall = @import("../arch/x86_64/syscall.zig");

/// sys_call: Send a message and block until a reply is received.
/// RDI = endpoint_cap_idx, RSI = msg0, RDX = msg1, R10 = msg2
pub fn sys_call(ep_idx: usize, msg0: u64, msg1: u64, msg2: u64) isize {
    const caller = thread.getCurrent() orelse return -1;
    
    // 1. Lookup the Endpoint capability
    const ep_cap = caller.getCapability(ep_idx) orelse return abi.KOZO_ERR_NO_CAP;
    const ep = ep_cap.getEndpoint() orelse return abi.KOZO_ERR_INVALID;

    // 2. Fast Path: Is there a receiver waiting?
    if (ep.recv_queue.dequeue()) |server| {
        // DIRECT TRANSFER: 
        const server_frame = @as(*arch_syscall.SyscallFrame, @ptrFromInt(@intFromPtr(server.getSyscallFrame())));
        
        // Transfer 3 Message Words (RSI, RDX, R10 as per specification)
        server_frame.rax = 0; // KOZO_OK
        server_frame.rsi = msg0; 
        server_frame.rdx = msg1;
        server_frame.r10 = msg2;
        
        // Secure Badge Transfer (Caller ID) - Goes to RDI
        server_frame.rdi = ep_cap.badge; 
        
        // Block caller for reply
        caller.state = .BLOCKED_REPLY;
        
        // Wake up server
        server.state = .RUNNABLE;
        scheduler.enqueue(server);

        // Switch to reduce latency (Direct switch)
        scheduler.switchTo(server);
        return 0; 
    } else {
        // No receiver: Block caller on send queue
        caller.state = .BLOCKED_SEND;
        ep.send_queue.enqueue(caller);
        
        // Store the message and badge for later transfer
        const caller_frame = @as(*arch_syscall.SyscallFrame, @ptrFromInt(@intFromPtr(caller.getSyscallFrame())));
        caller_frame.rsi = msg0; 
        caller_frame.rdx = msg1;
        caller_frame.r10 = msg2;
        caller_frame.rbx = ep_cap.badge; 

        scheduler.yield();
        return 0;
    }
}

/// sys_reply_wait: Atomic Reply-then-Receive
/// client_tid: Who we are replying to
/// reply0, reply1, reply2: The 3-word message to the client
/// ep_idx: The endpoint to wait on for the next request
pub fn sys_reply_wait(client_tid: u32, reply0: u64, reply1: u64, reply2: u64, ep_idx: usize) isize {
    const server = thread.getCurrent() orelse return -1;
    
    // 1. Reply to Client
    if (thread.getTCBByTid(client_tid)) |client| {
        if (client.state == .BLOCKED_REPLY) {
            const client_frame = @as(*arch_syscall.SyscallFrame, @ptrFromInt(@intFromPtr(client.getSyscallFrame())));
            
            // Transfer 3 words back to client
            client_frame.rax = 0; // KOZO_OK
            client_frame.rsi = reply0;
            client_frame.rdx = reply1;
            client_frame.r10 = reply2;
            
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
        const server_frame = @as(*arch_syscall.SyscallFrame, @ptrFromInt(@intFromPtr(server.getSyscallFrame())));
        server_frame.rax = 0; // KOZO_OK
        server_frame.rsi = client_frame.rsi; // msg0
        server_frame.rdx = client_frame.rdx; // msg1
        server_frame.r10 = client_frame.r10; // msg2
        server_frame.rdi = client_frame.rbx; // Secure Badge
        
        next_client.state = .BLOCKED_REPLY;
        return 0; // Server continues directly in user-space
    } else {
        // No client: Block server on recv queue
        server.state = .BLOCKED_RECV;
        ep.recv_queue.enqueue(server);

        // Optional: Zero out server's message registers while waiting
        const server_frame = @as(*arch_syscall.SyscallFrame, @ptrFromInt(@intFromPtr(server.getSyscallFrame())));
        server_frame.rsi = 0;
        server_frame.rdx = 0;
        server_frame.r10 = 0;

        scheduler.yield();
        return 0;
    }
}
