# -*- coding: utf-8 -*-
"""
VILLA AURELIA — 20 x 15 m 全娱乐设施现代别墅
================================================
Blender 5.2 LTS / bpy 程序化基础空间布局模型

运行方式
--------
1. Blender 5.2 → Scripting 工作区 → 打开本文件 → Run Script（Alt+P）。
2. 或命令行：
   blender --background --factory-startup --python villa_entertainment_5_2.py

脚本会自动清空当前场景，然后生成：
  • 20.0 x 15.0 m 两层灰白色别墅壳体（200 mm 外墙、平屋顶、大面积玻璃幕墙）
  • 一层：挑高客厅、带吧台的台球室、室内恒温泳池
  • 二层：家庭影院、电竞房、专业健身房、玻璃栏板走廊
  • 室外：8 x 4 m 露天泳池、半场篮球场、躺椅、树植与庭院
  • 六个区域的彩色地面标识与中英文字标签
  • 太阳光、程序化天空、室内氛围灯与两台已对准别墅的摄像机

提示
----
• 屋顶、幕墙、每一件家具都按专业前缀命名，并归入可折叠的集合。
• 默认使用 Cycles 并自动启用 GPU；没有可用 GPU 时自动回退 CPU。
• 默认输出路径为 //villa_entertainment.png（F12 即可渲染）。
• 集合 03_SHELL_Roof 可以直接隐藏，用来查看二层平面与室内。
"""

import bpy
import math
import os
import random
from math import radians, sin, cos, pi, atan2

# =============================================================================
# 01. 全局配置
# =============================================================================

RENDER_ENGINE = "CYCLES"         # "CYCLES"（推荐，自动启用 GPU）或 "EEVEE"（快）
RENDER_SAMPLES = 96              # EEVEE TAA / Cycles 采样
OUTPUT_FILE = "//villa_entertainment.png"

# 建筑基本尺寸（单位：米）
VILLA_W = 20.0                  # X 向总宽
VILLA_D = 15.0                  # Y 向进深
WALL_T = 0.20                   # 外墙厚 200 mm
X0, X1 = -VILLA_W / 2, VILLA_W / 2
Y0, Y1 = -VILLA_D / 2, VILLA_D / 2
XIN0, XIN1 = X0 + WALL_T, X1 - WALL_T
YIN0, YIN1 = Y0 + WALL_T, Y1 - WALL_T

GROUND_Z = 0.20                 # 一层完成面
F2_Z = 3.40                     # 二层完成面（两层楼板，层高 3.2 m）
CEIL_Z = 6.40                   # 屋顶结构底
ROOF_Z = 6.60                   # 屋顶完成面
PARAPET_TOP = 7.15
PLINTH_TOP = 0.20

# 场地
SITE_X0, SITE_X1 = -20.0, 42.0
SITE_Y0, SITE_Y1 = -24.0, 22.0
SITE_Z = 0.0

# 室外泳池：8 x 4 m
POOL_X0, POOL_X1 = 12.4, 20.4
POOL_Y0, POOL_Y1 = -5.5, -1.5
DECK_Z = 0.15
WATER_Z = -0.10

# 半场篮球场
COURT_X0, COURT_X1 = 23.5, 38.5
COURT_Y0, COURT_Y1 = -8.0, 6.0
COURT_Z = 0.14

# 字体
FONT_EN = None
FONT_CN = None
RNG = random.Random(20260526)

# 全局容器
COLL = {}
MAT = {}


# =============================================================================
# 02. 场景、集合与基础工具
# =============================================================================

def reset_scene():
    """完全清空当前场景，避免重复执行脚本时叠加对象。"""
    if bpy.context.mode != 'OBJECT':
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)

    for datablocks in (
        bpy.data.meshes, bpy.data.curves, bpy.data.materials,
        bpy.data.cameras, bpy.data.lights, bpy.data.images,
        bpy.data.node_groups, bpy.data.worlds,
    ):
        for block in list(datablocks):
            try:
                datablocks.remove(block)
            except Exception:
                pass

    try:
        bpy.ops.outliner.orphans_purge(do_recursive=True)
    except Exception:
        pass


def setup_scene():
    scene = bpy.context.scene
    scene.name = "VILLA_AURELIA_20x15"
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.length_unit = 'METERS'
    scene.unit_settings.scale_length = 1.0

    # 世界只负责很柔和的天空环境补光；摄像机中可见的渐变天空由独立 Sky Dome 提供。
    world = bpy.data.worlds.new("WORLD_SoftBlue_Ambient")
    world.use_nodes = True
    scene.world = world
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    out.location = (420, 0)
    bg = nodes.new("ShaderNodeBackground")
    bg.location = (160, 0)
    bg.inputs["Color"].default_value = hex_color("#9DB4C8")
    bg.inputs["Strength"].default_value = 0.30
    links.new(bg.outputs["Background"], out.inputs["Surface"])


def make_collections():
    """建立可折叠、可单独隐藏的集合树。"""
    COLL.clear()
    root = bpy.data.collections.new("VILLA_AURELIA_20x15")
    bpy.context.scene.collection.children.link(root)
    COLL["root"] = root

    specs = [
        ("site",        "00_SITE",             None),
        ("shell",       "01_VILLA_SHELL",       None),
        ("shell_body",  "01_SHELL_Body",        "shell"),
        ("shell_glass", "02_SHELL_Glazing",     "shell"),
        ("shell_roof",  "03_SHELL_Roof",        "shell"),
        ("shell_stair", "04_SHELL_Stair",       "shell"),
        ("pool",        "02_OUTDOOR_POOL",      None),
        ("court",       "03_BASKETBALL_COURT",  None),
        ("f1",          "04_INTERIOR_F1",       None),
        ("f1_zones",    "F1_Zones_Labels",      "f1"),
        ("f1_living",   "F1_Living",            "f1"),
        ("f1_billiard", "F1_Billiard_Bar",      "f1"),
        ("f1_pool",     "F1_Indoor_Pool",       "f1"),
        ("f2",          "05_INTERIOR_F2",       None),
        ("f2_zones",    "F2_Zones_Labels",      "f2"),
        ("f2_theater",  "F2_Home_Theater",      "f2"),
        ("f2_esports",  "F2_Esports",           "f2"),
        ("f2_gym",      "F2_Gym",               "f2"),
        ("f2_gallery",  "F2_Gallery",           "f2"),
        ("labels",      "06_ROOM_LABELS",       None),
        ("landscape",   "07_LANDSCAPE",         None),
        ("lighting",    "08_LIGHTING",          None),
        ("camera",      "09_CAMERA",            None),
    ]
    for key, name, parent in specs:
        coll = bpy.data.collections.new(name)
        parent_coll = COLL[parent] if parent else root
        parent_coll.children.link(coll)
        COLL[key] = coll


def load_fonts():
    global FONT_EN, FONT_CN
    latin_candidates = [
        r"C:\Windows\Fonts\bahnschrift.ttf",
        r"C:\Windows\Fonts\seguisb.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        "/System/Library/Fonts/Avenir Next.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    cjk_candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]

    for path in latin_candidates:
        if os.path.exists(path):
            try:
                FONT_EN = bpy.data.fonts.load(path, check_existing=True)
                break
            except Exception:
                pass
    for path in cjk_candidates:
        if os.path.exists(path):
            try:
                FONT_CN = bpy.data.fonts.load(path, check_existing=True)
                break
            except Exception:
                pass


def _new_mesh_obj(name, verts, faces, mat, coll):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    if mat:
        mesh.materials.append(mat)
    return obj


def add_box(name, loc, size, mat, coll, rot=(0.0, 0.0, 0.0),
            bevel=0.0, bevel_segments=2):
    """以真实尺寸生成立方体（不依赖 bpy.ops，重复运行更稳健）。"""
    sx, sy, sz = size
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    verts = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7),
        (0, 1, 5, 4), (1, 2, 6, 5),
        (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    obj = _new_mesh_obj(name, verts, faces, mat, coll)
    obj.location = loc
    obj.rotation_euler = rot
    if bevel > 0:
        mod = obj.modifiers.new("Soft_Edges", 'BEVEL')
        mod.width = bevel
        mod.segments = bevel_segments
        mod.limit_method = 'ANGLE'
        mod.angle_limit = radians(28)
    return obj


def add_cylinder(name, loc, radius, depth, mat, coll,
                 radius_top=None, segments=32, rot=(0, 0, 0),
                 smooth=True, bevel=0.0):
    """圆柱/圆台，轴向为局部 Z。"""
    if radius_top is None:
        radius_top = radius
    verts = []
    z0, z1 = -depth / 2.0, depth / 2.0
    for z, r in ((z0, radius), (z1, radius_top)):
        for i in range(segments):
            a = 2.0 * pi * i / segments
            verts.append((r * cos(a), r * sin(a), z))
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, segments + j, segments + i))
    faces.append(tuple(reversed(range(segments))))
    faces.append(tuple(range(segments, segments * 2)))
    obj = _new_mesh_obj(name, verts, faces, mat, coll)
    obj.location = loc
    obj.rotation_euler = rot
    if smooth:
        for poly in obj.data.polygons:
            if poly.index < segments:
                poly.use_smooth = True
    if bevel > 0:
        mod = obj.modifiers.new("Soft_Edges", 'BEVEL')
        mod.width = bevel
        mod.segments = 2
    return obj


def add_sphere(name, loc, radius, mat, coll, scale=(1, 1, 1),
               segments=20, rings=12, smooth=True):
    verts = [(0.0, 0.0, radius)]
    for i in range(1, rings):
        theta = pi * i / rings
        z = radius * cos(theta)
        r = radius * sin(theta)
        for j in range(segments):
            phi = 2 * pi * j / segments
            verts.append((r * cos(phi), r * sin(phi), z))
    verts.append((0.0, 0.0, -radius))
    bottom_idx = len(verts) - 1
    faces = []
    for j in range(segments):
        nj = (j + 1) % segments
        faces.append((0, 1 + j, 1 + nj))
    for i in range(rings - 2):
        a0 = 1 + i * segments
        a1 = 1 + (i + 1) * segments
        for j in range(segments):
            nj = (j + 1) % segments
            faces.append((a0 + j, a1 + j, a1 + nj, a0 + nj))
    last_ring = 1 + (rings - 2) * segments
    for j in range(segments):
        nj = (j + 1) % segments
        faces.append((last_ring + j, bottom_idx, last_ring + nj))
    obj = _new_mesh_obj(name, verts, faces, mat, coll)
    obj.location = loc
    obj.scale = scale
    if smooth:
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def add_text(name, body, loc, size, mat, coll, rot=(0, 0, 0),
             font=None, align_x='CENTER', align_y='CENTER',
             extrude=0.002, space_character=1.0):
    curve = bpy.data.curves.new(name + "_data", type='FONT')
    curve.body = body
    curve.size = size
    curve.align_x = align_x
    curve.align_y = align_y
    curve.extrude = extrude
    curve.space_character = space_character
    curve.materials.append(mat)
    if font is not None:
        curve.font = font
    obj = bpy.data.objects.new(name, curve)
    obj.location = loc
    obj.rotation_euler = rot
    coll.objects.link(obj)
    return obj


def add_line_2d(name, p0, p1, width, z, mat, coll, thickness=0.006):
    """地面上两点之间的细矩形线（用于球场标线）。"""
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return None
    ang = atan2(dy, dx)
    return add_box(
        name,
        ((x0 + x1) / 2.0, (y0 + y1) / 2.0, z + thickness / 2.0),
        (length, width, thickness), mat, coll, rot=(0, 0, ang),
    )


def add_arc_ribbon(name, center, radius, width, z, a0, a1, mat, coll,
                   steps=72, closed=False):
    """生成平铺在 XY 平面上的圆弧白线。"""
    cx, cy = center
    if closed:
        angles = [a0 + (a1 - a0) * i / steps for i in range(steps + 1)]
    else:
        angles = [a0 + (a1 - a0) * i / steps for i in range(steps + 1)]
    verts = []
    for a in angles:
        ca, sa = cos(a), sin(a)
        verts.append((cx + (radius - width / 2) * ca,
                      cy + (radius - width / 2) * sa, z))
        verts.append((cx + (radius + width / 2) * ca,
                      cy + (radius + width / 2) * sa, z))
    faces = []
    for i in range(steps):
        a, b = i * 2, i * 2 + 1
        c, d = (i + 1) * 2, (i + 1) * 2 + 1
        faces.append((a, b, d, c))
    obj = _new_mesh_obj(name, verts, faces, mat, coll)
    mod = obj.modifiers.new("Court_Line_Thickness", 'SOLIDIFY')
    mod.thickness = 0.006
    mod.offset = 0.0
    return obj


def add_curve_tube(name, points, bevel, mat, coll, cyclic=False, resolution=2):
    curve = bpy.data.curves.new(name + "_data", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = resolution
    curve.bevel_depth = bevel
    curve.bevel_resolution = 1
    curve.resolution_u = 1
    spline = curve.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for i, p in enumerate(points):
        spline.points[i].co = (p[0], p[1], p[2], 1.0)
    spline.use_cyclic_u = cyclic
    curve.materials.append(mat)
    obj = bpy.data.objects.new(name, curve)
    coll.objects.link(obj)
    return obj


def track_to(obj, target, track_axis='TRACK_NEGATIVE_Z', up_axis='UP_Y'):
    """用约束把摄像机/灯光对准目标点，空物体目标可随时移动。"""
    empty = bpy.data.objects.new(obj.name + "_Target", None)
    COLL["lighting" if obj.type == 'LIGHT' else "camera"].objects.link(empty)
    empty.location = target
    empty.empty_display_size = 0.35
    c = obj.constraints.new('TRACK_TO')
    c.target = empty
    c.track_axis = track_axis
    c.up_axis = up_axis
    return empty


def light_area(name, loc, target, energy, color, size, size_y=None, coll=None):
    data = bpy.data.lights.new(name + "_data", 'AREA')
    data.energy = energy
    data.color = color
    data.shape = 'RECTANGLE'
    data.size = size
    data.size_y = size_y if size_y else size
    obj = bpy.data.objects.new(name, data)
    (coll or COLL["lighting"]).objects.link(obj)
    obj.location = loc
    direction = (mathutils_vector(target) - obj.location)
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return obj


def light_point(name, loc, energy, color, radius=0.3, coll=None):
    data = bpy.data.lights.new(name + "_data", 'POINT')
    data.energy = energy
    data.color = color
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    (coll or COLL["lighting"]).objects.link(obj)
    obj.location = loc
    return obj


def light_spot(name, loc, target, energy, color, spot_size=50, spot_blend=0.4):
    data = bpy.data.lights.new(name + "_data", 'SPOT')
    data.energy = energy
    data.color = color
    data.spot_size = radians(spot_size)
    data.spot_blend = spot_blend
    obj = bpy.data.objects.new(name, data)
    COLL["lighting"].objects.link(obj)
    obj.location = loc
    direction = (mathutils_vector(target) - obj.location)
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return obj


def mathutils_vector(v):
    from mathutils import Vector
    return Vector(v)


# =============================================================================
# 03. 材质
# =============================================================================

def srgb_to_linear(c):
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def hex_color(value, alpha=1.0):
    value = value.lstrip("#")
    r, g, b = (int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


def set_bsdf_input(bsdf, names, value):
    for name in names:
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = value
            return True
    return False


def make_pbr(name, hexcol, roughness=0.5, metallic=0.0, alpha=1.0,
             emission=None, emission_strength=0.0, transmission=0.0,
             coat=0.0, ior=1.45):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = hex_color(hexcol, alpha)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    set_bsdf_input(bsdf, ("Base Color",), hex_color(hexcol))
    set_bsdf_input(bsdf, ("Roughness",), roughness)
    set_bsdf_input(bsdf, ("Metallic",), metallic)
    set_bsdf_input(bsdf, ("IOR",), ior)
    set_bsdf_input(bsdf, ("Alpha",), alpha)
    set_bsdf_input(bsdf, ("Transmission Weight", "Transmission"), transmission)
    set_bsdf_input(bsdf, ("Coat Weight", "Clearcoat"), coat)
    if emission:
        set_bsdf_input(bsdf, ("Emission Color", "Emission"), hex_color(emission))
        set_bsdf_input(bsdf, ("Emission Strength",), emission_strength)

    if alpha < 1.0:
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = 'BLENDED'
        if hasattr(mat, "use_transparent_shadow"):
            mat.use_transparent_shadow = True
        if hasattr(mat, "show_transparent_back"):
            mat.show_transparent_back = False
    return mat


def add_bump(mat, scale=5.0, strength=0.035, detail=4.0, roughness_tex=0.55):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    tex = nodes.new("ShaderNodeTexNoise")
    tex.location = (-520, -220)
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = detail
    tex.inputs["Roughness"].default_value = roughness_tex
    bump = nodes.new("ShaderNodeBump")
    bump.location = (-260, -220)
    bump.inputs["Strength"].default_value = strength
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return tex, bump


def add_color_variation(mat, color_a, color_b, scale=2.2, detail=4.0,
                        world_space=False):
    """叠加两色大尺度噪声，避免大面积草坪/场地看起来像纯色卡纸。"""
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-760, 220)
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = detail
    noise.inputs["Roughness"].default_value = 0.62
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-520, 220)
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[0].color = hex_color(color_a)
    ramp.color_ramp.elements[1].position = 0.70
    ramp.color_ramp.elements[1].color = hex_color(color_b)
    if world_space:
        geom = nodes.new("ShaderNodeNewGeometry")
        geom.location = (-980, 220)
        links.new(geom.outputs["Position"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return noise


def add_pool_caustics(mat, base_hex="#176577", crest_hex="#9BE9E2", scale=2.3):
    """程序化水面焦散纹，透过透明水体在池底形成亮线。"""
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    coord = nodes.new("ShaderNodeTexCoord")
    coord.location = (-1040, 40)
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-860, 40)
    mapping.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    vor = nodes.new("ShaderNodeTexVoronoi")
    vor.location = (-660, 40)
    vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs["Scale"].default_value = scale
    vor.inputs["Randomness"].default_value = 1.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-420, 40)
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = hex_color(crest_hex)
    cr.elements[1].position = 0.055
    cr.elements[1].color = hex_color(base_hex)
    el = cr.elements.new(0.14)
    el.color = hex_color(base_hex)
    links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], vor.inputs["Vector"])
    links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    add_bump(mat, scale=4.0, strength=0.03, detail=2.0)


def add_marble_veins(mat, scale=2.4, strength=0.18):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-680, 160)
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 7.0
    noise.inputs["Roughness"].default_value = 0.68
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-430, 160)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = hex_color("#CEC7B8")
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = hex_color("#E9E4D9")
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    add_bump(mat, scale=3.0, strength=strength, detail=3.0)


def add_wood_grain(mat, scale=7.0, strength=0.055):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nodes.new("ShaderNodeTexWave")
    tex.location = (-480, 100)
    tex.wave_type = 'BANDS'
    tex.bands_direction = 'X'
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Distortion"].default_value = 3.0
    tex.inputs["Detail"].default_value = 2.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-240, 100)
    ramp.color_ramp.elements[0].color = hex_color("#5A3B29")
    ramp.color_ramp.elements[1].color = hex_color("#91613F")
    links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    add_bump(mat, scale=8.0, strength=strength, detail=2.0)


