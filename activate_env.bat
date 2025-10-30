@echo off
REM Activate the virtual environment with OpenCV and GStreamer support
REM Usage: activate_env.bat

echo Activating DroneAutonomy virtual environment...
call venv\Scripts\activate.bat

echo.
echo Virtual environment activated!
echo OpenCV and GStreamer DLL paths will be configured automatically when importing drone_autonomy
echo.
echo DLL Paths configured:
echo   - C:\opencv\build\bin\Release
echo   - C:\gstreamer\1.0\msvc_x86_64\bin
echo.
