#!/bin/bash
# Test script for GstCameraPlugin installation

set -e

echo "======================================"
echo "GstCameraPlugin Installation Test"
echo "======================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Helper function for tests
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing: $test_name ... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED++))
        return 1
    fi
}

# Test 1: Check if Gazebo is installed
run_test "Gazebo installation" "which gazebo"

# Test 2: Check Gazebo version
if gazebo --version > /dev/null 2>&1; then
    VERSION=$(gazebo --version 2>&1 | grep "Gazebo" | head -1)
    echo -e "${GREEN}  → $VERSION${NC}"
fi

# Test 3: Check GStreamer installation
run_test "GStreamer installation" "which gst-launch-1.0"

# Test 4: Check GStreamer version
if gst-launch-1.0 --version > /dev/null 2>&1; then
    GST_VERSION=$(gst-launch-1.0 --version 2>&1 | grep "version" | head -1)
    echo -e "${GREEN}  → $GST_VERSION${NC}"
fi

# Test 5: Check for required GStreamer plugins
echo ""
echo "Checking GStreamer plugins:"
REQUIRED_PLUGINS=("x264enc" "rtph264pay" "udpsink" "appsrc" "videoconvert")

for plugin in "${REQUIRED_PLUGINS[@]}"; do
    run_test "  GStreamer plugin: $plugin" "gst-inspect-1.0 $plugin"
done

# Test 6: Check if plugin source directory exists
echo ""
run_test "Plugin source directory" "test -d ~/gazebo_gst_plugin"

# Test 7: Check if plugin is built
run_test "Plugin library built" "test -f ~/gazebo_gst_plugin/build/libGstCameraPlugin.so"

# Test 8: Check Gazebo plugin path
echo ""
echo "Checking Gazebo environment:"
if [ -n "$GAZEBO_PLUGIN_PATH" ]; then
    echo -e "${GREEN}  → GAZEBO_PLUGIN_PATH is set${NC}"
    echo "     $GAZEBO_PLUGIN_PATH"
    ((PASSED++))
else
    echo -e "${YELLOW}  → GAZEBO_PLUGIN_PATH not set (may need to source ~/.bashrc)${NC}"
    ((FAILED++))
fi

# Test 9: List available Gazebo plugins
echo ""
echo "Available Gazebo plugins in system:"
PLUGIN_DIR=$(pkg-config --variable=plugindir gazebo 2>/dev/null || echo "/usr/lib/x86_64-linux-gnu/gazebo-11/plugins")
if [ -d "$PLUGIN_DIR" ]; then
    echo -e "${GREEN}  → Plugin directory: $PLUGIN_DIR${NC}"
    ls "$PLUGIN_DIR" | grep -i camera | head -5
else
    echo -e "${YELLOW}  → Plugin directory not found${NC}"
fi

# Test 10: Check build dependencies
echo ""
echo "Checking build dependencies:"
run_test "  CMake" "which cmake"
run_test "  pkg-config" "which pkg-config"
run_test "  g++" "which g++"

# Test 11: Verify Gazebo development libraries
run_test "  Gazebo dev libraries" "pkg-config --exists gazebo"

# Test 12: Verify GStreamer development libraries
run_test "  GStreamer dev libraries" "pkg-config --exists gstreamer-1.0"

# Test 13: Test simple GStreamer pipeline
echo ""
echo "Testing GStreamer functionality:"
echo -n "Testing basic GStreamer pipeline ... "
if timeout 2 gst-launch-1.0 videotestsrc num-buffers=10 ! fakesink > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAILED${NC}"
    ((FAILED++))
fi

# Test 14: Check for example SDF file
echo ""
run_test "Example SDF file exists" "test -f config/gazebo_models/iris_with_gst_camera.sdf"

# Test 15: Validate plugin library with ldd
echo ""
echo "Checking plugin dependencies:"
if [ -f ~/gazebo_gst_plugin/build/libGstCameraPlugin.so ]; then
    echo -n "Checking shared library dependencies ... "
    if ldd ~/gazebo_gst_plugin/build/libGstCameraPlugin.so > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
        
        # Check for critical dependencies
        MISSING_DEPS=$(ldd ~/gazebo_gst_plugin/build/libGstCameraPlugin.so | grep "not found" | wc -l)
        if [ "$MISSING_DEPS" -gt 0 ]; then
            echo -e "${RED}  → Warning: $MISSING_DEPS missing dependencies!${NC}"
            ldd ~/gazebo_gst_plugin/build/libGstCameraPlugin.so | grep "not found"
        else
            echo -e "${GREEN}  → All dependencies satisfied${NC}"
        fi
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED++))
    fi
fi

# Summary
echo ""
echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! Your installation is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Test with Gazebo: gazebo config/gazebo_models/iris_with_gst_camera.sdf"
    echo "2. View stream: gst-launch-1.0 udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink"
    echo ""
    exit 0
else
    echo -e "${YELLOW}⚠ Some tests failed. Please review the errors above.${NC}"
    echo ""
    echo "Common fixes:"
    echo "1. Source environment: source ~/.bashrc"
    echo "2. Rebuild plugin: cd ~/gazebo_gst_plugin/build && cmake .. && make"
    echo "3. Check installation script output for errors"
    echo ""
    exit 1
fi