def make_materials():
    global MAT
    MAT = {}

    MAT["wall"] = make_pbr("M_Wall_WarmWhite", "#E7E1D5", roughness=0.72)
    MAT["wall_white"] = make_pbr("M_Wall_Chalk", "#F2EEE5", roughness=0.58)
    MAT["wall_grey"] = make_pbr("M_Concrete_Grey", "#8D8C86", roughness=0.78)
    MAT["dark"] = make_pbr("M_Metal_Black", "#171A19", roughness=0.34, metallic=0.55)
    MAT["dark_matte"] = make_pbr("M_Dark_Matte", "#262A28", roughness=0.72)
    MAT["bronze"] = make_pbr("M_Bronze_Warm", "#7A5A3C", roughness=0.32, metallic=0.65)
    MAT["concrete"] = make_pbr("M_Concrete_Pad", "#B7B0A3", roughness=0.8)
    MAT["stone"] = make_pbr("M_Travertine", "#BCB29F", roughness=0.65)
    MAT["stone_dark"] = make_pbr("M_Stone_Dark", "#57544F", roughness=0.68)
    MAT["marble"] = make_pbr("M_Marble_Warm", "#DAD4C8", roughness=0.24, coat=0.25)
    add_marble_veins(MAT["marble"])
    MAT["wood"] = make_pbr("M_Wood_Oak", "#A97853", roughness=0.42)
    add_wood_grain(MAT["wood"])
    MAT["wood_dark"] = make_pbr("M_Wood_Walnut", "#5A3B28", roughness=0.43)
    add_wood_grain(MAT["wood_dark"], scale=8.0)
    MAT["wood_light"] = make_pbr("M_Wood_Pale", "#C6A077", roughness=0.5)

    MAT["grass"] = make_pbr("M_Lawn", "#36552F", roughness=0.92)
    add_color_variation(MAT["grass"], "#2B4729", "#5F7447", scale=0.22,
                        detail=5.0, world_space=True)
    add_bump(MAT["grass"], scale=48.0, strength=0.28, detail=5.0)
    MAT["field"] = MAT["grass"]
    MAT["hedge"] = make_pbr("M_Hedge", "#26452B", roughness=0.88)
    add_bump(MAT["hedge"], scale=24.0, strength=0.30, detail=6.0)
    MAT["leaf"] = make_pbr("M_Leaf", "#2C4D30", roughness=0.82)
    MAT["leaf_light"] = make_pbr("M_Leaf_Light", "#4B6D40", roughness=0.84)
    MAT["leaf_far"] = make_pbr("M_Leaf_Far", "#4D6354", roughness=0.9)
    MAT["leaf_far_light"] = make_pbr("M_Leaf_Far_Light", "#687A61", roughness=0.9)
    MAT["bark"] = make_pbr("M_Bark", "#4B3728", roughness=0.9)
    MAT["gravel"] = make_pbr("M_Gravel", "#A49B8A", roughness=0.9)
    add_bump(MAT["gravel"], scale=55.0, strength=0.25, detail=4.0)

    MAT["glass"] = make_pbr(
        "M_Glass_Clear", "#C5E0E2", roughness=0.045, metallic=0.0,
        alpha=0.13, transmission=0.70, coat=0.30, ior=1.45,
    )
    MAT["glass_dark"] = make_pbr(
        "M_Glass_Smoked", "#7E999A", roughness=0.08, metallic=0.0,
        alpha=0.38, transmission=0.0, coat=0.25, ior=1.5,
    )
    MAT["glass_white"] = make_pbr(
        "M_Glass_Frosted", "#DDE4E0", roughness=0.24, alpha=0.22,
        transmission=0.0,
    )
    MAT["water"] = make_pbr(
        "M_Water_Pool", "#0B7D99", roughness=0.03, alpha=0.36,
        transmission=0.85, coat=0.42, ior=1.333,
    )
    add_bump(MAT["water"], scale=7.0, strength=0.18, detail=3.0)
    MAT["water_indoor"] = make_pbr(
        "M_Water_Indoor", "#0D7F91", roughness=0.035, alpha=0.40,
        transmission=0.82, coat=0.38, ior=1.333,
    )
    add_bump(MAT["water_indoor"], scale=9.0, strength=0.14, detail=3.0)
    MAT["pool_tile"] = make_pbr("M_Pool_Tile_Deep", "#1B6A7A", roughness=0.32)
    MAT["pool_tile_light"] = make_pbr("M_Pool_Tile_Aqua", "#3EA5B0", roughness=0.38)
    MAT["pool_tile_floor"] = make_pbr("M_Pool_Floor_Caustic", "#176577", roughness=0.34)
    add_pool_caustics(MAT["pool_tile_floor"])

    MAT["court"] = make_pbr("M_Basketball_Green", "#235B3F", roughness=0.62)
    add_color_variation(MAT["court"], "#1D4D36", "#2E6F4E", scale=3.5, detail=3.0)
    add_bump(MAT["court"], scale=42.0, strength=0.05, detail=3.0)
    MAT["court_key"] = make_pbr("M_Basketball_Key", "#2A6949", roughness=0.6)
    MAT["line"] = make_pbr("M_Court_Line_White", "#F1EDE1", roughness=0.52)
    MAT["orange"] = make_pbr("M_Basketball_Orange", "#D36B2B", roughness=0.55)
    MAT["metal"] = make_pbr("M_Metal_Brushed", "#9C9F9E", roughness=0.3, metallic=0.8)
    MAT["mirror"] = make_pbr("M_Mirror", "#DDE7E7", roughness=0.04, metallic=1.0)

    MAT["zone_living"] = make_pbr("M_Zone_Living_Sand", "#A99579", roughness=0.72)
    MAT["zone_billiard"] = make_pbr("M_Zone_Billiard_Teal", "#2D6255", roughness=0.68)
    MAT["zone_pool"] = make_pbr("M_Zone_Pool_Aqua", "#4EA5AB", roughness=0.62)
    MAT["zone_theater"] = make_pbr("M_Zone_Theater_Plum", "#583A4A", roughness=0.76)
    MAT["zone_esports"] = make_pbr("M_Zone_Esports_Indigo", "#44447F", roughness=0.66)
    MAT["zone_gym"] = make_pbr("M_Zone_Gym_Terracotta", "#B76E48", roughness=0.72)
    MAT["rug"] = make_pbr("M_Rug_WarmGrey", "#7E7C73", roughness=0.92)
    MAT["rug_dark"] = make_pbr("M_Rug_Dark", "#3A3C3D", roughness=0.92)
    MAT["felt"] = make_pbr("M_PoolTable_Felt", "#1E7A55", roughness=0.92, coat=0.05)
    MAT["cushion"] = make_pbr("M_Sofa_Fabric", "#C6B9A3", roughness=0.93)
    MAT["cushion_dark"] = make_pbr("M_Chair_Fabric_Dark", "#383A39", roughness=0.9)
    MAT["leather"] = make_pbr("M_Cinema_Leather", "#3E2E2D", roughness=0.5)
    MAT["ceiling"] = make_pbr("M_Ceiling_Plaster", "#ECE8DE", roughness=0.7)

    MAT["emit_warm"] = make_pbr("M_LED_Warm", "#FFD8A4", roughness=0.3,
                                emission="#FFBD73", emission_strength=5.5)
    MAT["emit_soft_warm"] = make_pbr("M_LED_SoftWarm", "#FFE7C7", roughness=0.4,
                                     emission="#FFD9A8", emission_strength=2.5)
    MAT["emit_cyan"] = make_pbr("M_LED_Cyan", "#64F5FF", roughness=0.25,
                                emission="#24D7F2", emission_strength=7.0)
    MAT["emit_magenta"] = make_pbr("M_LED_Magenta", "#FF66D8", roughness=0.25,
                                   emission="#F529B7", emission_strength=7.0)
    MAT["emit_violet"] = make_pbr("M_LED_Violet", "#8E8CFF", roughness=0.25,
                                  emission="#675AF7", emission_strength=6.0)
    MAT["emit_cool"] = make_pbr("M_LED_CoolWhite", "#E9FAFF", roughness=0.3,
                                emission="#C8F5FF", emission_strength=4.0)
    MAT["screen"] = make_pbr("M_Screen", "#526B72", roughness=0.18,
                             emission="#8CB9C7", emission_strength=1.4)
    MAT["screen_game"] = make_pbr("M_Screen_Game", "#25364E", roughness=0.2,
                                  emission="#3A62B8", emission_strength=2.2)
    MAT["label"] = make_pbr("M_Label_WarmWhite", "#F4EFE4", roughness=0.48,
                            emission="#FFF8E9", emission_strength=0.35)
    MAT["label_dark"] = make_pbr("M_Label_Charcoal", "#242827", roughness=0.5,
                                 emission="#1C1E1D", emission_strength=0.05)

    MAT["pot"] = make_pbr("M_Planter_Concrete", "#918C82", roughness=0.76)
    MAT["soil"] = make_pbr("M_Soil", "#342D25", roughness=0.95)
    MAT["black_net"] = make_pbr("M_Net_White", "#E2E0D8", roughness=0.8)
    MAT["art"] = make_pbr("M_Art_Canvas", "#7A8E88", roughness=0.75)
    MAT["mirror_dark"] = make_pbr("M_Mirror_Smoked", "#84918D", roughness=0.07,
                                  metallic=0.95)
    MAT["accent_mustard"] = make_pbr("M_Accent_Mustard", "#C7A250", roughness=0.85)
    MAT["accent_blue"] = make_pbr("M_Accent_Blue", "#4B6E87", roughness=0.8)
    MAT["ceramic"] = make_pbr("M_Ceramic", "#EDE9DE", roughness=0.25, coat=0.2)
    MAT["ball_red"] = make_pbr("M_Ball_Red", "#B83D32", roughness=0.18, coat=0.5)
    MAT["ball_yellow"] = make_pbr("M_Ball_Yellow", "#D7A632", roughness=0.18, coat=0.5)
    MAT["ball_blue"] = make_pbr("M_Ball_Blue", "#2B5E94", roughness=0.18, coat=0.5)
    MAT["ball_white"] = make_pbr("M_Ball_White", "#EFEBDE", roughness=0.18, coat=0.5)
    MAT["screen_cyan"] = make_pbr("M_Screen_Cyan", "#1C3944", roughness=0.18,
                                  emission="#2AC7D9", emission_strength=2.8)
    MAT["screen_magenta"] = make_pbr("M_Screen_Magenta", "#3F2138", roughness=0.18,
                                     emission="#E143B5", emission_strength=2.4)
    MAT["books"] = make_pbr("M_Books", "#B0A38C", roughness=0.8)
    MAT["lavender"] = make_pbr("M_Lavender", "#6D6290", roughness=0.82)
    MAT["flower_white"] = make_pbr("M_Flower_White", "#E8E2D0", roughness=0.75)
    MAT["ember"] = make_pbr("M_Fire_Ember", "#FF7B32", roughness=0.5,
                            emission="#FF5A18", emission_strength=3.2)

    for key in ("water", "water_indoor", "glass", "glass_dark", "glass_white"):
        mat = MAT[key]
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = 'BLENDED'
        if hasattr(mat, "use_transparent_shadow"):
            mat.use_transparent_shadow = True


# =============================================================================
# 04. 场地、室外泳池、篮球场
# =============================================================================

def build_site():
    site = COLL["site"]

    # 草坪被泳池开洞，用四块草皮围合出真实的下沉泳池。
    lawn_specs = [
        ("Lawn_West", (SITE_X0 + POOL_X0) / 2, (SITE_Y0 + SITE_Y1) / 2,
         (POOL_X0 - SITE_X0), (SITE_Y1 - SITE_Y0)),
        ("Lawn_East", (POOL_X1 + SITE_X1) / 2, (SITE_Y0 + SITE_Y1) / 2,
         (SITE_X1 - POOL_X1), (SITE_Y1 - SITE_Y0)),
        ("Lawn_South", (POOL_X0 + POOL_X1) / 2, (SITE_Y0 + POOL_Y0) / 2,
         (POOL_X1 - POOL_X0), (POOL_Y0 - SITE_Y0)),
        ("Lawn_North", (POOL_X0 + POOL_X1) / 2, (POOL_Y1 + SITE_Y1) / 2,
         (POOL_X1 - POOL_X0), (SITE_Y1 - POOL_Y1)),
    ]
    for name, cx, cy, sx, sy in lawn_specs:
        add_box(name, (cx, cy, SITE_Z - 0.15), (sx, sy, 0.30),
                MAT["grass"], site)

    # 别墅基础与入口平台
    add_box("Foundation_Plinth", (0, 0, 0.10), (VILLA_W + 0.5, VILLA_D + 0.5, 0.28),
            MAT["concrete"], COLL["shell_body"], bevel=0.025)
    add_box("Entry_Terrace", (-1.7, -8.65, 0.075), (8.6, 2.5, 0.15),
            MAT["stone"], site, bevel=0.02)
    add_box("Entry_Terrace_Lower", (-1.7, -10.25, 0.035), (7.2, 1.25, 0.07),
            MAT["stone_dark"], site)

    # 入口步道
    for i in range(7):
        add_box("Entry_Step_%02d" % (i + 1),
                (-1.7, -10.9 - i * 1.15, 0.025), (2.7, 0.82, 0.05),
                MAT["concrete"], site, bevel=0.01)
    add_box("Entry_Step_00", (-1.7, -9.80, 0.045), (3.1, 0.52, 0.09),
            MAT["concrete"], site, bevel=0.012)

    # 草皮边缘的石材收边
    add_box("Terrace_Edge_West", (-10.4, -9.8, 0.04), (0.4, 5.2, 0.08),
            MAT["stone_dark"], site)
    add_box("Terrace_Edge_East", (7.0, -9.5, 0.04), (0.3, 4.4, 0.08),
            MAT["stone_dark"], site)

    # 树池/花池
    planter_specs = [
        (-12.8, -6.7, 3.0, 1.4),
        (-13.2, 7.8, 2.4, 1.3),
        (-6.8, -12.1, 3.2, 1.2),
    ]
    for i, (x, y, sx, sy) in enumerate(planter_specs):
        add_box("Planter_Base_%02d" % i, (x, y, 0.14), (sx, sy, 0.28),
                MAT["concrete"], site, bevel=0.025)
        add_box("Planter_Soil_%02d" % i, (x, y, 0.285), (sx - 0.16, sy - 0.16, 0.04),
                MAT["soil"], site)

    # 入口两侧低矮绿篱
    add_box("Entry_Hedge_L", (-6.5, -10.0, 0.42), (3.8, 0.55, 0.84),
            MAT["hedge"], site, bevel=0.08)
    add_box("Entry_Hedge_R", (3.0, -10.0, 0.42), (3.2, 0.55, 0.84),
            MAT["hedge"], site, bevel=0.08)


def build_outdoor_pool():
    pool = COLL["pool"]
    px0, px1, py0, py1 = POOL_X0, POOL_X1, POOL_Y0, POOL_Y1
    cx, cy = (px0 + px1) / 2, (py0 + py1) / 2
    deck_top = DECK_Z

    # 泳池周围石材平台（避开池洞）
    deck_specs = [
        ("Pool_Deck_West", (10.0 + px0) / 2, (py0 + py1) / 2,
         px0 - 10.0, 9.8),
        ("Pool_Deck_East", (px1 + 23.2) / 2, (py0 + py1) / 2,
         23.2 - px1, 9.8),
        ("Pool_Deck_South", (px0 + px1) / 2, (-8.2 + py0) / 2,
         px1 - px0, py0 + 8.2),
        ("Pool_Deck_North", (px0 + px1) / 2, (py1 + 1.8) / 2,
         px1 - px0, 1.8 - py1),
    ]
    for name, x, y, sx, sy in deck_specs:
        add_box(name, (x, y, deck_top / 2), (sx, sy, deck_top),
                MAT["stone"], pool, bevel=0.012)

    # 平台范围：x 10.0..23.2 / y -8.2..1.8，中间留出泳池洞口。

    # 池壁、池底
    wall_t = 0.16
    add_box("Pool_Basement", (cx, cy, -1.23), (px1 - px0, py1 - py0, 0.12),
            MAT["stone_dark"], pool)
    add_box("Pool_Floor", (cx, cy, -1.15), (px1 - px0 - 0.1, py1 - py0 - 0.1, 0.07),
            MAT["pool_tile_floor"], pool)
    add_box("Pool_Wall_W", (px0 + wall_t / 2, cy, -0.51),
            (wall_t, py1 - py0, 1.30), MAT["pool_tile"], pool)
    add_box("Pool_Wall_E", (px1 - wall_t / 2, cy, -0.51),
            (wall_t, py1 - py0, 1.30), MAT["pool_tile"], pool)
    add_box("Pool_Wall_S", (cx, py0 + wall_t / 2, -0.51),
            (px1 - px0 - 2 * wall_t, wall_t, 1.30), MAT["pool_tile"], pool)
    add_box("Pool_Wall_N", (cx, py1 - wall_t / 2, -0.51),
            (px1 - px0 - 2 * wall_t, wall_t, 1.30), MAT["pool_tile"], pool)

    # 池底瓷砖分隔带
    for i in range(1, 8):
        x = px0 + i * (px1 - px0) / 8
        add_box("Pool_Floor_Line_%02d" % i, (x, cy, -1.108),
                (0.026, py1 - py0 - 0.3, 0.012), MAT["pool_tile_light"], pool)

    # 水面
    add_box("Pool_Water_Surface", (cx, cy, WATER_Z),
            (px1 - px0 - 0.18, py1 - py0 - 0.18, 0.026),
            MAT["water"], pool)

    # 外侧石材压顶
    coping_w = 0.38
    add_box("Pool_Coping_S", (cx, py0 + 0.02, deck_top + 0.035),
            (px1 - px0 + 0.1, coping_w, 0.07), MAT["stone"], pool, bevel=0.012)
    add_box("Pool_Coping_N", (cx, py1 - 0.02, deck_top + 0.035),
            (px1 - px0 + 0.1, coping_w, 0.07), MAT["stone"], pool, bevel=0.012)
    add_box("Pool_Coping_W", (px0 + 0.02, cy, deck_top + 0.035),
            (coping_w, py1 - py0 - 2 * coping_w, 0.07),
            MAT["stone"], pool, bevel=0.012)
    add_box("Pool_Coping_E", (px1 - 0.02, cy, deck_top + 0.035),
            (coping_w, py1 - py0 - 2 * coping_w, 0.07),
            MAT["stone"], pool, bevel=0.012)

    # 入水台阶（浅水区）
    for i in range(3):
        add_box("Pool_Step_%02d" % (i + 1),
                (px0 + 1.05, -3.55, -0.28 - i * 0.27),
                (1.8 - i * 0.25, 2.5, 0.26), MAT["stone"], pool, bevel=0.012)

    # 水下灯
    for i, x in enumerate((px0 + 1.5, cx, px1 - 1.5)):
        add_box("Pool_Light_%02d" % i, (x, py0 + 0.19, -0.55),
                (0.38, 0.035, 0.14), MAT["emit_cyan"], pool)
        light_point("Pool_Underwater_Light_%02d" % i,
                    (x, py0 + 0.45, -0.36), 42.0, (0.1, 0.78, 1.0), 0.35)

    # 不锈钢泳池扶梯
    for i, x in enumerate((px1 - 0.9, px1 - 0.35)):
        add_cylinder("Pool_Ladder_Rail_%02d" % i, (x, py1 - 0.55, 0.15),
                     0.025, 1.45, MAT["metal"], pool, segments=12)
    for i, z in enumerate((0.0, -0.35)):
        add_cylinder("Pool_Ladder_Rung_%02d" % i, (px1 - 0.625, py1 - 0.55, z),
                     0.021, 0.6, MAT["metal"], pool, segments=12,
                     rot=(0, radians(90), 0))

    # 两张日光躺椅（放在东侧平台上）
    add_lounger("Pool_Lounger_01", (21.55, -4.45), pool, rot_z=radians(90))
    add_lounger("Pool_Lounger_02", (21.55, -2.55), pool, rot_z=radians(90))
    add_box("Pool_Side_Table", (22.25, -3.5, 0.42), (0.48, 0.48, 0.42),
            MAT["wood_dark"], pool, bevel=0.025)

    # 边角绿植
    add_planter_box("Pool_Planter_01", (11.35, -7.45), pool, 0.8, 0.8, 0.72)
    add_planter_box("Pool_Planter_02", (22.35, -7.3), pool, 0.9, 0.9, 0.8)

    # 东侧木铺装（泳池边的暖色休憩平台）
    plank_x0, plank_x1 = 20.72, 23.05
    n_planks = 10
    gap = 0.035
    plank_w = ((plank_x1 - plank_x0) - gap * (n_planks - 1)) / n_planks
    for i in range(n_planks):
        x = plank_x0 + plank_w / 2 + i * (plank_w + gap)
        add_box("Pool_WoodDeck_Plank_%02d" % i, (x, -3.25, 0.165),
                (plank_w, 9.2, 0.035), MAT["wood"], pool, bevel=0.006)
    add_box("Pool_WoodDeck_Edge", (20.68, -3.25, 0.18), (0.05, 9.2, 0.07),
            MAT["dark"], pool)

    # 从泳池平台通向篮球场的一小段石材汀步
    for i in range(3):
        add_box("Pool_Court_Paver_%d" % i, (21.15 + i * 0.95, -8.8, 0.035),
                (0.78, 0.78, 0.06), MAT["concrete"], pool, bevel=0.01)

    # 小尺度尺寸标注牌（可选，非常低调）
    add_text("Pool_Dimension_Text", "8 m x 4 m  /  OUTDOOR POOL",
             (16.4, -6.85, deck_top + 0.055), 0.17, MAT["label"], pool,
             font=FONT_EN)


