# ⚾ Baseball Mocap Pipeline

A complete motion capture processing pipeline for baseball biomechanics analysis, converting Cooper's mocap data into Blender-ready BVH files optimized for MetaHuman retargeting.

## 🎯 Features

- **Smart Data Processing**: Auto-detects frame/joint counts (~900 frames, ~84 joints)
- **Format Handling**: Strips BOM and skips headers automatically
- **Coordinate Conversion**: Y-up → Z-up transformation for Blender compatibility
- **Scaling**: Centimeter → meter conversion (0.01 scale factor)
- **BVH Export**: Clean BVH with root joint (6 channels) + child joints (3 channels)
- **Blender Integration**: Direct import with MetaHuman preparation
- **MetaHuman Ready**: Optimized for UE5 retargeting workflow

## 📁 Project Structure

```
mocap-project/
│
├── data/
│   ├── jointcenterscooper.txt    # Joint positions (cm, Y-up)
│   ├── jointrotationscooper.txt  # Joint rotations (degrees, Y-up)
│   └── baseballspecificcooper.txt # Baseball-specific metadata
│
├── scripts/
│   ├── bvh_exporter.py          # Python BVH converter
│   └── blender_importer.py      # Blender integration script
│
└── README.md                    # This file
```

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Python dependencies
pip install numpy

# For Blender script (built-in)
# Blender 3.0+ recommended
```

### 2. Convert Mocap Data to BVH

```bash
cd mocap-project/scripts

# Basic conversion
python bvh_exporter.py ../data/jointcenterscooper.txt ../data/jointrotationscooper.txt output_full_joints.bvh

# The script will:
# ✓ Auto-detect 900 frames, 84 joints
# ✓ Strip BOM and headers
# ✓ Convert Y-up → Z-up coordinates
# ✓ Scale cm → meters (0.01)
# ✓ Generate clean BVH with proper hierarchy
```

### 3. Import in Blender

1. **Open Blender** (3.0+)
2. **Load Script**: Go to Scripting workspace → Open `scripts/blender_importer.py`
3. **Run Script**: Click ▶️ Run
4. **Use Pipeline**: Open 3D Viewport sidebar (N key) → "Baseball Mocap" tab
5. **Import**: Click "Process Complete Pipeline" → Select your BVH file

## 📊 Data Format Details

### Input Files

#### jointcenterscooper.txt
```
# Cooper Baseball Motion Capture Data - Joint Centers
# Format: X Y Z coordinates in centimeters (Y-up coordinate system)
# Total Joints: 84, Total Frames: 900, Frame Rate: 30 FPS

0.000 105.234 -2.345 5.123 112.567 -1.987 ... (84 joints × 3 coords per frame)
1.123 105.789 -2.210 6.234 113.123 -1.854 ... (next frame)
```

#### jointrotationscooper.txt
```
# Cooper Baseball Motion Capture Data - Joint Rotations  
# Format: X Y Z Euler angles in degrees (Y-up coordinate system)
# Rotation Order: XYZ Euler

0.000 0.000 0.000 2.345 0.876 -1.234 ... (84 joints × 3 rotations per frame)
1.234 0.567 -0.890 3.456 1.234 -1.567 ... (next frame)
```

### Output BVH Structure

```
HIERARCHY
ROOT Hips
{
    OFFSET 0.00 0.00 0.00
    CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
    JOINT Spine
    {
        OFFSET 0.00 10.00 0.00
        CHANNELS 3 Zrotation Xrotation Yrotation
        ...
    }
}
MOTION
Frames: 900
Frame Time: 0.033333
```

## 🎮 Pipeline Workflow

### Phase 1: Data Conversion
```python
from scripts.bvh_exporter import BVHExporter

exporter = BVHExporter()
success = exporter.convert_to_bvh(
    joint_centers_file="data/jointcenterscooper.txt",
    joint_rotations_file="data/jointrotationscooper.txt", 
    output_file="output_full_joints.bvh"
)
```

### Phase 2: Blender Processing
```python
# In Blender
from scripts.blender_importer import BaseballMocapImporter

