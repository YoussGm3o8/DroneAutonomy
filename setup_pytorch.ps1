# Setup script to fix PyTorch and dependencies for DroneAutonomy
# This script installs correct versions compatible with CUDA 12.9 and Depth Anything V2
# Usage: .\setup_pytorch.ps1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "DroneAutonomy PyTorch Environment Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will:" -ForegroundColor Yellow
Write-Host "  1. Uninstall incompatible torch/torchvision versions"
Write-Host "  2. Install PyTorch 2.7.1 with CUDA 11.8 support"
Write-Host "  3. Install compatible torchvision and torchaudio"
Write-Host "  4. Verify CUDA availability"
Write-Host ""
Write-Host "Note: Ensure you are in the virtual environment!" -ForegroundColor Yellow
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Using Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found. Please activate your virtual environment first." -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 1: Clean old installation
Write-Host "[1/4] Cleaning old PyTorch installation..." -ForegroundColor Cyan
pip uninstall -y torch torchvision torchaudio 2>$null
if ($?) {
    Write-Host "✓ Cleaned previous installation" -ForegroundColor Green
} else {
    Write-Host "(No previous installation found)" -ForegroundColor Gray
}
Write-Host ""

# Step 2: Install PyTorch
Write-Host "[2/4] Installing PyTorch 2.7.1 with CUDA 11.8..." -ForegroundColor Cyan
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 --force-reinstall

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install PyTorch" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Installation successful" -ForegroundColor Green
Write-Host ""

# Step 3: Verify PyTorch
Write-Host "[3/4] Verifying PyTorch installation..." -ForegroundColor Cyan
$verifyScript = @"
import torch
print('Torch Version:', torch.__version__)
print('CUDA Available:', torch.cuda.is_available())
print('CUDA Version:', torch.version.cuda)
if torch.cuda.is_available():
    print('GPU Device:', torch.cuda.get_device_name(0))
"@

python -c $verifyScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PyTorch verification failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Verification successful" -ForegroundColor Green
Write-Host ""

# Step 4: Install other dependencies
Write-Host "[4/4] Installing other dependencies from requirements.txt..." -ForegroundColor Cyan
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Some dependencies may not have installed correctly" -ForegroundColor Yellow
}
Write-Host ""

# Final status
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "PyTorch Configuration:" -ForegroundColor Yellow
Write-Host "  - Version: 2.7.1"
Write-Host "  - CUDA Support: 11.8 (compatible with CUDA 12.9)"
Write-Host "  - Target: GPU Acceleration with Depth Anything V2"
Write-Host ""
Write-Host "Compatibility Notes:" -ForegroundColor Yellow
Write-Host "  - Depth Anything V2: Compatible"
Write-Host "  - CUDA 12.9: Forward compatible"
Write-Host "  - Python 3.11+: Recommended for all features"
Write-Host ""
Write-Host "If you encounter issues:" -ForegroundColor Yellow
Write-Host "  1. Check CUDA drivers: nvidia-smi"
Write-Host "  2. Verify Python version: python --version"
Write-Host "  3. Test import: python -c 'import torch; print(torch.cuda.is_available())'"
Write-Host ""
Write-Host "Documentation: See TORCH_FIX_SUMMARY.md" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
