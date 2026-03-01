#!/bin/sh
# KOZO OS: Integration Test Runner
# File Path: scripts/integration-test.sh
# Responsibility: Run smoke tests in QEMU and validate output
# Usage: ./integration-test.sh <arch> <disk_image>
# Output: JUnit XML to stdout or file

set -euo pipefail

ARCH="${1:-x86_64}"
IMAGE="${2:-}"
TIMEOUT="${KOZO_TEST_TIMEOUT:-30}"
OUTPUT_XML="${KOZO_JUNIT_OUTPUT:-}"

if [ -z "$IMAGE" ] || [ ! -f "$IMAGE" ]; then
    echo "ERROR: Disk image not found: $IMAGE" >&2
    exit 1
fi

# Temporary file for QEMU output
QEMU_LOG=$(mktemp)
trap 'rm -f "$QEMU_LOG"' EXIT

echo "Running KOZO integration test (timeout: ${TIMEOUT}s)..."

# Run QEMU with serial output captured
timeout $TIMEOUT qemu-system-$ARCH \
    -machine q35 \
    -cpu host,-smap \
    -m 128M \
    -drive "format=raw,file=$IMAGE" \
    -serial "file:$QEMU_LOG" \
    -no-reboot \
    -nographic \
    -display none \
    2>/dev/null || true

# Analyze output
TEST_PASSED=0
FAILURES=""

if grep -q "Init>" "$QEMU_LOG"; then
    echo "✓ Init prompt reached"
else
    echo "✗ Init prompt NOT found"
    FAILURES="$FAILURES<failure message='Init prompt not found'/>"
    TEST_PASSED=1
fi

if grep -q "Policy: ready" "$QEMU_LOG"; then
    echo "✓ Policy Service registered"
else
    echo "✗ Policy Service NOT registered"
    FAILURES="$FAILURES<failure message='Policy Service not ready'/>"
    TEST_PASSED=1
fi

if grep -q "IPC_OK" "$QEMU_LOG"; then
    echo "✓ IPC test passed"
else
    echo "✗ IPC test NOT passed"
    FAILURES="$FAILURES<failure message='IPC test failed'/>"
    TEST_PASSED=1
fi

if grep -q "PANIC" "$QEMU_LOG"; then
    echo "✗ Kernel panic detected"
    FAILURES="$FAILURES<failure message='Kernel panic'/>"
    TEST_PASSED=1
fi

# Output JUnit XML if requested
if [ -n "$OUTPUT_XML" ]; then
    cat > "$OUTPUT_XML" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="KOZO_Integration" tests="3" failures="$(($TEST_PASSED == 0 ? 0 : 1))" time="$TIMEOUT">
    <testcase classname="boot" name="Init_Reaches_Prompt" time="1">
      $(grep -q "Init>" "$QEMU_LOG" || echo "<failure message='Init prompt not found'/>")
    </testcase>
    <testcase classname="services" name="Policy_Service_Ready" time="1">
      $(grep -q "Policy: ready" "$QEMU_LOG" || echo "<failure message='Policy not ready'/>")
    </testcase>
    <testcase classname="ipc" name="IPC_Roundtrip" time="1">
      $(grep -q "IPC_OK" "$QEMU_LOG" || echo "<failure message='IPC failed'/>")
    </testcase>
  </testsuite>
</testsuites>
EOF
    echo "JUnit XML written to: $OUTPUT_XML"
fi

# Output log on failure
if [ $TEST_PASSED -ne 0 ]; then
    echo ""
    echo "=== QEMU Output ==="
    cat "$QEMU_LOG"
    echo "==================="
    exit 1
fi

echo ""
echo "SUCCESS: All integration tests passed"
exit 0