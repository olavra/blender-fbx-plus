import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty
from bpy.types import PropertyGroup, UIList


class ActionSelectionItem(PropertyGroup):
    """Property group for storing action selection state"""
    name: StringProperty()
    action: StringProperty()  # Store action name as string
    selected: BoolProperty(default=True)


class AnimationGroupSelectionItem(PropertyGroup):
    """Property group for animation group selection items"""
    name: StringProperty()
    group_name: StringProperty()
    selected: BoolProperty(default=True)


def is_action_binder_enabled():
    """Check if Action Binder addon is enabled"""
    try:
        import addon_utils
        # Check multiple possible addon names
        addon_names = ["action_binder", "Action Binder"]
        for name in addon_names:
            if addon_utils.check(name)[0]:
                return True
        
        # Also check if the module is directly available
        try:
            import sys
            return "action_binder" in sys.modules
        except:
            pass
            
        return False
    except Exception as e:
        print(f"Error checking Action Binder addon: {e}")
        return False


def get_animation_groups_data():
    """Get Animation Groups data from scene if Action Binder is enabled"""
    if not is_action_binder_enabled():
        return None
    
    scene = bpy.context.scene
    if not hasattr(scene, 'animation_groups_data'):
        return None
    
    return scene.animation_groups_data


class ACTION_UL_selection_list(UIList):
    """UIList for displaying action selection with checkboxes and compatibility info"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Get the action and check compatibility
            action = bpy.data.actions.get(item.action)
            is_compatible = True
            compatible_objects = []
            
            # Check compatibility if actions export is enabled
            if hasattr(data, 'bake_anim_export_actions') and data.bake_anim_export_actions:
                is_compatible, compatible_objects = is_action_compatible_with_export(context, data, action)
            
            # Main row
            row = layout.row(align=True)
            
            # Checkbox
            checkbox_row = row.row()
            checkbox_row.alignment = 'LEFT'
            if not is_compatible:
                checkbox_row.alert = True
            checkbox_row.prop(item, "selected", text="")
            
            # Add some spacing between checkbox and name
            row.separator_spacer()
            
            # Action name
            name_row = row.row()
            if not is_compatible:
                name_row.alert = True
            name_row.label(text=item.name)
            
            # Right side - compatibility info and count
            info_row = row.row()
            info_row.alignment = 'RIGHT'
            
            if not is_compatible:
                # Warning icon for incompatible actions
                warning_op = info_row.operator("action.show_compatibility_warning", text="", icon='ERROR', emboss=False)
                warning_op.action_name = item.name
                info_row.label(text="0")
            else:
                # Info icon and count for compatible actions
                if compatible_objects:
                    count = len(compatible_objects)
                    info_op = info_row.operator("action.show_compatibility_info", text="", icon='OUTLINER_OB_ARMATURE', emboss=False)
                    info_op.action_name = item.name
                    info_op.compatible_objects = "\n".join(f"• {obj_name}" for obj_name in compatible_objects)
                    info_row.label(text=str(count))
                else:
                    # No compatible objects but no error
                    info_row.label(text="", icon='BLANK1')
                    info_row.label(text="0")
        elif self.layout_type == 'GRID':
            layout.prop(item, "selected", text="")
            layout.label(text=item.name)


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


class ACTION_OT_select_all_actions(bpy.types.Operator):
    """Select all actions in the list"""
    bl_idname = "action.select_all_actions"
    bl_label = "Select All"
    bl_description = "Select all actions for export"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    # Store reference to the operator
    operator_ref = None
    
    def execute(self, context):
        if self.operator_ref and hasattr(self.operator_ref, 'selected_actions'):
            for item in self.operator_ref.selected_actions:
                item.selected = True
        return {'FINISHED'}


class ACTION_OT_deselect_all_actions(bpy.types.Operator):
    """Deselect all actions in the list"""
    bl_idname = "action.deselect_all_actions"
    bl_label = "Deselect All"
    bl_description = "Deselect all actions for export"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    # Store reference to the operator
    operator_ref = None
    
    def execute(self, context):
        if self.operator_ref and hasattr(self.operator_ref, 'selected_actions'):
            for item in self.operator_ref.selected_actions:
                item.selected = False
        return {'FINISHED'}


class ACTION_OT_select_compatible_actions(bpy.types.Operator):
    """Select only compatible actions in the list"""
    bl_idname = "action.select_compatible_actions"
    bl_label = "Select Compatible"
    bl_description = "Select only actions that are compatible with the exported objects"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    # Store reference to the operator
    operator_ref = None
    
    def execute(self, context):
        if self.operator_ref and hasattr(self.operator_ref, 'selected_actions'):
            for item in self.operator_ref.selected_actions:
                action = bpy.data.actions.get(item.action)
                if action:
                    is_compatible, _ = is_action_compatible_with_export(context, self.operator_ref, action)
                    item.selected = is_compatible
        return {'FINISHED'}


class ANIMATION_GROUP_UL_selection_list(UIList):
    """UIList for displaying animation group selection with checkboxes"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Main row
            row = layout.row(align=True)
            
            # Checkbox
            checkbox_row = row.row()
            checkbox_row.alignment = 'LEFT'
            checkbox_row.prop(item, "selected", text="")
            
            # Add some spacing between checkbox and name
            row.separator_spacer()
            
            # Animation Group name
            name_row = row.row()
            name_row.label(text=item.name, icon='SEQ_STRIP_META')
            
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.prop(item, "selected", text="")


