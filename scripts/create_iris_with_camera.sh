#!/bin/bash
# Create iris_with_camera model by adding GStreamer camera to ArduPilot iris

OUTPUT_DIR="$HOME/gz_ws/src/ardupilot_gazebo/models/iris_with_camera"

# Get Windows IP
WINDOWS_IP=$(ip route show | grep -i default | awk '{ print $3}')

echo "🚁 Creating iris_with_camera model..."
echo "🌐 Windows IP: $WINDOWS_IP"

# Create model directory
mkdir -p "$OUTPUT_DIR"

# Create model.config
cat > "$OUTPUT_DIR/model.config" << 'EOF'
<?xml version="1.0"?>
<model>
  <name>iris_with_camera</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author>
    <name>Auto-generated</name>
    <email></email>
  </author>
  <description>
    Iris quadcopter with GStreamer camera
  </description>
</model>
EOF

# Create model.sdf with GStreamer camera
cat > "$OUTPUT_DIR/model.sdf" << EOF
<?xml version='1.0'?>
<sdf version="1.9">
  <model name="iris_with_camera">
    <!-- Include base iris model -->
    <include>
      <uri>model://iris_with_standoffs</uri>
    </include>

    <!-- ArduPilot plugin -->
    <plugin
      filename="gz-sim-ardupilot-plugin"
      name="ardupilot_plugin::ArduPilotPlugin">
      <fdm_addr>127.0.0.1</fdm_addr>
      <fdm_port_in>9002</fdm_port_in>
      <fdm_port_out>9003</fdm_port_out>
      <modelXYZToAirplaneXForwardZDown>0 0 0 3.141593 0 0</modelXYZToAirplaneXForwardZDown>
      <gazeboXYZToNED>0 0 0 3.141593 0 0</gazeboXYZToNED>
      <imuName>iris_with_standoffs::iris::imu_link::imu_sensor</imuName>
      <connectionTimeoutMaxCount>5</connectionTimeoutMaxCount>
      <lock_step>1</lock_step>
    </plugin>

    <!-- Camera link mounted on drone body -->
    <link name="camera_link">
      <pose relative_to="iris_with_standoffs::base_link">0.15 0 -0.05 0 0.52 0</pose>
      
      <inertial>
        <mass>0.015</mass>
        <inertia>
          <ixx>0.00001</ixx>
          <ixy>0</ixy>
          <ixz>0</ixz>
          <iyy>0.00001</iyy>
          <iyz>0</iyz>
          <izz>0.00001</izz>
        </inertia>
      </inertial>

      <visual name="visual">
        <geometry>
          <box>
            <size>0.03 0.06 0.02</size>
          </box>
        </geometry>
        <material>
          <ambient>0.2 0.2 0.2 1</ambient>
          <diffuse>0.2 0.2 0.2 1</diffuse>
        </material>
      </visual>

      <collision name="collision">
        <geometry>
          <box>
            <size>0.03 0.06 0.02</size>
          </box>
        </geometry>
      </collision>

      <!-- Camera sensor with GStreamer plugin -->
      <sensor name="camera" type="camera">
        <pose>0 0 0 0 0 0</pose>
        <camera>
          <horizontal_fov>1.047</horizontal_fov>
          <image>
            <width>1280</width>
            <height>720</height>
            <format>R8G8B8</format>
          </image>
          <clip>
            <near>0.1</near>
            <far>100</far>
          </clip>
        </camera>
        <always_on>1</always_on>
        <update_rate>30</update_rate>
        <visualize>true</visualize>
        <topic>camera</topic>
        
        <!-- GStreamer Plugin -->
        <plugin filename="GstCameraPlugin" name="gazebo_gstreamer::GstCameraPlugin">
          <udp_host>$WINDOWS_IP</udp_host>
          <udp_port>5600</udp_port>
        </plugin>
      </sensor>
    </link>

    <!-- Joint to attach camera to drone body -->
    <joint name="camera_joint" type="fixed">
      <parent>iris_with_standoffs::base_link</parent>
      <child>camera_link</child>
    </joint>

  </model>
</sdf>
EOF

echo "✓ Created model at: $OUTPUT_DIR"
echo ""
echo "To use this model:"
echo "  gz sim -v4 -r ~/gz_ws/src/ardupilot_gazebo/worlds/iris_runway.sdf"
echo ""
echo "Or spawn it in a world:"
echo "  <include>"
echo "    <uri>model://iris_with_camera</uri>"
echo "  </include>"
