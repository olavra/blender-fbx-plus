import bpy
import bmesh
from mathutils import Euler, Matrix
import math

# Constants for Bake Transform
BAKE_ROTATION_X = math.radians(90)  # 90 degrees in radians
BAKE_TOLERANCE = 1e-6  # Tolerance for floating-point precision cleanup


def apply_bake_transform(obj, context):
    """Apply Bake Transform to a single object.
    Returns the original active object and selection state for restoration."""
    
    print(f"BAKE_TRANSFORM: Applying Bake Transform to '{obj.name}' (Type: {obj.type})")
    
    # Store original active object and selection
    original_active = context.view_layer.objects.active
    original_selected = obj.select_get()
    
    try:
        # Clear selection and select only current object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        # Store original rotation
        original_rotation = obj.rotation_euler.copy()
        print(f"    Original rotation: {[math.degrees(x) for x in original_rotation]}")
        
        # Step 1: Reset object rotation to (0, 0, 0)
        obj.rotation_euler = (0, 0, 0)
        
        # Step 2: Rotate -90 degrees in X axis (LOCAL space)
        bpy.ops.transform.rotate(
            value=-BAKE_ROTATION_X, 
            orient_axis='X', 
            orient_type='LOCAL',
            constraint_axis=(True, False, False)
        )
        
        # Step 3: Apply rotation (bakes the -90 rotation into mesh data)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        
        # Step 4: Add original rotation + 90 degrees in X
        # This restores visual orientation while keeping mesh data transformed
        final_rotation = original_rotation.copy()
        final_rotation[0] += BAKE_ROTATION_X  # Add 90 degrees to X
        
        # Clean up floating-point precision errors (snap near-zero values to zero)
        for i in range(3):
            if abs(final_rotation[i]) < BAKE_TOLERANCE:
                final_rotation[i] = 0.0
        
        obj.rotation_euler = final_rotation
        
        print(f"    Final rotation: {[math.degrees(x) for x in obj.rotation_euler]}")
        print(f"    SUCCESS: Bake Transform applied to '{obj.name}'")
        return True, original_active, original_selected
        
    except Exception as e:
        print(f"    ERROR: Failed to apply Bake Transform to '{obj.name}': {str(e)}")
        return False, original_active, original_selected


def revert_bake_transform(obj, context):
    """Revert Bake Transform from a single object (inverse Bake Transform).
    Returns the original active object and selection state for restoration."""
    
    print(f"BAKE_TRANSFORM: Reverting Bake Transform from '{obj.name}' (Type: {obj.type})")
    
    # Store original active object and selection
    original_active = context.view_layer.objects.active
    original_selected = obj.select_get()
    
    try:
        # Clear selection and select only current object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        # Current rotation should be original + (90, 0, 0)
        current_rotation = obj.rotation_euler.copy()
        print(f"    Current rotation: {[math.degrees(x) for x in current_rotation]}")
        
        # Step 1: Calculate original rotation by subtracting the 90 degrees in X
        original_rotation = current_rotation.copy()
        original_rotation[0] -= BAKE_ROTATION_X  # Subtract 90 degrees from X
        
        # Clean up floating-point precision errors (snap near-zero values to zero)
        for i in range(3):
            if abs(original_rotation[i]) < BAKE_TOLERANCE:
                original_rotation[i] = 0.0
        
        print(f"    Calculated original rotation: {[math.degrees(x) for x in original_rotation]}")
        
        # Step 2: Reset object rotation to (0, 0, 0)
        obj.rotation_euler = (0, 0, 0)
        
        # Step 3: Rotate +90 degrees in X axis (LOCAL space)
        bpy.ops.transform.rotate(
            value=BAKE_ROTATION_X, 
            orient_axis='X', 
            orient_type='LOCAL',
            constraint_axis=(True, False, False)
        )
        
        # Step 4: Apply rotation (bakes the +90° rotation to cancel the -90° mesh rotation)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        
        # Step 5: Restore original rotation
        obj.rotation_euler = original_rotation
        
        print(f"    Final rotation: {[math.degrees(x) for x in obj.rotation_euler]}")
        print(f"    SUCCESS: Bake Transform reverted from '{obj.name}'")
        return True, original_active, original_selected
        
    except Exception as e:
        print(f"    ERROR: Failed to revert Bake Transform from '{obj.name}': {str(e)}")
        return False, original_active, original_selected


def apply_bake_transform_to_objects(objects, context):
    """Apply Bake Transform to a list of objects.
    Returns success status and restoration data."""
    
    print(f"BAKE_TRANSFORM: Applying Bake Transform to {len(objects)} objects")
    
    # Store original active object and selection
    original_active = context.view_layer.objects.active
    original_selection = [obj for obj in objects if obj.select_get()]
    
    success_count = 0
    failed_objects = []
    
    for obj in objects:
        if obj.type in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'ARMATURE', 'EMPTY'}:
            success, _, _ = apply_bake_transform(obj, context)
            if success:
                success_count += 1
            else:
                failed_objects.append(obj.name)
    
    # Restore original selection
    bpy.ops.object.select_all(action='DESELECT')
    for obj in original_selection:
        obj.select_set(True)
    if original_active:
        context.view_layer.objects.active = original_active
    
    context.view_layer.update()
    
    print(f"BAKE_TRANSFORM: Applied to {success_count} objects")
    if failed_objects:
        print(f"BAKE_TRANSFORM: Failed objects: {failed_objects}")
    
    return success_count > 0, original_active, original_selection


def revert_bake_transform_from_objects(objects, context, original_active=None, original_selection=None):
    """Revert Bake Transform from a list of objects.
    Restores original active object and selection."""
    
    print(f"BAKE_TRANSFORM: Reverting Bake Transform from {len(objects)} objects")
    
    success_count = 0
    failed_objects = []
    
    for obj in objects:
        if obj.type in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'ARMATURE', 'EMPTY'}:
            success, _, _ = revert_bake_transform(obj, context)
            if success:
                success_count += 1
            else:
                failed_objects.append(obj.name)
    
    # Restore original selection if provided
    if original_selection is not None:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selection:
            try:
                if obj.name in bpy.context.scene.objects:  # Make sure object still exists
                    obj.select_set(True)
            except:
                pass  # Object might have been deleted
    
    if original_active:
        try:
            if original_active.name in bpy.context.scene.objects:
                context.view_layer.objects.active = original_active
        except:
            pass  # Object might have been deleted
    
    context.view_layer.update()
    
    print(f"BAKE_TRANSFORM: Reverted from {success_count} objects")
    if failed_objects:
        print(f"BAKE_TRANSFORM: Failed objects: {failed_objects}")
    
    return success_count > 0 