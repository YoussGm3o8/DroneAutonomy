#!/bin/bash
# Quick start script - Run this after installation to test the setup

echo "======================================"
echo "GStreamer Camera Plugin Quick Start"
echo "======================================"
echo ""

# Get Windows host IP for streaming
WINDOWS_IP=$(ip route show | grep -i default | awk '{ print $3}')
echo "Windows host IP: $WINDOWS_IP"
echo ""

# Ask user what they want to do
echo "Select an option:"
echo "1. Test Gazebo with GStreamer plugin (local)"
echo "2. Test Gazebo with GStreamer plugin (stream to Windows)"
echo "3. View GStreamer stream (receiver)"
echo "4. Test GStreamer installation"
echo "5. Show plugin info"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "Starting Gazebo with GStreamer plugin..."
        echo "Stream will be available at udp://127.0.0.1:5600"
        echo ""
        echo "To view in another terminal, run:"
        echo "gst-launch-1.0 udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink"
        echo ""
        gazebo config/gazebo_models/iris_with_gst_camera.sdf
        ;;
    
    2)
        echo ""
        echo "Starting Gazebo with GStreamer plugin (streaming to Windows)..."
        echo "Stream will be available at udp://$WINDOWS_IP:5600"
        echo ""
        echo "To view on Windows, run in PowerShell:"
        echo "gst-launch-1.0.exe udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink"
        echo "OR open VLC and play: udp://@:5600"
        echo ""
        
        # Create temporary SDF with Windows IP
        TMP_SDF="/tmp/iris_gst_win.sdf"
        sed "s/<udp_host>127.0.0.1<\/udp_host>/<udp_host>$WINDOWS_IP<\/udp_host>/g" \
            config/gazebo_models/iris_with_gst_camera.sdf > "$TMP_SDF"
        
        gazebo "$TMP_SDF"
        ;;
    
    3)
        echo ""
        echo "Starting GStreamer receiver..."
        echo "Waiting for stream on port 5600..."
        echo "Press Ctrl+C to stop"
        echo ""
        gst-launch-1.0 udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink
        ;;
    
    4)
        echo ""
        echo "Testing GStreamer installation..."
        echo ""
        
        # Test 1: Send test pattern
        echo "Test 1: Sending test pattern on port 5600..."
        gst-launch-1.0 videotestsrc pattern=smpte num-buffers=300 ! \
            video/x-raw,width=1280,height=720,framerate=30/1 ! \
            x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! \
            rtph264pay ! udpsink host=127.0.0.1 port=5600 &
        GST_PID=$!
        
        sleep 2
        
        # Test 2: Receive and display
        echo "Test 2: Receiving and displaying..."
        echo "You should see a color test pattern. Press Ctrl+C to stop."
        echo ""
        
        timeout 10 gst-launch-1.0 udpsrc port=5600 ! \
            application/x-rtp ! rtph264depay ! avdec_h264 ! \
            videoconvert ! autovideosink || true
        
        # Cleanup
        kill $GST_PID 2>/dev/null || true
        
        echo ""
        echo "Test complete!"
        ;;
    
    5)
        echo ""
        echo "Plugin Information:"
        echo "===================="
        echo ""
        
        # Check if plugin exists
        if [ -f ~/gazebo_gst_plugin/build/libGstCameraPlugin.so ]; then
            echo "✓ Plugin built: ~/gazebo_gst_plugin/build/libGstCameraPlugin.so"
            echo ""
            
            # Show file info
            ls -lh ~/gazebo_gst_plugin/build/libGstCameraPlugin.so
            echo ""
            
            # Show dependencies
            echo "Plugin dependencies:"
            ldd ~/gazebo_gst_plugin/build/libGstCameraPlugin.so | grep -E "gstreamer|gazebo" | sed 's/^/  /'
            echo ""
            
            # Show environment
            echo "Gazebo plugin path:"
            echo "  $GAZEBO_PLUGIN_PATH"
            echo ""
            
            # Show usage
            echo "Usage in SDF:"
            echo '  <plugin name="gst_camera_plugin" filename="libGstCameraPlugin.so">'
            echo '    <udp_host>127.0.0.1</udp_host>'
            echo '    <udp_port>5600</udp_port>'
            echo '  </plugin>'
            echo ""
        else
            echo "✗ Plugin not found!"
            echo "Run the installation script: bash scripts/install_gazebo_gstreamer.sh"
        fi
        ;;
    
    *)
        echo "Invalid choice!"
        exit 1
        ;;
esac
