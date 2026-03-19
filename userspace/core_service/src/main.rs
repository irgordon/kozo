#![no_std]
#![no_main]

#[path = "../../../bindings/rust/kozo_abi.rs"]
mod abi;

use abi::{K_HANDLE, K_STATUS};

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {}
}

// KOZO: STUB MODE — no real syscall boundary
fn invoke_heartbeat_stub(syscall: abi::K_SYSCALL_ID, payload: &mut abi::HeartbeatPayload) -> abi::K_STATUS {
    if syscall != abi::K_SYSCALL_DEBUG_HEARTBEAT {
        return abi::K_INVALID;
    }
    if payload.sequence != 0xCAFEFEED {
        return abi::K_INVALID;
    }
    payload.sequence = 0xCAFEFEEE;
    payload.timestamp = 0xDEADBEEF;
    abi::K_OK
}

fn assert_heartbeat_postconditions(payload: &abi::HeartbeatPayload) {
    debug_assert!(payload.sequence == 0xCAFEFEEE);
    debug_assert!(payload.timestamp == 0xDEADBEEF);
}

pub fn heartbeat_request() -> abi::K_STATUS {
    let mut payload = abi::HeartbeatPayload {
        sequence: 0xCAFEFEED,
        timestamp: 0,
        status_bits: abi::K_INVALID,
    };
    let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_DEBUG_HEARTBEAT;
    let payload_handle = (&mut payload as *mut abi::HeartbeatPayload as usize) as abi::K_HANDLE;
    let _ = payload_handle;

    let status = invoke_heartbeat_stub(syscall, &mut payload);
    match status {
        abi::K_OK => {
            assert_heartbeat_postconditions(&payload);
            abi::K_OK
        }
        _ => panic!("heartbeat syscall returned non-K_OK"),
    }
}

#[no_mangle]
pub extern "C" fn core_service_entry(handle: K_HANDLE) -> K_STATUS {
    let _ = handle;
    heartbeat_request()
}
