package x86_64

import abi "../../../bindings/odin"

bootstrap :: proc() -> abi.K_STATUS {
	return serial_init()
}

read_timestamp :: proc "contextless"() -> u64 {
	return asm() -> u64 #side_effects #intel {
		"rdtsc; shl rdx, 32; or rax, rdx",
		"={ax}"
	}()
}

halt :: proc "contextless" () {
	_ = asm #side_effects #intel {
		"hlt",
		""
	}
}
