#!/bin/bash
# Create iris_runway world with GStreamer camera

ARDUPILOT_GAZEBO="$HOME/gz_ws/src/ardupilot_gazebo"
OUTPUT_FILE="$ARDUPILOT_GAZEBO/worlds/iris_runway_camera.sdf"

echo "🌍 Creating iris_runway_camera.sdf world..."

# Copy original iris_runway and modify it
cat "$ARDUPILOT_GAZEBO/worlds/iris_runway.sdf" | \
sed 's|<world name="iris_runway">|<world name="iris_runway_camera">|' > "$OUTPUT_FILE"

# Add the camera-enabled iris model spawn at the end (before </world>)
# First, remove the closing </world> tag
sed -i '$ d' "$OUTPUT_FILE"

# Add iris_with_camera spawn
cat >> "$OUTPUT_FILE" << 'EOF'

    <!-- Spawn iris quadcopter with GStreamer camera -->
    <include>
      <uri>model://iris_with_camera</uri>
      <name>iris</name>
      <pose>0 0 0.2 0 0 0</pose>
    </include>

  </world>
</sdf>
EOF

echo "✓ Created world at: $OUTPUT_FILE"
echo ""
echo "To launch:"
echo "  gz sim -v4 -r ~/gz_ws/src/ardupilot_gazebo/worlds/iris_runway_camera.sdf"
echo ""
echo "With ArduPilot SITL:"
echo "  1. Terminal 1: gz sim -v4 -r ~/gz_ws/src/ardupilot_gazebo/worlds/iris_runway_camera.sdf"
echo "  2. Terminal 2: sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --map --console"
