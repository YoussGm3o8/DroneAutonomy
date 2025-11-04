#!/bin/bash
# Create iris_runway world with GStreamer camera (FIXED VERSION)

ARDUPILOT_GAZEBO="$HOME/gz_ws/src/ardupilot_gazebo"
ORIGINAL_WORLD="$ARDUPILOT_GAZEBO/worlds/iris_runway.sdf"
OUTPUT_FILE="$ARDUPILOT_GAZEBO/worlds/iris_runway_camera.sdf"

echo "🌍 Creating iris_runway_camera.sdf world..."

# Copy original world
cp "$ORIGINAL_WORLD" "$OUTPUT_FILE"

# Change world name
sed -i 's/name="iris_runway"/name="iris_runway_camera"/' "$OUTPUT_FILE"

# REMOVE the original iris_with_gimbal model (lines 116-121)
sed -i '/iris_with_gimbal/,+5d' "$OUTPUT_FILE"

# Add iris_with_camera spawn before </world>
sed -i '$ d' "$OUTPUT_FILE"  # Remove last line (</world>)
sed -i '$ d' "$OUTPUT_FILE"  # Remove last line (</sdf>)

# Add our camera-enabled iris model
cat >> "$OUTPUT_FILE" << 'EOF'

    <!-- Spawn iris quadcopter with GStreamer camera -->
    <include>
      <uri>model://iris_with_camera</uri>
      <name>iris</name>
      <pose>0 0 0.195 0 0 0</pose>
    </include>

  </world>
</sdf>
EOF

echo "✓ Created world at: $OUTPUT_FILE"
echo ""
echo "To launch:"
echo "  gz sim -v4 -r ~/gz_ws/src/ardupilot_gazebo/worlds/iris_runway_camera.sdf"
