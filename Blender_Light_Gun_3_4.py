bl_info = {
    "name": "Blender Light Gun",
    "author": "Jeff Walters (aka Plastered_Crab)",
    "version": (2, 5),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Light Gun",
    "description": "Use an active camera to point and place lights in your scene with ease using raycasts",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy
import bmesh
import time
import math
import numpy as np
from mathutils import Matrix, Vector
import bpy_extras
from bpy.app.handlers import persistent
from mathutils import Euler
import sys
from bpy.props import FloatProperty, BoolProperty
from bpy.types import Operator, Panel
from math import log
import bgl
import blf

# Global variable to store the last time the function was called
last_time_called = 0.0

# Define a minimum time interval between subsequent calls (in seconds)
min_interval = 0.005  # 0.1 seconds, adjust as needed




# class CustomErrorHandler:
    # def __init__(self, original_stderr):
        # self.original_stderr = original_stderr

    # def write(self, message):
        # if "RecursionError" not in message:
            # self.original_stderr.write(message)

    # def flush(self):
        # self.original_stderr.flush()

# sys.stderr = CustomErrorHandler(sys.stderr)

@persistent
def load_handler(dummy):
    bpy.ops.raycast.update_light_preview()

def raycast_from_camera(context):
    #print("raycast_from_camera")
    scene = context.scene
    camera = scene.camera
    cam_matrix = camera.matrix_world

    # Get the camera's direction
    direction = cam_matrix.to_quaternion() @ Vector((0.0, 0.0, -1.0))

    # Perform the raycast
    depsgraph = context.evaluated_depsgraph_get()
    hit, loc, norm, face_idx, *_ = scene.ray_cast(depsgraph, cam_matrix.translation, direction)

    if hit:
        return loc, norm
    else:
        return None, None
               
        


        #if settings.light_placement_mode == 'CAMERA':
            #print("In CAMERA settings update 1")
            #update_preview_light_position()
        #elif settings.light_placement_mode == 'ORBIT':
            # ... (Handle Orbit Mode)
            #print("In Orbit settings update 1")
        #else:
            #print("In NONE settings update 1")

#update statement for preview lights
def update_light_type(self, context):
    print("Updating light type to:", self.light_type)
    bpy.ops.object.preview_light_update()

def update_light_color(self, context):
    bpy.ops.object.preview_light_update()

def update_light_power(self, context):
    bpy.ops.object.preview_light_update()
    
def update_light_radius(self, context):
    bpy.ops.object.preview_light_update()

def update_light_diffuse(self, context):
    bpy.ops.object.preview_light_update()
    
def update_light_specular(self, context):
    bpy.ops.object.preview_light_update()

def update_light_volume(self, context):
    bpy.ops.object.preview_light_update()

def update_light_angle(self, context):
    bpy.ops.object.preview_light_update()
    
def update_light_spot_size(self, context):          
    bpy.ops.object.preview_light_update()    
    
def update_light_spot_blend(self, context):
    bpy.ops.object.preview_light_update()

def update_light_cone(self, context):
    bpy.ops.object.preview_light_update()
    
def update_light_are_shape(self, context):
    bpy.ops.object.preview_light_update()    
    
def update_light_area_size(self, context):
    bpy.ops.object.preview_light_update()    
    
def copy_settings_from_light(context):
    settings = context.scene.raycast_light_tool_settings
    light_object = context.active_object
    light_data = light_object.data
    
    settings.light_type = light_data.type
    settings.light_color = light_data.color
    settings.light_power = light_data.energy
    
    if light_data.type == 'POINT':
         settings.light_radius = light_data.shadow_soft_size
         settings.light_diffuse = light_data.diffuse_factor
         settings.light_specular = light_data.specular_factor
         settings.light_volume = light_data.volume_factor
    elif light_data.type == 'SUN':   
         settings.light_angle = light_data.angle
         settings.light_diffuse = light_data.diffuse_factor
         settings.light_specular = light_data.specular_factor
         settings.light_volume = light_data.volume_factor
    elif light_data.type == 'SPOT':
         settings.light_radius = light_data.shadow_soft_size
         settings.light_spot_size = light_data.spot_size
         settings.light_spot_blend = light_data.spot_blend
         settings.light_diffuse = light_data.diffuse_factor
         settings.light_specular = light_data.specular_factor
         settings.light_volume = light_data.volume_factor
         settings.light_show_cone = light_data.show_cone
    elif light_data.type == 'AREA':
         settings.light_area_shape = light_data.shape
         settings.light_area_size = (light_data.size, light_data.size_y)  
         #settings.light_area_size[0] = light_data.size
         #settings.light_area_size[1] = light_data.size_y
        
         settings.light_diffuse = light_data.diffuse_factor
         settings.light_specular = light_data.specular_factor
         settings.light_volume = light_data.volume_factor
          
    
class RAYCAST_OT_copy_settings(bpy.types.Operator):
    bl_idname = "raycast.copy_settings"
    bl_label = "Clone settings from light"
    bl_description = "Copy all settings from the selected light in the scene"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'LIGHT'

    def execute(self, context):
        copy_settings_from_light(context)
        return {'FINISHED'}    

class RAYCAST_OT_create_light(bpy.types.Operator):
    bl_idname = "object.raycast_create_light"
    bl_label = "Create Light"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        camera = scene.camera

        if not camera:
            self.report({'WARNING'}, "No active camera in the scene")
            return {'CANCELLED'}

        if camera.type != 'CAMERA':
            self.report({'WARNING'}, "Active camera is not a Camera object")
            return {'CANCELLED'}

        depsgraph = context.evaluated_depsgraph_get()
        settings = context.scene.raycast_light_tool_settings

        ray_start = camera.matrix_world.to_translation()
        ray_end = ray_start + camera.matrix_world.to_quaternion() @ Vector((0, 0, -10000000000000000))

        

        #checks if mesh hit is needing to be passed through and if not set the locations and other data
        success, location, normal, index, object, matrix = ray_cast_visible_meshes(scene, depsgraph, ray_start, ray_end)

        if success:
            if object.type == 'MESH':
                light_data = bpy.data.lights.new(name="New Light", type=settings.light_type)
                light_data.color = settings.light_color
                light_data.energy = settings.light_power


                print(f"Surface normal: {normal}, Object: {object.name}, Face index: {index}")
                if settings.light_type == 'POINT':
                    light_data.shadow_soft_size = settings.light_radius
                    light_data.diffuse_factor = settings.light_diffuse
                    light_data.specular_factor = settings.light_specular
                    light_data.volume_factor = settings.light_volume
                elif settings.light_type == 'SUN':   
                    light_data.angle = settings.light_angle
                    light_data.diffuse_factor = settings.light_diffuse
                    light_data.specular_factor = settings.light_specular
                    light_data.volume_factor = settings.light_volume
                elif settings.light_type == 'SPOT':
                    light_data.shadow_soft_size = settings.light_radius
                    light_data.spot_size = settings.light_spot_size
                    light_data.spot_blend = settings.light_spot_blend
                    light_data.diffuse_factor = settings.light_diffuse
                    light_data.specular_factor = settings.light_specular
                    light_data.volume_factor = settings.light_volume
                    light_data.show_cone = settings.light_show_cone
                elif settings.light_type == 'AREA':
                    light_data.shape = settings.light_area_shape
                    light_data.size = settings.light_area_size[0]
                    light_data.size_y = settings.light_area_size[1]
                    
                    light_data.diffuse_factor = settings.light_diffuse
                    light_data.specular_factor = settings.light_specular
                    light_data.volume_factor = settings.light_volume
                
                if location and normal and object is not None:
                    # Check if the object is a 2D object
                    is_2d_object = any(dimension == 0 for dimension in object.dimensions)
                    
                    if is_2d_object:
                        # Check if the camera's forward vector and the normal are pointing in the same direction
                        camera_forward = (camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
                        angle = normal.angle(camera_forward)

                        # If the angle between the normal and the camera's forward vector is more than 90 degrees, invert the normal
                        if not angle > math.radians(90):
                            normal = -normal


                light_object = bpy.data.objects.new(f"{settings.light_type.capitalize()} Light", light_data)
                light_object.location = location
                light_object.matrix_world.translation = location
                
                # Offset area light from the surface to prevent z-fighting
                offset_distance = 0.001  # You can adjust this value to change the offset
                if settings.light_type == 'AREA':
                    light_object.location += normal * offset_distance

                # Align the light to the face normal
                up = Vector((0, 0, -1))
                quat = normal.rotation_difference(up)
                light_object.rotation_euler = quat.to_euler()
                
                # Multiply the X and Y rotations for the light object by -1 if the Invert X/Y checkbox is checked
                
                light_object.rotation_euler.x *= -1
                light_object.rotation_euler.y *= -1

                try:
                    context.collection.objects.link(light_object)
                    
                    # Link the new light object's data to the previously created light object with the same settings
                    if settings.light_link_together and settings.last_created_light_name:
                        prev_light = context.scene.objects.get(settings.last_created_light_name)
                        if prev_light is not None:
                            if prev_light and prev_light.type == 'LIGHT' and prev_light.data.type == settings.light_type:
                                is_same_settings = True
                                for attr in ['color', 'energy', 'size', 'shadow_soft_size']:
                                    if hasattr(prev_light.data, attr) and getattr(prev_light.data, attr) != getattr(light_data, attr):
                                        is_same_settings = False
                                        break
                                if is_same_settings:
                                    try:
                                        # Replace the light data of the new light object first
                                        light_object.data = prev_light.data
                                        
                                        # Then remove the old light data
                                        light_data.user_clear()
                                        bpy.data.lights.remove(light_data)

                                        # Find the last created Linked Lights Set
                                        linked_lights_set_number = 1
                                        while bpy.data.collections.get(f"Linked Lights Set {linked_lights_set_number}") is not None:
                                            if prev_light.name in bpy.data.collections[f"Linked Lights Set {linked_lights_set_number}"].objects:
                                                break
                                            linked_lights_set_number += 1

                                        # Create a new Linked Lights Set if necessary
                                        if bpy.data.collections.get(f"Linked Lights Set {linked_lights_set_number}") is None:
                                            linked_lights_collection = bpy.data.collections.new(f"Linked Lights Set {linked_lights_set_number}")
                                            context.scene.collection.children.link(linked_lights_collection)

                                            # Move the first linked light to the new collection
                                            context.collection.objects.unlink(prev_light)
                                            linked_lights_collection.objects.link(prev_light)

                                        else:
                                            linked_lights_collection = bpy.data.collections[f"Linked Lights Set {linked_lights_set_number}"]

                                        # Move the new light object to the Linked Lights Set collection
                                        context.collection.objects.unlink(light_object)
                                        linked_lights_collection.objects.link(light_object)

                                    #handle a removed previous light
                                    except Exception:
                                        # Create a new light instead of linking
                                        light_object = bpy.data.objects.new(f"{settings.light_type.capitalize()} Light", light_data)
                                        context.collection.objects.link(light_object)
                                        
                                    # Update the 'last_created_light_name' property
                                    settings.last_created_light_name = light_object.name
                                    
                                else:
                                    light_object.data = light_data
                    else:
                        light_object.data = light_data
                except Exception as e:
                    self.report({'ERROR'}, f"Failed to link new light object to previous light (Maybe it was deleted?): {e}")
                    # Create a new light object using the current settings
                    new_light_data = bpy.data.lights.new(name="New Light", type=settings.light_type)
                    new_light_data.color = settings.light_color
                    new_light_data.energy = settings.light_power
                    
                    if settings.light_type == 'POINT':
                        new_light_data.shadow_soft_size = settings.light_radius
                        new_light_data.diffuse_factor = settings.light_diffuse
                        new_light_data.specular_factor = settings.light_specular
                        new_light_data.volume_factor = settings.light_volume
                    elif settings.light_type == 'SUN':   
                        new_light_data.angle = settings.light_angle
                        new_light_data.diffuse_factor = settings.light_diffuse
                        new_light_data.specular_factor = settings.light_specular
                        new_light_data.volume_factor = settings.light_volume
                    elif settings.light_type == 'SPOT':
                        new_light_data.shadow_soft_size = settings.light_radius
                        new_light_data.spot_size = settings.light_spot_size
                        new_light_data.spot_blend = settings.light_spot_blend
                        new_light_data.diffuse_factor = settings.light_diffuse
                        new_light_data.specular_factor = settings.light_specular
                        new_light_data.volume_factor = settings.light_volume
                        new_light_data.show_cone = settings.light_show_cone
                    elif settings.light_type == 'AREA':
                        new_light_data.shape = settings.light_area_shape
                        new_light_data.size = settings.light_area_size[0]
                        new_light_data.size_y = settings.light_area_size[1]
                        
                        new_light_data.diffuse_factor = settings.light_diffuse
                        new_light_data.specular_factor = settings.light_specular
                        new_light_data.volume_factor = settings.light_volume
                    # ... set other light data properties ...
                    
                    if location and normal and object is not None:
                        # Check if the object is a 2D object
                        is_2d_object = any(dimension == 0 for dimension in object.dimensions)
                        
                        if is_2d_object:
                            # Check if the camera's forward vector and the normal are pointing in the same direction
                            camera_forward = (camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
                            angle = normal.angle(camera_forward)

                            # If the angle between the normal and the camera's forward vector is more than 90 degrees, invert the normal
                            if not angle > math.radians(90):
                                normal = -normal
                    
                    new_light_object = bpy.data.objects.new(f"{settings.light_type.capitalize()} Light", new_light_data)
                    new_light_object.location = location
                    new_light_object.matrix_world.translation = location
                    
                    # Offset area light from the surface to prevent z-fighting
                    offset_distance = 0.001  # You can adjust this value to change the offset
                    if settings.light_type == 'AREA':
                        new_light_object.location += normal * offset_distance
                    
                    if settings.light_placement_mode == 'ORBIT':                   
                        
                        if location and normal and object is not None:
                            # Check if the object is a 2D object
                            is_2d_object = any(dimension == 0 for dimension in object.dimensions)
                            
                            if is_2d_object:
                                # Check if the camera's forward vector and the normal are pointing in the same direction
                                camera_forward = (camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
                                angle = normal.angle(camera_forward)

                                # If the angle between the normal and the camera's forward vector is more than 90 degrees, invert the normal
                                if not angle > math.radians(90):
                                    normal = -normal
                        
                        
                        empty = bpy.data.objects.new("Light Orbit Empty", None)
                        empty.location = location

                        # Set the empty object's rotation equal to the light object's rotation
                        empty.rotation_euler = new_light_object.rotation_euler

                        context.collection.objects.link(empty)

                        # Deselect all objects and select the empty object
                        bpy.ops.object.select_all(action='DESELECT')
                        context.view_layer.objects.active = empty
                        empty.select_set(True)

                        # Set the empty object as the light's parent
                        new_light_object.parent = empty

                        # Calculate the light's world location relative to the empty object
                        light_world_location = location + normal * settings.orbit_distance

                        # Set the light object's local location
                        new_light_object.location = empty.matrix_world.inverted() @ light_world_location
                        
                        # Add a Track To constraint to the light object
                        track_to_constraint = new_light_object.constraints.new(type="TRACK_TO")
                        track_to_constraint.target = empty
                        track_to_constraint.track_axis = 'TRACK_NEGATIVE_Z'
                        track_to_constraint.up_axis = 'UP_Y'
                    
                    elif settings.light_placement_mode == 'CAMERA':
                        new_light_object.location = camera.location
                        new_light_object.rotation_euler = camera.rotation_euler

                        # Deselect all objects and select the light object
                        bpy.ops.object.select_all(action='DESELECT')
                        context.view_layer.objects.active = new_light_object
                        new_light_object.select_set(True)
                    
                    # ... set other light object properties ...
                    context.collection.objects.link(new_light_object)
                    
                if settings.light_placement_mode == 'ORBIT':
                    
                    
                    if location and normal and object is not None:
                        # Check if the object is a 2D object
                        is_2d_object = any(dimension == 0 for dimension in object.dimensions)
                        
                        if is_2d_object:
                            # Check if the camera's forward vector and the normal are pointing in the same direction
                            camera_forward = (camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
                            angle = normal.angle(camera_forward)

                            # If the angle between the normal and the camera's forward vector is more than 90 degrees, invert the normal
                            if not angle > math.radians(90):
                                normal = -normal
                    
                    empty = bpy.data.objects.new("Light Orbit Empty", None)
                    empty.location = location

                    # Set the empty object's rotation equal to the light object's rotation
                    empty.rotation_euler = light_object.rotation_euler

                    context.collection.objects.link(empty)

                    # Deselect all objects and select the empty object
                    bpy.ops.object.select_all(action='DESELECT')
                    context.view_layer.objects.active = empty
                    empty.select_set(True)

                    # Set the empty object as the light's parent
                    light_object.parent = empty

                    # Calculate the light's world location relative to the empty object
                    light_world_location = location + normal * settings.orbit_distance

                    # Set the light object's local location
                    light_object.location = empty.matrix_world.inverted() @ light_world_location

                    # Add a Track To constraint to the light object
                    track_to_constraint = light_object.constraints.new(type="TRACK_TO")
                    track_to_constraint.target = empty
                    track_to_constraint.track_axis = 'TRACK_NEGATIVE_Z'
                    track_to_constraint.up_axis = 'UP_Y'



                elif settings.light_placement_mode == 'CAMERA':
                    light_object.location = camera.location
                    light_object.rotation_euler = camera.rotation_euler

                    # Deselect all objects and select the light object
                    bpy.ops.object.select_all(action='DESELECT')
                    context.view_layer.objects.active = light_object
                    light_object.select_set(True)
                
                # for Transform overrides for NONE mode
                else:
                    # Set transform overrides if present
                    if settings.transform_override:
                        # Apply additional location
                        light_object.location.x += settings.transform_location.x
                        light_object.location.y += settings.transform_location.y
                        light_object.location.z += settings.transform_location.z

                        # Apply additional rotation
                        light_object.rotation_euler.x += settings.transform_rotation.x
                        light_object.rotation_euler.y += settings.transform_rotation.y
                        light_object.rotation_euler.z += settings.transform_rotation.z

                        # Apply additional scale
                        light_object.scale.x *= settings.transform_scale.x
                        light_object.scale.y *= settings.transform_scale.y
                        light_object.scale.z *= settings.transform_scale.z
                
                
                # Update the 'last_created_light_name' property
                context.scene.raycast_light_tool_settings.last_created_light_name = light_object.name
                
            else:
                self.report({'WARNING'}, "Raycast did not hit a mesh object")
                return {'CANCELLED'}
        else:
            self.report({'WARNING'}, "No object hit by the raycast")
            return {'CANCELLED'}

        return {'FINISHED'}

def reset_settings(context):
    #prev_empty = bpy.context.object.get("Preview Empty")
    #preview_light = bpy.context.object.get("Preview Light")
    
    settings = context.scene.raycast_light_tool_settings
    settings.light_type = 'POINT'
    settings.light_color = (1.0, 1.0, 1.0)
    settings.light_power = 1000
    settings.light_radius = 1.0
    settings.light_diffuse = 1.0
    settings.light_specular = 1.0
    settings.light_volume = 1.0
    settings.light_angle = math.radians(45.0)
    settings.light_spot_size = math.radians(45.0)
    settings.light_spot_blend = 0.15
    settings.light_show_cone = False
    settings.light_area_shape = 'SQUARE'
    settings.light_area_size = (1.0, 1.0)
    settings.orbit_mode = False
    settings.orbit_distance = 1.0
    settings.light_placement_mode = 'NONE'
    settings.light_link_together = False
    settings.preview_mode = False
    
    empty_obj = bpy.data.objects.get("Preview Empty")
    if empty_obj is not None:
        bpy.data.objects.remove(empty_obj, do_unlink=True)
    
    light_obj = bpy.data.objects.get("Preview Light")
    if light_obj is not None:
        bpy.data.objects.remove(light_obj, do_unlink=True)

class RAYCAST_OT_reset_settings(bpy.types.Operator):
    bl_idname = "raycast.reset_settings"
    bl_label = "Reset to Default"
    bl_description = "Reset all settings to their default values"

    def execute(self, context):
        reset_settings(context)
        return {'FINISHED'}


# ------ Preview Light Code -------


def remove_preview_light_if_exists():     
    light_obj = bpy.data.objects.get("Preview Light")
    if light_obj is not None:
        bpy.data.objects.remove(light_obj, do_unlink=True)
        
def remove_prev_empty_if_exists():        
    empty_obj = bpy.data.objects.get("Preview Empty")
    if empty_obj is not None:
        bpy.data.objects.remove(empty_obj, do_unlink=True)


def update_preview_mode(self, context):
    settings = context.scene.raycast_light_tool_settings
    if settings.preview_mode:
        #remove empty upon switch to another placement mode:
        if settings.light_placement_mode != "ORBIT":
            remove_prev_empty_if_exists()
        
        #update preview light information
        bpy.ops.object.preview_light_update()
        
        
    
    else:
        remove_preview_light_if_exists()
        remove_prev_empty_if_exists()
    #print("update_preview_mode() called")

class RAYCAST_OT_preview_light_update(bpy.types.Operator):
    bl_idname = "object.preview_light_update"
    bl_label = "Update Light Preview"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        settings = bpy.context.scene.raycast_light_tool_settings

        # Check if the preview light already exists
        preview_light = context.scene.objects.get('Preview Light')

        if settings.preview_mode:
            if not preview_light:
                # Create the preview light
                light_data = bpy.data.lights.new(name="Preview Light", type=settings.light_type)
                preview_light = bpy.data.objects.new("Preview Light", light_data)
                bpy.context.collection.objects.link(preview_light)
                preview_light["is_preview_light"] = True

            

            preview_light["is_preview_light"] = True

            # Check if the type has changed and adjust accordingly
            if preview_light.data.type != settings.light_type:
                new_light_data = bpy.data.lights.new(name="Preview Light Data", type=settings.light_type)
                preview_light.data = new_light_data


            # Update the preview light's properties based on the settings
            light_data = preview_light.data
            light_data.type = settings.light_type
            light_data.color = settings.light_color
            light_data.energy = settings.light_power
            light_data.shadow_soft_size = settings.light_radius

            if settings.light_type == 'POINT':
                light_data.shadow_soft_size = settings.light_radius
                light_data.diffuse_factor = settings.light_diffuse
                light_data.specular_factor = settings.light_specular
                light_data.volume_factor = settings.light_volume
            elif settings.light_type == 'SUN':   
                light_data.angle = settings.light_angle
                light_data.diffuse_factor = settings.light_diffuse
                light_data.specular_factor = settings.light_specular
                light_data.volume_factor = settings.light_volume
            elif settings.light_type == 'SPOT':
                light_data.shadow_soft_size = settings.light_radius
                light_data.spot_size = settings.light_spot_size
                light_data.spot_blend = settings.light_spot_blend
                light_data.diffuse_factor = settings.light_diffuse
                light_data.specular_factor = settings.light_specular
                light_data.volume_factor = settings.light_volume
                light_data.show_cone = settings.light_show_cone
            elif settings.light_type == 'AREA':
                light_data.shape = settings.light_area_shape
                light_data.size = settings.light_area_size[0]
                light_data.size_y = settings.light_area_size[1]
                
                light_data.diffuse_factor = settings.light_diffuse
                light_data.specular_factor = settings.light_specular
                light_data.volume_factor = settings.light_volume

            
            if settings.light_placement_mode == 'CAMERA':
                #print("Moving Preview Light with CAMERA")
                camera = bpy.context.scene.camera
                camera_matrix = camera.matrix_world
                preview_light.matrix_world = camera_matrix.copy()
                preview_light.parent = camera
            elif settings.light_placement_mode == 'ORBIT':
                #print("Moving Preview Light with ORBIT")
                prev_empty = context.scene.objects.get('Preview Empty')
                if not prev_empty:
                    prev_empty = bpy.data.objects.new("Preview Empty", None)
                    bpy.context.collection.objects.link(prev_empty)
                update_preview_light_position(bpy.context.scene, prev_empty)  # Pass 'prev_empty' as an argument
            else:
                #print("Moving Preview Light with NONE")
                update_preview_light_position(bpy.context.scene)


        else:
            if preview_light:
                # Remove the preview light
                bpy.data.objects.remove(preview_light, do_unlink=True)

        return {'FINISHED'}

#what controls where the preview light is aimed at
def light_follow_camera(scene):
    
    global last_time_called  # Declare the global variable
    
    # Get the current time
    current_time = time.time()

    # Check if enough time has passed since the last call
    if current_time - last_time_called < min_interval:
        return  # Exit the function if not enough time has passed

    # Update last_time_called for the next call
    last_time_called = current_time
    
    settings = scene.raycast_light_tool_settings
    preview_light = scene.objects.get('Preview Light')
    
    if settings.preview_mode and settings.light_placement_mode == 'CAMERA' and preview_light:
        camera = scene.camera
        camera_matrix = camera.matrix_world
        preview_light.matrix_world = camera_matrix.copy()

    elif settings.preview_mode and settings.light_placement_mode == 'NONE' and preview_light:
        update_preview_light_position(bpy.context.scene)

    elif settings.preview_mode and settings.light_placement_mode == 'ORBIT' and preview_light:
        prev_empty = scene.objects.get('Preview Empty')
        update_preview_light_position(bpy.context.scene, prev_empty)
    
def ray_cast_visible_meshes(scene, depsgraph, ray_origin, ray_target, distance=1e6):
    result, location, normal, face_index, obj, matrix = scene.ray_cast(depsgraph, ray_origin, ray_target, distance=distance)
    
    
    #print("result: " + str(result))
    #print("location: " + str(location))
    #print("face_index: " + str(face_index))
    #print("matrix: " + str(matrix))

    
    while result:
        if obj.type == 'MESH' and not (obj.display_type == 'WIRE' or obj.get("is_volume") == 1):
            
            #debugging code
            #print("valid object hit, drawing line")
            #draw_ray(ray_origin, ray_target)
            #draw_normal(location, normal)
            
            return True, location, normal, face_index, obj, matrix
        else:
            #if result:
                #print(f"Ray hit object: {obj.name}")
            
            #print("Trying to check past initial hit object")
            
            # Move the ray_origin slightly past the current hit location
            new_ray_origin = location + (ray_target - ray_origin).normalized() * 0.001
            result, location, normal, face_index, obj, matrix = scene.ray_cast(depsgraph, new_ray_origin, ray_target, distance=distance)

    return False, None, None, None, None, None
    
    # for obj in scene.objects:
        # if obj.type == 'MESH' and not (obj.display_type == 'WIRE' or obj.get("is_volume") == 1):
            # evaluated_obj = obj.evaluated_get(depsgraph)
            # if evaluated_obj.type == 'MESH' and evaluated_obj.data is not None:
                # matrix_world_inv = obj.matrix_world.inverted()
                # ray_origin_obj_space = matrix_world_inv @ ray_origin
                # ray_target_obj_space = matrix_world_inv @ ray_target
                # result, hit, normal, face_index = evaluated_obj.ray_cast(ray_origin_obj_space, ray_target_obj_space, distance=distance)
                # if result:
                    # hit_world_space = obj.matrix_world @ hit
                    # normal_world_space = (obj.matrix_world.to_3x3() @ normal).normalized()
                    # hits.append((hit_world_space, normal_world_space, face_index, obj))

    # if hits:
        # hits.sort(key=lambda x: (ray_origin - x[0]).length)
        # return True, hits[0][0], hits[0][1], hits[0][2], hits[0][3], hits[0][3].matrix_world
    # else:
        # return False, None, None, None, None, None  

def update_preview_light_position(scene, prev_empty=None):
    settings = scene.raycast_light_tool_settings
    preview_light = scene.objects.get('Preview Light')
    
    camera = scene.camera
    if settings.preview_mode and settings.light_placement_mode == "NONE":
        ray_start = camera.matrix_world.to_translation()
        ray_end = ray_start + camera.matrix_world.to_quaternion() @ Vector((0, 0, -10000000000000000))

        depsgraph = bpy.context.evaluated_depsgraph_get()
        success, location, normal, index, object, matrix = ray_cast_visible_meshes(scene, depsgraph, ray_start, ray_end)
        
   #     print("update_preview_light_position() Updating XYZ NONE")
        
        # Check if the Preview Light exists and is parented to a camera
        if preview_light and preview_light.parent and preview_light.parent.type == 'CAMERA':
            # Unparent the Preview Light
            preview_light.parent = None
            print("Preview Light has been unparented.")
        
        if location and normal and object is not None:
            # Check if the object is a 2D object
            is_2d_object = any(dimension == 0 for dimension in object.dimensions)
            
            if is_2d_object:
                # Check if the camera's forward vector and the normal are pointing in the same direction
                camera_forward = (camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
                angle = normal.angle(camera_forward)

                # If the angle between the normal and the camera's forward vector is more than 90 degrees, invert the normal
                if not angle > math.radians(90):
                    normal = -normal
        
        if location and normal:
            if not preview_light:
                preview_light = create_preview_light(bpy.context)
            # Unhide the preview light when it hits a MESH object
            preview_light.hide_viewport = False
            preview_light.hide_render = False
            
            preview_light.location = location
            
            # Offset area light from the surface to prevent z-fighting
            offset_distance = 0.01  # You can adjust this value to change the offset
            if settings.light_type == 'AREA':
                preview_light.location += normal * offset_distance
            
            #preview_light.rotation_euler = norm.to_track_quat("Z", "Y").to_euler()
            # Align the light to the face normal
            up = Vector((0, 0, -1))
            quat = normal.rotation_difference(up)
            preview_light.rotation_euler = quat.to_euler()
            
            # Multiply the X and Y rotations for the light object by -1 if the Invert X/Y checkbox is checked
            
            preview_light.rotation_euler.x *= -1
            preview_light.rotation_euler.y *= -1
        
        elif preview_light:

            # Hide the preview light when it doesn't hit a MESH object
            preview_light.hide_viewport = True
            preview_light.hide_render = True
            
            #move the preview light to the world origin if raycast doesn't point at a MESH object
            preview_light.location = Vector((0, 0, 0))
            preview_light.rotation_euler = Euler((0, 0, 0))
            
        if settings.transform_override:
            print("trying to override transform data")
            
            # Apply additional location
            preview_light.location.x += settings.transform_location.x
            preview_light.location.y += settings.transform_location.y
            preview_light.location.z += settings.transform_location.z

            # Apply additional rotation
            preview_light.rotation_euler.x += settings.transform_rotation.x
            preview_light.rotation_euler.y += settings.transform_rotation.y
            preview_light.rotation_euler.z += settings.transform_rotation.z

            # Apply additional scale
            preview_light.scale.x = settings.transform_scale.x
            preview_light.scale.y = settings.transform_scale.y
            preview_light.scale.z = settings.transform_scale.z
            
    elif settings.preview_mode and settings.light_placement_mode == "CAMERA" and preview_light:
    #    print("update_preview_light_position() update XYZ CAMERA")
        camera = scene.camera
        camera_matrix = camera.matrix_world
        preview_light.matrix_world = camera_matrix.copy()
    elif settings.preview_mode and settings.light_placement_mode == "ORBIT":
        #loc, norm = raycast_from_camera(bpy.context)
        ray_start = camera.matrix_world.to_translation()
        ray_end = ray_start + camera.matrix_world.to_quaternion() @ Vector((0, 0, -10000000000000000))
        
        depsgraph = bpy.context.evaluated_depsgraph_get()
        success, location, normal, index, object, matrix = ray_cast_visible_meshes(scene, depsgraph, ray_start, ray_end)
   #     print("update_preview_light_position() Updating XYZ NONE")
        
        if settings.light_placement_mode == 'ORBIT' and prev_empty is None:
            prev_empty = scene.objects.get('Preview Empty')
            if prev_empty is None:
                prev_empty = bpy.data.objects.new("Preview Empty", None)
                scene.collection.objects.link(prev_empty)
        if location and normal and object is not None:
            # Check if the object is a 2D object
            is_2d_object = any(dimension == 0 for dimension in object.dimensions)
            
            if is_2d_object:
                # Check if the camera's forward vector and the normal are pointing in the same direction
                camera_forward = (camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
                angle = normal.angle(camera_forward)

                # If the angle between the normal and the camera's forward vector is more than 90 degrees, invert the normal
                if not angle > math.radians(90):
                    normal = -normal
        
        if location and normal:
            if not preview_light:
                preview_light = create_preview_light(bpy.context)

            # Logic for the Preview Empty
            if prev_empty is None:
                prev_empty = scene.objects.get('Preview Empty')
                if prev_empty is None:
                    prev_empty = bpy.data.objects.new("Preview Empty", None)
                    scene.collection.objects.link(prev_empty)

            # Unhide the Preview Empty when it hits a MESH object
            prev_empty.hide_viewport = False
            prev_empty.hide_render = False
            prev_empty.location = location
            
            # Unhide the Preview Light and position it
            preview_light.hide_viewport = False
            preview_light.hide_render = False
            
            #testing this below
            # Set the empty object's rotation equal to the light object's rotation
            prev_empty.rotation_euler = preview_light.rotation_euler
            
            # Set the empty object as the light's parent
            preview_light.parent = prev_empty
            
            # Calculate the light's world location relative to the empty object
            light_world_location = location + normal * settings.orbit_distance
            
            # Set the light object's local location
            preview_light.location = prev_empty.matrix_world.inverted() @ light_world_location

            # Check if the preview_light already has a "TRACK_TO" constraint
            track_to_constraint = None
            for constraint in preview_light.constraints:
                if constraint.type == 'TRACK_TO':
                    track_to_constraint = constraint
                    break

            # If the constraint doesn't exist, create it
            if not track_to_constraint:
                track_to_constraint = preview_light.constraints.new(type="TRACK_TO")
                track_to_constraint.track_axis = 'TRACK_NEGATIVE_Z'
                track_to_constraint.up_axis = 'UP_Y'

            # Update the constraint target
            track_to_constraint.target = prev_empty
            #testing this above
            
            # Align the light to the face normal
    #        up = Vector((0, 0, -1))
     #       quat = normal.rotation_difference(up)
     #       preview_light.rotation_euler = quat.to_euler()
            
            # Multiply the X and Y rotations for the light object by -1 if the Invert X/Y checkbox is checked
            
    #        preview_light.rotation_euler.x *= -1
    #        preview_light.rotation_euler.y *= -1
        
            #bpy.ops.object.preview_light_update()
        
        # Handle case when ray does not hit a MESH object
        elif preview_light:
            # Hide both the Preview Light and Preview Empty
            preview_light.hide_viewport = True
            preview_light.hide_render = True
            preview_light.location = Vector((0, 0, 0))
            preview_light.rotation_euler = Euler((0, 0, 0))

            if prev_empty:
                prev_empty.hide_viewport = True
                prev_empty.hide_render = True
                prev_empty.location = Vector((0, 0, 0))
                prev_empty.rotation_euler = Euler((0, 0, 0))
    
    

    #if setting.light_placement_mode != "CAMERA":
        
    
    #if ORBIT mode is switched off and prev_empty still exists then remove it
    if settings.light_placement_mode != 'ORBIT' and prev_empty:
        scene.collection.objects.unlink(prev_empty) 
        bpy.data.objects.remove(prev_empty, do_unlink=True)
        
class RAYCAST_OT_update_light_preview(bpy.types.Operator):
    bl_idname = "raycast.update_light_preview"
    bl_label = "Update Light Preview"

    _timer = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            update_preview_light_position(bpy.context.scene)

        return {'PASS_THROUGH'}

    def update(self, context):
        settings = context.scene.raycast_light_tool_settings
        if not settings.preview_mode or settings.light_placement_mode != 'ORBIT':
            remove_prev_empty_if_exists()

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}

#----[Start of Volumetric functions]-----
     

def delete_sphere_for_point(sphere_obj):
    bpy.data.objects.remove(sphere_obj)


# Function to get cone vertices
def get_cone_vertices(spot_light, steps, distance):
    cone_angle = spot_light.data.spot_size / 2
    
    # Take the parent's transform into account
    spot_matrix_world = spot_light.matrix_world

    base_center = spot_matrix_world.to_translation() + (spot_matrix_world.to_quaternion() @ Vector((0, 0, -distance)))
    vertices = []

    for i in range(steps):
        angle = (i / steps) * 2 * math.pi
        x = math.tan(cone_angle) * distance * math.cos(angle)
        y = math.tan(cone_angle) * distance * math.sin(angle)
        z = -distance
        vertex = spot_matrix_world.to_quaternion() @ Vector((x, y, z)) + spot_matrix_world.to_translation()
        vertices.append(vertex)

    return vertices

def get_sphere_vertices(point_light, steps, distance):
    # Take the parent's transform into account
    point_matrix_world = point_light.matrix_world

    print(point_light.matrix_world)

    sphere_center = point_matrix_world.to_translation()
    vertices = []

    for i in range(steps):
        for j in range(steps):
            theta = (i / (steps - 1)) * 2 * np.pi  # azimuthal angle
            phi = (j / (steps - 1)) * np.pi  # polar angle

            x = distance * np.sin(phi) * np.cos(theta)
            y = distance * np.sin(phi) * np.sin(theta)
            z = distance * np.cos(phi)

            vertex = Vector((x, y, z)) + sphere_center
            vertices.append(vertex)

    return vertices



# Function to create the cone volume mesh
def create_cone_mesh(name, spot_light, vertices):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    bm.from_mesh(mesh)

    # Get the local position of the apex relative to the SPOT light
    local_apex = spot_light.matrix_world.inverted() @ spot_light.matrix_world.to_translation()

    apex = bm.verts.new(local_apex)
    base_verts = [bm.verts.new(spot_light.matrix_world.inverted() @ vertex) for vertex in vertices]

    for i in range(len(base_verts)):
        bm.faces.new((apex, base_verts[i], base_verts[(i + 1) % len(base_verts)]))

    bm.faces.new(base_verts)
    bm.to_mesh(mesh)
    bm.free()

    # Set the parent
    obj.parent = spot_light
    
    # Create a new material and set it to use nodes
    material = bpy.data.materials.new(name="ConeMaterial")
    material.use_nodes = True

    # Get the material nodes
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    # Clear all nodes
    nodes.clear()

    # Create new Material Output and Principled Volume nodes
    material_output_node = nodes.new("ShaderNodeOutputMaterial")
    principled_volume_node = nodes.new("ShaderNodeVolumePrincipled")

    # Connect the Principled Volume node to the Material Output node
    links.new(principled_volume_node.outputs["Volume"], material_output_node.inputs["Volume"])

    # Assign the new material to the cone object
    obj.data.materials.append(material)

    #set the display mode to Wireframe so it doesn't interupt the main Light Gun functionality
    #obj.display_type = 'WIRE'
    
    obj.hide_select = True
    
    obj["is_volume"] = True

    return obj
    
    
def create_sphere_mesh(name, point_light, vertices):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    bm.from_mesh(mesh)

    # Calculate the radius of the sphere
    radius = (vertices[0] - point_light.location).length

    # Translate the bmesh to the point light's location
    bmesh.ops.translate(bm, vec=point_light.location)

    # Create a sphere at the translated location of the bmesh
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=radius)

    bm.to_mesh(mesh)
    bm.free()

    # Set the parent
    obj.parent = point_light

    # Create a new material and set it to use nodes
    material = bpy.data.materials.new(name="ConeMaterial")
    material.use_nodes = True

    # Get the material nodes
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    # Clear all nodes
    nodes.clear()

    # Create new Material Output and Principled Volume nodes
    material_output_node = nodes.new("ShaderNodeOutputMaterial")
    principled_volume_node = nodes.new("ShaderNodeVolumePrincipled")

    # Connect the Principled Volume node to the Material Output node
    links.new(principled_volume_node.outputs["Volume"], material_output_node.inputs["Volume"])

    # Assign the new material to the cone object
    obj.data.materials.append(material)

    #set the display mode to Wireframe so it doesn't interupt the main Light Gun functionality
    #obj.display_type = 'WIRE'
    
    obj.hide_select = True
    
    obj["is_volume"] = True

    # Print the coordinates of the point light and the sphere
    print(f"Point light location: {point_light.location}")
    print(f"Point light location: {point_light.matrix_world.translation}")
    print(f"Sphere location: {obj.matrix_world.translation}")
    print(f"Sphere location2: {obj.location}")

    return obj





#create volume depending on the type of light is active
def create_volume(light, distance, density, anisotropy, radius):
    if light.type == "POINT":
        create_sphere_for_point(light)
    elif light.type == "SPOT":
        create_cone_for_spotlight(light, distance, density, anisotropy)

def create_cone_for_spotlight(light, distance, density, anisotropy):
    #resolution of the Cone object
    steps = 64
    #distance = 10  # Set the distance value based on user requirements

    cone_vertices = get_cone_vertices(light, steps, distance)
    volume_mesh = create_cone_mesh(f"volume_{light.name}", light, cone_vertices) # Pass the 'light' parameter instead of 'light.name'
    volume_mesh.parent = light
    
    # Set the density and anisotropy values for the new cone mesh
    set_volume_density(light, density)
    set_volume_anisotropy(light, anisotropy)

def create_sphere_for_point(light):
    #resolution of the Sphere object
    steps = 64
    #distance = 10  # Set the distance value based on user requirements

    sphere_vertices = get_sphere_vertices(light, steps, light.data.shadow_soft_size)
    volume_mesh = create_sphere_mesh(f"volume_{light.name}", light, sphere_vertices) # Pass the 'light' parameter instead of 'light.name'
    volume_mesh.parent = light
    
    # Set the density and anisotropy values for the new cone mesh
    set_volume_density(light, light.data.density)
    set_volume_anisotropy(light, light.data.anisotropy)


def delete_volume(volume_obj):
    bpy.data.objects.remove(volume_obj)    
    

    
    
#What happens when the volumetric mesh gets updated
def update_volumetric_mesh(self, context):
    print("I am trying to update the volumetric mesh!")
    light = context.active_object
    if not light:
        return

    cone_distance = self.cone_distance
    sphere_distance = self.sphere_distance
    cube_distance = self.cube_distance

    if light.data.type == 'SPOT':
        print("SPOT LIGHT update distance")
        volume_name = f"volume_{light.name}"
        volume_mesh = bpy.data.objects.get(volume_name)

        # If the cone mesh already exists, remove it
        if volume_mesh:
            bpy.data.objects.remove(volume_mesh)

        # Create a new cone mesh with the updated distance
        cone_vertices = get_cone_vertices(light, 64, cone_distance)
        volume_mesh = create_cone_mesh(volume_name, light, cone_vertices)
        volume_mesh.parent = light
        
        volume_mesh.hide_select = True
        
        #Set the Density and Anisotropy based on the values in the panel upon update
        set_volume_density(light, self.density)
        set_volume_anisotropy(light, self.anisotropy)
        
    elif light.data.type == 'POINT':
        print("POINT LIGHT update distance")
        volume_name = f"volume_{light.name}"
        volume_mesh = bpy.data.objects.get(volume_name)

        # If the cone mesh already exists, remove it
        if volume_mesh:
            print("I AM DELETING THE MESH")
            bpy.data.objects.remove(volume_mesh)
        else:
            print("I DID NOT FIND THE MESH")


        # Create a new sphere mesh with the updated distance
        sphere_vertices = get_sphere_vertices(light, 64, sphere_distance)
        volume_mesh = create_sphere_mesh(volume_name, light, sphere_vertices)
        volume_mesh.parent = light
        
        volume_mesh.hide_select = True
        
        #Set the Density and Anisotropy based on the values in the panel upon update
        set_volume_density(light, self.density)
        set_volume_anisotropy(light, self.anisotropy)
        
    else:
        print("The selected object is not a SPOT light.")

def set_volume_density(light, density):
    volume_name = f"volume_{light.name}"
    volume_obj = bpy.data.objects.get(volume_name)
    if volume_obj:
        material = volume_obj.data.materials[0]
        principled_volume_node = material.node_tree.nodes.get("Principled Volume")
        principled_volume_node.inputs["Density"].default_value = density

def update_density(self, context):
    light = context.active_object
    if not light:
        return
    set_volume_density(light, self.density)

def set_volume_anisotropy(light, anisotropy):
    volume_name = f"volume_{light.name}"
    volume_obj = bpy.data.objects.get(volume_name)
    if volume_obj:
        material = volume_obj.data.materials[0]
        principled_volume_node = material.node_tree.nodes.get("Principled Volume")
        principled_volume_node.inputs["Anisotropy"].default_value = anisotropy

def update_anisotropy(self, context):
    light = context.active_object
    if not light:
        return
    set_volume_anisotropy(light, self.anisotropy)

class RAYCAST_PT_edit_light(bpy.types.Panel):
    bl_label = "Edit Selected Light Properties"
    bl_idname = "OBJECT_PT_raycast_edit_light"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Light Gun"
    bl_order = 2

    bpy.types.Light.cube_distance = FloatProperty(name="Cube Distance", default=10, min=0.001, update=update_volumetric_mesh)
    bpy.types.Light.sphere_distance = FloatProperty(name="Sphere Distance", default=5, min=0.001, update=update_volumetric_mesh)
    bpy.types.Light.cone_distance = FloatProperty(name="Cone Distance", default=10, min=0.001, update=update_volumetric_mesh)
    bpy.types.Light.density = FloatProperty(name="Density", default=.1, min=0, max=1, update=update_density)
    bpy.types.Light.anisotropy = FloatProperty(name="Anisotropy", default=0, min=-1, max=1, update=update_anisotropy)


    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.select_get() and context.object.type == 'LIGHT' and not context.object.get("is_preview_light")

    def toggle_volumetric(self, context):
        light = context.object
        light_data = light.data
        volume_name = f"volume_{light.name}"
        if light_data.type == "SPOT":
            print("Trying to toggle volumetric mesh for Cone")
            if light_data.use_volumetric_lighting :
                create_cone_for_spotlight(light, light_data.cone_distance, light_data.density, light_data.anisotropy)
            else:
                #volume_name = f"volume_{light.name}"
                
                print("Cone Name: " + volume_name)
                
                volume_obj = bpy.data.objects.get(volume_name)
                if volume_obj:
                    #delete_cone_for_spotlight(cone_obj)
                    print("Deleting Cone Mesh")
                    delete_volume(volume_obj)
        elif light_data.type == "POINT":
            print("Trying to toggle volumetric mesh for Point")
            if light_data.use_volumetric_lighting :
                create_sphere_for_point(light)            
            else:
                #volume_name = f"volume_{light.name}"
                print("Sphere Name: " + volume_name)
                volume_obj = bpy.data.objects.get(volume_name)
                if volume_obj:
                    print("Deleting Sphere Mesh")
                    delete_volume(volume_obj)            

    def draw(self, context):
        layout = self.layout
        light = context.object.data

        settings = bpy.context.scene.raycast_light_tool_settings

        layout.prop(light, "name", text="Light Name")
        layout.prop(light, "type", text="Type")

        if "color_mode" in light and light["color_mode"] == "TEMPERATURE":
            layout.operator("light.switch_to_rgb", text="Switch to RGB", icon="EVENT_T")
            #layout.label(text="Temperature")
            
            row = layout.row(align=True)
            row.scale_x = 2.6
            row.prop(light, "temperature_value", slider=True)
            
            sub = row.row(align=True)
            sub.scale_x = 0.2
            sub.operator("light.decrease_temperature", text="-", emboss=True)
            
            sub = row.row(align=True)
            sub.scale_x = 0.2
            sub.operator("light.increase_temperature", text="+", emboss=True)
            
            # Custom drawn color rectangle
            color_rect = row.column()
            color_rect.scale_x = 0.3
            color_rect.scale_y = 1
            color_rect.prop(light, "color", text="")
        else:     
            layout.operator("light.switch_to_temperature", text="Switch to Temperature", icon="EVENT_C")
            #layout.label(text="RGB Color")
            row = layout.row()
            row.prop(light, "color", text="Color")


        if light.type == 'POINT':
            #layout.prop(light, "energy", text="Power")
            row2 = layout.row(align=True)
            row2.scale_x = 2.0
            row2.prop(light, "energy", text="Power")
            
            sub = row2.row()
            sub.scale_x = 0.25
            sub.operator("light.decrease_power", text="-", emboss=True)
            
            sub = row2.row()
            sub.scale_x = 0.25  # Make the - button half as wide as the default
            sub.operator("light.increase_power", text="+", emboss=True)
            
            layout.prop(light, "shadow_soft_size", text="Radius")

            box = layout.box()
            box.prop(settings, "show_advanced_properties_edit", text="Advanced Properties", icon='TRIA_DOWN' if settings.show_advanced_properties_edit else 'TRIA_RIGHT')
            if settings.show_advanced_properties_edit:
                box.prop(light, "diffuse_factor", text="Diffuse")
                box.prop(light, "specular_factor", text="Specular")
                box.prop(light, "volume_factor", text="Volume")
            
            # #Volumetric Controls
            # layout.prop(light, "use_volumetric_lighting", text="Volumetric Lighting")
            # if light.use_volumetric_lighting:
                # layout.prop(light, "sphere_distance", text="Sphere Distance")
                # layout.prop(light, "density", text="Density")
                # layout.prop(light, "anisotropy", text="Anisotropy")

        elif light.type == 'SUN':
            #layout.prop(light, "energy", text="Power")
            row2 = layout.row(align=True)
            row2.scale_x = 2.0
            row2.prop(light, "energy", text="Power")
            
            sub = row2.row()
            sub.scale_x = 0.25
            sub.operator("light.decrease_power", text="-", emboss=True)
            
            sub = row2.row()
            sub.scale_x = 0.25  # Make the - button half as wide as the default
            sub.operator("light.increase_power", text="+", emboss=True)
            
            layout.prop(light, "shadow_soft_size", text="Radius")
            layout.prop(light, "angle", text="Angle")

            box = layout.box()
            box.prop(settings, "show_advanced_properties_edit", text="Advanced Properties", icon='TRIA_DOWN' if settings.show_advanced_properties_edit else 'TRIA_RIGHT')
            if settings.show_advanced_properties_edit:
                box.prop(light, "diffuse_factor", text="Diffuse")
                box.prop(light, "specular_factor", text="Specular")
                box.prop(light, "volume_factor", text="Volume")

        elif light.type == 'SPOT':
            #layout.prop(light, "energy", text="Power")
            row2 = layout.row(align=True)
            row2.scale_x = 2.0
            row2.prop(light, "energy", text="Power")
            
            sub = row2.row()
            sub.scale_x = 0.25
            sub.operator("light.decrease_power", text="-", emboss=True)
            
            sub = row2.row()
            sub.scale_x = 0.25  # Make the - button half as wide as the default
            sub.operator("light.increase_power", text="+", emboss=True)
            
            layout.prop(light, "shadow_soft_size", text="Radius")
            layout.prop(light, "spot_size", text="Spot Size")

            box = layout.box()
            box.prop(settings, "show_advanced_properties_edit", text="Advanced Properties", icon='TRIA_DOWN' if settings.show_advanced_properties_edit else 'TRIA_RIGHT')
            if settings.show_advanced_properties_edit:
                
                box.prop(light, "diffuse_factor", text="Diffuse")
                box.prop(light, "specular_factor", text="Specular")
                box.prop(light, "volume_factor", text="Volume")
                box.prop(light, "spot_blend", text="Blend")
            layout.prop(light, "show_cone", text="Show Cone")
            
            # #Volumetric Controls
            # layout.prop(light, "use_volumetric_lighting", text="Volumetric Lighting")
            # if light.use_volumetric_lighting:
                # layout.prop(light, "cone_distance", text="Cone Distance")
                # layout.prop(light, "density", text="Density")
                # layout.prop(light, "anisotropy", text="Anisotropy")

        elif light.type == 'AREA':
            #layout.prop(light, "energy", text="Power")
            row2 = layout.row(align=True)
            row2.scale_x = 2.0
            row2.prop(light, "energy", text="Power")
            
            sub = row2.row()
            sub.scale_x = 0.25
            sub.operator("light.decrease_power", text="-", emboss=True)
            
            sub = row2.row()
            sub.scale_x = 0.25  # Make the - button half as wide as the default
            sub.operator("light.increase_power", text="+", emboss=True)
            
            layout.prop(light, "shape", text="Shape")
            layout.prop(light, "size", text="Size X")
            if(light.shape == "RECTANGLE" or light.shape == "ELLIPSE"):
                layout.prop(light, "size_y", text="Size Y")

            box = layout.box()
            box.prop(settings, "show_advanced_properties_edit", text="Advanced Properties", icon='TRIA_DOWN' if settings.show_advanced_properties_edit else 'TRIA_RIGHT')
            if settings.show_advanced_properties_edit:
                box.prop(light, "diffuse_factor", text="Diffuse")
                box.prop(light, "specular_factor", text="Specular")
                box.prop(light, "volume_factor", text="Volume")
            
            # #Volumetric Controls
            # layout.prop(light, "use_volumetric_lighting", text="Volumetric Lighting")
            # if light.use_volumetric_lighting:
                # layout.prop(light, "cube_distance", text="Cube Distance")
                # layout.prop(light, "density", text="Density")
                # layout.prop(light, "anisotropy", text="Anisotropy")
    
    def update_volumetric(self, context):
        light = context.object
        update_cone(light.data, context)
        
    
    bpy.types.Light.use_volumetric_lighting = bpy.props.BoolProperty(name="Volumetric Lighting", update=toggle_volumetric)

#main panel power increases

class RAYCAST_OT_increase_light_power(bpy.types.Operator):
    bl_idname = "raycast.increase_light_power"
    bl_label = "Increase Light Power"

    def execute(self, context):
        settings = context.scene.raycast_light_tool_settings
        settings.light_power = settings.light_power + settings.light_power * .20  # Increase power by 20% each time
        return {'FINISHED'}


class RAYCAST_OT_decrease_light_power(bpy.types.Operator):
    bl_idname = "raycast.decrease_light_power"
    bl_label = "Decrease Light Power"

    def execute(self, context):
        settings = context.scene.raycast_light_tool_settings
        settings.light_power = settings.light_power - settings.light_power * .20  # Decrease power by 20% each time
        return {'FINISHED'}
 
# edit light panel power increases
 
class LIGHT_OT_increase_power(bpy.types.Operator):
    bl_idname = "light.increase_power"
    bl_label = "Increase Power"

    def execute(self, context):
        light = context.object.data
        light.energy = light.energy + light.energy * .20  # Increase power by 10% each time
        return {'FINISHED'}

class LIGHT_OT_decrease_power(bpy.types.Operator):
    bl_idname = "light.decrease_power"
    bl_label = "Decrease Power"

    def execute(self, context):
        light = context.object.data
        light.energy = light.energy - light.energy * .20  # Decrease power by 10% each time
        return {'FINISHED'}

 
class LIGHT_OT_SwitchToTemperatureNew(bpy.types.Operator):
    bl_idname = "light.switch_to_temperature_new"
    bl_label = "Switch to Temperature Mode for New Light"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.raycast_light_tool_settings
        settings["color_mode"] = "TEMPERATURE"
        
        
        settings.temperature_value = 6500

        
        return {'FINISHED'}

class LIGHT_OT_SwitchToRGBNew(bpy.types.Operator):
    bl_idname = "light.switch_to_rgb_new"
    bl_label = "Switch to RGB Mode for New Light"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.raycast_light_tool_settings
        if "color_mode" in settings:
            del settings["color_mode"]
            
        # Set the default RGB value
        settings.light_color = (1, 1, 1)  # White    
            
        return {'FINISHED'}

 
def update_temperature_color(self, context):
    rgb = kelvin_to_rgb(self.temperature_value)
    self.color = rgb

class LIGHT_OT_SwitchToTemperature(bpy.types.Operator):
    bl_idname = "light.switch_to_temperature"
    bl_label = "Switch to Temperature Mode"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        light = context.object.data
        light["color_mode"] = "TEMPERATURE"
        
        # Set the temperature_value to 6500 Kelvin
        light.temperature_value = 6500
        
        update_temperature_color(light, context)
        return {'FINISHED'}

class LIGHT_OT_SwitchToRGB(bpy.types.Operator):
    bl_idname = "light.switch_to_rgb"
    bl_label = "Switch to RGB Mode"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        light = context.object.data
        if "color_mode" in light:
            del light["color_mode"]
            
        # Set the default RGB value for the light
        light.color = (1, 1, 1)  # White
       
        return {'FINISHED'}

def kelvin_to_rgb(color_temperature):
    
    #Converts from K to RGB, algorithm courtesy of 
    #http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/
    

    # Range check
    if color_temperature < 1000: 
        color_temperature = 1000
    elif color_temperature > 40000:
        color_temperature = 40000
    
    tmp_internal = color_temperature / 100.0
    
    # Calculate Red:
    if tmp_internal <= 66:
        red = 255
    else:
        tmp_red = 329.698727446 * (tmp_internal - 60) ** -0.1332047592
        red = clamp(tmp_red, 0, 255)

    # Calculate Green:  
    if tmp_internal <= 66:
        tmp_green = 99.4708025861 * math.log(tmp_internal) - 161.1195681661
    else:
        tmp_green = 288.1221695283 * (tmp_internal - 60) ** -0.0755148492
    green = clamp(tmp_green, 0, 255)
    
    # Calculate Blue:
    if tmp_internal >= 66:
        blue = 255
    elif tmp_internal <= 19:
        blue = 0
    else:
        tmp_blue = 138.5177312231 * math.log(tmp_internal - 10) - 305.0447927307
        blue = clamp(tmp_blue, 0, 255)

    # Make it more reddish as it approaches 1000 K
    if color_temperature <= 1500:
        diff = 1500 - color_temperature

        # Quadratic Increase for Red
        red = red * (1 + (diff / 1000.0) ** 2)
        
        # Quadratic Decrease for Green and Blue
        green = green * (1 - 1.8 * (diff / 1000.0) ** 2)
        blue = blue * (1 - 1.8 * (diff / 1000.0) ** 2)
        
        red = clamp(red, 0, 255)
        green = clamp(green, 0, 255)
        blue = clamp(blue, 0, 255)


    return srgb_to_linear(red / 255), srgb_to_linear(green / 255), srgb_to_linear(blue / 255)

def srgb_to_linear(value):
    #Convert sRGB value to linear space.
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4

def clamp(x, min_val=0, max_val=255):
    
    return max(min(x, max_val), min_val)


def update_temperature_mode(light):
    if "color_mode" in light and light["color_mode"] == "TEMPERATURE":
        if "previous_rgb" in light:
            light.color = light["previous_rgb"]
        else:
            converter = ColorTemperatureConverter()
            light.color = kelvin_to_rgb(light["temperature_value"] if "temperature_value" in light else 1000)
    else:
        light["previous_rgb"] = light.color

class LIGHT_OT_increase_temperature(bpy.types.Operator):
    bl_idname = "light.increase_temperature"
    bl_label = "Increase Temperature"

    def execute(self, context):
        light = context.object.data
        light.temperature_value = light.temperature_value + light.temperature_value * .2  # Increment by 20% for demonstration; adjust as needed.
        return {'FINISHED'}

class LIGHT_OT_decrease_temperature(bpy.types.Operator):
    bl_idname = "light.decrease_temperature"
    bl_label = "Decrease Temperature"

    def execute(self, context):
        light = context.object.data
        light.temperature_value = light.temperature_value - light.temperature_value * .2  # Decrement by 20% for demonstration; adjust as needed.
        return {'FINISHED'}


def update_temperature_preview(self, context):
    temp_rgb = kelvin_to_rgb(self.temperature_value)
    self.temp_preview = temp_rgb
    
    
def update_temperature(self, context):
    self.light_color = kelvin_to_rgb(self.temperature_value)    
    
    
class RAYCAST_OT_increase_temperature(bpy.types.Operator):
    bl_idname = "raycast.increase_temperature"
    bl_label = "Increase Temperature for Raycast Panel"

    def execute(self, context):
        settings = context.scene.raycast_light_tool_settings
        settings.temperature_value += settings.temperature_value * .2  # Increment by 20% for demonstration; adjust as needed.
        return {'FINISHED'}    
    
class RAYCAST_OT_decrease_temperature(bpy.types.Operator):
    bl_idname = "raycast.decrease_temperature"
    bl_label = "Decrease Temperature for Raycast Panel"

    def execute(self, context):
        settings = context.scene.raycast_light_tool_settings
        settings.temperature_value -= settings.temperature_value * .2  # Decrement by 20% for demonstration; adjust as needed.
        return {'FINISHED'}

    
# Beginning of Orbit Distance Code changes

class RAYCAST_OT_increase_orbit_distance(bpy.types.Operator):
    bl_idname = "raycast.increase_orbit_distance"
    bl_label = "Increase Orbit Distance"

    def execute(self, context):
        settings = context.scene.raycast_light_tool_settings
        settings.orbit_distance = settings.orbit_distance + settings.orbit_distance * .20  # Increase orbit distance by 20% each time
        update_preview_light_position(context.scene)
        return {'FINISHED'}


class RAYCAST_OT_decrease_orbit_distance(bpy.types.Operator):
    bl_idname = "raycast.decrease_orbit_distance"
    bl_label = "Decrease Orbit Distance"

    def execute(self, context):
        settings = context.scene.raycast_light_tool_settings
        settings.orbit_distance = settings.orbit_distance - settings.orbit_distance * .20  # Decrease orbit distance by 20% each time
        update_preview_light_position(context.scene)
        return {'FINISHED'}    
    
    
    
    

##START OF EDIT CAMERA OPTIONS

def update_global_volumetrics(self, context):
    world = context.scene.world
    world_nodes = world.node_tree.nodes
    world_output = world_nodes.get("World Output")

    if self.global_volumetrics:
        # Create and connect the Volume Scatter node
        volume_scatter = world_nodes.new("ShaderNodeVolumeScatter")
        world_nodes.active = volume_scatter
        volume_scatter.inputs["Density"].default_value = 0.01
        volume_scatter.location = world_output.location + Vector((-300, 0))

        world_links = world.node_tree.links
        world_links.new(volume_scatter.outputs["Volume"], world_output.inputs["Volume"])

    else:
        # Delete the Volume Scatter node if it exists
        volume_scatter = world_nodes.get("Volume Scatter")
        if volume_scatter:
            world_nodes.remove(volume_scatter)
            
def update_volume_scatter_density(self, context):
    world = context.scene.world
    world_nodes = world.node_tree.nodes
    volume_scatter = world_nodes.get("Volume Scatter")
    
    if volume_scatter:
        volume_scatter.inputs["Density"].default_value = self.volume_scatter_density

def update_volume_scatter_anisotropy(self, context):
    world = context.scene.world
    world_nodes = world.node_tree.nodes
    volume_scatter = world_nodes.get("Volume Scatter")
    
    if volume_scatter:
        volume_scatter.inputs["Anisotropy"].default_value = self.volume_scatter_anisotropy




class RAYCAST_OT_shoot_raycast(bpy.types.Operator):
    bl_idname = "raycast.shoot_raycast"
    bl_label = "Detect Focus Distance"
    bl_description = "Shoot a raycast from the camera and set the Focus Distance to the first MESH object hit"

    def execute(self, context):
        camera = context.object
        scene = context.scene
        depsgraph = context.evaluated_depsgraph_get()

        origin = camera.location
        direction = camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))

        max_distance = 100000000  # You can adjust this value based on your scene's scale
        while True:
            # Raycast from the camera's location in the direction it's pointing
            result, location, normal, index, object, matrix = scene.ray_cast(depsgraph, origin, direction, distance=max_distance)

            if result:
                if object.type == 'MESH' and not (object.get("is_focus_plane", False) or object.get("is_volume", False)):
                    print("Raycast hit: " + object.name)
                    distance = (location - camera.location).length
                    camera.data.focus_distance = distance
                    self.report({'INFO'}, f"Focus Distance set to: {distance:.2f}")
                    break
                else:
                    # Update the raycast origin to ignore the hit object and continue the loop
                    origin = location + direction * 0.001
            else:
                self.report({'WARNING'}, "Raycast did not hit any object")
                break

        return {'FINISHED'}



# FOV Frustum Code Changes

#updates FOV Frustum upon changes to settings 

bpy.types.WindowManager.is_fov_timer_running = bpy.props.BoolProperty(default=False)

def get_active_scene_camera():
    scene = bpy.context.scene
    return scene.camera.data if scene.camera else None

#timer based updater for FOV preview mode
class FOV_UPDATE_OT_timer_operator(bpy.types.Operator):
    bl_idname = "fov_update.timer_operator"
    bl_label = "FOV Update Timer Operator"
    
    _timer = None
    _camera = None  # Store a reference to the camera object

    def invoke(self, context, event):
        wm = context.window_manager
        self._timer = wm.event_timer_add(1, window=context.window)
        wm.modal_handler_add(self)

        # When invoking, store a reference to the current camera
        self._camera = context.object
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        wm = context.window_manager
        
        if not context.scene.show_fov_lines:  # Use the scene property here
            print("Timer is turning off")
            self.cancel(context)
            wm.is_fov_timer_running = False
            return {'FINISHED'}

        if event.type == 'TIMER':
            print("Timer is on")
            camera_data = get_active_scene_camera()
            if camera_data:
                update_fov_lines(camera_data, context)
        
        return {'PASS_THROUGH'}
        
    def cancel(self, context):
        # Remove existing FOV lines and frustum mesh
        for obj in bpy.data.objects:
            if obj.name.startswith("FOV_Line") or obj.name.startswith("FOV_Frustum"):
                bpy.data.objects.remove(obj, do_unlink=True)
        
        context.window_manager.event_timer_remove(self._timer)

        
# show fov toggle button        
class FOV_TOGGLE_OT_start_stop(bpy.types.Operator):
    bl_idname = "fov_toggle.start_stop"
    bl_label = "Toggle FOV Lines"
    
    def execute(self, context):
        wm = context.window_manager
        
        if context.scene.show_fov_lines:  # Use the scene property here
            # If currently showing FOV lines, stop the timer
            context.scene.show_fov_lines = False
            print("Stopping Real-time FOV Preview")
            if wm.is_fov_timer_running:
                bpy.ops.fov_update.timer_operator('INVOKE_DEFAULT')  # This should call the modal's 'FINISHED' path
                
        else:
            # If not currently showing FOV lines, start the timer
            context.scene.show_fov_lines = True
            print("Starting Real-time FOV Preview")
            if not wm.is_fov_timer_running:
                bpy.ops.fov_update.timer_operator('INVOKE_DEFAULT')

        return {'FINISHED'}
        
        

def update_fov_lines(self, context):
    #print("[INFO] Updating FOV lines...")
    
    camera_obj = context.scene.camera
    if camera_obj is None:
        return
    camera = camera_obj.data

    wm = context.window_manager
    
    # Check the toggle on the scene property
    if context.scene.show_fov_lines:
        # Check if the operator is already running
        if not wm.is_fov_timer_running:
            # If not, start the operator
            bpy.ops.fov_update.timer_operator('INVOKE_DEFAULT')
            wm.is_fov_timer_running = True
    else:
        # If 'Show FOV Lines' is unchecked, the timer will stop in the next modal call.
        pass


    # Remove existing FOV lines and frustum mesh
    for obj in bpy.data.objects:
        if obj.name.startswith("FOV_Line") or obj.name.startswith("FOV_Frustum"):
            bpy.data.objects.remove(obj, do_unlink=True)

    if context.scene.show_fov_lines:
        cam_matrix = context.object.matrix_world
        sensor_width = camera.sensor_width
        sensor_height = camera.sensor_height
        focal_length = camera.lens

        # Define the FOV line distance
        fov_line_distance = camera.clip_end

        # Get render settings
        render = bpy.context.scene.render
        render_aspect_ratio_x = render.resolution_x * render.pixel_aspect_x
        render_aspect_ratio_y = render.resolution_y * render.pixel_aspect_y
        render_aspect_ratio = render_aspect_ratio_x / render_aspect_ratio_y

        # Calculate the aspect ratio and FOV angles based on the Sensor Fit property
        render = context.scene.render
        
        #check to see the ratios of both settings
        #swap_dimensions = render.resolution_y > render.resolution_x or render.pixel_aspect_y > render.pixel_aspect_x
        swap_dimensions_res = render.resolution_y > render.resolution_x
        swap_dimensions_aspect = render.pixel_aspect_y > render.pixel_aspect_x
        

        if swap_dimensions_res:
            if not swap_dimensions_aspect:
                aspect_ratio = (render.resolution_y * render.pixel_aspect_y) / (render.resolution_x * render.pixel_aspect_x)
            else:
                aspect_ratio = (render.resolution_x * render.pixel_aspect_x) / (render.resolution_y * render.pixel_aspect_y)
        else:
            if not swap_dimensions_aspect:
                aspect_ratio = (render.resolution_x * render.pixel_aspect_x) / (render.resolution_y * render.pixel_aspect_y)
            else: 
                aspect_ratio = (render.resolution_y * render.pixel_aspect_y) / (render.resolution_x * render.pixel_aspect_x)

        #Reasons it fails:
        #Resolution Y is bigger than Resolution X

        if (camera.sensor_fit == 'AUTO' and aspect_ratio > 1):
            #print("------------------------")
            #print("Path1")
            #print("Swap Dimensions Res: " + str(swap_dimensions_res))
            #print("Swap Dimensions Asp: " + str(swap_dimensions_aspect))
            #print("Aspect Ratio: " + str(aspect_ratio))
            #print("________________________")
            fov_x = 2 * math.atan(sensor_width / (2 * focal_length))
            fov_y = 2 * math.atan(math.tan(fov_x / 2) / aspect_ratio)
        elif (camera.sensor_fit == 'AUTO' and aspect_ratio < 1):
            #print("------------------------")
            #print("Path2")
            #print("Swap Dimensions Res: " + str(swap_dimensions_res))
            #print("Swap Dimensions Asp: " + str(swap_dimensions_aspect))
            #print("Aspect Ratio: " + str(aspect_ratio))
            #print("________________________")
            fov_y = 2 * math.atan(sensor_height / (2 * focal_length))
            fov_x = 2 * math.atan(math.tan(fov_y / 2) * aspect_ratio)
        elif (camera.sensor_fit == 'HORIZONTAL' and aspect_ratio > 1):
            #print("------------------------")
            #print("Path3")
            #print("Swap Dimensions Res: " + str(swap_dimensions_res))
            #print("Swap Dimensions Asp: " + str(swap_dimensions_aspect))
            #print("Aspect Ratio: " + str(aspect_ratio))
            #print("________________________")
            fov_x = 2 * math.atan(sensor_width / (2 * focal_length))
            fov_y = 2 * math.atan(math.tan(fov_x / 2) / aspect_ratio)
        elif (camera.sensor_fit == 'HORIZONTAL' and aspect_ratio < 1):
            #print("------------------------")
            #print("Path4")
            #print("Swap Dimensions Res: " + str(swap_dimensions_res))
            #print("Swap Dimensions Asp: " + str(swap_dimensions_aspect))
            #print("Aspect Ratio: " + str(aspect_ratio))
            #print("________________________")
            fov_y = 2 * math.atan(sensor_width / (2 * focal_length))
            fov_x = 2 * math.atan(math.tan(fov_y / 2) * aspect_ratio)
        elif (camera.sensor_fit == 'VERTICAL' and aspect_ratio > 1):
            #print("------------------------")
            #print("Path5")
            #print("Swap Dimensions Res: " + str(swap_dimensions_res))
            #print("Swap Dimensions Asp: " + str(swap_dimensions_aspect))
            #print("Aspect Ratio: " + str(aspect_ratio))
            #print("________________________")
            fov_x = 2 * math.atan(sensor_height / (2 * focal_length))
            fov_y = 2 * math.atan(math.tan(fov_x / 2) / aspect_ratio)
        elif (camera.sensor_fit == 'VERTICAL' and aspect_ratio < 1):
            #print("------------------------")
            #print("Path6")
            #print("Swap Dimensions Res: " + str(swap_dimensions_res))
            #print("Swap Dimensions Asp: " + str(swap_dimensions_aspect))
            #print("Aspect Ratio: " + str(aspect_ratio))
            #print("________________________")
            fov_y = 2 * math.atan(sensor_height / (2 * focal_length))
            fov_x = 2 * math.atan(math.tan(fov_y / 2) * aspect_ratio)


        # Calculate the corner points
        half_width = math.tan(fov_x / 2) * fov_line_distance
        half_height = math.tan(fov_y / 2) * fov_line_distance

        #if swap_dimensions:
        #    half_width, half_height = half_height, half_width

        if swap_dimensions_res:
            if not swap_dimensions_aspect:
                #print("Swapped half width/height")
                half_width, half_height = half_height, half_width
            else:
                #print("Regular half width/height")
                half_width, half_height = half_width, half_height
        else:
            if not swap_dimensions_aspect:
                #print("Regular half width/height")
                half_width, half_height = half_width, half_height
            else: 
                #print("Swapped half width/height")
                half_width, half_height = half_height, half_width

        # Define the 4 corner points in the camera's local space
        local_points = [
            Vector((-half_width, -half_height, -fov_line_distance)),
            Vector((half_width, -half_height, -fov_line_distance)),
            Vector((half_width, half_height, -fov_line_distance)),
            Vector((-half_width, half_height, -fov_line_distance))
        ]

        # Create the FOV frustum mesh
        frustum_name = "FOV_Frustum"
        frustum_mesh_data = bpy.data.meshes.new(frustum_name)
        frustum = bpy.data.objects.new(frustum_name, frustum_mesh_data)

        bpy.context.collection.objects.link(frustum)

        # Set the frustum's parent to the camera object
        frustum.parent = camera_obj

        # Set the frustum to be unselectable
        frustum.hide_select = True
        frustum.hide_render = True

        # Create the frustum vertices and faces
        frustum_mesh_data.from_pydata([Vector((0, 0, 0))] + local_points, [], [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1)])

        frustum_mesh_data.update()

        # Set the frustum color to red and apply opacity
        frustum_material = bpy.data.materials.new("FOV_Frustum_Material")
        frustum_material.use_nodes = True
        bsdf = frustum_material.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (1, 0, 0, 1)
        bsdf.inputs["Alpha"].default_value = camera.frustum_opacity
        frustum_material.blend_method = 'BLEND'
        frustum.data.materials.append(frustum_material)
        
        # Allow light to pass through the frustum mesh
        frustum_material.shadow_method = 'NONE'

        # Set the "is_volume" property to True for the frustum
        frustum["is_volume"] = True
        
        # start or end timer
        if context.scene.show_fov_lines:
            # Start the timer if it's not running
            if not wm.is_fov_timer_running:
                bpy.ops.fov_update.timer_operator('INVOKE_DEFAULT')
        

def update_focus_distance(self, context):
    camera = context.object.data
    focus_distance = camera.focus_distance

    # Set the actual Depth of Field properties
    camera.dof.use_dof = True
    camera.dof.focus_distance = focus_distance

    # Remove existing focus plane
    if "Focus_Distance_Plane" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Focus_Distance_Plane"], do_unlink=True)
    
    # Create a new focus plane
    if camera.show_focus_distance_plane:
        mesh = bpy.data.meshes.new("Focus_Distance_Plane_Mesh")
        plane = bpy.data.objects.new("Focus_Distance_Plane", mesh)

        bpy.context.collection.objects.link(plane)

        # Set the plane's parent to the camera object
        plane.parent = context.object

        # Add custom property to the Plane
        plane["is_focus_plane"] = True
        
        # Set the frustum to be unselectable
        plane.hide_select = True
        plane.hide_render = True

        # Set the plane's location and rotation relative to its parent
        plane.rotation_euler = (0, 0, 0)
        plane.location = context.object.matrix_world.inverted() @ (context.object.location + context.object.matrix_world.to_quaternion() @ Vector((0, 0, -focus_distance)))

        mesh.from_pydata([(0.25, 0.25, 0), (0.25, -0.25, 0), (-0.25, -0.25, 0), (-0.25, 0.25, 0)], [], [(0, 1, 2, 3)])
        mesh.update()

        mat = bpy.data.materials.new("Focus_Distance_Plane_Material")
        mat.use_nodes = True
        plane_opacity = context.object.get('plane_opacity', 0.5)
        mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = plane_opacity
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 0, 0, 1)
        mat.blend_method = 'BLEND'
        mat.diffuse_color = (1, 0, 0, plane_opacity)
        mesh.materials.append(mat)
        
        mat.shadow_method = 'NONE'
        

def update_show_focus_distance_plane(self, context):
    camera = context.object.data
    if not camera.show_focus_distance_plane:
        if "Focus_Distance_Plane" in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects["Focus_Distance_Plane"], do_unlink=True)
    else:
        update_focus_distance(self, context)


