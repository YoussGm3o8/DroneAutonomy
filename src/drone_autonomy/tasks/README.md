"""
# Competition Tasks Module

Robust task execution framework for drone competitions with comprehensive implementations of common competition tasks.

## Overview

The tasks module provides a structured framework for executing competition tasks with:
- **State Management**: Robust lifecycle management with error handling
- **Performance Metrics**: Real-time monitoring and scoring
- **Safety Checks**: Altitude limits, battery monitoring, collision detection
- **Result Reporting**: Comprehensive JSON logs with task details
- **Extensibility**: Easy to create custom tasks

## Available Tasks

### 1. Target Search and Identification (`TargetSearchTask`)

**Objective**: Search for and identify red circular targets in a designated area

**Features**:
- Systematic search pattern execution
- Red circle detection with confidence scoring
- Camera centering with PID control
- GPS coordinate logging for each target
- Photo documentation with timestamps
- Duplicate target filtering

**Scoring** (0-100):
- 20 points per target found
- +10 bonus for centering accuracy (<30 pixels)
- +5 bonus for quick identification (<5 seconds)
- Time bonus: (1 - time_used/time_limit) × 10
- +10 completion bonus

**Configuration**:
```yaml
target_search:
  target_count_required: 3  # Number of targets to find
  search_altitude: 5.0  # meters
  centering_accuracy: 30  # pixels
  identification_time_bonus: 5.0  # seconds
  timeout: 300.0  # seconds (5 minutes)
```

**Usage**:
```python
from drone_autonomy.tasks import TargetSearchTask

config = {
    'target_count_required': 3,
    'search_altitude': 5.0,
    'timeout': 300.0,
    'log_dir': 'logs/target_search',
}

task = TargetSearchTask('task_1', config, telemetry, logger)
task.start()

# In main loop:
task.update(frame, depth_map, detections, target_detection)

# When complete:
result = task.stop()
print(f"Score: {result.score}/100")
```

---

### 2. Waypoint Navigation (`WaypointNavigationTask`)

**Objective**: Navigate through a sequence of GPS waypoints with precision

**Features**:
- GPS-based navigation
- Altitude maintenance
- Path deviation tracking
- Distance-to-waypoint monitoring
- Automatic waypoint advancement

**Scoring** (0-100):
- 50 points for waypoint completion ratio
- 30 points accuracy bonus (path deviation)
- 20 points time bonus

**Configuration**:
```yaml
waypoint_navigation:
  waypoints:  # List of (lat, lon, alt) tuples
    - [47.6062, -122.3321, 10.0]
    - [47.6065, -122.3325, 10.0]
    - [47.6068, -122.3329, 10.0]
  waypoint_tolerance: 2.0  # meters
  altitude_tolerance: 0.5  # meters
  timeout: 300.0
```

---

### 3. Obstacle Course Navigation (`ObstacleCourseTask`)

**Objective**: Navigate through obstacle course using vision-based avoidance

**Features**:
- Real-time obstacle detection using depth estimation
- Collision detection and tracking
- Path smoothness monitoring
- Goal-based navigation

**Scoring** (0-100):
- 50 points for course completion
- 20 points obstacle avoidance bonus
- 30 points time bonus
- -10 points per collision

**Configuration**:
```yaml
obstacle_course:
  obstacle_threshold: 2.0  # meters
  goal_position: [47.6070, -122.3330]  # (lat, lon)
  collision_penalty: 10.0
  timeout: 300.0
```

---

### 4. Precision Landing (`PrecisionLandingTask`)

**Objective**: Land precisely on a designated landing pad

**Features**:
- Landing pad detection (red circle)
- Camera centering control
- Controlled descent at specified rate
- Landing accuracy verification
- Smoothness monitoring

**Scoring** (0-100):
- 40 points for successful landing
- 30 points centering accuracy bonus
- 20 points time bonus
- 10 points smoothness bonus

**Configuration**:
```yaml
precision_landing:
  landing_altitude: 5.0  # meters - start altitude
  descent_rate: 0.5  # m/s
  centering_tolerance: 50  # pixels
  landing_tolerance: 1.0  # meters
  timeout: 180.0  # seconds (3 minutes)
```

---

## Task Manager

The `TaskManager` handles sequential execution of multiple tasks:

**Features**:
- Sequential task scheduling
- Automatic state transitions
- Score aggregation
- Competition-wide result reporting
- Configurable failure handling

**Usage**:
```python
from drone_autonomy.tasks import TaskManager, TargetSearchTask, WaypointNavigationTask

# Create manager
manager = TaskManager({
    'max_tasks': 10,
    'auto_advance': True,
    'stop_on_failure': False,
}, telemetry, logger)

# Add tasks
task1 = TargetSearchTask('task_1', config1, telemetry, logger)
task2 = WaypointNavigationTask('task_2', config2, telemetry, logger)
manager.add_task(task1)
manager.add_task(task2)

# Start competition
manager.start_competition()

# Main loop
while True:
    continue_comp = manager.update(frame, depth_map, detections, target_detection)
    if not continue_comp:
        break

# Get results
result = manager.stop_competition()
print(f"Total Score: {result.total_score}")
```

---

## Creating Custom Tasks

To create a custom task, extend the `BaseTask` class:

```python
from drone_autonomy.tasks import BaseTask, TaskStatus

class MyCustomTask(BaseTask):
    def __init__(self, task_id, config, telemetry, logger=None):
        super().__init__(
            task_id=task_id,
            task_name="My Custom Task",
            config=config,
            telemetry=telemetry,
            logger=logger
        )
        # Custom initialization
    
    def _on_start(self) -> bool:
        """Initialize task"""
        # Custom setup
        return True
    
    def _on_update(self, frame, depth_map, detections, target_detection) -> bool:
        """Update task logic"""
        # Process sensor data
        # Return True to continue, False to complete
        return True
    
    def _on_stop(self):
        """Cleanup"""
        pass
    
    def _calculate_score(self) -> float:
        """Calculate task score (0-100)"""
        return 0.0
```

---

## Running Competition Tasks

### Command Line

```bash
# Run single task
python examples/run_competition_tasks.py --tasks target_search

# Run multiple tasks in sequence
python examples/run_competition_tasks.py --tasks target_search waypoint precision

# Use webcam for testing
python examples/run_competition_tasks.py --tasks target_search --webcam

# Use AirSim simulation
python examples/run_competition_tasks.py --tasks target_search --simulation

# Headless mode (no display)
python examples/run_competition_tasks.py --tasks target_search --no-display
```

### Programmatic

```python
from drone_autonomy.tasks import TaskManager, TargetSearchTask

# Setup components (video, depth, detection, telemetry)
# ...

# Create and run task
task = TargetSearchTask('task_1', config, telemetry, logger)
task.start()

while True:
    frame = get_frame()
    depth_map = estimate_depth(frame)
    detections = detect_objects(frame)
    target = detect_target(frame)
    
    continue_task = task.update(frame, depth_map, detections, target)
    if not continue_task:
        break

result = task.stop()
```

---

## Result Format

Task results are saved as JSON:

```json
{
  "status": "completed",
  "success": true,
  "score": 85.5,
  "duration": 147.3,
  "data": {
    "task_id": "target_search_1",
    "task_name": "Target Search and Identification",
    "start_time": "2025-10-31T14:30:00",
    "end_time": "2025-10-31T14:32:27"
  },
  "metrics": {
    "frames_processed": 4419,
    "decisions_made": 156,
    "warnings_issued": 2,
    "errors_encountered": 0
  },
  "errors": [],
  "warnings": []
}
```

Competition results:

```json
{
  "total_score": 267.5,
  "tasks_completed": 3,
  "tasks_failed": 0,
  "total_duration": 542.7,
  "task_results": [...]
}
```

---

## Safety Features

All tasks include:
- **Altitude Limits**: Enforced min/max altitude bounds
- **Battery Monitoring**: Warnings for low battery
- **Timeout Protection**: Automatic task abortion on timeout
- **Error Recovery**: Retry logic with configurable attempts
- **Emergency Stop**: Immediate task abortion on safety violations
- **Telemetry Validation**: Connection and data integrity checks

---

## Performance Optimization

Tips for optimal task performance:

1. **Use Depth Anything V2 vits**: Lightest and fastest model
2. **Lower resolution**: Process depth at 480p (640×480)
3. **Frame skipping**: Process every 2nd frame if needed
4. **GPU acceleration**: Ensure CUDA is enabled
5. **Reduce logging**: Use INFO or WARNING level in production

---

## Troubleshooting

**Task not starting**:
- Check telemetry connection
- Verify safety checks pass
- Review log files for errors

**Low scores**:
- Adjust timeout values
- Tune PID gains for centering
- Calibrate depth estimation
- Check camera focus and exposure

**False target detections**:
- Adjust HSV thresholds in config
- Increase confidence requirements
- Enable duplicate filtering

**GPS navigation issues**:
- Verify GPS lock and accuracy
- Check waypoint coordinates
- Increase waypoint tolerance

---

## Examples

See `examples/run_competition_tasks.py` for complete usage example.

---

## License

MIT License - See LICENSE file for details
"""
