#!/usr/bin/env python3
"""
Fix Gazebo environment in WSL ~/.bashrc
"""
import subprocess

# Read current bashrc
result = subprocess.run(['wsl', 'cat', '~/.bashrc'], capture_output=True, text=True)
bashrc_lines = result.stdout.split('\n')

# Remove any existing GZ_SIM lines
bashrc_lines = [line for line in bashrc_lines if 'GZ_SIM' not in line and 'Gazebo paths' not in line]

# Add correct Gazebo environment
gazebo_config = [
    '',
    '# Gazebo paths for ardupilot_gazebo',
    'export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/gz_ws/src/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH}',
    'export GZ_SIM_RESOURCE_PATH=$HOME/gz_ws/src/ardupilot_gazebo/models:$HOME/gz_ws/src/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH}',
    ''
]

# Combine
new_bashrc = '\n'.join(bashrc_lines + gazebo_config)

# Write back
proc = subprocess.Popen(['wsl', 'tee', '~/.bashrc'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
proc.communicate(input=new_bashrc)

print("✓ Updated ~/.bashrc with correct Gazebo paths")
print("\nAdded lines:")
for line in gazebo_config:
    if line.strip():
        print(f"  {line}")

# Verify
print("\nVerifying...")
result = subprocess.run(['wsl', 'bash', '-c', 'tail -6 ~/.bashrc'], capture_output=True, text=True)
print("\nLast 6 lines of ~/.bashrc:")
print(result.stdout)

# Test the paths
print("\nTesting environment with login shell...")
result = subprocess.run(['wsl', 'bash', '-l', '-c', 'echo "GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH"'], 
                       capture_output=True, text=True)
print(result.stdout)

if result.stdout.strip().endswith('='):
    print("⚠ WARNING: Environment variable is empty!")
else:
    print("✓ Environment variable is set correctly")
