@echo off
REM ArduPilot SITL Launcher for Windows (No GUI modules)
REM This script launches SITL without console/map GUI modules to avoid NumPy issues

echo Starting ArduPilot SITL (No GUI)...
wsl bash -c "export PATH=\"$HOME/.local/bin:$PATH\" && cd ~/ardupilot && Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I0"
pause
