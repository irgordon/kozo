//! KOZO Init Service - Bootstrap Process (Tier 1)
//! File Path: services/init/src/main.rs
//! Responsibility: First user process, capability bootstrap, spawns Policy Service
//! Depends on: services/kozo-sys/src/abi.rs (Generated), services/kozo-sys/src/lib.rs

#![no_std]
#![no_main]

use kozo_sys::{Syscall, CapType, Rights, Error}; // From: services/kozo-sys/src/abi.rs (Generated)

/// BootInfo structure provided by the Zig Kernel via register/pass
/// File Path: kernel/src/boot.zig (Zig side definition)
#[repr(C)]
pub struct BootInfo {
    untyped_base: usize,      // Physical address of initial untyped memory
    untyped_size: usize,      // Size of initial untyped pool (16MB typical)
    root_cnode_ptr: usize,    // Root CNode capability address
    kernel_info_offset: usize, // Offset to kernel boot info page
}

#[no_mangle]
pub extern "C" fn _start(info: &BootInfo) -> ! {
    main(info)
}

fn main(info: &BootInfo) -> ! {
    debug_print("INIT: KOZO 0.0.1-dev bootstrap starting...\n");
    debug_print("INIT: Untyped pool at 0x");
    debug_print_hex(info.untyped_base);
    debug_print(", size 0x");
    debug_print_hex(info.untyped_size);
    debug_print("\n");

    // === STEP 1: Create Policy Service CNode ===
    // Retype Untyped memory (Slot 0) into a CNode for Policy Service
    // This gives Policy Service its own capability table (1024 slots)
    let policy_cnode_slot = 1;
    let cnode_size_bits = 10; // 2^10 = 1024 slots
    
    debug_print("INIT: Retyping Untyped -> CNode for Policy Service...\n");
    
    let res = unsafe {
        syscall4(
            Syscall::Retype as usize,
            0,                      // Source: Initial Untyped Cap (Slot 0)
            CapType::Cnode as usize, // New Type: CNode
            policy_cnode_slot,       // Dest slot in Root CNode
            cnode_size_bits,         // Size: 1024 slots
        )
    };

    if res < 0 {
        debug_print("INIT: FATAL - Failed to retype memory for Policy CNode\n");
        debug_print("Error code: ");
        debug_print_dec(res as i64);
        loop {} // Halt - cannot recover
    }

    debug_print("INIT: Policy CNode created at slot ");
    debug_print_dec(policy_cnode_slot as i64);
    debug_print("\n");

    // === STEP 2: Create Policy Service Endpoint ===
    // Create an IPC endpoint that Policy Service will listen on
    let policy_ep_slot = 2;
    
    let res2 = unsafe {
        syscall4(
            Syscall::Retype as usize,
            0,                         // Source: Untyped
            CapType::Endpoint as usize, // New Type: Endpoint
            policy_ep_slot,            // Dest slot
            0,                         // Size: 0 (endpoints are fixed size)
        )
    };

    if res2 < 0 {
        debug_print("INIT: FATAL - Failed to create Policy Endpoint\n");
        loop {}
    }

    debug_print("INIT: Policy Endpoint created at slot ");
    debug_print_dec(policy_ep_slot as i64);
    debug_print("\n");

    // === STEP 3: Transfer Endpoint to Policy Service CNode ===
    // Move the endpoint capability into Policy's CNode (slot 0)
    let res3 = unsafe {
        syscall4(
            Syscall::CapTransfer as usize,
            policy_ep_slot,           // Source: our slot 2
            policy_cnode_slot,        // Dest CNode: Policy's CNode
            0,                        // Dest slot: 0 in Policy's CNode
            Rights::RIGHT_READ | Rights::RIGHT_WRITE | Rights::RIGHT_GRANT,
        )
    };

    if res3 < 0 {
        debug_print("INIT: FATAL - Failed to transfer endpoint to Policy\n");
        loop {}
    }

    // Delete our reference to the endpoint (Policy now owns it)
    unsafe {
        syscall2(
            Syscall::CapDelete as usize,
            policy_ep_slot,
            0, // flags
        );
    }

    debug_print("INIT: Endpoint transferred to Policy Service\n");

    // === STEP 4: Create Thread for Policy Service ===
    // For genesis, we create a thread that will execute the Policy Service
    // In reality, we'd load the binary from initrd here
    debug_print("INIT: Spawning Policy Service thread...\n");
    
    // TODO: Load Policy Service binary from initrd (zig-out/initrd.cpio)
    // For smoke test, we just prove the capability structure is set up

    // === STEP 5: Signal Ready and Wait ===
    debug_print("INIT: Bootstrap complete. System ready.\n");
    debug_print("Init> ");

    // Idle loop - in full implementation, we'd become the service manager
    // receiving requests via our own endpoint
    loop {
        // Halt until interrupt (wait for work)
        unsafe { core::arch::asm!("hlt"); }
    }
}

// === Syscall Wrappers ===

unsafe fn syscall4(n: usize, a1: usize, a2: usize, a3: usize, a4: usize) -> isize {
    let ret: isize;
    core::arch::asm!(
        "syscall",
        in("rax") n,
        in("rdi") a1,
        in("rsi") a2,
        in("rdx") a3,
        in("r10") a4,
        lateout("rax") ret,
        out("rcx") _, out("r11") _,
        options(nostack, preserves_flags)
    );
    ret
}

unsafe fn syscall2(n: usize, a1: usize, a2: usize) -> isize {
    let ret: isize;
    core::arch::asm!(
        "syscall",
        in("rax") n,
        in("rdi") a1,
        in("rsi") a2,
        lateout("rax") ret,
        out("rcx") _, out("r11") _,
        options(nostack, preserves_flags)
    );
    ret
}

// === Debug Output ===

fn debug_print(s: &str) {
    for c in s.bytes() {
        unsafe { 
            syscall1(Syscall::DebugPutchar as usize, c as usize);
        }
    }
}

fn debug_print_hex(n: usize) {
    const HEX_DIGITS: &[u8] = b"0123456789ABCDEF";
    let mut buf = [0u8; 16];
    for i in (0..16).rev() {
        buf[i] = HEX_DIGITS[(n >> (i * 4)) & 0xF];
    }
    for c in buf {
        unsafe {
            syscall1(Syscall::DebugPutchar as usize, c as usize);
        }
    }
}

fn debug_print_dec(n: i64) {
    if n < 0 {
        unsafe { syscall1(Syscall::DebugPutchar as usize, b'-' as usize); }
        return debug_print_dec(-n);
    }
    if n >= 10 {
        debug_print_dec(n / 10);
    }
    unsafe {
        syscall1(Syscall::DebugPutchar as usize, (b'0' + (n % 10) as u8) as usize);
    }
}

unsafe fn syscall1(n: usize, a1: usize) -> isize {
    let ret: isize;
    core::arch::asm!(
        "syscall",
        in("rax") n,
        in("rdi") a1,
        lateout("rax") ret,
        out("rcx") _, out("r11") _,
        options(nostack, preserves_flags)
    );
    ret
}

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    debug_print("\nINIT PANIC!\n");
    loop {}
}