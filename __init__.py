bl_info = {
    "name" : "ImageSq2Vid",
    "author" : "3D_Bubble",
    "description" : "Convert rendered sequence of images to a video",
    "blender" : (3, 3, 0),
    "version" : (0, 0, 0),
    "location" : "View3D",
    "warning" : "",
    "category" : "Generic"
}

import os
import bpy
from mathutils import Vector
from bpy.props import *
from bpy.types import (Panel,Menu,Operator,PropertyGroup)

class ImgSq2VidProperties(PropertyGroup):
    output_container : EnumProperty(
        name = "Output Container",
        description = "Container type of output video",
        items=[
            ('MPEG4', "MPEG-4", ""),
            ('MKV', "Matroska", ""),
            ('AVI', "AVI", ""),
            ('FLASH', "Flash", ""),
            ('WEBM', "WebM", ""),
        ],
        default = "MPEG4"
    )
    output_quality : EnumProperty(
        name = "Output Quality",
        description = "Constant Rate Factor(CRF); Tradeoff between video quailty and file size",
        items=[
            ("NONE", "Constant Bitrate", ""),
            ("LOSSLESS", "Lossless", ""),
            ("PERC_LOSSLESS", "Perceptually Lossless", ""),
            ("HIGH", "High Quality", ""),
            ("MEDIUM", "Medium Quality", ""),
            ("LOW", "Low Quality", ""),
            ("VERYLOW", "Very Low Quality", ""),
            ("LOWEST", "Lowest Quality", ""),
        ],
        default = "PERC_LOSSLESS"
    )
    encoding_speed : EnumProperty(
        name = "Encoding Speed",
        description = "Tradeoff between encoding speed and compression ratio",
        items=[
            ("BEST", "Best", ""),
            ("Good", "Good", ""),
            ("REALTIME", "Realtime", ""),
        ],
        default = "BEST"
    )
    img_seq_path : StringProperty(
        name = "Image Sequence Path",
        description = "Path where all images in sequence are located",
        default = "//",
        subtype = "DIR_PATH"
    )

class ImgSq2Vid_OT_convert_to_seq(bpy.types.Operator):
    bl_idname = "object.convert_to_seq"
    bl_label = "Convert to Video"
    bl_description = "Converts rendered sequence of images to a video"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        vid_tool = context.scene.vid_tool
        ret = convert_to_seq(vid_tool.img_seq_path,
                            vid_tool.output_container,
                            vid_tool.output_quality,
                            vid_tool.encoding_speed)
        if ret == 0:
            self.report({'INFO'}, 'Done')
        elif ret == 1:
            self.report({'OPERATOR'},'No files found at the location')
        elif ret == 2:
            self.report({'OPERATOR'}, 'Location not found')
        return {'FINISHED'}


class OBJECT_PT_ImgSq2VidFuncs(Panel):
    bl_idname = "OBJECT_PT_ImgSq2VidFuncs"
    bl_label = "Image sequence to Video"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ImgSq2Vid"
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        vid_tool = scene.vid_tool
        
        row = layout.row()
        row.label(text="Image Sequence Path")
        row.prop(vid_tool, "img_seq_path", text="")
        layout.row(align=True)

        row = layout.row()
        row.label(text="Output Conatiner")
        row.prop(vid_tool, "output_container", text="")
        
        row = layout.row()
        row.label(text="Output Quality")
        row.prop(vid_tool, "output_quality", text="")
        
        row = layout.row()
        row.label(text="Encoding Speed")
        row.prop(vid_tool, "encoding_speed", text="")

        layout.operator("object.convert_to_seq")
        layout.row(align=True)
        
        

classes = (
    ImgSq2VidProperties,
    OBJECT_PT_ImgSq2VidFuncs,
    ImgSq2Vid_OT_convert_to_seq
)

def convert_to_seq(path, output_container, output_quality, encoding_speed):
    current_scene = bpy.context.window.scene
    new_scene_name = 'img2vid'
    if new_scene_name in bpy.data.scenes:
        i = 1
        while new_scene_name not in bpy.data.scenes:
            i+=1
            new_scene_name = 'img2vid'+str(i)

    bpy.data.scenes.new(name=new_scene_name)
    new_scene = bpy.data.scenes[new_scene_name]

    bpy.context.window.scene = new_scene
    new_scene.render.engine = 'BLENDER_EEVEE'
    new_scene.eevee.taa_render_samples = 1

    old_area_type = bpy.context.area.type
    bpy.context.area.type = 'SEQUENCE_EDITOR'

    files=[]
    path = bpy.path.abspath(path)
    if not os.path.isdir(path):
        revert_to_original_state(old_area_type, current_scene, new_scene)
        return 2
            
    for i in os.listdir(path):
        fileName, fileExtension = os.path.splitext(i)
        if fileExtension.lower() in ['.jpg' , '.png', '.jpeg', '.exr', '.tiff']:
            files.append(i)
    
    if len(files)==0:
        revert_to_original_state(old_area_type, current_scene, new_scene)
        return 1
    
    extension = files[0].split('.')[1]
    temp = files[0].split('.')[0].split('_')
    before_num = '_'.join(temp[:len(temp)-1])
    before_num = before_num if before_num=='' else before_num+'_'
    nums = [file.split('.')[0].split('_')[-1] for file in files]
    nums = [int(num) for num in nums]
    nums.sort()
    nums = [str(num).rjust(4,'0') for num in nums]
    files = [before_num+num+'.'+extension for num in nums]
    dfiles = [{'name':file} for file in files]


    bpy.ops.sequencer.image_strip_add(directory = path, files=dfiles, channel=1, frame_start=1, frame_end=len(dfiles))

    width = new_scene.sequence_editor.sequences_all[0].elements[0].orig_width
    height = new_scene.sequence_editor.sequences_all[0].elements[0].orig_height

    new_scene.frame_start = 1
    new_scene.frame_end = len(dfiles)
    new_scene.render.resolution_x = width
    new_scene.render.resolution_y = height

    new_scene.sequence_editor.sequences_all[0].transform.scale_x = 1
    new_scene.sequence_editor.sequences_all[0].transform.scale_y = 1

    new_scene.render.filepath = os.path.join(path, before_num)
    new_scene.render.image_settings.file_format = 'FFMPEG'
    new_scene.render.ffmpeg.format = output_container
    new_scene.render.ffmpeg.constant_rate_factor = output_quality
    new_scene.render.ffmpeg.ffmpeg_preset = encoding_speed

    bpy.ops.render.render(animation=True, scene=new_scene_name)

    revert_to_original_state(old_area_type, current_scene, new_scene)
    
    return 0

def revert_to_original_state(old_area_type, current_scene, new_scene):
    bpy.context.area.type = old_area_type
    bpy.context.window.scene = current_scene
    bpy.data.scenes.remove(new_scene, do_unlink=True)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.vid_tool = PointerProperty(type=ImgSq2VidProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.vid_tool

if __name__ == "__main__":
    register()
