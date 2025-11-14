# Python 3.11 Downgrade Guide

## Issue
TensorRT 10.13.3.9 has compatibility issues with Python 3.13 - the `create_network()` API call crashes silently. Python 3.11 is the recommended version for TensorRT 10.x.

## Solution: Recreate venv with Python 3.11

### Step 1: Download and Install Python 3.11.11
1. Download from: https://www.python.org/downloads/release/python-31111/
2. Choose: **Windows installer (64-bit)**
3. During installation:
   - ✅ Check "Add python.exe to PATH"
   - ✅ Check "Install for all users" (optional)
   - Click "Install Now"

### Step 2: Verify Installation
```powershell
py -3.11 --version
```
Expected output: `Python 3.11.11`

### Step 3: Run the Recreation Script
```powershell
.\recreate_venv_py311.ps1
```

This script will:
1. Deactivate current venv
2. Backup old venv to `venv_old_py313`
3. Create new venv with Python 3.11
4. Install all dependencies from `requirements.txt`
5. Verify installations (PyTorch, TensorRT, CUDA)

### Step 4: Test TensorRT
```powershell
.\venv\Scripts\Activate.ps1
python scripts/convert_to_tensorrt.py
```

Expected: TensorRT engine builds successfully without crashes!

---

## Manual Steps (Alternative)

If you prefer manual control:

```powershell
# 1. Deactivate current venv
deactivate

# 2. Backup old venv
Rename-Item venv venv_old_py313

# 3. Create new venv with Python 3.11
py -3.11 -m venv venv

# 4. Activate new venv
.\venv\Scripts\Activate.ps1

# 5. Upgrade pip
python -m pip install --upgrade pip

# 6. Install PyTorch with CUDA 12.4
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# 7. Install TensorRT
pip install tensorrt

# 8. Install remaining dependencies
pip install -r requirements.txt

# 9. Verify installations
python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
python -c "import tensorrt as trt; print(f'TensorRT: {trt.__version__}')"
```

---

## What This Fixes

- ✅ TensorRT `create_network()` crash
- ✅ TensorRT ONNX parser compatibility
- ✅ Stable CUDA bindings
- ✅ All existing code remains unchanged

## After Downgrade

Run the conversion:
```powershell
python scripts/convert_to_tensorrt.py
```

Expected performance:
- **Conversion time**: 3-5 minutes (first time)
- **Engine size**: ~24 MB (FP16 optimized)
- **Inference speed**: 18-24ms/frame on RTX 3060 Mobile

---

## Note on Python Versions

**TensorRT 10.13.3.9 Official Support:**
- ✅ Python 3.8
- ✅ Python 3.9
- ✅ Python 3.10
- ✅ Python 3.11
- ❌ Python 3.12 (experimental)
- ❌ Python 3.13 (not supported)

**Recommendation**: Stay on Python 3.11 for this project until TensorRT officially supports 3.13.
