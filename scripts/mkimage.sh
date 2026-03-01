#!/bin/sh
# KOZO OS: Create Bootable Disk Image
# File Path: scripts/mkimage.sh
# Responsibility: Combine kernel + initrd into bootable disk image
# Usage: ./mkimage.sh <kernel_bin> <initrd_cpio> <output_img>
# Generates: <output_img> (Raw disk image for QEMU/bootloader)

set -euo pipefail

KERNEL_BIN="${1:-}"
INITRD="${2:-}"
OUTPUT="${3:-}"

if [ -z "$KERNEL_BIN" ] || [ -z "$INITRD" ] || [ -z "$OUTPUT" ]; then
    echo "ERROR: Usage: $0 <kernel_bin> <initrd_cpio> <output_img>" >&2
    exit 1
fi

if [ ! -f "$KERNEL_BIN" ]; then
    echo "ERROR: Kernel not found: $KERNEL_BIN" >&2
    exit 1
fi

if [ ! -f "$INITRD" ]; then
    echo "ERROR: Initrd not found: $INITRD" >&2
    exit 1
fi

# Image layout:
# 0-511: Boot sector (MBR/multiboot2)
# 512-4095: Kernel (padded to 3584 bytes)
# 4096+: Initrd

BLOCK_SIZE=512
KERNEL_SIZE=$(stat -c%s "$KERNEL_BIN")
INITRD_SIZE=$(stat -c%s "$INITRD")

# Calculate required blocks (kernel starts at block 1, initrd at block 8)
KERNEL_BLOCKS=$(( (KERNEL_SIZE + BLOCK_SIZE - 1) / BLOCK_SIZE ))
INITRD_OFFSET=$(( 8 * BLOCK_SIZE ))  # 4KB alignment
TOTAL_SIZE=$(( INITRD_OFFSET + INITRD_SIZE ))

echo "Creating disk image:"
echo "  Kernel: $KERNEL_SIZE bytes ($KERNEL_BLOCKS blocks)"
echo "  Initrd: $INITRD_SIZE bytes"
echo "  Total: $TOTAL_SIZE bytes"

# Create sparse file
dd if=/dev/zero of="$OUTPUT" bs=1 count=0 seek=$TOTAL_SIZE 2>/dev/null

# Write kernel at offset 512 (block 1)
dd if="$KERNEL_BIN" of="$OUTPUT" bs=$BLOCK_SIZE seek=1 conv=notrunc 2>/dev/null

# Write initrd at offset 4096 (block 8)
dd if="$INITRD" of="$OUTPUT" bs=$BLOCK_SIZE seek=8 conv=notrunc 2>/dev/null

# Create multiboot2 header at start of image (optional, for QEMU direct boot)
# This allows QEMU to load the kernel directly without a bootloader
if command -v mkmultiboot2 >/dev/null 2>&1; then
    mkmultiboot2 "$OUTPUT" "$KERNEL_SIZE" "$INITRD_SIZE"
fi

echo "✓ Created bootable image: $OUTPUT"
echo "  Boot with: qemu-system-x86_64 -drive format=raw,file=$OUTPUT"