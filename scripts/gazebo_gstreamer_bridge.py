#!/usr/bin/env python3
"""
Gazebo to GStreamer Bridge (for WSL to Windows)

- Subscribes to a Gazebo camera topic using gz-transport.
- Dynamically finds the Windows host IP from within WSL.
- Creates a GStreamer pipeline to encode the video to H.264.
- Streams the video over RTP/UDP to the Windows host.
"""
import sys
import argparse
import numpy as np
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from gz.transport13 import Node
from gz.msgs10.image_pb2 import Image
import time

def get_windows_ip():
    """
    Get the Windows host IP address from WSL's /etc/resolv.conf.
    This is the most reliable method for WSL2.
    """
    try:
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                if line.strip().startswith('nameserver'):
                    ip = line.split()[1]
                    print(f"✓ Found Windows host IP: {ip}")
                    return ip
    except Exception as e:
        print(f"✗ Could not find Windows IP, defaulting to localhost. Error: {e}")
        return '127.0.0.1'

class GazeboGStreamerBridge:
    """Bridge Gazebo camera to GStreamer RTP stream"""
    
    def __init__(self, topic, host, port=5600, use_hw_accel=True):
        self.topic = topic
        self.host = host
        self.port = port
        self.frame_count = 0
        
        # Initialize GStreamer
        Gst.init(None)
        
        # Use NVIDIA hardware encoder if available, otherwise fallback to software
        encoder = 'nvh264enc preset=low-latency-hq bitrate=4000' if use_hw_accel else 'x264enc tune=zerolatency bitrate=4000 speed-preset=ultrafast'
        
        pipeline_str = (
            f'appsrc name=source is-live=true format=time do-timestamp=true '
            f'caps=video/x-raw,format=RGB,width=1280,height=720,framerate=30/1 ! '
            f'videoconvert ! '
            f'{encoder} ! '
            f'h264parse config-interval=1 ! '
            f'rtph264pay config-interval=1 pt=96 mtu=1400 ! '
            f'udpsink host={host} port={port} sync=false'
        )
        
        print(f"GStreamer Pipeline: {pipeline_str}")
        
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
            self.appsrc = self.pipeline.get_by_name('source')
            self.pipeline.set_state(Gst.State.PLAYING)
            print(f"✓ GStreamer pipeline started, streaming to {host}:{port}")
        except Exception as e:
            print(f"✗ Failed to create GStreamer pipeline: {e}")
            sys.exit(1)
        
        # Create Gazebo node and subscribe
        self.node = Node()
        if not self.node.subscribe(Image, topic, self.on_image):
            print(f"✗ Failed to subscribe to {topic}")
            sys.exit(1)
        
        print(f"✓ Subscribed to Gazebo topic: {topic}")
        print("Streaming... Press Ctrl+C to stop")
    
    def on_image(self, msg: Image):
        """Callback for Gazebo camera images"""
        try:
            if self.frame_count == 0:
                print(f"✓ Received first frame from Gazebo! Size: {msg.width}x{msg.height}")
            
            img_data = np.frombuffer(msg.data, dtype=np.uint8).reshape((msg.height, msg.width, 3))
            buffer = Gst.Buffer.new_wrapped(img_data.tobytes())
            self.appsrc.emit('push-buffer', buffer)
            self.frame_count += 1
            if self.frame_count % 90 == 0:
                print(f"  ... {self.frame_count} frames streamed ...")
                
        except Exception as e:
            print(f"✗ Error processing image: {e}")
    
    def run(self):
        """Run the bridge"""
        try:
            GLib.MainLoop().run()
        except KeyboardInterrupt:
            print("\n✓ Stopping bridge...")
        finally:
            self.pipeline.set_state(Gst.State.NULL)
            print("✓ Bridge stopped")

def main():
    parser = argparse.ArgumentParser(description='Gazebo to GStreamer Bridge for WSL')
    parser.add_argument('--topic', default='/world/iris_runway/model/iris_with_camera/link/camera_link/sensor/camera/image',
                       help='Gazebo camera topic')
    parser.add_argument('--port', type=int, default=5600, help='Target UDP port')
    
    args = parser.parse_args()
    
    host_ip = get_windows_ip()
    
    bridge = GazeboGStreamerBridge(args.topic, host_ip, args.port)
    bridge.run()

if __name__ == '__main__':
    main()
