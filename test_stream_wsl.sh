#!/bin/bash
# Test GStreamer video reception inside WSL

echo "=========================================="
echo "Testing GStreamer Video Stream in WSL"
echo "=========================================="
echo ""

# Check if Gazebo is running
echo "[1] Checking if Gazebo is running..."
if pgrep -f "gz sim" > /dev/null; then
    echo "  ✓ Gazebo is running"
    ps aux | grep "[g]z sim" | head -1
else
    echo "  ✗ Gazebo is NOT running!"
    echo "  Start Gazebo first!"
    exit 1
fi

# Check if camera topic exists
echo ""
echo "[2] Checking camera topic..."
if gz topic -l | grep -q "/camera"; then
    echo "  ✓ Camera topic exists: /camera"
else
    echo "  ✗ Camera topic not found!"
    gz topic -l | head -10
    exit 1
fi

# Check camera info
echo ""
echo "[3] Camera topic info..."
gz topic -i -t /camera

# Try to receive one frame
echo ""
echo "[4] Attempting to receive one camera frame..."
timeout 5 gz topic -e -t /camera -n 1 2>&1 | head -20

# Check if UDP port 5600 is active
echo ""
echo "[5] Checking UDP port 5600..."
netstat -tulpn 2>/dev/null | grep 5600 || echo "  ℹ Port 5600 not listening (normal for send-only)"

# Check Windows IP
echo ""
echo "[6] Windows IP address..."
WIN_IP=$(ip route show | grep -i default | awk '{print $3}')
echo "  Windows IP: $WIN_IP"

# Test GStreamer pipeline (save to file instead of display)
echo ""
echo "[7] Testing GStreamer pipeline (5 seconds)..."
echo "  Receiving H.264 stream and saving to test.h264..."

timeout 5 gst-launch-1.0 -v \
    udpsrc address=0.0.0.0 port=5600 ! \
    application/x-rtp, encoding-name=H264 ! \
    rtph264depay ! \
    h264parse ! \
    filesink location=/tmp/test_stream.h264 \
    2>&1 | grep -i "setting\|preroll\|playing\|error" || echo "  Timeout or no data"

if [ -f /tmp/test_stream.h264 ]; then
    SIZE=$(stat -c%s /tmp/test_stream.h264)
    echo "  ✓ Received $SIZE bytes"
    if [ $SIZE -gt 1000 ]; then
        echo "  ✓ SUCCESS! Video stream is working!"
    else
        echo "  ⚠ File too small - stream might not be active"
    fi
    rm /tmp/test_stream.h264
else
    echo "  ✗ No data received"
fi

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
