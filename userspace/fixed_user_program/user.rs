#![cfg_attr(not(test), no_std)]

#[cfg(all(not(test), not(target_arch = "x86_64")))]
compile_error!("The fixed user program requires the governed x86-64 target");

#[allow(dead_code, non_camel_case_types)]
#[path = "../../bindings/rust/kozo_abi.rs"]
mod abi;

use core::ptr::{read_volatile, write_volatile};

const REQUEST: usize = 0x0000_4000_0000_1000;
const RESPONSE: usize = 0x0000_4000_0000_1080;
const CONSUMPTION: usize = 0x0000_4000_0000_1100;
const ARGUMENT_SCRATCH: usize = 0x0000_4000_0000_1130;
const ARGUMENT: u64 = 7;
const WIRE_VERSION: u64 = 2;
const REQUEST_ID: u64 = 2;
const REQUEST_BYTES: u64 = 40;
const RESPONSE_BYTES: u64 = 96;
const SEQUENCE: u64 = 1;
const INVALID: u32 = 1;

#[no_mangle]
pub unsafe extern "C" fn kozo_rust_user_request_entry() -> u32 {
    if !at_cpl3() {
        return INVALID;
    }
    #[cfg(kozo_fault_fixture)]
    fault_fixture_request();
    construct_request();
    abi::K_OK
}

#[no_mangle]
pub unsafe extern "C" fn kozo_rust_user_response_entry() -> u32 {
    if !at_cpl3() {
        return INVALID;
    }
    #[cfg(kozo_fault_fixture)]
    fault_fixture_response();
    let response = read_response();
    let argument = read_argument_scratch();
    if !response_is_valid(&response, argument) {
        return INVALID;
    }
    write_consumption(consumption_words(&response));
    abi::K_OK
}

#[inline(always)]
unsafe fn construct_request() {
    let words = request_words(ARGUMENT);
    for index in 0..5 {
        write_volatile((REQUEST as *mut u64).add(index), words[index]);
    }
    write_volatile(ARGUMENT_SCRATCH as *mut u64, ARGUMENT);
}

#[inline(always)]
fn request_words(argument: u64) -> [u64; 5] {
    [WIRE_VERSION | (REQUEST_ID << 32), REQUEST_BYTES | (RESPONSE_BYTES << 32),
     SEQUENCE, argument, 0]
}

#[inline(always)]
unsafe fn read_response() -> [u64; 12] {
    let mut words = [0; 12];
    for index in 0..12 {
        words[index] = read_volatile((RESPONSE as *const u64).add(index));
    }
    words
}

#[inline(always)]
unsafe fn read_argument_scratch() -> u64 {
    read_volatile(ARGUMENT_SCRATCH as *const u64)
}

#[inline(always)]
fn response_is_valid(words: &[u64; 12], argument: u64) -> bool {
    if argument > 65535 {
        return false;
    }
    words[0] == WIRE_VERSION | (REQUEST_ID << 32)
        && words[1] == (RESPONSE_BYTES << 32) | u64::from(abi::K_OK)
        && words[2] == SEQUENCE
        && words[3] == 5
        && words[4] == 63
        && words[5] == 4096
        && words[6] == 3
        && words[7] == 3
        && words[8] == 6
        && words[9] == 127
        && words[10] == 0
        && words[11] == argument + 1
}

#[inline(always)]
fn consumption_words(response: &[u64; 12]) -> [u64; 6] {
    let digest = response.iter().fold(0, |digest, word| digest ^ word);
    [1 | (1 << 32), 48, response[2], response[4], digest, 0]
}

#[inline(always)]
unsafe fn write_consumption(words: [u64; 6]) {
    for index in 0..6 {
        write_volatile((CONSUMPTION as *mut u64).add(index), words[index]);
    }
}

#[inline(always)]
#[cfg(target_arch = "x86_64")]
unsafe fn at_cpl3() -> bool {
    let selector: u16;
    core::arch::asm!("mov {selector:x}, cs", selector = out(reg) selector,
                     options(nomem, nostack, preserves_flags));
    selector & 3 == 3
}

