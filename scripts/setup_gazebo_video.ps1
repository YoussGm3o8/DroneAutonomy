# Gazebo Video Fix - Quick Setup
# Run this script to install and configure everything needed for Gazebo video streaming

Write-Host "=============================================="
Write-Host "Gazebo Video Fix - Quick Setup"
Write-Host "=============================================="
Write-Host ""

# Check if WSL is available
Write-Host "Checking WSL availability..."
$wslCheck = wsl -l -v 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: WSL not found or not running" -ForegroundColor Red
    Write-Host "Please install WSL2 first: wsl --install"
    exit 1
}
Write-Host "OK: WSL is available" -ForegroundColor Green
Write-Host ""

# Step 1: Install GStreamer in WSL
Write-Host "=============================================="
Write-Host "Step 1: Installing GStreamer in WSL"
Write-Host "=============================================="
Write-Host ""

$setupScript = "C:\Users\Youssef\Documents\Code\ComputerVision\DroneAutonomy\scripts\setup_wsl_gstreamer.sh"
if (Test-Path $setupScript) {
    Write-Host "Running GStreamer setup script in WSL..."
    wsl bash -c "cd /mnt/c/Users/Youssef/Documents/Code/ComputerVision/DroneAutonomy/scripts && bash setup_wsl_gstreamer.sh"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK: GStreamer installed successfully" -ForegroundColor Green
    } else {
        Write-Host "WARNING: GStreamer installation had issues" -ForegroundColor Yellow
        Write-Host "Continue anyway? (y/n)" -ForegroundColor Yellow
        $response = Read-Host
        if ($response -ne "y") {
            exit 1
        }
    }
} else {
    Write-Host "ERROR: Setup script not found: $setupScript" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Run diagnostics
Write-Host "=============================================="
Write-Host "Step 2: Running diagnostics"
Write-Host "=============================================="
Write-Host ""

$diagScript = "C:\Users\Youssef\Documents\Code\ComputerVision\DroneAutonomy\scripts\diagnose_gstreamer.py"
if (Test-Path $diagScript) {
    Write-Host "Running diagnostic checks..."
    python $diagScript
    Write-Host ""
} else {
    Write-Host "WARNING: Diagnostic script not found: $diagScript" -ForegroundColor Yellow
}

# Step 3: Check firewall
Write-Host "=============================================="
Write-Host "Step 3: Checking Windows Firewall for UDP 5600"
Write-Host "=============================================="
Write-Host ""

$firewallRule = Get-NetFirewallRule -DisplayName "GStreamer RTP Port 5600" -ErrorAction SilentlyContinue

if ($null -eq $firewallRule) {
    Write-Host "Creating firewall rule for UDP port 5600..."
    try {
        New-NetFirewallRule -DisplayName "GStreamer RTP Port 5600" `
                           -Direction Inbound `
                           -Protocol UDP `
                           -LocalPort 5600 `
                           -Action Allow `
                           -Profile Any `
                           -ErrorAction Stop
        Write-Host "OK: Firewall rule created" -ForegroundColor Green
    } catch {
        Write-Host "WARNING: Could not create firewall rule (may need admin privileges)" -ForegroundColor Yellow
        Write-Host "Please manually allow UDP port 5600 in Windows Firewall"
    }
} else {
    Write-Host "OK: Firewall rule already exists" -ForegroundColor Green
}

Write-Host ""

# Step 4: Verify Python dependencies
Write-Host "=============================================="
Write-Host "Step 4: Checking Python dependencies"
Write-Host "=============================================="
Write-Host ""

$requiredPackages = @("opencv-contrib-python", "numpy", "PyQt6")

foreach ($package in $requiredPackages) {
    Write-Host "Checking $package..."
    $checkCmd = "python -c `"import importlib; importlib.import_module('$($package.Replace('-', '_'))')`""
    
    $result = Invoke-Expression $checkCmd 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: $package installed" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: $package not found" -ForegroundColor Yellow
    }
}

Write-Host ""

# Summary and next steps
Write-Host "=============================================="
Write-Host "Setup Complete!"
Write-Host "=============================================="
Write-Host ""
Write-Host "Summary of changes:" -ForegroundColor Cyan
Write-Host "  - Fixed GStreamer pipeline with proper RTP caps"
Write-Host "  - Added NVIDIA GPU acceleration support"
Write-Host "  - Installed GStreamer plugins in WSL"
Write-Host "  - Configured firewall for UDP port 5600"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Test the video stream:"
Write-Host "     python launch_gui.py"
Write-Host ""
Write-Host "  2. Or start components manually:"
Write-Host "     - Gazebo: python launch_gazebo.py"
Write-Host "     - GUI: python launch_gui.py"
Write-Host ""
Write-Host "  3. If issues persist, check:"
Write-Host "     python scripts/diagnose_gstreamer.py"
Write-Host ""
Write-Host "For detailed information, see:"
Write-Host "  docs/GAZEBO_VIDEO_FIX.md"
Write-Host ""

# Ask if user wants to test now
Write-Host "Would you like to test the setup now? (y/n)" -ForegroundColor Yellow
$testNow = Read-Host

if ($testNow -eq "y") {
    Write-Host ""
    Write-Host "Starting Gazebo GUI test..." -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop when done testing"
    Write-Host ""
    
    # Give user time to read
    Start-Sleep -Seconds 2
    
    # Launch GUI
    python launch_gui.py
}

Write-Host ""
Write-Host "Setup script finished!" -ForegroundColor Green
