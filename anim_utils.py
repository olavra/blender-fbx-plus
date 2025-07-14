import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty
from bpy.types import PropertyGroup


class ActionSelectionItem(PropertyGroup):
    """Property group for storing action selection state"""
    name: StringProperty()
    action: StringProperty()  # Store action name as string
    selected: BoolProperty(default=True)


class ACTION_OT_show_compatibility_warning(bpy.types.Operator):
    """Show compatibility warning for action"""
    bl_idname = "action.show_compatibility_warning"
    bl_label = "Action Compatibility Warning"
    bl_description = "This action is not compatible with any of the exported objects, or contains invalid f-curves"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    action_name: StringProperty()
    
    def execute(self, context):
        self.report({'WARNING'}, f"Action '{self.action_name}' is not compatible with any exported objects")
        return {'FINISHED'}


class ACTION_OT_show_compatibility_info(bpy.types.Operator):
    """Show compatibility info for action"""
    bl_idname = "action.show_compatibility_info"
    bl_label = "Action Compatibility Info"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    action_name: StringProperty()
    compatible_objects: StringProperty()
    
    @classmethod
    def description(cls, context, properties):
        if properties.compatible_objects:
            return f"Action '{properties.action_name}' is compatible with:\n{properties.compatible_objects}"
        return f"Action '{properties.action_name}' compatibility information"
    
    def execute(self, context):
        return {'FINISHED'}


def get_context_objects_for_export(context, operator):
    """Get the objects that would be exported based on the operator settings"""
    try:
        # Determine source collection
        source_collection = None
        if hasattr(operator, 'use_active_collection') and operator.use_active_collection:
            source_collection = context.view_layer.active_layer_collection.collection
        elif hasattr(operator, 'collection') and operator.collection:
            local_collection = bpy.data.collections.get((operator.collection, None))
            if local_collection:
                source_collection = local_collection

        # Get base objects
        if source_collection:
            if hasattr(operator, 'use_selection') and operator.use_selection:
                ctx_objects = tuple(obj for obj in source_collection.all_objects if obj.select_get())
            else:
                ctx_objects = source_collection.all_objects
        else:
            if hasattr(operator, 'use_selection') and operator.use_selection:
                ctx_objects = context.selected_objects
            else:
                ctx_objects = context.view_layer.objects

        # Filter by visibility
        if hasattr(operator, 'use_visible') and operator.use_visible:
            ctx_objects = tuple(obj for obj in ctx_objects if obj.visible_get())

        # Filter by object types
        filtered_objects = []
        if hasattr(operator, 'object_types') and operator.object_types:
            for obj in ctx_objects:
                if obj.type in operator.object_types:
                    filtered_objects.append(obj)
        else:
            filtered_objects = list(ctx_objects)

        return filtered_objects
    except Exception:
        # Return empty list if something goes wrong
        return []


def validate_actions(act, path_resolve):
    """Check if an action is compatible with an object by validating its f-curves"""
    if not act or not act.fcurves:
        return True  # Empty action is technically valid
    
    for fc in act.fcurves:
        data_path = fc.data_path
        if fc.array_index:
            data_path = data_path + "[%d]" % fc.array_index
        try:
            path_resolve(data_path)
        except ValueError:
            return False  # Invalid path
    return True  # All paths valid


def is_action_compatible_with_export(context, operator, action):
    """Check if an action is compatible with any of the objects that would be exported
    
    Returns:
        tuple: (is_compatible: bool, compatible_objects: list) where
               is_compatible is True if action is compatible with at least one object,
               compatible_objects is list of object names that are compatible
    """
    if not action or not action.fcurves:
        return True, []  # Empty action is technically compatible
    
    # Get objects that would be exported
    ctx_objects = get_context_objects_for_export(context, operator)
    
    # If no objects to export, consider action incompatible
    if not ctx_objects:
        return False, []
    
    compatible_objects = []
    
    # Check if action is compatible with any object
    for obj in ctx_objects:
        if not obj.animation_data:
            continue
        
        # Skip if action is read-only for this object
        if obj.animation_data.is_property_readonly('action'):
            continue
        
        # Check if action is compatible with this object
        try:
            path_resolve = obj.path_resolve
            if validate_actions(action, path_resolve):
                compatible_objects.append(obj.name)
        except Exception:
            continue  # Skip objects that can't be checked
    
    is_compatible = len(compatible_objects) > 0
    return is_compatible, compatible_objects


