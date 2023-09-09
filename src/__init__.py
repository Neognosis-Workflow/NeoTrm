import bpy
import bmesh
import struct
from bpy_extras.io_utils import ImportHelper

class ImportTrm(bpy.types.Operator, ImportHelper):
    bl_idname = "import_mesh.trm"
    bl_label = "Import TRM Mesh"
    filename_ext = ".trm"
    filter_glob: bpy.props.StringProperty(
        default="*.trm",
        options={'HIDDEN'}
    )

    quadrify: bpy.props.BoolProperty(
        name="As Quads",
        description="Whether the TRM should be imported as quads.",
        default=True
        )
    
    merge: bpy.props.BoolProperty(
        name="Merge Vertices",
        description="Whether the vertices should be merged.",
        default=True
        )
    
    def TrmToBlender(self, trm, name):
        # create mesh
        mesh = bpy.data.meshes.new(name)

        faces = []

        if self.quadrify:
            for i in range(0, trm.trisLen, 6):
                face = [trm.tris[i + 5], trm.tris[i + 2], trm.tris[i + 1], trm.tris[i]]
                faces.append(face)
        else:
            for i in range(0, trm.trisLen, 3):
                face = [trm.tris[i + 2], trm.tris[i + 1], trm.tris[i]]
                faces.append(face)

        mesh.from_pydata(trm.verts, [], faces)
        mesh.validate()
        mesh.update()

        # create object
        scene = bpy.context.scene
        obj = bpy.data.objects.new(name, mesh)

        scene.collection.objects.link(obj)
        layer = bpy.context.view_layer
        layer.update()

        if self.merge:
            bm = bmesh.new()

            bm.from_mesh(mesh)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
            bm.to_mesh(mesh)
            mesh.update()
            bm.clear()
            bm.free()

        return obj

    def execute(self, context):
        filepath = self.properties.filepath
        #return {'CANCELLED'}

        with open(filepath, "rb") as f:
            # identifier
            idLen = int.from_bytes(f.read(1), byteorder='little', signed=False)

            if idLen != 10: # identifer should be 10 bytes for Track Mesh string
                self.report({"ERROR"}, "Not a valid TRM file.")
                return {'CANCELLED'}

            idName = f.read(idLen).decode("utf-8") # should be Track Mesh
            if idName != "Track Mesh":
                self.report({"ERROR"}, "Not a valid TRM file.")
                return {'CANCELLED'}

            # header
            headerEntryCount = int.from_bytes(f.read(4), byteorder='little', signed=False)
            headerEntries = []
            for i in range(0, headerEntryCount):
                headerEntries.append(ModFmtHeader(f))

            # data
            trmMeshes = []
            for e in headerEntries:
                f.seek(e.dataPosition)
                trmMeshes.append(TrmMesh(f))

            trmObjects = []
            for i in range(0, headerEntryCount):
                if (headerEntries[i].name == "Tunnel"): continue # legacy feature, we're not interested in the tunnel meshes

                trmObjects.append(self.TrmToBlender(trmMeshes[i], headerEntries[i].name))

            if len(trmObjects) > 0:
                # create trm collection
                newCollection = bpy.data.collections.new("TRM Mesh")
                bpy.context.scene.collection.children.link(newCollection)

                # parent trm meshes to new collection
                for trm in trmObjects:
                    bpy.context.scene.collection.objects.unlink(trm)
                    newCollection.objects.link(trm)


        return {'FINISHED'}

class ModFmtHeader:
    def __init__(self, f):
        nameLen = int.from_bytes(f.read(1), byteorder='little', signed=False)
        self.name = f.read(nameLen).decode("utf-8")
        self.dataPosition = int.from_bytes(f.read(8), byteorder='little', signed=False)

class TrmMesh:
    def __init__(self, f):
        self.verts = []
        self.normals = []
        self.tris = []

        dataLen = int.from_bytes(f.read(4), byteorder='little', signed=True)

        # mesh data lengths
        self.vertLen = int.from_bytes(f.read(4), byteorder='little', signed=True)
        self.normalsLen = int.from_bytes(f.read(4), byteorder='little', signed=True)
        self.trisLen = int.from_bytes(f.read(4), byteorder='little', signed=True)

        # build vertex list
        for i in range(0, self.vertLen):
            x = struct.unpack('f', f.read(4))
            y = struct.unpack('f', f.read(4))
            z = struct.unpack('f', f.read(4))

            self.verts.append([x[0], z[0], y[0]])

        # build normals list
        for i in range(0, self.normalsLen):
            x = struct.unpack('f', f.read(4))
            y = struct.unpack('f', f.read(4))
            z = struct.unpack('f', f.read(4))

            self.normals.append([x[0], z[0], y[0]])

        # build triangles list
        for i in range(0, self.trisLen):
            self.tris.append(int.from_bytes(f.read(4), byteorder='little', signed=True))

bl_info = {
    "name": "Neognosis TRM",
    "description": "Import BallisticNG TRM meshes.",
    "author": "Adam Chivers",
    "version": (1, 1),
    "blender": (2, 90, 0),
    "location": "File -> Import",
    "category": "Import-Export"
}

classes = (
    ImportTrm,
)

def menu_import(self, context):
    self.layout.operator(ImportTrm.bl_idname, text = "Track Render Mesh (.trm)")

def register():
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.TOPBAR_MT_file_import.append(menu_import)

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

    bpy.types.TOPBAR_MT_file_import.remove(menu_import)