# Activate the virtual environment with OpenCV and GStreamer support
# Usage: .\activate_env.ps1

Write-Host "Activating DroneAutonomy virtual environment..." -ForegroundColor Green

# Activate the virtual environment
& ".\venv\Scripts\Activate.ps1"

Write-Host "Virtual environment activated!" -ForegroundColor Green
Write-Host "OpenCV and GStreamer DLL paths will be configured automatically when importing drone_autonomy" -ForegroundColor Cyan
Write-Host ""
Write-Host "DLL Paths configured:" -ForegroundColor Yellow
Write-Host "  - C:\opencv\build\bin\Release" -ForegroundColor Gray
Write-Host "  - C:\gstreamer\1.0\msvc_x86_64\bin" -ForegroundColor Gray
Write-Host ""