class ANIMATION_GROUP_OT_select_all_groups(bpy.types.Operator):
    """Select all animation groups"""
    bl_idname = "animation_group.select_all_groups"
    bl_label = "Select All Animation Groups"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    # Class variable to store operator reference
    operator_ref = None
    
    def execute(self, context):
        if self.operator_ref is None:
            return {'CANCELLED'}
        
        operator = self.operator_ref
        
        for item in operator.selected_animation_groups:
            item.selected = True
        
        return {'FINISHED'}


class ANIMATION_GROUP_OT_deselect_all_groups(bpy.types.Operator):
    """Deselect all animation groups"""
    bl_idname = "animation_group.deselect_all_groups"
    bl_label = "Deselect All Animation Groups"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    # Class variable to store operator reference
    operator_ref = None
    
    def execute(self, context):
        if self.operator_ref is None:
            return {'CANCELLED'}
        
        operator = self.operator_ref
        
        for item in operator.selected_animation_groups:
            item.selected = False
        
        return {'FINISHED'}


class ANIMATION_GROUP_OT_select_compatible_groups(bpy.types.Operator):
    """Select only compatible animation groups"""
    bl_idname = "animation_group.select_compatible_groups"
    bl_label = "Select Compatible Animation Groups"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    # Class variable to store operator reference
    operator_ref = None
    
    def execute(self, context):
        if self.operator_ref is None:
            return {'CANCELLED'}
        
        operator = self.operator_ref
        
        for item in operator.selected_animation_groups:
            is_compatible = is_animation_group_compatible_with_export(context, operator, item.group_name)
            item.selected = is_compatible
        
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


def get_fcurves_for_slot(action, slot_index):
    """Get all f-curves for a specific slot in an action"""
    if not (hasattr(action, 'slots') and action.slots and slot_index < len(action.slots)):
        return []
    
    slot = action.slots[slot_index]
    fcurves = []
    
    try:
        # Get the channelbag for this slot
        if hasattr(action, 'layers') and action.layers:
            layer = action.layers[0]  # Blender 4.4 only supports single layer
            if hasattr(layer, 'strips') and layer.strips:
                strip = layer.strips[0]  # Single strip
                if hasattr(strip, 'channelbag'):
                    channelbag = strip.channelbag(slot)
                    if channelbag and hasattr(channelbag, 'fcurves'):
                        fcurves = list(channelbag.fcurves)
    except Exception as e:
        print(f"Error getting f-curves for slot {slot_index}: {e}")
    
    return fcurves