importer = BaseballMocapImporter()
importer.process_baseball_mocap(
    bvh_filepath="output_full_joints.bvh",
    export_filepath="baseball_animation.fbx"  # For UE5
)
```

### Phase 3: MetaHuman Retargeting

1. **Export from Blender**: FBX format with animation
2. **Import to UE5**: Create Animation Blueprint
3. **Retarget**: Map to MetaHuman skeleton
4. **Refine**: Adjust for baseball-specific movements

## ⚙️ Advanced Configuration

### Custom Joint Hierarchy

Edit `bvh_exporter.py` to modify the joint hierarchy:

```python
self.joint_hierarchy = {
    'Hips': {'parent': None, 'offset': [0, 0, 0], 'channels': 6},
    'Spine': {'parent': 'Hips', 'offset': [0, 10, 0], 'channels': 3},
    # Add custom joints here
}
```

### MetaHuman Bone Mapping

Edit `blender_importer.py` to customize MetaHuman mapping:

```python
common_mappings = {
    'Hips': 'pelvis',
    'RightArm': 'upperarm_r',  # Throwing arm
    'LeftArm': 'upperarm_l',   # Glove arm
    # Customize mappings here
}
```

### Baseball Motion Phases

Reference `baseballspecificcooper.txt` for motion timing:

```
windup_start = 1       # Frame 1-150
stride_start = 151     # Frame 151-300  
arm_cocking_start = 301 # Frame 301-450
acceleration_start = 451 # Frame 451-600
ball_release = 601     # Key frame
follow_through_start = 602 # Frame 602-900
```

## 🔧 Troubleshooting

### Common Issues

**BOM/Encoding Errors**
```bash
# Script handles BOM automatically, but if issues persist:
# Convert file encoding to UTF-8 without BOM
```

**Dimension Mismatch**
```bash
# Check that both files have same frame count
# Script auto-detects: frames = total_values / (joints × 3)
```

**Blender Import Fails**
```python
# Check Blender version (3.0+ recommended)
# Verify BVH file is valid
# Check console for error messages
```

**MetaHuman Mapping Issues**
```python
# Verify bone names match MetaHuman skeleton
# Check custom mappings in blender_importer.py
# Test with simplified skeleton first
```

### Validation Commands

```bash
# Check BVH file structure
head -50 output_full_joints.bvh

# Verify data dimensions
python -c "
import numpy as np
data = np.loadtxt('data/jointcenterscooper.txt', skiprows=20)
print(f'Shape: {data.shape}')
print(f'Frames: {len(data) // 84}, Joints: 84')
"
```

## 📈 Performance Tips

- **Large Files**: Use `search_replace` tool for files >2500 lines
- **Memory**: Process in chunks for >10,000 frames
- **Blender**: Close unnecessary windows for better performance
- **Export**: Use FBX binary format for smaller file sizes

## 🎯 MetaHuman Integration Workflow

### 1. UE5 Import Setup
```
Import Settings:
✓ Import Animations: True
✓ Skeleton: MetaHuman_Skeleton
✓ Import Custom Attribute: True
✓ Sample Rate: 30 FPS
```

### 2. Retargeting Configuration
```
Source: Baseball BVH Skeleton
Target: MetaHuman Skeleton  
Chain Mapping:
  - Spine Chain: Auto
  - Arm Chains: Manual (throwing vs glove arm)
  - Leg Chains: Auto
  - Root Motion: Enabled
```

### 3. Baseball-Specific Adjustments
```
Key Considerations:
- Right arm (throwing): Full range of motion
- Hip rotation: Primary power source  
- Stride leg: Weight transfer dynamics
- Follow-through: Natural deceleration
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Cooper's Mocap Data**: Professional baseball motion capture
- **Vicon Systems**: Motion capture technology
- **Blender Foundation**: Open-source 3D software
- **Epic Games**: MetaHuman and Unreal Engine 5
- **Baseball Biomechanics Community**: Research and insights

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)  
- **Documentation**: [Wiki](https://github.com/your-repo/wiki)

---

**🎯 Ready to bring baseball motion to life in MetaHuman!** ⚾🎮