from typing import Dict, List, Optional
import bpy
from pathlib import Path
import json
import openai
import mathutils
import random
import time

from .planner import ScenePlan, SceneObject
from renderers.blender import BlenderRenderer

class ExecutorAgent:
    """Agent responsible for executing scene construction plans."""
    
    def __init__(self, renderer: str = "blender", config: Dict = None):
        """Initialize the executor agent."""
        self.renderer = renderer
        self.config = config or {}
        self._load_tools()
        
        # Initialize Blender renderer
        if renderer == "blender":
            render_config = {
                'blender_path': self.config.get('render', {}).get('blender_path', ''),
                'samples': self.config.get('render', {}).get('samples', 128),
                'resolution': self.config.get('render', {}).get('resolution', [1920, 1080])
            }
            self.blender = BlenderRenderer(render_config)
    
    def _load_tools(self):
        """Load available scene manipulation tools."""
        self.tools = {
            "place_object": self._place_object,
            "set_lighting": self._set_lighting,
            "apply_material": self._apply_material,
            "set_camera": self._set_camera
        }
    
    def _place_object(self, obj_type: str, position: Dict[str, float], attributes: Dict, object_index: int = 0):
        """Place an object in the scene."""
        # Create object
        obj = self.blender.create_object(
            obj_type,
            position,
            scale=attributes.get("scale"),
            rotation=attributes.get("rotation"),
            object_index=object_index
        )
        
        # Apply material if specified
        if "material" in attributes:
            material = self.blender.create_material(
                f"{obj_type}_material",
                attributes["material"]
            )
            self.blender.apply_material(obj, material)
        
        return obj
    
    def _set_lighting(self, lighting_config: Dict):
        """Configure scene lighting."""
        # Create main light
        main_light = self.blender.create_light(
            lighting_config["type"],
            lighting_config["position"],
            {
                "energy": lighting_config.get("energy", 5.0),
                "color": lighting_config.get("color", (1.0, 0.95, 0.8))
            }
        )
        
        # Create fill light if specified
        if "fill_light" in lighting_config:
            fill_light = self.blender.create_light(
                lighting_config["fill_light"]["type"],
                lighting_config["fill_light"]["position"],
                {
                    "energy": lighting_config["fill_light"].get("energy", 2.0),
                    "color": lighting_config["fill_light"].get("color", (0.8, 0.8, 1.0))
                }
            )
    
    def _apply_material(self, object_name: str, material_properties: Dict):
        """Apply material to an object."""
        obj = bpy.data.objects.get(object_name)
        if obj:
            material = self.blender.create_material(
                f"{object_name}_material",
                material_properties
            )
            self.blender.apply_material(obj, material)
    
    def _set_camera(self, position: Dict[str, float], target: Dict[str, float]):
        """Set up camera position and orientation."""
        self.blender.set_camera(
            position,
            target,
            fov=self.config.get("camera", {}).get("fov", 60.0)
        )
    
    def _execute_object_placement(self, obj: SceneObject, object_index: int = 0):
        """Execute placement of a single object."""
        # Convert position string to coordinates
        position = self._parse_position(obj.position)
        
        # Create object
        created_obj = self._place_object(obj.type, position, obj.attributes, object_index=object_index)
        
        # Apply relationships
        for rel in obj.relationships:
            self._apply_relationship(created_obj, rel)
        
        return created_obj
    
    def _parse_position(self, position_str: str) -> Dict[str, float]:
        """Convert position string to coordinates."""
        # Parse position string (e.g., "center", "left wall", "next to window")
        if position_str == "center":
            return {"x": 0, "y": 0, "z": 0}
        elif position_str == "left wall":
            return {"x": -4, "y": 0, "z": 0}
        elif position_str == "right wall":
            return {"x": 4, "y": 0, "z": 0}
        elif position_str == "front wall":
            return {"x": 0, "y": 4, "z": 0}
        elif position_str == "back wall":
            return {"x": 0, "y": -4, "z": 0}
        else:
            # Default to center if position is not recognized
            return {"x": 0, "y": 0, "z": 0}
    
    def _apply_relationship(self, obj: bpy.types.Object, relationship: Dict):
        """Apply spatial relationship between objects."""
        target_obj = bpy.data.objects.get(relationship["target"])
        if not target_obj:
            return
        
        if relationship["type"] == "next_to":
            # Position object next to target
            offset = relationship.get("offset", 1.0)
            direction = relationship.get("direction", "right")
            
            if direction == "right":
                obj.location.x = target_obj.location.x + offset
            elif direction == "left":
                obj.location.x = target_obj.location.x - offset
            elif direction == "front":
                obj.location.y = target_obj.location.y + offset
            elif direction == "back":
                obj.location.y = target_obj.location.y - offset
        
        elif relationship["type"] == "on_top":
            # Position object on top of target
            obj.location.z = target_obj.location.z + target_obj.dimensions.z/2 + obj.dimensions.z/2
        
        elif relationship["type"] == "inside":
            # Position object inside target
            obj.location = target_obj.location.copy()
    
    def execute(self, plan: ScenePlan) -> str:
        """Execute a scene construction plan and return the rendered image path."""
        try:
            # Clear existing scene
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete()
            
            # Create ground plane
            self.blender.create_ground_plane(size=10.0)
            
            # Create room if specified, else create a default room
            if hasattr(plan, "room") and plan.room:
                self.blender.create_room(
                    plan.room["dimensions"],
                    plan.room["wall_material"]
                )
            else:
                # Default room: 8x8x3, white walls
                self.blender.create_room(
                    {"width": 8.0, "length": 8.0, "height": 3.0},
                    {"base_color": (1.0, 1.0, 1.0, 1.0), "metallic": 0.0, "roughness": 0.8}
                )
            
            # Always add a sun light
            self.blender.create_sun_light(position={"x": 0, "y": 0, "z": 5}, energy=10.0)
            
            # Place objects
            for idx, obj in enumerate(plan.objects):
                created_obj = self._execute_object_placement(obj, object_index=idx)
                # Assign default material by type
                if obj.type.lower() in ["sofa"]:
                    material = self.blender.create_material("sofa_material", {"base_color": (0.5, 0.5, 0.5, 1.0)})
                    self.blender.apply_material(created_obj, material)
                elif obj.type.lower() in ["coffee_table", "coffee table"]:
                    material = self.blender.create_material("coffee_table_material", {"base_color": (0.9, 0.9, 0.9, 1.0)})
                    self.blender.apply_material(created_obj, material)
                elif obj.type.lower() in ["tv"]:
                    material = self.blender.create_material("tv_material", {"base_color": (0.1, 0.1, 0.1, 1.0)})
                    self.blender.apply_material(created_obj, material)
            
            # Set up camera (use default position/target for best visibility)
            self.blender.set_camera()
            
            # Create output directory if it doesn't exist
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            # Generate unique filename
            timestamp = int(time.time())
            output_path = str(output_dir.absolute() / f"scene_{timestamp}.png")
            
            # Render scene
            if not self.blender.render(output_path):
                raise RuntimeError("Failed to render scene")
            
            return output_path
            
        except Exception as e:
            print(f"Error executing plan: {str(e)}")
            raise
    
    def _apply_style_constraints(self, style: str, constraints: List[Dict]):
        """Apply style-specific constraints to the scene."""
        # Apply color scheme
        if style == "modern":
            self._apply_modern_style()
        elif style == "scandinavian":
            self._apply_scandinavian_style()
        elif style == "industrial":
            self._apply_industrial_style()
        
        # Apply specific constraints
        for constraint in constraints:
            if constraint["type"] == "color_scheme":
                self._apply_color_scheme(constraint["colors"])
            elif constraint["type"] == "lighting_style":
                self._apply_lighting_style(constraint["style"])
    
    def _apply_modern_style(self):
        """Apply modern style to the scene."""
        # Set neutral colors
        neutral_colors = [
            (0.9, 0.9, 0.9, 1.0),  # White
            (0.2, 0.2, 0.2, 1.0),  # Black
            (0.5, 0.5, 0.5, 1.0)   # Gray
        ]
        
        # Apply to objects
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                material = self.blender.create_material(
                    f"{obj.name}_material",
                    {"base_color": random.choice(neutral_colors)}
                )
                self.blender.apply_material(obj, material)
    
    def _apply_scandinavian_style(self):
        """Apply Scandinavian style to the scene."""
        # Set light, natural colors
        scandi_colors = [
            (0.95, 0.95, 0.95, 1.0),  # Off-white
            (0.9, 0.85, 0.8, 1.0),    # Light wood
            (0.8, 0.9, 0.95, 1.0)     # Light blue
        ]
        
        # Apply to objects
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                material = self.blender.create_material(
                    f"{obj.name}_material",
                    {"base_color": random.choice(scandi_colors)}
                )
                self.blender.apply_material(obj, material)
    
    def _apply_industrial_style(self):
        """Apply industrial style to the scene."""
        # Set industrial colors
        industrial_colors = [
            (0.2, 0.2, 0.2, 1.0),    # Dark gray
            (0.4, 0.4, 0.4, 1.0),    # Medium gray
            (0.6, 0.6, 0.6, 1.0)     # Light gray
        ]
        
        # Apply to objects
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                material = self.blender.create_material(
                    f"{obj.name}_material",
                    {
                        "base_color": random.choice(industrial_colors),
                        "metallic": 0.8,
                        "roughness": 0.2
                    }
                )
                self.blender.apply_material(obj, material)
    
    def render(self, output_path: str) -> bool:
        """Render the current scene."""
        try:
            # Set render settings
            bpy.context.scene.render.filepath = output_path
            bpy.context.scene.render.image_settings.file_format = 'PNG'
            
            # Render
            bpy.ops.render.render(write_still=True)
            return True
            
        except Exception as e:
            print(f"Error rendering scene: {str(e)}")
            return False

    def save_script(self, script: str, path: str = 'gen_scene.py'):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(script) 