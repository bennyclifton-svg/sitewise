# =============================================================
#  KYOTO MACHIYA — "DIGITAL TWIN" EDITION
#  Hero model for AI construction-management landing page
#  Run in Blender 3.x / 4.x (Scripting tab > Open > Run Script)
#  Best in a NEW file. Builds into its own collection.
#
#  PERIOD DETAILING (every element is canon machiya/sukiya):
#   - Irimoya-style massing: gable main roof + mokoshi skirt roof
#   - Kawara tile courses (arrayed tile rows), ridge + onigawara caps
#   - Taruki rafters exposed under every eave
#   - Koshi slatted lattice bays on the ground-floor facade
#   - Sliding shoji entrance doors with kumiko grids  (ANIMATED)
#   - Ranma transom, engawa deck on stone footings, step stones
#   - Toro stone lantern, bamboo, tobi-ishi stepping stones, fence
#
#  FUTURISTIC MATERIALITY (the AI embodiment):
#   - Structure "wood" -> translucent amber acrylic
#   - Walls -> pearl polymer; roofs -> smoked glass tile
#   - Shoji -> frosted panels with PULSING inner glow (animated)
#   - Holographic data ring orbiting the model      (ANIMATED)
#   - Cyan scan plane sweeping the building up/down (ANIMATED)
#   - Holo seam framing the base platform
#
#  Timeline: 1-240 @ 24 fps, designed to LOOP seamlessly.
# =============================================================

import bpy
import math

COLL = bpy.data.collections.new("Machiya_DigitalTwin")
bpy.context.scene.collection.children.link(COLL)

def to_coll(o):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    COLL.objects.link(o)

# ---------------- materials ----------------
BSDF = {}

