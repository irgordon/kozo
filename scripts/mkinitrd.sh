#!/bin/sh
# KOZO OS: Generate Initial RAM Disk (initrd)
# File Path: scripts/mkinitrd.sh
# Responsibility: Package Rust service binaries into CPIO archive for kernel boot
# Usage: ./mkinitrd.sh <init_bin> <policy_bin> <fsd_bin> <output_file>
# Generates: <output_file> (CPIO archive loaded by kernel at boot)

set -euo pipefail  # Strict error handling

# Arguments
INIT_BIN="${1:-}"
POLICY_BIN="${2:-}"
FSD_BIN="${3:-}"
OUTPUT="${4:-}"

# Validate arguments
if [ -z "$INIT_BIN" ] || [ -z "$POLICY_BIN" ] || [ -z "$FSD_BIN" ] || [ -z "$OUTPUT" ]; then
    echo "ERROR: Usage: $0 <init_bin> <policy_bin> <fsd_bin> <output_file>" >&2
    exit 1
fi

# Verify binaries exist
for bin in "$INIT_BIN" "$POLICY_BIN" "$FSD_BIN"; do
    if [ ! -f "$bin" ]; then
        echo "ERROR: Binary not found: $bin" >&2
        exit 1
    done
done

# Create temporary directory structure
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT  # Cleanup on exit

mkdir -p "$TEMP_DIR/bin"
mkdir -p "$TEMP_DIR/etc"

# Copy binaries with specific names expected by kernel
# Order matters: Init must be first in execution order
echo "Packing initrd:"
echo "  -> init (bootstrap)"
cp -v "$INIT_BIN" "$TEMP_DIR/bin/init"

echo "  -> policy (Tier 1 service)"
cp -v "$POLICY_BIN" "$TEMP_DIR/bin/policy"

echo "  -> fsd (Tier 2 service)"  
cp -v "$FSD_BIN" "$TEMP_DIR/bin/fsd"

# Generate manifest for kernel validation
# Kernel uses this to verify integrity and load order
cat > "$TEMP_DIR/etc/manifest.txt" << EOF
# KOZO Initrd Manifest v0.0.1-dev
# File Path: /etc/manifest.txt (inside initrd)
# Format: <name> <path> <sha256> <tier>

init /bin/init $(sha256sum "$INIT_BIN" | cut -d' ' -f1) tier1
policy /bin/policy $(sha256sum "$POLICY_BIN" | cut -d' ' -f1) tier1
fsd /bin/fsd $(sha256sum "$FSD_BIN" | cut -d' ' -f1) tier2
EOF

# Set permissions (readable/executable by all, writable by none)
chmod 755 "$TEMP_DIR/bin/"*

# Create the CPIO archive
# -H newc: "new" portable format (standard for Linux kernels)
# --quiet: Suppress file list output
# --owner=0:0: Set all files to root ownership
echo "Creating CPIO archive..."
(cd "$TEMP_DIR" && find . -print0 | cpio -o -H newc --quiet --owner=0:0 --null) > "$OUTPUT"

# Verify archive was created
if [ ! -s "$OUTPUT" ]; then
    echo "ERROR: Failed to create initrd archive" >&2
    exit 1
fi

# Optional: Compress with gzip for smaller size
# Kernel must have decompression support if enabled
if [ "${KOZO_COMPRESS_INITRD:-}" = "1" ]; then
    echo "Compressing initrd..."
    gzip -9 -f "$OUTPUT"
    mv "$OUTPUT.gz" "$OUTPUT"
    echo "✓ Created compressed initrd: $OUTPUT ($(stat -c%s "$OUTPUT") bytes)"
else
    echo "✓ Created initrd: $OUTPUT ($(stat -c%s "$OUTPUT") bytes)"
fi

# Output manifest for debugging
echo ""
echo "Manifest:"
cat "$TEMP_DIR/etc/manifest.txt"