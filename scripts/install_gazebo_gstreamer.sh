#!/bin/bash
# Install Gazebo with GstCameraPlugin for GStreamer support on WSL
# This script installs Gazebo 11 and builds the GstCameraPlugin

set -e

echo "======================================"
echo "Gazebo + GstCameraPlugin Installation"
echo "======================================"

# Update system
echo "Step 1: Updating system packages..."
sudo apt-get update

# Install Gazebo 11
echo "Step 2: Installing Gazebo 11..."
sudo sh -c 'echo "deb http://packages.osrfoundation.org/gazebo/ubuntu-stable `lsb_release -cs` main" > /etc/apt/sources.list.d/gazebo-stable.list'
wget https://packages.osrfoundation.org/gazebo.key -O - | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y gazebo11 libgazebo11-dev

# Install GStreamer and dependencies
echo "Step 3: Installing GStreamer and dependencies..."
sudo apt-get install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-good1.0-dev

# Install build tools
echo "Step 4: Installing build tools..."
sudo apt-get install -y \
    cmake \
    build-essential \
    git \
    pkg-config

# Create workspace for plugin
echo "Step 5: Setting up plugin workspace..."
WORKSPACE_DIR="$HOME/gazebo_gst_plugin"
mkdir -p "$WORKSPACE_DIR"
cd "$WORKSPACE_DIR"

# Download or create the GstCameraPlugin
echo "Step 6: Creating GstCameraPlugin..."

# Create CMakeLists.txt
cat > CMakeLists.txt << 'EOF'
cmake_minimum_required(VERSION 3.10)
project(gazebo_gst_camera_plugin)

# Find Gazebo
find_package(gazebo REQUIRED)
find_package(PkgConfig REQUIRED)

# Find GStreamer
pkg_check_modules(GSTREAMER REQUIRED gstreamer-1.0)
pkg_check_modules(GSTREAMER_APP REQUIRED gstreamer-app-1.0)

include_directories(
    ${GAZEBO_INCLUDE_DIRS}
    ${GSTREAMER_INCLUDE_DIRS}
)

link_directories(
    ${GAZEBO_LIBRARY_DIRS}
    ${GSTREAMER_LIBRARY_DIRS}
)

# Add the plugin
add_library(GstCameraPlugin SHARED GstCameraPlugin.cc)
target_link_libraries(GstCameraPlugin 
    ${GAZEBO_LIBRARIES}
    ${GSTREAMER_LIBRARIES}
    ${GSTREAMER_APP_LIBRARIES}
    CameraPlugin
)

# Install the plugin
install(TARGETS GstCameraPlugin DESTINATION ${GAZEBO_PLUGIN_PATH})
EOF

# Create the plugin source code
cat > GstCameraPlugin.cc << 'EOF'
#include <gazebo/gazebo.hh>
#include <gazebo/plugins/CameraPlugin.hh>
#include <gazebo/sensors/sensors.hh>
#include <gazebo/rendering/Camera.hh>
#include <gst/gst.h>
#include <gst/app/gstappsrc.h>
#include <cstring>

namespace gazebo
{
  class GstCameraPlugin : public CameraPlugin
  {
    public: GstCameraPlugin() : CameraPlugin() {}