def add_lounger(name, xy, coll, rot_z=0.0):
    x, y = xy
    root = add_box(name + "_Base", (x, y, 0.34), (2.0, 0.75, 0.16),
                   MAT["wood_light"], coll, rot=(0, 0, rot_z), bevel=0.04)
    # 用旋转后的局部方向放置坐垫和靠背
    ca, sa = cos(rot_z), sin(rot_z)
    def lx(local_x, local_y):
        return (x + local_x * ca - local_y * sa,
                y + local_x * sa + local_y * ca)

    c = lx(0.0, 0.0)
    add_box(name + "_Cushion", (c[0], c[1], 0.45), (1.55, 0.62, 0.10),
            MAT["cushion"], coll, rot=(0, 0, rot_z), bevel=0.04)
    back_center = lx(-0.58, 0.0)
    add_box(name + "_Back", (back_center[0], back_center[1], 0.73),
            (0.62, 0.68, 0.48), MAT["cushion"], coll,
            rot=(radians(-18), 0, rot_z), bevel=0.045)
    for sx in (-0.82, 0.82):
        leg = lx(sx, 0.0)
        add_box(name + "_Leg_%s" % ("L" if sx < 0 else "R"),
                (leg[0], leg[1], 0.18), (0.07, 0.62, 0.32),
                MAT["dark"], coll, rot=(0, 0, rot_z))


def add_planter_box(name, xy, coll, sx, sy, h):
    x, y = xy
    add_box(name + "_Pot", (x, y, SITE_Z + h / 2), (sx, sy, h),
            MAT["pot"], coll, bevel=0.035)
    add_box(name + "_Soil", (x, y, SITE_Z + h + 0.015), (sx - 0.12, sy - 0.12, 0.04),
            MAT["soil"], coll)
    # 简约观赏草
    for i in range(5):
        ox = RNG.uniform(-sx * 0.28, sx * 0.28)
        oy = RNG.uniform(-sy * 0.28, sy * 0.28)
        h2 = RNG.uniform(0.35, 0.8)
        add_cone("Plant_Grass_%s_%02d" % (name, i),
                 (x + ox, y + oy, SITE_Z + h + h2 / 2),
                 0.035, 0.16, h2, MAT["leaf"], coll, segments=5)


def add_cone(name, loc, r_bottom, r_top, depth, mat, coll, segments=10,
             rot=(0, 0, 0)):
    data = bpy.data.meshes.new(name + "_mesh")
    verts = []
    for z, r in ((-depth / 2, r_bottom), (depth / 2, r_top)):
        for i in range(segments):
            a = 2 * pi * i / segments
            verts.append((r * cos(a), r * sin(a), z))
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, segments + j, segments + i))
    faces.append(tuple(reversed(range(segments))))
    faces.append(tuple(range(segments, segments * 2)))
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    data.materials.append(mat)
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def build_court():
    court = COLL["court"]
    cx = (COURT_X0 + COURT_X1) / 2
    cy = (COURT_Y0 + COURT_Y1) / 2
    cw, cd = COURT_X1 - COURT_X0, COURT_Y1 - COURT_Y0
    top = COURT_Z

    add_box("Court_Concrete_Base", (cx, cy, 0.055), (cw + 0.5, cd + 0.5, 0.11),
            MAT["stone_dark"], court, bevel=0.025)
    add_box("Court_Surface", (cx, cy, top), (cw, cd, 0.035),
            MAT["court"], court, bevel=0.01)

    line_z = top + 0.038
    line_w = 0.065
    x0, x1 = COURT_X0 + 0.18, COURT_X1 - 0.18
    y0, y1 = COURT_Y0 + 0.18, COURT_Y1 - 0.18

    # 边界线
    add_line_2d("Court_Line_S", (x0, y0), (x1, y0), line_w, line_z, MAT["line"], court)
    add_line_2d("Court_Line_N", (x0, y1), (x1, y1), line_w, line_z, MAT["line"], court)
    add_line_2d("Court_Line_W", (x0, y0), (x0, y1), line_w, line_z, MAT["line"], court)
    add_line_2d("Court_Line_E", (x1, y0), (x1, y1), line_w, line_z, MAT["line"], court)

    # 半场线 / 中圈（只取进入场内的半圆）
    mid_y = y0
    add_arc_ribbon("Court_HalfCircle", (cx, mid_y), 1.8, line_w, line_z,
                   0, pi, MAT["line"], court, steps=48)

    # 三秒区（钥匙区）与罚球线：篮筐在北侧，因此钥匙区从北底线向南延伸。
    key_w = 4.9
    key_y0 = y1 - 5.8
    key_y1 = y1
    kx0, kx1 = cx - key_w / 2, cx + key_w / 2
    add_box("Court_Key_Fill", (cx, (key_y0 + key_y1) / 2, top + 0.018),
            (key_w, key_y1 - key_y0, 0.008), MAT["court_key"], court)
    add_line_2d("Court_Key_W", (kx0, key_y0), (kx0, key_y1), line_w, line_z, MAT["line"], court)
    add_line_2d("Court_Key_E", (kx1, key_y0), (kx1, key_y1), line_w, line_z, MAT["line"], court)
    add_line_2d("Court_FreeThrow_Line", (kx0, key_y0), (kx1, key_y0), line_w, line_z,
                MAT["line"], court)
    add_arc_ribbon("Court_FreeThrow_Circle", (cx, key_y0), 1.8, line_w, line_z,
                   0, 2 * pi, MAT["line"], court, steps=64, closed=True)

    # 篮筐坐标 / 三分线
    hoop_y = y1 - 1.35
    hoop_x = cx
    hoop_z = 3.05
    # 限制区半圆
    add_arc_ribbon("Court_RestrictedArea", (hoop_x, hoop_y), 1.25, line_w,
                   line_z, pi, 2 * pi, MAT["line"], court, steps=32)

    three_r = 6.75
    three_x = 6.4
    dy = math.sqrt(max(0.0, three_r * three_r - three_x * three_x))
    arc_y = hoop_y - dy
    for sign, nm in ((-1, "W"), (1, "E")):
        add_line_2d("Court_ThreeCorner_%s" % nm,
                    (hoop_x + sign * three_x, y1),
                    (hoop_x + sign * three_x, arc_y),
                    line_w, line_z, MAT["line"], court)
    a_left = atan2(arc_y - hoop_y, -three_x)
    a_right = atan2(arc_y - hoop_y, three_x)
    add_arc_ribbon("Court_ThreePointArc", (hoop_x, hoop_y), three_r, line_w,
                   line_z, a_left, a_right, MAT["line"], court, steps=80)

    # 篮架：立柱在北侧底线外，悬臂伸向场内。
    pole_y = y1 + 0.55
    board_y = hoop_y + 0.30
    add_cylinder("Basketball_Pole", (cx, pole_y, 1.92), 0.09, 3.55,
                 MAT["dark"], court, segments=20)
    add_box("Basketball_Pole_Base", (cx, pole_y, 0.20), (0.9, 0.9, 0.22),
            MAT["dark_matte"], court)
    arm_len = max(0.4, pole_y - board_y + 0.15)
    add_box("Basketball_Arm", (cx, (pole_y + board_y) / 2, 3.7),
            (0.24, arm_len, 0.13), MAT["dark"], court, bevel=0.02)
    add_box("Basketball_Backboard", (cx, board_y, 3.45), (1.85, 0.055, 1.08),
            MAT["glass_white"], court, bevel=0.008)
    # 篮板正面（朝南）的橙色边框与瞄准框
    face_y = board_y - 0.036
    add_box("Basketball_BoardFrame_B", (cx, face_y, 2.91),
            (1.86, 0.012, 0.05), MAT["orange"], court)
    add_box("Basketball_BoardFrame_T", (cx, face_y, 3.99),
            (1.86, 0.012, 0.05), MAT["orange"], court)
    add_box("Basketball_BoardFrame_L", (cx - 0.91, face_y, 3.45),
            (0.05, 0.012, 1.08), MAT["orange"], court)
    add_box("Basketball_BoardFrame_R", (cx + 0.91, face_y, 3.45),
            (0.05, 0.012, 1.08), MAT["orange"], court)
    add_box("Basketball_AimBox_Bottom", (cx, face_y, 3.20),
            (0.62, 0.012, 0.026), MAT["orange"], court)
    add_box("Basketball_AimBox_Top", (cx, face_y, 3.58),
            (0.62, 0.012, 0.026), MAT["orange"], court)
    add_box("Basketball_AimBox_L", (cx - 0.30, face_y, 3.39),
            (0.026, 0.012, 0.38), MAT["orange"], court)
    add_box("Basketball_AimBox_R", (cx + 0.30, face_y, 3.39),
            (0.026, 0.012, 0.38), MAT["orange"], court)

    # 篮筐圆环（曲线倒角）
    rim_pts = [(cx + 0.23 * cos(2 * pi * i / 48),
                hoop_y + 0.23 * sin(2 * pi * i / 48), hoop_z)
               for i in range(48)]
    add_curve_tube("Basketball_Rim", rim_pts, 0.018, MAT["orange"], court, cyclic=True)
    # 篮网：8 根向下收拢的细线
    for i in range(8):
        a = 2 * pi * i / 8
        net_top = (cx + 0.22 * cos(a), hoop_y + 0.22 * sin(a), hoop_z - 0.02)
        net_bot = (cx + 0.12 * cos(a), hoop_y + 0.12 * sin(a), hoop_z - 0.43)
        add_curve_tube("Basketball_Net_%02d" % i, [net_top, net_bot], 0.006,
                       MAT["black_net"], court)
    for i in range(3):
        z = hoop_z - 0.12 - i * 0.12
        r = 0.22 - (0.10 * (i + 1) / 3)
        circle = [(cx + r * cos(2 * pi * j / 24),
                   hoop_y + r * sin(2 * pi * j / 24), z) for j in range(24)]
        add_curve_tube("Basketball_NetRing_%02d" % i, circle, 0.0045,
                       MAT["black_net"], court, cyclic=True)

    # 篮球
    add_sphere("Basketball_Ball", (cx - 3.5, -0.8, top + 0.16), 0.14,
               MAT["orange"], court, segments=24, rings=16)
    add_sphere("Basketball_Ball_Line", (cx - 3.5, -0.8, top + 0.16), 0.141,
               MAT["dark_matte"], court, scale=(1.0, 0.08, 1.0),
               segments=24, rings=12)

    # 场边观赛长凳
    add_box("Court_Bench_Seat", (cx, -10.0, 0.47), (5.0, 0.52, 0.10),
            MAT["wood"], court, bevel=0.025)
    for sx in (-2.0, 0.0, 2.0):
        add_box("Court_Bench_Leg_%s" % sx, (cx + sx, -10.0, 0.23),
                (0.08, 0.42, 0.42), MAT["dark"], court)
    add_box("Court_Bench_Back", (cx, -10.28, 0.82), (5.0, 0.09, 0.55),
            MAT["wood"], court, rot=(radians(-8), 0, 0), bevel=0.018)

    add_text("Court_Floor_Text", "HALF  COURT", (cx, -5.2, top + 0.045),
             0.48, MAT["label"], court, font=FONT_EN)


# =============================================================================
# 05. 建筑外壳（墙体、玻璃幕墙、屋顶、楼梯）
# =============================================================================

def wall_y(name, x0, x1, z0, z1, mat=None, y_center=None, thickness=WALL_T,
           bevel=0.008):
    if x1 <= x0 or z1 <= z0:
        return None
    yc = Y0 + WALL_T / 2 if y_center is None else y_center
    return add_box(name, ((x0 + x1) / 2, yc, (z0 + z1) / 2),
                   (x1 - x0, thickness, z1 - z0), mat or MAT["wall"],
                   COLL["shell_body"], bevel=bevel)


def wall_x(name, y0, y1, z0, z1, mat=None, x_center=None, thickness=WALL_T,
           bevel=0.008):
    if y1 <= y0 or z1 <= z0:
        return None
    xc = X1 - WALL_T / 2 if x_center is None else x_center
    return add_box(name, (xc, (y0 + y1) / 2, (z0 + z1) / 2),
                   (thickness, y1 - y0, z1 - z0), mat or MAT["wall"],
                   COLL["shell_body"], bevel=bevel)


def glazing_y(prefix, x0, x1, z0, z1, y, divisions=4,
              transoms=(), glass_mat=None, frame_mat=None,
              glass_coll=None, frame_coll=None):
    """在 Y 向立面（南/北）做整面幕墙，带黑色金属竖梃与横梃。"""
    glass_mat = glass_mat or MAT["glass"]
    frame_mat = frame_mat or MAT["dark"]
    gcoll = glass_coll or COLL["shell_glass"]
    bcoll = frame_coll or COLL["shell_body"]
    xs = [x0 + (x1 - x0) * i / divisions for i in range(divisions + 1)]
    zs = [z0] + sorted([t for t in transoms if z0 < t < z1]) + [z1]
    fw = 0.075
    glass_depth = 0.018
    frame_depth = 0.10

    for r in range(len(zs) - 1):
        for c in range(divisions):
            gx0, gx1 = xs[c] + 0.012, xs[c + 1] - 0.012
            gz0, gz1 = zs[r] + 0.012, zs[r + 1] - 0.012
            add_box("%s_Glass_%d_%d" % (prefix, r, c),
                    ((gx0 + gx1) / 2, y, (gz0 + gz1) / 2),
                    (gx1 - gx0, glass_depth, gz1 - gz0),
                    glass_mat, gcoll)

    # 外框与竖梃
    add_box(prefix + "_Frame_Bottom",
            ((x0 + x1) / 2, y - 0.003, z0 + fw / 2),
            (x1 - x0 + 0.06, frame_depth, fw), frame_mat, bcoll, bevel=0.006)
    add_box(prefix + "_Frame_Top",
            ((x0 + x1) / 2, y - 0.003, z1 - fw / 2),
            (x1 - x0 + 0.06, frame_depth, fw), frame_mat, bcoll, bevel=0.006)
    for x in xs:
        add_box("%s_Mullion_%s" % (prefix, ("%.2f" % x).replace(".", "_")),
                (x, y - 0.003, (z0 + z1) / 2),
                (fw, frame_depth, z1 - z0), frame_mat, bcoll, bevel=0.004)
    for z in zs[1:-1]:
        add_box("%s_Transom_%s" % (prefix, ("%.2f" % z).replace(".", "_")),
                ((x0 + x1) / 2, y - 0.003, z),
                (x1 - x0, frame_depth, 0.06), frame_mat, bcoll, bevel=0.004)


def glazing_x(prefix, y0, y1, z0, z1, x, divisions=4,
              transoms=(), glass_mat=None, frame_mat=None,
              glass_coll=None, frame_coll=None):
    """在 X 向立面（东/西）做整面幕墙。"""
    glass_mat = glass_mat or MAT["glass"]
    frame_mat = frame_mat or MAT["dark"]
    gcoll = glass_coll or COLL["shell_glass"]
    bcoll = frame_coll or COLL["shell_body"]
    ys = [y0 + (y1 - y0) * i / divisions for i in range(divisions + 1)]
    zs = [z0] + sorted([t for t in transoms if z0 < t < z1]) + [z1]
    fw = 0.075
    for r in range(len(zs) - 1):
        for c in range(divisions):
            gy0, gy1 = ys[c] + 0.012, ys[c + 1] - 0.012
            gz0, gz1 = zs[r] + 0.012, zs[r + 1] - 0.012
            add_box("%s_Glass_%d_%d" % (prefix, r, c),
                    (x, (gy0 + gy1) / 2, (gz0 + gz1) / 2),
                    (0.018, gy1 - gy0, gz1 - gz0),
                    glass_mat, gcoll)
    add_box(prefix + "_Frame_Bottom",
            (x + 0.003, (y0 + y1) / 2, z0 + fw / 2),
            (0.10, y1 - y0 + 0.06, fw), frame_mat, bcoll, bevel=0.006)
    add_box(prefix + "_Frame_Top",
            (x + 0.003, (y0 + y1) / 2, z1 - fw / 2),
            (0.10, y1 - y0 + 0.06, fw), frame_mat, bcoll, bevel=0.006)
    for y in ys:
        add_box("%s_Mullion_%s" % (prefix, ("%.2f" % y).replace(".", "_")),
                (x + 0.003, y, (z0 + z1) / 2),
                (0.10, fw, z1 - z0), frame_mat, bcoll, bevel=0.004)
    for z in zs[1:-1]:
        add_box("%s_Transom_%s" % (prefix, ("%.2f" % z).replace(".", "_")),
                (x + 0.003, (y0 + y1) / 2, z),
                (0.10, y1 - y0, 0.06), frame_mat, bcoll, bevel=0.004)