# Start of Edit Camera Panel code

class RAYCAST_PT_edit_camera(bpy.types.Panel):
    bl_label = "Edit Selected Camera Properties"
    bl_idname = "OBJECT_PT_raycast_edit_camera"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Light Gun"
    bl_order = 3

    bpy.types.Camera.focus_distance = FloatProperty(name="Focus Distance", default=10, min=0.001, update=update_focus_distance)
    bpy.types.Camera.show_focus_distance_plane = BoolProperty(name="Show Focus Distance Plane", default=False, update=update_show_focus_distance_plane)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.select_get() and context.object.type == 'CAMERA'

    def draw(self, context):
        layout = self.layout
        obj = context.object

        layout.prop(obj.data.dof, "use_dof", text="Depth of Field")
        
        # The other settings will be displayed only when Depth of Field is enabled
        if obj.data.dof.use_dof:
            layout.enabled = obj.data.dof.use_dof
            layout.prop(obj.data, "focus_distance")
            layout.prop(obj.data, "show_focus_distance_plane")
            if obj.data.show_focus_distance_plane:
                layout.prop(obj, "plane_opacity", text="Plane Opacity")
            layout.operator("raycast.shoot_raycast")
            
        if context.scene.show_fov_lines:     
            layout.operator("fov_toggle.start_stop", text="Disable FOV Lines")
            layout.prop(obj.data, "frustum_opacity", text="Frustum Opacity")
        else:
            layout.operator("fov_toggle.start_stop", text="Enable FOV Lines")
        
        

