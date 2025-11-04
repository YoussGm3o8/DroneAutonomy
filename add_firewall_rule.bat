@echo off
echo ============================================
echo  Adding Windows Firewall Rule for Gazebo
echo ============================================
echo.
echo This will allow UDP traffic on port 5600
echo from WSL to Windows for GStreamer video.
echo.
pause

netsh advfirewall firewall add rule name="Gazebo GStreamer UDP" dir=in action=allow protocol=UDP localport=5600

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo  SUCCESS! Firewall rule added.
    echo ============================================
    echo.
    echo You can now receive video from Gazebo!
    echo.
    echo Test with: test_gstreamer_windows.bat
    echo Or launch GUI: python launch_gui.py
    echo.
) else (
    echo.
    echo ============================================
    echo  ERROR: Failed to add firewall rule
    echo ============================================
    echo.
    echo Make sure you ran this as Administrator!
    echo Right-click this file and select "Run as administrator"
    echo.
)

pause
