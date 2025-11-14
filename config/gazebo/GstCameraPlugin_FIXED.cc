#include <gz/plugin/Register.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/Camera.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/Sensor.hh>
#include <gz/transport/Node.hh>
#include <gz/msgs/image.pb.h>

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

      this->udpHost = udpHost;
      this->udpPort = udpPort;

      // Find camera sensor and get its topic
      std::string cameraName = gz::sim::scopedName(_entity, _ecm);
      this->cameraTopic = "/camera";  // Default topic from SDF

      // Subscribe to camera image topic
      this->node.Subscribe(this->cameraTopic, &GstCameraPlugin::OnImage, this);

      gzmsg << "GstCameraPlugin: Subscribed to camera topic: " << this->cameraTopic << std::endl;
      gzmsg << "GstCameraPlugin: Will stream to udp://" << udpHost << ":" << udpPort << std::endl;

      this->entity = _entity;
      this->initialized = true;
    }

    // Callback when camera image is received
    private: void OnImage(const gz::msgs::Image &_msg)
    {
      // Initialize pipeline on first frame
      if (!this->pipeline && !this->pipelineCreated)
      {
        this->width = _msg.width();
        this->height = _msg.height();
        
        // Create GStreamer pipeline
        std::string pipelineStr =
          "appsrc name=source ! "
          "videoconvert ! "
          "video/x-raw,format=I420 ! "
          "x264enc tune=zerolatency bitrate=2000 speed-preset=superfast ! "
          "rtph264pay config-interval=1 pt=96 ! "
          "udpsink host=" + this->udpHost + " port=" + std::to_string(this->udpPort);

        gzmsg << "GstCameraPlugin: Creating pipeline: " << pipelineStr << std::endl;

        this->pipeline = gst_parse_launch(pipelineStr.c_str(), nullptr);
        if (!this->pipeline)
        {
          gzerr << "Failed to create GStreamer pipeline" << std::endl;
          return;
        }

        this->source = gst_bin_get_by_name(GST_BIN(this->pipeline), "source");

        // Configure appsrc
        g_object_set(G_OBJECT(this->source),
                     "stream-type", 0,  // GST_APP_STREAM_TYPE_STREAM
                     "format", GST_FORMAT_TIME,
                     "is-live", TRUE,
                     "do-timestamp", TRUE,
                     nullptr);

        // Set caps based on actual camera resolution
        GstCaps *caps = gst_caps_new_simple("video/x-raw",
                                            "format", G_TYPE_STRING, "RGB",
                                            "width", G_TYPE_INT, this->width,
                                            "height", G_TYPE_INT, this->height,
                                            "framerate", GST_TYPE_FRACTION, 30, 1,
                                            nullptr);
        gst_app_src_set_caps(GST_APP_SRC(this->source), caps);
        gst_caps_unref(caps);

        // Start pipeline
        GstStateChangeReturn ret = gst_element_set_state(this->pipeline, GST_STATE_PLAYING);
        if (ret == GST_STATE_CHANGE_FAILURE)
        {
          gzerr << "Failed to start GStreamer pipeline" << std::endl;
          return;
        }

        gzmsg << "GstCameraPlugin: Pipeline started! Streaming " << this->width << "x" << this->height << std::endl;
        this->pipelineCreated = true;
      }

      // Push frame to GStreamer
      if (this->pipeline && this->source)
      {
        // Convert image data
        const std::string &data = _msg.data();
        size_t size = data.size();

        if (size == 0)
          return;

        // Create GStreamer buffer
        GstBuffer *buffer = gst_buffer_new_allocate(nullptr, size, nullptr);
        GstMapInfo map;
        gst_buffer_map(buffer, &map, GST_MAP_WRITE);
        memcpy(map.data, data.c_str(), size);
        gst_buffer_unmap(buffer, &map);

        // Push buffer to pipeline
        GstFlowReturn ret = gst_app_src_push_buffer(GST_APP_SRC(this->source), buffer);
        if (ret != GST_FLOW_OK)
        {
          if (this->frameCount % 100 == 0)  // Only log occasionally
          {
            gzwarn << "GstCameraPlugin: Failed to push buffer, return: " << ret << std::endl;
          }
        }

        this->frameCount++;
        if (this->frameCount % 100 == 0)
        {
          gzmsg << "GstCameraPlugin: Streamed " << this->frameCount << " frames" << std::endl;
        }
      }
    }

    public: void PostUpdate(
        const gz::sim::UpdateInfo &_info,
        const gz::sim::EntityComponentManager &_ecm) override
    {
      // Nothing needed here - all work done in OnImage callback
    }

    private: gz::sim::Entity entity;
    private: bool initialized = false;
    private: bool pipelineCreated = false;
    private: GstElement *pipeline = nullptr;
    private: GstElement *source = nullptr;
    private: gz::transport::Node node;
    private: std::string cameraTopic;
    private: std::string udpHost;
    private: int udpPort;
    private: unsigned int width = 0;
    private: unsigned int height = 0;
    private: unsigned int frameCount = 0;
  };
}

// Register the plugin
GZ_ADD_PLUGIN(
    gazebo_gstreamer::GstCameraPlugin,
    gz::sim::System,
    gazebo_gstreamer::GstCameraPlugin::ISystemConfigure,
    gazebo_gstreamer::GstCameraPlugin::ISystemPostUpdate)

GZ_ADD_PLUGIN_ALIAS(gazebo_gstreamer::GstCameraPlugin, "GstCameraPlugin")