#Properties for the Edit Camera Panel
bpy.types.Object.plane_opacity = FloatProperty(name="Plane Opacity", default=0.5, min=.4, max=1, update=update_focus_distance)
bpy.types.Camera.show_fov_lines = BoolProperty(name="Show FOV Lines", default=False, update=update_fov_lines)
bpy.types.Camera.frustum_opacity = FloatProperty(name="Frustum Opacity", default=0.5, min=.4, max=1, update=update_fov_lines)


# #Switch color modes
# class PHOTOGRAPHER_OT_SwitchColorMode(bpy.types.Operator):
    # bl_idname = "photographer.switchcolormode"
    # bl_label = "Switch Color Mode"
    # bl_description = "Choose between Temperature in Kelvin and Color RGB"

    # light: bpy.props.StringProperty()

    # def execute(self, context):
        # light = bpy.data.lights[self.light]
        # if context.scene.render.engine == 'LUXCORE' and not light.photographer.enable_lc_physical:
            # if light.luxcore.color_mode == 'rgb':
                # light.luxcore.color_mode = 'temperature'
            # else:
                # light.luxcore.color_mode = 'rgb'
            # # Refresh viewport Trick
            # bpy.ops.object.add(type='EMPTY')
            # bpy.ops.object.delete()
        # else:
            # settings = light.photographer
            # settings.use_light_temperature = not settings.use_light_temperature

        # # Clear attributes
        # self.light = ''
        # return{'FINISHED'}

