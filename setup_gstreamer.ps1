# PowerShell wrapper for GStreamer Camera Plugin installation and management
# Run this from Windows to manage the Gazebo GStreamer plugin on WSL

param(
    [Parameter(Position=0)]
    [ValidateSet("install", "test", "quickstart", "view", "help")]
    [string]$Action = "help"
)

function Show-Help {
    Write-Host ""
    Write-Host "======================================"
    Write-Host "Gazebo GStreamer Plugin Manager"
    Write-Host "======================================"
    Write-Host ""
    Write-Host "Usage: .\setup_gstreamer.ps1 [action]"
    Write-Host ""
    Write-Host "Actions:"
    Write-Host "  install     - Install Gazebo and GstCameraPlugin on WSL"
    Write-Host "  test        - Run installation tests"
    Write-Host "  quickstart  - Interactive quick start menu"
    Write-Host "  view        - View GStreamer stream (requires GStreamer on Windows)"
    Write-Host "  help        - Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\setup_gstreamer.ps1 install"
    Write-Host "  .\setup_gstreamer.ps1 test"
    Write-Host "  .\setup_gstreamer.ps1 quickstart"
    Write-Host ""
}

function Install-Plugin {
    Write-Host ""
    Write-Host "======================================"
    Write-Host "Installing Gazebo GStreamer Plugin"
    Write-Host "======================================"
    Write-Host ""
    Write-Host "This will:"
    Write-Host "  1. Install Gazebo 11 on WSL"
    Write-Host "  2. Install GStreamer and dependencies"
    Write-Host "  3. Build the GstCameraPlugin"
    Write-Host "  4. Configure environment"
    Write-Host ""
    Write-Host "This may take 10-15 minutes..."
    Write-Host ""
    
    $confirm = Read-Host "Continue? (y/n)"
    if ($confirm -ne "y") {
        Write-Host "Installation cancelled."
        return
    }
    
    Write-Host ""
    Write-Host "Starting installation on WSL..."
    Write-Host ""
    
    wsl bash scripts/install_gazebo_gstreamer.sh
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "======================================"
        Write-Host "Installation Complete!"
        Write-Host "======================================"
        Write-Host ""
        Write-Host "Next steps:"
        Write-Host "  1. Test installation: .\setup_gstreamer.ps1 test"
        Write-Host "  2. Quick start: .\setup_gstreamer.ps1 quickstart"
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "Installation failed! Check the output above for errors."
        Write-Host ""
    }
}

function Test-Installation {
    Write-Host ""
    Write-Host "Running installation tests..."
    Write-Host ""
    
    wsl bash scripts/test_gstreamer_setup.sh
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "All tests passed! [OK]"
    } else {
        Write-Host ""
        Write-Host "Some tests failed. See output above."
    }
}

function Start-QuickStart {
    Write-Host ""
    Write-Host "Launching interactive quick start..."
    Write-Host ""
    
    wsl bash scripts/quickstart_gstreamer.sh
}

function View-Stream {
    Write-Host ""
    Write-Host "======================================"
    Write-Host "GStreamer Video Stream Viewer"
    Write-Host "======================================"
    Write-Host ""
    
    # Check if GStreamer is installed on Windows
    $gstPath = Get-Command gst-launch-1.0.exe -ErrorAction SilentlyContinue
    
    if ($gstPath) {
        Write-Host "Starting GStreamer viewer on port 5600..."
        Write-Host "Press Ctrl+C to stop"
        Write-Host ""
        
        & gst-launch-1.0.exe udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink
    } else {
        Write-Host "GStreamer not found on Windows!"
        Write-Host ""
        Write-Host "Options:"
        Write-Host ""
        Write-Host "1. Install GStreamer for Windows:"
        Write-Host "   Download from: https://gstreamer.freedesktop.org/download/"
        Write-Host ""
        Write-Host "2. Use VLC Media Player:"
        Write-Host "   Open VLC → Media → Open Network Stream"
        Write-Host "   Enter: udp://@:5600"
        Write-Host ""
        Write-Host "3. Use FFmpeg/FFplay:"
        Write-Host "   ffplay -fflags nobuffer -flags low_delay udp://127.0.0.1:5600"
        Write-Host ""
        Write-Host "4. Use the WSL viewer:"
        Write-Host "   wsl bash scripts/quickstart_gstreamer.sh"
        Write-Host "   Select option 3"
        Write-Host ""
    }
}

# Main script execution
switch ($Action) {
    "install" {
        Install-Plugin
    }
    "test" {
        Test-Installation
    }
    "quickstart" {
        Start-QuickStart
    }
    "view" {
        View-Stream
    }
    "help" {
        Show-Help
    }
    default {
        Show-Help
    }
}
