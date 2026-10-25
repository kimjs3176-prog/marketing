"""Builds the keynote-style motion graphics scene for the RDA trap patent video.

Run: blender -b --factory-startup -noaudio --python build_scene.py
Saves trap_keynote.blend next to this file.
"""
import bpy, math, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 24
END_T = 61.0
random.seed(7)


def F(t):
    return int(round(t * FPS)) + 1


FONT_DIR = os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "Windows", "Fonts")
FONTS = {k: bpy.data.fonts.load(os.path.join(FONT_DIR, f"NanumSquareNeo-{k}.ttf"))
         for k in ("aLt", "bRg", "cBd", "dEb", "eHv")}


def srgb(h, a=1.0):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (a,)


WHITE = srgb("#f5f5f7")
GRAY = srgb("#86868b")
LGRAY = srgb("#c7c7cc")
G1 = ("#a8f26b", "#2ed3a4")   # 01 green
G2 = ("#4fd8ff", "#3d7bff")   # 02 blue
G3 = ("#ffc24b", "#ff6a3d")   # 03 orange
GB = ("#a8f26b", "#4fd8ff")   # brand

prefs = bpy.context.preferences.edit


def interp(kind):
    prefs.keyframe_new_interpolation_type = kind


def fcurves(idb):
    ad = idb.animation_data
    try:
        from bpy_extras.anim_utils import action_get_channelbag_for_slot
        return action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves
    except Exception:
        return ad.action.fcurves


def set_interp(idb, kind, path=""):
    """The new-keyframe preference is ignored in background mode, so force it after keying."""
    for fc in fcurves(idb):
        if path in fc.data_path:
            for kp in fc.keyframe_points:
                kp.interpolation = kind


# ---------------------------------------------------------------- scene setup
sc = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        pass
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.resolution_percentage = 100
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, F(END_T) - 1
sc.eevee.taa_render_samples = 12
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
world = bpy.data.worlds.new("Black")
sc.world = world
try:
    world.use_nodes = True
except Exception:
    pass
world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.render.image_settings.compression = 15
sc.render.filepath = "//frames/f_"

coll = sc.collection


def link(o):
    coll.objects.link(o)
    return o


def empty(name, loc=(0, 0, 0), parent=None):
    e = link(bpy.data.objects.new(name, None))
    e.location = loc
    e.parent = parent
    return e


# ---------------------------------------------------------------- materials
def set_blend(m):
    for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
        try:
            setattr(m, attr, val)
            return
        except Exception:
            pass


def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    return m


