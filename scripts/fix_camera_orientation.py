#!/usr/bin/env python3
"""Fix camera orientation in iris_with_camera model to face forward."""

import os
import re

# Path to model file
model_path = os.path.expanduser('~/gz_ws/src/ardupilot_gazebo/models/iris_with_camera/model.sdf')

print(f"📄 Reading {model_path}")

# Read file
with open(model_path, 'r') as f:
    content = f.read()

# Fix camera pose - change pitch from 0.52 (downward ~30°) to 0 (forward-facing)
old_pose = '<pose relative_to="iris_with_standoffs::base_link">0.15 0 -0.05 0 0.52 0</pose>'
new_pose = '<pose relative_to="iris_with_standoffs::base_link">0.15 0 0 0 0 0</pose>'

if old_pose in content:
    content = content.replace(old_pose, new_pose)
    print("✓ Fixed camera pitch: 0.52 rad (30° down) → 0 rad (forward)")
    print("✓ Adjusted camera height: -0.05m → 0m (centered on drone)")
else:
    print("⚠ Camera pose not found or already modified")

# Write file
with open(model_path, 'w') as f:
    f.write(content)

print(f"✓ Updated {model_path}")
print("\n📝 Camera is now mounted:")
print("   - Position: 0.15m forward, 0m right, 0m up (centered)")
print("   - Rotation: 0° roll, 0° pitch, 0° yaw (facing forward)")
print("\n🔄 Restart Gazebo to apply changes")
