import os
import bpy
import math
import random
from typing import Dict, List, Tuple, Optional
import numpy as np
from mathutils import Vector, Quaternion, Matrix
from pathlib import Path

class BlenderRenderer:
    """Blender-specific scene manipulation functions."""
    
    # Object type mapping to basic shapes
    OBJECT_TYPES = {
        # Basic shapes
        "cube": "cube",
        "sphere": "sphere",
        "cylinder": "cylinder",
        "plane": "plane",
        
        # Furniture
        "sofa": "cube",  # Will be modified with custom dimensions
        "table": "cube",
        "coffee_table": "cube",  # Added coffee table
        "chair": "cube",
        "tv": "cube",
        "bed": "cube",
        "bookshelf": "cube",
        
        # Decorations
        "lamp": "cylinder",
        "vase": "cylinder",
        "picture": "plane",
        "rug": "plane",
        
        # Electronics
        "computer": "cube",
        "speaker": "cube",
        "monitor": "cube",
    }
    
    # Default dimensions for furniture
    OBJECT_DIMENSIONS = {
        "sofa": {"x": 2.0, "y": 0.8, "z": 0.8},
        "table": {"x": 1.2, "y": 0.8, "z": 0.5},
        "coffee_table": {"x": 1.0, "y": 0.6, "z": 0.4},  # Added coffee table dimensions
        "chair": {"x": 0.6, "y": 0.6, "z": 0.5},
        "tv": {"x": 1.5, "y": 0.1, "z": 0.9},
        "bed": {"x": 2.0, "y": 1.6, "z": 0.5},
        "bookshelf": {"x": 1.0, "y": 0.4, "z": 2.0},
        "lamp": {"x": 0.2, "y": 0.2, "z": 1.2},
        "vase": {"x": 0.3, "y": 0.3, "z": 0.4},
        "picture": {"x": 1.0, "y": 0.1, "z": 0.7},
        "rug": {"x": 2.0, "y": 3.0, "z": 0.02},
        "computer": {"x": 0.4, "y": 0.3, "z": 0.05},
        "speaker": {"x": 0.3, "y": 0.3, "z": 0.4},
        "monitor": {"x": 0.6, "y": 0.1, "z": 0.4},
    }
    
    def __init__(self, config: Dict = None):
        """Initialize the Blender renderer."""
        self.config = config or {}
        self.blender_path = self.config.get('blender_path', '')
        self.samples = self.config.get('samples', 128)
        self.resolution = self.config.get('resolution', [1920, 1080])
        
        # Initialize Blender
        if not self.blender_path:
            raise ValueError("Blender path not specified in config")
        
        # Set up Blender environment
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.samples = self.samples
        bpy.context.scene.render.resolution_x = self.resolution[0]
        bpy.context.scene.render.resolution_y = self.resolution[1]
        
        # 设置Blender的Python路径
        if self.blender_path and self.blender_path not in os.environ["PATH"]:
            os.environ["PATH"] = os.path.dirname(self.blender_path) + os.pathsep + os.environ["PATH"]
        
        # 初始化场景
        self._setup_scene()
    
    def _setup_scene(self):
        """Set up the basic scene configuration."""
        # 清除默认物体
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        
        # 设置世界背景
        world = bpy.context.scene.world
        world.use_nodes = True
        bg = world.node_tree.nodes['Background']
        bg.inputs[0].default_value = (0.1, 0.1, 0.1, 1)  # 深灰色背景
        
        print("Blender scene setup completed")
    
    def create_object(self, obj_type: str, position: Dict[str, float], 
                     scale: Optional[Dict[str, float]] = None,
                     rotation: Optional[Dict[str, float]] = None,
                     object_index: int = 0) -> bpy.types.Object:
        """Create a new object in the scene (refactored for clarity and visibility)."""
        # Use cube for sofa, coffee_table, tv
        base_type = self.OBJECT_TYPES.get(obj_type.lower())
        if not base_type:
            base_type = self.OBJECT_TYPES.get(obj_type.lower().replace(' ', '_'))
        if not base_type:
            raise ValueError(f"Unsupported object type: {obj_type}")
        if base_type == "cube":
            bpy.ops.mesh.primitive_cube_add()
        elif base_type == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add()
        elif base_type == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add()
        elif base_type == "plane":
            bpy.ops.mesh.primitive_plane_add()
        obj = bpy.context.active_object
        obj.name = obj_type
        # Set scale
        if scale:
            obj.scale = (scale["x"], scale["y"], scale["z"])
        elif obj_type.lower() in self.OBJECT_DIMENSIONS:
            default_scale = self.OBJECT_DIMENSIONS[obj_type.lower()]
            obj.scale = (default_scale["x"], default_scale["y"], default_scale["z"])
        elif obj_type.lower().replace(' ', '_') in self.OBJECT_DIMENSIONS:
            default_scale = self.OBJECT_DIMENSIONS[obj_type.lower().replace(' ', '_')]
            obj.scale = (default_scale["x"], default_scale["y"], default_scale["z"])
        # Set position
        pos_x = position["x"]
        pos_y = position["y"]
        pos_z = position["z"]
        if pos_y == 0:
            pos_y = object_index * 2.0
        if pos_z == 0:
            obj_height = obj.scale[2] if hasattr(obj, 'scale') else 0.5
            pos_z = obj_height
        obj.location = (pos_x, pos_y, pos_z)
        print(f"[DEBUG] Created {obj_type} at {obj.location} with scale {obj.scale}")
        # Set rotation
        if rotation:
            obj.rotation_euler = (
                math.radians(rotation["x"]),
                math.radians(rotation["y"]),
                math.radians(rotation["z"])
            )
        return obj
    
    def create_material(self, name: str, properties: Dict) -> bpy.types.Material:
        """Create a new material with specified properties (refactored for visibility)."""
        material = bpy.data.materials.new(name=name)
        # Use diffuse_color directly for visibility
        if "base_color" in properties:
            material.diffuse_color = properties["base_color"]
        else:
            material.diffuse_color = (0.8, 0.8, 0.8, 1.0)
        return material
    
    def apply_material(self, obj: bpy.types.Object, material: bpy.types.Material):
        """Apply material to an object (always assign)."""
        obj.data.materials.clear()
        obj.data.materials.append(material)
    
    def create_light(self, light_type: str, position: Dict[str, float], 
                    properties: Dict) -> bpy.types.Object:
        """Create a new light in the scene."""
        # Create light
        if light_type == "sun":
            bpy.ops.object.light_add(type='SUN')
        elif light_type == "point":
            bpy.ops.object.light_add(type='POINT')
        elif light_type == "area":
            bpy.ops.object.light_add(type='AREA')
        elif light_type in ["ambient", "ambient_light"]:
            # Use sun light for ambient lighting
            bpy.ops.object.light_add(type='SUN')
            light = bpy.context.active_object
            # Set default properties for ambient light
            light.data.energy = properties.get("energy", 1.0)
            light.data.angle = 0.1  # Small angle for soft shadows
            light.data.use_shadow = False  # Disable shadows for ambient light
            print(f"[DEBUG] Light {light_type} at {light.location}")
            return light
        else:
            raise ValueError(f"Unsupported light type: {light_type}")
        
        light = bpy.context.active_object
        
        # Set position
        light.location = (position["x"], position["y"], position["z"])
        
        # Set properties
        if "energy" in properties:
            light.data.energy = properties["energy"]
        if "color" in properties:
            light.data.color = properties["color"]
        
        print(f"[DEBUG] Light {light_type} at {light.location}")
        
        return light
    
    def set_camera(self, position: Dict[str, float] = None, target: Dict[str, float] = None, fov: float = 60.0):
        """Set up camera position and orientation. Defaults to (0, -6, 2) looking at (0, 0, 1)."""
        if position is None:
            position = {"x": 0, "y": -6, "z": 2}
        if target is None:
            target = {"x": 0, "y": 0, "z": 1}
        # Create camera if it doesn't exist
        if "Camera" not in bpy.data.objects:
            bpy.ops.object.camera_add()
            camera = bpy.context.active_object
            camera.name = "Camera"
        else:
            camera = bpy.data.objects["Camera"]
        # Set position
        camera.location = (position["x"], position["y"], position["z"])
        # Set target
        direction = (
            target["x"] - position["x"],
            target["y"] - position["y"],
            target["z"] - position["z"]
        )
        rot_quat = direction_to_rotation(direction)
        camera.rotation_euler = rot_quat.to_euler()
        # Set FOV
        camera.data.angle = math.radians(fov)
        # Set as active camera
        bpy.context.scene.camera = camera
        print(f"[DEBUG] Camera at {camera.location}, looking at {target}")
    
    def create_room(self, dimensions: Dict[str, float], wall_material: Dict):
        """Create a room with floor and back wall only (for visibility)."""
        # Create floor
        floor = self.create_object(
            "plane",
            {"x": 0, "y": 0, "z": 0},
            scale={"x": dimensions["width"]/2, "y": dimensions["length"]/2, "z": 1}
        )
        # Create back wall
        back_wall = self.create_object(
            "cube",
            {"x": 0, "y": -dimensions["length"]/2, "z": dimensions["height"]/2},
            scale={"x": dimensions["width"]/2, "y": 1, "z": dimensions["height"]/2},
            rotation={"x": 0, "y": 0, "z": 0}
        )
        # Create and apply wall material
        material = self.create_material("wall_material", wall_material)
        self.apply_material(back_wall, material)
        return {
            "floor": floor,
            "back_wall": back_wall
        }
    
    def create_window(self, wall: bpy.types.Object, size: Dict[str, float],
                     position: Dict[str, float]):
        """Create a window in a wall."""
        # Create window frame
        frame = self.create_object(
            "cube",
            position,
            scale={"x": size["width"]/2, "y": 0.1, "z": size["height"]/2}
        )
        
        # Create window glass
        glass = self.create_object(
            "cube",
            position,
            scale={"x": size["width"]/2 - 0.1, "y": 0.05, "z": size["height"]/2 - 0.1}
        )
        
        # Create materials
        frame_material = self.create_material("window_frame", {
            "base_color": (0.2, 0.2, 0.2, 1.0),
            "metallic": 0.0,
            "roughness": 0.5
        })
        
        glass_material = self.create_material("window_glass", {
            "base_color": (0.8, 0.8, 1.0, 0.1),
            "metallic": 0.0,
            "roughness": 0.0
        })
        
        # Apply materials
        self.apply_material(frame, frame_material)
        self.apply_material(glass, glass_material)
        
        return {"frame": frame, "glass": glass}

    def render(self, output_path: str) -> bool:
        """Render the current scene to the specified output path."""
        try:
            # Set render settings
            bpy.context.scene.render.filepath = output_path
            bpy.context.scene.render.image_settings.file_format = 'PNG'
            
            # Set render engine and samples
            bpy.context.scene.render.engine = 'CYCLES'
            bpy.context.scene.cycles.samples = self.samples
            
            # Set resolution
            bpy.context.scene.render.resolution_x = self.resolution[0]
            bpy.context.scene.render.resolution_y = self.resolution[1]
            
            # Render
            bpy.ops.render.render(write_still=True)
            return True
            
        except Exception as e:
            print(f"Error rendering scene: {str(e)}")
            return False

    def create_ground_plane(self, size: float = 10.0):
        """Create a ground plane at z=0."""
        bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
        plane = bpy.context.active_object
        plane.name = "Ground"
        print(f"[DEBUG] Created ground plane at {plane.location} with size {size}")
        return plane

    def create_sun_light(self, position: Dict[str, float] = None, energy: float = 10.0):
        """Create a sun light above the scene."""
        if position is None:
            position = {"x": 0, "y": 0, "z": 5}
        bpy.ops.object.light_add(type='SUN', location=(position["x"], position["y"], position["z"]))
        light = bpy.context.active_object
        light.data.energy = energy
        print(f"[DEBUG] Sun light at {light.location} with energy {energy}")
        return light

def direction_to_rotation(direction: Tuple[float, float, float]) -> Quaternion:
    """Convert direction vector to rotation quaternion."""
    # Normalize direction
    dir_vec = Vector(direction).normalized()
    
    # Calculate rotation
    z_axis = Vector((0, 0, 1))
    rotation_axis = z_axis.cross(dir_vec)
    
    if rotation_axis.length < 0.0001:
        # Direction is parallel to z-axis
        if dir_vec.z > 0:
            return Quaternion((1, 0, 0, 0))  # Identity
        else:
            return Quaternion((0, 1, 0, 0))  # 180 degrees around x-axis
    
    rotation_axis.normalize()
    rotation_angle = z_axis.angle(dir_vec)
    
    return Quaternion(rotation_axis, rotation_angle) 