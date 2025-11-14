@echo off
REM Test GStreamer UDP reception from Gazebo
echo Testing GStreamer UDP stream reception from Gazebo...
echo.
echo Listening on UDP port 5600...
echo Press Ctrl+C to stop
echo.

REM Simple UDP stream viewer using GStreamer
gst-launch-1.0 udpsrc address=0.0.0.0 port=5600 caps="application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264" ! rtpjitterbuffer ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
