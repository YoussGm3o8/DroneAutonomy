# MAVProxy Router for ArduPilot SITL
# This receives MAVLink from SITL and distributes to multiple clients

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "MAVProxy Router - Connecting to ArduPilot SITL" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "Input:  UDP 127.0.0.1:14550 (ArduPilot SITL)" -ForegroundColor Yellow
Write-Host "Output: UDP 127.0.0.1:14560 (Vision Pipeline)" -ForegroundColor Yellow  
Write-Host "Output: UDP 127.0.0.1:14561 (Mission Planner)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Red
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Run MAVProxy
# Note: udpin binds to port 14550 and waits for SITL to send data
mavproxy.py `
    --master=udpin:0.0.0.0:14550 `
    --out=udp:127.0.0.1:14560 `
    --out=udp:127.0.0.1:14561 `
    --daemon
