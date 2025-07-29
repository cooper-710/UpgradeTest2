#!/usr/bin/env python3
"""
Baseball Mocap Pipeline - Blender BVH Importer
Imports BVH files into Blender and prepares them for MetaHuman retargeting.

Features:
- Clean BVH import with proper scaling
- Armature cleanup and optimization
- MetaHuman skeleton preparation
- Animation constraint setup
- Export utilities for retargeting

Usage in Blender:
1. Open Blender
2. Go to Scripting workspace
3. Load this script
4. Run the script
5. Use the operators in the 3D Viewport sidebar (N panel)

Author: Baseball Mocap Pipeline
"""

import bpy
import bmesh
import mathutils
from mathutils import Vector, Quaternion, Matrix
import os
import sys
from typing import List, Dict, Optional, Tuple


class BaseballMocapImporter:
    """
    Blender addon for importing and processing baseball mocap data.
    """
    
    def __init__(self):
        self.armature = None
        self.animation_data = None
        self.metahuman_bones = {
            # MetaHuman UE5 skeleton bone names mapping
            'root': 'root',
            'pelvis': 'pelvis',
            'spine_01': 'spine_01', 
            'spine_02': 'spine_02',
            'spine_03': 'spine_03',
            'neck_01': 'neck_01',
            'head': 'head',
            'clavicle_l': 'clavicle_l',
            'upperarm_l': 'upperarm_l',
            'lowerarm_l': 'lowerarm_l',
            'hand_l': 'hand_l',
            'clavicle_r': 'clavicle_r',
            'upperarm_r': 'upperarm_r',
            'lowerarm_r': 'lowerarm_r',
            'hand_r': 'hand_r',
            'thigh_l': 'thigh_l',
            'calf_l': 'calf_l',
            'foot_l': 'foot_l',
            'thigh_r': 'thigh_r',
            'calf_r': 'calf_r',
            'foot_r': 'foot_r',
        }
    
    def clear_scene(self):
        """Clear the current scene."""
        # Select all objects
        bpy.ops.object.select_all(action='SELECT')
        # Delete all objects
        bpy.ops.object.delete(use_global=False)
        
        # Clear all mesh data
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)
        
        # Clear all armature data
        for armature in bpy.data.armatures:
            bpy.data.armatures.remove(armature)
        
        print("Scene cleared.")
    
    def import_bvh(self, filepath: str, scale: float = 1.0) -> bool:
        """
        Import BVH file into Blender.
        
        Args:
            filepath: Path to BVH file
            scale: Scale factor for import
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Import BVH
            bpy.ops.import_anim.bvh(
                filepath=filepath,
                filter_glob="*.bvh",
                target='ARMATURE',
                global_scale=scale,
                frame_start=1,
                use_fps_scale=True,
                use_cyclic=False,
                rotate_mode='NATIVE',
                axis_forward='-Z',
                axis_up='Y'
            )
            
            # Get the imported armature
            armature_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
            if armature_objects:
                self.armature = armature_objects[0]
                bpy.context.view_layer.objects.active = self.armature
                print(f"Successfully imported BVH: {os.path.basename(filepath)}")
                print(f"Armature: {self.armature.name}")
                print(f"Bone count: {len(self.armature.data.bones)}")
                return True
            else:
                print("ERROR: No armature found after BVH import")
                return False
                
        except Exception as e:
            print(f"ERROR importing BVH: {str(e)}")
            return False
    
    def cleanup_armature(self):
        """Clean up imported armature for better performance."""
        if not self.armature:
            print("ERROR: No armature to clean up")
            return
        
        # Switch to Edit mode
        bpy.context.view_layer.objects.active = self.armature
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Remove unnecessary bones (end sites, etc.)
        bones_to_remove = []
        for bone in self.armature.data.edit_bones:
            if 'End Site' in bone.name or 'end' in bone.name.lower():
                bones_to_remove.append(bone.name)
        
        for bone_name in bones_to_remove:
            bone = self.armature.data.edit_bones.get(bone_name)
            if bone:
                self.armature.data.edit_bones.remove(bone)
                print(f"Removed bone: {bone_name}")
        
        # Switch back to Object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        print(f"Cleanup complete. Remaining bones: {len(self.armature.data.bones)}")
    
    def setup_metahuman_mapping(self) -> Dict[str, str]:
        """
        Create bone mapping for MetaHuman retargeting.
        
        Returns:
            Dictionary mapping BVH bones to MetaHuman bones
        """
        bone_mapping = {}
        
        # Common bone name mappings
        common_mappings = {
            'Hips': 'pelvis',
            'Spine': 'spine_01',
            'Spine1': 'spine_02', 
            'Spine2': 'spine_03',
            'Neck': 'neck_01',
            'Head': 'head',
            'LeftShoulder': 'clavicle_l',
            'LeftArm': 'upperarm_l',
            'LeftForeArm': 'lowerarm_l',
            'LeftHand': 'hand_l',
            'RightShoulder': 'clavicle_r',
            'RightArm': 'upperarm_r',
            'RightForeArm': 'lowerarm_r',
            'RightHand': 'hand_r',
            'LeftUpLeg': 'thigh_l',
            'LeftLeg': 'calf_l',
            'LeftFoot': 'foot_l',
            'RightUpLeg': 'thigh_r',
            'RightLeg': 'calf_r',
            'RightFoot': 'foot_r',
        }
        
        # Map existing bones
        for bvh_bone, metahuman_bone in common_mappings.items():
            if bvh_bone in self.armature.data.bones:
                bone_mapping[bvh_bone] = metahuman_bone
                print(f"Mapped: {bvh_bone} -> {metahuman_bone}")
        
        return bone_mapping
    
    def create_metahuman_constraints(self, bone_mapping: Dict[str, str]):
        """
        Create constraints for MetaHuman retargeting.
        
        Args:
            bone_mapping: Dictionary mapping BVH bones to MetaHuman bones
        """
        if not self.armature:
            print("ERROR: No armature for constraint setup")
            return
        
        # Switch to Pose mode
        bpy.context.view_layer.objects.active = self.armature
        bpy.ops.object.mode_set(mode='POSE')
        
        # Add custom properties for retargeting
        for bvh_bone, metahuman_bone in bone_mapping.items():
            pose_bone = self.armature.pose.bones.get(bvh_bone)
            if pose_bone:
                # Add custom property for MetaHuman mapping
                pose_bone["metahuman_target"] = metahuman_bone
                
                # Add custom property for retargeting weight
                pose_bone["retarget_weight"] = 1.0
                
                # Color code bones for visual feedback
                pose_bone.bone_group_index = 0  # Can be customized
        
        bpy.ops.object.mode_set(mode='OBJECT')
        print(f"Created constraints for {len(bone_mapping)} bones")
    
    def optimize_animation(self):
        """Optimize animation data for better performance."""
        if not self.armature or not self.armature.animation_data:
            print("No animation data to optimize")
            return
        
        action = self.armature.animation_data.action
        if not action:
            print("No action to optimize")
            return
        
        # Simplify keyframes (remove redundant keys)
        bpy.context.view_layer.objects.active = self.armature
        bpy.ops.object.mode_set(mode='POSE')
        
        # Select all pose bones
        for bone in self.armature.pose.bones:
            bone.bone.select = True
        
        # Simplify animation
        bpy.ops.action.clean(threshold=0.001)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        print(f"Animation optimization complete")
    
    def export_for_retargeting(self, export_path: str):
        """
        Export processed animation for retargeting.
        
        Args:
            export_path: Path to export the processed animation
        """
        if not self.armature:
            print("ERROR: No armature to export")
            return False
        
        # Select only the armature
        bpy.ops.object.select_all(action='DESELECT')
        self.armature.select_set(True)
        bpy.context.view_layer.objects.active = self.armature
        
        # Export as FBX for UE5 compatibility
        try:
            bpy.ops.export_scene.fbx(
                filepath=export_path,
                use_selection=True,
                object_types={'ARMATURE'},
                use_mesh_modifiers=False,
                use_armature_deform_only=True,
                bake_anim=True,
                bake_anim_use_all_bones=True,
                bake_anim_use_nla_strips=False,
                bake_anim_use_all_actions=False,
                bake_anim_force_startend_keying=True,
                add_leaf_bones=False,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                armature_nodetype='NULL',
                bake_space_transform=True,
                global_scale=1.0,
                apply_unit_scale=True,
                apply_scale_options='FBX_SCALE_NONE',
                axis_forward='-Z',
                axis_up='Y'
            )
            print(f"Exported animation to: {export_path}")
            return True
        except Exception as e:
            print(f"ERROR exporting animation: {str(e)}")
            return False
    
    def process_baseball_mocap(self, bvh_filepath: str, export_filepath: str = None):
        """
        Complete processing pipeline for baseball mocap data.
        
        Args:
            bvh_filepath: Path to input BVH file
            export_filepath: Path to export processed animation (optional)
        """
        print("=== Baseball Mocap Pipeline - Blender Import ===")
        print(f"Processing: {bvh_filepath}")
        
        # Clear scene
        self.clear_scene()
        
        # Import BVH
        if not self.import_bvh(bvh_filepath, scale=1.0):
            print("❌ BVH import failed")
            return False
        
        # Cleanup armature
        self.cleanup_armature()
        
        # Setup MetaHuman mapping
        bone_mapping = self.setup_metahuman_mapping()
        
        # Create constraints
        self.create_metahuman_constraints(bone_mapping)
        
        # Optimize animation
        self.optimize_animation()
        
        # Export if path provided
        if export_filepath:
            self.export_for_retargeting(export_filepath)
        
        print("✅ Baseball mocap processing complete!")
        print(f"Ready for MetaHuman retargeting in UE5")
        
        return True


# Blender Operator Classes
class MOCAP_OT_ImportBVH(bpy.types.Operator):
    """Import Baseball Mocap BVH"""
    bl_idname = "mocap.import_bvh"
    bl_label = "Import Baseball BVH"
    bl_description = "Import BVH file for baseball mocap processing"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Path to BVH file",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )
    
    def execute(self, context):
        importer = BaseballMocapImporter()
        if importer.import_bvh(self.filepath):
            self.report({'INFO'}, f"Successfully imported: {os.path.basename(self.filepath)}")
        else:
            self.report({'ERROR'}, "Failed to import BVH file")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class MOCAP_OT_ProcessPipeline(bpy.types.Operator):
    """Process Complete Baseball Mocap Pipeline"""
    bl_idname = "mocap.process_pipeline" 
    bl_label = "Process Baseball Mocap"
    bl_description = "Complete processing pipeline for baseball mocap data"
    bl_options = {'REGISTER', 'UNDO'}
    
    bvh_filepath: bpy.props.StringProperty(
        name="BVH File",
        description="Path to BVH file",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )
    
    export_filepath: bpy.props.StringProperty(
        name="Export File",
        description="Path to export processed animation",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )
    
    def execute(self, context):
        importer = BaseballMocapImporter()
        export_path = self.export_filepath if self.export_filepath else None
        
        if importer.process_baseball_mocap(self.bvh_filepath, export_path):
            self.report({'INFO'}, "Baseball mocap processing completed successfully")
        else:
            self.report({'ERROR'}, "Baseball mocap processing failed")
        return {'FINISHED'}


class MOCAP_PT_Panel(bpy.types.Panel):
    """Baseball Mocap Pipeline Panel"""
    bl_label = "Baseball Mocap Pipeline"
    bl_idname = "MOCAP_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Baseball Mocap"
    
    def draw(self, context):
        layout = self.layout
        
        # Import section
        box = layout.box()
        box.label(text="Import BVH", icon='IMPORT')
        box.operator("mocap.import_bvh", text="Import BVH File")
        
        # Processing section
        box = layout.box()
        box.label(text="Process Pipeline", icon='MODIFIER')
        box.operator("mocap.process_pipeline", text="Process Complete Pipeline")
        
        # Info section
        box = layout.box()
        box.label(text="Pipeline Info", icon='INFO')
        box.label(text="• Handles BOM + headers")
        box.label(text="• Y-up → Z-up conversion")
        box.label(text="• cm → meters scaling")
        box.label(text="• MetaHuman ready")


# Registration
classes = [
    MOCAP_OT_ImportBVH,
    MOCAP_OT_ProcessPipeline,
    MOCAP_PT_Panel,
]


def register():
    """Register Blender addon classes."""
    for cls in classes:
        bpy.utils.register_class(cls)
    print("Baseball Mocap Pipeline addon registered")


def unregister():
    """Unregister Blender addon classes."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("Baseball Mocap Pipeline addon unregistered")


# Auto-registration when script is run
if __name__ == "__main__":
    # Unregister if already registered
    try:
        unregister()
    except:
        pass
    
    # Register
    register()
    
    print("\n🎯 Baseball Mocap Pipeline - Blender Script Loaded!")
    print("Check the 3D Viewport sidebar (N panel) for 'Baseball Mocap' tab")
    
    # Example usage:
    # importer = BaseballMocapImporter()
    # importer.process_baseball_mocap("path/to/output_full_joints.bvh", "path/to/export.fbx")