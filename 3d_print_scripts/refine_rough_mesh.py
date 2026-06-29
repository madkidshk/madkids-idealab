import argparse
import bmesh
import json
import bpy
import os
import sys
from pathlib import Path


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.engine = "BLENDER_EEVEE"
    bpy.context.scene.unit_settings.system = "METRIC"


def import_mesh(path):
    ext = Path(path).suffix.lower()
    if ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        raise ValueError(f"Unsupported input format: {ext}")

    bpy.context.view_layer.update()
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("No mesh object imported")
    return meshes


def join_meshes(meshes):
    if len(meshes) == 1:
        return meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    return bpy.context.object


def set_active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_modifier(obj, modifier):
    set_active(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def normalize_scale(obj, target_height_mm):
    if target_height_mm <= 0:
        return
    bpy.context.view_layer.update()
    height = obj.dimensions.z
    if height <= 0:
        return
    obj.scale *= target_height_mm / height
    set_active(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def add_thickness(obj, thickness_mm):
    if thickness_mm <= 0:
        return
    solid = obj.modifiers.new(name="PrintThickness", type="SOLIDIFY")
    solid.thickness = thickness_mm
    solid.offset = 0.0
    solid.use_quality_normals = True
    solid.use_even_offset = True
    apply_modifier(obj, solid)


def round_edges(obj, width_mm, segments):
    if width_mm <= 0:
        return
    bevel = obj.modifiers.new(name="SoftRoundEdges", type="BEVEL")
    bevel.width = width_mm
    bevel.segments = max(1, segments)
    bevel.profile = 0.65
    bevel.affect = "EDGES"
    apply_modifier(obj, bevel)


def voxel_remesh(obj, voxel_size, adaptivity):
    if voxel_size <= 0:
        return
    remesh = obj.modifiers.new(name="VoxelRemesh", type="REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = voxel_size
    remesh.adaptivity = adaptivity
    apply_modifier(obj, remesh)


def smooth_mesh(obj, iterations, factor):
    if iterations <= 0 or factor <= 0:
        return
    smooth = obj.modifiers.new(name="SurfaceSmooth", type="SMOOTH")
    smooth.iterations = iterations
    smooth.factor = factor
    apply_modifier(obj, smooth)


def clean_mesh(obj, args):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.mesh.fill_holes(sides=0)
    bpy.ops.object.mode_set(mode="OBJECT")

    normalize_scale(obj, args.target_height_mm)
    add_thickness(obj, args.solidify_mm)
    round_edges(obj, args.bevel_mm, args.bevel_segments)
    voxel_remesh(obj, args.voxel_size, args.voxel_adaptivity)
    smooth_mesh(obj, args.smooth_iterations, args.smooth_factor)


def mesh_report(obj):
    bpy.context.view_layer.update()
    mesh = obj.data
    mesh.update(calc_edges=True)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    dims = [round(v, 3) for v in obj.dimensions]
    nonmanifold_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
    loose_edges = sum(1 for edge in bm.edges if len(edge.link_faces) == 0)
    loose_vertices = sum(1 for vertex in bm.verts if len(vertex.link_edges) == 0)
    bm.free()
    return {
        "object": obj.name,
        "dimensions_mm": dims,
        "vertices": len(mesh.vertices),
        "faces": len(mesh.polygons),
        "nonmanifold_edges": nonmanifold_edges,
        "loose_edges": loose_edges,
        "loose_vertices": loose_vertices,
        "printability": "pass" if nonmanifold_edges == 0 and loose_edges == 0 and loose_vertices == 0 else "check",
    }


def export_mesh(obj, path):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    ext = Path(path).suffix.lower()
    if ext == ".stl":
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, global_scale=1.0, ascii_format=False)
    elif ext == ".obj":
        bpy.ops.wm.obj_export(filepath=path, export_selected_objects=True, global_scale=1.0)
    else:
        raise ValueError(f"Unsupported output format: {ext}")


def main():
    parser = argparse.ArgumentParser(description="Import a rough mesh, clean it, and export a printable mesh.")
    parser.add_argument("--input", required=True, help="Input mesh path (.stl, .obj, .glb, .gltf)")
    parser.add_argument("--output", required=True, help="Output mesh path (.stl or .obj)")
    parser.add_argument("--target-height-mm", type=float, default=80.0, help="Scale model to this height before export; use 0 to keep scale")
    parser.add_argument("--solidify-mm", type=float, default=0.0, help="Add centered thickness for thin/flat source meshes")
    parser.add_argument("--bevel-mm", type=float, default=0.8, help="Round sharp edges before remesh")
    parser.add_argument("--bevel-segments", type=int, default=5, help="Roundness quality for bevel")
    parser.add_argument("--voxel-size", type=float, default=0.9, help="Voxel remesh size in model units/mm")
    parser.add_argument("--voxel-adaptivity", type=float, default=0.0, help="Voxel remesh adaptivity")
    parser.add_argument("--smooth-iterations", type=int, default=10, help="Surface smoothing iterations")
    parser.add_argument("--smooth-factor", type=float, default=0.24, help="Surface smoothing strength")
    parser.add_argument("--report", help="Optional JSON printability report path")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)

    ensure_dir(os.path.dirname(args.output) or ".")
    reset_scene()
    meshes = import_mesh(args.input)
    obj = join_meshes(meshes)
    clean_mesh(obj, args)
    report = mesh_report(obj)
    export_mesh(obj, args.output)
    if args.report:
        ensure_dir(os.path.dirname(args.report) or ".")
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
    print(json.dumps({"refined": f"{args.input} -> {args.output}", **report}, ensure_ascii=False))


if __name__ == "__main__":
    main()
