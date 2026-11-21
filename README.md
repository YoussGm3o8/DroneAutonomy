# DroneAutonomy

This is a real-time monocular vision pipeline for a small multirotor. A ground laptop receives the drone's camera stream and runs perception: monocular depth, YOLO detection, red-target detection and visual odometry. It then talks to ArduPilot over MAVLink, sending vision position estimates, and in guided mode it can also send velocity commands for obstacle avoidance. Input can come from RTSP/GStreamer, a webcam, or a Gazebo camera. The repo includes an ArduPilot SITL + Gazebo setup.

## Status

This is a research prototype for GPS-denied flight, not flight-qualified software.

- **Visual odometry** (`vio/vio_estimator.py`): frame-to-frame ORB features → essential matrix (RANSAC) → `recoverPose`. It is monocular, so translation is up to scale. IMU data is accepted but not yet fused, and there is no keyframing or loop closure. The class is the integration point for VINS-Mono / ORB-SLAM3.
- **Depth**: Depth Anything V2 (ViT-S) with TensorRT FP16 produces relative depth. `depth/scale_calibrator.py` converts it to metric depth using altitude from telemetry and a ground-plane fit.
- **What it can't do yet:** VO drift is unbounded, and the VO covariance is a fixed placeholder. The avoidance controller switches the vehicle to GUIDED before sending velocity commands, so test only in SITL or with a safety pilot.

## Architecture

```
GStreamer / RTSP / Gazebo camera
        │
        ▼
 video/ ──► vio/        ORB VO ─────────────► mavlink/telemetry.py ──► ArduPilot
        ├─► depth/      Depth Anything V2 (TRT)     VISION_POSITION_ESTIMATE
        ├─► detection/  YOLO (ultralytics) + HSV/Hough red-target detector
        ▼
 fusion/decision_layer.py      detections + depth → obstacle distance / approach cmd
 fusion/safety_arbitrator.py   vision vs. proximity sensors (vision-primary,
                               sensor-primary, parallel-redundant, weighted fusion)
        ▼
 navigation/   obstacle avoidance & autonomous controller → SET_POSITION_TARGET (velocity)
 gui/          PyQt6 operator GUI: video, overlays, telemetry, arm/disarm, mode
```

| Path | Contents |
|---|---|
| `src/drone_autonomy/pipeline.py` | Main loop (`DronePipeline`): frame skipping, fast mode, timing stats |
| `src/drone_autonomy/mavlink/` | pymavlink connection, telemetry, VO publishing, guided-mode commands, proximity sensors |
| `config/*.yaml` | Pipeline configs (default, high-performance, Gazebo, obstacle avoidance) |
| `gz/`, `config/gazebo/` | Gazebo test world and iris model with GStreamer camera |
| `scripts/` | SITL / Gazebo / GStreamer setup and diagnostics (Windows + WSL) |

## Run

Developed on Windows with an NVIDIA laptop GPU, with Gazebo and ArduPilot SITL running in WSL. Requires Python 3.11 (the version the setup scripts use), an OpenCV build with GStreamer, and TensorRT for depth.

```bash
pip install -r requirements.txt
pip install -e .

# Headless pipeline on the configured video source + MAVLink endpoint
python -m drone_autonomy.pipeline --config config/default_config.yaml --no-display

# Faster: skip depth, process every 2nd frame
python -m drone_autonomy.pipeline --fast --interval 2 --config config/high_performance.yaml

# Operator GUI
python launch_gui.py --video-source webcam
```

Set `video.gstreamer_pipeline` and `mavlink.connection_string` in the config. To have ArduPilot's EKF use the vision estimate, set `VISO_TYPE = 1` (MAVLink) and `EK3_SRC1_POSXY = 6` / `EK3_SRC1_VELXY = 6` (ExternalNav).

Simulation: `scripts/start_sitl.sh`, then `python launch_gazebo.py`. The Gazebo camera is streamed to the pipeline over GStreamer/UDP; see `config/gazebo/README.md`.

## Tests

`tests/unit` and `tests/integration` cover the GStreamer receive path, TensorRT depth loading, heartbeat filtering, mode changes and the MAVLink connection. Several of them need the hardware or simulator running.

## License

See [LICENSE](LICENSE).
