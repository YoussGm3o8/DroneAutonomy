# Script to recreate venv with Python 3.11
# Run this AFTER installing Python 3.11

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Recreating Virtual Environment with Python 3.11" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Step 1: Deactivate current venv (if active)
Write-Host "`n[1/5] Deactivating current virtual environment..." -ForegroundColor Yellow
if ($env:VIRTUAL_ENV) {
    deactivate
}

# Step 2: Backup current venv (optional)
Write-Host "`n[2/5] Backing up current venv..." -ForegroundColor Yellow
if (Test-Path "venv") {
    if (Test-Path "venv_old_py313") {
        Remove-Item -Recurse -Force "venv_old_py313"
    }
    Rename-Item "venv" "venv_old_py313"
    Write-Host "  Old venv backed up to: venv_old_py313" -ForegroundColor Green
}

# Step 3: Create new venv with Python 3.11
Write-Host "`n[3/5] Creating new virtual environment with Python 3.11..." -ForegroundColor Yellow
py -3.11 -m venv venv

if (-not $?) {
    Write-Host "ERROR: Failed to create venv. Make sure Python 3.11 is installed!" -ForegroundColor Red
    Write-Host "Install from: https://www.python.org/downloads/release/python-31111/" -ForegroundColor Red
    exit 1
}

Write-Host "  Virtual environment created successfully!" -ForegroundColor Green

# Step 4: Activate new venv
Write-Host "`n[4/5] Activating new virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Step 5: Install dependencies
Write-Host "`n[5/5] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "Virtual Environment Recreation Complete!" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Python Version:" -ForegroundColor Yellow
python --version
Write-Host "`nPyTorch CUDA:" -ForegroundColor Yellow
python -c "import torch; print(f'  PyTorch: {torch.__version__}'); print(f'  CUDA available: {torch.cuda.is_available()}')"
Write-Host "`nTensorRT:" -ForegroundColor Yellow
python -c "import tensorrt as trt; print(f'  TensorRT: {trt.__version__}')"

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "Next Step: Run TensorRT conversion" -ForegroundColor Green
Write-Host "  python scripts/convert_to_tensorrt.py" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan
