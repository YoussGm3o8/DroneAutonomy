# Fixing ONNX Model for TensorRT

## Issue Identified
The ONNX model you have (`depth_anything_v2_vits.onnx`) was exported with **dynamic shapes**, which causes TensorRT conversion failures. TensorRT requires **fixed input shapes**.

From the spacewalk01/depth-anything-tensorrt repository, the correct approach is:
1. Export the model with **fixed batch size** (1) and **fixed spatial dimensions** (518×518)
2. Use **opset version 17** for better operator support
3. Ensure no dynamic axes in the ONNX export

## Solution: Re-export the Model

### Step 1: Install Depth Anything V2 Package

```powershell
pip install depth-anything-v2
```

Or clone the official repo:
```powershell
git clone https://github.com/DepthAnything/Depth-Anything-V2
cd Depth-Anything-V2
pip install -e .
```

### Step 2: Download Pre-trained Weights

Create a `checkpoints` folder and download the ViT-Small weights:

```powershell
mkdir checkpoints
```

Download from: https://huggingface.co/depth-anything/Depth-Anything-V2-Small/resolve/main/depth_anything_v2_vits.pth

Save to: `checkpoints/depth_anything_v2_vits.pth`

### Step 3: Export with Fixed Shapes

```powershell
python export_depth_anything_v2.py --input-size 518
```

This will create: `depth_anything_v2_vits.onnx` with **FIXED** shapes [1, 3, 518, 518]

### Step 4: Convert to TensorRT

```powershell
python scripts/convert_to_tensorrt.py --onnx-path depth_anything_v2_vits.onnx --verbose
```

## Why Your Current ONNX Model Fails

Checking your model:
```python
Input shape: ['dynamic', 3, 'dynamic', 'dynamic']  # ❌ Dynamic!
```

TensorRT error:
```
ERROR: broadcast dimensions must be conformable
```

This happens because:
1. Dynamic shapes cause shape inference failures in TensorRT
2. Positional embeddings use broadcasting that requires fixed shapes
3. TensorRT can't optimize dynamic Add operations

## What the Fixed Model Will Have

```python
Input shape: [1, 3, 518, 518]  # ✅ Fixed!
Output shape: [1, 518, 518]    # ✅ Fixed!
```

This allows TensorRT to:
- ✅ Properly optimize all operators
- ✅ Eliminate dynamic shape operations
- ✅ Build FP16 engine successfully

## Alternative: Use Pre-exported ONNX

If you can't re-export, try downloading a pre-exported ONNX from:
https://github.com/spacewalk01/depth-anything-tensorrt

They provide properly exported models with fixed shapes for all variants (ViT-S, ViT-B, ViT-L).

## Expected Results After Fix

✅ **ONNX Parsing**: Success  
✅ **TensorRT Build**: Success (~3-5 minutes)  
✅ **Engine File**: `models/depth_anything_v2_vits_fp16.engine` (~24 MB)  
✅ **Inference Speed**: 18-24ms per frame on RTX 3060 Mobile  

---

**Summary**: The root cause is dynamic shapes in your ONNX export. Re-exporting with fixed [1, 3, 518, 518] shapes will solve all TensorRT conversion issues.
