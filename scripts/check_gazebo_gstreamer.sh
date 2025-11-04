#!/bin/bash
# Check if Gazebo GStreamer plugin is loaded and working

echo "=== Checking Gazebo GStreamer Status ==="
echo ""

# Check if Gazebo running
if pgrep -f "gz sim" > /dev/null; then
    echo "✓ Gazebo is running (PID: $(pgrep -f 'gz sim' | head -1))"
else
    echo "✗ Gazebo is NOT running"
    exit 1
fi

# Check if plugin file exists
PLUGIN="$HOME/gazebo_gst_plugin/build/libGstCameraPlugin.so"
if [ -f "$PLUGIN" ]; then
    echo "✓ Plugin file exists: $PLUGIN"
else
    echo "✗ Plugin file NOT found!"
    exit 1
fi

# Check environment
echo ""
echo "Plugin path: $GZ_SIM_SYSTEM_PLUGIN_PATH"
echo "Library path: $LD_LIBRARY_PATH"

# Check if any GStreamer process is running
echo ""
if pgrep -f "gst" > /dev/null; then
    echo "✓ GStreamer process(es) detected"
    pgrep -af "gst" | head -5
else
    echo "⚠ No GStreamer processes found"
fi

# Check UDP activity (requires ss command)
echo ""
echo "Checking UDP port 5600..."
if command -v ss &> /dev/null; then
    ss -anu | grep 5600 || echo "  No activity on port 5600"
else
    echo "  (ss command not found, cannot check)"
fi

# Get Gazebo log location
echo ""
echo "Check Gazebo logs at:"
echo "  ~/.gz/sim/log/"
ls -lht ~/.gz/sim/log/ 2>/dev/null | head -5

echo ""
echo "To see plugin messages, check the Gazebo terminal window"
echo "Look for:"
echo "  - 'GstCameraPlugin: Initialized'"
echo "  - 'Streaming to udp://...'"