def emis_mat(name, color=WHITE, grad=None, alpha=1.0, strength=1.0):
    """Unlit emission material with an animatable alpha socket."""
    m = new_mat(name)
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    N.clear()
    out = N.new("ShaderNodeOutputMaterial")
    em = N.new("ShaderNodeEmission")
    tr = N.new("ShaderNodeBsdfTransparent")
    mix = N.new("ShaderNodeMixShader")
    em.inputs["Strength"].default_value = strength
    if grad:
        tc = N.new("ShaderNodeTexCoord")
        sep = N.new("ShaderNodeSeparateXYZ")
        cr = N.new("ShaderNodeValToRGB")
        L.new(tc.outputs["Generated"], sep.inputs[0])
        L.new(sep.outputs[0], cr.inputs[0])
        cr.color_ramp.elements[0].color = srgb(grad[0])
        cr.color_ramp.elements[1].color = srgb(grad[1])
        L.new(cr.outputs[0], em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = color
    L.new(tr.outputs[0], mix.inputs[1])
    L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    mix.inputs[0].default_value = alpha
    set_blend(m)
    return m, mix.inputs[0], em.inputs["Strength"]


def pbr(name, base, rough=0.4, metal=0.0, emis_color=None):
    m = new_mat(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = base
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emis_color:
        b.inputs["Emission Color"].default_value = emis_color
    b.inputs["Emission Strength"].default_value = 0.0
    return m, b.inputs["Emission Strength"]


def glass_mat():
    m = new_mat("Glass")
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.9, 0.93, 0.95, 1)
    b.inputs["Roughness"].default_value = 0.06
    out = N["Material Output"]
    tr = N.new("ShaderNodeBsdfTransparent")
    mix = N.new("ShaderNodeMixShader")
    lw = N.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    pw = N.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.2
    mu = N.new("ShaderNodeMath"); mu.operation = "MULTIPLY_ADD"
    mu.inputs[1].default_value = 0.55; mu.inputs[2].default_value = 0.05
    L.new(lw.outputs["Facing"], pw.inputs[0])
    L.new(pw.outputs[0], mu.inputs[0])
    L.new(mu.outputs[0], mix.inputs[0])
    L.new(tr.outputs[0], mix.inputs[1])
    L.new(b.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    set_blend(m)
    return m


WHITE_M, _ = pbr("White", (0.8, 0.8, 0.82, 1), rough=0.32)
METAL_M, _ = pbr("Metal", (0.62, 0.64, 0.67, 1), rough=0.22, metal=1.0)
DARK_M, _ = pbr("Dark", (0.012, 0.012, 0.015, 1), rough=0.2)
WEIGHT_M, WEIGHT_E = pbr("Weight", (0.08, 0.08, 0.09, 1), rough=0.25, metal=1.0, emis_color=srgb(G3[0]))
GLASS_M = glass_mat()
E1_M, E1_E = pbr("Emit1", (0.05, 0.05, 0.05, 1), rough=0.3, emis_color=srgb(G1[0]))
E2_M, E2_E = pbr("Emit2", (0.05, 0.05, 0.05, 1), rough=0.3, emis_color=srgb(G2[0]))
LENS_M, LENS_E = pbr("LensRing", (0.05, 0.05, 0.05, 1), rough=0.3, emis_color=srgb(G2[0]))
PLATE_M, _ = pbr("Plate", (0.85, 0.85, 0.87, 1), rough=0.28)
RIM_M, RIM_E = pbr("PlateRim", (0.1, 0.1, 0.1, 1), rough=0.3, emis_color=srgb(G3[0]))
MOTOR_M, MOTOR_E = pbr("MotorAccent", (0.05, 0.05, 0.05, 1), rough=0.3, emis_color=srgb(G3[1]))
PEST_M, _ = pbr("Pest", srgb("#9a6630"), rough=0.35)
WING_M, _, _ = emis_mat("Wing", color=(0.8, 0.85, 0.9, 1), alpha=0.35, strength=0.6)


def smooth(o):
    for op in ("shade_smooth_by_angle", "shade_auto_smooth", "shade_smooth"):
        try:
            getattr(bpy.ops.object, op)()
            return
        except Exception:
            pass


def prim(kind, name, mat, loc, parent, rot=(0, 0, 0), smooth_it=True, bevel=0.0, **kw):
    getattr(bpy.ops.mesh, f"primitive_{kind}_add")(location=loc, rotation=rot, **kw)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    if smooth_it:
        smooth(o)
    if bevel:
        bm = o.modifiers.new("Bevel", "BEVEL")
        bm.width = bevel
        bm.segments = 3
    o.parent = parent
    return o


# ---------------------------------------------------------------- the trap
root = empty("Trap")
V = 96
prim("cylinder", "Base", WHITE_M, (0, 0, 0.07), root, vertices=V, radius=0.62, depth=0.14, bevel=0.02)
prim("cylinder", "GlassBody", GLASS_M, (0, 0, 1.84), root, vertices=V, radius=0.55, depth=3.42,
     end_fill_type="NOTHING")
for z in (1.2, 2.55):
    prim("cylinder", f"Band{z}", METAL_M, (0, 0, z), root, vertices=V, radius=0.565, depth=0.045)
prim("cylinder", "Collar", WHITE_M, (0, 0, 3.6), root, vertices=V, radius=0.66, depth=0.16, bevel=0.02)
for i in range(4):
    a = math.radians(45 + 90 * i)
    prim("cylinder", f"Post{i}", METAL_M, (0.6 * math.cos(a), 0.6 * math.sin(a), 4.03), root,
         vertices=24, radius=0.03, depth=0.72)
prim("cylinder", "Roof", WHITE_M, (0, 0, 4.42), root, vertices=V, radius=0.84, depth=0.07, bevel=0.02)
prim("cone", "Funnel", WHITE_M, (0, 0, 3.93), root, vertices=V, radius1=0.1, radius2=0.52, depth=0.5,
     end_fill_type="NOTHING")
prim("cube", "Emitter1", WHITE_M, (0, 0, 4.58), root, size=1, scale=(0.34, 0.34, 0.24), bevel=0.04,
     smooth_it=False)
prim("cylinder", "Emitter1Strip", E1_M, (0, 0, 4.71), root, vertices=64, radius=0.12, depth=0.02)
prim("cylinder", "Nozzle1", METAL_M, (0, 0, 4.25), root, vertices=24, radius=0.03, depth=0.5)

# imaging section: camera module tilted toward the plate centre, second emitter on the wall
cam_mod = prim("cylinder", "CamModule", DARK_M, (0.3, 0, 3.38), root, rot=(0, math.radians(14), 0),
               vertices=48, radius=0.12, depth=0.14)
prim("cylinder", "Lens", DARK_M, (0, 0, -0.08), cam_mod, vertices=48, radius=0.065, depth=0.03)
prim("torus", "LensRing", LENS_M, (0, 0, -0.075), cam_mod, major_radius=0.078, minor_radius=0.012,
     major_segments=48, minor_segments=12)
prim("cube", "CamArm", METAL_M, (0.45, 0, 3.47), root, size=1, scale=(0.2, 0.05, 0.03), smooth_it=False)
prim("cube", "Emitter2", WHITE_M, (0.71, 0, 3.02), root, size=1, scale=(0.24, 0.32, 0.36), bevel=0.04,
     smooth_it=False)
prim("cube", "Emitter2Strip", E2_M, (0.835, 0, 3.1), root, size=1, scale=(0.01, 0.22, 0.03), smooth_it=False)
prim("cylinder", "Nozzle2", METAL_M, (0.52, 0, 3.0), root, rot=(0, math.radians(90), 0), vertices=24,
     radius=0.025, depth=0.22)

# discharge section: plate on a horizontal axle driven by a wall motor, pendulum weight beneath
PLATE_Z = 2.15
MOTOR_A = math.radians(-100)
pivot = empty("PlatePivot", (0, 0, PLATE_Z), root)
pivot.rotation_euler = (0, 0, MOTOR_A)
prim("cylinder", "Plate", PLATE_M, (0, 0, 0), pivot, vertices=V, radius=0.5, depth=0.03)
prim("torus", "PlateRim", RIM_M, (0, 0, 0), pivot, major_radius=0.5, minor_radius=0.014,
     major_segments=96, minor_segments=12)
prim("cone", "WeightCone", WHITE_M, (0, 0, -0.175), pivot, vertices=64, radius1=0.02, radius2=0.3, depth=0.32)
prim("uv_sphere", "Weight", WEIGHT_M, (0, 0, -0.38), pivot, segments=32, ring_count=16, radius=0.085)
prim("cylinder", "Axle", METAL_M, (0, 0, 0), pivot, rot=(0, math.radians(90), 0), vertices=24,
     radius=0.022, depth=1.16)
mx, my = math.cos(MOTOR_A), math.sin(MOTOR_A)
prim("cube", "Motor", DARK_M, (0.74 * mx, 0.74 * my, PLATE_Z), root, rot=(0, 0, MOTOR_A), size=1,
     scale=(0.26, 0.22, 0.28), bevel=0.03, smooth_it=False)
prim("cylinder", "MotorAccent", MOTOR_M, (0.875 * mx, 0.875 * my, PLATE_Z), root,
     rot=(0, math.radians(90), MOTOR_A), vertices=48, radius=0.07, depth=0.02)

# pest
pest = empty("Pest", (0, 0, 0), root)
body = prim("uv_sphere", "PestBody", PEST_M, (0, 0, 0), pest, segments=24, ring_count=12, radius=1)
body.scale = (0.09, 0.042, 0.04)
prim("uv_sphere", "PestHead", PEST_M, (0.095, 0, 0.005), pest, segments=16, ring_count=8, radius=0.032)
wings = []
for side in (1, -1):
    wp = empty(f"WingPivot{side}", (0, 0.012 * side, 0.03), pest)
    w = prim("uv_sphere", f"Wing{side}", WING_M, (-0.01, 0.04 * side, 0), wp, segments=16, ring_count=8, radius=1)
    w.scale = (0.08, 0.034, 0.003)
    wings.append((wp, side))

# flash light inside the imaging section
flash_data = bpy.data.lights.new("Flash", "POINT")
flash_data.energy = 0
flash_data.color = (0.85, 0.93, 1.0)
flash = link(bpy.data.objects.new("Flash", flash_data))
flash.location = (0.25, 0, 3.2)
flash.parent = root

focus_m, focus_a, _ = emis_mat("FocusRing", color=WHITE, alpha=0.0)
focus = prim("torus", "FocusRing", focus_m, (0, 0, 2.21), root, major_radius=0.17, minor_radius=0.005,
             major_segments=64, minor_segments=8)

# ---------------------------------------------------------------- stage: lights, glow, camera
target = empty("CamTarget", (0, 0, 2.25))


def area(name, loc, energy, size, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, "AREA")
    d.energy, d.size, d.color = energy, size, color
    o = link(bpy.data.objects.new(name, d))
    o.location = loc
    c = o.constraints.new("TRACK_TO")
    c.target = target_light
    c.track_axis, c.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
    return d


target_light = empty("LightTarget", (0, 0, 2.2))
key = area("Key", (-4.5, -6, 7), 1400, 4)
rimL = area("RimL", (-4, 5, 4.5), 1300, 2.5, (0.85, 0.92, 1.0))
rimR = area("RimR", (4, 5, 4.5), 1300, 2.5, (0.85, 0.92, 1.0))
fill = area("Fill", (6, -4, 1), 250, 3)

glow_m = new_mat("BackGlow")
nt = glow_m.node_tree
N, L = nt.nodes, nt.links
N.clear()
out = N.new("ShaderNodeOutputMaterial")
em = N.new("ShaderNodeEmission")
tc = N.new("ShaderNodeTexCoord")
vm = N.new("ShaderNodeVectorMath"); vm.operation = "MULTIPLY_ADD"
vm.inputs[1].default_value = (2, 2, 2); vm.inputs[2].default_value = (-1, -1, -1)
gt = N.new("ShaderNodeTexGradient"); gt.gradient_type = "SPHERICAL"
cr = N.new("ShaderNodeValToRGB")
cr.color_ramp.elements[0].color = (0, 0, 0, 1)
cr.color_ramp.elements[1].color = (0.010, 0.016, 0.028, 1)
L.new(tc.outputs["Generated"], vm.inputs[0]); L.new(vm.outputs[0], gt.inputs[0])
L.new(gt.outputs[1], cr.inputs[0]); L.new(cr.outputs[0], em.inputs["Color"])
L.new(em.outputs[0], out.inputs["Surface"])
bpy.ops.mesh.primitive_plane_add(size=18, location=(0, 8, 2.2), rotation=(math.radians(90), 0, 0))
bpy.context.active_object.data.materials.append(glow_m)

cam_data = bpy.data.cameras.new("Cam")
cam_data.lens, cam_data.sensor_width = 50, 36
cam_data.clip_start, cam_data.clip_end = 0.05, 200
cam = link(bpy.data.objects.new("Cam", cam_data))
sc.camera = cam
c = cam.constraints.new("TRACK_TO")
c.target = target
c.track_axis, c.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
hud = empty("HUD", (0, 0, -1), cam)   # visible area in HUD units: x ±3.6, y ±2.025
hud.scale = (0.1, 0.1, 0.1)


# ---------------------------------------------------------------- typography
def keys(sock, pts, path="default_value"):
    for t, v in pts:
        sock.default_value = v
        sock.keyframe_insert(path, frame=F(t))


def text(body, w, size, x, y, t_in, t_out, align="CENTER", color=WHITE, grad=None,
         dims=(), slide=0.10, din=0.6, dout=0.45):
    cu = bpy.data.curves.new("Txt", "FONT")
    cu.body = body
    cu.font = FONTS[w]
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.space_line = 1.15
    cu.resolution_u = 10
    o = link(bpy.data.objects.new("Txt", cu))
    o.parent = hud
    m, a, _ = emis_mat("TxtMat", color=color, grad=grad, alpha=0.0)
    cu.materials.append(m)
    pts = [(t_in, 0.0), (t_in + din, 1.0)]
    for td, v in dims:
        pts += [(td, pts[-1][1]), (td + 0.4, v)]
    pts += [(t_out - dout, pts[-1][1]), (t_out, 0.0)]
    keys(a, pts)
    for t, yy in ((t_in, y - slide), (t_in + din, y)):
        o.location = (x, yy, 0)
        o.keyframe_insert("location", frame=F(t))
    return o


def hud_plane(name, sx, sy, x, y, color, pts, z=0.0, interp_kind="BEZIER"):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x, y, z))
    o = bpy.context.active_object
    o.name = name
    o.scale = (sx, sy, 1)
    o.parent = hud
    m, a, _ = emis_mat(name + "Mat", color=color, alpha=0.0)
    o.data.materials.append(m)
    keys(a, pts)
    if interp_kind != "BEZIER":
        set_interp(m.node_tree, interp_kind)
    return o


