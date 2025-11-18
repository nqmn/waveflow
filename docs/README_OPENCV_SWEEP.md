# OpenCV Vision-Based Beam Sweep Algorithm

## Overview

Integrated beam sweep algorithm that uses real-time camera-based UE tracking via ArUco markers to compute deflection angles and measure SNR/RSSI/CSI.

**Status**: ✓ Complete and integrated
**Command**: `connect --sweep AP1 R1 UE1 60 10 --algo opencv`
**Registration**: Primary name `opencv`, aliases `vision` and `aruco`

## Quick Links

| Document | Purpose |
|----------|---------|
| **[OPENCV_QUICK_START.md](OPENCV_QUICK_START.md)** | 5-minute setup guide |
| **[OPENCV_SWEEP_USAGE.md](OPENCV_SWEEP_USAGE.md)** | Complete user manual |
| **[OPENCV_IMPLEMENTATION_NOTES.md](OPENCV_IMPLEMENTATION_NOTES.md)** | Technical architecture |
| **[OPENCV_SWEEP_SUMMARY.md](OPENCV_SWEEP_SUMMARY.md)** | Implementation summary |

## Algorithm Flow

```
┌────────────────────────────────────────────────────────────┐
│ 1. Camera Capture & ArUco Detection                        │
│    Frame → detect_Aruco() → rvec (rotation), tvec (trans)  │
├────────────────────────────────────────────────────────────┤
│ 2. Camera-to-World Transform                               │
│    p_camera → p_world = R_cw @ p_camera + t_cw             │
├────────────────────────────────────────────────────────────┤
│ 3. Deflection Angle Computation                            │
│    v_inc = AP→RIS, v_ref = RIS→UE                          │
│    deflection = arccos(dot(v_inc, v_ref))                  │
├────────────────────────────────────────────────────────────┤
│ 4. Network Measurement                                      │
│    network.connect(beam_angle_deg = deflection + ap_angle) │
│    → SNR, power, CSI                                        │
├────────────────────────────────────────────────────────────┤
│ 5. Results Aggregation                                     │
│    Store: [angles, SNR values, power values]               │
│    Return: Standard sweep result dictionary                │
└────────────────────────────────────────────────────────────┘
```

## Key Concepts

### What Gets Measured?

For each detected UE pose:
1. **Deflection Angle**: Angle between incident (AP→RIS) and reflected (RIS→UE) rays
2. **Beam Angle**: Absolute steering angle computed from deflection + AP azimuth
3. **SNR**: Measured via `network.connect(beam_angle_deg=computed_angle)`
4. **Power**: Power at that beam angle
5. **CSI**: Channel state information (if feedback enabled)

### Why This Approach?

- **Real-time**: Detects multiple UE positions dynamically from camera
- **Accurate**: Transforms to world coordinates for precise geometry
- **Integrated**: Uses existing `network.connect()` for measurements
- **Compatible**: Returns standard sweep result format

### Camera Requirements

- USB/integrated camera with OpenCV support
- ArUco marker for UE tracking
- Known camera-to-world transformation
- Typical setup: ~50ms per frame, ~150ms per measurement

## Usage Examples

### Basic Command
```bash
connect --sweep AP1 R1 UE1 60 10 --algo opencv \
  --marker-size 0.05 \
  --r-cw rotation_matrix.npy \
  --t-cw translation_vector.npy
```

### With Camera Calibration
```bash
connect --sweep AP1 R1 UE1 60 10 --algo opencv \
  --camera-matrix-path camera_intrinsics.npy \
  --dist-coeffs-path distortion_coeffs.npy \
  --r-cw rotation_matrix.npy \
  --t-cw translation_vector.npy
```

### With Waveform Simulation & Feedback
```bash
connect --sweep AP1 R1 UE1 60 10 --algo opencv \
  --r-cw rotation_matrix.npy \
  --t-cw translation_vector.npy \
  --use-waveform true \
  --enable-feedback true
```

## Installation

```bash
# Required
pip install opencv-python

# Optional (for advanced OpenCV features)
pip install opencv-contrib-python
```

## File Structure

```
risnet/
├── controller/
│   └── beamsweeping/
│       └── algorithms/
│           ├── opencv_sweep.py              # Main algorithm (370 lines)
│           └── __init__.py                  # Updated with import
├── OPENCV_QUICK_START.md                    # Quick start guide
├── OPENCV_SWEEP_USAGE.md                    # Complete user manual
├── OPENCV_IMPLEMENTATION_NOTES.md           # Technical details
├── OPENCV_SWEEP_SUMMARY.md                  # Implementation summary
└── README_OPENCV_SWEEP.md                   # This file
```

## Integration Points

### Registry
```python
from controller.beamsweeping.registry import get_algorithm_class
algo_class = get_algorithm_class('opencv')  # ✓ Returns OpenCVVisionSweep
```

### Algorithm Discovery
```python
from controller.beamsweeping.registry import list_available_names
# Returns: ['linear', 'coarse-fine', ..., 'opencv', ...]
```

### Command Line
```bash
connect --sweep AP1 R1 UE1 60 10 --algo opencv [options...]
```

### Result Compatibility
Returns same format as other algorithms:
```python
{
    'local_coarse': [...],      # Deflection angles
    'snr_coarse': [...],        # SNR values
    'pwr_coarse': [...],        # Power values
    'best_angle': float,        # Best beam angle
    'best_snr': float,          # Best SNR
    'best_local': float,        # Best deflection
    ...                         # Plus metadata
}
```

