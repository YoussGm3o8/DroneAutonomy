#!/bin/bash
# Test if Gazebo camera is actually streaming data

echo "Testing GStreamer UDP reception..."
echo "Listening on port 5600 for 10 seconds..."

# Use timeout and look for actual data
timeout 10 nc -u -l 5600 | xxd | head -20

if [ $? -eq 124 ]; then
    echo ""
    echo "⚠️  No data received after 10 seconds"
    echo ""
    echo "Possible issues:"
    echo "1. Gazebo simulation is PAUSED - Click PLAY button in Gazebo GUI"
    echo "2. Camera not rendering - Make sure Gazebo window is visible"
    echo "3. Firewall blocking - Check Windows firewall allows UDP 5600"
    echo "4. Wrong IP - Check Windows IP: $(ip route show | grep default | awk '{print $3}')"
else
    echo ""
    echo "✓ Data received! Stream is working."
fi
