#![no_std]
#![no_main]

#[path = "../../../bindings/rust/kozo_abi.rs"]
mod abi;

use abi::{K_HANDLE, K_STATUS};

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {}
}

extern "C" {
    fn syscall_entry(id: u64, payload: *mut abi::HeartbeatPayload) -> u64;
}

fn invoke_heartbeat_bridge(
    syscall: abi::K_SYSCALL_ID,
    payload: &mut abi::HeartbeatPayload,
) -> abi::K_STATUS {
    unsafe { syscall_entry(u64::from(syscall), payload as *mut abi::HeartbeatPayload) as abi::K_STATUS }
}

fn assert_heartbeat_postconditions(payload: &abi::HeartbeatPayload) {
    debug_assert!(payload.sequence == 0xCAFEFEEE);
    debug_assert!(payload.timestamp == 0xDEADBEEF);
    debug_assert!(payload.status_bits == abi::K_OK);
}

pub fn heartbeat_request() -> abi::K_STATUS {
    let mut payload = abi::HeartbeatPayload {
        sequence: 0xCAFEFEED,
        timestamp: 0,
        status_bits: abi::K_INVALID,
    };
    let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_DEBUG_HEARTBEAT;

    let status = invoke_heartbeat_bridge(syscall, &mut payload);
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
