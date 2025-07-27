
This is a fork of the io_scene_fbx addon for blender, version 5.13.0 (released with Blender 4.5), which includes extra features, oriented to the integration with game engines like Unity.

# Additional Features
## Transform
### Bake Transform
Apply -90º transformations on the X axis, then leave the objects in X 90 rotation. This allows to cancel unwanted rotations in game engines like Unity.
Once the export is finished, it reverts the changes to the objects.
Only available with -Z forward and Y Up.
Warning: it is recommended not to save the .blend file after exporting using this option. Use it at your own risk.

## Animation

### Animation > Add Rest Pose
Export the rest pose as the first animation with the name “Bind Pose”.

### Animation > Action Name
Allows the user to decide the format in which the action names will be exported:
- Action (default): The name of the action.
- Object|Action: Default mode that includes the concatenation of the object name linked to the action.

### Animation > Action List
Displays a list of all the Actions available in the blend file and allows you to select which ones will be exported as AnimStack.
Each Action does a pre-check of which objects included in the export are compatible with the f-curves.

### Animation > Animation Groups
If you have the Action Binder plugin installed, it allows you to export Animation Groups as individual FBXAnimStacks.
You can get [Action Binder here](https://github.com/olavra/blender-actions-binder).
