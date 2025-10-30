#!/usr/bin/env python3
"""Test pipeline initialization and basic functionality."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from drone_autonomy.pipeline import DronePipeline
from drone_autonomy.utils.logger import setup_logging

print("=" * 80)
print("DroneAutonomy Pipeline Test")
print("=" * 80)
print()

# Setup logging
setup_logging(log_level='INFO')

# Create pipeline
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'default_config.yaml')
print(f"Loading config from: {config_path}")
print()

try:
    pipeline = DronePipeline(config_path)
    print("✓ Pipeline object created successfully")
    print()
    
    # Initialize pipeline
    print("Initializing pipeline components...")
    if pipeline.initialize():
        print("✓ Pipeline initialized successfully")
        print()
        
        # Test with a few frames
        print("Running pipeline for 10 frames...")
        pipeline.run(display=True, max_frames=10)
        
        print()
        print("✓ Pipeline test completed successfully")
    else:
        print("✗ Pipeline initialization failed")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Error during pipeline test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 80)
