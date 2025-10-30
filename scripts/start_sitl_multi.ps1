# Start ArduPilot SITL with AirSim physics and multiple MAVLink outputs
# This allows simultaneous connections from:
#   - UDP 14550: Vision pipeline
#   - UDP 14551: Mission Planner / QGroundControl  
#   - TCP 5760: Alternative connection

# Navigate to ArduPilot directory
cd ~/ardupilot

# Kill any existing SITL instances
Write-Host "Stopping any existing SITL instances..." -ForegroundColor Yellow
wsl bash -c "pkill -9 arducopter"
Start-Sleep -Seconds 1

# Start ArduPilot SITL with multiple outputs
Write-Host "Starting ArduPilot SITL with AirSim physics..." -ForegroundColor Green
Write-Host ""
Write-Host "MAVLink Outputs:" -ForegroundColor Cyan
Write-Host "  UDP 14550 - Vision Pipeline" -ForegroundColor White
Write-Host "  UDP 14551 - Mission Planner / QGC" -ForegroundColor White
Write-Host "  TCP 5760  - Alternative connection" -ForegroundColor White
Write-Host ""

# Run SITL in WSL
wsl bash -c "cd ~/ardupilot && ./Tools/autotest/sim_vehicle.py --vehicle ArduCopter --model airsim-copter --speedup 1 --out=udp:127.0.0.1:14550 --out=udp:127.0.0.1:14551 --out=tcp:0.0.0.0:5760 --sim-address=127.0.0.1 --console --map"
