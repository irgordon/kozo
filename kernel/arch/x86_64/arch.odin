package x86_64

import kozo_abi "../../../bindings/odin"

bootstrap :: proc() -> kozo_abi.K_STATUS {
	return serial_init()
}

halt :: proc "contextless" () {
	_ = asm #side_effects #intel {
		"hlt",
		""
	}
}