#custom temp color preview box


# Start of Main Panel code

class RAYCAST_PT_panel(bpy.types.Panel):
    bl_label = "Light Gun Control Panel"
    bl_idname = "OBJECT_PT_raycast_light"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Light Gun"
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        settings = context.scene.raycast_light_tool_settings

        layout.label(text="Light Properties")
        layout.prop(settings, "light_type", text="Type")
        layout.label(text="Basic Properties")
        
        
        #row.prop(settings, "temperature_value", slider=True)
        #row.prop(settings, "temp_preview", text="")
        if "color_mode" in settings and settings["color_mode"] == "TEMPERATURE":
            layout.operator("light.switch_to_rgb_new", text="Switch to RGB", icon="EVENT_T")
            #layout.label(text="Temperature")
            
            row = layout.row(align=True)
            row.scale_x = 2.6
            row.prop(settings, "temperature_value", slider=True)
            
            # Make the + and - buttons slightly smaller
            button_scale = 0.2
            
            sub = row.row(align=True)
            sub.scale_x = button_scale
            sub.operator("raycast.decrease_temperature", text="-", emboss=True)
            
            sub = row.row(align=True)
            sub.scale_x = button_scale
            sub.operator("raycast.increase_temperature", text="+", emboss=True)
            
            # Custom drawn color rectangle
            color_rect = row.column()
            color_rect.scale_x = 0.3
            color_rect.scale_y = 1
            color_rect.prop(settings, "light_color", text="")

        else:     
            layout.operator("light.switch_to_temperature_new", text="Switch to Temperature", icon="EVENT_C")
            #layout.label(text="RGB Color")
            
            
            row = layout.row()
            row.prop(settings, "light_color", text="Color")
            

        if settings.light_type == 'POINT':
            row2 = layout.row(align=True)
            row2.scale_x = 2.0
            row2.prop(settings, "light_power", text="Power")
            
            sub = row2.row()
            sub.scale_x = 0.25
            sub.operator("raycast.decrease_light_power", text="-", emboss=True)
            
            sub = row2.row()
            sub.scale_x = 0.25  
            sub.operator("raycast.increase_light_power", text="+", emboss=True)

            layout.prop(settings, "light_radius", text="Radius")

            box = layout.box()
            box.prop(settings, "show_advanced_properties", text="Advanced Properties", icon='TRIA_DOWN' if settings.show_advanced_properties else 'TRIA_RIGHT')
            if settings.show_advanced_properties: 
                box.prop(settings, "light_diffuse", text="Diffuse")
                box.prop(settings, "light_specular", text="Specular")
                box.prop(settings, "light_volume", text="Volume")

        elif settings.light_type == 'SUN':
            row2 = layout.row(align=True)
            row2.scale_x = 2.0
            row2.prop(settings, "light_power", text="Strength")
            
            sub = row2.row()
            sub.scale_x = 0.25
            sub.operator("raycast.decrease_light_power", text="-", emboss=True)
            
            
            sub = row2.row()
            sub.scale_x = 0.25  
            sub.operator("raycast.increase_light_power", text="+", emboss=True)

            layout.prop(settings, "light_angle", text="Angle")
            
            box = layout.box()
            box.prop(settings, "show_advanced_properties", text="Advanced Properties", icon='TRIA_DOWN' if settings.show_advanced_properties else 'TRIA_RIGHT')
            if settings.show_advanced_properties: 
                box.prop(settings, "light_diffuse", text="Diffuse")
                box.prop(settings, "light_specular", text="Specular")
                box.prop(settings, "light_volume", text="Volume")

        elif settings.light_type == 'SPOT':
            row2 = layout.row(align=True)
            row2.scale_x = 2.0
            row2.prop(settings, "light_power", text="Strength")
            
            sub = row2.row()
            sub.scale_x = 0.25
            sub.operator("raycast.decrease_light_power", text="-", emboss=True)
            
            sub = row2.row()
            sub.scale_x = 0.25  
            sub.operator("raycast.increase_light_power", text="+", emboss=True)
            layout.prop(settings, "light_radius", text="Radius")
            layout.prop(settings, "light_spot_size", text="Spot Size")

            box = layout.box()
            box.prop(settings, "show_advanced_properties", text="Advanced Properties", icon='TRIA_DOWN' if settings.show_advanced_properties else 'TRIA_RIGHT')
            if settings.show_advanced_properties: 
                box.prop(settings, "light_diffuse", text="Diffuse")
                box.prop(settings, "light_specular", text="Specular")
                box.prop(settings, "light_volume", text="Volume")
                box.prop(settings, "light_spot_blend", text="Blend")
                box.prop(settings, "light_show_cone", text="Show Cone")

        elif settings.light_type == 'AREA':
            row2 = layout.row(align=True)
            row2.scale_x = 2.0
            row2.prop(settings, "light_power", text="Strength")
            
            sub = row2.row()
            sub.scale_x = 0.25
            sub.operator("raycast.decrease_light_power", text="-", emboss=True)
            
            sub = row2.row()
            sub.scale_x = 0.25  
            sub.operator("raycast.increase_light_power", text="+", emboss=True)
            layout.prop(settings, "light_area_shape", text="Shape")
            layout.prop(settings, "light_area_size", text="Size (X/Y)")

            box = layout.box()
            box.prop(settings, "show_advanced_properties", text="Advanced Properties", icon='TRIA_DOWN' if settings.show_advanced_properties else 'TRIA_RIGHT')
            if settings.show_advanced_properties: 
                box.prop(settings, "light_diffuse", text="Diffuse")
                box.prop(settings, "light_specular", text="Specular")
                box.prop(settings, "light_volume", text="Volume")
        # Inside RAYCAST_PT_panel draw() function
        if settings.light_placement_mode == 'NONE':
            layout.prop(settings, "transform_override", text="Transform Override")
            if settings.transform_override:
                box = layout.box()
                box.label(text="Transform Settings:")
                box.prop(settings, "transform_location", text="Location")
                box.prop(settings, "transform_rotation", text="Rotation")
                box.prop(settings, "transform_scale", text="Scale")
                layout.operator("raycast.reset_transform_override", text="Reset Transform Override")

        layout.row().label(text="")
        layout.label(text="Additional Options")
        layout.prop(settings, "light_placement_mode")
        if settings.light_placement_mode == 'ORBIT':
            row_orbit = layout.row(align=True)
            row_orbit.scale_x = 2.0
            row_orbit.prop(settings, "orbit_distance", text="Orbit Distance")
            
            sub_orbit = row_orbit.row()
            sub_orbit.scale_x = 0.25
            sub_orbit.operator("raycast.decrease_orbit_distance", text="-", emboss=True)
            
            sub_orbit = row_orbit.row()
            sub_orbit.scale_x = 0.25
            sub_orbit.operator("raycast.increase_orbit_distance", text="+", emboss=True)

        layout.prop(settings, "global_volumetrics", text="Global Volumetrics")
        if settings.global_volumetrics:
            layout.prop(settings, "volume_scatter_density", text="Density")
            layout.prop(settings, "volume_scatter_anisotropy", text="Anisotropy")
        layout.prop(settings, "preview_mode")
        layout.prop(settings, "light_link_together")
        layout.operator("raycast.copy_settings")
        layout.operator("raycast.reset_settings")

        if settings.draw_lights_active == True:
            layout.operator("object.toggle_draw_lights", text="Disable Draw Lights")
        
        else:
            layout.operator("object.toggle_draw_lights", text="Enable Draw Lights")

        layout.row().label(text="Create Light")
        layout.operator("object.raycast_create_light")
            
            