def build_villa_shell():
    body = COLL["shell_body"]
    glass_coll = COLL["shell_glass"]
    roof = COLL["shell_roof"]
    stair = COLL["shell_stair"]

    # 基础、楼板、二层楼板（挑高客厅与楼梯上方留洞）
    add_box("F1_Structural_Slab", (0, 0, 0.11), (VILLA_W, VILLA_D, 0.22),
            MAT["concrete"], body, bevel=0.018)
    add_box("F1_Finished_Floor", (0, 0, 0.225), (XIN1 - XIN0, YIN1 - YIN0, 0.025),
            MAT["marble"], body)

    slab_z = (3.20 + F2_Z) / 2
    slab_h = F2_Z - 3.20
    add_box("F2_Slab_Rear", (0, (1.32 + YIN1) / 2, slab_z),
            (XIN1 - XIN0, YIN1 - 1.32, slab_h), MAT["ceiling"], body, bevel=0.01)
    add_box("F2_Slab_East", ((0.85 + XIN1) / 2, (-7.3 + 1.32) / 2, slab_z),
            (XIN1 - 0.85, 1.32 + 7.3, slab_h), MAT["ceiling"], body, bevel=0.01)
    add_box("F2_Slab_Landing", ((-1.2 + 0.85) / 2, (-1.30 + 1.32) / 2, slab_z),
            (0.85 + 1.2, 1.32 + 1.30, slab_h), MAT["ceiling"], body, bevel=0.006)

    # 楼板收边（挑高客厅与楼梯洞口）
    add_box("F2_Edge_Rear", (0.0, 1.29, 3.30), (XIN1 - XIN0, 0.10, 0.28),
            MAT["dark_matte"], body)
    add_box("F2_Edge_Landing", (-0.18, -1.34, 3.30), (2.2, 0.10, 0.28),
            MAT["dark_matte"], body)
    add_box("F2_Edge_Gym", (0.82, -3.0, 3.30), (0.10, 8.6, 0.28),
            MAT["dark_matte"], body)

    # ======================= 南立面 / 主入口 =========================
    wall_y("S_Pier_Corner_W", X0, -9.55, PLINTH_TOP, ROOF_Z, MAT["wall"])
    wall_y("S_Pier_LivingEntry", -1.55, -0.75, PLINTH_TOP, ROOF_Z, MAT["wall"])
    wall_y("S_Pier_EntryBilliard", 1.05, 1.35, PLINTH_TOP, ROOF_Z, MAT["wall"])
    wall_y("S_Pier_Corner_E", 8.70, X1, PLINTH_TOP, ROOF_Z, MAT["wall"])
    wall_y("S_Header", X0, X1, 6.25, ROOF_Z, MAT["wall"])
    wall_y("S_Sill_Living", -9.55, -1.55, PLINTH_TOP, 0.35, MAT["dark_matte"])
    wall_y("S_Sill_Billiard", 1.05, 8.70, PLINTH_TOP, 0.35, MAT["dark_matte"])
    wall_y("S_Spandrel_Billiard", 1.35, 8.70, 3.05, 3.55, MAT["wall"])
    wall_y("S_Entry_Header", -1.55, 1.35, 3.10, 6.25, MAT["wall"])

    # 幕墙
    glazing_y("S_Living_Curtain", -9.40, -1.70, 0.35, 6.20, Y0 + 0.10,
              divisions=4, transoms=(3.40,))
    glazing_y("S_Billiard_Glazing", 1.45, 8.60, 0.35, 3.05, Y0 + 0.10,
              divisions=4)
    glazing_y("S_Gym_Glazing", 1.45, 8.60, 3.65, 6.20, Y0 + 0.10,
              divisions=4, transoms=(5.00,))

    # 入口门（深色玻璃旋转门）
    add_box("S_EntryDoor_Glass", (0.15, Y0 + 0.09, 1.63),
            (1.45, 0.035, 2.82), MAT["glass_dark"], glass_coll)
    add_box("S_EntryDoor_Frame_T", (0.15, Y0 + 0.05, 3.06),
            (1.60, 0.11, 0.085), MAT["dark"], body, bevel=0.004)
    add_box("S_EntryDoor_Frame_L", (-0.62, Y0 + 0.05, 1.62),
            (0.075, 0.11, 2.95), MAT["dark"], body, bevel=0.004)
    add_box("S_EntryDoor_Frame_R", (0.92, Y0 + 0.05, 1.62),
            (0.075, 0.11, 2.95), MAT["dark"], body, bevel=0.004)
    add_cylinder("S_EntryDoor_Handle", (-0.25, Y0 - 0.01, 1.35), 0.022, 0.85,
                 MAT["bronze"], body, segments=12)

    # 入口挑檐 + 檐下灯带
    add_box("S_Entry_Canopy", (-0.15, -8.55, 3.29), (4.7, 2.5, 0.20),
            MAT["wood_dark"], body, bevel=0.025)
    add_box("S_Entry_Canopy_Underside", (-0.15, -8.55, 3.175), (4.55, 2.35, 0.035),
            MAT["wood_light"], body, bevel=0.01)
    add_box("S_Entry_Canopy_LED", (-0.15, -9.45, 3.17), (3.6, 0.05, 0.028),
            MAT["emit_warm"], body)
    # 檐下小体量门牌
    add_box("S_HousePlaque", (1.32, Y0 - 0.08, 1.92),
            (0.44, 0.04, 0.34), MAT["bronze"], body, bevel=0.012)
    add_text("S_HouseNumber", "20", (1.32, Y0 - 0.115, 1.92), 0.17,
             MAT["label"], body, rot=(radians(90), 0, 0),
             font=FONT_EN, extrude=0.003)
    # 檐下筒灯
    for x in (-1.4, 0.0, 1.4):
        add_cylinder("S_Canopy_Downlight_%s" % x, (x, -9.25, 3.145),
                     0.055, 0.025, MAT["emit_warm"], body, segments=16)

    # 入口上方的竖向木格栅（增加材质层次）
    for i in range(11):
        x = -1.40 + i * 0.26
        add_box("S_Entry_Facade_Fins_%02d" % i, (x, Y0 - 0.055, 4.72),
                (0.065, 0.12, 2.85), MAT["wood_dark"], body, bevel=0.006)

    # 外立面基座暗带
    wall_y("S_Base_Shadow", X0, X1, 0.20, 0.29, MAT["dark_matte"], thickness=0.215)

    # ======================= 东立面 =================================
    wall_x("E_Pier_S", -7.5, -6.70, PLINTH_TOP, ROOF_Z, MAT["wall"])
    wall_x("E_Pier_Mid", 0.80, 2.00, PLINTH_TOP, ROOF_Z, MAT["wall"])
    wall_x("E_Pier_N", 6.70, 7.5, PLINTH_TOP, ROOF_Z, MAT["wall"])
    wall_x("E_Header", Y0, Y1, 6.25, ROOF_Z, MAT["wall"])
    wall_x("E_Sill_S", -6.70, 0.80, PLINTH_TOP, 0.35, MAT["dark_matte"])
    wall_x("E_Sill_N", 2.00, 6.70, PLINTH_TOP, 0.35, MAT["dark_matte"])
    wall_x("E_Spandrel", -6.70, 6.70, 3.05, 3.65, MAT["wall"])
    glazing_x("E_Billiard_Glazing", -6.55, 0.65, 0.35, 3.05, X1 - 0.10,
              divisions=4, transoms=(1.75,))
    glazing_x("E_Pool_Glazing", 2.15, 6.55, 0.35, 2.95, X1 - 0.10,
              divisions=3)
    glazing_x("E_Gym_Glazing", -6.55, 0.65, 3.70, 6.20, X1 - 0.10,
              divisions=4, transoms=(5.00,))
    glazing_x("E_Esports_Glazing", 2.15, 6.55, 3.70, 6.05, X1 - 0.10,
              divisions=3, transoms=(4.90,))
    wall_x("E_Base_Shadow", Y0, Y1, 0.20, 0.29, MAT["dark_matte"], thickness=0.215)
    # 东立面中央的深色石材核心筒，打断全玻璃界面的单调感
    add_box("E_DarkStone_Core", (X1 + 0.015, 1.40, 3.42),
            (0.075, 1.16, 6.30), MAT["stone_dark"], body, bevel=0.006)
    for i in range(5):
        add_box("E_Core_BronzeFin_%02d" % i,
                (X1 + 0.075, 0.92 + i * 0.24, 3.42),
                (0.075, 0.05, 6.10), MAT["bronze"], body, bevel=0.004)
    # 南立面东南角的木格栅竖向收边
    for i in range(3):
        add_box("S_EastCorner_Fins_%02d" % i,
                (9.05 + i * 0.28, Y0 - 0.055, 3.30),
                (0.075, 0.14, 6.04), MAT["wood_dark"], body, bevel=0.005)

    # 东立面木格栅挑檐（在二层窗户上方形成深遮阳）
    for i in range(7):
        y = -6.3 + i * 2.0
        add_box("E_BriseSoleil_%02d" % i, (X1 + 0.18, y, 6.18),
                (0.95, 0.075, 0.13), MAT["wood_dark"], body, bevel=0.006)

    # ======================= 西立面 =================================
    wall_x("W_Pier_S", -7.5, -6.70, PLINTH_TOP, ROOF_Z, MAT["wall"],
           x_center=X0 + 0.10)
    wall_x("W_Pier_Mid", 0.55, 1.45, PLINTH_TOP, ROOF_Z, MAT["wall"],
           x_center=X0 + 0.10)
    wall_x("W_Pier_N", 6.70, 7.5, PLINTH_TOP, ROOF_Z, MAT["wall"],
           x_center=X0 + 0.10)
    wall_x("W_Header", Y0, Y1, 6.25, ROOF_Z, MAT["wall"], x_center=X0 + 0.10)
    wall_x("W_Sill", -6.70, 6.70, PLINTH_TOP, 0.35, MAT["dark_matte"],
           x_center=X0 + 0.10)
    wall_x("W_Spandrel", -6.70, 6.70, 3.05, 3.65, MAT["wall"],
           x_center=X0 + 0.10)
    glazing_x("W_Living_Glazing", -6.55, 0.40, 0.35, 6.20, X0 + 0.10,
              divisions=3, transoms=(3.40,))
    glazing_x("W_Pool_Glazing", 2.15, 6.55, 0.35, 2.95, X0 + 0.10,
              divisions=3)
    glazing_x("W_Theater_Glazing", 2.15, 6.55, 3.70, 6.05, X0 + 0.10,
              divisions=3, transoms=(4.90,))
    wall_x("W_Base_Shadow", Y0, Y1, 0.20, 0.29, MAT["dark_matte"],
           x_center=X0 + 0.10, thickness=0.215)

    # 西侧后部木百叶
    for i in range(9):
        y = 2.2 + i * 0.52
        add_box("W_WoodFins_%02d" % i, (X0 - 0.13, y, 4.88),
                (0.15, 0.075, 2.40), MAT["wood_dark"], body, bevel=0.006)

    # ======================= 北立面 =================================
    wall_y("N_Pier_W", X0, -9.40, PLINTH_TOP, ROOF_Z, MAT["wall"],
           y_center=Y1 - 0.10)
    wall_y("N_Pier_E", 8.80, X1, PLINTH_TOP, ROOF_Z, MAT["wall"],
           y_center=Y1 - 0.10)
    wall_y("N_Header", X0, X1, 6.25, ROOF_Z, MAT["wall"], y_center=Y1 - 0.10)
    wall_y("N_Sill", -9.40, 8.80, PLINTH_TOP, 0.35, MAT["dark_matte"],
           y_center=Y1 - 0.10)
    wall_y("N_Theater_Wall", -9.40, 1.10, 3.55, 6.25, MAT["wall"],
           y_center=Y1 - 0.10)
    wall_y("N_Spandrel", -9.40, 8.80, 3.05, 3.55, MAT["wall"],
           y_center=Y1 - 0.10)
    glazing_y("N_IndoorPool_Glazing", -9.20, 8.60, 0.35, 2.95, Y1 - 0.10,
              divisions=5)
    glazing_y("N_Esports_Glazing", 2.20, 8.55, 3.75, 6.05, Y1 - 0.10,
              divisions=3)
    wall_y("N_Base_Shadow", X0, X1, 0.20, 0.29, MAT["dark_matte"],
           y_center=Y1 - 0.10, thickness=0.215)

    # 北侧室内泳池外的木格栅遮阳
    for i in range(9):
        x = -9.0 + i * 2.2
        add_box("N_WoodFins_%02d" % i, (x, Y1 + 0.14, 2.35),
                (0.09, 0.23, 3.8), MAT["wood_dark"], body, bevel=0.006)

    # ======================= 平屋面 =================================
    # 屋顶在挑高客厅上方留出真实的天窗洞口，让室内获得自然顶光。
    roof_hole_x0, roof_hole_x1 = -7.7, -3.4
    roof_hole_y0, roof_hole_y1 = -4.4, -1.1
    roof_x0, roof_x1 = X0 - 0.30, X1 + 0.30
    roof_y0, roof_y1 = Y0 - 0.30, Y1 + 0.30
    add_box("Roof_Slab_West", ((roof_x0 + roof_hole_x0) / 2, 0, 6.50),
            (roof_hole_x0 - roof_x0, roof_y1 - roof_y0, 0.20),
            MAT["wall_white"], roof, bevel=0.018)
    add_box("Roof_Slab_East", ((roof_hole_x1 + roof_x1) / 2, 0, 6.50),
            (roof_x1 - roof_hole_x1, roof_y1 - roof_y0, 0.20),
            MAT["wall_white"], roof, bevel=0.018)
    add_box("Roof_Slab_North", ((roof_hole_x0 + roof_hole_x1) / 2,
                                 (roof_hole_y1 + roof_y1) / 2, 6.50),
            (roof_hole_x1 - roof_hole_x0, roof_y1 - roof_hole_y1, 0.20),
            MAT["wall_white"], roof, bevel=0.018)
    add_box("Roof_Slab_South", ((roof_hole_x0 + roof_hole_x1) / 2,
                                 (roof_y0 + roof_hole_y0) / 2, 6.50),
            (roof_hole_x1 - roof_hole_x0, roof_hole_y0 - roof_y0, 0.20),
            MAT["wall_white"], roof, bevel=0.018)
    # 客厅天窗：黑色金属翻边 + 三块超白玻璃
    add_box("Living_Skylight_Curb_W", (roof_hole_x0 - 0.06, (roof_hole_y0 + roof_hole_y1) / 2, 6.72),
            (0.12, roof_hole_y1 - roof_hole_y0 + 0.24, 0.24), MAT["dark"], roof, bevel=0.01)
    add_box("Living_Skylight_Curb_E", (roof_hole_x1 + 0.06, (roof_hole_y0 + roof_hole_y1) / 2, 6.72),
            (0.12, roof_hole_y1 - roof_hole_y0 + 0.24, 0.24), MAT["dark"], roof, bevel=0.01)
    add_box("Living_Skylight_Curb_S", ((roof_hole_x0 + roof_hole_x1) / 2, roof_hole_y0 - 0.06, 6.72),
            (roof_hole_x1 - roof_hole_x0 + 0.12, 0.12, 0.24), MAT["dark"], roof, bevel=0.01)
    add_box("Living_Skylight_Curb_N", ((roof_hole_x0 + roof_hole_x1) / 2, roof_hole_y1 + 0.06, 6.72),
            (roof_hole_x1 - roof_hole_x0 + 0.12, 0.12, 0.24), MAT["dark"], roof, bevel=0.01)
    for i in range(3):
        gx0 = roof_hole_x0 + i * (roof_hole_x1 - roof_hole_x0) / 3
        gx1 = roof_hole_x0 + (i + 1) * (roof_hole_x1 - roof_hole_x0) / 3
        add_box("Living_Skylight_Glass_%d" % i,
                ((gx0 + gx1) / 2, (roof_hole_y0 + roof_hole_y1) / 2, 6.83),
                (gx1 - gx0 - 0.04, roof_hole_y1 - roof_hole_y0 - 0.04, 0.025),
                MAT["glass"], roof)
        add_box("Living_Skylight_Mullion_%d" % i, (gx1, (roof_hole_y0 + roof_hole_y1) / 2, 6.83),
                (0.06, roof_hole_y1 - roof_hole_y0 + 0.1, 0.05), MAT["dark"], roof)
    add_box("Roof_Fascia_Dark", (0, 0, 6.375), (VILLA_W + 0.65, VILLA_D + 0.65, 0.08),
            MAT["dark_matte"], roof, bevel=0.006)
    # 女儿墙
    par_h = PARAPET_TOP - ROOF_Z
    add_box("Parapet_S", (0, Y0 - 0.30, ROOF_Z + par_h / 2),
            (VILLA_W + 0.6, 0.22, par_h), MAT["wall"], roof, bevel=0.01)
    add_box("Parapet_N", (0, Y1 + 0.30, ROOF_Z + par_h / 2),
            (VILLA_W + 0.6, 0.22, par_h), MAT["wall"], roof, bevel=0.01)
    add_box("Parapet_W", (X0 - 0.30, 0, ROOF_Z + par_h / 2),
            (0.22, VILLA_D + 0.6, par_h), MAT["wall"], roof, bevel=0.01)
    add_box("Parapet_E", (X1 + 0.30, 0, ROOF_Z + par_h / 2),
            (0.22, VILLA_D + 0.6, par_h), MAT["wall"], roof, bevel=0.01)
    # 金属压顶
    for name, loc, size in (
        ("Parapet_Coping_S", (0, Y0 - 0.30, PARAPET_TOP + 0.025), (VILLA_W + 0.7, 0.30, 0.05)),
        ("Parapet_Coping_N", (0, Y1 + 0.30, PARAPET_TOP + 0.025), (VILLA_W + 0.7, 0.30, 0.05)),
        ("Parapet_Coping_W", (X0 - 0.30, 0, PARAPET_TOP + 0.025), (0.30, VILLA_D + 0.7, 0.05)),
        ("Parapet_Coping_E", (X1 + 0.30, 0, PARAPET_TOP + 0.025), (0.30, VILLA_D + 0.7, 0.05)),
    ):
        add_box(name, loc, size, MAT["metal"], roof, bevel=0.004)
    # 屋面上的小设备/天窗模块，平屋顶更可信
    for i, (x, y, sx, sy) in enumerate((
        (-6.2, 4.5, 2.2, 1.2),
        (-2.4, 4.5, 2.2, 1.2),
        (1.2, 4.5, 2.2, 1.2),
    )):
        add_box("Roof_Skylight_%02d" % i, (x, y, ROOF_Z + 0.06),
                (sx, sy, 0.12), MAT["dark_matte"], roof, bevel=0.015)
        add_box("Roof_Skylight_Glass_%02d" % i, (x, y, ROOF_Z + 0.125),
                (sx - 0.14, sy - 0.14, 0.035), MAT["glass_dark"], roof)
    add_box("Roof_Planter", (6.8, 3.8, ROOF_Z + 0.30),
            (3.6, 1.1, 0.60), MAT["concrete"], roof, bevel=0.035)
    add_box("Roof_Planter_Soil", (6.8, 3.8, ROOF_Z + 0.61),
            (3.45, 0.95, 0.04), MAT["soil"], roof)
    for i, x in enumerate((5.8, 6.8, 7.8)):
        add_shrub("Roof_Shrub_%d" % i, x, 3.8, ROOF_Z + 0.63, 0.34, COLL["landscape"])

    # 屋顶四周隐藏式灯带
    add_box("Roof_LED_S", (0, Y0 - 0.27, 6.33), (VILLA_W + 0.45, 0.035, 0.025),
            MAT["emit_warm"], roof)
    add_box("Roof_LED_E", (X1 + 0.27, 0, 6.33), (0.035, VILLA_D + 0.45, 0.025),
            MAT["emit_warm"], roof)

    # ======================= 悬浮楼梯 ===============================
    n_steps = 15
    run = 0.32
    stair_x0, stair_x1 = -1.05, 0.65
    start_y = -6.10
    rise = (F2_Z - PLINTH_TOP) / n_steps
    for i in range(n_steps):
        step_top = PLINTH_TOP + (i + 1) * rise
        y = start_y + i * run + run / 2
        add_box("Stair_Tread_%02d" % i,
                ((stair_x0 + stair_x1) / 2, y, step_top - 0.035),
                (stair_x1 - stair_x0, run + 0.035, 0.07),
                MAT["wood"], stair, bevel=0.012)
        # 隐藏式踏步灯：每 3 级一个
        if i % 3 == 0:
            add_box("Stair_Tread_LED_%02d" % i,
                    (stair_x0 + 0.03, y - 0.12, step_top - 0.082),
                    (0.055, 0.26, 0.018), MAT["emit_warm"], stair)
    # 两侧钢制梯梁
    slope_len = math.sqrt((n_steps * run) ** 2 + (n_steps * rise) ** 2)
    ang = atan2(n_steps * rise, n_steps * run)
    for idx, x in enumerate((stair_x0 + 0.02, stair_x1 - 0.02)):
        add_box("Stair_Stringer_%d" % idx,
                (x, start_y + n_steps * run / 2, PLINTH_TOP + n_steps * rise / 2 - 0.17),
                (0.075, slope_len + 0.12, 0.22), MAT["dark"], stair,
                rot=(ang, 0, 0), bevel=0.008)

    # 东侧玻璃栏板 + 细钢立柱
    for i in range(0, n_steps, 3):
        top = PLINTH_TOP + (i + 3) * rise
        y = start_y + (i + 1.5) * run
        add_box("Stair_Glass_%02d" % i,
                (stair_x1 + 0.02, y, top + 0.40),
                (0.018, run * 3.05, 0.95), MAT["glass"], stair)
        add_box("Stair_GlassRail_%02d" % i,
                (stair_x1 + 0.02, y, top + 0.90),
                (0.035, run * 3.05, 0.035), MAT["dark"], stair)
    # 楼梯口顶部与栏杆连接件
    add_box("Stair_Landing_Tread", (-0.18, -1.22, F2_Z - 0.055),
            (1.9, 0.40, 0.07), MAT["wood"], stair, bevel=0.012)

    # 入口台阶
    for i in range(2):
        add_box("Entry_Porch_Step_%d" % i,
                (-1.7, -9.92 - i * 0.36, 0.14 - i * 0.055),
                (4.5, 0.42, 0.11), MAT["stone"], body, bevel=0.015)


