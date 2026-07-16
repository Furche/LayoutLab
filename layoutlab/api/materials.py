import bpy


def ensure_material(name, color, backface_culling=False):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    try:
        mat.use_backface_culling = bool(backface_culling)
    except Exception:
        pass
    if len(color) == 4 and color[3] < 1.0:
        mat.use_nodes = True
        mat.blend_method = "BLEND"
        mat.show_transparent_back = True
        try:
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            bsdf.inputs["Alpha"].default_value = color[3]
        except Exception:
            pass
    return mat