#[cfg(kozo_fault_fixture)]
#[inline(always)]
unsafe fn fault_fixture_request() {
    let selector = read_volatile((ARGUMENT_SCRATCH + 8) as *const u8);
    if selector == 1 {
        kozo_rust_user_fault_probe();
    }
}

#[cfg(kozo_fault_fixture)]
#[inline(always)]
unsafe fn fault_fixture_response() {
    let selector = read_volatile((ARGUMENT_SCRATCH + 8) as *const u8);
    if selector == 2 {
        kozo_rust_user_fault_probe();
    }
}

#[cfg(kozo_fault_fixture)]
#[inline(never)]
unsafe extern "C" fn kozo_rust_user_fault_probe() -> ! {
    #[cfg(kozo_fault_bad_rsp)]
    core::arch::asm!("push 0");
    core::arch::asm!(
        ".if {control} == 33", "push 0x12", ".else", "push 2", ".endif", "popfq",
        ".if {control} != 0 && {control} != 7 && {control} != 33", "jmp 3f", ".endif",
        ".global kozo_rust_user_fault_site",
        ".set kozo_rust_user_fault_site, 2f",
        "2:",
        ".if {control} == 7", ".byte 0x0f, 0xb9, 0xc0",
        ".else", "ud2", ".endif",
        "3:",
        ".if {control} == 19", "int 6",
        ".elseif {control} == 20", "xor eax, eax", "mov rax, [rax]",
        ".else", "ud2", ".endif",
        control = const FAULT_CONTROL_INSTRUCTION,
        options(noreturn)
    );
}

#[cfg(all(kozo_fault_fixture, kozo_fault_bad_rip))]
const FAULT_CONTROL_INSTRUCTION: usize = 6;
#[cfg(all(kozo_fault_fixture, kozo_fault_int6))]
const FAULT_CONTROL_INSTRUCTION: usize = 19;
#[cfg(all(kozo_fault_fixture, kozo_fault_pf))]
const FAULT_CONTROL_INSTRUCTION: usize = 20;
#[cfg(all(kozo_fault_fixture, kozo_fault_bad_bytes))]
const FAULT_CONTROL_INSTRUCTION: usize = 7;
#[cfg(all(kozo_fault_fixture, kozo_fault_rflags_bit4))]
const FAULT_CONTROL_INSTRUCTION: usize = 33;
#[cfg(all(kozo_fault_fixture, not(any(kozo_fault_bad_rip, kozo_fault_int6, kozo_fault_pf, kozo_fault_bad_bytes, kozo_fault_rflags_bit4))))]
const FAULT_CONTROL_INSTRUCTION: usize = 0;

// Native non-x86 tests exercise pure wire policy, never guest privilege evidence.
#[cfg(all(test, not(target_arch = "x86_64")))]
unsafe fn at_cpl3() -> bool {
    false
}

#[cfg(not(test))]
#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    unsafe { core::arch::asm!("ud2", options(noreturn)) }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn response(argument: u64) -> [u64; 12] {
        [2 | (2 << 32), 96 << 32, 1, 5, 63, 4096, 3, 3, 6, 127, 0, argument + 1]
    }

    #[test]
    fn request_has_exact_wire_fields() {
        assert_eq!(request_words(7), [2 | (2 << 32), 40 | (96 << 32), 1, 7, 0]);
    }

    #[test]
    fn every_response_qword_is_required() {
        for argument in [0, 7, 65535] {
            let valid = response(argument);
            assert!(response_is_valid(&valid, argument));
            for index in 0..12 {
                let mut corrupted = valid;
                corrupted[index] ^= 1;
                assert!(!response_is_valid(&corrupted, argument));
            }
        }
        assert!(!response_is_valid(&response(7), 65536));
        assert!(!response_is_valid(&response(7), u64::MAX));
    }

    #[test]
    fn digest_covers_result_and_record_is_six_qwords() {
        let valid = response(7);
        let mut corrupted = valid;
        corrupted[11] ^= 1;
        assert_ne!(consumption_words(&valid)[4], consumption_words(&corrupted)[4]);
        let record = consumption_words(&valid);
        assert_eq!(core::mem::size_of_val(&record), 48);
        assert_eq!([record[0], record[1], record[2], record[3], record[5]],
                   [1 | (1 << 32), 48, 1, 63, 0]);
    }
}
