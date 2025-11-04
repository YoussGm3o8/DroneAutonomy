#!/bin/bash
# Fix apt sources and install GstCameraPlugin

set -e

echo "======================================"
echo "GstCameraPlugin Quick Install"
echo "======================================"
echo ""

# Fix broken apt sources first
echo "Step 1: Fixing apt sources..."
if [ -f /etc/apt/sources.list.d/nvidia-container-toolkit.list ]; then
    echo "Backing up and removing broken nvidia-container-toolkit.list..."
    sudo mv /etc/apt/sources.list.d/nvidia-container-toolkit.list /etc/apt/sources.list.d/nvidia-container-toolkit.list.bak
fi

# Try to update apt
echo "Updating package lists..."
sudo apt-get update || {
    echo "Warning: apt-get update had some issues, but continuing..."
}

# Install dependencies without full update if needed
echo ""
echo "Step 2: Installing required packages..."

# Check if gstreamer is already installed
if command -v gst-launch-1.0 &> /dev/null; then
    echo "✓ GStreamer already installed"
else
    echo "Installing GStreamer..."
    sudo apt-get install -y --no-install-recommends \
        gstreamer1.0-tools \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly \
        gstreamer1.0-libav \
        libgstreamer1.0-dev \
        libgstreamer-plugins-base1.0-dev \
        libgstreamer-plugins-good1.0-dev
fi

# Check if cmake is installed
if command -v cmake &> /dev/null; then
    echo "✓ CMake already installed"
else
    echo "Installing CMake..."
    sudo apt-get install -y cmake
fi

# Check if build-essential is installed
if command -v g++ &> /dev/null; then
    echo "✓ Build tools already installed"
else
    echo "Installing build tools..."
    sudo apt-get install -y build-essential pkg-config
fi

# Check for Gazebo dev libraries
if pkg-config --exists gazebo; then
    echo "✓ Gazebo dev libraries found"
else
    echo "Installing Gazebo dev libraries..."
    sudo apt-get install -y libgazebo-dev || sudo apt-get install -y libgazebo11-dev
fi

# Create workspace
echo ""
echo "Step 3: Creating plugin workspace..."
WORKSPACE_DIR="$HOME/gazebo_gst_plugin"
mkdir -p "$WORKSPACE_DIR"
cd "$WORKSPACE_DIR"

# Create CMakeLists.txt
echo "Creating build configuration..."
cat > CMakeLists.txt << 'CMAKEEOF'
cmake_minimum_required(VERSION 3.10)
project(gazebo_gst_camera_plugin)

find_package(gazebo REQUIRED)
find_package(PkgConfig REQUIRED)

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

add_library(GstCameraPlugin SHARED GstCameraPlugin.cc)
target_link_libraries(GstCameraPlugin 
    ${GAZEBO_LIBRARIES}
    ${GSTREAMER_LIBRARIES}
    ${GSTREAMER_APP_LIBRARIES}
    CameraPlugin
)

install(TARGETS GstCameraPlugin DESTINATION lib)
CMAKEEOF

# Create plugin source
echo "Creating plugin source code..."
cat > GstCameraPlugin.cc << 'CPPEOF'
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
      CameraPlugin::Load(_sensor, _sdf);

      if (!gst_is_initialized())
      {
        gst_init(nullptr, nullptr);
      }

      std::string udpHost = "127.0.0.1";
      int udpPort = 5600;
      
      if (_sdf->HasElement("udp_host"))
        udpHost = _sdf->Get<std::string>("udp_host");
      
      if (_sdf->HasElement("udp_port"))
        udpPort = _sdf->Get<int>("udp_port");

      std::string pipelineStr = 
        "appsrc name=source ! "
        "videoconvert ! "
        "video/x-raw,format=I420 ! "
        "x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! "
        "rtph264pay ! "
        "udpsink host=" + udpHost + " port=" + std::to_string(udpPort);

      this->pipeline = gst_parse_launch(pipelineStr.c_str(), nullptr);
      this->source = gst_bin_get_by_name(GST_BIN(this->pipeline), "source");

      g_object_set(G_OBJECT(this->source),
                   "stream-type", 0,
                   "format", GST_FORMAT_TIME,
                   "is-live", TRUE,
                   nullptr);

      GstCaps *caps = gst_caps_new_simple("video/x-raw",
                                          "format", G_TYPE_STRING, "RGB",
                                          "width", G_TYPE_INT, this->width,
                                          "height", G_TYPE_INT, this->height,
                                          "framerate", GST_TYPE_FRACTION, 30, 1,
                                          nullptr);
      gst_app_src_set_caps(GST_APP_SRC(this->source), caps);
      gst_caps_unref(caps);

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

      size_t size = _width * _height * _depth;
      GstBuffer *buffer = gst_buffer_new_allocate(nullptr, size, nullptr);
      
      GstMapInfo map;
      gst_buffer_map(buffer, &map, GST_MAP_WRITE);
      std::memcpy(map.data, _image, size);
      gst_buffer_unmap(buffer, &map);

      gst_app_src_push_buffer(GST_APP_SRC(this->source), buffer);
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
CPPEOF

# Build
echo ""
echo "Step 4: Building plugin..."
mkdir -p build
cd build
cmake ..
make -j$(nproc)

echo ""
echo "Step 5: Setting up environment..."
export GAZEBO_PLUGIN_PATH=$GAZEBO_PLUGIN_PATH:$WORKSPACE_DIR/build
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$WORKSPACE_DIR/build

if ! grep -q "GAZEBO_PLUGIN_PATH.*gazebo_gst_plugin" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# Gazebo GStreamer Plugin" >> ~/.bashrc
    echo "export GAZEBO_PLUGIN_PATH=\$GAZEBO_PLUGIN_PATH:$WORKSPACE_DIR/build" >> ~/.bashrc
    echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:$WORKSPACE_DIR/build" >> ~/.bashrc
fi

echo ""
echo "======================================"
echo "✓ Installation Complete!"
echo "======================================"
echo ""
echo "Plugin built: $WORKSPACE_DIR/build/libGstCameraPlugin.so"
echo ""
echo "Usage in SDF:"
echo '<plugin name="gst_camera_plugin" filename="libGstCameraPlugin.so">'
echo '  <udp_host>127.0.0.1</udp_host>'
echo '  <udp_port>5600</udp_port>'
echo '</plugin>'
echo ""
echo "View stream:"
echo "gst-launch-1.0 udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink"
echo ""
echo "For new terminals: source ~/.bashrc"
