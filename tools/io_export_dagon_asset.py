bl_info = {
    "name": "Dagon Asset Export",
    "author": "Timur Gafarov",
    "version": (1, 0),
    "blender": (2, 7, 0),
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
    mw = ob.matrix_world.copy()    
    ob.matrix_world.identity()
    scene.update()

    meshAbsPath = absPath + "/" + ob.data.name + ".obj"
    
    bpy.ops.object.select_all(action='DESELECT')

    bpy.ops.object.select_pattern(pattern = ob.name)
    
    bpy.ops.export_scene.obj(
      filepath = meshAbsPath, 
      use_selection = True, 
      use_materials = False,
      use_triangles = True,
      use_uvs = True,
      use_mesh_modifiers = True)
      
    bpy.ops.object.select_all(action='DESELECT')
    
    for sob in bpy.context.selected_objects:
        sob.select = False

    ob.matrix_world = mw.copy();
    scene.update()

def saveMeshEntity(scene, ob, absPath, localPath):
    entityAbsPath = absPath + "/" + ob.name + ".entity"

    global_matrix = bpy_extras.io_utils.axis_conversion(to_forward="-Z", to_up="Y").to_4x4()
    absTrans = global_matrix * ob.matrix_local * global_matrix.transposed()

    objPosition = absTrans.to_translation()
    objRotation = absTrans.to_quaternion()
    objScale = absTrans.to_scale()

    f = open(entityAbsPath, 'wb')
    name = 'name: \"%s\";\n' % (ob.name)
    f.write(bytearray(name.encode('ascii')))
    
    props = ob.dagonProps
    
    if ob.parent:
        parentFilename = localPath + ob.parent.name + ".entity"
        parentStr = 'parent: \"%s\";\n' % (parentFilename)
        f.write(bytearray(parentStr.encode('ascii')))
    
    pos = 'position: [%s, %s, %s];\n' % (objPosition.x, objPosition.y, objPosition.z)
    f.write(bytearray(pos.encode('ascii')))
    rot = 'rotation: [%s, %s, %s, %s];\n' % (objRotation.x, objRotation.y, objRotation.z, objRotation.w)
    f.write(bytearray(rot.encode('ascii')))
    scale = 'scale: [%s, %s, %s];\n' % (objScale.x, objScale.y, objScale.z)
    f.write(bytearray(scale.encode('ascii')))
    meshLocalPath = localPath + ob.data.name + ".obj"
    mesh = 'mesh: \"%s\";\n' % (meshLocalPath)
    f.write(bytearray(mesh.encode('ascii')))
    if len(ob.data.materials) > 0:
        mat = ob.data.materials[0]
        materialName = mat.name
        materialLocalPath = localPath + mat.name + ".mat"
        materialStr = 'material: \"%s\";\n' % (materialLocalPath)
        f.write(bytearray(materialStr.encode('ascii')))
        
    visible = 'visible: %s;\n' % (int(props.dagonVisible))
    f.write(bytearray(visible.encode('ascii')))
    
    castShadow = 'castShadow: %s;\n' % (int(props.dagonCastShadow))
    f.write(bytearray(castShadow.encode('ascii')))
    
    useMotionBlur = 'useMotionBlur: %s;\n' % (int(props.dagonUseMotionBlur))
    f.write(bytearray(useMotionBlur.encode('ascii')))
    
    solid = 'solid: %s;\n' % (int(props.dagonSolid))
    f.write(bytearray(solid.encode('ascii')))
    
    layer = 'layer: %s;\n' % (props.dagonLayer)
    f.write(bytearray(layer.encode('ascii')))

    f.close()
    
def saveEmptyEntity(scene, ob, absPath, localPath):
    entityAbsPath = absPath + "/" + ob.name + ".entity"

    global_matrix = bpy_extras.io_utils.axis_conversion(to_forward="-Z", to_up="Y").to_4x4()
    absTrans = global_matrix * ob.matrix_world * global_matrix.transposed()

    objPosition = absTrans.to_translation()
    objRotation = absTrans.to_quaternion()
    objScale = absTrans.to_scale()

    f = open(entityAbsPath, 'wb')
    name = 'name: \"%s\";\n' % (ob.name)
    f.write(bytearray(name.encode('ascii')))
    
    props = ob.dagonProps
    
    if ob.parent:
        parentFilename = localPath + ob.parent.name + ".entity"
        parentStr = 'parent: \"%s\";\n' % (parentFilename)
        f.write(bytearray(parentStr.encode('ascii')))
    
    pos = 'position: [%s, %s, %s];\n' % (objPosition.x, objPosition.y, objPosition.z)
    f.write(bytearray(pos.encode('ascii')))
    rot = 'rotation: [%s, %s, %s, %s];\n' % (objRotation.x, objRotation.y, objRotation.z, objRotation.w)
    f.write(bytearray(rot.encode('ascii')))
    scale = 'scale: [%s, %s, %s];\n' % (objScale.x, objScale.y, objScale.z)
    f.write(bytearray(scale.encode('ascii')))

    visible = 'visible: %s;\n' % (int(props.dagonVisible))
    f.write(bytearray(visible.encode('ascii')))
    
    castShadow = 'castShadow: %s;\n' % (int(props.dagonCastShadow))
    f.write(bytearray(castShadow.encode('ascii')))
    
    useMotionBlur = 'useMotionBlur: %s;\n' % (int(props.dagonUseMotionBlur))
    f.write(bytearray(useMotionBlur.encode('ascii')))
    
    solid = 'solid: %s;\n' % (int(props.dagonSolid))
    f.write(bytearray(solid.encode('ascii')))
    
    layer = 'layer: %s;\n' % (props.dagonLayer)
    f.write(bytearray(layer.encode('ascii')))

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

    # diffuse
    diffuse = ''
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

    # roughness
    roughness = ''
    if len(props.dagonRoughnessTexture):
        imageName = props.dagonRoughnessTexture
        imgAbsPath = bpy.path.abspath(props.dagonRoughnessTexture)
        if props.dagonRoughnessTexture in bpy.data.images:
            imgAbsPath = bpy.path.abspath(bpy.data.images[props.dagonRoughnessTexture].filepath)
        imageName = os.path.basename(imgAbsPath)
        imgPath = localPath + imageName
        roughness = 'roughness: \"%s\";\n' % (imgPath)
        copyFile(imgAbsPath, absPath)
    else:
        roughness = 'roughness: %s;\n' % (props.dagonRoughness)
    f.write(bytearray(roughness.encode('ascii')))

    # metallic
    metallic = ''
    if len(props.dagonMetallicTexture):
        imageName = props.dagonMetallicTexture
        imgAbsPath = bpy.path.abspath(props.dagonMetallicTexture)
        if props.dagonMetallicTexture in bpy.data.images:
            imgAbsPath = bpy.path.abspath(bpy.data.images[props.dagonMetallicTexture].filepath)
        imageName = os.path.basename(imgAbsPath)
        imgPath = localPath + imageName
        metallic = 'metallic: \"%s\";\n' % (imgPath)
        copyFile(imgAbsPath, absPath)
    else:
        metallic = 'metallic: %s;\n' % (props.dagonMetallic)
    f.write(bytearray(metallic.encode('ascii')))

    # emission
    emission = ''
    if len(props.dagonEmissionTexture):
        imageName = props.dagonEmissionTexture
        imgAbsPath = bpy.path.abspath(props.dagonEmissionTexture)
        if props.dagonEmissionTexture in bpy.data.images:
            imgAbsPath = bpy.path.abspath(bpy.data.images[props.dagonEmissionTexture].filepath)
        imageName = os.path.basename(imgAbsPath)
        imgPath = localPath + imageName
        emission = 'emission: \"%s\";\n' % (imgPath)
        copyFile(imgAbsPath, absPath)
    else:
        emission = 'emission: [%s, %s, %s];\n' % (props.dagonEmission.r, props.dagonEmission.g, props.dagonEmission.b)
    f.write(bytearray(emission.encode('ascii')))
    
    # energy
    energy = 'energy: %s;\n' % (props.dagonEnergy)
    f.write(bytearray(energy.encode('ascii')))
    
    # normal
    if len(props.dagonNormalTexture):
        imageName = props.dagonNormalTexture
        imgAbsPath = bpy.path.abspath(props.dagonNormalTexture)
        if props.dagonNormalTexture in bpy.data.images:
            imgAbsPath = bpy.path.abspath(bpy.data.images[props.dagonNormalTexture].filepath)
        imageName = os.path.basename(imgAbsPath)
        imgPath = localPath + imageName
        normal = 'normal: \"%s\";\n' % (imgPath)
        copyFile(imgAbsPath, absPath)
        f.write(bytearray(normal.encode('ascii')))
        
    # height
    if len(props.dagonHeightTexture):
        imageName = props.dagonHeightTexture
        imgAbsPath = bpy.path.abspath(props.dagonHeightTexture)
        if props.dagonHeightTexture in bpy.data.images:
            imgAbsPath = bpy.path.abspath(bpy.data.images[props.dagonHeightTexture].filepath)
        imageName = os.path.basename(imgAbsPath)
        imgPath = localPath + imageName
        height = 'height: \"%s\";\n' % (imgPath)
        copyFile(imgAbsPath, absPath)
        f.write(bytearray(height.encode('ascii')))
        
    # parallaxMode
    parallaxMode = {
        'ParallaxNone': 0,
        'ParallaxSimple': 1,
        'ParallaxOcclusionMapping': 2,
    }[props.dagonParallaxMode];
    parallax = 'parallax: %s;\n' % (parallaxMode)
    f.write(bytearray(parallax.encode('ascii')))
    
    # parallaxScale
    parallaxScale = 'parallaxScale: %s;\n' % (props.dagonParallaxScale)
    f.write(bytearray(parallaxScale.encode('ascii')))
    
    # parallaxBias
    parallaxBias = 'parallaxBias: %s;\n' % (props.dagonParallaxBias)
    f.write(bytearray(parallaxBias.encode('ascii')))
    
    # shadeless
    shadeless = 'shadeless: %s;\n' % (int(props.dagonShadeless))
    f.write(bytearray(shadeless.encode('ascii')))
    
    # culling
    culling = 'culling: %s;\n' % (int(props.dagonCulling))
    f.write(bytearray(culling.encode('ascii')))
    
    # colorWrite
    colorWrite = 'colorWrite: %s;\n' % (int(props.dagonColorWrite))
    f.write(bytearray(colorWrite.encode('ascii')))
    
    # depthWrite
    depthWrite = 'depthWrite: %s;\n' % (int(props.dagonDepthWrite))
    f.write(bytearray(depthWrite.encode('ascii')))
    
    # useShadows
    useShadows = 'useShadows: %s;\n' % (int(props.dagonReceiveShadows))
    f.write(bytearray(useShadows.encode('ascii')))
    
    # useFog
    useFog = 'useFog: %s;\n' % (int(props.dagonFog))
    f.write(bytearray(useFog.encode('ascii')))

    # shadowFilter
    shadowFilter = {
        'ShadowFilterNone': 0,
        'ShadowFilterPCF': 1
    }[props.dagonShadowFilter];
    shadowFilterStr = 'shadowFilter: %s;\n' % (shadowFilter)
    f.write(bytearray(shadowFilterStr.encode('ascii')))
    
    # blendingMode
    blendingMode = {
        'BlendingModeOpaque': 0,
        'BlendingModeTransparent': 1,
        'BlendingModeAdditive': 2
    }[props.dagonBlendingMode];
    blendingModeStr = 'blendingMode: %s;\n' % (blendingMode)
    f.write(bytearray(blendingModeStr.encode('ascii')))
    
    # transparency
    transparency = 'transparency: %s;\n' % (props.dagonTransparency)
    f.write(bytearray(transparency.encode('ascii')))
    
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

    dirLocal = '' #dirName + "/"

    entities = []
    meshes = []

    localFilenames = []
    absFilenames = []

    # Save *.obj and *.entity files
    for ob in scene.objects:
        if ob.type == 'MESH':
            meshName = ob.data.name
            if not meshName in meshes:
                saveMesh(scene, ob, dirAbs, dirLocal)
                meshLocalPath = dirLocal + meshName + ".obj"
                localFilenames.append(meshLocalPath)
                meshAbsPath = dirAbs + "/" + meshName + ".obj"
                absFilenames.append(meshAbsPath)
                meshes.append(meshName)

            saveMeshEntity(scene, ob, dirAbs, dirLocal)
            entityFileLocalPath = dirLocal + ob.name + ".entity"
            localFilenames.append(entityFileLocalPath)
            entityFileAbsPath = dirAbs + "/" + ob.name + ".entity"
            absFilenames.append(entityFileAbsPath)
            
            entities.append(entityFileLocalPath)
        #TODO: lamps    
        else:
            saveEmptyEntity(scene, ob, dirAbs, dirLocal)
            entityFileLocalPath = dirLocal + ob.name + ".entity"
            localFilenames.append(entityFileLocalPath)
            entityFileAbsPath = dirAbs + "/" + ob.name + ".entity"
            absFilenames.append(entityFileAbsPath)
            
            entities.append(entityFileLocalPath)

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

class DagonObjectProps(bpy.types.PropertyGroup):
    dagonVisible = bpy.props.BoolProperty(name="Visible", default=True)
    dagonSolid = bpy.props.BoolProperty(name="Solid", default=False)
    dagonCastShadow = bpy.props.BoolProperty(name="Cast Shadow", default=True)
    dagonUseMotionBlur = bpy.props.BoolProperty(name="Motion Blur", default=True)
    dagonLayer = bpy.props.IntProperty(name="Layer", default=1)
    
class DagonObjectPropsPanel(bpy.types.Panel):
    bl_label = "Dagon Properties"
    bl_idname = "dagon_object_props"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        obj = context.object

        props = obj.dagonProps
        
        row = self.layout.row()
        split = row.split(percentage=0.5)
        col = split.column()
        col.prop(props, 'dagonVisible')
        col = split.column()
        col.prop(props, 'dagonSolid')

        row = self.layout.row()
        split = row.split(percentage=0.5)
        col = split.column()
        col.prop(props, 'dagonCastShadow')
        col = split.column()
        col.prop(props, 'dagonUseMotionBlur')

        col = self.layout.column(align=True)
        col.prop(props, 'dagonLayer')

ParallaxModeEnum = [
    ('ParallaxNone', "None", "", 0),
    ('ParallaxSimple', "Simple", "", 1),
    ('ParallaxOcclusionMapping', "Occlusion Mapping", "", 2)
]

ShadowFilterEnum = [
    ('ShadowFilterNone', "None", "", 0),
    ('ShadowFilterPCF', "PCF", "", 1)
]

BlendingModeEnum = [
    ('BlendingModeOpaque', "Opaque", "", 0),
    ('BlendingModeTransparent', "Transparent", "", 1),
    ('BlendingModeAdditive', "Additive", "", 2)
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
    dagonParallaxScale = bpy.props.FloatProperty(name="Parallax Scale", default=0.03, min=0.0)
    dagonParallaxBias = bpy.props.FloatProperty(name="Parallax Bias", default=-0.01)
    dagonShadeless = bpy.props.BoolProperty(name="Shadeless", default=False)
    dagonCulling = bpy.props.BoolProperty(name="Culling", default=True)
    dagonColorWrite = bpy.props.BoolProperty(name="Color Write", default=True)
    dagonDepthWrite = bpy.props.BoolProperty(name="Depth Write", default=True)
    dagonReceiveShadows = bpy.props.BoolProperty(name="Receive Shadows", default=True)
    dagonFog = bpy.props.BoolProperty(name="Fog", default=True)
    dagonShadowFilter = bpy.props.EnumProperty(name="Shadow Filter", items=ShadowFilterEnum)
    dagonBlendingMode = bpy.props.EnumProperty(name="Blending Mode", items=BlendingModeEnum)
    dagonTransparency = bpy.props.FloatProperty(name="Transparency", default=1.0, min=0.0, max=1.0, subtype='FACTOR')

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

        col = self.layout.column(align=True)
        col.prop(props, 'dagonParallaxScale')
        col.prop(props, 'dagonParallaxBias')

        row = self.layout.row()
        split = row.split(percentage=0.5)
        col = split.column()
        col.prop(props, 'dagonShadeless')
        col = split.column()
        col.prop(props, 'dagonCulling')

        row = self.layout.row()
        split = row.split(percentage=0.5)
        col = split.column()
        col.prop(props, 'dagonColorWrite')
        col = split.column()
        col.prop(props, 'dagonDepthWrite')

        row = self.layout.row()
        split = row.split(percentage=0.5)
        col = split.column()
        col.prop(props, 'dagonReceiveShadows')
        col = split.column()
        col.prop(props, 'dagonFog')

        col = self.layout.column(align=True)
        col.prop(props, 'dagonShadowFilter')

        col = self.layout.column(align=True)
        col.prop(props, 'dagonBlendingMode')

        col = self.layout.column(align=True)
        col.prop(props, 'dagonTransparency')

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func_export_dagon_asset)
    bpy.types.Material.dagonProps = bpy.props.PointerProperty(type=DagonMaterialProps)
    bpy.types.Object.dagonProps = bpy.props.PointerProperty(type=DagonObjectProps)

def unregister():
    del bpy.types.Object.dagonProps
    del bpy.types.Material.dagonProps
    bpy.types.INFO_MT_file_export.remove(menu_func_export_dagon_asset)
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()