# S1 opening
text("농촌진흥청 특허기술", "bRg", 0.2, 0, 0.7, 0.6, 5.7, color=LGRAY)
text("트랩, 다시 생각하다.", "eHv", 0.62, 0, 0.0, 1.5, 5.8, color=WHITE)
text("장기간 유인 및 살충이 가능한 트랩", "cBd", 0.19, 0, -0.72, 2.4, 5.8, grad=GB)
text("특허 제10-3014127호   |   출원인  대한민국(농촌진흥청장) · 주식회사 비온디솔루션", "bRg", 0.13, 0, -1.02,
     2.8, 5.8, color=GRAY)
# S2 problem
text("금방 사라지는 유인 효과.", "dEb", 0.4, 0, 0.66, 6.6, 12.3, dims=((8.3, 0.3),))
text("쌓이는 해충.", "dEb", 0.4, 0, 0.0, 8.4, 12.3, dims=((10.0, 0.3),))
text("흐려지는 데이터.", "dEb", 0.4, 0, -0.66, 10.1, 12.3)
# S3 reveal
text("장기간 유인 및 살충이 가능한 트랩", "dEb", 0.3, 0, 1.72, 14.4, 18.4, grad=GB)
text("특허 제10-3014127호  ·  농촌진흥청", "bRg", 0.15, 0, -1.78, 15.0, 18.4, color=GRAY)
# S4–S6 three beats (product sits on the right, copy on the left)
LX = -3.25
for (num, head, cap, grad, t0, t1) in (
        ("01", "오래 유인하고.", "제1방출기  ·  페로몬·살충제 장기 하향 방출\n유입 해충의 도피 방지 및 살충", G1, 19.4, 27.5),
        ("02", "정확히 찍고.", "제2방출기  ·  촬영 직전 해충 움직임 억제\n중력식 수평유지  ·  선명한 해충 영상 확보", G2, 28.3, 38.9),
        ("03", "깨끗이 비운다.", "모터 구동 회전판 고속 회전\n해충 자동 배출  ·  누적 없는 다음 촬영", G3, 39.8, 46.3)):
    text(num, "eHv", 0.2, LX, 0.78, t0, t1, align="LEFT", grad=grad)
    text(head, "eHv", 0.46, LX, 0.25, t0 + 0.15, t1, align="LEFT", grad=grad)
    text(cap, "bRg", 0.145, LX, -0.42, t0 + 0.7, t1, align="LEFT", color=LGRAY)
