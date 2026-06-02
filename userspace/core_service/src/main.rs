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

fn invoke_no_payload_bridge(syscall: abi::K_SYSCALL_ID) -> abi::K_STATUS {
    unsafe { syscall_entry(u64::from(syscall), core::ptr::null_mut()) as abi::K_STATUS }
}

fn fail_heartbeat_contract() -> ! {
    panic!("heartbeat return path contract violated")
}

fn fail_nop_contract() -> ! {
    panic!("nop return path contract violated")
}

fn fail_status_contract() -> ! {
    panic!("status return path contract violated")
}

fn validate_heartbeat_return_path(
    status: abi::K_STATUS,
    payload: &abi::HeartbeatPayload,
) -> abi::K_STATUS {
    if status != abi::K_OK {
        fail_heartbeat_contract();
    }
    if payload.sequence != 0xCAFEFEEE {
        fail_heartbeat_contract();
    }
    if payload.timestamp != 0xDEADBEEF {
        fail_heartbeat_contract();
    }
    if payload.status_bits != abi::K_OK {
        fail_heartbeat_contract();
    }
    abi::K_OK
}

fn validate_nop_return_status(status: abi::K_STATUS) -> abi::K_STATUS {
    if status != abi::K_OK {
        fail_nop_contract();
    }
    abi::K_OK
}

fn validate_status_return_status(status: abi::K_STATUS) -> abi::K_STATUS {
    if status != abi::K_OK {
        fail_status_contract();
    }
    abi::K_OK
}

pub fn nop_request() -> abi::K_STATUS {
    let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_NOP;
    let status = invoke_no_payload_bridge(syscall);
    return validate_nop_return_status(status);
}

pub fn status_request() -> abi::K_STATUS {
    let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_STATUS;
    let status = invoke_no_payload_bridge(syscall);
    return validate_status_return_status(status);
}

pub fn heartbeat_request() -> abi::K_STATUS {
    let mut payload = abi::HeartbeatPayload {
        sequence: 0xCAFEFEED,
        timestamp: 0,
        status_bits: abi::K_INVALID,
    };
    let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_DEBUG_HEARTBEAT;

    let status = invoke_heartbeat_bridge(syscall, &mut payload);
    return validate_heartbeat_return_path(status, &payload);
}

#[no_mangle]
pub extern "C" fn core_service_entry(handle: K_HANDLE) -> K_STATUS {
    let _ = handle;
    let _ = nop_request();
    let _ = status_request();
    heartbeat_request()
}
