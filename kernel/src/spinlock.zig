//! KOZO Kernel - Spinlock
//! File Path: kernel/src/spinlock.zig
//! Responsibility: Minimal spinlock for kernel synchronization

/// Simple spinlock using x86 pause instruction
pub const SpinLock = struct {
    locked: u32,
    
    pub fn init() SpinLock {
        return .{ .locked = 0 };
    }
    
    /// Acquire lock, disabling interrupts
    /// Returns previous interrupt state
    pub fn lock(self: *SpinLock) u64 {
        // Disable interrupts and save previous state
        const flags = saveFlagsAndCli();
        
        // Spin until we acquire the lock
        while (@atomicRmw(u32, &self.locked, .Xchg, 1, .acquire) != 0) {
            // Pause instruction to reduce power/thermal in spin loop
            asm volatile ("pause");
        }
        
        return flags;
    }
    
    /// Release lock, restoring interrupt state
    pub fn unlock(self: *SpinLock, flags: u64) void {
        @atomicStore(u32, &self.locked, 0, .release);
        restoreFlags(flags);
    }
};

/// Save RFLAGS and disable interrupts
fn saveFlagsAndCli() u64 {
    var flags: u64 = undefined;
    asm volatile (
        \\pushfq
        \\popq %[flags]
        \\cli
        : [flags] "=r" (flags)
        :
        : "memory"
    );
    return flags;
}

/// Restore RFLAGS (including interrupt enable)
fn restoreFlags(flags: u64) void {
    asm volatile (
        \\pushq %[flags]
        \\popfq
        :
        : [flags] "r" (flags)
        : "memory", "cc"
    );
}
