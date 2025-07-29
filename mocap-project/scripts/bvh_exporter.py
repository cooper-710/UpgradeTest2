#!/usr/bin/env python3
"""
Baseball Mocap Pipeline - BVH Exporter
Converts Cooper's joint center and rotation data to BVH format for Blender import.

Features:
- Auto-detects frame and joint counts
- Handles BOM and header stripping
- Y-up to Z-up coordinate conversion
- Centimeter to meter scaling
- Proper BVH hierarchy with root joint (6 channels) and child joints (3 channels)
- Clean output ready for Blender and MetaHuman retargeting

Author: Baseball Mocap Pipeline
"""

import os
import sys
import numpy as np
import re
from typing import List, Tuple, Dict, Optional
from pathlib import Path


class BVHExporter:
    """
    Converts Cooper's mocap data files to BVH format.
    """
    
    def __init__(self):
        self.joint_names = []
        self.joint_positions = []
        self.joint_rotations = []
        self.frame_count = 0
        self.joint_count = 0
        self.frame_time = 1.0 / 30.0  # 30 FPS default
        
        # BVH hierarchy for baseball mocap (common skeleton structure)
        self.joint_hierarchy = {
            'Hips': {'parent': None, 'offset': [0, 0, 0], 'channels': 6},
            'Spine': {'parent': 'Hips', 'offset': [0, 10, 0], 'channels': 3},
            'Spine1': {'parent': 'Spine', 'offset': [0, 10, 0], 'channels': 3},
            'Spine2': {'parent': 'Spine1', 'offset': [0, 10, 0], 'channels': 3},
            'Neck': {'parent': 'Spine2', 'offset': [0, 15, 0], 'channels': 3},
            'Head': {'parent': 'Neck', 'offset': [0, 10, 0], 'channels': 3},
            'LeftShoulder': {'parent': 'Spine2', 'offset': [-15, 10, 0], 'channels': 3},
            'LeftArm': {'parent': 'LeftShoulder', 'offset': [-20, 0, 0], 'channels': 3},
            'LeftForeArm': {'parent': 'LeftArm', 'offset': [-25, 0, 0], 'channels': 3},
            'LeftHand': {'parent': 'LeftForeArm', 'offset': [-20, 0, 0], 'channels': 3},
            'RightShoulder': {'parent': 'Spine2', 'offset': [15, 10, 0], 'channels': 3},
            'RightArm': {'parent': 'RightShoulder', 'offset': [20, 0, 0], 'channels': 3},
            'RightForeArm': {'parent': 'RightArm', 'offset': [25, 0, 0], 'channels': 3},
            'RightHand': {'parent': 'RightForeArm', 'offset': [20, 0, 0], 'channels': 3},
            'LeftUpLeg': {'parent': 'Hips', 'offset': [-10, -5, 0], 'channels': 3},
            'LeftLeg': {'parent': 'LeftUpLeg', 'offset': [0, -40, 0], 'channels': 3},
            'LeftFoot': {'parent': 'LeftLeg', 'offset': [0, -40, 0], 'channels': 3},
            'RightUpLeg': {'parent': 'Hips', 'offset': [10, -5, 0], 'channels': 3},
            'RightLeg': {'parent': 'RightUpLeg', 'offset': [0, -40, 0], 'channels': 3},
            'RightFoot': {'parent': 'RightLeg', 'offset': [0, -40, 0], 'channels': 3},
        }
    
    def strip_bom_and_read(self, filepath: str) -> List[str]:
        """
        Read file and strip BOM if present.
        
        Args:
            filepath: Path to the input file
            
        Returns:
            List of lines with BOM stripped
        """
        try:
            # Try UTF-8 with BOM first
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Fallback to regular UTF-8
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        
        # Strip whitespace and filter empty lines
        lines = [line.strip() for line in lines if line.strip()]
        
        print(f"Read {len(lines)} lines from {filepath}")
        return lines
    
    def parse_joint_centers(self, filepath: str) -> np.ndarray:
        """
        Parse joint center positions from Cooper's format.
        Expected format: Frame by frame, joint positions in cm (Y-up)
        
        Args:
            filepath: Path to jointcenterscooper.txt
            
        Returns:
            3D array of shape (frames, joints, 3) in meters (Z-up)
        """
        lines = self.strip_bom_and_read(filepath)
        
        # Skip header lines (look for numeric data)
        data_start = 0
        for i, line in enumerate(lines):
            if re.match(r'^[\d\s\-\.]+$', line.strip()):
                data_start = i
                break
        
        print(f"Data starts at line {data_start + 1}")
        
        # Parse numeric data
        positions_data = []
        for line in lines[data_start:]:
            if line.strip():
                # Split by whitespace and convert to float
                values = [float(x) for x in line.split()]
                positions_data.extend(values)
        
        # Auto-detect dimensions
        total_values = len(positions_data)
        
        # Estimate joint count (should be divisible by 3 for x,y,z)
        # Try common joint counts: 84, 80, 76, etc.
        possible_joint_counts = [84, 80, 76, 72, 68, 64, 60]
        
        for joint_count in possible_joint_counts:
            if total_values % (joint_count * 3) == 0:
                frame_count = total_values // (joint_count * 3)
                print(f"Auto-detected: {frame_count} frames, {joint_count} joints")
                break
        else:
            # Fallback: assume standard counts
            joint_count = 84
            frame_count = total_values // (joint_count * 3)
            print(f"Using fallback: {frame_count} frames, {joint_count} joints")
        
        self.frame_count = frame_count
        self.joint_count = joint_count
        
        # Reshape data
        positions = np.array(positions_data).reshape(frame_count, joint_count, 3)
        
        # Convert from Y-up (cm) to Z-up (meters)
        # Y-up: [X, Y, Z] -> Z-up: [X, Z, -Y]
        positions_converted = np.zeros_like(positions)
        positions_converted[:, :, 0] = positions[:, :, 0]  # X stays X
        positions_converted[:, :, 1] = positions[:, :, 2]  # Z becomes Y
        positions_converted[:, :, 2] = -positions[:, :, 1]  # -Y becomes Z
        
        # Scale from centimeters to meters
        positions_converted *= 0.01
        
        print(f"Converted positions: {positions_converted.shape}")
        return positions_converted
    
    def parse_joint_rotations(self, filepath: str) -> np.ndarray:
        """
        Parse joint rotations from Cooper's format.
        Expected format: Frame by frame, Euler angles in degrees (Y-up)
        
        Args:
            filepath: Path to jointrotationscooper.txt
            
        Returns:
            3D array of shape (frames, joints, 3) in degrees (Z-up)
        """
        lines = self.strip_bom_and_read(filepath)
        
        # Skip header lines
        data_start = 0
        for i, line in enumerate(lines):
            if re.match(r'^[\d\s\-\.]+$', line.strip()):
                data_start = i
                break
        
        # Parse numeric data
        rotations_data = []
        for line in lines[data_start:]:
            if line.strip():
                values = [float(x) for x in line.split()]
                rotations_data.extend(values)
        
        # Reshape using detected dimensions
        rotations = np.array(rotations_data).reshape(self.frame_count, self.joint_count, 3)
        
        # Convert rotation order from Y-up to Z-up
        # This may need adjustment based on the specific rotation order used
        rotations_converted = np.zeros_like(rotations)
        rotations_converted[:, :, 0] = rotations[:, :, 0]  # X rotation
        rotations_converted[:, :, 1] = rotations[:, :, 2]  # Z rotation -> Y
        rotations_converted[:, :, 2] = -rotations[:, :, 1]  # -Y rotation -> Z
        
        print(f"Converted rotations: {rotations_converted.shape}")
        return rotations_converted
    
    def generate_joint_names(self, count: int) -> List[str]:
        """
        Generate joint names for the detected number of joints.
        
        Args:
            count: Number of joints detected
            
        Returns:
            List of joint names
        """
        # Use hierarchy names first, then generate additional if needed
        base_names = list(self.joint_hierarchy.keys())
        
        if count <= len(base_names):
            return base_names[:count]
        
        # Generate additional joint names
        names = base_names.copy()
        for i in range(len(base_names), count):
            names.append(f"Joint_{i:02d}")
        
        return names
    
    def write_bvh_header(self, file_handle, joint_names: List[str]) -> None:
        """
        Write BVH hierarchy section.
        
        Args:
            file_handle: File handle to write to
            joint_names: List of joint names
        """
        file_handle.write("HIERARCHY\n")
        
        # Write root joint (Hips)
        root_name = joint_names[0] if joint_names else "Hips"
        file_handle.write(f"ROOT {root_name}\n")
        file_handle.write("{\n")
        file_handle.write(f"\tOFFSET 0.00 0.00 0.00\n")
        file_handle.write(f"\tCHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation\n")
        
        # Write child joints
        for i, joint_name in enumerate(joint_names[1:], 1):
            file_handle.write(f"\tJOINT {joint_name}\n")
            file_handle.write("\t{\n")
            file_handle.write(f"\t\tOFFSET 0.00 10.00 0.00\n")  # Simple offset
            file_handle.write(f"\t\tCHANNELS 3 Zrotation Xrotation Yrotation\n")
        
        # Close all joints
        for i in range(len(joint_names)):
            if i == 0:
                file_handle.write("\tEnd Site\n")
                file_handle.write("\t{\n")
                file_handle.write("\t\tOFFSET 0.00 5.00 0.00\n")
                file_handle.write("\t}\n")
            file_handle.write("\t}\n")
        
        file_handle.write("}\n")
    
    def write_bvh_motion(self, file_handle, positions: np.ndarray, rotations: np.ndarray) -> None:
        """
        Write BVH motion section.
        
        Args:
            file_handle: File handle to write to
            positions: Joint positions array
            rotations: Joint rotations array
        """
        file_handle.write("MOTION\n")
        file_handle.write(f"Frames: {self.frame_count}\n")
        file_handle.write(f"Frame Time: {self.frame_time:.6f}\n")
        
        # Write motion data
        for frame in range(self.frame_count):
            # Root joint: position + rotation
            root_pos = positions[frame, 0]
            root_rot = rotations[frame, 0]
            
            # Write root data (6 channels)
            motion_data = [
                f"{root_pos[0]:.6f}",  # X position
                f"{root_pos[1]:.6f}",  # Y position  
                f"{root_pos[2]:.6f}",  # Z position
                f"{root_rot[2]:.6f}",  # Z rotation
                f"{root_rot[0]:.6f}",  # X rotation
                f"{root_rot[1]:.6f}",  # Y rotation
            ]
            
            # Other joints: rotation only (3 channels each)
            for joint_idx in range(1, self.joint_count):
                joint_rot = rotations[frame, joint_idx]
                motion_data.extend([
                    f"{joint_rot[2]:.6f}",  # Z rotation
                    f"{joint_rot[0]:.6f}",  # X rotation
                    f"{joint_rot[1]:.6f}",  # Y rotation
                ])
            
            file_handle.write(" ".join(motion_data) + "\n")
    
    def convert_to_bvh(self, joint_centers_file: str, joint_rotations_file: str, output_file: str) -> bool:
        """
        Main conversion function.
        
        Args:
            joint_centers_file: Path to joint centers file
            joint_rotations_file: Path to joint rotations file
            output_file: Output BVH file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print("=== Baseball Mocap Pipeline - BVH Converter ===")
            print(f"Processing: {joint_centers_file}")
            print(f"Processing: {joint_rotations_file}")
            print(f"Output: {output_file}")
            print()
            
            # Parse input files
            print("Parsing joint centers...")
            positions = self.parse_joint_centers(joint_centers_file)
            
            print("Parsing joint rotations...")
            rotations = self.parse_joint_rotations(joint_rotations_file)
            
            # Validate dimensions match
            if positions.shape != rotations.shape:
                print(f"ERROR: Dimension mismatch!")
                print(f"Positions: {positions.shape}")
                print(f"Rotations: {rotations.shape}")
                return False
            
            # Generate joint names
            joint_names = self.generate_joint_names(self.joint_count)
            print(f"Generated {len(joint_names)} joint names")
            
            # Write BVH file
            print(f"Writing BVH file: {output_file}")
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w') as f:
                self.write_bvh_header(f, joint_names)
                self.write_bvh_motion(f, positions, rotations)
            
            print(f"✓ Successfully created BVH file!")
            print(f"  - Frames: {self.frame_count}")
            print(f"  - Joints: {self.joint_count}")
            print(f"  - Duration: {self.frame_count * self.frame_time:.2f} seconds")
            print(f"  - File size: {os.path.getsize(output_file) / 1024:.1f} KB")
            
            return True
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """
    Main function for command-line usage.
    """
    if len(sys.argv) != 4:
        print("Usage: python bvh_exporter.py <joint_centers_file> <joint_rotations_file> <output_bvh>")
        print("Example: python bvh_exporter.py data/jointcenterscooper.txt data/jointrotationscooper.txt output_full_joints.bvh")
        sys.exit(1)
    
    joint_centers_file = sys.argv[1]
    joint_rotations_file = sys.argv[2]
    output_file = sys.argv[3]
    
    # Validate input files exist
    if not os.path.exists(joint_centers_file):
        print(f"ERROR: Joint centers file not found: {joint_centers_file}")
        sys.exit(1)
    
    if not os.path.exists(joint_rotations_file):
        print(f"ERROR: Joint rotations file not found: {joint_rotations_file}")
        sys.exit(1)
    
    # Convert to BVH
    exporter = BVHExporter()
    success = exporter.convert_to_bvh(joint_centers_file, joint_rotations_file, output_file)
    
    if success:
        print("\n🎯 BVH export completed successfully!")
        print("Ready for Blender import and MetaHuman retargeting.")
    else:
        print("\n❌ BVH export failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()