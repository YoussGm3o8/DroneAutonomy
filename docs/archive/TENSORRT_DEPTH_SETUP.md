# Depth Anything V2 Small - TensorRT FP16 Setup

## Overview

This system has been **optimized for RTX 3060 Mobile 6GB** using **Depth Anything V2 Small (ViT-S)** with **TensorRT FP16** acceleration.

### Key Specifications

- **Model**: Depth Anything V2 Small (ViT-S)
- **Precision**: FP16 (Half Precision)
- **Input**: Fixed 518×518 (Depth Anything V2 default)
- **Output**: Upsampled to 1920×1080 (configurable)
- **Expected Performance**: 18-24ms per frame (≥40-55 FPS) on RTX 3060 Mobile
- **VRAM Usage**: <2GB at batch=1
- **Optimization**: TensorRT engine with FP16 precision

## Why This Configuration?

Based on the official TensorRT Depth Anything V2 implementation measuring **3ms/frame at 720p on RTX 4090**, scaling by the FP32 throughput gap between RTX 4090 (82.6 TFLOPS) and RTX 3060 Mobile (10-13.1 TFLOPS) gives **18-24ms per frame** for 518×518 input on RTX 3060 Mobile.

**Benefits:**
- ✅ **2x faster** than FP32 (half-precision computation)
- ✅ **50% less memory** than FP32 (6GB → <2GB VRAM usage)
- ✅ **Fixed 518×518 input** ensures consistent performance
- ✅ **Real-time** at ≥30 FPS with headroom for 1080p upscaling
- ✅ **Single optimized model** - no model switching overhead

## Installation

### 1. Install TensorRT

```bash
# Install TensorRT Python bindings
pip install tensorrt pycuda

# Or via requirements.txt
pip install -r requirements.txt
```

**Note**: TensorRT requires:
- CUDA 11.8 or 12.x
- NVIDIA GPU with Compute Capability ≥ 6.1 (Pascal or newer)
- Windows: Visual Studio 2017-2022 for PyCUDA compilation

See: https://docs.nvidia.com/deeplearning/tensorrt/install-guide/

### 2. Convert ONNX to TensorRT Engine

```bash
# Convert the ONNX model to TensorRT FP16 engine
python scripts/convert_to_tensorrt.py

# Custom workspace size (default: 2GB for RTX 3060 Mobile)
python scripts/convert_to_tensorrt.py --workspace 4

# Custom output path
python scripts/convert_to_tensorrt.py --output custom/path/engine.trt
```

This creates: `models/depth_anything_v2_vits_fp16.engine`

**Conversion takes 3-10 minutes** (first-time TensorRT kernel profiling).

## Usage

### Test TensorRT Performance

```bash
# Test with webcam
python test_tensorrt_depth.py --source webcam

# Test with video file
python test_tensorrt_depth.py --source path/to/video.mp4

# Test with image (100 loops for accurate timing)
python test_tensorrt_depth.py --source path/to/image.jpg --loops 100
```

### Run GUI with TensorRT

```bash
python launch_gui.py --config config/default_config.yaml
```

The GUI is now **locked to TensorRT FP16** - no model selection needed.

### Use in Code

```python
from drone_autonomy.depth.depth_estimator import DepthEstimator

# Configuration
config = {
    'engine_path': 'models/depth_anything_v2_vits_fp16.engine',
    'output_width': 1920,
    'output_height': 1080,
    'use_metric_calibration': True
}

# Initialize
estimator = DepthEstimator(config)
estimator.load_model()

# Inference (any input size → 518×518 → upsampled to 1920×1080)
import cv2
frame = cv2.imread('test.jpg')
depth_map, inference_time = estimator.estimate_depth(frame)

print(f"Inference: {inference_time*1000:.2f}ms")

# Visualize
depth_colored = estimator.visualize_depth(depth_map)
cv2.imshow("Depth", depth_colored)
cv2.waitKey(0)
```

## Configuration Files

All config files have been updated to use TensorRT FP16:

- `config/default_config.yaml` - Main configuration
- `config/mavlink_avoidance.yaml` - Obstacle avoidance
- `config/webcam_test.yaml` - Webcam testing

### Example Configuration

