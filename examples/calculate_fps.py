"""
Quick FPS calculator based on actual timings
"""

# Measured timings (after warmup)
yolo_640_time = 10  # ms
yolo_416_time = 10  # ms
depth_time = 47  # ms
target_time_old = 29  # ms (before optimization)
target_time_new = 6  # ms (after downscale optimization)
vio_time = 15  # ms (estimated)
display_time = 5  # ms (estimated)

print("=" * 80)
print("FPS CALCULATOR - Based on Real Measurements")
print("=" * 80)
print()
print("Component Timings:")
print(f"  YOLO (640):      {yolo_640_time}ms")
print(f"  YOLO (416):      {yolo_416_time}ms")
print(f"  Depth:           {depth_time}ms")
print(f"  Target (old):    {target_time_old}ms")
print(f"  Target (NEW):    {target_time_new}ms ⚡ 5x FASTER")
print(f"  VIO:             ~{vio_time}ms")
print(f"  Display:         ~{display_time}ms")
print()
print("=" * 80)
print("EXPECTED FPS - DIFFERENT MODES")
print("=" * 80)
print()

# Mode 1: Full pipeline (everything)
total_full = yolo_640_time + depth_time + target_time_new + vio_time + display_time
fps_full = 1000 / total_full
print(f"1. Full Pipeline (All features):")
print(f"   Total: {total_full}ms → {fps_full:.1f} FPS")
print()

# Mode 2: Fast mode (no depth)
total_fast = yolo_640_time + target_time_new + vio_time + display_time
fps_fast = 1000 / total_fast
print(f"2. Fast Mode (--fast, no depth):")
print(f"   Total: {total_fast}ms → {fps_fast:.1f} FPS")
print()

# Mode 3: Fast + interval 2
fps_fast_interval2 = fps_fast * 2
print(f"3. Fast + Interval=2 (--fast --interval 2):")
print(f"   Effective: {fps_fast_interval2:.1f} FPS ⚡")
print()

# Mode 4: Fast + no VIO + YOLO 416
total_ultra = yolo_416_time + target_time_new + display_time
fps_ultra = 1000 / total_ultra
print(f"4. Ultra Mode (--fast, VIO off, YOLO 416):")
print(f"   Total: {total_ultra}ms → {fps_ultra:.1f} FPS")
print()

# Mode 5: Ultra + interval 2
fps_ultra_interval2 = fps_ultra * 2
print(f"5. Ultra + Interval=2:")
print(f"   Effective: {fps_ultra_interval2:.1f} FPS ⚡⚡")
print()

# Mode 6: Detection only (skip target)
total_detect_only = yolo_416_time + display_time
fps_detect_only = 1000 / total_detect_only
print(f"6. Detection Only (YOLO 416 only, no targets):")
print(f"   Total: {total_detect_only}ms → {fps_detect_only:.1f} FPS")
print()

print("=" * 80)
print("RECOMMENDATION FOR 20+ FPS")
print("=" * 80)
print()
print("✅ Mode 3: Fast + Interval=2")
print(f"   Command: python src/drone_autonomy/pipeline.py --fast --interval 2")
print(f"   Expected FPS: {fps_fast_interval2:.1f} FPS")
print()
print("✅ Mode 5: Ultra + Interval=2")
print(f"   Command: python src/drone_autonomy/pipeline.py --fast --interval 2 --config config/high_performance.yaml")
print(f"   Expected FPS: {fps_ultra_interval2:.1f} FPS")
print()
print("=" * 80)