# S7 technology transfer
text("기술이전 활용방안", "cBd", 0.2, 0, 1.4, 47.2, 54.9, color=GRAY)
for i, (title, who, t0) in enumerate((("스마트 예찰\n트랩 제품화", "농자재 · IoT 장비 기업", 47.7),
                                      ("AI 해충\n판독 서비스", "AgTech · 데이터 서비스 기업", 49.8),
                                      ("광역\n예찰망 구축", "지자체 · 농업기술센터", 51.7))):
    x = (i - 1) * 2.45
    text(f"0{i + 1}", "eHv", 0.2, x, 0.72, t0, 54.9, grad=GB)
    text(title, "dEb", 0.3, x, 0.0, t0 + 0.1, 54.9)
    text(who, "bRg", 0.14, x, -0.82, t0 + 0.4, 54.9, color=GRAY)
for i, x in enumerate((-1.225, 1.225)):
    hud_plane(f"Div{i}", 0.006, 1.9, x, -0.05, srgb("#3a3a3c"),
              [(48.6 + i * 2.0, 0), (49.2 + i * 2.0, 1), (54.4, 1), (54.9, 0)])
# S8 end card
text("장기간 유인 및 살충이 가능한 트랩", "dEb", 0.27, 0, -1.2, 56.0, 62.0, color=WHITE)
text("특허 제10-3014127호  ·  농촌진흥청", "bRg", 0.14, 0, -1.53, 56.4, 62.0, color=GRAY)
text("기술이전 문의   한국농업기술진흥원", "cBd", 0.15, 0, -1.84, 56.9, 62.0, grad=GB)
# camera flash + fade to black, drawn in front of the text
hud_plane("FlashCard", 7.4, 4.2, 0, 0, (1, 1, 1, 1),
          [(1, 0), (36.0, 0.22), (36.0 + 2 / FPS, 0), (37.2, 0.22), (37.2 + 2 / FPS, 0)],
          z=0.02, interp_kind="CONSTANT")
