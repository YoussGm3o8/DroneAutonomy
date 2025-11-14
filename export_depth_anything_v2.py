"""
Export Depth Anything V2 Small (ViT-S) to ONNX with FIXED shapes for TensorRT.
Based on: https://github.com/spacewalk01/depth-anything-tensorrt

This script properly exports the model with fixed 518×518 input shape,
which is required for TensorRT conversion.
"""

import argparse
import torch
import torch.onnx

# Import from local Depth-Anything-V2 folder
import sys
sys.path.insert(0, 'Depth-Anything-V2')

try:
    from depth_anything_v2.dpt import DepthAnythingV2
    print("✓ Loaded depth_anything_v2 from: Depth-Anything-V2/")
except ImportError as e:
    print(f"ERROR: depth_anything_v2 module not found: {e}")
    print("\nMake sure Depth-Anything-V2 folder exists with:")
    print("  git clone https://github.com/DepthAnything/Depth-Anything-V2")
    exit(1)


def export_to_onnx(input_size=518, model_size='vits'):
    """
    Export Depth Anything V2 to ONNX format with fixed shapes.
    
    Args:
        input_size: Fixed input size (default 518×518)
        model_size: Model variant - vitt, vits, vitb, or vitl
    """
    
    # Model configurations
    # Note: DA2 only has Small/Base/Large/Giant. No separate Tiny model.
    # vits is the smallest available model (24.8M params)
    model_configs = {
        'vits': {  # Small - 24.8M params - FASTEST AVAILABLE
            'encoder': 'vits',
            'features': 64,
            'out_channels': [48, 96, 192, 384],
            'name': 'Small (ViT-S)',
            'params': '24.8M'
        },
        'vitb': {  # Base - 97.5M params - HIGH QUALITY
            'encoder': 'vitb',
            'features': 128,
            'out_channels': [96, 192, 384, 768],
            'name': 'Base (ViT-B)',
            'params': '97.5M'
        },
        'vitl': {  # Large - 335.3M params - BEST QUALITY
            'encoder': 'vitl',
            'features': 256,
            'out_channels': [256, 512, 1024, 1024],
            'name': 'Large (ViT-L)',
            'params': '335.3M'
        }
    }
    
    config = model_configs[model_size]
    model_config = {
        'encoder': config['encoder'],
        'features': config['features'],
        'out_channels': config['out_channels']
    }
    
    print("=" * 70)
    print(f"Depth Anything V2 {config['name']} - ONNX Export for TensorRT")
    print("=" * 70)
    print(f"Model: {config['name']} ({config['params']} parameters)")
    print(f"Input size: {input_size}×{input_size}")
    print(f"Precision: FP32 (will be converted to FP16 by TensorRT)")
    print("=" * 70)
    
    print("\n[1/5] Creating model...")
    model = DepthAnythingV2(**model_config)
    
    # Load pretrained weights - try multiple locations
    checkpoint_paths = [
        f'Depth-Anything-V2/checkpoints/depth_anything_v2_{model_size}.pth',
        f'checkpoints/depth_anything_v2_{model_size}.pth',
        f'depth_anything_v2_{model_size}.pth'
    ]
    
    checkpoint_path = None
    for path in checkpoint_paths:
        import os
        if os.path.exists(path):
            checkpoint_path = path
            break
    
    if checkpoint_path is None:
        print(f"ERROR: Checkpoint not found in any of these locations:")
        for path in checkpoint_paths:
            print(f"  - {path}")
        print("\nDownload from:")
        print("  https://huggingface.co/depth-anything/Depth-Anything-V2-Small/resolve/main/depth_anything_v2_vits.pth")
        print("\nPlace it in one of the above locations")
        exit(1)
    
    print(f"\n[2/5] Loading weights from: {checkpoint_path}")
    try:
        model.load_state_dict(torch.load(checkpoint_path, map_location='cpu'))
        print("✓ Weights loaded successfully")
    except Exception as e:
        print(f"ERROR loading checkpoint: {e}")
        exit(1)
    
    model = model.to('cpu').eval()
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total parameters: {total_params / 1e6:.2f}M")
    
    # Create dummy input with FIXED BATCH SIZE
    print(f"\n[3/5] Creating dummy input: [1, 3, {input_size}, {input_size}]")
    dummy_input = torch.ones((1, 3, input_size, input_size), dtype=torch.float32)
    
    # Test forward pass
    print("\n[4/5] Testing forward pass...")
    with torch.no_grad():
        output = model.forward(dummy_input)
    print(f"✓ Output shape: {output.shape}")
    
    # Export to ONNX
    onnx_path = f'depth_anything_v2_{model_size}.onnx'
    print(f"\n[5/5] Exporting to ONNX: {onnx_path}")
    
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        opset_version=17,  # Use opset 17 for better operator support
        input_names=["input"],
        output_names=["output"],
        dynamic_axes=None,  # NO dynamic axes - fixed shapes only!
        verbose=False
    )
    
    print(f"✓ Model exported successfully!")
    
    # Verify the exported model
    print("\n" + "=" * 70)
    print("Verification:")
    print("=" * 70)
    
    import onnx
    onnx_model = onnx.load(onnx_path)
    
    # Check input shape
    input_shape = [d.dim_value for d in onnx_model.graph.input[0].type.tensor_type.shape.dim]
    output_shape = [d.dim_value for d in onnx_model.graph.output[0].type.tensor_type.shape.dim]
    
    print(f"Input shape: {input_shape} (NCHW)")
    print(f"Output shape: {output_shape}")
    print(f"ONNX opset: {onnx_model.opset_import[0].version}")
    print(f"File size: {onnx_model.ByteSize() / (1024*1024):.2f} MB")
    
    print("\n" + "=" * 70)
    print("✅ Export Complete!")
    print("=" * 70)
    print(f"ONNX model: {onnx_path}")
    print("\nNext step: Convert to TensorRT engine:")
    print(f"  python scripts/convert_to_tensorrt.py --onnx-path {onnx_path}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export Depth Anything V2 to ONNX')
    parser.add_argument('--input-size', type=int, default=518, help='Input size (default: 518)')
    parser.add_argument(
        '--model',
        type=str,
        default='vits',
        choices=['vits', 'vitb', 'vitl'],
        help='Model size: vits (Small, 24.8M - fastest), vitb (Base, 97.5M), vitl (Large, 335.3M - best quality)'
    )
    args = parser.parse_args()
    
    export_to_onnx(args.input_size, args.model)
