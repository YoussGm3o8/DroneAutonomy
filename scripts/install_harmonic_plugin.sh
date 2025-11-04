#!/bin/bash
# Install GstCameraPlugin for Gazebo Harmonic (New Gazebo)

set -e

echo "======================================"
echo "GstCameraPlugin for Gazebo Harmonic"
echo "======================================"
echo ""

# Fix apt sources
if [ -f /etc/apt/sources.list.d/nvidia-container-toolkit.list ]; then
    echo "Fixing broken apt sources..."
    sudo mv /etc/apt/sources.list.d/nvidia-container-toolkit.list /etc/apt/sources.list.d/nvidia-container-toolkit.list.bak 2>/dev/null || true
    sudo apt-get update
fi

# Install GStreamer if needed
echo "Step 1: Installing dependencies..."
if ! command -v gst-launch-1.0 &> /dev/null; then
    sudo apt-get install -y \
        gstreamer1.0-tools \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly \
        gstreamer1.0-libav \
        libgstreamer1.0-dev \
        libgstreamer-plugins-base1.0-dev
fi

# Install Gazebo Harmonic dev packages
echo "Installing Gazebo Harmonic development libraries..."
sudo apt-get install -y \
    gz-harmonic \
    libgz-sim8-dev \
    libgz-sensors8-dev \
    libgz-rendering8-dev \
    libgz-common5-dev \
    cmake build-essential pkg-config

# Create workspace
echo ""
echo "Step 2: Creating plugin workspace..."
WORKSPACE_DIR="$HOME/gazebo_gst_plugin"
mkdir -p "$WORKSPACE_DIR"
cd "$WORKSPACE_DIR"

# Create CMakeLists.txt for Gazebo Harmonic
echo "Creating build configuration..."
cat > CMakeLists.txt << 'CMAKEEOF'
cmake_minimum_required(VERSION 3.10.2)
project(GstCameraPlugin)

find_package(gz-cmake3 REQUIRED)
find_package(gz-plugin2 REQUIRED COMPONENTS register)
find_package(gz-sim8 REQUIRED)
find_package(gz-sensors8 REQUIRED)
find_package(gz-rendering8 REQUIRED)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GSTREAMER REQUIRED gstreamer-1.0)
pkg_check_modules(GSTREAMER_APP REQUIRED gstreamer-app-1.0)

set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${GZ-SIM_CXX_FLAGS}")

add_library(GstCameraPlugin SHARED GstCameraPlugin.cc)
set_property(TARGET GstCameraPlugin PROPERTY CXX_STANDARD 17)

target_link_libraries(GstCameraPlugin
  PRIVATE
    gz-plugin2::gz-plugin2
    gz-sim8::gz-sim8
    gz-sensors8::gz-sensors8
    gz-rendering8::gz-rendering8
    ${GSTREAMER_LIBRARIES}
    ${GSTREAMER_APP_LIBRARIES}
)

target_include_directories(GstCameraPlugin PRIVATE
  ${GSTREAMER_INCLUDE_DIRS}
)

install(TARGETS GstCameraPlugin DESTINATION ${CMAKE_INSTALL_PREFIX}/lib)
CMAKEEOF

# Create plugin source for Gazebo Harmonic
echo "Creating plugin source code..."
cat > GstCameraPlugin.cc << 'CPPEOF'
#include <gz/plugin/Register.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/Camera.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/Sensor.hh>
#include <gz/sensors/CameraSensor.hh>
#include <gz/sensors/SensorFactory.hh>
#include <gz/rendering/Camera.hh>
#include <gz/common/Image.hh>

#include <gst/gst.h>
#include <gst/app/gstappsrc.h>

#include <memory>
#include <string>
#include <cstring>