# =============================================================================
# 06. 室内公共构件、家具与中文标签
# =============================================================================

F1_PAD_TOP = 0.262
F2_PAD_TOP = 3.462


def add_zone_pad(name, x0, x1, y0, y1, z_top, mat, coll):
    return add_box(name, ((x0 + x1) / 2, (y0 + y1) / 2, z_top - 0.0125),
                   (x1 - x0, y1 - y0, 0.025), mat, coll, bevel=0.004)


def add_zone_label(name, cn, en, x, y, z, coll, dark=False,
                   cn_size=0.36, en_size=0.135):
    """地面双语区域标签。相机从南侧看时，文字方向保持正向可读。"""
    label_mat = MAT["label_dark"] if dark else MAT["label"]
    off = max(0.30, cn_size * 0.82) if FONT_CN else max(0.16, en_size * 0.9)
    if FONT_CN and cn:
        add_text(name + "_CN", cn, (x, y + off, z + 0.002),
                 cn_size, label_mat, coll, font=FONT_CN, extrude=0.0016)
    add_text(name + "_EN", en, (x, y - off, z + 0.002),
             en_size, label_mat, coll, font=FONT_EN, extrude=0.0016)
    # 很细的规则线，作为可视化标注的基线
    add_box(name + "_Rule", (x, y - off - en_size * 0.86, z),
            (max(1.5, len(en) * en_size * 0.52), 0.018, 0.007),
            label_mat, coll)


def add_potted_plant(name, x, y, z0, coll, height=1.65, spread=0.55,
                     pot_mat=None):
    pot_h = 0.52 * min(1.0, spread / 0.55)
    add_cylinder(name + "_Pot", (x, y, z0 + pot_h / 2), 0.27 * spread / 0.55,
                 pot_h, pot_mat or MAT["pot"], coll, radius_top=0.32 * spread / 0.55,
                 segments=24, bevel=0.012)
    add_cylinder(name + "_Soil", (x, y, z0 + pot_h - 0.018),
                 0.235 * spread / 0.55, 0.035, MAT["soil"], coll, segments=24)
    trunk_h = height - pot_h - 0.35
    add_cylinder(name + "_Trunk", (x, y, z0 + pot_h + trunk_h / 2),
                 0.035, trunk_h, MAT["bark"], coll, segments=10)
    base_z = z0 + pot_h + trunk_h
    for i in range(6):
        a = i * 2.399 + 0.4
        rr = RNG.uniform(0.18, spread)
        dx = rr * cos(a)
        dy = rr * sin(a)
        dz = RNG.uniform(-0.12, 0.30)
        leaf = add_sphere("%s_Leaf_%02d" % (name, i),
                          (x + dx, y + dy, base_z + dz),
                          RNG.uniform(0.26, 0.38), MAT["leaf_light"] if i % 2 else MAT["leaf"],
                          coll, scale=(1.0, 0.62, 0.26),
                          segments=16, rings=9)
        leaf.rotation_euler = (RNG.uniform(-0.3, 0.3), 0, a)


def add_pendant_light_geo(name, x, y, z_top, drop, radius, coll,
                          shade_mat=None, glow_mat=None):
    shade_mat = shade_mat or MAT["dark"]
    glow_mat = glow_mat or MAT["emit_warm"]
    add_cylinder(name + "_Canopy", (x, y, z_top - 0.018), 0.11, 0.035,
                 MAT["dark"], coll, segments=20)
    add_cylinder(name + "_Cable", (x, y, z_top - drop / 2), 0.008, drop,
                 MAT["dark"], coll, segments=6)
    add_cylinder(name + "_Shade", (x, y, z_top - drop - 0.10), radius, 0.20,
                 shade_mat, coll, radius_top=radius * 0.55,
                 segments=28, bevel=0.008)
    add_cylinder(name + "_Glow", (x, y, z_top - drop - 0.205), radius * 0.72,
                 0.015, glow_mat, coll, segments=24)


def add_armchair(name, x, y, z0, rot_z, coll, fabric=None):
    fabric = fabric or MAT["cushion_dark"]
    ca, sa = cos(rot_z), sin(rot_z)

    def at(lx, ly):
        return (x + lx * ca - ly * sa, y + lx * sa + ly * ca)

    add_box(name + "_Seat", (x, y, z0 + 0.28), (0.82, 0.78, 0.22),
            fabric, coll, rot=(0, 0, rot_z), bevel=0.09)
    p = at(0, -0.35)
    add_box(name + "_Back", (p[0], p[1], z0 + 0.58), (0.86, 0.20, 0.62),
            fabric, coll, rot=(radians(-8), 0, rot_z), bevel=0.075)
    for side in (-1, 1):
        p = at(side * 0.43, -0.01)
        add_box("%s_Arm_%s" % (name, side), (p[0], p[1], z0 + 0.46),
                (0.10, 0.74, 0.34), fabric, coll, rot=(0, 0, rot_z),
                bevel=0.045)
        p = at(side * 0.34, -0.30)
        add_cylinder("%s_Leg_%s" % (name, side), (p[0], p[1], z0 + 0.08),
                     0.025, 0.16, MAT["dark"], coll, segments=10)


def add_bar_stool(name, x, y, coll, seat_mat=None):
    add_cylinder(name + "_Base", (x, y, 0.27), 0.24, 0.035,
                 MAT["dark"], coll, segments=24)
    add_cylinder(name + "_Stem", (x, y, 0.47), 0.035, 0.43,
                 MAT["metal"], coll, segments=12)
    add_cylinder(name + "_Footrest", (x, y, 0.40), 0.18, 0.02,
                 MAT["bronze"], coll, segments=20)
    add_cylinder(name + "_Seat", (x, y, 0.72), 0.23, 0.09,
                 seat_mat or MAT["wood_dark"], coll, segments=28, bevel=0.015)


def add_pool_table(name, x, y, z0, coll):
    table_top = z0 + 0.78
    add_box(name + "_Body", (x, y, z0 + 0.63), (2.58, 1.34, 0.22),
            MAT["wood_dark"], coll, bevel=0.025)
    add_box(name + "_Felt", (x, y, table_top + 0.002), (2.30, 1.10, 0.028),
            MAT["felt"], coll, bevel=0.008)
    # 台面木边
    for nm, dx, dy, sx, sy in (
        ("LongN", 0, -0.65, 2.7, 0.15), ("LongS", 0, 0.65, 2.7, 0.15),
        ("EndW", -1.30, 0, 0.15, 1.35), ("EndE", 1.30, 0, 0.15, 1.35),
    ):
        add_box("%s_Rail_%s" % (name, nm), (x + dx, y + dy, table_top + 0.055),
                (sx, sy, 0.13), MAT["wood_dark"], coll, bevel=0.015)
    # 四条桌腿
    for sx in (-1.02, 1.02):
        for sy in (-0.43, 0.43):
            add_box("%s_Leg_%s_%s" % (name, sx, sy),
                    (x + sx, y + sy, z0 + 0.28), (0.20, 0.20, 0.56),
                    MAT["wood_dark"], coll, bevel=0.02)
    # 六个袋口
    for px, py in ((-1.28, -.62), (1.28, -.62), (-1.28, .62), (1.28, .62),
                   (-0.05, -.65), (-0.05, .65)):
        add_cylinder("%s_Pocket_%s_%s" % (name, px, py),
                     (x + px, y + py, table_top + 0.085), 0.09, 0.03,
                     MAT["dark"], coll, segments=18)
    # 球与球杆
    ball_mats = [MAT["ball_white"], MAT["ball_yellow"], MAT["ball_blue"],
                 MAT["ball_red"], MAT["dark"], MAT["orange"]]
    bx = x - 0.15
    for i in range(8):
        row = int((math.sqrt(8 * i + 1) + 1) / 2)
        idx = i - row * (row - 1) / 2
        px = bx + row * 0.07
        py = y + (idx - (row - 1) / 2) * 0.068
        add_sphere("%s_Ball_%02d" % (name, i), (px, py, table_top + 0.055),
                   0.031, ball_mats[i % len(ball_mats)], coll,
                   segments=16, rings=10).scale = (1, 1, 1)
    cue = add_cylinder(name + "_Cue", (x - 0.2, y - 0.91, table_top + 0.075),
                       0.008, 1.52, MAT["wood_light"], coll, segments=8,
                       rot=(radians(90), 0, radians(10)))
    # 台球桌上方两盏线性吊灯
    for i, dx in enumerate((-0.65, 0.65)):
        add_pendant_light_geo(name + "_Pendant_%d" % i, x + dx, y, 3.19, 0.74,
                              0.15, coll, shade_mat=MAT["dark"],
                              glow_mat=MAT["emit_soft_warm"])


def add_glass_wall_with_door(prefix, x0, x1, y, z0, z1, coll):
    glazing_y(prefix, x0, x1, z0, z1, y, divisions=5,
              transoms=(2.52,), glass_coll=coll, frame_coll=coll)
    # 推拉门框与拉手，让泳池玻璃隔断更像可开启的门
    add_box(prefix + "_SlidingDoor_Track", ((x0 + x1) / 2, y - 0.08, z0 + 0.015),
            (x1 - x0, 0.09, 0.03), MAT["dark"], coll)
    add_box(prefix + "_SlidingDoor_Handle", (-1.95, y - 0.16, 1.15),
            (0.035, 0.035, 0.72), MAT["bronze"], coll)
    add_box(prefix + "_SlidingDoor_Handle2", (2.0, y - 0.16, 1.15),
            (0.035, 0.035, 0.72), MAT["bronze"], coll)


def build_f1():
    living = COLL["f1_living"]
    billiard = COLL["f1_billiard"]
    indoor = COLL["f1_pool"]
    zones = COLL["f1_zones"]

    # 与挑高客厅、台球室、室内泳池对应的三个颜色分区
    add_zone_pad("F1_Zone_Living", -9.55, -1.30, -7.15, 1.22,
                 F1_PAD_TOP, MAT["zone_living"], zones)
    add_zone_pad("F1_Zone_Billiard", -1.05, 9.55, -7.15, 1.22,
                 F1_PAD_TOP, MAT["zone_billiard"], zones)
    add_zone_pad("F1_Zone_IndoorPool", -9.55, 9.55, 1.55, 7.15,
                 F1_PAD_TOP, MAT["zone_pool"], zones)

    add_zone_label("F1_Label_Living", "挑高客厅", "DOUBLE-HEIGHT LIVING",
                   -5.55, -6.32, F1_PAD_TOP + 0.004, COLL["labels"], dark=False,
                   cn_size=0.70, en_size=0.25)
    add_zone_label("F1_Label_Billiard", "台球室 · 吧台", "BILLIARD & BAR",
                   4.55, -6.30, F1_PAD_TOP + 0.004, COLL["labels"], dark=False,
                   cn_size=0.66, en_size=0.24)
    add_zone_label("F1_Label_IndoorPool", "室内恒温泳池", "INDOOR HEATED POOL",
                   0.0, 2.30, F1_PAD_TOP + 0.004, COLL["labels"], dark=True,
                   cn_size=0.52, en_size=0.19)

    # 客厅与台球室之间的片墙：开一个 3.8 m 宽的通高门洞，让楼梯可见
    add_box("F1_Partition_Living_Billiard_W", (-1.15, -6.65, 1.73),
            (0.14, 1.30, 2.98), MAT["wall"], living, bevel=0.008)
    add_box("F1_Partition_Living_Billiard_E", (-1.15, -0.40, 1.73),
            (0.14, 3.30, 2.98), MAT["wall"], living, bevel=0.008)
    add_box("F1_Partition_Header", (-1.15, -4.0, 3.05),
            (0.14, 3.80, 0.30), MAT["wall"], living, bevel=0.008)
    add_box("F1_Partition_Portal_Trim_L", (-1.15, -6.0, 1.62),
            (0.16, 0.05, 2.85), MAT["wood_dark"], living)
    add_box("F1_Partition_Portal_Trim_R", (-1.15, -2.1, 1.62),
            (0.16, 0.05, 2.85), MAT["wood_dark"], living)

    # 室内泳池玻璃隔断
    add_glass_wall_with_door("F1_IndoorPool_GlassWall", -9.65, 9.65, 1.36,
                             0.27, 3.19, indoor)

    # 吊顶线性灯：客厅挑高、台球室与泳池
    add_box("F1_Living_CoveLight_S", (-5.5, -7.12, 6.37), (8.2, 0.04, 0.025),
            MAT["emit_soft_warm"], living)
    add_box("F1_Living_CoveLight_W", (-9.68, -3.0, 6.37), (0.04, 7.8, 0.025),
            MAT["emit_soft_warm"], living)
    for i, y in enumerate((-5.9, -3.2, -0.5, 2.2)):
        add_box("F1_Pool_Ceiling_Light_%d" % i, (0.0, y, 3.185),
                (13.8, 0.045, 0.025), MAT["emit_cool"], indoor)
    for i, x in enumerate((2.0, 5.0, 8.0)):
        add_box("F1_Billiard_Ceiling_Light_%d" % i, (x, 0.4, 3.185),
                (0.045, 1.5, 0.025), MAT["emit_warm"], billiard)

    # ========================= 挑高客厅 ==============================
    add_box("LIV_Rug", (-5.7, -3.2, F1_PAD_TOP + 0.010), (6.3, 3.8, 0.018),
            MAT["rug"], living, bevel=0.01)
    # L 型沙发
    add_box("LIV_Sofa_Base", (-5.95, -4.35, 0.48), (4.5, 1.18, 0.35),
            MAT["cushion"], living, bevel=0.075)
    add_box("LIV_Sofa_Back", (-5.95, -4.98, 0.86), (4.5, 0.28, 0.78),
            MAT["cushion"], living, bevel=0.09)
    for i in range(3):
        add_box("LIV_Sofa_SeatCushion_%d" % i, (-7.30 + i * 1.34, -4.28, 0.68),
                (1.25, 1.03, 0.18), MAT["cushion"], living,
                rot=(radians(4), 0, 0), bevel=0.065)
    for i, x in enumerate((-4.3, -5.0, -7.0)):
        add_box("LIV_Sofa_Pillow_%d" % i, (x, -4.83, 1.02),
                (0.48, 0.16, 0.48), MAT["accent_mustard"] if i == 1 else MAT["accent_blue"],
                living, rot=(radians(-12), 0, radians(3)), bevel=0.07)
    add_box("LIV_Sofa_Chaise", (-8.45, -2.80, 0.46), (1.18, 3.05, 0.34),
            MAT["cushion"], living, bevel=0.07)
    add_box("LIV_Sofa_ChaiseCushion", (-8.38, -2.62, 0.66), (1.02, 2.55, 0.16),
            MAT["cushion"], living, bevel=0.06)
    add_box("LIV_Sofa_Arm_S", (-3.76, -4.46, 0.65), (0.22, 1.30, 0.60),
            MAT["cushion"], living, bevel=0.05)

    # 圆形咖啡桌
    add_cylinder("LIV_CoffeeTable_Base", (-5.65, -2.55, 0.40), 0.62, 0.12,
                 MAT["wood_dark"], living, radius_top=0.72, segments=40, bevel=0.015)
    add_cylinder("LIV_CoffeeTable_Top", (-5.65, -2.55, 0.50), 0.78, 0.06,
                 MAT["stone"], living, radius_top=0.78, segments=44, bevel=0.008)
    add_box("LIV_CoffeeTable_Book_1", (-6.0, -2.75, 0.55), (0.42, 0.30, 0.035),
            MAT["books"], living, rot=(0, 0, radians(16)), bevel=0.006)
    add_box("LIV_CoffeeTable_Book_2", (-5.95, -2.73, 0.58), (0.34, 0.25, 0.03),
            MAT["dark_matte"], living, rot=(0, 0, radians(8)))
    add_cylinder("LIV_CoffeeTable_Bowl", (-5.1, -2.45, 0.56), 0.16, 0.06,
                 MAT["ceramic"], living, radius_top=0.19, segments=24)

    # 两把休闲椅
    add_armchair("LIV_Armchair_1", -3.15, -2.55, F1_PAD_TOP, radians(112), living)
    add_armchair("LIV_Armchair_2", -3.15, -1.25, F1_PAD_TOP, radians(72), living)

    # 落地灯、植物、边几
    add_cylinder("LIV_FloorLamp_Base", (-8.75, -1.05, 0.29), 0.22, 0.04,
                 MAT["dark"], living, segments=24)
    add_cylinder("LIV_FloorLamp_Stem", (-8.75, -1.05, 1.32), 0.018, 2.06,
                 MAT["bronze"], living, segments=10)
    add_cylinder("LIV_FloorLamp_Shade", (-8.75, -1.05, 2.38), 0.30, 0.30,
                 MAT["emit_soft_warm"], living, radius_top=0.22, segments=28)
    add_cylinder("LIV_SideTable", (-8.35, -0.55, 0.48), 0.32, 0.025,
                 MAT["wood_dark"], living, segments=24)
    add_cylinder("LIV_SideTable_Stem", (-8.35, -0.55, 0.36), 0.035, 0.30,
                 MAT["dark"], living, segments=10)
    add_potted_plant("LIV_Plant", -2.0, 0.62, F1_PAD_TOP, living,
                     height=2.15, spread=0.82)

    # 片墙上的极简艺术画
    add_box("LIV_Art_Frame", (-1.215, -0.85, 1.75), (0.035, 1.60, 1.08),
            MAT["dark"], living, bevel=0.005)
    add_box("LIV_Art_Canvas", (-1.235, -0.85, 1.75), (0.012, 1.47, 0.95),
            MAT["art"], living)

    # 挑高空间三盏发光吊球
    for i, (dx, dy, drop) in enumerate(((-0.5, 0.0, 2.5), (0.35, 0.25, 3.05),
                                         (0.05, -0.45, 2.0))):
        x, y = -5.65 + dx, -2.55 + dy
        add_cylinder("LIV_Pendant_Cord_%d" % i, (x, y, 6.40 - drop / 2),
                     0.008, drop, MAT["dark"], living, segments=6)
        add_sphere("LIV_Pendant_Globe_%d" % i, (x, y, 6.40 - drop),
                   0.18, MAT["emit_soft_warm"], living, segments=20, rings=12)
        add_cylinder("LIV_Pendant_Cap_%d" % i, (x, y, 6.40 - drop + 0.16),
                     0.055, 0.06, MAT["bronze"], living, segments=16)

    # ========================= 台球室 + 吧台 =========================
    add_pool_table("BIL_PoolTable", 4.45, -2.88, F1_PAD_TOP, billiard)
    add_armchair("BIL_LoungeChair_1", 1.55, 0.75, F1_PAD_TOP, radians(-45),
                 billiard, fabric=MAT["leather"])
    add_potted_plant("BIL_Plant", 8.85, -6.55, F1_PAD_TOP, billiard,
                     height=1.6, spread=0.55)

    # 吧台：深色木饰面 + 石材台面 + 背光酒架
    add_box("BAR_BackPanel", (7.2, 1.22, 1.65), (4.2, 0.08, 2.62),
            MAT["wood_dark"], billiard, bevel=0.012)
    for i in range(3):
        z = 1.30 + i * 0.42
        add_box("BAR_Shelf_%d" % i, (7.2, 1.16, z), (3.9, 0.18, 0.045),
                MAT["wood"], billiard, bevel=0.008)
        add_box("BAR_ShelfLED_%d" % i, (7.2, 1.04, z + 0.025),
                (3.75, 0.016, 0.012), MAT["emit_warm"], billiard)
    # 酒瓶
    bottle_mats = [MAT["ball_red"], MAT["ball_blue"], MAT["ball_yellow"],
                   MAT["glass_dark"], MAT["ceramic"]]
    for i, x in enumerate((5.55, 6.10, 6.65, 7.35, 7.9, 8.45)):
        add_cylinder("BAR_Bottle_%02d_A" % i, (x, 1.12, 1.565), 0.035, 0.42,
                     bottle_mats[i % len(bottle_mats)], billiard,
                     radius_top=0.025, segments=12)
        add_cylinder("BAR_Bottle_%02d_Neck" % i, (x, 1.12, 1.825), 0.015, 0.11,
                     bottle_mats[i % len(bottle_mats)], billiard, segments=10)
        if i < 4:
            add_cylinder("BAR_Bottle_%02d_B" % i, (x + 0.16, 1.12, 1.42), 0.026, 0.24,
                         bottle_mats[(i + 2) % len(bottle_mats)], billiard,
                         radius_top=0.02, segments=10)
    add_box("BAR_Counter", (7.2, 0.44, 0.77), (4.3, 0.72, 1.04),
            MAT["wood_dark"], billiard, bevel=0.025)
    add_box("BAR_Counter_Top", (7.2, 0.40, 1.31), (4.55, 0.92, 0.075),
            MAT["stone"], billiard, bevel=0.018)
    add_box("BAR_Counter_LED", (7.2, 0.02, 1.27), (4.32, 0.018, 0.018),
            MAT["emit_warm"], billiard)
    for i, x in enumerate((5.65, 6.85, 8.05)):
        add_bar_stool("BAR_Stool_%02d" % i, x, -0.25, billiard)
        add_pendant_light_geo("BAR_Pendant_%02d" % i, x, 0.18, 3.19, 0.78,
                              0.17, billiard, shade_mat=MAT["bronze"],
                              glow_mat=MAT["emit_soft_warm"])
    # 吧台前侧竖向木饰面
    for i in range(17):
        add_box("BAR_FlutedPanel_%02d" % i, (5.15 + i * 0.26, 0.10, 0.77),
                (0.055, 0.08, 0.94), MAT["wood"], billiard, bevel=0.006)

    # 台球室灯具的局部金属轨道
    add_box("BIL_CeilingRail", (4.45, -0.3, 3.19), (6.4, 0.055, 0.035),
            MAT["dark"], billiard)
    add_box("BIL_CeilingRail2", (4.45, -4.6, 3.19), (6.4, 0.055, 0.035),
            MAT["dark"], billiard)

    # ========================= 室内恒温泳池 ==========================
    # 池体（浅抬高地台，视觉上保持“下沉”的水面）
    add_box("INP_Platform", (0.0, 4.65, 0.285), (12.1, 3.5, 0.06),
            MAT["stone"], indoor, bevel=0.012)
    add_box("INP_Basin_Floor", (0.0, 4.65, 0.305), (11.45, 2.85, 0.025),
            MAT["pool_tile_floor"], indoor)
    for nm, x, y, sx, sy in (
        ("S", 0.0, 3.20, 11.8, 0.13),
        ("N", 0.0, 6.10, 11.8, 0.13),
        ("W", -5.9, 4.65, 0.13, 2.9),
        ("E", 5.9, 4.65, 0.13, 2.9),
    ):
        add_box("INP_BasinWall_%s" % nm, (x, y, 0.33), (sx, sy, 0.06),
                MAT["pool_tile_light"], indoor)
    add_box("INP_Water", (0.0, 4.65, 0.36), (11.35, 2.72, 0.025),
            MAT["water_indoor"], indoor)
    # 压顶
    add_box("INP_Coping_S", (0.0, 3.1, 0.395), (12.4, 0.34, 0.06),
            MAT["stone"], indoor, bevel=0.012)
    add_box("INP_Coping_N", (0.0, 6.2, 0.395), (12.4, 0.34, 0.06),
            MAT["stone"], indoor, bevel=0.012)
    add_box("INP_Coping_W", (-6.05, 4.65, 0.395), (0.34, 3.25, 0.06),
            MAT["stone"], indoor, bevel=0.012)
    add_box("INP_Coping_E", (6.05, 4.65, 0.395), (0.34, 3.25, 0.06),
            MAT["stone"], indoor, bevel=0.012)
    # 池内台阶与水底灯
    for i in range(2):
        add_box("INP_Step_%d" % i, (-5.0, 4.65, 0.335 + i * 0.025),
                (1.2 - i * 0.25, 2.4, 0.05), MAT["stone"], indoor, bevel=0.01)
    for i, x in enumerate((-4.1, 4.1)):
        add_box("INP_UnderwaterLight_%d" % i, (x, 6.02, 0.30),
                (0.36, 0.025, 0.10), MAT["emit_cyan"], indoor)
    # 泳池甲板家具/绿植
    add_potted_plant("INP_Plant_W", -8.55, 5.55, F1_PAD_TOP, indoor,
                     height=1.75, spread=0.60)
    add_potted_plant("INP_Plant_E", 8.55, 5.45, F1_PAD_TOP, indoor,
                     height=1.75, spread=0.60)
    add_box("INP_Bench_Seat", (7.35, 2.65, 0.75), (2.2, 0.55, 0.12),
            MAT["wood"], indoor, bevel=0.02)
    for x in (6.45, 8.25):
        add_box("INP_Bench_Leg_%s" % x, (x, 2.65, 0.53), (0.08, 0.42, 0.32),
                MAT["dark"], indoor)
    add_box("INP_Bench_Back", (7.35, 2.97, 1.0), (2.2, 0.10, 0.42),
            MAT["wood"], indoor, rot=(radians(12), 0, 0), bevel=0.02)
    # 毛巾
    add_box("INP_Towel_1", (6.5, 2.65, 0.83), (0.40, 0.28, 0.04),
            MAT["ceramic"], indoor, bevel=0.015)
    add_box("INP_Towel_2", (8.0, 2.65, 0.83), (0.42, 0.28, 0.04),
            MAT["accent_blue"], indoor, bevel=0.015)
    add_box("INP_SideTable", (-7.55, 3.0, 0.52), (0.6, 0.6, 0.5),
            MAT["stone_dark"], indoor, bevel=0.02)

    # 泳池区壁灯
    for x in (-8.8, 8.8):
        add_box("INP_WallLight_%s" % x, (x, 7.17, 2.1), (0.06, 0.04, 0.55),
                MAT["emit_soft_warm"], indoor)