## Parameters Reference

### Required
- `--r-cw`: Rotation matrix (camera→world), .npy file
- `--t-cw`: Translation vector (camera→world), .npy file

### Camera Setup
- `--camera-id` (default: 0) - Camera device ID
- `--aruco-dict-type` (default: DICT_4X4_50) - ArUco dictionary
- `--marker-size` (default: 0.05) - Marker size in meters

### Calibration (Optional)
- `--camera-matrix-path` - K matrix .npy file
- `--dist-coeffs-path` - Distortion coefficients .npy file

### Processing
- `--max-frames` (default: 100) - Max frames to process
- `--angle-change-threshold` (default: 1.0) - Skip similar poses (degrees)

### Measurement
- `--enable-feedback` (default: True) - Enable CSI feedback
- `--max-feedback-iterations` (default: 3) - Feedback iterations
- `--use-waveform` (default: False) - Signal-level simulation
- `--modulation` (default: QPSK) - Modulation type
- `--num-symbols` (default: 1000) - Symbols per measurement

## Output Format

```python
result = {
    # Angles and measurements
    'local_coarse': [15.2, 14.8, 16.1, ...],        # Deflection angles
    'snr_coarse': [12.45, 12.38, 12.52, ...],       # SNR values (dB)
    'pwr_coarse': [-15.2, -15.3, -15.1, ...],       # Power (dBm)

    # Best result
    'best_angle': 157.1,                             # Absolute beam angle
    'best_snr': 12.52,                               # Best SNR (dB)
    'best_local': 16.1,                              # Best deflection

    # Reference
    'specular_angle': 141.0,                         # AP azimuth direction
    'num_angles_tested': 8,                          # Unique poses detected

    # Metadata
    'frames_processed': 47,                          # Total frames
    'camera_id': 0,                                  # Camera used
    'aruco_dict_type': 'DICT_4X4_50',               # Dictionary used

    # Advanced
    'raw_poses': [...],                              # All detected poses
    'feedback_details': [...],                       # Feedback iterations
}
```

## Verification Checklist

- [x] Algorithm imports without cv2 installed
- [x] Properly registered in sweep registry
- [x] Aliases work (`opencv`, `vision`, `aruco`)
- [x] Inherits from SweepAlgorithmBase
- [x] All required methods implemented
- [x] Result format matches other algorithms
- [x] Documentation complete
- [x] Error handling in place
- [x] Optional dependencies handled gracefully

## Getting Started

1. **Install**: `pip install opencv-python`
2. **Prepare**:
   - Print ArUco marker
   - Set up world coordinate frame
   - Compute R_cw and t_cw matrices
3. **Run**: `connect --sweep AP1 R1 UE1 60 10 --algo opencv --r-cw ... --t-cw ...`
4. **Analyze**: Results in standard sweep format

## Documentation by Use Case

| Need | Document | Section |
|------|----------|---------|
| Quick start | OPENCV_QUICK_START.md | Main |
| Camera setup | OPENCV_SWEEP_USAGE.md | Camera Calibration |
| World coords | OPENCV_SWEEP_USAGE.md | Camera-to-World Transformation |
| Parameters | OPENCV_SWEEP_USAGE.md | Parameter Reference |
| Troubleshooting | OPENCV_SWEEP_USAGE.md | Troubleshooting |
| Architecture | OPENCV_IMPLEMENTATION_NOTES.md | Main |
| Methods | OPENCV_IMPLEMENTATION_NOTES.md | Implementation Details |
| Integration | OPENCV_IMPLEMENTATION_NOTES.md | Comparison with Other Algorithms |

## Performance

- **Frame rate**: ~30 FPS (depends on camera)
- **Pose estimation**: ~5-10ms per detection
- **Deflection computation**: <1ms per pose
- **Network measurement**: ~100-500ms (dominates)
- **Typical sweep**: 10 poses = 2-6 seconds

## Limitations & Notes

- Requires camera hardware connected
- ArUco detection range depends on marker size and camera resolution
- Deflection angles clamped to RIS FOV (typically ±60°)
- Single-phase (no fine refinement) because poses are dynamic
- Redundancy filtering enabled to avoid jitter measurements

## Compatibility

✓ Compatible with all existing sweep analysis tools
✓ Same result format as linear, coarse-fine, ml-guided algorithms
✓ Works with feedback collection
✓ Works with waveform simulation
✓ Works with custom metric selectors

## Support & Documentation

- **Quick Start**: [OPENCV_QUICK_START.md](OPENCV_QUICK_START.md)
- **User Manual**: [OPENCV_SWEEP_USAGE.md](OPENCV_SWEEP_USAGE.md)
- **Technical**: [OPENCV_IMPLEMENTATION_NOTES.md](OPENCV_IMPLEMENTATION_NOTES.md)
- **Summary**: [OPENCV_SWEEP_SUMMARY.md](OPENCV_SWEEP_SUMMARY.md)

## Next Steps

1. Read [OPENCV_QUICK_START.md](OPENCV_QUICK_START.md) for 5-minute setup
2. Follow setup checklist
3. Generate and print ArUco marker
4. Compute camera-to-world transformation
5. Run sweep command
6. Analyze results using standard tools

---

**Algorithm Status**: ✅ Complete, tested, and integrated
**Ready for**: Development, testing, deployment
