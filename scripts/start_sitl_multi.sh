#!/bin/bash
# Start ArduPilot SITL with AirSim physics and multiple MAVLink outputs
# This allows simultaneous connections from:
#   - UDP 14550: Vision pipeline
#   - UDP 14551: Mission Planner / QGroundControl
#   - TCP 5760: Alternative connection

# Navigate to ArduPilot directory
cd ~/ardupilot

# Kill any existing SITL instances
echo "Stopping any existing SITL instances..."
pkill -9 arducopter
sleep 1

# Start ArduPilot SITL with multiple outputs
echo "Starting ArduPilot SITL with AirSim physics..."
echo ""
echo "MAVLink Outputs:"
echo "  UDP 14550 - Vision Pipeline"
echo "  UDP 14551 - Mission Planner / QGC"
echo "  TCP 5760  - Alternative connection"
echo ""

# Run SITL
./Tools/autotest/sim_vehicle.py \
    --vehicle ArduCopter \
    --model airsim-copter \
    --speedup 1 \
    --out=udp:127.0.0.1:14550 \
    --out=udp:127.0.0.1:14551 \
    --out=tcp:0.0.0.0:5760 \
    --sim-address=127.0.0.1 \
    --console \
    --map

# Alternative without sim_vehicle.py wrapper:
# ./build/sitl/bin/arducopter \
#     --model airsim-copter \
#     --speedup 1 \
#     --out=udp:127.0.0.1:14550 \
#     --out=udp:127.0.0.1:14551 \
#     --out=tcp:0.0.0.0:5760 \
#     --sim-address=127.0.0.1 \
#     --defaults Tools/autotest/default_params/copter.parm,Tools/autotest/default_params/airsim-quadX.parm
