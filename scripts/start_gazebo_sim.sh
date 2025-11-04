#!/bin/bash
# Auto-start Gazebo simulation

echo "Checking Gazebo simulation state..."

# Wait a moment for Gazebo to fully initialize
sleep 2

# Send play command via gz service
gz service -s /world/iris_runway_camera/control --reqtype gz.msgs.WorldControl --reptype gz.msgs.Boolean --timeout 1000 --req 'pause: false'

if [ $? -eq 0 ]; then
    echo "✓ Simulation started (playing)"
else
    echo "⚠ Could not start simulation"
fi

# Also try to get simulation info
echo ""
echo "Simulation info:"
gz topic -e -t /world/iris_runway_camera/stats -n 1 2>/dev/null | grep -E "paused|real_time_factor"
