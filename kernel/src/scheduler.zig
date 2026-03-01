// File Path: kernel/src/scheduler.zig
// Last Modified: 2026-03-01, 10:20:15.110
// Note: Refined Scheduler - Implements stack-based context switching and CR3 handling.

const std = @import("std");
const thread = @import("thread.zig");
const gdt = @import("arch/x86_64/gdt.zig");

// External assembly function
// void switch_context(uint64_t* old_stack, uint64_t new_stack, uint64_t new_cr3)
extern fn switch_context(current_stack: *u64, next_stack: u64, next_cr3: u64) void;

// Scratch area for syscall entry
extern var kernel_rsp_scratch: u64;

/// Run queue - simple singly-linked list via TCB.next
var runqueue_head: ?*thread.TCB = null;
var runqueue_tail: ?*thread.TCB = null;

/// The special Idle Thread
var idle_thread: *thread.TCB = undefined;
var idle_stack: [1024]u8 align(16) = undefined;

fn idleLoop() noreturn {
    while (true) {
        asm volatile ("hlt");
    }
}

/// Initialize scheduler
pub fn init() void {
    runqueue_head = null;
    runqueue_tail = null;
    thread.init();  // Initialize TCB pool

    // Initialize the Idle Thread
    // We allocate it like a normal thread but set priority 255.
    idle_thread = thread.allocTCB() orelse @panic("Failed to allocate Idle TCB");
    idle_thread.priority = 255;
    
    // Allocate a dedicated stack for the Idle thread
    const idle_stack = pmm.allocFrame() catch @panic("Failed to allocate Idle stack");
    const idle_stack_top = (idle_stack + 4096);
    
    // Idle is a kernel thread, so user_stack and kernel_stack are the same top.
    idle_thread.setupThread(@intFromPtr(&idle_loop), idle_stack_top, idle_stack_top, false);
    
    enqueue(idle_thread);
}

/// Add thread to run queue (append to tail)
pub fn enqueue(tcb: *thread.TCB) void {
    tcb.state = .RUNNABLE;
    tcb.next = null;
    
    if (runqueue_tail) |tail| {
        tail.next = tcb;
    } else {
        runqueue_head = tcb;
    }
    runqueue_tail = tcb;
}

/// Remove and return next runnable thread
pub fn dequeue() ?*thread.TCB {
    const tcb = runqueue_head orelse return null;
    
    runqueue_head = tcb.next;
    if (runqueue_head == null) {
        runqueue_tail = null;
    }
    
    tcb.next = null;
    return tcb;
}

/// Helper to create and enqueue a new thread
pub fn spawnThread(entry: u64, stack_top: u64, cr3: u64, priority: u8) !*thread.TCB {
    const tcb = thread.allocTCB() orelse return error.NoTCB;
    tcb.cr3 = cr3;
    tcb.priority = priority;
    // For spawned processes, stack_top is used for both User and Kernel stacks (temporarily)
    tcb.setupThread(entry, stack_top, stack_top, true);
    enqueue(tcb);
    return tcb;
}

/// Yield CPU to next runnable thread
pub fn yield() void {
    const current = thread.getCurrent() orelse return;
    const next = dequeue() orelse {
        // If state is still RUNNING or RUNNABLE, we just continue
        if (current.state == .RUNNING or current.state == .RUNNABLE) return;
        // Otherwise, we MUST switch to something else (Idle)
        const idle = getIdleThread();
        switchAway(current, idle);
        return;
    };

    // Only re-enqueue if we are still runnable (didn't block ourselves)
    if (current.state == .RUNNING or current.state == .RUNNABLE) {
        current.state = .RUNNABLE;
        enqueue(current);
    }

    switchAway(current, next);
}

fn switchAway(current: *thread.TCB, next: *thread.TCB) void {
    next.state = .RUNNING;
    thread.setCurrent(next);
    gdt.setKernelStack(next.stack_top);
    kernel_rsp_scratch = next.stack_top;

    // Perform the stack-based swap and CR3 update
    switch_context(&current.stack_ptr, next.stack_ptr, next.cr3);
}

fn getIdleThread() *thread.TCB {
    return idle_thread;
}

/// Switch to specific thread (e.g., for IPC return or first bootstrap)
pub fn switchTo(next: *thread.TCB) void {
    const current = thread.getCurrent();
    
    next.state = .RUNNING;
    thread.setCurrent(next);
    gdt.setKernelStack(next.stack_top);
    kernel_rsp_scratch = next.stack_top;

    if (current) |p| {
        switch_context(&p.stack_ptr, next.stack_ptr, next.cr3);
    } else {
        // Bootstrap: First thread execution
        // We manually switch address space and stack
        if (next.cr3 != 0) {
            asm volatile ("mov %[cr3], %%cr3" : : [cr3] "r" (next.cr3) : "memory");
        }
        
        asm volatile (
            \\movq %[rsp], %%rsp
            \\popq %%r15
            \\popq %%r14
            \\popq %%r13
            \\popq %%r12
            \\popq %%rbx
            \\popq %%rbp
            \\iretq
            :
            : [rsp] "r" (next.stack_ptr)
            : "memory"
        );
        unreachable;
    }
}

/// Block current thread (mark BLOCKED and switch away)
pub fn block() void {
    const current = thread.getCurrent() orelse return;
    current.state = .BLOCKED;
    
    const next = dequeue() orelse idle_thread;
    next.state = .RUNNING;
    thread.setCurrent(next);
    gdt.setKernelStack(next.stack_top);
    kernel_rsp_scratch = next.stack_top;
    
    switch_context(&current.stack_ptr, next.stack_ptr, next.cr3);
}

/// Unblock thread
pub fn unblock(tcb: *thread.TCB) void {
    if (tcb.state == .BLOCKED) {
        enqueue(tcb);
    }
}
