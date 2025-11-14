# Depth Anything V2 Model Selection - GUI Integration

## Overview

Successfully integrated **Depth Anything V2 Small and Base models** with **TensorRT FP16** into the GUI settings dialog. Users can now select between two optimized models based on their performance vs. quality requirements.

## Models Available

### Small Model (ViT-S) - Speed Optimized
- **Parameters**: 24.8M
- **Engine Size**: 50.35 MB
- **Performance**: 38.66ms/frame (25.9 FPS) - Tested on RTX 3060 Mobile
- **VRAM**: <1GB
- **Best for**: Real-time obstacle avoidance, fast navigation, limited GPU memory
- **Engine file**: `models/depth_anything_v2_vits_fp16.engine`

### Base Model (ViT-B) - Quality Optimized
- **Parameters**: 97.5M (4x larger than Small)
- **Engine Size**: 188.51 MB
- **Performance**: ~50-60ms/frame (~15-20 FPS estimated)
- **VRAM**: <2GB
- **Best for**: High-quality depth maps, detailed environment mapping, offline processing
- **Engine file**: `models/depth_anything_v2_vitb_fp16.engine`

## Implementation Details

### Files Modified

1. **`src/drone_autonomy/gui/settings_dialog.py`**
   - Updated `depth_model_combo` to show both Small and Base models
   - Added dynamic model descriptions showing parameters, performance, and use cases
   - Enabled model selection (was previously locked to Small only)

2. **`src/drone_autonomy/depth/depth_estimator_trt.py`**
   - Added `model_type` attribute extraction from config
   - Maps model name to correct TensorRT engine path:
     - `vits` → `models/depth_anything_v2_vits_fp16.engine`
     - `vitb` → `models/depth_anything_v2_vitb_fp16.engine`

3. **`src/drone_autonomy/depth/depth_estimator.py`**
   - Updated wrapper to expose `model_type` attribute for GUI detection
   - Properly passes model configuration to TensorRT backend

### Model Selection UI

**Settings Dialog → Depth Estimation Tab**

```
Depth Estimation Model:
┌─────────────────────────────────────────────────────┐
│ Depth Anything V2 Small (Fast - 25 FPS)           ▼│
│ Depth Anything V2 Base (Quality - ~15-20 FPS)      │
└─────────────────────────────────────────────────────┘

Model Description:
┌─────────────────────────────────────────────────────┐
│ 🚀 Small Model - Speed Optimized                    │
│ • Parameters: 24.8M                                 │
│ • Engine Size: 50.35 MB                             │
│ • Fixed 518×518 input (native DA2 resolution)      │
│ • TensorRT FP16 precision                           │
│ • Measured: 38.66ms/frame (25.9 FPS)               │
│ • VRAM: <1GB                                        │
│                                                     │
│ Best for: Real-time obstacle avoidance, fast       │
│ navigation, limited GPU memory                      │
└─────────────────────────────────────────────────────┘
```

### Model Switching Logic

The GUI uses the existing model switching infrastructure in `main_window.py` (lines 1586-1611):

1. **Detection**: Reads current `model_type` attribute from depth estimator
2. **Comparison**: Checks if selected model differs from current
3. **Reload**: Creates new estimator with updated config if changed
4. **Update**: Replaces `video_thread.depth_estimator` with new instance

```python
# From main_window.py line 1586
current_model = getattr(self.video_thread.depth_estimator, 'model_type', None)
new_model = depth_config.get('model')

if current_model != new_model or self.video_thread.depth_estimator is None:
    # Create new estimator with new config
    new_estimator = DepthEstimator(depth_config_full)
    if new_estimator.load_model():
        self.video_thread.depth_estimator = new_estimator
```

## Testing

### Test Script: `test_model_selection.py`

Verifies:
- ✓ Small model (vits) correctly maps to `depth_anything_v2_vits_fp16.engine`
- ✓ Base model (vitb) correctly maps to `depth_anything_v2_vitb_fp16.engine`
- ✓ `model_type` attribute properly set for GUI detection
- ✓ Model switching logic works as expected