hud_plane("FadeOut", 7.4, 4.2, 0, 0, (0, 0, 0, 1), [(60.2, 0), (61.0, 1)], z=0.03)

# ---------------------------------------------------------------- animation
def kloc(o, t, v):
    o.location = v
    o.keyframe_insert("location", frame=F(t))


def krot(o, t, axis, v):
    o.rotation_euler[axis] = v
    o.keyframe_insert("rotation_euler", index=axis, frame=F(t))


def kscale(o, t, v):
    o.scale = (v, v, v)
    o.keyframe_insert("scale", frame=F(t))


# product: rises in S3, sinks for S7, returns for S8
for t, z in ((0, -12), (12.6, -12), (14.9, 0), (46.2, 0), (47.5, -12), (54.6, -12), (56.9, 0)):
    kloc(root, t, (0, 0, z))
for t, r in ((12.6, -1.6), (18.4, -0.45), (19.5, -0.61), (46.2, -0.61), (54.6, -2.0), (61.0, -0.95)):
    krot(root, t, 2, r)

# camera moves
# wide shots sit at 19 units so the full product clears the title and footer lines
for t, loc, tgt in ((0, (0, -19, 2.3), (0, 0, 2.3)),
                    (12.6, (0, -19, 2.3), (0, 0, 2.3)),
                    (18.4, (1.0, -18.2, 2.5), (0, 0, 2.3)),
                    (19.6, (3.0, -6.4, 4.6), (-1.2, 0, 3.75)),
                    (27.4, (3.2, -6.6, 4.7), (-1.2, 0, 3.7)),
                    (28.5, (3.0, -6.0, 3.9), (-1.15, 0, 2.8)),
                    (38.9, (3.2, -6.2, 4.0), (-1.15, 0, 2.75)),
                    (39.9, (2.8, -5.4, 3.9), (-1.05, 0, 2.1)),
                    (46.2, (2.9, -5.6, 3.95), (-1.05, 0, 2.1)),
                    (47.4, (0, -19, 2.3), (0, 0, 2.3)),
                    (54.7, (0, -19, 1.65), (0, 0, 1.65)),
                    (61.0, (0, -17.8, 1.65), (0, 0, 1.65))):
    kloc(cam, t, loc)
    kloc(target, t, tgt)

