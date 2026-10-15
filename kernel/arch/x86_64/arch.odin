package x86_64

import abi "../../../bindings/odin"

@require foreign import hardware_bridge "syscall.asm"

foreign hardware_bridge {
	x86_read_timestamp :: proc "c" () -> u64 ---
	x86_halt :: proc "c" () ---
	x86_outb :: proc "c" (port: u16, value: u8) ---
	x86_inb :: proc "c" (port: u16) -> u8 ---
}

bootstrap :: proc() -> abi.K_STATUS {
	return serial_init()
}

read_timestamp :: proc "contextless"() -> u64 {
	when ODIN_ARCH == .amd64 {
		return x86_read_timestamp()
	}
	return 0
}

halt :: proc "contextless" () {
	when ODIN_ARCH == .amd64 {
		x86_halt()
		return
	}
}