**Test Results**: All tests passed ✓

```
======================================================================
✓ All model selection tests PASSED
======================================================================

Summary:
  • Small model (vits): maps to depth_anything_v2_vits_fp16.engine
  • Base model (vitb): maps to depth_anything_v2_vitb_fp16.engine
  • model_type attribute correctly set for GUI detection
  • Model switching logic verified
```

## Usage Instructions

### For End Users

1. **Launch GUI**: `python launch_gui.py` or `python -m drone_autonomy.gui`
2. **Open Settings**: Menu → Tools → Settings (or `Ctrl+,`)
3. **Select Model**: Navigate to "Depth Estimation" tab
4. **Choose Model**:
   - **Small (Fast)**: For real-time operations, obstacle avoidance, live navigation
   - **Base (Quality)**: For detailed mapping, offline processing, high-quality depth
5. **Apply**: Click "Apply" or "OK" to reload model
6. **Wait**: Model will reload on next frame (1-2 seconds)

### For Developers

#### Configuration Format

```python
depth_config = {
    'model': 'depth_anything_v2_vits_tensorrt_fp16',  # or 'vitb'
    'device': 'cuda',
    'output_width': 518,
    'output_height': 518,
    'use_metric_calibration': False
}

estimator = DepthEstimator(depth_config)
estimator.load_model()
```

#### Model Name Mapping

| Config Value | Model Variant | Engine Path |
|--------------|---------------|-------------|
| `depth_anything_v2_vits_tensorrt_fp16` | Small (ViT-S) | `models/depth_anything_v2_vits_fp16.engine` |
| `depth_anything_v2_vitb_tensorrt_fp16` | Base (ViT-B) | `models/depth_anything_v2_vitb_fp16.engine` |

#### Accessing Model Type

```python
# Read current model type
current_model = estimator.model_type  # 'vits' or 'vitb'

# Check if model change needed
new_model_name = 'depth_anything_v2_vitb_tensorrt_fp16'
new_model_type = 'vitb' if 'vitb' in new_model_name else 'vits'

if current_model != new_model_type:
    # Reload estimator with new config
    pass
```

## Performance Comparison

| Metric | Small (ViT-S) | Base (ViT-B) |
|--------|---------------|--------------|
| Parameters | 24.8M | 97.5M |
| Engine Size | 50.35 MB | 188.51 MB |
| Inference Time | 38.66ms | ~50-60ms (est.) |
| FPS | 25.9 | ~15-20 (est.) |
| VRAM | <1GB | <2GB |
| Quality | Good | Excellent |
| Use Case | Real-time | Offline/Quality |

## Next Steps

1. ✅ GUI integration complete
2. ⚠️ **TODO**: Benchmark Base model performance
   - Run: `python test_tensorrt_depth.py --engine models/depth_anything_v2_vitb_fp16.engine`
   - Verify expected ~50-60ms inference time
   - Document actual performance on RTX 3060 Mobile

3. ⚠️ **TODO**: Update configuration files
   - Add model selection to `config/default_config.yaml`
   - Document model trade-offs in comments

4. ⚠️ **TODO**: Test GUI model switching
   - Launch GUI with Small model
   - Switch to Base in settings
   - Verify proper reload and inference

## Technical Notes

- **Fixed Input Size**: Both models use 518×518 input (DA2 native resolution)
- **TensorRT FP16**: Half-precision for 2x speedup and 50% memory reduction
- **Native Output**: Default 518×518 output (no upsampling overhead)
- **Dynamic Upsampling**: Can optionally upscale to 1080p in settings
- **CUDA 12.4**: Compatible with PyTorch 2.6.0+cu124 and TensorRT 10.14.1
- **Python 3.11.9**: Required for TensorRT compatibility (not 3.13)

## References

- TensorRT optimization: `TENSORRT_OPTIMIZATION_RESULTS.md`
- Model export: `export_depth_anything_v2.py`
- TensorRT conversion: `scripts/convert_to_tensorrt.py`
- Performance benchmark: `test_tensorrt_depth.py`
- Original implementation: spacewalk01/depth-anything-tensorrt
