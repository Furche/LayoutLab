import bpy

from .collections import get_or_create_collection
from .materials import ensure_material
from .metadata import get_active_context
from .parts import register_created_object


def create_box(name, location, dimensions, color=(0.8, 0.8, 0.8, 1), collection="layout_tests", role=None, display_type=None, component=None):
    lx, ly, lz = [float(v) for v in location]
    dx, dy, dz = [float(v) for v in dimensions]
    mesh = bpy.data.meshes.new(name + "_mesh")
    verts = [(0,0,0),(dx,0,0),(dx,dy,0),(0,dy,0),(0,0,dz),(dx,0,dz),(dx,dy,dz),(0,dy,dz)]
    faces = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (lx, ly, lz)
    if color:
        obj.data.materials.append(ensure_material(f"MAT_{name}", color))
    if display_type:
        obj.display_type = display_type
    if role and not get_active_context():
        obj["layoutlab_role"] = role
    get_or_create_collection(collection).objects.link(obj)
    if register_created_object(obj):
        return obj
    if get_active_context() and role:
        obj["layoutlab_role"] = role
    return obj


def create_label(name, location, text, collection="layout_tests", size=0.35, component=None):
    curve = bpy.data.curves.new(name + "_curve", type="FONT")
    curve.body = text
    curve.size = size
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    get_or_create_collection(collection).objects.link(obj)
    if register_created_object(obj):
        return obj
    obj["layoutlab_role"] = "label"
    return obj
