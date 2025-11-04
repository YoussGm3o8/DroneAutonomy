# Add Windows Firewall Rule for Gazebo GStreamer
# RIGHT-CLICK and "Run as Administrator"

Write-Host "Adding Windows Firewall rule for Gazebo GStreamer..." -ForegroundColor Cyan

try {
    New-NetFirewallRule `
        -DisplayName "Gazebo GStreamer UDP 5600" `
        -Description "Allow incoming UDP video stream from Gazebo in WSL" `
        -Direction Inbound `
        -Protocol UDP `
        -LocalPort 5600 `
        -Action Allow `
        -Enabled True `
        -ErrorAction Stop
    
    Write-Host ""
    Write-Host "SUCCESS! Firewall rule added." -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now receive video from Gazebo!" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Test it:" -ForegroundColor Yellow
    Write-Host "  .\activate_env.ps1" -ForegroundColor Gray
    Write-Host "  py test_gstreamer_reception.py" -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "ERROR: Could not add firewall rule" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure you ran this script as Administrator!" -ForegroundColor Yellow
    Write-Host "Right-click the script and select 'Run as Administrator'" -ForegroundColor Yellow
}

Write-Host "Press any key to close..."
$null = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
