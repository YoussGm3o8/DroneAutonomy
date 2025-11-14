"""
Fix ONNX model by setting fixed input/output shapes for TensorRT.
The original model has dynamic shapes which cause TensorRT conversion issues.
"""

import onnx
from onnx import helper, shape_inference
import numpy as np

print("Loading original ONNX model...")
model = onnx.load("depth_anything_v2_vits.onnx")

# Get input and output names
input_name = model.graph.input[0].name
output_name = model.graph.output[0].name

print(f"Input: {input_name}")
print(f"Output: {output_name}")

# Create fixed input shape: 1×3×518×518
print("\nSetting fixed input shape: [1, 3, 518, 518]")
model.graph.input[0].type.tensor_type.shape.dim[0].dim_value = 1
model.graph.input[0].type.tensor_type.shape.dim[1].dim_value = 3
model.graph.input[0].type.tensor_type.shape.dim[2].dim_value = 518
model.graph.input[0].type.tensor_type.shape.dim[3].dim_value = 518

# Run shape inference to propagate fixed shapes throughout the graph
print("Running shape inference...")
try:
    model = shape_inference.infer_shapes(model)
    print("✓ Shape inference complete")
except Exception as e:
    print(f"⚠ Warning: Shape inference partially failed: {e}")
    print("Continuing anyway...")

# Set fixed output shape: 1×518×518
print("Setting fixed output shape: [1, 518, 518]")
model.graph.output[0].type.tensor_type.shape.dim[0].dim_value = 1
model.graph.output[0].type.tensor_type.shape.dim[1].dim_value = 518
model.graph.output[0].type.tensor_type.shape.dim[2].dim_value = 518

# Check and validate model
print("\nValidating ONNX model...")
try:
    onnx.checker.check_model(model)
    print("✓ Model validation passed")
except Exception as e:
    print(f"⚠ Validation warning: {e}")

# Save fixed model
output_path = "depth_anything_v2_vits_fixed.onnx"
print(f"\nSaving fixed model to: {output_path}")
onnx.save(model, output_path)

print("\n" + "=" * 60)
print("✅ Fixed ONNX model created!")
print("=" * 60)
print(f"Original: depth_anything_v2_vits.onnx")
print(f"Fixed:    {output_path}")
print(f"\nFixed shapes:")
print(f"  Input:  {input_name} [1, 3, 518, 518]")
print(f"  Output: {output_name} [1, 518, 518]")
print("\nNext: Run conversion with the fixed model:")
print(f"  python scripts/convert_to_tensorrt.py --onnx-path {output_path}")