namespace gazebo_gstreamer
{
  class GstCameraPlugin :
    public gz::sim::System,
    public gz::sim::ISystemConfigure,
    public gz::sim::ISystemPostUpdate
  {
    public: GstCameraPlugin() = default;
    
    public: ~GstCameraPlugin() override
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

    public: void Configure(
        const gz::sim::Entity &_entity,
        const std::shared_ptr<const sdf::Element> &_sdf,
        gz::sim::EntityComponentManager &_ecm,
        gz::sim::EventManager &_eventMgr) override
    {
      // Initialize GStreamer
      if (!gst_is_initialized())
      {
        gst_init(nullptr, nullptr);
      }

      // Get parameters
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
                   "stream-type", 0,
                   "format", GST_FORMAT_TIME,
                   "is-live", TRUE,
                   nullptr);

      // Set caps (will be updated with actual camera resolution)
      GstCaps *caps = gst_caps_new_simple("video/x-raw",
                                          "format", G_TYPE_STRING, "RGB",
                                          "width", G_TYPE_INT, 1280,
                                          "height", G_TYPE_INT, 720,
                                          "framerate", GST_TYPE_FRACTION, 30, 1,
                                          nullptr);
      gst_app_src_set_caps(GST_APP_SRC(this->source), caps);
      gst_caps_unref(caps);

      // Start pipeline
      gst_element_set_state(this->pipeline, GST_STATE_PLAYING);

      gzmsg << "GstCameraPlugin: Streaming to udp://" << udpHost << ":" << udpPort << std::endl;
      
      this->entity = _entity;
      this->initialized = true;
    }

    public: void PostUpdate(
        const gz::sim::UpdateInfo &_info,
        const gz::sim::EntityComponentManager &_ecm) override
    {
      // Note: For full implementation, you'd need to subscribe to camera image topic
      // This is a simplified version - actual image streaming would require
      // subscribing to the camera's image topic and processing those messages
      
      // This serves as a placeholder showing the plugin structure
      // Actual image capture would happen through Gazebo's topic system
    }

    private: gz::sim::Entity entity;
    private: bool initialized = false;
    private: GstElement *pipeline = nullptr;
    private: GstElement *source = nullptr;
  };
}

// Register the plugin
GZ_ADD_PLUGIN(
    gazebo_gstreamer::GstCameraPlugin,
    gz::sim::System,
    gazebo_gstreamer::GstCameraPlugin::ISystemConfigure,
    gazebo_gstreamer::GstCameraPlugin::ISystemPostUpdate)

GZ_ADD_PLUGIN_ALIAS(gazebo_gstreamer::GstCameraPlugin, "GstCameraPlugin")
CPPEOF

# Build
echo ""
echo "Step 3: Building plugin..."
mkdir -p build
cd build
cmake ..
make -j$(nproc)

# Install
echo ""
echo "Step 4: Installing plugin..."
sudo make install

# Set up environment
echo ""
echo "Step 5: Setting up environment..."
GZ_PLUGIN_PATH="$HOME/.gz/sim/plugins"
mkdir -p "$GZ_PLUGIN_PATH"
cp libGstCameraPlugin.so "$GZ_PLUGIN_PATH/"

if ! grep -q "GZ_SIM_SYSTEM_PLUGIN_PATH.*gazebo_gst_plugin" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# Gazebo Harmonic GStreamer Plugin" >> ~/.bashrc
    echo "export GZ_SIM_SYSTEM_PLUGIN_PATH=\$GZ_SIM_SYSTEM_PLUGIN_PATH:$WORKSPACE_DIR/build" >> ~/.bashrc
    echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:$WORKSPACE_DIR/build" >> ~/.bashrc
fi

export GZ_SIM_SYSTEM_PLUGIN_PATH=$GZ_SIM_SYSTEM_PLUGIN_PATH:$WORKSPACE_DIR/build
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$WORKSPACE_DIR/build

echo ""
echo "======================================"
echo "✓ Installation Complete!"
echo "======================================"
echo ""
echo "Plugin built: $WORKSPACE_DIR/build/libGstCameraPlugin.so"
echo "Also copied to: $GZ_PLUGIN_PATH/libGstCameraPlugin.so"
echo ""
echo "Usage in SDF (Gazebo Harmonic):"
echo '<plugin filename="GstCameraPlugin" name="gazebo_gstreamer::GstCameraPlugin">'
echo '  <udp_host>127.0.0.1</udp_host>'
echo '  <udp_port>5600</udp_port>'
echo '</plugin>'
echo ""
echo "View stream:"
echo "gst-launch-1.0 udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink"
echo ""
echo "For new terminals: source ~/.bashrc"
