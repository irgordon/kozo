// kernel/src/main.zig
// Last Modified: 2026-02-28, 21:03:12.112

const VgaColor = enum(u8) {
    Black = 0,
    Blue = 1,
    Green = 2,
    Cyan = 3,
    Red = 4,
    Magenta = 5,
    Brown = 6,
    LightGray = 7,
    DarkGray = 8,
    LightBlue = 9,
    LightGreen = 10,
    LightCyan = 11,
    LightRed = 12,
    Pink = 13,
    Yellow = 14,
    White = 15,
};

const VgaWriter = struct {
    buffer: [*]volatile u16,
    cursor: usize,

    pub fn init(phys_addr: usize) VgaWriter {
        return .{
            .buffer = @ptrFromInt(phys_addr),
            .cursor = 0,
        };
    }

    pub fn putChar(self: *VgaWriter, char: u8, fg: VgaColor, bg: VgaColor) void {
        const color = (@as(u16, @intFromEnum(bg)) << 12) | (@as(u16, @intFromEnum(fg)) << 8);
        self.buffer[self.cursor] = color | char;
        self.cursor += 1;
    }

    pub fn write(self: *VgaWriter, text: []const u8, fg: VgaColor, bg: VgaColor) void {
        for (text) |c| {
            self.putChar(c, fg, bg);
        }
    }
};

// Required for linking, even if unused in Genesis
export fn trap_dispatch(_: u64) void {}
export fn kozo_syscall_handler(_: usize, _: usize, _: usize, _: usize, _: usize, _: usize, _: usize) isize { return -1; }

export fn kozo_kernel_main() noreturn {
    // Initialize writer at the physical VGA address (mapped via Identity PD[0])
    var vga = VgaWriter.init(0xb8000);
    
    // Skip past the bootloader's pulses (Red '1', Yellow '2', White '+')
    vga.cursor = 6; 

    // Pulse 4: The Higher-Half "Genesis" Message
    vga.write(" KOZO GENESIS ", VgaColor.White, VgaColor.Green);

    while (true) {
        asm volatile ("hlt");
    }
}