# The function to reset the transform settings
def reset_transform_override(self, context):
    settings = context.scene.raycast_light_tool_settings
    settings.transform_location = (0.0, 0.0, 0.0)
    settings.transform_rotation = (0.0, 0.0, 0.0)
    settings.transform_scale = (1.0, 1.0, 1.0)

# Operator class for the reset button
class RAYCAST_OT_reset_transform_override(bpy.types.Operator):
    bl_idname = "raycast.reset_transform_override"
    bl_label = "Reset Transform Override"
    bl_description = "Reset the transform override settings to default values"

    def execute(self, context):
        reset_transform_override(self, context)
        bpy.ops.object.preview_light_update()
        return {'FINISHED'}



# Annotate draw lights code

def add_dummy_stroke(gp):
    # Create a new layer if it doesn't exist
    layer = gp.layers.get("Note")
    if layer is None:
        layer = gp.layers.new("Note", set_active=True)
    
    # Check if a frame already exists or create a new one
    frame = None
    for f in layer.frames:
        if f.frame_number == 1:
            frame = f
            break
    if frame is None:
        frame = layer.frames.new(1)
    
    # Create a new stroke
    stroke = frame.strokes.new()
    stroke.display_mode = '3DSPACE'
    
    # Add points to the stroke (for example, a single point at the origin)
    stroke.points.add(1)
    stroke.points[0].co = (0, 0, 0)
    
    # Clear the frame afterward
    frame.clear()


