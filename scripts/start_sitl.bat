@echo off
REM ArduPilot SITL Launcher for Windows
REM This script properly launches SITL in a new WSL window
REM Removed --map --console flags to avoid NumPy/matplotlib GUI issues

echo Starting ArduPilot SITL...
wsl bash -c "export PATH=\"$HOME/.local/bin:$PATH\" && cd ~/ardupilot && Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I0"
pause