def populate_action_list(operator):
    """Populate the selected_actions collection with available actions"""
    available_actions = list(bpy.data.actions)
    
    # Update selected_actions collection if needed
    if len(operator.selected_actions) != len(available_actions):
        operator.selected_actions.clear()
        context = bpy.context
        
        for action in available_actions:
            item = operator.selected_actions.add()
            item.name = action.name
            item.action = action.name
            
            # Check compatibility to set default selection
            if hasattr(operator, 'bake_anim_export_actions') and operator.bake_anim_export_actions:
                is_compatible, _ = is_action_compatible_with_export(context, operator, action)
                item.selected = is_compatible  # Only select compatible actions by default
            else:
                item.selected = True  # If export actions is disabled, select all by default


def draw_action_selection_ui(layout, operator, enabled=True):
    """Draw the action selection UI in the export panel"""
    # Always populate selected_actions collection
    populate_action_list(operator)
    
    # Get available actions
    available_actions = list(bpy.data.actions)
    
    # Action selection UI
    box = layout.box()
    box.enabled = enabled
    
    # Show action list with checkboxes
    if available_actions:
        # Create a column for the action list
        col = box.column(align=True)
        
        # Adjust scale for better fitting when many actions
        if len(available_actions) > 10:
            col.scale_y = 0.9  # Slightly smaller rows for many actions
        
        # Show all actions with checkboxes
        for i, action_item in enumerate(operator.selected_actions):
            row = col.row()
            
            # Check if this action is compatible with exported objects
            context = bpy.context
            action = bpy.data.actions.get(action_item.action)
            is_compatible = True
            compatible_objects = []
            
            # Only check compatibility if actions export is enabled
            if enabled and hasattr(operator, 'bake_anim_export_actions') and operator.bake_anim_export_actions:
                is_compatible, compatible_objects = is_action_compatible_with_export(context, operator, action)
            
            # Add the checkbox
            prop_row = row.row()
            if not is_compatible:
                prop_row.alert = True
            prop_row.prop(action_item, "selected", text=action_item.name)
            prop_row.alignment = 'LEFT'
            
            # Add info/warning icon with fixed small size
            icon_row = row.row()
            icon_row.scale_x = 0.8  # Make icons smaller
            icon_row.scale_y = 0.8
            prop_row.alignment = 'RIGHT'
            
            # Add count row - always show count
            count_row = row.row()
            count_row.scale_x = 0.8
            count_row.scale_y = 0.8
            count_row.alignment = 'RIGHT'
            
            if not is_compatible:
                # Warning icon for incompatible actions
                warning_op = icon_row.operator("action.show_compatibility_warning", text="", icon='ERROR')
                warning_op.action_name = action_item.name
                # Show 0 for incompatible actions
                count_row.label(text="0")
            else:
                # Info icon with count for compatible actions
                if compatible_objects:
                    count = len(compatible_objects)
                    icon = 'OUTLINER_OB_ARMATURE'
                    # Use emboss=False for a cleaner look and add count as overlay
                    info_op = icon_row.operator("action.show_compatibility_info", text="", icon=icon, emboss=False)
                    info_op.action_name = action_item.name
                    info_op.compatible_objects = "\n".join(f"• {obj_name}" for obj_name in compatible_objects)
                    # Always show count (including 1)
                    count_row.label(text=str(count))
    else:
        box.label(text="No actions available", icon='INFO')


def get_selected_action_names(operator):
    """Get a set of selected action names from the operator"""
    return {item.action for item in operator.selected_actions if item.selected}


def register():
    """Register the PropertyGroup classes"""
    bpy.utils.register_class(ActionSelectionItem)
    bpy.utils.register_class(ACTION_OT_show_compatibility_warning)
    bpy.utils.register_class(ACTION_OT_show_compatibility_info)


def unregister():
    """Unregister the PropertyGroup classes"""
    bpy.utils.unregister_class(ActionSelectionItem)
    bpy.utils.unregister_class(ACTION_OT_show_compatibility_warning)
    bpy.utils.unregister_class(ACTION_OT_show_compatibility_info) 