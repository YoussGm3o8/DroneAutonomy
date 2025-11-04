#!/bin/bash
# Launch Gazebo Harmonic with GStreamer camera plugin

# Set up plugin paths
export GZ_SIM_SYSTEM_PLUGIN_PATH=$GZ_SIM_SYSTEM_PLUGIN_PATH:$HOME/gazebo_gst_plugin/build:$HOME/gz_ws/src/ardupilot_gazebo/build
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/gazebo_gst_plugin/build:$HOME/gz_ws/src/ardupilot_gazebo/build

# Set up model paths for ArduPilot Gazebo
export GZ_SIM_RESOURCE_PATH=$HOME/gz_ws/src/ardupilot_gazebo/models:$HOME/gz_ws/src/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH

# Get Windows IP
WINDOWS_IP=$(ip route show | grep -i default | awk '{ print $3}')
echo "🌐 Windows IP: $WINDOWS_IP"

# World file path
WORLD_FILE="$1"
if [ -z "$WORLD_FILE" ]; then
    # Default to ArduCopter iris world with camera
    WORLD_FILE="$HOME/gz_ws/src/ardupilot_gazebo/worlds/iris_runway_camera.sdf"
fi

# Check for --with-sitl flag
START_SITL=false
if [ "$2" == "--with-sitl" ] || [ "$1" == "--with-sitl" ]; then
    START_SITL=true
    # If first arg is flag, use default world
    if [ "$1" == "--with-sitl" ]; then
        WORLD_FILE="$HOME/gz_ws/src/ardupilot_gazebo/worlds/iris_runway_camera.sdf"
    fi
fi

echo "🚀 Starting Gazebo Harmonic..."
echo "📁 World: $WORLD_FILE"
echo "🎥 Streaming to: $WINDOWS_IP:5600"
echo "📦 Model path: $GZ_SIM_RESOURCE_PATH"
echo "🔌 Plugin path: $GZ_SIM_SYSTEM_PLUGIN_PATH"
echo ""

# Start ArduPilot SITL if requested
if [ "$START_SITL" == "true" ]; then
    if [ -d "$HOME/ardupilot" ]; then
        echo "� Starting ArduPilot SITL..."
        cd "$HOME/ardupilot"
        sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --map --console -I0 &
        ARDUPILOT_PID=$!
        echo "   PID: $ARDUPILOT_PID"
        echo "   Waiting 5 seconds..."
        sleep 5
        echo ""
    else
        echo "⚠️  ArduPilot not found at ~/ardupilot - skipping SITL"
        echo ""
    fi
else
    echo "�💡 To start ArduCopter SITL manually, run in another terminal:"
    echo "   sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --map --console"
    echo ""
    echo "💡 Or run this script with --with-sitl flag to auto-start SITL"
    echo ""
fi

# Launch Gazebo with GUI and verbose output
gz sim -v4 -r "$WORLD_FILE"

# Cleanup when Gazebo closes
if [ -n "$ARDUPILOT_PID" ]; then
    echo ""
    echo "🛑 Stopping ArduPilot SITL (PID: $ARDUPILOT_PID)..."
    kill $ARDUPILOT_PID 2>/dev/null
    echo "✅ Done!"
fi