class ToggleDrawLightsOperator(bpy.types.Operator):
    bl_idname = "object.toggle_draw_lights"
    bl_label = "Toggle Draw Lights"
    
    def execute(self, context):
        settings = context.scene.raycast_light_tool_settings
        gp = bpy.data.grease_pencils.get("Annotations")
        
        # Create Annotations grease pencil data if it doesn't exist
        if gp is None:
            gp = bpy.data.grease_pencils.new("Annotations")
            context.scene.grease_pencil = gp
        
        if not settings.draw_lights_active:
            # Activate Annotate tool
            bpy.ops.wm.tool_set_by_id(name="builtin.annotate")
            
            # Set stroke placement to 'SURFACE'
            bpy.context.scene.tool_settings.annotation_stroke_placement_view3d = 'SURFACE'
            
            # Check if a layer named "Light" already exists
            light_layer = gp.layers.get("Light")
            
            if light_layer is None:
                # Add a dummy stroke to create a layer
                add_dummy_stroke(gp)
                
                # Rename the "Note" layer to "Light"
                default_layer = gp.layers.get("Note")
                if default_layer:
                    default_layer.info = "Light"
                    light_layer = default_layer
            
            # Set "Light" as the active layer and set its opacity to 0.0
            if light_layer:
                gp.layers.active = light_layer
                light_layer.annotation_opacity = 0.0
            
            # Start the modal timer (implement this as needed)
            bpy.ops.wm.modal_timer_operator()
            
            settings.draw_lights_active = True  # Set the draw lights mode to active
            
        else:
            # Deactivate Annotate tool
            bpy.ops.wm.tool_set_by_id(name="builtin.select_box")
            
            # Delete the 'Light' layer if it exists
            light_layer = gp.layers.get("Light")
            if light_layer:
                gp.layers.remove(light_layer)
                
            # Optionally, you can stop the modal timer here
            # Your implementation to stop the timer
            
            settings.draw_lights_active = False  # Set the draw lights mode to inactive

        return {'FINISHED'}



class PlaceLightsOperator(bpy.types.Operator):
    bl_idname = "object.place_lights_from_strokes"
    bl_label = "Place Lights from Strokes"

    def execute(self, context):
        scene = context.scene
        depsgraph = context.evaluated_depsgraph_get()
        gp = bpy.data.grease_pencils.get("Annotations")
        if gp:
            layer = gp.layers.get("Light")
            if layer:
                for frame in layer.frames:
                    for stroke in frame.strokes:
                        start_point = stroke.points[0].co if stroke.points else None
                        if start_point:
                            #print("Start Point:", start_point)

                            # Get the object and normal for the start_point
                            ray_start, ray_end = get_exact_object_and_normal(context, start_point, depsgraph)

                            if ray_start != None and ray_end != None:
                                # Create light at start_point
                                create_light_from_point(context, start_point, ray_start, ray_end)
                            
                    frame.clear()  # Remove all strokes from this frame

        return {'FINISHED'}
        