def make_mat(name, color, rough=0.5, metal=0.0,
             emission=None, e_strength=0.0, alpha=1.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    BSDF[name] = b
    if b:
        ins = b.inputs
        if "Base Color" in ins: ins["Base Color"].default_value = (*color, 1)
        if "Roughness" in ins:  ins["Roughness"].default_value = rough
        if "Metallic" in ins:   ins["Metallic"].default_value = metal
        if emission:
            for nm in ("Emission Color", "Emission"):
                if nm in ins:
                    ins[nm].default_value = (*emission, 1)
                    break
            if "Emission Strength" in ins:
                ins["Emission Strength"].default_value = e_strength
        if transmission > 0:
            for nm in ("Transmission Weight", "Transmission"):
                if nm in ins:
                    ins[nm].default_value = transmission
                    break
        if alpha < 1.0 and "Alpha" in ins:
            ins["Alpha"].default_value = alpha
            try: m.blend_method = 'BLEND'
            except Exception: pass
            if hasattr(m, "surface_render_method"):
                try: m.surface_render_method = 'BLENDED'
                except Exception: pass
    m.diffuse_color = (*color, min(1.0, alpha + 0.3))
    return m

M_PEARL = make_mat("MC_PearlPolymer", (0.92, 0.90, 0.86), 0.18, 0.05)
M_BLACK = make_mat("MC_ObsidianGloss", (0.015, 0.015, 0.022), 0.06, 0.3)
M_AMBER = make_mat("MC_AmberAcrylic", (0.72, 0.42, 0.14), 0.15,
                   transmission=0.35)
M_SHOJI = make_mat("MC_FrostShoji", (0.95, 0.94, 0.90), 0.35,
                   emission=(1.0, 0.82, 0.55), e_strength=1.2)
M_HOLO  = make_mat("MC_HoloCyan", (0.0, 0.35, 0.4), 0.3,
                   emission=(0.0, 0.9, 1.0), e_strength=4.0, alpha=0.65)
M_SCAN  = make_mat("MC_HoloScan", (0.0, 0.3, 0.35), 0.3,
                   emission=(0.0, 0.85, 1.0), e_strength=2.5, alpha=0.12)
M_TILE  = make_mat("MC_GlassTile", (0.035, 0.045, 0.085), 0.12, 0.55)
M_JADE  = make_mat("MC_JadeGlass", (0.25, 0.55, 0.42), 0.2,
                   transmission=0.3)
M_TITAN = make_mat("MC_Titanium", (0.60, 0.62, 0.66), 0.35, 1.0)
M_GLOW  = make_mat("MC_WarmCore", (1.0, 0.6, 0.25), 0.4,
                   emission=(1.0, 0.55, 0.2), e_strength=2.0)
M_GND   = make_mat("MC_Graphite", (0.05, 0.055, 0.06), 0.45)

# ---------------- primitive helpers ----------------
def setmat(o, m):
    if o.data and hasattr(o.data, "materials"):
        o.data.materials.append(m)

def smooth(o):
    try:
        for p in o.data.polygons:
            p.use_smooth = True
    except Exception:
        pass

def add_box(name, loc, size, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name; o.scale = size
    setmat(o, mat); to_coll(o)
    return o

def add_cyl(name, loc, r, depth, mat, rot=(0, 0, 0), verts=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth,
                                        location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name; setmat(o, mat); to_coll(o); smooth(o)
    return o

def add_cone(name, loc, r, depth, mat, verts=8, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=0,
                                    depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name; setmat(o, mat); to_coll(o)
    return o

def add_sphere(name, loc, r, mat, scale=None, subdiv=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=r,
                                          location=loc)
    o = bpy.context.active_object
    o.name = name
    if scale: o.scale = scale
    setmat(o, mat); to_coll(o); smooth(o)
    return o

def add_empty(name, loc):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=loc)
    o = bpy.context.active_object
    o.name = name; to_coll(o)
    return o

def parent_keep(child, parent):
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()

def add_array(o, count, offset):
    """Array modifier with constant offset in object-local space."""
    mod = o.modifiers.new("arr", 'ARRAY')
    mod.count = count
    mod.use_relative_offset = False
    mod.use_constant_offset = True
    mod.constant_offset_displace = offset
    return o

def roof_slab(name, cx, cy, z0, w, d, h, ov, mat, gable=False):
    """Hipped (or gabled) roof solid, ridge along the longer axis."""
    W, D = w / 2 + ov, d / 2 + ov
    if w >= d:
        rx = W if gable else max((w - d) / 2, 0.001)
        r1, r2 = (cx - rx, cy, z0 + h), (cx + rx, cy, z0 + h)
        faces = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4), (0, 3, 2, 1)]
    else:
        ry = D if gable else max((d - w) / 2, 0.001)
        r1, r2 = (cx, cy - ry, z0 + h), (cx, cy + ry, z0 + h)
        faces = [(0, 1, 4), (1, 2, 5, 4), (2, 3, 5), (3, 0, 4, 5), (0, 3, 2, 1)]
    verts = [(cx - W, cy - D, z0), (cx + W, cy - D, z0),
             (cx + W, cy + D, z0), (cx - W, cy + D, z0), r1, r2]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate(); me.update()
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    setmat(o, mat)
    return o

# =============================================================
#  DIMENSIONS
# =============================================================
PLAT_W, PLAT_D, PLAT_H = 10.0, 7.0, 0.35
GF_W, GF_D, GF_H = 8.0, 5.6, 2.7          # ground floor
GF_Z0 = PLAT_H                             # 0.35 .. 3.05
SK_Z0 = GF_Z0 + GF_H                       # skirt (mokoshi) roof base
SK_OV, SK_H = 0.75, 0.85
F2_W, F2_D, F2_H = 6.4, 4.4, 2.2           # second storey
F2_Z0 = 3.3                                # rises through the skirt roof
RF_Z0 = F2_Z0 + F2_H                       # 5.5  main roof base
RF_OV, RF_H = 0.85, 1.5                    # ridge at 7.0
FRONT = -GF_D / 2                          # -2.8 ground-floor face
F2_FRONT = -F2_D / 2                       # -2.2

# =============================================================
#  GROUND / PLATFORM / HOLO SEAM
# =============================================================
add_box("MC_Ground", (0, -1.5, -0.03), (46, 40, 0.06), M_GND)
add_box("MC_Platform", (0, 0, PLAT_H / 2), (PLAT_W, PLAT_D, PLAT_H), M_BLACK)
# holographic seam framing the platform — the "digital twin" datum
add_box("MC_HoloSeamF", (0, -PLAT_D / 2 - 0.05, PLAT_H + 0.005),
        (PLAT_W + 0.4, 0.06, 0.015), M_HOLO)
add_box("MC_HoloSeamB", (0, PLAT_D / 2 + 0.05, PLAT_H + 0.005),
        (PLAT_W + 0.4, 0.06, 0.015), M_HOLO)
add_box("MC_HoloSeamL", (-PLAT_W / 2 - 0.05, 0, PLAT_H + 0.005),
        (0.06, PLAT_D + 0.1, 0.015), M_HOLO)
add_box("MC_HoloSeamR", (PLAT_W / 2 + 0.05, 0, PLAT_H + 0.005),
        (0.06, PLAT_D + 0.1, 0.015), M_HOLO)
for i, (nx, ny) in enumerate([(-1, -1), (1, -1), (1, 1), (-1, 1)]):
    add_sphere(f"MC_HoloNode{i}",
               (nx * (PLAT_W / 2 + 0.05), ny * (PLAT_D / 2 + 0.05),
                PLAT_H + 0.02), 0.07, M_HOLO, subdiv=1)

# =============================================================
#  BODY: ground floor, second storey
# =============================================================
add_box("MC_GroundFloor", (0, 0, GF_Z0 + GF_H / 2), (GF_W, GF_D, GF_H), M_PEARL)
add_box("MC_SecondFloor", (0, 0, F2_Z0 + F2_H / 2), (F2_W, F2_D, F2_H), M_PEARL)

# =============================================================
#  ROOFS  (main gable + mokoshi skirt), tiles, ridge, rafters
# =============================================================
roof_slab("MC_RoofMain", 0, 0, RF_Z0, F2_W, F2_D, RF_H, RF_OV, M_TILE,
          gable=True)
roof_slab("MC_RoofSkirt", 0, 0, SK_Z0, GF_W + 0.6, GF_D + 0.6, SK_H, SK_OV,
          M_TILE)

# ---- kawara tile courses on the main roof (front + back slopes)
D_rf = F2_D / 2 + RF_OV                 # 3.05 half-depth incl overhang
W_rf = F2_W / 2 + RF_OV                 # 4.05
slope_len = math.sqrt(D_rf ** 2 + RF_H ** 2)
tilt = math.atan2(D_rf, RF_H)           # rotation magnitude about X
n_off = 0.07                             # lift off the roof plane (normal)
for side, sgn in (("F", -1), ("B", 1)):
    y_mid = sgn * (D_rf / 2) + sgn * (n_off * RF_H / slope_len)
    z_mid = RF_Z0 + RF_H / 2 + n_off * D_rf / slope_len
    col = add_cyl(f"MC_TileCourse{side}",
                  (-W_rf + 0.10, y_mid, z_mid), 0.055, slope_len + 0.18,
                  M_TILE, rot=(sgn * tilt, 0, 0), verts=10)
    add_array(col, 57, (0.143, 0, 0))
# ridge + onigawara end caps
add_cyl("MC_Ridge", (0, 0, RF_Z0 + RF_H + 0.03), 0.10, 2 * W_rf + 0.25,
        M_TILE, rot=(0, math.pi / 2, 0), verts=14)
for s, sx in (("L", -1), ("R", 1)):
    add_box(f"MC_Onigawara{s}", (sx * (W_rf + 0.06), 0, RF_Z0 + RF_H + 0.06),
            (0.30, 0.26, 0.34), M_TILE)
    add_cone(f"MC_OnigawaraHorn{s}", (sx * (W_rf + 0.06), 0,
             RF_Z0 + RF_H + 0.30), 0.14, 0.24, M_TILE, verts=4)
# eave-edge round tiles (nokimaru) + fascia, main roof
for side, sgn in (("F", -1), ("B", 1)):
    add_cyl(f"MC_NokimaruMain{side}", (0, sgn * (D_rf + 0.02), RF_Z0 + 0.02),
            0.06, 2 * W_rf + 0.15, M_TILE, rot=(0, math.pi / 2, 0), verts=10)
    add_box(f"MC_FasciaMain{side}", (0, sgn * (D_rf + 0.02), RF_Z0 - 0.05),
            (2 * W_rf + 0.15, 0.06, 0.10), M_TITAN)
# bargeboards (hafu) on the gable ends
for s, sx in (("L", -1), ("R", 1)):
    for side, sgn in (("F", -1), ("B", 1)):
        add_box(f"MC_Hafu{s}{side}",
                (sx * (W_rf + 0.03), sgn * D_rf / 2, RF_Z0 + RF_H / 2),
                (0.06, slope_len + 0.1, 0.14), M_TITAN,
                rot=(sgn * tilt, 0, 0))
# taruki rafters under main eaves
beta = math.atan2(RF_H, D_rf)
for side, sgn in (("F", -1), ("B", 1)):
    y_r = sgn * (D_rf - 0.42)
    z_r = RF_Z0 + (1 - abs(y_r) / D_rf) * RF_H - 0.09
    r = add_box(f"MC_TarukiMain{side}", (-W_rf + 0.15, y_r, z_r),
                (0.05, 0.62, 0.05), M_AMBER, rot=(-sgn * beta, 0, 0))
    add_array(r, 24, (0.34, 0, 0))

# ---- skirt roof trim: fascia frame, nokimaru, rafters
SW = (GF_W + 0.6) / 2 + SK_OV            # 5.05
SD = (GF_D + 0.6) / 2 + SK_OV            # 3.85
add_box("MC_FasciaSkF", (0, -SD, SK_Z0 - 0.04), (2 * SW + 0.1, 0.07, 0.10), M_TITAN)
add_box("MC_FasciaSkB", (0, SD, SK_Z0 - 0.04), (2 * SW + 0.1, 0.07, 0.10), M_TITAN)
add_box("MC_FasciaSkL", (-SW, 0, SK_Z0 - 0.04), (0.07, 2 * SD + 0.1, 0.10), M_TITAN)
add_box("MC_FasciaSkR", (SW, 0, SK_Z0 - 0.04), (0.07, 2 * SD + 0.1, 0.10), M_TITAN)
add_cyl("MC_NokimaruSkF", (0, -SD - 0.02, SK_Z0 + 0.02), 0.055,
        2 * SW + 0.1, M_TILE, rot=(0, math.pi / 2, 0), verts=10)
beta_s = math.atan2(SK_H, SD)
zr = SK_Z0 + (1 - 3.5 / SD) * SK_H - 0.08
rs = add_box("MC_TarukiSkirt", (-SW + 0.15, -3.5, zr), (0.05, 0.72, 0.05),
             M_AMBER, rot=(beta_s, 0, 0))
add_array(rs, 30, (0.34, 0, 0))

# =============================================================
#  FACADE: posts, koshi lattice bays, sliding shoji, ranma
# =============================================================
post = add_box("MC_PostFront", (-3.93, FRONT - 0.04, GF_Z0 + GF_H / 2),
               (0.14, 0.14, GF_H), M_AMBER)
add_array(post, 7, (1.31, 0, 0))
for s, sx in (("L", -1), ("R", 1)):
    p = add_box(f"MC_PostSide{s}", (sx * 3.93, -1.4, GF_Z0 + GF_H / 2),
                (0.14, 0.14, GF_H), M_AMBER)
    add_array(p, 3, (0, 1.4, 0))

# koshi lattice bays (machiya signature) — 4 bays flanking the entrance
for cxb in (-3.275, -1.965, 1.965, 3.275):
    add_box(f"MC_KoshiBack_{cxb}", (cxb, FRONT + 0.02, 1.55),
            (1.24, 0.04, 2.05), M_BLACK)
    slat = add_box(f"MC_KoshiSlat_{cxb}", (cxb - 0.5, FRONT - 0.07, 1.55),
                   (0.035, 0.05, 1.9), M_AMBER)
    add_array(slat, 10, (0.111, 0, 0))
    add_box(f"MC_KoshiRailT_{cxb}", (cxb, FRONT - 0.07, 2.53),
            (1.2, 0.055, 0.06), M_AMBER)
    add_box(f"MC_KoshiRailB_{cxb}", (cxb, FRONT - 0.07, 0.57),
            (1.2, 0.055, 0.06), M_AMBER)

# entrance recess + ANIMATED sliding shoji doors with kumiko grids
add_box("MC_EntryRecess", (0, FRONT + 0.03, 1.48), (2.5, 0.04, 2.15), M_BLACK)
add_box("MC_EntryTrack", (0, FRONT - 0.10, 0.42), (2.6, 0.10, 0.05), M_TITAN)

def shoji_panel(tag, cx_closed, slide_to):
    pz, ph, pw = 1.45, 2.0, 1.18
    pan = add_box(f"MC_Shoji{tag}", (cx_closed, FRONT - 0.09, pz),
                  (pw, 0.04, ph), M_SHOJI)
    kids = [
        add_box(f"MC_Shoji{tag}_frT", (cx_closed, FRONT - 0.09, pz + ph / 2),
                (pw, 0.06, 0.06), M_AMBER),
        add_box(f"MC_Shoji{tag}_frB", (cx_closed, FRONT - 0.09, pz - ph / 2),
                (pw, 0.06, 0.06), M_AMBER),
        add_box(f"MC_Shoji{tag}_frL", (cx_closed - pw / 2, FRONT - 0.09, pz),
                (0.06, 0.06, ph), M_AMBER),
        add_box(f"MC_Shoji{tag}_frR", (cx_closed + pw / 2, FRONT - 0.09, pz),
                (0.06, 0.06, ph), M_AMBER),
    ]
    v = add_box(f"MC_Shoji{tag}_kumV", (cx_closed - 0.44, FRONT - 0.09, pz),
                (0.02, 0.05, ph - 0.1), M_AMBER)
    add_array(v, 5, (0.22, 0, 0)); kids.append(v)
    hh = add_box(f"MC_Shoji{tag}_kumH", (cx_closed, FRONT - 0.09, 0.70),
                 (pw - 0.08, 0.05, 0.02), M_AMBER)
    add_array(hh, 6, (0, 0, 0.30)); kids.append(hh)
    for k in kids:
        parent_keep(k, pan)
    # slide open, hold, slide shut — loop-friendly
    for f, x in ((1, cx_closed), (15, cx_closed), (85, slide_to),
                 (170, slide_to), (230, cx_closed), (240, cx_closed)):
        pan.location.x = x
        pan.keyframe_insert("location", frame=f)

shoji_panel("L", -0.60, -1.78)
shoji_panel("R",  0.60,  1.78)

# ranma transom above the entrance
rn = add_box("MC_RanmaSlat", (0, FRONT - 0.07, 2.60), (2.45, 0.05, 0.03),
             M_AMBER)
add_array(rn, 4, (0, 0, 0.10))
add_box("MC_RanmaFrame", (0, FRONT - 0.07, 2.78), (2.5, 0.055, 0.05), M_AMBER)

# =============================================================
#  SECOND-STOREY SHOJI BAND (pulsing glow) + kumiko grid
# =============================================================
add_box("MC_F2ShojiBand", (0, F2_FRONT - 0.04, 4.45), (5.9, 0.05, 1.5),
        M_SHOJI)
kv = add_box("MC_F2KumV", (-2.80, F2_FRONT - 0.07, 4.45),
             (0.025, 0.05, 1.44), M_AMBER)
add_array(kv, 19, (0.311, 0, 0))
kh = add_box("MC_F2KumH", (0, F2_FRONT - 0.07, 3.80), (5.85, 0.05, 0.025),
             M_AMBER)
add_array(kh, 5, (0, 0, 0.325))
add_box("MC_F2Sill", (0, F2_FRONT - 0.09, 3.66), (6.0, 0.10, 0.07), M_TITAN)
add_box("MC_F2Head", (0, F2_FRONT - 0.09, 5.24), (6.0, 0.10, 0.07), M_TITAN)
for s, sx in (("L", -1), ("R", 1)):     # plain frosted side windows
    add_box(f"MC_F2Side{s}", (sx * (F2_W / 2 + 0.03), 0, 4.4),
            (0.05, 2.9, 1.3), M_SHOJI)

# =============================================================
#  ENGAWA deck, footings, entry steps
# =============================================================
bd = add_box("MC_DeckBoard", (-4.55, -3.42, 0.475), (0.13, 1.15, 0.045),
             M_AMBER)
add_array(bd, 63, (0.146, 0, 0))
add_box("MC_DeckEdge", (0, -4.02, 0.43), (9.3, 0.10, 0.09), M_TITAN)
for i in range(5):
    add_cyl(f"MC_Footing{i}", (-4 + i * 2, -3.9, 0.18), 0.09, 0.36, M_BLACK,
            verts=10)
add_box("MC_Step1", (0, -4.35, 0.28), (1.5, 0.55, 0.13), M_BLACK)
add_box("MC_Step2", (0, -4.85, 0.12), (1.3, 0.5, 0.11), M_BLACK)

# =============================================================
#  GARDEN: tobi-ishi stones, toro lantern, bamboo, fence
# =============================================================
for i, (px, py) in enumerate([(0.15, -5.4), (-0.25, -6.1), (0.2, -6.8),
                              (-0.15, -7.5), (0.1, -8.1)]):
    add_sphere(f"MC_TobiIshi{i}", (px, py, 0.045), 1.0, M_BLACK,
               scale=(0.42, 0.34, 0.08), subdiv=2)

# toro stone lantern with warm pulsing core
LX, LY = -5.3, -5.0
add_cyl("MC_ToroBase", (LX, LY, 0.10), 0.42, 0.20, M_PEARL, verts=12)
add_cyl("MC_ToroPost", (LX, LY, 0.48), 0.13, 0.56, M_PEARL, verts=12)
add_box("MC_ToroShelf", (LX, LY, 0.82), (0.56, 0.56, 0.10), M_PEARL)
add_box("MC_ToroCore", (LX, LY, 1.06), (0.32, 0.32, 0.34), M_GLOW)
for i, (nx, ny) in enumerate([(-1, -1), (1, -1), (1, 1), (-1, 1)]):
    add_box(f"MC_ToroPost{i}", (LX + nx * 0.20, LY + ny * 0.20, 1.06),
            (0.07, 0.07, 0.36), M_PEARL)
add_cone("MC_ToroCap", (LX, LY, 1.40), 0.48, 0.30, M_PEARL, verts=4,
         rot=(0, 0, math.pi / 4))
add_sphere("MC_ToroJewel", (LX, LY, 1.60), 0.08, M_PEARL, subdiv=1)

# bamboo clusters (jade acrylic)
for gx, gy in ((5.9, -4.1), (-6.5, 0.9)):
    for j, (ox, oy) in enumerate([(0, 0), (0.35, 0.2), (-0.25, 0.35)]):
        bx, by = gx + ox, gy + oy
        add_cyl(f"MC_Bamboo_{gx}_{j}", (bx, by, 1.7), 0.045, 3.4, M_JADE,
                verts=8)
        for k, nz in enumerate((1.0, 1.9, 2.8)):
            add_cyl(f"MC_BambooNode_{gx}_{j}_{k}", (bx, by, nz), 0.056, 0.04,
                    M_JADE, verts=8)
        add_sphere(f"MC_BambooLeaf_{gx}_{j}", (bx + 0.1, by, 3.55), 0.32,
                   M_JADE, scale=(1, 1, 0.7), subdiv=1)

# low garden fence with a gap for the path
for s, x0 in (("L", -7.8), ("R", 1.85)):
    pk = add_cyl(f"MC_FencePicket{s}", (x0, -8.5, 0.52), 0.032, 1.0, M_JADE,
                 verts=8)
    add_array(pk, 23, (0.26, 0, 0))
    xm = x0 + 11 * 0.26
    for zr_ in (0.58, 0.88):
        add_cyl(f"MC_FenceRail{s}{zr_}", (xm, -8.5, zr_), 0.028, 6.1, M_JADE,
                rot=(0, math.pi / 2, 0), verts=8)

# =============================================================
#  AI LAYER: orbiting holo ring + vertical scan sweep
# =============================================================
bpy.ops.mesh.primitive_torus_add(major_radius=7.6, minor_radius=0.045,
                                 major_segments=72, minor_segments=8,
                                 location=(0, 0, 3.6))
ring = bpy.context.active_object
ring.name = "MC_HoloRing"
setmat(ring, M_HOLO); to_coll(ring); smooth(ring)
ring.rotation_euler = (0, 0, 0)
ring.keyframe_insert("rotation_euler", frame=1)
ring.rotation_euler = (0, 0, math.pi * 2)
ring.keyframe_insert("rotation_euler", frame=241)
if ring.animation_data and ring.animation_data.action:
    for fc in ring.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
# three small data-node beads riding the ring
for i in range(3):
    a = i * 2 * math.pi / 3
    bead = add_sphere(f"MC_RingBead{i}",
                      (7.6 * math.cos(a), 7.6 * math.sin(a), 3.6), 0.11,
                      M_HOLO, subdiv=1)
    parent_keep(bead, ring)

scan = add_box("MC_ScanPlane", (0, 0, 0.4), (13.5, 9.5, 0.035), M_SCAN)
for f, z in ((10, 0.4), (110, 7.9), (210, 0.4), (240, 0.4)):
    scan.location.z = z
    scan.keyframe_insert("location", frame=f)

# pulsing emission: shoji glow + lantern core (loop-friendly)
def pulse(mat_name, lo, hi, frames):
    b = BSDF.get(mat_name)
    if not b or "Emission Strength" not in b.inputs:
        return
    inp = b.inputs["Emission Strength"]
    for f, v in frames:
        inp.default_value = lo if v == 0 else hi
        inp.keyframe_insert("default_value", frame=f)

pulse("MC_FrostShoji", 1.2, 4.0,
      [(1, 0), (60, 1), (120, 0), (180, 1), (240, 0)])
pulse("MC_WarmCore", 2.0, 6.0,
      [(1, 0), (60, 1), (120, 0), (180, 1), (240, 0)])

# =============================================================
#  LIGHTS / WORLD / CAMERA / TIMELINE
# =============================================================
target = add_empty("MC_CamTarget", (0, -0.5, 2.9))

bpy.ops.object.light_add(type='SUN', location=(10, -14, 16),
                         rotation=(math.radians(55), 0, math.radians(35)))
sun = bpy.context.active_object
sun.name = "MC_MoonSun"; sun.data.energy = 1.3
sun.data.color = (0.72, 0.80, 1.0)
to_coll(sun)

bpy.ops.object.light_add(type='AREA', location=(7.5, -9, 6.5))
key = bpy.context.active_object
key.name = "MC_KeyLight"; key.data.energy = 900
key.data.size = 6.0; key.data.color = (1.0, 0.9, 0.78)
to_coll(key)
kc = key.constraints.new(type='TRACK_TO'); kc.target = target

world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("MC_World")
    bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.008, 0.012, 0.022, 1.0)
    bg.inputs[1].default_value = 1.0

bpy.ops.object.camera_add(location=(12.5, -13.5, 5.8))
cam = bpy.context.active_object
cam.name = "MC_Camera"; to_coll(cam)
cc = cam.constraints.new(type='TRACK_TO'); cc.target = target
bpy.context.scene.camera = cam

sc = bpy.context.scene
sc.frame_start = 1
sc.frame_end = 240
sc.render.fps = 24
if hasattr(sc, "eevee") and hasattr(sc.eevee, "use_bloom"):
    sc.eevee.use_bloom = True          # makes the holo layer sing (<=4.1)
sc.frame_set(1)

print("Machiya digital twin generated:", len(COLL.objects),
      "objects. Loop: shoji slide 15-230, ring 360deg, scan sweep, glow pulse.")
