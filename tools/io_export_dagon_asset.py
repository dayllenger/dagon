bl_info = {
    "name": "Dagon Asset Export",
    "author": "Timur Gafarov",
    "version": (1, 0),
    "blender": (2, 6, 4),
    "location": "File > Export > Dagon Asset (.asset)",
    "description": "Export Dagon engine asset file",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"}

import os
import shutil
import struct
from pathlib import Path
from math import pi
import bpy
import bpy_extras
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper
import mathutils

def packVector4f(v):
    return struct.pack('<ffff', v[0], v[1], v[2], v[3])

def packVector3f(v):
    return struct.pack('<fff', v[0], v[1], v[2])

def packVector2f(v):
    return struct.pack('<ff', v[0], v[1])

def saveMesh(scene, ob, absPath, localPath):
    parentTrans = ob.matrix_world * ob.matrix_local.inverted()
    locTrans = ob.matrix_local.copy()
    absTrans = parentTrans.inverted()

    ob.location = absTrans.to_translation()
    ob.rotation_euler = absTrans.to_euler()
    ob.rotation_quaternion = absTrans.to_quaternion()
    ob.scale = absTrans.to_scale()

    scene.update()

    meshAbsPath = absPath + "/" + ob.name + ".obj"

    bpy.ops.object.select_pattern(pattern = ob.name)
    bpy.ops.export_scene.obj(
      filepath = meshAbsPath, 
      use_selection = True, 
      use_materials = False,
      use_triangles = True,
      use_uvs = True,
      use_mesh_modifiers = True)
      
    bpy.ops.object.select_all(action='DESELECT')

    ob.location = locTrans.to_translation()
    ob.rotation_euler = locTrans.to_euler()
    ob.rotation_quaternion = locTrans.to_quaternion()
    ob.scale = locTrans.to_scale()

    scene.update()

def saveEntity(scene, ob, absPath, localPath):
    entityAbsPath = absPath + "/" + ob.name + ".entity"

    global_matrix = bpy_extras.io_utils.axis_conversion(to_forward="-Z", to_up="Y").to_4x4()
    absTrans = global_matrix * ob.matrix_world * global_matrix.transposed()

    objPosition = absTrans.to_translation()
    objRotation = absTrans.to_quaternion()
    objScale = absTrans.to_scale()

    f = open(entityAbsPath, 'wb')
    name = 'name: \"%s\";\n' % (ob.name)
    f.write(bytearray(name.encode('ascii')))
    pos = 'position: [%s, %s, %s];\n' % (objPosition.x, objPosition.y, objPosition.z)
    f.write(bytearray(pos.encode('ascii')))
    rot = 'rotation: [%s, %s, %s, %s];\n' % (objRotation.x, objRotation.y, objRotation.z, objRotation.w)
    f.write(bytearray(rot.encode('ascii')))
    scale = 'scale: [%s, %s, %s];\n' % (objScale.x, objScale.y, objScale.z)
    f.write(bytearray(scale.encode('ascii')))
    meshLocalPath = localPath + ob.name + ".obj"
    mesh = 'mesh: \"%s\";\n' % (meshLocalPath)
    f.write(bytearray(mesh.encode('ascii')))
    if len(ob.data.materials) > 0:
        mat = ob.data.materials[0]
        materialName = mat.name
        materialLocalPath = localPath + mat.name + ".mat"
        materialStr = 'material: \"%s\";\n' % (materialLocalPath)
        f.write(bytearray(materialStr.encode('ascii')))
    f.close()

def copyFile(fileSrc, destDir):
    destFile = destDir + "/" + os.path.basename(fileSrc)
    if not os.path.exists(destFile):
        shutil.copy2(fileSrc, destDir + "/")

def saveMaterial(scene, mat, absPath, localPath):
    matAbsPath = absPath + "/" + mat.name + ".mat"
    f = open(matAbsPath, 'wb')
    name = 'name: \"%s\";\n' % (mat.name)
    f.write(bytearray(name.encode('ascii')))
    
    props = mat.dagonProps
    if len(props.dagonDiffuseTexture):
        imageName = props.dagonDiffuseTexture
        imgAbsPath = bpy.path.abspath(props.dagonDiffuseTexture)
        if props.dagonDiffuseTexture in bpy.data.images:
            imgAbsPath = bpy.path.abspath(bpy.data.images[props.dagonDiffuseTexture].filepath)
        
        imageName = os.path.basename(imgAbsPath)
        imgPath = localPath + imageName
        diffuse = 'diffuse: \"%s\";\n' % (imgPath)
        copyFile(imgAbsPath, absPath)
    else:
        diffuse = 'diffuse: [%s, %s, %s];\n' % (props.dagonDiffuse.r, props.dagonDiffuse.g, props.dagonDiffuse.b)
    f.write(bytearray(diffuse.encode('ascii')))
    roughness = 'roughness: %s;\n' % (props.dagonRoughness)
    f.write(bytearray(roughness.encode('ascii')))
    metallic = 'metallic: %s;\n' % (props.dagonMetallic)
    f.write(bytearray(metallic.encode('ascii')))
    
    f.close()
    
def saveIndexFile(entities, absPath, dirLocal):
    indexAbsPath = absPath + "/INDEX"
    f = open(indexAbsPath, 'wb')
    for e in entities:
        estr = '%s\n' % (e)
        f.write(bytearray(estr.encode('ascii')))
    f.close()

def doExport(context, filepath = ""):

    scene = context.scene

    dirName = Path(filepath).stem
    dirParent = os.path.dirname(filepath)
    dirAbs = dirParent + "/" + dirName + "_root"

    if os.path.exists(dirAbs):
        shutil.rmtree(dirAbs)
    os.makedirs(dirAbs)

    dirLocal = dirName + "/"

    entities = []

    localFilenames = []
    absFilenames = []

    # Save *.obj and *.entity files
    for ob in scene.objects:
        if ob.type == 'MESH':
            saveMesh(scene, ob, dirAbs, dirLocal)
            meshLocalPath = dirLocal + ob.name + ".obj"
            localFilenames.append(meshLocalPath)
            meshAbsPath = dirAbs + "/" + ob.name + ".obj"
            absFilenames.append(meshAbsPath)

            saveEntity(scene, ob, dirAbs, dirLocal)
            entityFileLocalPath = dirLocal + ob.name + ".entity"
            localFilenames.append(entityFileLocalPath)
            entityFileAbsPath = dirAbs + "/" + ob.name + ".entity"
            absFilenames.append(entityFileAbsPath)
            
            entities.append(entityFileLocalPath)
        #TODO: other object types (empties, lamps)

    for mat in bpy.data.materials:
        saveMaterial(scene, mat, dirAbs, dirLocal)
        matLocalPath = dirLocal + mat.name + ".mat"
        localFilenames.append(matLocalPath)
        matAbsPath = dirAbs + "/" + mat.name + ".mat"
        absFilenames.append(matAbsPath)

    for filename in os.listdir(dirAbs + "/"):
        if filename.endswith(".png") or filename.endswith(".jpg") or filename.endswith(".bmp") or filename.endswith(".tga") or filename.endswith(".hdr"):
             texLocalPath = dirLocal + os.path.basename(filename)
             localFilenames.append(texLocalPath)
             texAbsPath = dirAbs + "/" + os.path.basename(filename)
             absFilenames.append(texAbsPath)
        
    saveIndexFile(entities, dirAbs, dirLocal)
    indexLocalPath = "INDEX"
    localFilenames.append(indexLocalPath)
    indexAbsPath = dirAbs + "/INDEX"
    absFilenames.append(indexAbsPath)

    fileDataOffset = 12; #initial offset
    for i, filename in enumerate(localFilenames):
        fileDataOffset = fileDataOffset + 4; # filename size
        fileDataOffset = fileDataOffset + len(filename.encode('ascii'))
        fileDataOffset = fileDataOffset + 8 # data offset
        fileDataOffset = fileDataOffset + 8 # data size

    # Save *.asset file (Box archive)

    # Write header
    f = open(filepath, 'wb')
    f.write(bytearray('BOXF'.encode('ascii')))
    f.write(struct.pack('<Q', len(localFilenames)))

    # Write index
    for i, filename in enumerate(localFilenames):
        filenameData = bytearray(filename.encode('ascii'))
        filePathSize = len(filenameData)
        fileDataSize = os.path.getsize(absFilenames[i])
        f.write(struct.pack('<I', filePathSize))
        f.write(filenameData)
        f.write(struct.pack('<Q', fileDataOffset))
        f.write(struct.pack('<Q', fileDataSize))
        fileDataOffset = fileDataOffset + fileDataSize

    # Write data
    for i, filename in enumerate(absFilenames):
        f2 = open(filename, 'rb')
        fileData = bytearray(f2.read())
        f.write(fileData)
        f2.close()

    f.close()

    return {'FINISHED'}

class ExportDagonAsset(bpy.types.Operator, ExportHelper):
    bl_idname = "scene.asset"
    bl_label = "Export Dagon Asset"
    filename_ext = ".asset"

    filter_glob = StringProperty(default = "unknown.asset", options = {"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)           
        return doExport(context, filepath)

    def invoke(self, context, event):
        wm = context.window_manager
        if True:
            wm.fileselect_add(self)
            return {"RUNNING_MODAL"}
        elif True:
            wm.invoke_search_popup(self)
            return {"RUNNING_MODAL"}
        elif False:
            return wm.invoke_props_popup(self, event)
        elif False:
            return self.execute(context)

def menu_func_export_dagon_asset(self, context):
    self.layout.operator(ExportDagonAsset.bl_idname, text = "Dagon Asset (.asset)")

ParallaxModeEnum = [
    ('ParallaxNone', "None", "", 0),
    ('ParallaxSimple', "Simple", "", 1),
    ('ParallaxOcclusionMapping', "Occlusion Mapping", "", 2),
]

class DagonMaterialProps(bpy.types.PropertyGroup):
    dagonDiffuse = bpy.props.FloatVectorProperty(name="Diffuse", default=(0.8, 0.8, 0.8), min=0.0, max=1.0, subtype='COLOR')
    dagonRoughness = bpy.props.FloatProperty(name="Roughness", default=0.5, min=0.0, max=1.0, subtype='FACTOR')
    dagonMetallic = bpy.props.FloatProperty(name="Metallic", default=0.0, min=0.0, max=1.0, subtype='FACTOR')
    dagonEmission = bpy.props.FloatVectorProperty(name="Emission", default=(0.0, 0.0, 0.0), min=0.0, max=1.0, subtype='COLOR')
    dagonEnergy = bpy.props.FloatProperty(name="Energy", default=0.0, min=0.0)
    dagonDiffuseTexture = bpy.props.StringProperty(name="Diffuse Texture", subtype='FILE_PATH')
    dagonRoughnessTexture = bpy.props.StringProperty(name="Roughness Texture", subtype='FILE_PATH')
    dagonMetallicTexture = bpy.props.StringProperty(name="Metallic Texture", subtype='FILE_PATH')
    dagonNormalTexture = bpy.props.StringProperty(name="Normal Texture", subtype='FILE_PATH')
    dagonHeightTexture = bpy.props.StringProperty(name="Height Texture", subtype='FILE_PATH')
    dagonEmissionTexture = bpy.props.StringProperty(name="Emission Texture", subtype='FILE_PATH')
    dagonParallaxMode = bpy.props.EnumProperty(name="Parallax Mode", items=ParallaxModeEnum)

class DagonMaterialPropsPanel(bpy.types.Panel):
    bl_label = "Dagon Properties"
    bl_idname = "dagon_material_props"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    def draw(self, context):
        obj = context.object
        mat = obj.active_material
        col = self.layout.column(align=True)
        props = mat.dagonProps
        col.prop(props, 'dagonDiffuse')

        col = self.layout.column(align=True)
        col.prop(props, 'dagonRoughness')
        col.prop(props, 'dagonMetallic')

        col = self.layout.column(align=True)
        col.prop(props, 'dagonEmission')
        col.prop(props, 'dagonEnergy')

        col = self.layout.column(align=True)
        col.prop_search(props, "dagonDiffuseTexture", bpy.data, "images")

        col = self.layout.column(align=True)
        col.prop_search(props, "dagonRoughnessTexture", bpy.data, "images")

        col = self.layout.column(align=True)
        col.prop_search(props, "dagonMetallicTexture", bpy.data, "images")

        col = self.layout.column(align=True)
        col.prop_search(props, "dagonNormalTexture", bpy.data, "images")

        col = self.layout.column(align=True)
        col.prop_search(props, "dagonHeightTexture", bpy.data, "images")

        col = self.layout.column(align=True)
        col.prop_search(props, "dagonEmissionTexture", bpy.data, "images")

        col = self.layout.column(align=True)
        col.prop(props, 'dagonParallaxMode')

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func_export_dagon_asset)
    bpy.types.Material.dagonProps = bpy.props.PointerProperty(type=DagonMaterialProps)

def unregister():
    del bpy.types.Material.dagonProps
    bpy.types.INFO_MT_file_export.remove(menu_func_export_dagon_asset)
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()