# =============================================================================
# 07. 二层室内
# =============================================================================

def add_theater_seat(name, x, y, z0, coll):
    add_box(name + "_Base", (x, y, z0 + 0.15), (0.76, 0.82, 0.30),
            MAT["leather"], coll, bevel=0.08)
    add_box(name + "_Seat", (x, y + 0.02, z0 + 0.38), (0.68, 0.72, 0.10),
            MAT["leather"], coll, bevel=0.05)
    add_box(name + "_Back", (x, y - 0.34, z0 + 0.78), (0.72, 0.20, 0.68),
            MAT["leather"], coll, rot=(radians(12), 0, 0), bevel=0.06)
    for side in (-1, 1):
        add_box("%s_Arm_%s" % (name, side),
                (x + side * 0.39, y, z0 + 0.53), (0.10, 0.72, 0.26),
                MAT["cushion_dark"], coll, bevel=0.03)
        add_cylinder("%s_Cup_%s" % (name, side),
                     (x + side * 0.39, y + 0.23, z0 + 0.68), 0.04, 0.02,
                     MAT["metal"], coll, segments=12)
    add_box(name + "_Foot", (x, y + 0.30, z0 + 0.10), (0.52, 0.24, 0.08),
            MAT["dark"], coll, bevel=0.02)


def add_gaming_chair(name, x, y, z0, rot_z, coll, color_mat=None):
    color_mat = color_mat or MAT["cushion_dark"]
    ca, sa = cos(rot_z), sin(rot_z)

    def at(lx, ly):
        return (x + lx * ca - ly * sa, y + lx * sa + ly * ca)

    add_box(name + "_Seat", (x, y, z0 + 0.48), (0.58, 0.56, 0.12),
            color_mat, coll, rot=(0, 0, rot_z), bevel=0.05)
    p = at(0, -0.26)
    add_box(name + "_Back", (p[0], p[1], z0 + 0.84), (0.56, 0.14, 0.72),
            color_mat, coll, rot=(radians(12), 0, rot_z), bevel=0.05)
    p = at(0, -0.26)
    add_box(name + "_Headrest", (p[0], p[1], z0 + 1.20), (0.34, 0.13, 0.18),
            color_mat, coll, rot=(0, 0, rot_z), bevel=0.035)
    for side in (-1, 1):
        p = at(side * 0.34, 0.0)
        add_box("%s_Arm_%s" % (name, side), (p[0], p[1], z0 + 0.65),
                (0.08, 0.48, 0.07), MAT["dark"], coll, rot=(0, 0, rot_z))
        p = at(side * 0.25, 0.05)
        add_cylinder("%s_BaseLeg_%s" % (name, side),
                     (p[0], p[1], z0 + 0.12), 0.025, 0.22,
                     MAT["dark"], coll, segments=8)
    add_cylinder(name + "_Base", (x, y, z0 + 0.05), 0.30, 0.04,
                 MAT["dark"], coll, segments=5)


def add_gaming_station(prefix, x, z0, coll, screen_mat):
    desk_top = z0 + 0.76
    add_box(prefix + "_MonitorArm", (x, 6.76, desk_top + 0.30),
            (0.17, 0.05, 0.28), MAT["dark"], coll)
    add_box(prefix + "_MonitorBody", (x, 6.60, desk_top + 0.55),
            (0.90, 0.055, 0.52), MAT["dark"], coll, bevel=0.012)
    add_box(prefix + "_MonitorScreen", (x, 6.565, desk_top + 0.56),
            (0.80, 0.006, 0.43), screen_mat, coll)
    add_box(prefix + "_Keyboard", (x, 6.26, desk_top + 0.038),
            (0.52, 0.16, 0.025), MAT["dark"], coll, bevel=0.005)
    add_box(prefix + "_Mousepad", (x + 0.42, 6.26, desk_top + 0.036),
            (0.30, 0.22, 0.008), MAT["emit_violet"], coll)
    add_box(prefix + "_PC", (x + 0.42, 6.82, z0 + 0.25),
            (0.25, 0.20, 0.48), MAT["dark"], coll, bevel=0.012)
    add_box(prefix + "_PC_RGB", (x + 0.42, 6.71, z0 + 0.26),
            (0.17, 0.008, 0.36), MAT["emit_magenta"], coll)
    add_gaming_chair(prefix + "_Chair", x, 5.90, z0, 0.0, coll,
                     color_mat=MAT["cushion_dark"])


def add_treadmill(name, x, y, z0, coll):
    add_box(name + "_Deck", (x, y, z0 + 0.16), (1.00, 2.30, 0.15),
            MAT["dark"], coll, bevel=0.03)
    add_box(name + "_Belt", (x, y + 0.05, z0 + 0.245), (0.72, 1.62, 0.035),
            MAT["dark_matte"], coll, bevel=0.01)
    for side in (-1, 1):
        add_box("%s_Rail_%s" % (name, side),
                (x + side * 0.43, y, z0 + 0.41), (0.075, 1.78, 0.055),
                MAT["metal"], coll)
    add_box(name + "_Upright_L", (x - 0.42, y + 0.92, z0 + 0.87),
            (0.075, 0.10, 1.28), MAT["dark"], coll)
    add_box(name + "_Upright_R", (x + 0.42, y + 0.92, z0 + 0.87),
            (0.075, 0.10, 1.28), MAT["dark"], coll)
    add_box(name + "_Console", (x, y + 0.94, z0 + 1.48), (0.98, 0.20, 0.37),
            MAT["dark"], coll, bevel=0.03)
    add_box(name + "_ConsoleScreen", (x, y + 0.83, z0 + 1.50),
            (0.80, 0.012, 0.26), MAT["screen_cyan"], coll)
    add_box(name + "_FrontCap", (x, y + 1.13, z0 + 0.16),
            (0.94, 0.12, 0.18), MAT["dark_matte"], coll)


def add_weight_rack(name, x, y, z0, coll):
    add_box(name + "_Base", (x, y, z0 + 0.08), (2.8, 0.70, 0.16),
            MAT["dark"], coll, bevel=0.02)
    for sx in (-1.22, 1.22):
        add_box("%s_Upright_%s" % (name, sx), (x + sx, y, z0 + 1.10),
                (0.09, 0.09, 2.00), MAT["metal"], coll)
        add_box("%s_Cap_%s" % (name, sx), (x + sx, y, z0 + 2.11),
                (0.16, 0.16, 0.08), MAT["dark"], coll)
    add_cylinder(name + "_Bar", (x, y, z0 + 1.28), 0.025, 2.65,
                 MAT["metal"], coll, segments=14, rot=(0, radians(90), 0))
    for side in (-1, 1):
        for j, r in enumerate((0.18, 0.24, 0.20)):
            add_cylinder("%s_Plate_%s_%d" % (name, side, j),
                         (x + side * (0.85 + j * 0.075), y, z0 + 1.28),
                         r, 0.055, MAT["dark"], coll, segments=24)
    # 哑铃架
    add_box(name + "_DumbbellShelf", (x, y - 0.55, z0 + 0.42),
            (2.7, 0.28, 0.06), MAT["wood_dark"], coll, bevel=0.01)
    for i, pos in enumerate((-0.95, -0.32, 0.32, 0.95)):
        add_cylinder("%s_Dumbbell_%d" % (name, i), (x + pos, y - 0.55, z0 + 0.51),
                     0.055, 0.38, MAT["dark"], coll, segments=10,
                     rot=(0, radians(90), 0))
        for side in (-1, 1):
            add_cylinder("%s_DumbbellPlate_%d_%s" % (name, i, side),
                         (x + pos + side * 0.15, y - 0.55, z0 + 0.51),
                         0.10, 0.05, MAT["dark"], coll, segments=14,
                         rot=(0, radians(90), 0))


def add_gym_locker(name, x, y, z0, coll):
    add_box(name, (x, y, z0 + 0.95), (1.5, 0.46, 1.90),
            MAT["wood_dark"], coll, bevel=0.018)
    for i in range(4):
        add_box("%s_Door_%d" % (name, i), (x - 0.56 + i * 0.37, y - 0.24, z0 + 0.98),
                (0.34, 0.02, 1.76), MAT["wood"], coll, bevel=0.008)
        add_box("%s_Handle_%d" % (name, i), (x - 0.43 + i * 0.37, y - 0.265, z0 + 1.0),
                (0.02, 0.025, 0.30), MAT["metal"], coll)