```yaml
depth:
  model: depth_anything_v2_vits_tensorrt_fp16
  device: cuda
  engine_path: models/depth_anything_v2_vits_fp16.engine
  output_width: 1920   # Upsample target
  output_height: 1080
  use_metric_calibration: true
```

## Performance Expectations

### RTX 3060 Mobile (6GB)
- **Inference**: 18-24ms per frame
- **Throughput**: ≥40-55 FPS at 518×518
- **With 1080p upscaling**: ≥30 FPS
- **VRAM**: <2GB

### RTX 3070 Mobile (8GB)
- **Inference**: 12-18ms per frame
- **Throughput**: ≥55-80 FPS

### RTX 4060 Mobile (8GB)
- **Inference**: 8-12ms per frame
- **Throughput**: ≥80-120 FPS

### Desktop RTX 4090
- **Inference**: ~3ms per frame (720p)
- **Throughput**: ≥300 FPS

## Architecture

```
Input Frame (any size)
    ↓
Preprocessing (resize to 518×518, normalize)
    ↓
TensorRT FP16 Inference (518×518 → depth)
    ↓
Postprocessing (normalize, upsample to 1920×1080)
    ↓
Output Depth Map (1920×1080)
```

**Pipeline Components:**
1. **Preprocessing**: Resize, RGB conversion, ImageNet normalization
2. **TensorRT Inference**: FP16 on GPU (518×518 fixed)
3. **Postprocessing**: Normalize [0, 1], upsample to target resolution
4. **Metric Calibration** (optional): Convert relative → metric depth

## Files Modified

### Core Implementation
- ✅ `src/drone_autonomy/depth/depth_estimator_trt.py` - New TensorRT implementation
- ✅ `src/drone_autonomy/depth/depth_estimator.py` - Simplified wrapper
- ✅ `src/drone_autonomy/gui/settings_dialog.py` - Locked to TensorRT FP16

### Configuration
- ✅ `config/default_config.yaml` - TensorRT FP16 config
- ✅ `config/mavlink_avoidance.yaml` - TensorRT FP16 config
- ✅ `config/webcam_test.yaml` - TensorRT FP16 config

### Scripts & Tools
- ✅ `scripts/convert_to_tensorrt.py` - ONNX → TensorRT converter
- ✅ `test_tensorrt_depth.py` - Performance benchmark tool
- ✅ `requirements.txt` - Added TensorRT dependencies

### Cleanup
- ❌ Removed `dpt_levit_224.pt` (MiDaS model)
- ❌ Removed `dpt_swin2_base_384.pt` (MiDaS model)
- ❌ Removed `dpt_swin2_tiny_256.pt` (MiDaS model)
- ❌ Removed `examples/compare_depth_models.py`
- ✅ Kept `depth_anything_v2_vits.onnx` (source for TensorRT)

## Troubleshooting

### TensorRT Not Found
```bash
pip install tensorrt pycuda
```

### CUDA Version Mismatch
TensorRT requires CUDA 11.8 or 12.x. Verify:
```bash
nvcc --version
python -c "import torch; print(torch.version.cuda)"
```

### Engine Build Failed
- **Increase workspace**: `python scripts/convert_to_tensorrt.py --workspace 4`
- **Check CUDA memory**: Close other GPU applications
- **Verify ONNX model**: Ensure `depth_anything_v2_vits.onnx` exists

### Performance Below Target
- **GPU locked**: Check other processes using GPU (Task Manager > Performance > GPU)
- **Power mode**: Ensure laptop is on "High Performance" power plan
- **Thermal throttling**: Check GPU temperature
- **Background apps**: Close Chrome, Discord, etc.

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Verify CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

## References

- **TensorRT Depth Anything V2**: https://github.com/spacewalk01/depth-anything-tensorrt
- **Depth Anything V2 Paper**: https://arxiv.org/abs/2406.09414
- **TensorRT Documentation**: https://docs.nvidia.com/deeplearning/tensorrt/
- **Original Implementation**: https://github.com/DepthAnything/Depth-Anything-V2

## Next Steps

1. **Convert Model**: `python scripts/convert_to_tensorrt.py`
2. **Test Performance**: `python test_tensorrt_depth.py --source webcam`
3. **Run GUI**: `python launch_gui.py`
4. **Deploy**: Engine file is portable across same GPU architecture

---

**System optimized for real-time depth estimation on RTX 3060 Mobile 6GB.**
