"""Pure-Python mesh objects for headless generators (DD-014 Phase B2)."""

from __future__ import annotations

import copy
from typing import Any


class Vec3:
    __slots__ = ("x", "y", "z")

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def as_list(self):
        return [self.x, self.y, self.z]

    def copy(self):
        return Vec3(self.x, self.y, self.z)


BOX_FACES = (
    (0, 1, 2, 3),
    (4, 7, 6, 5),
    (0, 4, 5, 1),
    (1, 5, 6, 2),
    (2, 6, 7, 3),
    (3, 7, 4, 0),
)


def box_local_verts(dx, dy, dz):
    return [
        (0.0, 0.0, 0.0),
        (dx, 0.0, 0.0),
        (dx, dy, 0.0),
        (0.0, dy, 0.0),
        (0.0, 0.0, dz),
        (dx, 0.0, dz),
        (dx, dy, dz),
        (0.0, dy, dz),
    ]


def triangulate_faces(faces):
    tris = []
    for face in faces:
        idxs = list(face)
        if len(idxs) < 3:
            continue
        for i in range(1, len(idxs) - 1):
            tris.append([idxs[0], idxs[i], idxs[i + 1]])
    return tris


class MeshObject:
    """Minimal stand-in for a Blender object used by generators."""

    __slots__ = (
        "name",
        "type",
        "location",
        "rotation_z_deg",
        "vertices",
        "faces",
        "props",
        "display_type",
        "show_in_front",
        "collection",
        "parent",
        "color",
        "text",
    )

    def __init__(
        self,
        name,
        *,
        location=(0, 0, 0),
        rotation_z_deg=0.0,
        vertices=None,
        faces=None,
        obj_type="MESH",
        collection="",
        display_type=None,
        color=None,
        text=None,
    ):
        self.name = name
        self.type = obj_type
        self.location = Vec3(*location)
        self.rotation_z_deg = float(rotation_z_deg or 0.0)
        self.vertices = list(vertices or [])
        self.faces = list(faces or [])
        self.props: dict[str, Any] = {}
        self.display_type = display_type or "SOLID"
        self.show_in_front = False
        self.collection = collection or ""
        self.parent = None
        self.color = color
        self.text = text

    def __setitem__(self, key, value):
        self.props[key] = value

    def __getitem__(self, key):
        return self.props[key]

    def get(self, key, default=None):
        return self.props.get(key, default)

    def keys(self):
        return self.props.keys()

    def _rotate_z(self, x, y, degrees):
        import math

        if not degrees:
            return x, y
        rad = math.radians(float(degrees))
        c, s = math.cos(rad), math.sin(rad)
        return x * c - y * s, x * s + y * c

    def local_point_to_world(self, x, y, z):
        """Map a point in this object's local space to world (Z-rotation + parent chain)."""
        rx, ry = self._rotate_z(float(x), float(y), self.rotation_z_deg)
        wx = rx + self.location.x
        wy = ry + self.location.y
        wz = float(z) + self.location.z
        if self.parent is not None:
            return self.parent.local_point_to_world(wx, wy, wz)
        return (wx, wy, wz)

    def world_origin(self):
        return self.local_point_to_world(0.0, 0.0, 0.0)

    def world_vertices(self):
        return [list(self.local_point_to_world(v[0], v[1], v[2])) for v in self.vertices]

    def world_bbox_corners(self):
        verts = self.world_vertices()
        if not verts:
            ox, oy, oz = self.world_origin()
            return [[ox, oy, oz]] * 8
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        z0, z1 = min(zs), max(zs)
        return [
            [x0, y0, z0],
            [x1, y0, z0],
            [x1, y1, z0],
            [x0, y1, z0],
            [x0, y0, z1],
            [x1, y0, z1],
            [x1, y1, z1],
            [x0, y1, z1],
        ]

    def dimensions(self):
        corners = self.world_bbox_corners()
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        zs = [c[2] for c in corners]
        return [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)]


def join_mesh_objects(objects, result_name, collection):
    """Join mesh objects into one (Blender join semantics: anchor = first by location)."""
    meshes = [o for o in objects if o.type == "MESH"]
    others = [o for o in objects if o.type != "MESH"]

    if not meshes and len(others) == 1:
        others[0].name = result_name
        return others[0]

    if len(meshes) == 1 and not others:
        meshes[0].name = result_name
        return meshes[0]

    if not meshes:
        return None

    meshes = sorted(meshes, key=lambda o: (o.location.x, o.location.y, o.location.z))
    anchor = meshes[0]
    ax, ay, az = anchor.location.x, anchor.location.y, anchor.location.z
    all_verts = [tuple(v) for v in anchor.vertices]
    all_faces = [tuple(f) for f in anchor.faces]
    offset = len(all_verts)

    for other in meshes[1:]:
        ox = other.location.x - ax
        oy = other.location.y - ay
        oz = other.location.z - az
        for v in other.vertices:
            all_verts.append((float(v[0]) + ox, float(v[1]) + oy, float(v[2]) + oz))
        for face in other.faces:
            all_faces.append(tuple(i + offset for i in face))
        offset = len(all_verts)

    joined = MeshObject(
        result_name,
        location=(ax, ay, az),
        vertices=all_verts,
        faces=all_faces,
        collection=collection,
        color=anchor.color,
        display_type=anchor.display_type,
    )
    # Prefer clearance/wire props from any input mesh
    for src in meshes:
        for key, value in src.props.items():
            if key not in joined.props:
                joined.props[key] = value
        if src.display_type == "WIRE":
            joined.display_type = "WIRE"
            joined.show_in_front = True
    return joined


class MeshStore:
    """Collection of headless objects produced by generators."""

    def __init__(self):
        self.objects: list[MeshObject] = []

    def clear(self):
        self.objects.clear()

    def clone(self) -> "MeshStore":
        """Deep copy including parent links (for dry-run clones)."""
        other = MeshStore()
        other.objects = copy.deepcopy(self.objects)
        return other

    def add(self, obj: MeshObject):
        self.objects.append(obj)
        return obj

    def remove(self, obj: MeshObject):
        if obj in self.objects:
            self.objects.remove(obj)

    def delete_collection(self, collection_name: str) -> int:
        before = len(self.objects)
        self.objects = [o for o in self.objects if o.collection != collection_name]
        return before - len(self.objects)

    def delete_prefix(self, prefix: str) -> int:
        before = len(self.objects)
        self.objects = [o for o in self.objects if not o.name.startswith(prefix)]
        return before - len(self.objects)

    def delete_by_object_id(self, object_id: str) -> int:
        before = len(self.objects)
        self.objects = [o for o in self.objects if o.get("layoutlab_object_id") != object_id]
        return before - len(self.objects)
