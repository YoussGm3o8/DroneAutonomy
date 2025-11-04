"""
Analyze the dpt_swin2_tiny_256.pt checkpoint structure
"""

import torch
import os

def analyze_checkpoint():
    """Analyze the checkpoint to understand its structure."""
    
    checkpoint_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'dpt_swin2_tiny_256.pt'
    )
    checkpoint_path = os.path.abspath(checkpoint_path)
    
    print("=" * 60)
    print("Analyzing checkpoint: dpt_swin2_tiny_256.pt")
    print("=" * 60)
    
    if not os.path.exists(checkpoint_path):
        print(f"ERROR: Checkpoint not found at {checkpoint_path}")
        return
    
    print(f"\nFile: {checkpoint_path}")
    file_size_mb = os.path.getsize(checkpoint_path) / (1024 * 1024)
    print(f"Size: {file_size_mb:.2f} MB")
    
    # Load checkpoint
    print("\nLoading checkpoint...")
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
    
    # Analyze structure
    print("\nCheckpoint type:", type(checkpoint))
    
    if isinstance(checkpoint, dict):
        print("\nTop-level keys:")
        for key in checkpoint.keys():
            value = checkpoint[key]
            if isinstance(value, dict):
                print(f"  {key}: dict with {len(value)} keys")
            elif isinstance(value, torch.Tensor):
                print(f"  {key}: Tensor {value.shape}")
            else:
                print(f"  {key}: {type(value)}")
        
        # Find the state dict
        if 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
            print("\nUsing 'state_dict' key")
        elif 'model' in checkpoint:
            state_dict = checkpoint['model']
            print("\nUsing 'model' key")
        else:
            state_dict = checkpoint
            print("\nUsing checkpoint directly as state_dict")
    else:
        state_dict = checkpoint
        print("\nCheckpoint is directly a state dict")
    
    # Analyze state dict keys
    print(f"\nState dict has {len(state_dict)} keys")
    
    # Sample keys
    print("\nFirst 10 keys:")
    for i, key in enumerate(list(state_dict.keys())[:10]):
        tensor = state_dict[key]
        if isinstance(tensor, torch.Tensor):
            print(f"  {key}: {tensor.shape}")
        else:
            print(f"  {key}: {type(tensor)}")
    
    # Analyze architecture from keys
    print("\nDetecting architecture from keys...")
    
    # Check for specific patterns
    has_swin = any('swin' in k.lower() for k in state_dict.keys())
    has_vit = any('vit' in k.lower() for k in state_dict.keys())
    has_resnet = any('resnet' in k.lower() for k in state_dict.keys())
    has_pretrained = any('pretrained' in k for k in state_dict.keys())
    
    print(f"  Has 'swin' keys: {has_swin}")
    print(f"  Has 'vit' keys: {has_vit}")
    print(f"  Has 'resnet' keys: {has_resnet}")
    print(f"  Has 'pretrained' keys: {has_pretrained}")
    
    # Check layer structure
    if has_pretrained:
        pretrained_keys = [k for k in state_dict.keys() if k.startswith('pretrained.')]
        print(f"\n  Pretrained model keys: {len(pretrained_keys)}")
        
        # Check for swin-specific layers
        layers_keys = [k for k in pretrained_keys if 'layers.' in k]
        if layers_keys:
            # Extract layer numbers
            import re
            layer_nums = set()
            for key in layers_keys:
                match = re.search(r'layers\.(\d+)\.', key)
                if match:
                    layer_nums.add(int(match.group(1)))
            print(f"  Number of Swin layers: {len(layer_nums)}")
            print(f"  Layer indices: {sorted(layer_nums)}")
            
            # Check dimensions of first layer
            downsample_keys = [k for k in layers_keys if 'downsample' in k and 'weight' in k]
            if downsample_keys:
                print(f"\n  Sample downsample layer shapes:")
                for key in downsample_keys[:3]:
                    print(f"    {key}: {state_dict[key].shape}")
    
    # Try to determine exact model type
    print("\nLikely model architecture:")
    
    # Check specific layer dimensions
    if 'pretrained.model.layers.0.blocks.0.attn.relative_position_bias_table' in state_dict:
        shape = state_dict['pretrained.model.layers.0.blocks.0.attn.relative_position_bias_table'].shape
        print(f"  Window size indicator: {shape}")
    
    if 'pretrained.model.patch_embed.proj.weight' in state_dict:
        shape = state_dict['pretrained.model.patch_embed.proj.weight'].shape
        print(f"  Patch embed shape: {shape}")
        embed_dim = shape[0]
        print(f"  Embedding dimension: {embed_dim}")
        
        # Swin Tiny: 96, Small: 96, Base: 128, Large: 192
        if embed_dim == 96:
            print("  → Likely Swin Transformer Tiny or Small")
        elif embed_dim == 128:
            print("  → Likely Swin Transformer Base")
        elif embed_dim == 192:
            print("  → Likely Swin Transformer Large")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    analyze_checkpoint()