class ModalTimerOperator(bpy.types.Operator):
    bl_idname = "wm.modal_timer_operator"
    bl_label = "Modal Timer Operator"

    _timer = None

    def modal(self, context, event):
        settings = context.scene.raycast_light_tool_settings
        if event.type == 'TIMER' and settings.draw_lights_active:
            # your existing code
            bpy.ops.object.place_lights_from_strokes()
        
        active_tool = bpy.context.workspace.tools.from_space_view3d_mode('OBJECT', create=False)
        
        if not settings.draw_lights_active or (active_tool == True and active_tool.idname != "builtin.annotate"):
            return {'FINISHED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(1.0, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}     
 
def get_viewpoint_3d_coordinates(context):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                region_data = area.spaces.active.region_3d
                view_matrix = region_data.view_matrix

                # Direction from the viewpoint towards what the user is looking at
                view_direction = view_matrix.to_quaternion() @ Vector((0, 0, -1))

                # Invert the view matrix to transform from camera space to world space
                inverted_view_matrix = view_matrix.inverted()

                # Extract the camera's world-space location from the fourth column
                camera_location = Vector((inverted_view_matrix[0][3], inverted_view_matrix[1][3], inverted_view_matrix[2][3]))

                return camera_location, view_direction.normalized()

        return None, None
 
# detect which object was drawn on and where it was drawn on        
def get_exact_object_and_normal(context, start_point, depsgraph):
    # Function to get viewpoint coordinates

    # Initialize raycasting variables
    view_location, view_direction = get_viewpoint_3d_coordinates(context)

    if view_location is None or view_direction is None:
        return None, None

    # Calculate the direction from the view location to the start_point
    direction_to_start_point = start_point - view_location

    # Extend this direction to set ray_end
    ray_end = start_point + (direction_to_start_point.normalized() * 10000000000000000)  # some large number

    # ray_start would be the camera's view location
    ray_start = view_location

    # to debug the ray that is drawn
    #draw_ray(ray_start, ray_end)
    
    #print(f"Ray cast start: {ray_start}")
    #print(f"Ray cast end: {ray_end}")
    
    return ray_start, ray_end
       
def draw_normal(location, normal):
    normal_end = location + normal * 0.1  # Change the multiplier to set the length of the normal
    draw_ray(location, normal_end)
        
#debug ray line draw
def draw_ray(ray_start, ray_end):
    # Create a new mesh
    mesh = bpy.data.meshes.new(name="Ray")
    obj = bpy.data.objects.new("Ray", mesh)

    # Link it to scene
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Construct it in edit mode
    mesh = bpy.context.object.data
    bm = bmesh.new()

    # Create vertices
    v1 = bm.verts.new(ray_start)
    v2 = bm.verts.new(ray_end)

    # Create edge
    bm.edges.new((v1, v2))

    # Update & Free BMesh
    bm.to_mesh(mesh)
    bm.free()        
        
#function that PlaceLightsOperator uses when annotating in draw mode
def create_light_from_point(context, draw_location, ray_start, ray_end):
    # location is where object was hit by grease brush
    print("---------------------------------------")
    print("Inside Create Light From Point")
    print(f"Creating light at drawn location: {draw_location}")
    #print(f"Object hit: {object_hit}")
    #print(f"Initial normal: {normal}")
    
    depsgraph = context.evaluated_depsgraph_get()
    settings = context.scene.raycast_light_tool_settings
    scene = context.scene

    #draw_ray(ray_start, ray_end)

    #checks if mesh hit is needing to be passed through and if not set the locations and other data
    success, location, normal, index, object, matrix = ray_cast_visible_meshes(scene, depsgraph, ray_start, ray_end)
    #print("test old code location: " + str(location))
    
    

    #overrite location with draw_location
    #location = draw_location

    if success:
        #print("successfully hit visible object")
        if object.type == 'MESH':
            light_data = bpy.data.lights.new(name="New Light", type=settings.light_type)
            light_data.color = settings.light_color
            light_data.energy = settings.light_power


            print(f"Surface normal: {normal}, Object: {object.name}, Face index: {index}")
            if settings.light_type == 'POINT':
                light_data.shadow_soft_size = settings.light_radius
                light_data.diffuse_factor = settings.light_diffuse
                light_data.specular_factor = settings.light_specular
                light_data.volume_factor = settings.light_volume
            elif settings.light_type == 'SUN':   
                light_data.angle = settings.light_angle
                light_data.diffuse_factor = settings.light_diffuse
                light_data.specular_factor = settings.light_specular
                light_data.volume_factor = settings.light_volume
            elif settings.light_type == 'SPOT':
                light_data.shadow_soft_size = settings.light_radius
                light_data.spot_size = settings.light_spot_size
                light_data.spot_blend = settings.light_spot_blend
                light_data.diffuse_factor = settings.light_diffuse
                light_data.specular_factor = settings.light_specular
                light_data.volume_factor = settings.light_volume
                light_data.show_cone = settings.light_show_cone
            elif settings.light_type == 'AREA':
                light_data.shape = settings.light_area_shape
                light_data.size = settings.light_area_size[0]
                light_data.size_y = settings.light_area_size[1]
                
                light_data.diffuse_factor = settings.light_diffuse
                light_data.specular_factor = settings.light_specular
                light_data.volume_factor = settings.light_volume
            
            if location and normal and object is not None:
                # Check if the object is a 2D object
                is_2d_object = any(dimension == 0 for dimension in object.dimensions)
                
                if is_2d_object:
                    # Get the direction the viewport is looking towards
                    view_location, view_direction = get_viewpoint_3d_coordinates(context)
                    
                    # Calculate the direction of the ray itself (from start point to hit point)
                    ray_direction = (location - view_location).normalized()
                    
                    # Compute the angle between the ray direction and the surface normal
                    angle = normal.angle(ray_direction)
                    dot_product = normal.dot(ray_direction)

                    # If the angle between the normal and the ray's direction is more than 90 degrees, invert the normal
                    if not angle > math.radians(90):
                        normal = -normal


            light_object = bpy.data.objects.new(f"{settings.light_type.capitalize()} Light", light_data)
            light_object.location = location
            light_object.matrix_world.translation = location
            
            # Offset area light from the surface to prevent z-fighting
            offset_distance = 0.001  # You can adjust this value to change the offset
            if settings.light_type == 'AREA':
                light_object.location += normal * offset_distance

            # Align the light to the face normal
            up = Vector((0, 0, -1))
            quat = normal.rotation_difference(up)
            light_object.rotation_euler = quat.to_euler()
            
            # Multiply the X and Y rotations for the light object by -1 if the Invert X/Y checkbox is checked
            
            light_object.rotation_euler.x *= -1
            light_object.rotation_euler.y *= -1

            try:
                context.collection.objects.link(light_object)
                
                # Link the new light object's data to the previously created light object with the same settings
                if settings.light_link_together and settings.last_created_light_name:
                    prev_light = context.scene.objects.get(settings.last_created_light_name)
                    if prev_light is not None:
                        if prev_light and prev_light.type == 'LIGHT' and prev_light.data.type == settings.light_type:
                            is_same_settings = True
                            for attr in ['color', 'energy', 'size', 'shadow_soft_size']:
                                if hasattr(prev_light.data, attr) and getattr(prev_light.data, attr) != getattr(light_data, attr):
                                    is_same_settings = False
                                    break
                            if is_same_settings:
                                try:
                                    # Replace the light data of the new light object first
                                    light_object.data = prev_light.data
                                    
                                    # Then remove the old light data
                                    light_data.user_clear()
                                    bpy.data.lights.remove(light_data)

                                    # Find the last created Linked Lights Set
                                    linked_lights_set_number = 1
                                    while bpy.data.collections.get(f"Linked Lights Set {linked_lights_set_number}") is not None:
                                        if prev_light.name in bpy.data.collections[f"Linked Lights Set {linked_lights_set_number}"].objects:
                                            break
                                        linked_lights_set_number += 1

                                    # Create a new Linked Lights Set if necessary
                                    if bpy.data.collections.get(f"Linked Lights Set {linked_lights_set_number}") is None:
                                        linked_lights_collection = bpy.data.collections.new(f"Linked Lights Set {linked_lights_set_number}")
                                        context.scene.collection.children.link(linked_lights_collection)

                                        # Move the first linked light to the new collection
                                        context.collection.objects.unlink(prev_light)
                                        linked_lights_collection.objects.link(prev_light)

                                    else:
                                        linked_lights_collection = bpy.data.collections[f"Linked Lights Set {linked_lights_set_number}"]

                                    # Move the new light object to the Linked Lights Set collection
                                    context.collection.objects.unlink(light_object)
                                    linked_lights_collection.objects.link(light_object)

                                #handle a removed previous light
                                except Exception:
                                    # Create a new light instead of linking
                                    light_object = bpy.data.objects.new(f"{settings.light_type.capitalize()} Light", light_data)
                                    context.collection.objects.link(light_object)
                                    
                                # Update the 'last_created_light_name' property
                                settings.last_created_light_name = light_object.name
                                
                            else:
                                light_object.data = light_data
                else:
                    light_object.data = light_data
            except Exception as e:
                self.report({'ERROR'}, f"Failed to link new light object to previous light (Maybe it was deleted?): {e}")
                # Create a new light object using the current settings
                new_light_data = bpy.data.lights.new(name="New Light", type=settings.light_type)
                new_light_data.color = settings.light_color
                new_light_data.energy = settings.light_power
                
                if settings.light_type == 'POINT':
                    new_light_data.shadow_soft_size = settings.light_radius
                    new_light_data.diffuse_factor = settings.light_diffuse
                    new_light_data.specular_factor = settings.light_specular
                    new_light_data.volume_factor = settings.light_volume
                elif settings.light_type == 'SUN':   
                    new_light_data.angle = settings.light_angle
                    new_light_data.diffuse_factor = settings.light_diffuse
                    new_light_data.specular_factor = settings.light_specular
                    new_light_data.volume_factor = settings.light_volume
                elif settings.light_type == 'SPOT':
                    new_light_data.shadow_soft_size = settings.light_radius
                    new_light_data.spot_size = settings.light_spot_size
                    new_light_data.spot_blend = settings.light_spot_blend
                    new_light_data.diffuse_factor = settings.light_diffuse
                    new_light_data.specular_factor = settings.light_specular
                    new_light_data.volume_factor = settings.light_volume
                    new_light_data.show_cone = settings.light_show_cone
                elif settings.light_type == 'AREA':
                    new_light_data.shape = settings.light_area_shape
                    new_light_data.size = settings.light_area_size[0]
                    new_light_data.size_y = settings.light_area_size[1]
                    
                    new_light_data.diffuse_factor = settings.light_diffuse
                    new_light_data.specular_factor = settings.light_specular
                    new_light_data.volume_factor = settings.light_volume
                # ... set other light data properties ...
                
                if location and normal and object is not None:
                    # Check if the object is a 2D object
                    is_2d_object = any(dimension == 0 for dimension in object.dimensions)
                    
                    if is_2d_object:
                        # Get the direction the viewport is looking towards
                        view_location, view_direction = get_viewpoint_3d_coordinates(context)
                        
                        # Calculate the direction of the ray itself (from start point to hit point)
                        ray_direction = (location - view_location).normalized()
                        
                        # Compute the angle between the ray direction and the surface normal
                        angle = normal.angle(ray_direction)
                        dot_product = normal.dot(ray_direction)

                        # If the angle between the normal and the ray's direction is more than 90 degrees, invert the normal
                        if not angle > math.radians(90):
                            normal = -normal
                
                new_light_object = bpy.data.objects.new(f"{settings.light_type.capitalize()} Light", new_light_data)
                new_light_object.location = location
                new_light_object.matrix_world.translation = location
                
                # Offset area light from the surface to prevent z-fighting
                offset_distance = 0.001  # You can adjust this value to change the offset
                if settings.light_type == 'AREA':
                    new_light_object.location += normal * offset_distance
                
                if settings.light_placement_mode == 'ORBIT':                   
                    
                    if location and normal and object is not None:
                        # Check if the object is a 2D object
                        is_2d_object = any(dimension == 0 for dimension in object.dimensions)
                        
                        if is_2d_object:
                            # Get the direction the viewport is looking towards
                            view_location, view_direction = get_viewpoint_3d_coordinates(context)
                            
                            # Calculate the direction of the ray itself (from start point to hit point)
                            ray_direction = (location - view_location).normalized()
                            
                            # Compute the angle between the ray direction and the surface normal
                            angle = normal.angle(ray_direction)
                            dot_product = normal.dot(ray_direction)

                            # If the angle between the normal and the ray's direction is more than 90 degrees, invert the normal
                            if not angle > math.radians(90):
                                normal = -normal
                    
                    
                    empty = bpy.data.objects.new("Light Orbit Empty", None)
                    empty.location = location

                    # Set the empty object's rotation equal to the light object's rotation
                    empty.rotation_euler = new_light_object.rotation_euler

                    context.collection.objects.link(empty)

                    # Deselect all objects and select the empty object
                    bpy.ops.object.select_all(action='DESELECT')
                    context.view_layer.objects.active = empty
                    empty.select_set(True)

                    # Set the empty object as the light's parent
                    new_light_object.parent = empty

                    # Calculate the light's world location relative to the empty object
                    light_world_location = location + normal * settings.orbit_distance

                    # Set the light object's local location
                    new_light_object.location = empty.matrix_world.inverted() @ light_world_location
                    
                    # Add a Track To constraint to the light object
                    track_to_constraint = new_light_object.constraints.new(type="TRACK_TO")
                    track_to_constraint.target = empty
                    track_to_constraint.track_axis = 'TRACK_NEGATIVE_Z'
                    track_to_constraint.up_axis = 'UP_Y'
                
                elif settings.light_placement_mode == 'CAMERA':
                    return
                
                # ... set other light object properties ...
                context.collection.objects.link(new_light_object)
                
            if settings.light_placement_mode == 'ORBIT':
                
                
                if location and normal and object is not None:
                    # Check if the object is a 2D object
                    is_2d_object = any(dimension == 0 for dimension in object.dimensions)
                    
                    if is_2d_object:
                        # Get the direction the viewport is looking towards
                        view_location, view_direction = get_viewpoint_3d_coordinates(context)
                        
                        # Calculate the direction of the ray itself (from start point to hit point)
                        ray_direction = (location - view_location).normalized()
                        
                        # Compute the angle between the ray direction and the surface normal
                        angle = normal.angle(ray_direction)
                        dot_product = normal.dot(ray_direction)

                        # If the angle between the normal and the ray's direction is more than 90 degrees, invert the normal
                        if not angle > math.radians(90):
                            normal = -normal
                
                empty = bpy.data.objects.new("Light Orbit Empty", None)
                empty.location = location

                # Set the empty object's rotation equal to the light object's rotation
                empty.rotation_euler = light_object.rotation_euler

                context.collection.objects.link(empty)

                # Deselect all objects and select the empty object
                bpy.ops.object.select_all(action='DESELECT')
                context.view_layer.objects.active = empty
                empty.select_set(True)

                # Set the empty object as the light's parent
                light_object.parent = empty

                # Calculate the light's world location relative to the empty object
                light_world_location = location + normal * settings.orbit_distance

                # Set the light object's local location
                light_object.location = empty.matrix_world.inverted() @ light_world_location

                # Add a Track To constraint to the light object
                track_to_constraint = light_object.constraints.new(type="TRACK_TO")
                track_to_constraint.target = empty
                track_to_constraint.track_axis = 'TRACK_NEGATIVE_Z'
                track_to_constraint.up_axis = 'UP_Y'



            elif settings.light_placement_mode == 'CAMERA':
                return
            
            # for Transform overrides for NONE mode
            else:
                # Set transform overrides if present
                if settings.transform_override:
                    # Apply additional location
                    light_object.location.x += settings.transform_location.x
                    light_object.location.y += settings.transform_location.y
                    light_object.location.z += settings.transform_location.z

                    # Apply additional rotation
                    light_object.rotation_euler.x += settings.transform_rotation.x
                    light_object.rotation_euler.y += settings.transform_rotation.y
                    light_object.rotation_euler.z += settings.transform_rotation.z

                    # Apply additional scale
                    light_object.scale.x *= settings.transform_scale.x
                    light_object.scale.y *= settings.transform_scale.y
                    light_object.scale.z *= settings.transform_scale.z
            
            
            # Update the 'last_created_light_name' property
            context.scene.raycast_light_tool_settings.last_created_light_name = light_object.name
            
        else:
            #self.report({'WARNING'}, "Raycast did not hit a mesh object")
            return {'CANCELLED'} 
    else:
        #self.report({'WARNING'}, "Grease Brush did not hit a mesh object")
        return {'CANCELLED'}
    
    return light_object



class RaycastLightToolSettings(bpy.types.PropertyGroup):
    light_type: bpy.props.EnumProperty(
        name="Light Type",
        items=[
            ('POINT', "Point", "Point light"),
            ('SUN', "Sun", "Sun light"),
            ('SPOT', "Spot", "Spot light"),
            ('AREA', "Area", "Area light"),
        ],
        default='POINT',
        description="Color of the light",
        update=update_light_type,
    )
    light_color: bpy.props.FloatVectorProperty(
        name="Light Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        update=update_light_color,
    )
    light_power: bpy.props.FloatProperty(
        name="Power",
        default=1000,
        min=0.0,
        max=1000000.0,
        description="Power: light energy emitted over the entire area of the light in all directions",
        update=update_light_power,
    )
    light_radius: bpy.props.FloatProperty(
        name="Radius",
        default=1.0,
        min=0.0,
        max=10000.0,
        unit='LENGTH',
        description="Shadow Soft Size: light size for ray shadow sampling (Raytraced Shadows)",
        update=update_light_radius,
    )
    light_diffuse: bpy.props.FloatProperty(
        name="Diffuse",
        default=1.0,
        min=0.0,
        max=1.0,
        description="Diffuse Factor: diffuse reflection multiplier",
        update=update_light_diffuse,
    )
    light_specular: bpy.props.FloatProperty(
        name="Specular",
        default=1.0,
        min=0.0,
        max=1.0,
        description="Specular Factor: specular reflection multiplier",
        update=update_light_specular,
    )
    light_volume: bpy.props.FloatProperty(
        name="Volume",
        default=1.0,
        min=0.0,
        max=1.0,
        description="Volume Factor: volume light multiplier",
        update=update_light_volume,
    )
    light_angle: bpy.props.FloatProperty(
        name="Angle",
        default=math.radians(45.0),  
        min=math.radians(0.0),
        max=math.radians(360.0),   
        unit = 'ROTATION',
        description="Angle: angular diameter of the Sun as seen from the earth",
        update=update_light_angle,
    )
    light_spot_size: bpy.props.FloatProperty(
        name="Spot Size",
        default=math.radians(45.0),  
        min=math.radians(0.0),
        max=math.radians(180.0),   
        unit = 'ROTATION',
        description="Spot Size: angle of the spotlight beam",
        update=update_light_spot_size,
    )
    light_spot_blend: bpy.props.FloatProperty(
        name="Blend",
        default=0.15,
        min=0.0,
        max=1.0,
        description="Spot Blend: the softness of the spotlight edge",
        update=update_light_spot_blend,
    )
    light_show_cone: bpy.props.BoolProperty(
        name="Show Cone",
        default=False,
        description="Display transparent cone in 3D view to show what objects are contained in it",
        update=update_light_cone,
    )
    light_area_shape: bpy.props.EnumProperty(
        name="Area Shape",
        items=[
            ('SQUARE', "Square", "Square shape"),
            ('RECTANGLE', "Rectangle", "Rectangle shape"),
            ('DISK', "Disk", "Disk shape"),
            ('ELLIPSE', "Ellipse", "Ellipse shape"),
        ],
        default='SQUARE',
        description="Shape of area light",
        update=update_light_are_shape,
    )
    light_area_size: bpy.props.FloatVectorProperty(
        name="Size (X/Y)",
        default=(1.0, 1.0),
        size=2,
        subtype='XYZ',
        min=0.0,
        max=1000000.0,
        unit='LENGTH',
        description="Length in meters of each dimension of an area light",
        update=update_light_area_size,
    )
    
    #extra properties    
    orbit_mode: bpy.props.BoolProperty(
        name="Orbit Mode",
        description="Activate Orbit Mode for created lights",
        default=False,
    )
    orbit_distance: bpy.props.FloatProperty(
        name="Orbit Distance",
        description="Distance of the light from the surface in Orbit Mode",
        default=1.0,
        min=0.0,
        unit='LENGTH',
    )
    
    
    light_placement_mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('NONE', "None", "Places lights onto surfaces where camera is pointing"),
            ('ORBIT', "Orbit", "Places lights that are pointing at where the camera is pointing"),
            ('CAMERA', "Camera Position", "Place lights from exactly where the camera is at")
        ],
        default='NONE',
        description="Extra ways to place lights using the camera",
        update=update_preview_mode,
    )
    light_link_together: bpy.props.BoolProperty(
        name="Link Lights Together",
        description="Link lights created with the same settings together for synchronized editing",
        default=False,
    )    
    preview_mode: bpy.props.BoolProperty(
        name="Show Preview Light",
        description="Preview and tweak the light before placement (warning: Orbit Preview is demanding)",
        default=False,
        update=update_preview_mode
    )
    
    custom_distance: bpy.props.BoolProperty(
        name="Custom Distance",
        description="Custom Attenuation: Use custom attenuation distance instead of global light threshold",
        default=False,
    )    
    
    use_shadow: bpy.props.BoolProperty(
        name="Shadow Mode",
        description="",
        default=False,
    )    
    
    contact_shadow: bpy.props.BoolProperty(
        name="Contact Shadows",
        description="Contact Shadow: Use screenspace ray-tracing to have correct shadowing near occlurder, or for small features that does not appear in shadow maps. ",
        default=False,
    )        
    
    #store the last created light
    last_created_light_name: bpy.props.StringProperty(
        name="Last Created Light Name",
        description="The name of the most recently created light object",
    )
    
    #Global Volumetric Toggle
    global_volumetrics: bpy.props.BoolProperty(
        name="Global Volumetrics",
        description="Use global volumetrics with Volume Scatter node in the World shader nodes",
        default=False,
        update=update_global_volumetrics
    )
    
    volume_scatter_density: bpy.props.FloatProperty(
        name="Density",
        description="Density value for the global Volume Scatter node",
        default=0.01,
        min=0.0,
        max=100.0,
        update=update_volume_scatter_density,
    )
    
    volume_scatter_anisotropy: bpy.props.FloatProperty(
        name="Anisotropy",
        description="Anisotropy value for the global Volume Scatter node",
        default=0.00,
        min=-1.0,
        max=1.0,
        update=update_volume_scatter_anisotropy,
    )

    bpy.types.Light.temperature_value = bpy.props.FloatProperty(
        name="Temperature", 
        description="Color temperature in Kelvin", 
        min=1000, 
        max=13000, 
        default=6500,
        precision=0,
        update=update_temperature_color
    )
    
    temperature_value: bpy.props.FloatProperty(
        name="Temperature",
        description="Color temperature in Kelvin",
        default=6500,
        min=1000,
        max=13000,
        precision=0,
        update=update_temperature
    )
    
    temp_preview = bpy.props.FloatVectorProperty(
        name="Temperature Preview",
        subtype='COLOR',
        default=(1, 1, 1),
        min=0.0,
        max=1.0,
        description="Preview of the color temperature"
    )
    
    # Inside RaycastLightToolSettings
    transform_override: bpy.props.BoolProperty(
        name="Transform Override",
        description="Override the transform settings for the preview and created lights",
        default=False,
    )
    transform_location: bpy.props.FloatVectorProperty(
        name="Location",
        description="Location of the light",
        default=(0.0, 0.0, 0.0),
        subtype='XYZ',
    )
    transform_rotation: bpy.props.FloatVectorProperty(
        name="Rotation",
        description="Rotation of the light",
        default=(0.0, 0.0, 0.0),
        subtype='EULER',
    )
    transform_scale: bpy.props.FloatVectorProperty(
        name="Scale",
        description="Scale of the light",
        default=(1.0, 1.0, 1.0),
        subtype='XYZ',
    )
    
    show_advanced_properties: bpy.props.BoolProperty(
        name="Show Advanced Properties",
        description="Whether to show the advanced properties or not",
        default=True
    )
    
    show_advanced_properties_edit: bpy.props.BoolProperty(
        name="Show Advanced Properties",
        description="Whether to show the advanced properties or not",
        default=True
    )

    # fov property
    bpy.types.Scene.show_fov_lines = bpy.props.BoolProperty(
        name="Show FOV Lines",
        default=False,
        description="Toggle for showing FOV lines in the active camera"
    )

    # annotate draw light properties
    toggle_draw_lights: bpy.props.BoolProperty(
        name="Toggle Draw Lights",
        description="Enable/Disable Draw Lights",
        default=False
    )

    draw_lights_active: bpy.props.BoolProperty(
        name="Draw Lights Active",
        description="Whether the Draw Lights mode is active",
        default=False
    )