def validate_fcurves_for_object(fcurves, obj, slot_type):
    """Validate if f-curves are compatible with an object"""
    if not fcurves:
        return True  # Empty f-curves are technically valid
    
    # Determine target object based on slot type
    if slot_type == 'KEY':
        if not (obj.type == 'MESH' and obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys):
            return False  # Object has no shape keys
        target_obj = obj.data.shape_keys
    else:
        target_obj = obj
    
    # Check each f-curve
    for fcurve in fcurves:
        try:
            target_obj.path_resolve(fcurve.data_path)
        except Exception:
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
        # First check against the object's default path_resolve (for actions without slots)
        try:
            path_resolve = obj.path_resolve
            if validate_actions(action, path_resolve):
                compatible_objects.append(obj.name)
                continue  # If compatible with default, no need to check slots
        except Exception:
            pass  # Continue to check slots
        
        # Check against action slots
        if hasattr(action, 'slots') and action.slots:
            for slot_index, slot in enumerate(action.slots):
                try:
                    # Get the slot type
                    slot_type = getattr(slot, 'target_id_type', 'OBJECT')
                    
                    # Get f-curves for this specific slot
                    slot_fcurves = get_fcurves_for_slot(action, slot_index)
                    
                    # Validate f-curves against the object
                    if validate_fcurves_for_object(slot_fcurves, obj, slot_type):
                        compatible_objects.append(obj.name)
                        break  # Found compatibility with this slot
                except Exception:
                    continue  # Try next slot
    
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
    """Draw the action selection UI in the export panel using template_list"""
    # Always populate selected_actions collection
    populate_action_list(operator)
    
    # Get available actions
    available_actions = list(bpy.data.actions)
    
    # Action selection UI
    box = layout.box()
    box.enabled = enabled
    
    if available_actions:
        # Set the operator reference for selection operators
        ACTION_OT_select_all_actions.operator_ref = operator
        ACTION_OT_deselect_all_actions.operator_ref = operator
        ACTION_OT_select_compatible_actions.operator_ref = operator
        
        # Template list for actions
        box.template_list(
            "ACTION_UL_selection_list", "",  # UIList identifier
            operator, "selected_actions",     # Data collection
            operator, "selected_actions_index",  # Active index property
            rows=6, maxrows=12               # Display settings
        )
        
        # Selection buttons
        row = box.row(align=True)
        select_all_op = row.operator("action.select_all_actions", text="All", icon='CHECKBOX_HLT')
        deselect_all_op = row.operator("action.deselect_all_actions", text="None", icon='CHECKBOX_DEHLT')
        
        # Add compatible selection button if actions export is enabled
        if hasattr(operator, 'bake_anim_export_actions') and operator.bake_anim_export_actions:
            compatible_op = row.operator("action.select_compatible_actions", text="Compatible", icon='CHECKMARK')
    else:
        box.label(text="No actions available", icon='INFO')


def get_selected_action_names(operator):
    """Get a set of selected action names from the operator"""
    return {item.action for item in operator.selected_actions if item.selected}


def is_animation_group_compatible_with_export(context, operator, group_name):
    """Check if an Animation Group is compatible with export objects"""
    if not is_action_binder_enabled():
        return False
    
    groups_data = get_animation_groups_data()
    if not groups_data:
        return False
    
    # Find the group by name
    target_group = None
    for group in groups_data.groups:
        if group.name == group_name:
            target_group = group
            break
    
    if not target_group or not target_group.action:
        return False
    
    # Get objects that would be exported
    ctx_objects = get_context_objects_for_export(context, operator)
    if not ctx_objects:
        return False
    
    # Get assigned objects from the group
    assigned_objects = []
    for assignment in target_group.slot_assignments:
        if assignment.assigned_object:
            assigned_objects.append(assignment.assigned_object)
    
    if not assigned_objects:
        return False
    
    # Check if any assigned object is in the export selection
    ctx_object_names = {obj.name for obj in ctx_objects}
    assigned_object_names = {obj.name for obj in assigned_objects}
    
    return bool(ctx_object_names.intersection(assigned_object_names))


def populate_animation_group_list(operator):
    """Populate the selected_animation_groups collection with available animation groups"""
    if not is_action_binder_enabled():
        operator.selected_animation_groups.clear()
        return
    
    groups_data = get_animation_groups_data()
    if not groups_data:
        operator.selected_animation_groups.clear()
        return
    
    available_groups = list(groups_data.groups)
    
    # Update selected_animation_groups collection if needed
    if len(operator.selected_animation_groups) != len(available_groups):
        operator.selected_animation_groups.clear()
        context = bpy.context
        
        for group in available_groups:
            if not group.action:  # Skip groups without actions
                continue
                
            item = operator.selected_animation_groups.add()
            item.name = group.name
            item.group_name = group.name
            
            # Check compatibility to set default selection
            if hasattr(operator, 'bake_anim_export_animation_groups') and operator.bake_anim_export_animation_groups:
                is_compatible = is_animation_group_compatible_with_export(context, operator, group.name)
                item.selected = is_compatible  # Only select compatible groups by default
            else:
                item.selected = True  # If export animation groups is disabled, select all by default


