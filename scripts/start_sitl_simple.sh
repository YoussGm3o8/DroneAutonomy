#!/bin/bash
# Start ArduPilot SITL with built-in physics (no external simulator needed)
# This will allow Mission Planner to connect immediately

cd ~/ardupilot

echo "Stopping any existing SITL instances..."
pkill -9 arducopter
sleep 1

echo "Starting ArduPilot SITL with built-in physics (no AirSim)..."
echo "This will work immediately for testing Mission Planner!"
echo ""
echo "MAVLink Outputs:"
echo "  UDP 14550 - Primary"
echo "  UDP 14551 - Mission Planner"
echo "  TCP 5760  - Alternative"
echo ""

./Tools/autotest/sim_vehicle.py \
    --vehicle ArduCopter \
    --model + \
    --speedup 1 \
    --out=udp:127.0.0.1:14550 \
    --out=udp:127.0.0.1:14551 \
    --out=tcp:0.0.0.0:5760 \
    --console \
    --map
