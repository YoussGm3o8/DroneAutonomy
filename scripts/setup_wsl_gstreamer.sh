#!/bin/bash
#
# WSL GStreamer Setup Script
# Installs required GStreamer plugins, NVIDIA GPU support, and Python dependencies for the bridge.
#

echo "=============================================="
echo "WSL GStreamer & Bridge Dependencies Setup"
echo "=============================================="

# Update package list
echo "Updating package list..."
sudo apt-get update -y

# Install GStreamer base and plugins
echo ""
echo "Installing GStreamer core and plugins..."
sudo apt-get install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev

# Install GStreamer Python bindings and pip
echo ""
echo "Installing GStreamer Python bindings and pip..."
sudo apt-get install -y \
    python3-pip \
    python3-gi \
    python3-gst-1.0 \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0

# Install Python packages for the bridge script
echo ""
echo "Installing Python packages for the bridge (numpy, opencv, gz-transport)..."
pip3 install numpy opencv-python gz-transport13 gz-msgs10

# Check if NVIDIA GPU is available
echo ""
echo "Checking for NVIDIA GPU..."
if command -v nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA GPU detected"
    sudo apt-get install -y gstreamer1.0-plugins-nvcodec
else
    echo "⚠ No NVIDIA GPU detected. Hardware encoding will not be available."
fi

echo ""
echo "=============================================="
echo "Setup Complete!"
echo "=============================================="
echo "✓ GStreamer and Python dependencies for the bridge are installed in WSL."
