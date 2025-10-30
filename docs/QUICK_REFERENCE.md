# Quick Reference: Running DroneAutonomy

## Choose Your Mode

### 🚁 Real Drone Mode
**When to use:** Flying with physical drone and RTSP camera

```bash
# Standard (2-3 FPS, full features)
python src/drone_autonomy/pipeline.py

# High Performance (20+ FPS)
python src/drone_autonomy/pipeline.py --fast --interval 2 --config config/high_performance.yaml
```

**Config:** `config/default_config.yaml` or `config/high_performance.yaml`

---

### 🎮 Simulation Mode (AirSim)
**When to use:** Testing without drone, development, training

```bash
# Standard simulation
python examples/test_airsim_pipeline.py

# High Performance (20-30 FPS)
python examples/test_airsim_pipeline.py --fast --interval 2
```

**Config:** `config/airsim_simulation.yaml`

**Prerequisites:**
1. Install: `pip install airsim`
2. Launch AirSim simulator
3. Run test script

---

## Command Line Options

```bash
python src/drone_autonomy/pipeline.py [OPTIONS]

Options:
  --config PATH       Config file (default: auto-detect)
  --fast             Skip depth estimation (2.4x faster)
  --interval N       Process every Nth frame (Nx faster)
  --no-display       Headless mode
  --max-frames N     Process N frames then exit
```

---

## Performance Comparison

| Mode | Command | FPS | Features |
|------|---------|-----|----------|
| Full | `pipeline.py` | 2-3 | All features (depth + detection) |
| Fast | `pipeline.py --fast` | 6-7 | Detection only |
| Fast+Interval | `pipeline.py --fast --interval 2` | 12-15 | Every 2nd frame |
| High Perf | `--fast --interval 2 --config high_performance.yaml` | 20+ | Optimized config |

---

## Quick Troubleshooting

### Real Drone Issues

**Camera not connecting:**
```bash
# Check RTSP stream
ffplay rtsp://192.168.1.231:8554/1

# Verify GStreamer
python tests/test_dll_setup.py
```

**MAVLink not connecting:**
- Check UDP port 14550 is available
- Try USB ports (COM5, COM6) - auto-detected
- Verify heartbeat from drone

### Simulation Issues

**AirSim not connecting:**
1. Is AirSim simulator running?
2. Check port 41451 is available
3. Verify `simulation.enabled: true` in config

---

## Configuration Files

| File | Purpose | When to Use |
|------|---------|-------------|
| `default_config.yaml` | Full quality, real drone | Standard operation |
| `high_performance.yaml` | Speed optimized, real drone | 20+ FPS requirement |
| `airsim_simulation.yaml` | AirSim simulation | Testing without drone |

---

## Example Workflows

### Development Testing
```bash
# 1. Test in simulation first
python examples/test_airsim_pipeline.py --fast --max-frames 50

# 2. Verify detection working
# (Check display window for bounding boxes)

# 3. Deploy to real drone
python src/drone_autonomy/pipeline.py --fast
```

### Flight Operations
```bash
# High-performance real-time detection
python src/drone_autonomy/pipeline.py --fast --interval 2 --config config/high_performance.yaml
```

### Data Collection
```bash
# Full pipeline with all sensors
python src/drone_autonomy/pipeline.py --config config/default_config.yaml
```

---

## Documentation Links

- **Setup:** [VENV_SETUP.md](docs/VENV_SETUP.md)
- **Usage:** [USAGE_GUIDE.md](docs/USAGE_GUIDE.md)
- **Simulation:** [AIRSIM_SIMULATION.md](docs/AIRSIM_SIMULATION.md)
- **Performance:** [USAGE_GUIDE.md#achieving-20-fps-checklist](docs/USAGE_GUIDE.md)

---

## Need Help?

1. Check logs in `logs/` directory
2. Review documentation in `docs/`
3. Run test scripts in `examples/`
4. Verify environment with `tests/test_dll_setup.py`
