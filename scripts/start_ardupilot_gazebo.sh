#!/bin/bash
# Start ArduPilot SITL and Gazebo together

echo "=========================================="
echo " Starting ArduPilot SITL + Gazebo"
echo "=========================================="
echo

# Get Windows IP
WIN_IP=$(ip route show | grep default | awk '{print $3}')
echo "Windows IP: $WIN_IP"

# Set environment variables
export GZ_SIM_RESOURCE_PATH=~/gz_ws/src/ardupilot_gazebo/models:~/gz_ws/src/ardupilot_gazebo/worlds
export GZ_SIM_SYSTEM_PLUGIN_PATH=~/gz_ws/src/ardupilot_gazebo/build:~/.gz/sim/plugins

# Update SDF with correct IP
WORLD_FILE=~/gz_ws/src/ardupilot_gazebo/worlds/iris_runway_camera.sdf
if [ -f "$WORLD_FILE" ]; then
    # Create backup if it doesn't exist
    if [ ! -f "${WORLD_FILE}.bak" ]; then
        cp "$WORLD_FILE" "${WORLD_FILE}.bak"
    fi
    
    # Update IP in world file
    sed -i "s/<udp_host>.*<\/udp_host>/<udp_host>$WIN_IP<\/udp_host>/" "$WORLD_FILE"
    echo "Updated world file with Windows IP: $WIN_IP"
fi

# Check if ArduPilot directory exists
if [ ! -d ~/ardupilot ]; then
    echo "ERROR: ArduPilot not found at ~/ardupilot"
    echo "Please install ArduPilot first"
    exit 1
fi

# Start ArduPilot SITL in background
echo
echo "Starting ArduPilot SITL..."
cd ~/ardupilot
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --map --console -I0 &
ARDUPILOT_PID=$!

echo "ArduPilot SITL started (PID: $ARDUPILOT_PID)"
echo "Waiting 5 seconds for SITL to initialize..."
sleep 5

# Start Gazebo
echo
echo "Starting Gazebo..."
cd ~/gz_ws/src/ardupilot_gazebo
gz sim -v4 -r worlds/iris_runway_camera.sdf

# Cleanup when Gazebo closes
echo
echo "Gazebo closed. Stopping ArduPilot SITL..."
kill $ARDUPILOT_PID 2>/dev/null

echo "Done!"
