# ArduPilot SITL Launcher for Windows
# Launches SITL in a new WSL window with proper command execution
# Removed --map --console flags to avoid NumPy/matplotlib GUI issues

Write-Host "Starting ArduPilot SITL..." -ForegroundColor Green

# Method 1: Try Windows Terminal if available
$wtExists = Get-Command wt.exe -ErrorAction SilentlyContinue
if ($wtExists) {
    Write-Host "Using Windows Terminal..." -ForegroundColor Cyan
    Start-Process wt.exe -ArgumentList "wsl bash -c 'export PATH=`"$HOME/.local/bin:$PATH`" && cd ~/ardupilot && Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I0'"
} else {
    # Method 2: Use standard WSL
    Write-Host "Using WSL..." -ForegroundColor Cyan
    Start-Process wsl -ArgumentList "bash -c 'export PATH=`"$HOME/.local/bin:$PATH`" && cd ~/ardupilot && Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I0'"
}

Write-Host "SITL terminal opened. Check the new window." -ForegroundColor Green
Write-Host "Press any key to close this window..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