def build_f2():
    gallery = COLL["f2_gallery"]
    theater = COLL["f2_theater"]
    esports = COLL["f2_esports"]
    gym = COLL["f2_gym"]
    zones = COLL["f2_zones"]

    # 楼层饰面
    add_box("F2_Hall_Floor", (-0.18, 3.0, F2_Z + 0.014),
            (2.05, 8.6, 0.028), MAT["wood"], gallery)
    add_zone_pad("F2_Zone_Theater", -9.55, -1.30, 1.55, 7.10,
                 F2_PAD_TOP, MAT["zone_theater"], zones)
    add_zone_pad("F2_Zone_Esports", 1.00, 9.55, 1.55, 7.10,
                 F2_PAD_TOP, MAT["zone_esports"], zones)
    add_zone_pad("F2_Zone_Gym", 1.00, 9.55, -7.10, 1.20,
                 F2_PAD_TOP, MAT["zone_gym"], zones)

    add_zone_label("F2_Label_Theater", "家庭影院", "HOME THEATER",
                   -5.4, 2.05, F2_PAD_TOP + 0.021, COLL["labels"],
                   cn_size=0.58, en_size=0.22)
    add_zone_label("F2_Label_Esports", "电竞房", "ESPORTS LOUNGE",
                   3.9, 3.55, F2_PAD_TOP + 0.021, COLL["labels"],
                   cn_size=0.54, en_size=0.21)
    add_zone_label("F2_Label_Gym", "专业健身房", "PROFESSIONAL GYM",
                   5.0, -4.80, F2_PAD_TOP + 0.020, COLL["labels"],
                   cn_size=0.62, en_size=0.24)

    # ===================== 二层墙体与门洞 ==========================
    # 影院东墙（面向走廊）
    add_box("F2_Theater_EastWall_S", (-1.20, 2.91, 4.90),
            (0.12, 3.18, 3.00), MAT["wall"], theater, bevel=0.008)
    add_box("F2_Theater_EastWall_N", (-1.20, 6.43, 4.90),
            (0.12, 1.74, 3.00), MAT["wall"], theater, bevel=0.008)
    add_box("F2_Theater_EastWall_Header", (-1.20, 5.05, 5.95),
            (0.12, 0.98, 0.90), MAT["wall"], theater, bevel=0.008)
    # 影院木门
    add_box("F2_Theater_Door", (-1.22, 5.05, 4.45),
            (0.045, 0.92, 2.08), MAT["wood_dark"], theater, bevel=0.012)
    add_cylinder("F2_Theater_DoorHandle", (-1.255, 5.38, 4.52), 0.017, 0.57,
                 MAT["bronze"], theater, segments=10)
    add_box("F2_Theater_DoorFrame_T", (-1.21, 5.05, 5.51),
            (0.15, 1.04, 0.08), MAT["dark"], theater)
    # 影院与中庭之间的南墙，面向挑高客厅做木格栅背景墙
    add_box("F2_Theater_SouthWall", (-5.45, 1.33, 4.90),
            (8.35, 0.12, 3.00), MAT["wall_dark"] if "wall_dark" in MAT else MAT["wall"],
            theater, bevel=0.008)
    for i in range(24):
        x = -9.45 + i * 0.36
        add_box("F2_Theater_SouthSlat_%02d" % i, (x, 1.25, 4.95),
                (0.085, 0.07, 2.65), MAT["wood_dark"], theater, bevel=0.005)
    add_box("F2_Theater_SouthSlat_LED", (-5.45, 1.22, 6.23),
            (8.0, 0.025, 0.018), MAT["emit_warm"], theater)

    # 电竞房西墙与门洞
    add_box("F2_Esports_WestWall_S", (0.85, 2.92, 4.90),
            (0.12, 3.14, 3.00), MAT["wall"], esports, bevel=0.008)
    add_box("F2_Esports_WestWall_N", (0.85, 6.34, 4.90),
            (0.12, 1.92, 3.00), MAT["wall"], esports, bevel=0.008)
    add_box("F2_Esports_WestWall_Header", (0.85, 4.90, 5.95),
            (0.12, 1.05, 0.90), MAT["wall"], esports, bevel=0.008)
    add_box("F2_Esports_Door", (0.84, 4.90, 4.45),
            (0.04, 0.98, 2.08), MAT["glass_dark"], esports)
    add_box("F2_Esports_DoorFrame_T", (0.85, 4.90, 5.51),
            (0.15, 1.08, 0.08), MAT["dark"], esports)

    # 健身房西墙与玻璃门
    add_box("F2_Gym_WestWall_S", (0.85, -4.27, 4.90),
            (0.12, 6.06, 3.00), MAT["wall"], gym, bevel=0.008)
    add_box("F2_Gym_WestWall_N", (0.85, 0.61, 4.90),
            (0.12, 1.42, 3.00), MAT["wall"], gym, bevel=0.008)
    add_box("F2_Gym_WestWall_Header", (0.85, -0.65, 5.95),
            (0.12, 1.05, 0.90), MAT["wall"], gym, bevel=0.008)
    add_box("F2_Gym_Door", (0.84, -0.65, 4.45),
            (0.035, 1.0, 2.08), MAT["glass"], gym)
    add_box("F2_Gym_DoorFrame_T", (0.85, -0.65, 5.51),
            (0.15, 1.08, 0.08), MAT["dark"], gym)
    add_cylinder("F2_Gym_DoorHandle", (0.78, -0.25, 4.45),
                 0.017, 0.62, MAT["bronze"], gym, segments=10)

    # 健身房与电竞房之间的隔墙
    add_box("F2_Gym_Esports_Divider", (5.25, 1.32, 4.90),
            (8.8, 0.12, 3.00), MAT["wall"], gym, bevel=0.008)
    # 健身房侧的吸音木格栅
    for i in range(16):
        x = 1.2 + i * 0.54
        add_box("F2_Gym_AcousticSlat_%02d" % i, (x, 1.24, 4.92),
                (0.08, 0.05, 2.5), MAT["wood"], gym, bevel=0.004)

    # ===================== 影院 ====================================
    # 地面地毯与两级踏步
    add_box("CIN_Carpet", (-5.45, 4.25, F2_PAD_TOP + 0.008),
            (8.1, 5.55, 0.018), MAT["rug_dark"], theater)
    add_box("CIN_RearPlatform", (-5.45, 3.35, F2_Z + 0.12),
            (7.1, 1.35, 0.24), MAT["wood_dark"], theater, bevel=0.025)
    add_box("CIN_RearPlatform_Top", (-5.45, 3.35, F2_Z + 0.26),
            (6.95, 1.20, 0.035), MAT["rug_dark"], theater)
    add_box("CIN_StepLED", (-5.45, 4.02, F2_Z + 0.095),
            (6.8, 0.025, 0.02), MAT["emit_warm"], theater)
    # 大屏幕及黑框
    add_box("CIN_Screen_Frame", (-5.45, 7.14, 4.98),
            (6.2, 0.06, 2.75), MAT["dark"], theater, bevel=0.012)
    add_box("CIN_Screen", (-5.45, 7.10, 4.98),
            (5.95, 0.018, 2.52), MAT["screen"], theater)
    add_box("CIN_Screen_BottomLED", (-5.45, 7.08, 3.56),
            (6.2, 0.02, 0.02), MAT["emit_warm"], theater)
    # 深色声学墙体与软包
    add_box("CIN_BackAcoustic", (-5.45, 7.23, 4.98),
            (8.2, 0.12, 2.88), MAT["dark_matte"], theater)
    for i in range(5):
        add_box("CIN_WestPanel_%02d" % i, (-9.68, 2.45 + i * 0.86, 4.90),
                (0.10, 0.72, 2.15), MAT["wood_dark"], theater, bevel=0.015)
    for i in range(4):
        add_box("CIN_EastPanel_%02d" % i, (-1.30, 2.35 + i * 0.95, 4.95),
                (0.08, 0.62, 2.3), MAT["rug_dark"], theater, bevel=0.012)
    # 两排影院座椅
    for i in range(5):
        add_theater_seat("CIN_Seat_R1_%02d" % i, -7.7 + i * 1.10, 4.78,
                         F2_Z + 0.02, theater)
        add_theater_seat("CIN_Seat_R2_%02d" % i, -7.7 + i * 1.10, 3.22,
                         F2_Z + 0.27, theater)
    # 投影机
    add_box("CIN_Projector_Body", (-5.45, 2.25, 6.17), (0.55, 0.62, 0.22),
            MAT["dark"], theater, bevel=0.025)
    add_cylinder("CIN_Projector_Lens", (-5.45, 1.94, 6.12), 0.08, 0.12,
                 MAT["glass_dark"], theater, segments=24, rot=(radians(90), 0, 0))
    add_cylinder("CIN_Projector_Mount", (-5.45, 2.55, 6.30), 0.04, 0.35,
                 MAT["dark"], theater, segments=10)
    # 天花板暖色灯槽
    add_box("CIN_CoveLED_W", (-9.55, 4.45, 6.28), (0.035, 5.5, 0.018),
            MAT["emit_soft_warm"], theater)
    add_box("CIN_CoveLED_E", (-1.37, 4.45, 6.28), (0.035, 5.5, 0.018),
            MAT["emit_soft_warm"], theater)
    add_potted_plant("CIN_Plant", -2.05, 6.55, F2_PAD_TOP, theater,
                     height=1.35, spread=0.4)

    # ===================== 电竞房 ==================================
    add_box("ESP_Rug", (5.2, 4.4, F2_PAD_TOP + 0.008),
            (5.5, 3.8, 0.018), MAT["rug_dark"], esports)
    # 北墙连续桌面与三套设备
    add_box("ESP_MainDesk", (6.0, 6.62, F2_Z + 0.725),
            (5.8, 0.76, 0.07), MAT["dark_matte"], esports, bevel=0.015)
    for x in (3.25, 8.75):
        add_box("ESP_DeskSupport_%s" % x, (x, 6.62, F2_Z + 0.36),
                (0.08, 0.66, 0.72), MAT["dark"], esports)
    add_gaming_station("ESP_Station_1", 4.1, F2_Z, esports, MAT["screen_game"])
    add_gaming_station("ESP_Station_2", 5.55, F2_Z, esports, MAT["screen_cyan"])
    add_gaming_station("ESP_Station_3", 7.0, F2_Z, esports, MAT["screen_magenta"])
    # 矮柜、饮料冰箱与灯带
    add_box("ESP_MiniFridge", (9.20, 2.15, F2_Z + 0.55),
            (0.55, 0.58, 1.10), MAT["dark"], esports, bevel=0.012)
    add_box("ESP_MiniFridge_LED", (8.91, 2.15, F2_Z + 0.57),
            (0.015, 0.40, 0.85), MAT["emit_cyan"], esports)
    add_box("ESP_SideConsole", (2.0, 2.1, F2_Z + 0.33),
            (1.8, 0.52, 0.66), MAT["wood_dark"], esports, bevel=0.015)
    add_potted_plant("ESP_Plant", 9.2, 6.6, F2_PAD_TOP, esports,
                     height=1.6, spread=0.45)
    # 声学墙面与霓虹灯
    add_box("ESP_AcousticWall", (0.94, 4.9, 4.9), (0.06, 3.8, 2.8),
            MAT["dark_matte"], esports)
    for i in range(8):
        y = 3.2 + (i % 4) * 0.8
        z = 4.1 + (i // 4) * 1.05
        add_box("ESP_AcousticTile_%02d" % i, (0.985, y, z),
                (0.04, 0.62, 0.62), MAT["zone_esports"], esports)
    add_box("ESP_NeonBack", (4.8, 7.22, 5.85), (3.3, 0.04, 0.62),
            MAT["dark"], esports)
    add_text("ESP_NeonText", "LEVEL  UP", (4.8, 7.18, 5.85), 0.42,
             MAT["emit_cyan"], esports, rot=(radians(90), 0, 0),
             font=FONT_EN, extrude=0.006)
    # 天花板 RGB 灯带
    for i, (x, mat) in enumerate(((2.0, MAT["emit_cyan"]), (4.1, MAT["emit_magenta"]),
                                   (6.2, MAT["emit_violet"]), (8.0, MAT["emit_cyan"]))):
        add_box("ESP_CeilingRGB_%d" % i, (x, 4.5, 6.36), (0.04, 4.5, 0.025),
                mat, esports)
    add_box("ESP_FloorLED", (1.02, 4.8, F2_PAD_TOP + 0.02),
            (0.022, 3.4, 0.018), MAT["emit_magenta"], esports)
    # 小圆桌和游戏椅
    add_cylinder("ESP_CoffeeTable", (8.15, 3.35, F2_Z + 0.42), 0.48, 0.045,
                 MAT["stone"], esports, segments=32, bevel=0.01)
    add_cylinder("ESP_CoffeeTable_Leg", (8.15, 3.35, F2_Z + 0.21), 0.06, 0.40,
                 MAT["dark"], esports, segments=12)
    add_cylinder("ESP_CoffeeTable_Glow", (8.15, 3.35, F2_Z + 0.13), 0.30, 0.025,
                 MAT["emit_violet"], esports, segments=24)

    # ===================== 专业健身房 ==============================
    # 有氧区、力量区、镜子与软木地面
    add_box("GYM_RubberZone", (4.7, -3.7, F2_PAD_TOP + 0.007),
            (4.4, 4.8, 0.012), MAT["zone_gym"], gym)
    add_box("GYM_YogaMat_1", (3.0, -6.45, F2_PAD_TOP + 0.026),
            (1.9, 0.95, 0.035), MAT["accent_blue"], gym, bevel=0.06)
    add_box("GYM_YogaMat_2", (4.95, -6.45, F2_PAD_TOP + 0.026),
            (1.9, 0.95, 0.035), MAT["rug_dark"], gym, bevel=0.06)
    add_treadmill("GYM_Treadmill", 2.85, -2.45, F2_PAD_TOP, gym)
    # 史密斯/深蹲架
    add_weight_rack("GYM_WeightRack", 5.75, 0.45, F2_Z, gym)
    add_gym_locker("GYM_Locker", 8.4, 0.65, F2_Z, gym)
    # 三角训练架（简洁的空中框架）
    for x in (7.85, 9.20):
        add_box("GYM_Rig_Upright_%s" % x, (x, -1.55, F2_Z + 1.25),
                (0.07, 0.07, 2.5), MAT["metal"], gym)
    add_box("GYM_Rig_Top", (8.52, -1.55, F2_Z + 2.5),
            (1.42, 0.07, 0.07), MAT["metal"], gym)
    for i in range(3):
        add_cylinder("GYM_Rig_Handle_%d" % i, (8.2 + i * 0.3, -1.55, F2_Z + 2.12),
                     0.018, 0.35, MAT["dark"], gym, segments=8)
    # 瑜伽球
    add_sphere("GYM_YogaBall", (8.55, -5.9, F2_Z + 0.48), 0.46,
               MAT["accent_blue"], gym, scale=(1, 1, 1), segments=24, rings=14)
    # 镜面墙
    add_box("GYM_Mirror_Frame", (0.94, -3.05, 4.85), (0.07, 4.65, 2.65),
            MAT["dark"], gym, bevel=0.008)
    add_box("GYM_Mirror", (0.98, -3.05, 4.85), (0.015, 4.45, 2.45),
            MAT["mirror_dark"], gym)
    # 健身器材上方的长条灯
    for i, x in enumerate((2.9, 5.2, 7.5)):
        add_box("GYM_CeilingLight_%d" % i, (x, -2.6, 6.36),
                (0.06, 3.6, 0.025), MAT["emit_cool"], gym)
    # 墙面显示器和毛巾柜
    add_box("GYM_WallScreen", (4.6, 1.27, 5.15), (1.9, 0.03, 1.05),
            MAT["dark"], gym, bevel=0.012)
    add_box("GYM_WallScreen_Image", (4.6, 1.245, 5.15), (1.76, 0.01, 0.91),
            MAT["screen"], gym)
    add_box("GYM_TowelCabinet", (2.25, 1.06, F2_Z + 0.42),
            (1.2, 0.42, 0.84), MAT["wood"], gym, bevel=0.015)
    add_potted_plant("GYM_Plant", 2.05, -5.9, F2_PAD_TOP, gym,
                     height=1.4, spread=0.4)

    # ===================== 走廊、玻璃栏板 ==========================
    # 挑高客厅上方的玻璃栏板（东侧与楼梯口南侧）
    add_box("GAL_RailGlass_West", (-1.18, 0.0, 3.93), (0.018, 2.55, 0.96),
            MAT["glass"], gallery)
    add_box("GAL_RailGlass_South", (-0.18, -1.28, 3.93), (2.0, 0.018, 0.96),
            MAT["glass"], gallery)
    add_box("GAL_RailTop_West", (-1.18, 0.0, 4.44), (0.04, 2.6, 0.04),
            MAT["dark"], gallery)
    add_box("GAL_RailTop_South", (-0.18, -1.28, 4.44), (2.08, 0.04, 0.04),
            MAT["dark"], gallery)
    for y in (-1.27, 0.0, 1.24):
        add_box("GAL_RailPost_W_%s" % y, (-1.18, y, 3.92),
                (0.045, 0.045, 1.0), MAT["dark"], gallery)
    for x in (-1.16, -0.18, 0.80):
        add_box("GAL_RailPost_S_%s" % x, (x, -1.28, 3.92),
                (0.045, 0.045, 1.0), MAT["dark"], gallery)

    # 走廊尽头的装饰边柜与画
    add_box("GAL_Console", (0.1, 6.45, F2_Z + 0.42), (1.35, 0.36, 0.84),
            MAT["wood_dark"], gallery, bevel=0.015)
    add_box("GAL_Console_Top", (0.1, 6.45, F2_Z + 0.86), (1.45, 0.42, 0.04),
            MAT["stone"], gallery, bevel=0.008)
    add_box("GAL_Art_Frame", (-1.12, 6.45, 5.25), (0.04, 1.1, 1.4),
            MAT["dark"], gallery)
    add_box("GAL_Art", (-1.095, 6.45, 5.25), (0.015, 0.98, 1.26),
            MAT["art"], gallery)
    add_potted_plant("GAL_Plant", 0.15, 5.4, F2_PAD_TOP, gallery,
                     height=1.5, spread=0.4)
    # 楼梯上方的小型吊灯
    add_pendant_light_geo("GAL_Pendant", -0.25, -4.0, 6.40, 2.8, 0.22,
                          gallery, shade_mat=MAT["bronze"],
                          glow_mat=MAT["emit_soft_warm"])


# =============================================================================
# 08. 景观、灯光、摄像机、渲染设置
# =============================================================================

def add_tree(name, x, y, height, canopy_r, coll, seed=0):
    rng = random.Random(seed)
    add_cylinder(name + "_Trunk", (x, y, height * 0.36), 0.24 * canopy_r / 2.2,
                 height * 0.72, MAT["bark"], coll,
                 radius_top=0.13 * canopy_r / 2.2, segments=12)
    # 分叉枝干
    for i in range(3):
        a = i * 2.1 + 0.7
        add_cylinder("%s_Branch_%d" % (name, i),
                     (x + 0.55 * cos(a), y + 0.55 * sin(a), height * 0.62),
                     0.055, 1.6, MAT["bark"], coll, segments=8,
                     rot=(radians(35), 0, a))
    base_z = height * 0.66
    for i in range(6):
        a = rng.uniform(0, 2 * pi)
        rr = rng.uniform(0.2, 0.8) * canopy_r
        dz = rng.uniform(-0.35, 0.7) * canopy_r
        r = rng.uniform(0.65, 1.0) * canopy_r
        add_sphere("%s_Canopy_%02d" % (name, i),
                   (x + rr * cos(a), y + rr * sin(a), base_z + dz),
                   r, MAT["leaf"] if i % 3 else MAT["leaf_light"], coll,
                   scale=(1.0, 0.92, 0.72), segments=16, rings=10)
    add_cylinder(name + "_Gravel", (x, y, 0.015), canopy_r * 0.75, 0.03,
                 MAT["gravel"], coll, segments=28)


def add_shrub(name, x, y, z, r, coll):
    for i in range(3):
        a = i * 2.1
        add_sphere("%s_%d" % (name, i),
                   (x + 0.35 * r * cos(a), y + 0.35 * r * sin(a), z + r * 0.58),
                   r * (0.72 + 0.12 * i), MAT["leaf"] if i % 2 else MAT["leaf_light"],
                   coll, scale=(1, 0.9, 0.7), segments=14, rings=8)


def build_landscape():
    land = COLL["landscape"]
    site = COLL["site"]

    # 场地外沿绿篱
    add_box("Hedge_West", (-19.2, -2.0, 0.52), (0.8, 29.0, 1.04),
            MAT["hedge"], land, bevel=0.10)
    add_box("Hedge_North", (-12.0, 20.8, 0.52), (15.5, 0.8, 1.04),
            MAT["hedge"], land, bevel=0.10)
    add_box("Hedge_Court_East", (39.4, -1.0, 0.62), (0.7, 13.6, 1.24),
            MAT["hedge"], land, bevel=0.10)
    add_box("Hedge_Court_North", (31.4, 6.7, 0.62), (14.2, 0.7, 1.24),
            MAT["hedge"], land, bevel=0.10)

    # 乔木与灌木
    tree_data = [
        ("Tree_West_A", -14.8, -3.0, 7.0, 2.5, 11),
        ("Tree_West_B", -15.4, 7.0, 5.6, 2.0, 23),
        ("Tree_West_C", -13.8, -13.4, 6.2, 2.2, 37),
        ("Tree_Foreground_W", -18.2, -17.8, 9.0, 3.2, 83),
        ("Tree_North_A", -7.0, 16.8, 7.6, 2.4, 41),
        ("Tree_North_B", 8.2, 16.0, 6.4, 2.1, 59),
        ("Tree_Far_East", 38.0, 12.5, 5.8, 2.0, 67),
        ("Tree_Court_North", 30.0, 12.4, 8.4, 2.9, 97),
    ]
    for name, x, y, h, r, seed in tree_data:
        add_tree(name, x, y, h, r, land, seed=seed)

    # 更远处再增加几组树，形成柔和的场地边界而非“空草地”。
    extra_far = [
        ("FarTree_01", -57.0, 40.0, 11.0, 3.2, False),
        ("FarTree_02", -38.0, 53.0, 13.0, 3.6, False),
        ("FarTree_03", 5.0, 57.0, 12.0, 3.4, False),
        ("FarTree_04", 38.0, 58.0, 14.0, 3.8, False),
        ("FarTree_05", 72.0, 35.0, 10.0, 2.9, False),
        ("FarTree_06", 86.0, 5.0, 9.5, 2.8, False),
        ("FarCypress_01", -52.0, 15.0, 9.0, 1.1, True),
        ("FarCypress_02", 18.0, 48.0, 10.0, 1.2, True),
        ("FarCypress_03", 62.0, 23.0, 8.5, 1.0, True),
    ]
    for i, (name, x, y, h, r, cyp) in enumerate(extra_far):
        add_distant_tree(name, x, y, h, r, land, seed=181 + i, cypress=cyp)

    # 南侧沿建筑的低矮种植带
    add_box("Front_GravelBed", (6.35, -8.25, 0.035), (6.9, 1.0, 0.07),
            MAT["gravel"], land, bevel=0.02)
    add_box("Front_GravelBed_Curb", (6.35, -8.83, 0.10), (7.0, 0.16, 0.2),
            MAT["concrete"], land, bevel=0.02)
    for i in range(9):
        x = 3.15 + i * 0.78
        add_cone("Front_OrnamentalGrass_%02d" % i,
                 (x, -8.25 + RNG.uniform(-0.18, 0.18), 0.44),
                 0.04, 0.14, RNG.uniform(0.55, 0.9), MAT["leaf_light"], land,
                 segments=5)
        if i % 2 == 0:
            add_sphere("Front_Lavender_%02d" % i, (x + 0.3, -8.55, 0.34),
                       0.12, MAT["lavender"], land, scale=(0.8, 0.8, 1.8),
                       segments=10, rings=7)
    # 入口两侧的观赏草
    for side, x in ((-1, -6.9), (1, 3.55)):
        for j in range(4):
            add_cone("Entry_OrnamentalGrass_%s_%02d" % (side, j),
                     (x + RNG.uniform(-0.6, 0.6), -10.4 + RNG.uniform(-0.2, 0.2),
                      0.36 + j * 0.01),
                     0.03, 0.09, RNG.uniform(0.5, 0.8), MAT["leaf_light"], land,
                     segments=5)
    for name, x, y, r in (
        ("Shrub_Entry_L1", -11.8, -7.2, 0.55),
        ("Shrub_Entry_L2", -12.9, -8.5, 0.7),
        ("Shrub_Entry_R", 8.0, -7.1, 0.5),
        ("Shrub_Pool", 11.5, -0.8, 0.6),
        ("Shrub_Court", 22.7, -8.4, 0.7),
        ("Shrub_East", 40.1, -13.8, 0.8),
    ):
        add_shrub(name, x, y, SITE_Z, r, land)

    # 花池里的种植
    for i, (x, y) in enumerate(((-12.8, -6.7), (-13.2, 7.8), (-6.8, -12.1))):
        add_shrub("Planter_Shrub_%02d" % i, x, y, 0.29, 0.6, land)
        for j in range(4):
            add_cone("Planter_Grass_%02d_%02d" % (i, j),
                     (x + RNG.uniform(-0.8, 0.8), y + RNG.uniform(-0.35, 0.35), 0.55),
                     0.035, 0.12, 0.85, MAT["leaf_light"], land, segments=5)

    # 步道灯与室外小地灯
    for i in range(6):
        y = -11.8 - i * 1.25
        for sx in (-4.3, 2.9):
            add_cylinder("Path_Bollard_%02d_%s" % (i, sx), (sx, y, 0.42),
                         0.045, 0.82, MAT["dark"], site, segments=10)
            add_cylinder("Path_Bollard_LED_%02d_%s" % (i, sx), (sx, y, 0.835),
                         0.048, 0.025, MAT["emit_warm"], site, segments=14)

    # 简单车道/停车铺装（在画面左前侧增加层次）
    add_box("Driveway", (-13.0, -13.0, 0.025), (7.2, 9.0, 0.05),
            MAT["concrete"], site, bevel=0.015)
    for i in range(6):
        add_box("Driveway_Stripe_%02d" % i, (-16.2 + i * 1.25, -16.4, 0.052),
                (0.055, 2.1, 0.003), MAT["label"], site)
    # 停车位旁的极简花池
    add_box("Driveway_Planter", (-9.3, -13.0, 0.22), (0.8, 8.7, 0.44),
            MAT["concrete"], land, bevel=0.05)
    for i in range(4):
        add_shrub("Driveway_Shrub_%d" % i, -9.3, -15.8 + i * 1.9, 0.42, 0.45, land)

    # 篮球场旁的小边凳和一个球车
    add_box("Court_BallCart_Base", (39.0, -7.2, 0.24), (0.8, 1.1, 0.10),
            MAT["dark"], court if False else COLL["court"], bevel=0.02)
    add_cylinder("Court_BallCart_Wheel_1", (38.65, -7.2, 0.18), 0.16, 0.06,
                 MAT["dark"], COLL["court"], segments=16, rot=(0, radians(90), 0))
    add_cylinder("Court_BallCart_Wheel_2", (39.35, -7.2, 0.18), 0.16, 0.06,
                 MAT["dark"], COLL["court"], segments=16, rot=(0, radians(90), 0))
    for i, (dx, dz) in enumerate(((0.0, 0.45), (0.22, 0.48), (-0.22, 0.52))):
        add_sphere("Court_ExtraBall_%d" % i, (39.0 + dx, -7.2, dz), 0.14,
                   MAT["orange"], COLL["court"], segments=20, rings=12)


def build_sky_backdrop():
    """用一只巨大的内发光球体提供可控的渐变天空；只对摄像机与反射可见。"""
    mat = bpy.data.materials.new("M_Sky_Gradient")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    tex = nodes.new("ShaderNodeTexCoord")
    tex.location = (-620, 0)
    sep = nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-420, 0)
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-190, 0)
    emission = nodes.new("ShaderNodeEmission")
    emission.location = (120, 0)
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (380, 0)
    emission.inputs["Strength"].default_value = 1.0

    cr = ramp.color_ramp
    cr.elements[0].position = 0.470
    cr.elements[0].color = hex_color("#DAA97B")
    cr.elements[1].position = 0.760
    cr.elements[1].color = hex_color("#5E8EB7")
    for pos, col in (
        (0.495, "#E7C49A"),
        (0.505, "#C7D9DB"),
        (0.516, "#9CC4D9"),
        (0.535, "#82B0CE"),
        (0.580, "#6599BE"),
        (0.680, "#497DA7"),
        (0.830, "#2C567B"),
        (1.000, "#18364F"),
    ):
        el = cr.elements.new(pos)
        el.color = hex_color(col)

    links.new(tex.outputs["Generated"], sep.inputs["Vector"])
    links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs["Emission"], out.inputs["Surface"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = 'DITHERED'

    dome = add_sphere("ENV_Sky_Gradient_Dome", (0.0, 0.0, 0.0), 1600.0,
                      mat, COLL["landscape"], segments=64, rings=32,
                      smooth=True)
    dome.name = "ENV_Sky_Gradient_Dome"
    dome.hide_select = True
    dome.display_type = 'BOUNDS'
    # Cycles：只让相机与玻璃反射看见它，不参与照明和阴影，环境光由 World 提供。
    for attr, val in (
        ("visible_camera", True),
        ("visible_diffuse", False),
        ("visible_glossy", True),
        ("visible_transmission", False),
        ("visible_volume_scatter", False),
        ("visible_shadow", False),
    ):
        if hasattr(dome, attr):
            try:
                setattr(dome, attr, val)
            except Exception:
                pass
    return dome


def add_distant_tree(name, x, y, height, radius, coll, seed=0, cypress=False):
    rng = random.Random(seed)
    leaf_a = MAT["leaf_far"]
    leaf_b = MAT["leaf_far_light"]
    if cypress:
        add_cylinder(name + "_Trunk", (x, y, SITE_Z + height / 2), 0.12,
                     height, MAT["bark"], coll, segments=7)
        for i in range(4):
            frac = 1.0 - i * 0.22
            add_cone("%s_Crown_%d" % (name, i),
                     (x, y, height * (0.28 + i * 0.18)),
                     radius * frac, 0.0, height * 0.42,
                     leaf_a if i % 2 else leaf_b, coll, segments=9)
        return

    add_cylinder(name + "_Trunk", (x, y, height * 0.36), 0.16,
                 height * 0.72, MAT["bark"], coll, segments=8)
    for i in range(4):
        a = rng.uniform(0, 2 * pi)
        rr = rng.uniform(0.1, 0.65) * radius
        add_sphere("%s_Canopy_%d" % (name, i),
                   (x + rr * cos(a), y + rr * sin(a),
                    height * 0.73 + rng.uniform(-0.4, 0.4) * radius),
                   radius * rng.uniform(0.68, 1.0),
                   leaf_a if i % 2 else leaf_b, coll,
                   scale=(1.0, 0.9, 0.72), segments=12, rings=7)


def build_distant_context():
    land = COLL["landscape"]
    far = 900.0
    # 超大尺度外围场地：分四块，避免遮住下沉泳池。
    site_cx = (SITE_X0 + SITE_X1) / 2
    site_w = SITE_X1 - SITE_X0
    outer = [
        ("Field_West", (SITE_X0 + -far) / 2, 0.0, SITE_X0 + far, far * 2),
        ("Field_East", (SITE_X1 + far) / 2, 0.0, far - SITE_X1, far * 2),
        ("Field_South", site_cx, (SITE_Y0 + -far) / 2, site_w, far + SITE_Y0),
        ("Field_North", site_cx, (SITE_Y1 + far) / 2, site_w, far - SITE_Y1),
    ]
    for name, cx, cy, sx, sy in outer:
        add_box(name, (cx, cy, -0.075), (sx, sy, 0.15),
                MAT["field"], land)

    # 远处树线；不再使用大体量山体，让天空与建筑轮廓保持干净。
    bg_trees = [
        ("BG_Tree_01", -40.0, 34.0, 10.0, 3.0, False),
        ("BG_Tree_02", -26.0, 46.0, 12.0, 3.4, False),
        ("BG_Tree_03", -12.0, 31.0, 8.5, 2.4, False),
        ("BG_Tree_04", 16.0, 34.0, 11.0, 3.0, False),
        ("BG_Tree_05", 30.0, 48.0, 13.0, 3.8, False),
        ("BG_Tree_06", 52.0, 29.0, 9.0, 2.7, False),
        ("BG_Tree_07", 67.0, 8.0, 10.5, 3.0, False),
        ("BG_Tree_08", -30.0, -28.0, 8.0, 2.3, False),
        ("BG_Tree_09", 50.0, -22.0, 9.5, 2.8, False),
        ("BG_Cypress_01", -24.0, 16.0, 8.0, 1.1, True),
        ("BG_Cypress_02", 42.0, 20.0, 9.0, 1.2, True),
        ("BG_Cypress_03", -23.0, 3.0, 7.0, 1.0, True),
    ]
    for i, (name, x, y, h, r, cyp) in enumerate(bg_trees):
        add_distant_tree(name, x, y, h, r, land, seed=71 + i, cypress=cyp)

    # 大面积草坪上再用一些散置花境压低“空地感”
    for i, (x, y, r) in enumerate((
        (-16.5, -20.2, 0.8), (11.0, -15.0, 0.65), (34.0, -16.0, 0.9),
        (42.5, 12.5, 0.9), (-17.8, 12.0, 0.7),
    )):
        add_shrub("Lawn_Shrub_%02d" % i, x, y, SITE_Z, r, land)


def build_lighting():
    lights = COLL["lighting"]

    # 太阳光：从西南方向切入，让南立面受光、东立面形成阴影，体量更立体。
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 4.6
    sun_data.color = (1.0, 0.77, 0.55)
    sun_data.angle = radians(1.1)
    sun = bpy.data.objects.new("Sun", sun_data)
    lights.objects.link(sun)
    sun.location = (-27.0, -31.0, 22.5)
    track_to(sun, (0.0, 0.0, 0.0))

    # 主摄像机：东南方向四分之三鸟瞰，重点表现别墅、入口与泳池。
    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    COLL["camera"].objects.link(cam)
    cam.location = (28.0, -32.0, 13.0)
    cam_data.lens = 35.0
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 4000.0
    cam_data.dof.use_dof = False
    track_to(cam, (6.0, 0.0, 3.0))
    bpy.context.scene.camera = cam

    # 第二个全景机位：把 8 x 4 m 泳池与整片半场篮球场完整收入画面。
    cam2_data = bpy.data.cameras.new("Camera_Site_Overview")
    cam2 = bpy.data.objects.new("Camera_Site_Overview", cam2_data)
    COLL["camera"].objects.link(cam2)
    cam2.location = (52.0, -50.0, 14.0)
    cam2_data.lens = 38.0
    cam2_data.sensor_width = 36.0
    cam2_data.clip_start = 0.1
    cam2_data.clip_end = 4000.0
    cam2_data.dof.use_dof = False
    track_to(cam2, (8.0, 6.0, 3.5))

    # 室内主光（柔光面光源）
    light_area("Light_Living_Soft", (-5.4, -2.2, 6.10),
               (-5.2, -2.2, 0.2), 1100.0, (1.0, 0.80, 0.63), 5.6, 4.2)
    light_area("Light_Billiard_Soft", (4.5, -2.0, 3.07),
               (4.5, -2.0, 0.2), 480.0, (1.0, 0.83, 0.68), 5.2, 3.2)
    light_area("Light_IndoorPool_Soft", (0.0, 4.4, 3.07),
               (0.0, 4.4, 0.3), 540.0, (0.78, 0.93, 1.0), 10.4, 2.8)
    light_area("Light_Theater_Soft", (-5.4, 4.8, 6.10),
               (-5.4, 4.8, 3.5), 300.0, (1.0, 0.70, 0.50), 4.1, 3.3)
    light_area("Light_Esports_Soft", (5.3, 4.4, 6.10),
               (5.3, 4.4, 3.5), 330.0, (0.65, 0.72, 1.0), 4.1, 3.3)
    light_area("Light_Gym_Soft", (5.2, -2.8, 6.10),
               (5.2, -2.8, 3.5), 500.0, (0.92, 0.95, 1.0), 4.4, 4.2)
    light_area("Light_Gallery_Soft", (-0.2, 3.2, 6.10),
               (-0.2, 3.2, 3.5), 160.0, (1.0, 0.82, 0.66), 1.7, 4.0)

    # 室内重点光
    light_point("Light_Living_Pendants", (-5.6, -2.5, 4.15), 65.0,
                (1.0, 0.72, 0.44), 1.0)
    for i, x in enumerate((5.65, 6.85, 8.05)):
        light_point("Light_Bar_Pendant_%d" % i, (x, 0.18, 2.35), 16.0,
                    (1.0, 0.66, 0.36), 0.35)
    for i, x in enumerate((-4.1, 4.1)):
        light_point("Light_IndoorPool_Water_%d" % i, (x, 4.9, 0.48), 35.0,
                    (0.15, 0.78, 1.0), 0.8)
    light_point("Light_Esports_Cyan", (2.7, 4.3, 5.9), 55.0,
                (0.20, 0.85, 1.0), 1.2)
    light_point("Light_Esports_Magenta", (7.2, 4.3, 5.9), 55.0,
                (1.0, 0.24, 0.75), 1.2)
    light_point("Light_Gym_Cool", (5.7, -2.4, 5.9), 60.0,
                (0.78, 0.90, 1.0), 1.2)
    light_point("Light_Theater_Cove", (-6.0, 6.6, 5.9), 45.0,
                (1.0, 0.57, 0.36), 0.8)

    # 入口与外部夜景氛围
    light_spot("Light_Entry_Downlight", (0.15, -9.25, 3.12),
               (0.15, -8.4, 0.0), 80.0, (1.0, 0.72, 0.43), 65, 0.5)
    light_area("Light_Roof_Wash", (-5.0, -7.9, 5.9),
               (-5.0, -7.4, 4.3), 130.0, (1.0, 0.72, 0.42), 3.4, 0.25)
    light_area("Light_Roof_Wash_E", (10.1, -2.5, 5.9),
               (9.7, -2.5, 4.3), 100.0, (1.0, 0.72, 0.42), 3.2, 0.25)

    # 篮球场和泳池氛围灯（白天不刺眼，但让材质更有层次）
    light_point("Light_Court_Ambient", (31.0, 1.5, 6.0), 65.0,
                (1.0, 0.87, 0.72), 1.8)
    for i, x in enumerate((13.3, 16.4, 19.5)):
        light_point("Light_OutdoorPool_Glow_%d" % i, (x, -5.05, 0.0), 20.0,
                    (0.10, 0.72, 1.0), 0.6)

    # 灯光统一启用阴影
    for obj in lights.objects:
        if obj.type == 'LIGHT':
            obj.data.use_shadow = True


def configure_render():
    scene = bpy.context.scene
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.film_transparent = False
    scene.render.filepath = OUTPUT_FILE
    scene.render.use_file_extension = True

    engine = RENDER_ENGINE.upper()
    if engine == "CYCLES":
        scene.render.engine = 'CYCLES'
        cyc = scene.cycles
        cyc.samples = RENDER_SAMPLES
        cyc.preview_samples = 24
        cyc.use_denoising = True
        cyc.use_adaptive_sampling = True
        cyc.adaptive_threshold = 0.012
        cyc.max_bounces = 8
        cyc.diffuse_bounces = 4
        cyc.glossy_bounces = 4
        cyc.transmission_bounces = 8
        cyc.transparent_max_bounces = 12
        cyc.caustics_reflective = True
        cyc.caustics_refractive = True
        # 自动尝试 OptiX / CUDA；没有 GPU 环境时回退到 CPU，不阻断脚本。
        cyc.device = 'CPU'
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            for compute_type in ('OPTIX', 'CUDA', 'HIP', 'ONEAPI'):
                try:
                    prefs.compute_device_type = compute_type
                    prefs.get_devices()
                except Exception:
                    continue
                gpu_devices = [d for d in prefs.devices if d.type != 'CPU']
                if gpu_devices:
                    for d in prefs.devices:
                        d.use = (d.type != 'CPU')
                    cyc.device = 'GPU'
                    break
        except Exception:
            cyc.device = 'CPU'
    else:
        # Blender 4.2–4.5 使用 BLENDER_EEVEE_NEXT；5.0+ 重新使用 BLENDER_EEVEE。
        eevee = 'BLENDER_EEVEE' if bpy.app.version >= (5, 0, 0) else 'BLENDER_EEVEE_NEXT'
        try:
            scene.render.engine = eevee
        except Exception:
            scene.render.engine = 'BLENDER_EEVEE'
        e = scene.eevee
        try:
            e.taa_render_samples = RENDER_SAMPLES
        except Exception:
            pass
        for attr, value in (
            ("use_raytracing", True),
            ("use_shadows", True),
            ("use_shadow_jitter_viewport", True),
        ):
            try:
                setattr(e, attr, value)
            except Exception:
                pass
        if hasattr(e, "ray_tracing_method"):
            try:
                e.ray_tracing_method = 'SCREEN'
            except Exception:
                pass
        try:
            e.shadow_resolution_scale = 2
        except Exception:
            pass

    # Standard 在这个明亮的外景中能保留更饱满的草地与木材颜色；
    # 若你使用外部 HDRI 或更暗的夜景，也可以改回 'AgX'。
    try:
        scene.view_settings.view_transform = 'Standard'
    except Exception:
        scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.render.use_compositing = True
    scene.render.use_sequencer = False
    scene.render.use_persistent_data = False

    # 在世界环境光与直接太阳光之间取得平衡
    if scene.world and scene.world.node_tree:
        bg = next((n for n in scene.world.node_tree.nodes
                   if n.type == 'BACKGROUND'), None)
        if bg:
            bg.inputs["Strength"].default_value = 0.30


def write_readme():
    txt = bpy.data.texts.new("README_VILLA_AURELIA")
    txt.write(
        "VILLA AURELIA / 20 x 15 m 全娱乐设施现代别墅\n"
        "=====================================================\n"
        "Blender 5.2 LTS 程序化生成 · 无需外部资产\n\n"
        "空间清单\n"
        "F1  挑高客厅 (约 8.3 x 8.5 m)、台球室 + 吧台、室内恒温泳池\n"
        "F2  家庭影院、电竞房、专业健身房、玻璃栏板走廊\n"
        "户外  8 x 4 m 下沉泳池、半场篮球场、日光躺椅、庭院与树植\n\n"
        "操作提示\n"
        "• 集合 VILLA_AURELIA_20x15 下按功能分组，可单独隐藏屋顶 / 玻璃 / 家具。\n"
        "• 摄像机 Camera 与太阳 Sun 都带有 Track To 目标，可直接移动目标调整构图。\n"
        "• 地面彩色区域与中英文标签位于 04/05 室内集合与 06_ROOM_LABELS。\n"
        "• 默认已启用 CYCLES，脚本会自动尝试 OptiX / CUDA，找不到 GPU 时回退 CPU。\n"
        "• 如果只想快速查看，把脚本顶部 RENDER_ENGINE 改为 'EEVEE'。\n"
        "• 摄像机集合里有两个机位：Camera（主视角，强调别墅与泳池）和\n"
        "  Camera_Site_Overview（全景机位，完整收入泳池与半场篮球场）。\n"
        "• 当前场景按 1600 x 1000 设置；F12 渲染输出到 //villa_entertainment.png。\n"
        "• 色彩管理默认使用 Standard 以保持饱满的日光和木材颜色；也可改成 AgX。\n"
        "• 如果要扩大窗户或调整空间划分，修改各 façade 的 glazing_x / glazing_y 参数，\n"
        "  再分别调整墙体、二层楼板开洞即可。\n"
    )
    txt.use_module = True


def main():
    reset_scene()
    setup_scene()
    make_collections()
    load_fonts()
    make_materials()

    build_sky_backdrop()
    build_distant_context()
    build_site()
    build_outdoor_pool()
    build_court()
    build_villa_shell()
    build_f1()
    build_f2()
    build_landscape()
    build_lighting()
    configure_render()
    write_readme()

    # 把测试/编辑视角留给用户：选中摄像机，方便直接开始构图
    for obj in bpy.data.objects:
        obj.select_set(False)
    cam = bpy.data.objects.get("Camera")
    if cam:
        bpy.context.view_layer.objects.active = cam
        cam.select_set(True)

    scene = bpy.context.scene
    stats = (
        "VILLA AURELIA 已生成\n"
        "  建筑：20.0 x 15.0 m / 两层 / 平屋顶\n"
        "  房间：6 个功能空间 + 吧台 + 娱乐设施\n"
        "  室外：8 x 4 m 泳池 + 半场篮球场\n"
        "  对象：%d / 集合：%d\n"
        "  输出：%s"
    ) % (len(bpy.data.objects), len(bpy.data.collections), OUTPUT_FILE)
    print(stats)


if __name__ == "__main__":
    main()

