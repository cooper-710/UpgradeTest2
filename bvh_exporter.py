#!/usr/bin/env python3
"""
BVH Exporter Script
Converts jointcenterscooper.txt and jointrotationscooper.txt to BVH format.

Requirements:
- Auto-detect joint count and frame count
- Strip BOM markers and skip header lines
- Handle ~900 frames and ~84 joints
- Convert from Y-up to Z-up coordinate system
- Scale positions from cm to meters (factor 0.01)
- Hips (joint 0) as root, centered at origin
- BVH hierarchy: root + flat children
- Root joint: 6 channels (Xposition Yposition Zposition Zrotation Xrotation Yrotation)
- Other joints: 3 rotation channels (Zrotation Xrotation Yrotation)
"""

import numpy as np
import os
import re


def strip_bom(line):
    """Remove BOM markers from line"""
    # Remove UTF-8 BOM if present
    if line.startswith('\ufeff'):
        line = line[1:]
    # Remove byte-order marks
    line = line.replace('\ufeff', '')
    return line


def load_data_file(filename):
    """Load and parse data from TXT file, skipping headers"""
    print(f"Loading {filename}...")
    
    with open(filename, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    
    # Strip BOM and clean lines
    lines = [strip_bom(line.strip()) for line in lines if line.strip()]
    
    # Skip header lines that contain "X Y Z" patterns
    data_lines = []
    for line in lines:
        # Skip lines that look like headers (contain patterns like "X Y Z Length v(X)")
        if re.search(r'\bX\s+Y\s+Z\b', line) or re.search(r'\bLength\s+v\(', line):
            continue
        # Skip empty lines
        if not line or line.isspace():
            continue
        data_lines.append(line)
    
    print(f"Found {len(data_lines)} data lines after skipping headers")
    
    # Parse numeric data
    data = []
    for i, line in enumerate(data_lines):
        try:
            # Split by whitespace and convert to float
            values = [float(x) for x in line.split()]
            data.append(values)
        except ValueError as e:
            print(f"Warning: Could not parse line {i+1}: {e}")
            continue
    
    return np.array(data)


def detect_data_structure(data):
    """Auto-detect number of joints and frames from data structure"""
    num_frames = data.shape[0]
    total_values = data.shape[1]
    
    # Each joint should have 3 values (X, Y, Z for positions) or (Rx, Ry, Rz for rotations)
    # But the files seem to have additional columns (Length, velocity, acceleration)
    # Based on the header pattern, it looks like each joint has 12 columns:
    # X Y Z Length v(X) v(Y) v(Z) v(abs) a(X) a(Y) a(Z) a(abs)
    
    values_per_joint = 12
    num_joints = total_values // values_per_joint
    
    print(f"Data structure: {num_frames} frames, {total_values} total values")
    print(f"Detected {num_joints} joints ({values_per_joint} values per joint)")
    
    return num_frames, num_joints


def extract_positions_rotations(data, num_joints):
    """Extract X, Y, Z coordinates from the data (first 3 values per joint)"""
    num_frames = data.shape[0]
    
    # Extract positions: every 12th value starting from indices 0, 1, 2
    positions = np.zeros((num_frames, num_joints, 3))
    
    for joint_idx in range(num_joints):
        start_col = joint_idx * 12
        if start_col + 2 < data.shape[1]:
            positions[:, joint_idx, 0] = data[:, start_col]     # X
            positions[:, joint_idx, 1] = data[:, start_col + 1] # Y
            positions[:, joint_idx, 2] = data[:, start_col + 2] # Z
    
    return positions


def convert_coordinate_system(positions):
    """Convert from Y-up to Z-up coordinate system"""
    # Y-up to Z-up conversion: X stays, Y becomes Z, Z becomes -Y
    converted = positions.copy()
    converted[:, :, [1, 2]] = positions[:, :, [2, 1]]  # Swap Y and Z
    converted[:, :, 2] = -converted[:, :, 2]  # Negate new Y (original Z)
    return converted


def scale_to_meters(positions):
    """Scale positions from centimeters to meters"""
    return positions * 0.01


def center_root_joint(positions):
    """Center the root joint (hips) at the origin"""
    # Subtract the root joint position from all joints to center at origin
    root_offset = positions[:, 0, :].copy()  # Root joint positions
    positions_centered = positions.copy()
    
    for joint_idx in range(positions.shape[1]):
        positions_centered[:, joint_idx, :] = positions[:, joint_idx, :] - root_offset
    
    return positions_centered


def generate_joint_names(num_joints):
    """Generate joint names for the hierarchy"""
    if num_joints >= 1:
        names = ["Hips"]  # Root joint
    else:
        return ["Joint_0"]
    
    # Generate names for remaining joints
    for i in range(1, num_joints):
        names.append(f"Joint_{i:02d}")
    
    return names


def write_bvh_hierarchy(file, joint_names):
    """Write the HIERARCHY section of the BVH file"""
    file.write("HIERARCHY\n")
    
    # Root joint (Hips) with 6 channels
    file.write("ROOT Hips\n")
    file.write("{\n")
    file.write("  OFFSET 0.0 0.0 0.0\n")
    file.write("  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation\n")
    
    # Add all other joints as direct children of root (flat hierarchy)
    for i in range(1, len(joint_names)):
        joint_name = joint_names[i]
        file.write(f"  JOINT {joint_name}\n")
        file.write("  {\n")
        file.write("    OFFSET 0.0 0.0 0.0\n")
        file.write("    CHANNELS 3 Zrotation Xrotation Yrotation\n")
        file.write("    End Site\n")
        file.write("    {\n")
        file.write("      OFFSET 0.0 0.0 0.0\n")
        file.write("    }\n")
        file.write("  }\n")
    
    file.write("}\n")


def write_bvh_motion(file, positions, rotations, num_frames):
    """Write the MOTION section of the BVH file"""
    file.write("MOTION\n")
    file.write(f"Frames: {num_frames}\n")
    file.write("Frame Time: 0.033333\n")  # ~30 FPS
    
    # Write frame data
    for frame in range(num_frames):
        frame_data = []
        
        # Root joint: 6 values (position + rotation)
        root_pos = positions[frame, 0, :]
        frame_data.extend([f"{root_pos[0]:.6f}", f"{root_pos[1]:.6f}", f"{root_pos[2]:.6f}"])
        
        # Root rotation (use rotations if available, otherwise default to 0)
        if rotations is not None and rotations.shape[1] > 0:
            root_rot = rotations[frame, 0, :]
            frame_data.extend([f"{root_rot[2]:.6f}", f"{root_rot[0]:.6f}", f"{root_rot[1]:.6f}"])  # ZXY order
        else:
            frame_data.extend(["0.0", "0.0", "0.0"])
        
        # Other joints: 3 rotation values each
        for joint_idx in range(1, positions.shape[1]):
            if rotations is not None and rotations.shape[1] > joint_idx:
                joint_rot = rotations[frame, joint_idx, :]
                frame_data.extend([f"{joint_rot[2]:.6f}", f"{joint_rot[0]:.6f}", f"{joint_rot[1]:.6f}"])  # ZXY order
            else:
                frame_data.extend(["0.0", "0.0", "0.0"])
        
        file.write(" ".join(frame_data) + "\n")


def convert_to_bvh(centers_file, rotations_file, output_file):
    """Main conversion function"""
    print(f"Converting {centers_file} and {rotations_file} to {output_file}")
    
    # Load data files
    centers_data = load_data_file(centers_file)
    rotations_data = load_data_file(rotations_file)
    
    # Detect data structure
    frames_centers, joints_centers = detect_data_structure(centers_data)
    frames_rotations, joints_rotations = detect_data_structure(rotations_data)
    
    if frames_centers != frames_rotations:
        print(f"Warning: Frame count mismatch - centers: {frames_centers}, rotations: {frames_rotations}")
    
    if joints_centers != joints_rotations:
        print(f"Warning: Joint count mismatch - centers: {joints_centers}, rotations: {joints_rotations}")
    
    num_frames = min(frames_centers, frames_rotations)
    num_joints = min(joints_centers, joints_rotations)
    
    print(f"Using {num_frames} frames and {num_joints} joints")
    
    # Extract positions and rotations
    positions = extract_positions_rotations(centers_data, num_joints)
    rotations = extract_positions_rotations(rotations_data, num_joints)  # Same extraction for rotations
    
    print(f"Extracted positions shape: {positions.shape}")
    print(f"Extracted rotations shape: {rotations.shape}")
    
    # Apply transformations
    print("Converting coordinate system from Y-up to Z-up...")
    positions = convert_coordinate_system(positions)
    
    print("Scaling positions from cm to meters...")
    positions = scale_to_meters(positions)
    
    print("Centering root joint at origin...")
    positions = center_root_joint(positions)
    
    # Generate joint names
    joint_names = generate_joint_names(num_joints)
    print(f"Generated joint names: {joint_names[:5]}... (showing first 5)")
    
    # Write BVH file
    print(f"Writing BVH file: {output_file}")
    with open(output_file, 'w') as f:
        write_bvh_hierarchy(f, joint_names)
        write_bvh_motion(f, positions, rotations, num_frames)
    
    print(f"Successfully created {output_file}")
    print(f"File contains {num_frames} frames with {num_joints} joints")


def main():
    """Main function"""
    centers_file = "jointcenterscooper.txt"
    rotations_file = "jointrotationscooper.txt"
    output_file = "output_full_joints.bvh"
    
    # Check if input files exist
    if not os.path.exists(centers_file):
        print(f"Error: {centers_file} not found!")
        return
    
    if not os.path.exists(rotations_file):
        print(f"Error: {rotations_file} not found!")
        return
    
    try:
        convert_to_bvh(centers_file, rotations_file, output_file)
        print("\nConversion completed successfully!")
        print(f"Output file '{output_file}' is ready for Blender import.")
        print("To import in Blender: File → Import → Motion Capture (.bvh)")
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()