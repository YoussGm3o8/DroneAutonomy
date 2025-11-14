@echo off
REM Test GStreamer with detailed debug output

echo Testing GStreamer pipeline with debug info...
echo.

REM Set debug level
set GST_DEBUG=3

echo Starting pipeline...
echo If video doesn't appear, check the error messages below:
echo.

gst-launch-1.0 -v udpsrc address=0.0.0.0 port=5600 ! "application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264, payload=(int)96" ! rtpjitterbuffer latency=0 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink sync=false

pause
