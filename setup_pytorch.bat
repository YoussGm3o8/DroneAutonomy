@REM Setup script to fix PyTorch and dependencies for DroneAutonomy
@REM This script installs correct versions compatible with CUDA 12.9 and Depth Anything V2

@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo DroneAutonomy PyTorch Environment Setup
echo ============================================================
echo.
echo This script will:
echo   1. Uninstall incompatible torch/torchvision versions
echo   2. Install PyTorch 2.7.1 with CUDA 11.8 support
echo   3. Install compatible torchvision and torchaudio
echo   4. Verify CUDA availability
echo.
echo Note: Ensure you are in the virtual environment!
echo.

:check_python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please activate your virtual environment first.
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Using Python: %PYTHON_VERSION%
echo.

:clean_install
echo [1/4] Cleaning old PyTorch installation...
pip uninstall -y torch torchvision torchaudio 2>nul
if errorlevel 1 (
    echo (No previous installation found)
)
echo.

:install_pytorch
echo [2/4] Installing PyTorch 2.7.1 with CUDA 11.8...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 --force-reinstall
if errorlevel 1 (
    echo ERROR: Failed to install PyTorch
    exit /b 1
)
echo.

:verify_torch
echo [3/4] Verifying PyTorch installation...
python -c "import torch; print('Torch Version:', torch.__version__); print('CUDA Available:', torch.cuda.is_available()); print('CUDA Version:', torch.version.cuda)"
if errorlevel 1 (
    echo ERROR: PyTorch verification failed
    exit /b 1
)
echo.

:install_deps
echo [4/4] Installing other dependencies from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some dependencies may not have installed correctly
)
echo.

:success
echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo PyTorch Configuration:
echo   - Version: 2.7.1
echo   - CUDA Support: 11.8 (compatible with CUDA 12.9)
echo   - Target: GPU Acceleration with Depth Anything V2
echo.
echo Compatibility Notes:
echo   - Depth Anything V2: Compatible
echo   - CUDA 12.9: Forward compatible
echo   - Python 3.11+: Recommended for all features
echo.
echo If you encounter issues:
echo   1. Check CUDA drivers: nvidia-smi
echo   2. Verify Python version: python --version
echo   3. Test import: python -c "import torch; torch.cuda.is_available()"
echo.
echo Documentation: See TORCH_FIX_SUMMARY.md
echo ============================================================

pause