    public: void Load(sensors::SensorPtr _sensor, sdf::ElementPtr _sdf)
    {
      // Load parent camera plugin
      CameraPlugin::Load(_sensor, _sdf);

      // Initialize GStreamer
      if (!gst_is_initialized())
      {
        gst_init(nullptr, nullptr);
      }

      // Get parameters from SDF
      std::string udpHost = "127.0.0.1";
      int udpPort = 5600;
      
      if (_sdf->HasElement("udp_host"))
        udpHost = _sdf->Get<std::string>("udp_host");
      
      if (_sdf->HasElement("udp_port"))
        udpPort = _sdf->Get<int>("udp_port");

      // Create GStreamer pipeline
      std::string pipelineStr = 
        "appsrc name=source ! "
        "videoconvert ! "
        "video/x-raw,format=I420 ! "
        "x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! "
        "rtph264pay ! "
        "udpsink host=" + udpHost + " port=" + std::to_string(udpPort);

      this->pipeline = gst_parse_launch(pipelineStr.c_str(), nullptr);
      this->source = gst_bin_get_by_name(GST_BIN(this->pipeline), "source");

      // Configure appsrc
      g_object_set(G_OBJECT(this->source),
                   "stream-type", 0, // GST_APP_STREAM_TYPE_STREAM
                   "format", GST_FORMAT_TIME,
                   "is-live", TRUE,
                   nullptr);

      // Set caps for appsrc
      GstCaps *caps = gst_caps_new_simple("video/x-raw",
                                          "format", G_TYPE_STRING, "RGB",
                                          "width", G_TYPE_INT, this->width,
                                          "height", G_TYPE_INT, this->height,
                                          "framerate", GST_TYPE_FRACTION, 30, 1,
                                          nullptr);
      gst_app_src_set_caps(GST_APP_SRC(this->source), caps);
      gst_caps_unref(caps);

      // Start pipeline
      gst_element_set_state(this->pipeline, GST_STATE_PLAYING);

      gzlog << "GstCameraPlugin: Streaming to udp://" << udpHost << ":" << udpPort << std::endl;
    }

    public: void OnNewFrame(const unsigned char *_image,
                           unsigned int _width, unsigned int _height,
                           unsigned int _depth,
                           const std::string &_format)
    {
      if (!this->pipeline || !this->source)
        return;

      // Create buffer
      size_t size = _width * _height * _depth;
      GstBuffer *buffer = gst_buffer_new_allocate(nullptr, size, nullptr);
      
      // Copy image data
      GstMapInfo map;
      gst_buffer_map(buffer, &map, GST_MAP_WRITE);
      std::memcpy(map.data, _image, size);
      gst_buffer_unmap(buffer, &map);

      // Push buffer
      GstFlowReturn ret = gst_app_src_push_buffer(GST_APP_SRC(this->source), buffer);
      
      if (ret != GST_FLOW_OK)
      {
        gzerr << "GstCameraPlugin: Error pushing buffer" << std::endl;
      }
    }

    public: ~GstCameraPlugin()
    {
      if (this->pipeline)
      {
        gst_element_set_state(this->pipeline, GST_STATE_NULL);
        gst_object_unref(this->pipeline);
      }
      if (this->source)
      {
        gst_object_unref(this->source);
      }
    }

    private: GstElement *pipeline = nullptr;
    private: GstElement *source = nullptr;
  };

  GZ_REGISTER_SENSOR_PLUGIN(GstCameraPlugin)
}
EOF

# Build the plugin
echo "Step 7: Building GstCameraPlugin..."
mkdir -p build
cd build
cmake ..
make -j$(nproc)

# Install the plugin
echo "Step 8: Installing GstCameraPlugin..."
sudo make install

# Set up environment variables
echo "Step 9: Configuring environment..."
GAZEBO_PLUGIN_PATH=$(pkg-config --variable=plugindir gazebo)

# Add to bashrc if not already present
if ! grep -q "GAZEBO_PLUGIN_PATH.*gazebo_gst_plugin" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# Gazebo GStreamer Plugin" >> ~/.bashrc
    echo "export GAZEBO_PLUGIN_PATH=\$GAZEBO_PLUGIN_PATH:$WORKSPACE_DIR/build" >> ~/.bashrc
    echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:$WORKSPACE_DIR/build" >> ~/.bashrc
fi

# Source the updated bashrc
source ~/.bashrc

echo ""
echo "======================================"
echo "Installation Complete!"
echo "======================================"
echo ""
echo "Plugin installed to: $WORKSPACE_DIR/build"
echo "Gazebo plugin path: $GAZEBO_PLUGIN_PATH"
echo ""
echo "To use the plugin, add this to your SDF file:"
echo ""
echo '<plugin name="gst_camera_plugin" filename="libGstCameraPlugin.so">'
echo '  <udp_host>127.0.0.1</udp_host>'
echo '  <udp_port>5600</udp_port>'
echo '</plugin>'
echo ""
echo "View stream with: gst-launch-1.0 udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink"
echo ""
echo "Please restart your terminal or run: source ~/.bashrc"
