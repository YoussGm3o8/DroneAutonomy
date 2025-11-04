#!/bin/bash
# Test Gazebo startup and diagnose issues

echo "=== Gazebo GStreamer Diagnostic Tool ==="
echo ""

# 1. Check Gazebo installation
echo "1. Checking Gazebo Harmonic..."
if command -v gz &> /dev/null; then
    echo "   ✓ Gazebo found: $(gz sim --version | head -1)"
else
    echo "   ✗ Gazebo not found!"
    exit 1
fi

# 2. Check plugin
echo ""
echo "2. Checking GStreamer plugin..."
PLUGIN_PATH="$HOME/gazebo_gst_plugin/build/libGstCameraPlugin.so"
if [ -f "$PLUGIN_PATH" ]; then
    echo "   ✓ Plugin found: $PLUGIN_PATH"
    echo "   Plugin info:"
    ldd "$PLUGIN_PATH" 2>&1 | grep -E "(gstreamer|not found)" | head -5
else
    echo "   ✗ Plugin not found at $PLUGIN_PATH"
fi

# 3. Check GStreamer
echo ""
echo "3. Checking GStreamer..."
if command -v gst-launch-1.0 &> /dev/null; then
    echo "   ✓ GStreamer found: $(gst-launch-1.0 --version | head -1)"
else
    echo "   ✗ GStreamer not found!"
fi

# 4. Check world file
echo ""
echo "4. Checking world file..."
WORLD_FILE="/mnt/c/Users/Youssef/Documents/Code/ComputerVision/DroneAutonomy/config/gazebo_models/camera_gstreamer_test.sdf"
if [ -f "$WORLD_FILE" ]; then
    echo "   ✓ World file found"
    echo "   Checking for Windows IP in file..."
    if grep -q "127.0.0.1" "$WORLD_FILE"; then
        echo "   ⚠ WARNING: Using 127.0.0.1 - should use Windows IP!"
        WINDOWS_IP=$(ip route show | grep -i default | awk '{ print $3}')
        echo "   Windows IP should be: $WINDOWS_IP"
    fi
else
    echo "   ✗ World file not found!"
fi

# 5. Test plugin loading
echo ""
echo "5. Testing plugin loading (dry-run)..."
export GZ_SIM_SYSTEM_PLUGIN_PATH=$GZ_SIM_SYSTEM_PLUGIN_PATH:$HOME/gazebo_gst_plugin/build
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/gazebo_gst_plugin/build

echo "   Plugin path: $GZ_SIM_SYSTEM_PLUGIN_PATH"

# Try to verify the SDF
echo ""
echo "6. Validating SDF file..."
gz sdf -k "$WORLD_FILE" 2>&1 | head -20

# 7. Check display
echo ""
echo "7. Checking display settings..."
if [ -z "$DISPLAY" ]; then
    echo "   ⚠ WARNING: DISPLAY not set - GUI may not work!"
    echo "   Setting DISPLAY=:0"
    export DISPLAY=:0
else
    echo "   ✓ DISPLAY=$DISPLAY"
fi

# 8. Try headless mode
echo ""
echo "8. Testing headless mode (5 seconds)..."
timeout 5s gz sim -s "$WORLD_FILE" 2>&1 | grep -E "(Error|error|GstCamera|Loading plugin)" || echo "   No obvious errors in first 5 seconds"

echo ""
echo "=== Diagnostic Complete ==="
echo ""
echo "To test full GUI mode, run:"
echo "   gz sim '$WORLD_FILE'"
