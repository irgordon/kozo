// File Path: kernel/src/arch/x86_64/vga.zig
// Last Modified: 2026-02-28, 22:50:04.120
const BootInfo = @import("../../../common/boot_info.zig").BootInfo;

pub const VgaWriter = struct {
    fb: [*]volatile u32,
    width: u32,
    height: u32,
    pitch: u32,

    pub fn init(info: *const BootInfo) VgaWriter {
        return .{
            .fb = @ptrFromInt(info.fb_base),
            .width = info.width,
            .height = info.height,
            .pitch = info.pitch,
        };
    }

    pub fn clear(self: VgaWriter, color: u32) void {
        var i: usize = 0;
        const total = (self.pitch / 4) * self.height;
        while (i < total) : (i += 1) {
            self.fb[i] = color;
        }
    }
};