# rim lights fade up with the reveal
for t, e in ((0, 0), (12.8, 0), (15.0, 1300)):
    for d in (rimL, rimR):
        d.energy = e
        d.keyframe_insert("energy", frame=F(t))

# highlights
keys(E1_E, [(0, 0), (20.6, 0), (21.2, 6), (27.2, 6), (27.9, 0)])
keys(E2_E, [(0, 0), (29.6, 0), (30.0, 6), (32.3, 6), (32.8, 0)])
keys(LENS_E, [(0, 0.8), (35.0, 0.8), (35.4, 5), (38.6, 5), (39.2, 0.8)])
keys(RIM_E, [(0, 0), (32.3, 0), (32.7, 5), (35.2, 5), (35.6, 0), (41.6, 0), (42.0, 6), (44.8, 6), (45.6, 0)])
keys(WEIGHT_E, [(0, 0), (32.3, 0), (32.7, 3), (35.2, 3), (35.6, 0)])
keys(MOTOR_E, [(0, 0), (41.4, 0), (41.8, 8), (45.0, 8), (45.8, 0)])

interp("CONSTANT")
for t, e in ((0, 0), (36.0, 900), (36.0 + 2 / FPS, 0), (37.2, 900), (37.2 + 2 / FPS, 0)):
    flash_data.energy = e
    flash_data.keyframe_insert("energy", frame=F(t))
