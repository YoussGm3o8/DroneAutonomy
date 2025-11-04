@echo off
title ArduPilot SITL
echo ========================================
echo   ArduPilot SITL Starting...
echo ========================================
echo.
wsl bash -c "export PATH=\"$HOME/.local/bin:$PATH\" && cd ~/ardupilot && Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I0"
echo.
echo SITL terminated.
pause
