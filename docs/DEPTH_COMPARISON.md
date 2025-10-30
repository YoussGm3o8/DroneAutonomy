# Depth Anything V2 Performance Analysis

## Summary

Depth Anything V2 was tested as a replacement for MiDaS for depth estimation in the autonomous drone navigation pipeline. While Depth Anything V2 offers superior depth quality, it comes with a significant performance penalty.

## Performance Comparison

### Standalone Depth Estimation (640x480 input)
| Model | Avg Time | FPS | Relative Speed |
|-------|----------|-----|----------------|
| **MiDaS Small** | 19.44ms | 51.4 FPS | **1.0x (baseline)** |
| **Depth Anything V2 (vits)** | 71.30ms | 14.0 FPS | **0.27x (3.67x slower)** |

### Standalone Depth Estimation (1920x1080 input)
| Model | Avg Time | FPS | Relative Speed |
|-------|----------|-----|----------------|
| **MiDaS Small** | 38.61ms | 25.9 FPS | **1.0x (baseline)** |
| **Depth Anything V2 (vits)** | 132.76ms | 7.5 FPS | **0.19x (3.44x slower)** |

### Full Pipeline Performance (YOLO + Depth)
**With Depth Anything V2:**
- **Total Pipeline**: 132.72ms (7.53 FPS)
- **Detection**: 11.75ms (8.9%)
- **Depth**: 120.97ms (91.1%) ← **Major Bottleneck**

**With MiDaS (Previous Baseline):**
- **Total Pipeline**: ~60-80ms (12-16 FPS)
- **Detection**: ~12ms (15-20%)
- **Depth**: ~47ms (60-70%)

## Analysis

### Why is Depth Anything V2 Slower?

1. **Vision Transformer Architecture**: 
   - Even the smallest vits variant uses a Vision Transformer encoder
   - ViT has quadratic complexity with image patch count
   - MiDaS uses lightweight CNN (EfficientNet-lite3)

2. **Preprocessing Overhead**:
   - Complex transform pipeline (Resize → Normalize → PrepareForNet)
   - Runs every frame without caching
   - Device detection overhead in image2tensor()

3. **Output Interpolation**:
   - Always interpolates depth map back to input resolution (1920x1080)
   - Bilinear interpolation on GPU is still expensive at full resolution
   - Cannot be disabled in the standard API

4. **Model Size**:
   - vits: 99.2MB checkpoint
   - 64 feature channels through the network
   - More parameters than MiDaS_small despite being "smallest" variant

### Quality vs Performance Trade-off

**Depth Anything V2 Advantages:**
- Superior depth quality (trained on 1.5M+ diverse images)
- Better generalization to diverse scenes
- More accurate relative depth estimation
- Better edge preservation

**MiDaS Advantages:**
- **3.5x faster** inference time
- Lower memory footprint
- Simpler preprocessing
- Proven performance in drone applications

## Recommendations

### Option 1: Keep MiDaS (Recommended for Real-time Autonomous Navigation)
**Pros:**
- 3.5x faster (critical for 10-20 FPS autonomous control)
- Proven performance in existing pipeline
- Lower latency for obstacle avoidance
- Better for battery-constrained drones

**Cons:**
- Slightly lower depth quality in challenging scenes
- Less robust to lighting variations

### Option 2: Use Depth Anything V2 for High-Quality Mode
**Use cases:**
- Mapping missions (offline processing acceptable)
- High-precision target localization
- When quality > speed (inspection, surveying)
- Post-processing and analysis

**Implementation:**
- Add `--high-quality-depth` flag to pipeline
- Use MiDaS for real-time, DA-V2 for recording
- Configurable via `config/high_quality.yaml`

### Option 3: Optimize Depth Anything V2
**Potential optimizations:**
1. **Export to ONNX/TensorRT**: Could gain 2-3x speedup
2. **Reduce input resolution**: Use 320x320 instead of 518x518
3. **Skip output interpolation**: Keep depth at lower resolution
4. **Batch processing**: Process multiple frames together
5. **Model quantization**: INT8 inference (FP16 → INT8)

**Estimated best-case**: 40-60ms (still slower than MiDaS)

## Implementation Status

### Completed
✅ Full Depth Anything V2 integration
✅ Dual model support (MiDaS + DA-V2)
✅ Configuration system for model selection
✅ Comprehensive performance testing
✅ Backward compatibility maintained

### Current Configuration
All config files updated to `depth_anything_v2_vits`:
- `config/default_config.yaml`
- `config/high_performance.yaml`
- `config/airsim_simulation.yaml`
- `config/airsim_sitl.yaml`

### Code Changes
- `depth_estimator.py`: Refactored with dual model support
- `requirements.txt`: Added depth-anything-v2, huggingface-hub
- Test scripts created for performance validation

## Decision

**For autonomous navigation with obstacle avoidance, recommend reverting to MiDaS** due to the critical importance of low-latency depth estimation (3-5ms makes the difference between collision and safe avoidance at drone speeds).

**However, keep Depth Anything V2 available** as an optional high-quality mode for specific use cases.

## Next Steps

1. **Create separate config profiles**:
   - `real_time.yaml` → MiDaS (default for autonomous)
   - `high_quality.yaml` → Depth Anything V2 (for mapping/analysis)

2. **Update documentation** to explain when to use each model

3. **Consider TensorRT optimization** if DA-V2 is needed for real-time use

4. **Test both models** in actual flight scenarios to validate quality differences

## Files
- Performance test: `examples/test_depth_performance.py`
- Pipeline test: `examples/test_pipeline_performance.py`
- Depth estimator: `src/drone_autonomy/depth/depth_estimator.py`
- This analysis: `docs/DEPTH_COMPARISON.md`

---
*Analysis Date: 2025-10-30*
*System: NVIDIA GPU (CUDA), 1920x1080 processing resolution*