def register():
    bpy.utils.register_class(RAYCAST_OT_create_light)
    bpy.utils.register_class(RAYCAST_PT_panel)
    bpy.utils.register_class(RaycastLightToolSettings)
    bpy.utils.register_class(RAYCAST_OT_preview_light_update)
    bpy.utils.register_class(RAYCAST_OT_update_light_preview)
    bpy.app.handlers.load_post.append(load_handler)
    bpy.app.handlers.depsgraph_update_pre.append(light_follow_camera)
    bpy.utils.register_class(RAYCAST_OT_reset_settings)
    bpy.utils.register_class(RAYCAST_OT_copy_settings)
    
    bpy.utils.register_class(RAYCAST_OT_decrease_light_power)
    bpy.utils.register_class(RAYCAST_OT_increase_light_power)
    bpy.utils.register_class(RAYCAST_OT_increase_temperature)
    bpy.utils.register_class(RAYCAST_OT_decrease_temperature)
    bpy.utils.register_class(LIGHT_OT_SwitchToTemperatureNew)
    bpy.utils.register_class(LIGHT_OT_SwitchToRGBNew)
    
    #transform override
    bpy.utils.register_class(RAYCAST_OT_reset_transform_override)
    
    #orbit distance buttons
    bpy.utils.register_class(RAYCAST_OT_increase_orbit_distance)
    bpy.utils.register_class(RAYCAST_OT_decrease_orbit_distance)
    
    #Light edit panel
    bpy.utils.register_class(RAYCAST_PT_edit_light)
    bpy.types.Light.temperature = bpy.props.FloatProperty(name="Temperature", default=6500.0, min=1000.0, max=10000.0)
    bpy.utils.register_class(LIGHT_OT_increase_power)
    bpy.utils.register_class(LIGHT_OT_decrease_power)
    
    bpy.utils.register_class(LIGHT_OT_SwitchToTemperature)
    bpy.utils.register_class(LIGHT_OT_SwitchToRGB)
    
    bpy.utils.register_class(LIGHT_OT_increase_temperature)
    bpy.utils.register_class(LIGHT_OT_decrease_temperature)
    
    #Edit Camera panel
    bpy.utils.register_class(RAYCAST_PT_edit_camera)
    bpy.utils.register_class(RAYCAST_OT_shoot_raycast)
        
    bpy.utils.register_class(FOV_UPDATE_OT_timer_operator)   
    bpy.utils.register_class(FOV_TOGGLE_OT_start_stop)    

    #Volumetric
    #bpy.utils.register_class(ToggleVolumetricOperator)

    bpy.types.Scene.raycast_light_tool_settings = bpy.props.PointerProperty(type=RaycastLightToolSettings)


    # Annotation Grease Pencil Draw Lights code
    bpy.utils.register_class(ToggleDrawLightsOperator)
    bpy.utils.register_class(PlaceLightsOperator)
    bpy.utils.register_class(ModalTimerOperator)


def unregister():
    bpy.utils.unregister_class(RAYCAST_OT_create_light)
    bpy.utils.unregister_class(RAYCAST_PT_panel)
    bpy.utils.unregister_class(RaycastLightToolSettings)
    bpy.utils.unregister_class(RAYCAST_OT_preview_light_update)
    bpy.utils.unregister_class(RAYCAST_OT_update_light_preview)
    bpy.app.handlers.load_post.remove(load_handler)
    bpy.app.handlers.depsgraph_update_pre.remove(light_follow_camera)
    bpy.utils.unregister_class(RAYCAST_OT_reset_settings)
    bpy.utils.unregister_class(RAYCAST_OT_copy_settings)
    
    
    bpy.utils.unregister_class(RAYCAST_OT_decrease_light_power)
    bpy.utils.unregister_class(RAYCAST_OT_increase_light_power)
    bpy.utils.unregister_class(RAYCAST_OT_increase_temperature)
    bpy.utils.unregister_class(RAYCAST_OT_decrease_temperature)

    bpy.utils.unregister_class(LIGHT_OT_SwitchToTemperatureNew)
    bpy.utils.unregister_class(LIGHT_OT_SwitchToRGBNew)
    
    #transform override
    bpy.utils.unregister_class(RAYCAST_OT_reset_transform_override)

    
    
    #orbit distance buttons
    bpy.utils.unregister_class(RAYCAST_OT_increase_orbit_distance)
    bpy.utils.unregister_class(RAYCAST_OT_decrease_orbit_distance)
    
    
    #Light edit panel
    bpy.utils.unregister_class(RAYCAST_PT_edit_light)
    bpy.utils.unregister_class(LIGHT_OT_increase_power)
    bpy.utils.unregister_class(LIGHT_OT_decrease_power)
    
    bpy.utils.unregister_class(LIGHT_OT_SwitchToTemperature)
    bpy.utils.unregister_class(LIGHT_OT_SwitchToRGB)
    
    bpy.utils.unregister_class(LIGHT_OT_increase_temperature)
    bpy.utils.unregister_class(LIGHT_OT_decrease_temperature)
    
    #Edit Camera panel
    bpy.utils.unregister_class(RAYCAST_PT_edit_camera)
    bpy.utils.unregister_class(RAYCAST_OT_shoot_raycast)
    
    bpy.utils.unregister_class(FOV_UPDATE_OT_timer_operator)
    bpy.utils.unregister_class(FOV_TOGGLE_OT_start_stop)
    
    #Volumetric
    #bpy.utils.unregister_class(ToggleVolumetricOperator)

    del bpy.types.Scene.raycast_light_tool_settings
    del bpy.types.Light.temperature
    
    # Annotation Grease Pencil Draw Lights code
    bpy.utils.unregister_class(ToggleDrawLightsOperator)
    bpy.utils.unregister_class(PlaceLightsOperator)
    bpy.utils.unregister_class(ModalTimerOperator)

if __name__ == "__main__":
    register()
    
    
#TODO Later


#turn object into fake volumetric with button click?

#button to gain control of the light and fly it around to where you want it
    # put this maybe in the Edit Light plane
    # snap camera to the rotations of the light
    # add button to unsnap the camera from the light   
   
#mess with volumetric lighting
    #allow for toggleable Boolean modifiers with all Volumetric shapes so there is not stacking volume densities
    #single button that cycles through all selected lights with children MESH objects and selected MESH objects and adds a Union Boolean modifier to each one
    #fix issue with Linked volumetric lights not getting added to collections
    