def draw_animation_group_selection_ui(layout, operator, enabled=True):
    """Draw the animation group selection UI in the export panel using template_list"""
    # Always populate selected_animation_groups collection
    populate_animation_group_list(operator)
    
    # Get available groups
    groups_data = get_animation_groups_data()
    available_groups = list(groups_data.groups) if groups_data else []
    is_addon_enabled = is_action_binder_enabled()
    
    # Animation Group selection UI
    box = layout.box()
    box.enabled = enabled
    
    if available_groups:
        # Set the operator reference for selection operators
        ANIMATION_GROUP_OT_select_all_groups.operator_ref = operator
        ANIMATION_GROUP_OT_deselect_all_groups.operator_ref = operator
        ANIMATION_GROUP_OT_select_compatible_groups.operator_ref = operator
        
        # Template list for animation groups
        box.template_list(
            "ANIMATION_GROUP_UL_selection_list", "",  # UIList identifier
            operator, "selected_animation_groups",     # Data collection
            operator, "selected_animation_groups_index",  # Active index property
            rows=6, maxrows=12               # Display settings
        )
        
        # Selection buttons
        row = box.row(align=True)
        select_all_op = row.operator("animation_group.select_all_groups", text="All", icon='CHECKBOX_HLT')
        deselect_all_op = row.operator("animation_group.deselect_all_groups", text="None", icon='CHECKBOX_DEHLT')
        
        # Add compatible selection button if animation groups export is enabled
        if hasattr(operator, 'bake_anim_export_animation_groups') and operator.bake_anim_export_animation_groups:
            compatible_op = row.operator("animation_group.select_compatible_groups", text="Compatible", icon='CHECKMARK')
    else:
        if is_addon_enabled:
            box.label(text="No Animation Groups available", icon='INFO')
        else:
            box.label(text="Action Binder addon not enabled", icon='ERROR')


def get_selected_animation_group_names(operator):
    """Get a set of selected animation group names from the operator"""
    return {item.group_name for item in operator.selected_animation_groups if item.selected}


def register():
    """Register the PropertyGroup classes"""
    bpy.utils.register_class(ActionSelectionItem)
    bpy.utils.register_class(AnimationGroupSelectionItem)
    bpy.utils.register_class(ACTION_UL_selection_list)
    bpy.utils.register_class(ANIMATION_GROUP_UL_selection_list)
    bpy.utils.register_class(ACTION_OT_show_compatibility_warning)
    bpy.utils.register_class(ACTION_OT_show_compatibility_info)
    bpy.utils.register_class(ACTION_OT_select_all_actions)
    bpy.utils.register_class(ACTION_OT_deselect_all_actions)
    bpy.utils.register_class(ACTION_OT_select_compatible_actions)
    bpy.utils.register_class(ANIMATION_GROUP_OT_select_all_groups)
    bpy.utils.register_class(ANIMATION_GROUP_OT_deselect_all_groups)
    bpy.utils.register_class(ANIMATION_GROUP_OT_select_compatible_groups)


def unregister():
    """Unregister the PropertyGroup classes"""
    bpy.utils.unregister_class(ANIMATION_GROUP_OT_select_compatible_groups)
    bpy.utils.unregister_class(ANIMATION_GROUP_OT_deselect_all_groups)
    bpy.utils.unregister_class(ANIMATION_GROUP_OT_select_all_groups)
    bpy.utils.unregister_class(ACTION_OT_select_compatible_actions)
    bpy.utils.unregister_class(ACTION_OT_deselect_all_actions)
    bpy.utils.unregister_class(ACTION_OT_select_all_actions)
    bpy.utils.unregister_class(ACTION_OT_show_compatibility_info)
    bpy.utils.unregister_class(ACTION_OT_show_compatibility_warning)
    bpy.utils.unregister_class(ANIMATION_GROUP_UL_selection_list)
    bpy.utils.unregister_class(ACTION_UL_selection_list)
    bpy.utils.unregister_class(AnimationGroupSelectionItem)
    bpy.utils.unregister_class(ActionSelectionItem) 