interp("BEZIER")
set_interp(flash_data, "CONSTANT")

keys(focus_a, [(0, 0), (35.3, 0), (35.8, 1), (38.5, 1), (39.0, 0)])
kscale(focus, 35.3, 1.8)
kscale(focus, 35.9, 1.0)

# plate: wobble on landing (gravity levelling), high-speed spin, pendulum settle
for t, r in ((0, 0), (30.4, 0), (30.7, 0.14), (31.1, -0.08), (31.5, 0.035), (31.9, 0),
             (42.0, 0), (44.4, 10 * math.pi + 0.5), (44.9, 10 * math.pi - 0.28),
             (45.3, 10 * math.pi + 0.11), (45.8, 10 * math.pi)):
    krot(pivot, t, 0, r)

# pest flight → landing → discharge
interp("CONSTANT")
for t, s in ((0, 0), (22.4, 1.7), (43.05, 0)):
    kscale(pest, t, s)
interp("BEZIER")
set_interp(pest, "CONSTANT", "scale")
for t, p in ((22.5, (2.4, -1.6, 5.0)), (23.6, (1.2, -0.7, 4.45)), (24.5, (0.55, -0.15, 4.27)),
             (25.3, (0.05, 0, 3.95)), (26.6, (0, 0, 3.1)), (27.6, (0.05, 0.03, 3.0)),
             (28.8, (-0.04, 0, 3.05)), (29.6, (0, 0, 3.0)), (30.4, (0, 0, 2.21)),
             (42.2, (0, 0, 2.21)), (43.0, (0.06, 0, -0.6))):
    kloc(pest, t, p)
for t, r in ((22.5, 2.55), (25.3, 2.55), (30.4, 1.2)):
    krot(pest, t, 2, r)
for t, r in ((42.2, 0), (43.0, 6)):
    krot(pest, t, 1, r)
f = F(22.4)
up = True
while f < F(30.4):
    for wp, side in wings:
        wp.rotation_euler[0] = (0.7 if up else -0.5) * side
        wp.keyframe_insert("rotation_euler", index=0, frame=f)
    up = not up
    f += 2
for wp, side in wings:
    wp.rotation_euler[0] = -0.15 * side
    wp.keyframe_insert("rotation_euler", index=0, frame=F(30.6))


# emitter mist: looping particles, linear motion, shown only during their beat
def mist(name, n, color, start_fn, end_fn, period, t_show, t_hide):
    m, _, _ = emis_mat(name + "Mat", color=color, alpha=0.85, strength=3.0)
    for i in range(n):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.016)
        o = bpy.context.active_object
        o.name = f"{name}{i}"
        o.data.materials.append(m)
        o.parent = root
        s, e = start_fn(), end_fn()
        interp("LINEAR")
        t = t_show - random.random() * period
        while t < t_hide:
            kloc(o, t, s)
            kloc(o, t + period - 1 / FPS, e)
            t += period
        interp("CONSTANT")
        kscale(o, 0, 0)
        kscale(o, t_show + random.random() * 0.4, 1)
        kscale(o, t_hide, 0)
        interp("BEZIER")
        set_interp(o, "LINEAR", "location")
        set_interp(o, "CONSTANT", "scale")


def ring_pt(rmin, rmax, z):
    a = random.random() * math.tau
    r = random.uniform(rmin, rmax)
    return (r * math.cos(a), r * math.sin(a), z)


mist("MistA", 34, srgb(G1[0]), lambda: ring_pt(0, 0.1, 4.2), lambda: ring_pt(0.08, 0.46, 3.2),
     1.6, 21.0, 27.6)
mist("MistB", 22, srgb(G2[0]),
     lambda: (0.5, random.uniform(-0.05, 0.05), random.uniform(2.95, 3.05)),
     lambda: (random.uniform(-0.15, 0.2), random.uniform(-0.3, 0.3), random.uniform(2.35, 2.6)),
     1.2, 29.8, 32.5)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "trap_keynote.blend"))
print("BUILD_OK", sc.render.engine, sc.frame_end)
