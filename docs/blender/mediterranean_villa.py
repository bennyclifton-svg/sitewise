# =============================================================
#  MEDITERRANEAN VILLA GENERATOR
#  Run in Blender 3.x / 4.x  (Scripting tab > Open > Run Script)
#  Best run in a NEW empty file. Everything is created inside
#  its own collection "Mediterranean_Villa" — nothing is deleted.
#
#  What it builds:
#   - Two-storey stucco villa + one-storey wing + corner tower
#   - Hipped terracotta roofs, chimney, stone trim band
#   - Arched windows w/ weathered-blue shutters (2 pairs ANIMATED)
#   - Arched front door, fanlight, balcony w/ wrought-iron rail
#   - Courtyard wall + ANIMATED double wrought-iron gate (fr 10-100)
#   - Pergola terrace, cypress trees, terracotta pots, path
#   - Sun light, sky, camera (tracked)
#  Animation: frames 1-240 @ 24 fps
# =============================================================

import bpy
import math

# ---------------- collection ----------------
VILLA = bpy.data.collections.new("Mediterranean_Villa")
bpy.context.scene.collection.children.link(VILLA)

def to_coll(o):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    VILLA.objects.link(o)

# ---------------- materials ----------------
def make_mat(name, color, rough=0.8, metal=0.0, glassy=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        if "Base Color" in b.inputs:
            b.inputs["Base Color"].default_value = (*color, 1.0)
        if "Roughness" in b.inputs:
            b.inputs["Roughness"].default_value = rough
        if "Metallic" in b.inputs:
            b.inputs["Metallic"].default_value = metal
        if glassy:
            for nm in ("Transmission Weight", "Transmission"):
                if nm in b.inputs:
                    b.inputs[nm].default_value = 0.7
                    break
    m.diffuse_color = (*color, 1.0)  # viewport solid color
    return m

M_STUCCO  = make_mat("MV_Stucco",       (0.93, 0.87, 0.76), 0.9)
M_ROOF    = make_mat("MV_Terracotta",   (0.66, 0.30, 0.19), 0.85)
M_WOOD    = make_mat("MV_Wood",         (0.38, 0.23, 0.12), 0.7)
M_SHUTTER = make_mat("MV_ShutterBlue",  (0.22, 0.42, 0.44), 0.6)
M_IRON    = make_mat("MV_WroughtIron",  (0.04, 0.04, 0.05), 0.45, metal=0.9)
M_GLASS   = make_mat("MV_Glass",        (0.35, 0.48, 0.52), 0.08, glassy=True)
M_STONE   = make_mat("MV_StoneTrim",    (0.84, 0.80, 0.72), 0.85)
M_TILE    = make_mat("MV_FloorTile",    (0.62, 0.38, 0.26), 0.8)
M_GRASS   = make_mat("MV_Ground",       (0.38, 0.45, 0.26), 0.95)
M_LEAF    = make_mat("MV_Foliage",      (0.12, 0.30, 0.13), 0.9)

# ---------------- primitive helpers ----------------
def setmat(o, m):
    if o.data and hasattr(o.data, "materials"):
        o.data.materials.append(m)

def add_box(name, loc, size, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    setmat(o, mat)
    to_coll(o)
    return o

def add_cyl(name, loc, r, depth, mat, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r,
                                        depth=depth, location=loc,
                                        rotation=rot)
    o = bpy.context.active_object
    o.name = name
    setmat(o, mat)
    to_coll(o)
    return o

def add_cone(name, loc, r, depth, mat, verts=8, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=0,
                                    depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    setmat(o, mat)
    to_coll(o)
    return o

def add_empty(name, loc):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=loc)
    o = bpy.context.active_object
    o.name = name
    to_coll(o)
    return o

def parent_keep(child, parent):
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()

def hip_roof(name, cx, cy, z0, w, d, h, ov, mat):
    """Hipped roof slab: rectangle w x d, overhang ov, ridge height h."""
    W, D = w / 2 + ov, d / 2 + ov
    if w >= d:
        rx = max((w - d) / 2, 0.001)
        r1, r2 = (cx - rx, cy, z0 + h), (cx + rx, cy, z0 + h)
    else:
        ry = max((d - w) / 2, 0.001)
        r1, r2 = (cx, cy - ry, z0 + h), (cx, cy + ry, z0 + h)
    A = (cx - W, cy - D, z0)
    B = (cx + W, cy - D, z0)
    C = (cx + W, cy + D, z0)
    Dv = (cx - W, cy + D, z0)
    verts = [A, B, C, Dv, r1, r2]
    if w >= d:
        faces = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4), (0, 3, 2, 1)]
    else:
        faces = [(0, 1, 4), (1, 2, 5, 4), (2, 3, 5), (3, 0, 4, 5), (0, 3, 2, 1)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    o = bpy.data.objects.new(name, me)
    VILLA.objects.link(o)
    setmat(o, mat)
    # ridge cap
    if w >= d:
        L = 2 * rx + 0.3
        add_cyl(name + "_ridge", (cx, cy, z0 + h), 0.09, L, mat,
                rot=(0, math.pi / 2, 0), verts=12)
    else:
        L = 2 * ry + 0.3
        add_cyl(name + "_ridge", (cx, cy, z0 + h), 0.09, L, mat,
                rot=(math.pi / 2, 0, 0), verts=12)
    return o

# ---------------- arched window / door ----------------
def arched_window(tag, cx, cz, wall_y, w=0.9, h=1.4,
                  shutters=False, animate=False, panel_mat=None):
    """Window on a -Y facing wall. Layered (no booleans):
       stone trim plate -> glass/wood plate -> sill. Arch = half cylinders."""
    pm = panel_mat or M_GLASS
    # trim plate + trim arch
    add_box(f"MV_{tag}_trim", (cx, wall_y - 0.03, cz), (w + 0.24, 0.06, h), M_STONE)
    add_cyl(f"MV_{tag}_trimArch", (cx, wall_y - 0.03, cz + h / 2),
            w / 2 + 0.12, 0.06, M_STONE, rot=(math.pi / 2, 0, 0))
    # glass / door panel + arch
    add_box(f"MV_{tag}_pane", (cx, wall_y - 0.07, cz), (w, 0.04, h), pm)
    add_cyl(f"MV_{tag}_paneArch", (cx, wall_y - 0.07, cz + h / 2),
            w / 2, 0.04, M_GLASS, rot=(math.pi / 2, 0, 0))
    # sill
    add_box(f"MV_{tag}_sill", (cx, wall_y - 0.10, cz - h / 2 - 0.04),
            (w + 0.34, 0.20, 0.07), M_STONE)
    if not shutters:
        return
    # shutters (built CLOSED over the window, then rotated/keyed open)
    for side, sgn in (("L", -1), ("R", 1)):
        hinge_x = cx + sgn * (w / 2 + 0.10)
        piv = add_empty(f"MV_{tag}_shutterPivot{side}",
                        (hinge_x, wall_y - 0.13, cz))
        pan = add_box(f"MV_{tag}_shutter{side}",
                      (cx + sgn * (w / 4 + 0.02), wall_y - 0.13, cz),
                      (w / 2 + 0.04, 0.04, h), M_SHUTTER)
        parent_keep(pan, piv)
        open_ang = math.radians(-165 if side == "L" else 165)
        if animate:
            piv.rotation_euler = (0, 0, 0)
            piv.keyframe_insert("rotation_euler", frame=20)
            piv.rotation_euler = (0, 0, open_ang)
            piv.keyframe_insert("rotation_euler", frame=90)
        else:
            piv.rotation_euler = (0, 0, open_ang)

# =============================================================
#  BUILD
# =============================================================
FRONT = -3.0   # front wall plane of the main block (y)

# ground, terrace, path
add_box("MV_Ground", (0, -2, -0.03), (44, 40, 0.06), M_GRASS)
add_box("MV_Terrace", (6, -4.9, 0.03), (4.8, 3.2, 0.06), M_TILE)
for i in range(6):
    add_box(f"MV_Path{i}", (0, -3.75 - i * 0.92, 0.03), (1.8, 0.85, 0.06), M_TILE)

# main block, wing, tower
add_box("MV_MainBlock", (0, 0, 2.8), (8, 6, 5.6), M_STUCCO)
add_box("MV_Wing", (6, -0.5, 1.5), (4, 5, 3.0), M_STUCCO)
add_box("MV_Tower", (-3.4, 2.4, 4.0), (2.7, 2.7, 8.0), M_STUCCO)
add_box("MV_TrimBand", (0, 0, 2.82), (8.16, 6.16, 0.14), M_STONE)   # storey band

# roofs
hip_roof("MV_RoofMain", 0, 0, 5.6, 8, 6, 1.7, 0.45, M_ROOF)
hip_roof("MV_RoofWing", 6, -0.5, 3.0, 4, 5, 1.15, 0.4, M_ROOF)
# tower: 4-sided pyramid, rotated 45 deg so edges align with walls
add_cone("MV_RoofTower", (-3.4, 2.4, 8.55), (2.7 / 2) * math.sqrt(2) + 0.35,
         1.5, M_ROOF, verts=4, rot=(0, 0, math.pi / 4))
add_box("MV_Chimney", (2.4, 1.2, 6.4), (0.55, 0.55, 1.9), M_STUCCO)
add_box("MV_ChimneyCap", (2.4, 1.2, 7.4), (0.75, 0.75, 0.12), M_STONE)

# front door (arched, wood, fanlight) + step + pots
arched_window("Door", 0, 1.1, FRONT, w=1.2, h=2.2, panel_mat=M_WOOD)
add_box("MV_Step", (0, FRONT - 0.35, 0.07), (2.0, 0.8, 0.14), M_STONE)
for sgn in (-1, 1):
    add_cyl(f"MV_Pot{'L' if sgn < 0 else 'R'}",
            (sgn * 1.3, FRONT - 0.55, 0.22), 0.26, 0.44, M_TILE, verts=16)
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=1, radius=0.32, location=(sgn * 1.3, FRONT - 0.55, 0.62))
    o = bpy.context.active_object
    o.name = f"MV_PotPlant{'L' if sgn < 0 else 'R'}"
    setmat(o, M_LEAF)
    to_coll(o)

# ground-floor windows (main block + wing + tower slit)
arched_window("WinG1", -2.6, 1.5, FRONT, shutters=True)
arched_window("WinG2",  2.6, 1.5, FRONT, shutters=True)
arched_window("WinWing", 6.0, 1.5, FRONT, shutters=True)
# tower oculus windows (round, high up where the tower clears the main roof)
add_cyl("MV_TowerOculusTrimF", (-3.4, 1.03, 7.15), 0.37, 0.06, M_STONE,
        rot=(math.pi / 2, 0, 0))
add_cyl("MV_TowerOculusF", (-3.4, 0.99, 7.15), 0.28, 0.05, M_GLASS,
        rot=(math.pi / 2, 0, 0))
add_cyl("MV_TowerOculusTrimL", (-4.78, 2.4, 7.15), 0.37, 0.06, M_STONE,
        rot=(0, math.pi / 2, 0))
add_cyl("MV_TowerOculusL", (-4.82, 2.4, 7.15), 0.28, 0.05, M_GLASS,
        rot=(0, math.pi / 2, 0))

# upper-floor windows — the two flanking the balcony have ANIMATED shutters
arched_window("WinU1", -2.6, 4.15, FRONT, shutters=True, animate=True)
arched_window("WinU2",  2.6, 4.15, FRONT, shutters=True, animate=True)

# balcony: slab, french door, wrought-iron railing
add_box("MV_BalconySlab", (0, FRONT - 0.55, 2.94), (2.6, 1.1, 0.14), M_STONE)
arched_window("DoorBalc", 0, 3.95, FRONT, w=1.1, h=1.8, panel_mat=M_GLASS)
add_box("MV_BalcRailTop", (0, FRONT - 1.05, 3.95), (2.6, 0.05, 0.05), M_IRON)
for i in range(9):
    x = -1.2 + i * 0.3
    add_cyl(f"MV_BalcBar{i}", (x, FRONT - 1.05, 3.47), 0.02, 0.9, M_IRON, verts=8)
for sgn in (-1, 1):  # railing sides
    add_box(f"MV_BalcRailSide{'L' if sgn < 0 else 'R'}",
            (sgn * 1.28, FRONT - 0.55, 3.95), (0.05, 1.05, 0.05), M_IRON)

# pergola over the wing terrace
for i, (px, py) in enumerate([(4.4, -6.2), (7.6, -6.2), (4.4, -3.6), (7.6, -3.6)]):
    add_cyl(f"MV_PergolaPost{i}", (px, py, 1.2), 0.08, 2.4, M_WOOD, verts=10)
add_box("MV_PergolaBeamF", (6, -6.2, 2.46), (3.8, 0.12, 0.12), M_WOOD)
add_box("MV_PergolaBeamB", (6, -3.6, 2.46), (3.8, 0.12, 0.12), M_WOOD)
for i in range(6):
    add_box(f"MV_PergolaRafter{i}", (4.5 + i * 0.6, -4.9, 2.58),
            (0.08, 3.2, 0.08), M_WOOD)

# courtyard wall + pillars
add_box("MV_WallL", (-5.85, -9, 0.65), (8.9, 0.3, 1.3), M_STUCCO)
add_box("MV_WallR", ( 5.85, -9, 0.65), (8.9, 0.3, 1.3), M_STUCCO)
add_box("MV_WallCapL", (-5.85, -9, 1.34), (9.0, 0.42, 0.08), M_STONE)
add_box("MV_WallCapR", ( 5.85, -9, 1.34), (9.0, 0.42, 0.08), M_STONE)
for sgn in (-1, 1):
    s = 'L' if sgn < 0 else 'R'
    add_box(f"MV_Pillar{s}", (sgn * 1.4, -9, 0.9), (0.45, 0.45, 1.8), M_STUCCO)
    add_box(f"MV_PillarCap{s}", (sgn * 1.4, -9, 1.86), (0.6, 0.6, 0.12), M_STONE)

# ----- ANIMATED wrought-iron double gate (frames 10-100) -----
def gate_leaf(side):
    sgn = -1 if side == "L" else 1
    hinge_x = sgn * 1.18
    piv = add_empty(f"MV_GatePivot{side}", (hinge_x, -9, 0))
    inner = sgn * 0.06
    cxr = (hinge_x + inner) / 2
    wl = abs(hinge_x - inner) - 0.04
    parts = [
        add_box(f"MV_Gate{side}_railT", (cxr, -9, 1.5), (wl, 0.045, 0.05), M_IRON),
        add_box(f"MV_Gate{side}_railB", (cxr, -9, 0.32), (wl, 0.045, 0.05), M_IRON),
    ]
    for i in range(6):
        bx = hinge_x - sgn * (0.12 + i * 0.18)
        parts.append(add_cyl(f"MV_Gate{side}_bar{i}", (bx, -9, 0.91),
                             0.022, 1.22, M_IRON, verts=8))
        # spear finial
        parts.append(add_cone(f"MV_Gate{side}_tip{i}", (bx, -9, 1.62),
                              0.035, 0.12, M_IRON, verts=8))
    for p in parts:
        parent_keep(p, piv)
    piv.rotation_euler = (0, 0, 0)
    piv.keyframe_insert("rotation_euler", frame=10)
    piv.rotation_euler = (0, 0, math.radians(105) * (1 if side == "L" else -1))
    piv.keyframe_insert("rotation_euler", frame=100)

gate_leaf("L")
gate_leaf("R")

# cypress trees
for i, (tx, ty) in enumerate([(-6.5, -6.5), (-8.5, -4), (9.5, -7), (-7.5, 1)]):
    add_cyl(f"MV_CypressTrunk{i}", (tx, ty, 0.25), 0.08, 0.5, M_WOOD, verts=8)
    add_cone(f"MV_Cypress{i}", (tx, ty, 2.1), 0.55, 3.3, M_LEAF, verts=8)

# ---------------- light / sky / camera / timeline ----------------
bpy.ops.object.light_add(type='SUN', location=(8, -12, 14),
                         rotation=(math.radians(52), math.radians(8),
                                   math.radians(38)))
sun = bpy.context.active_object
sun.name = "MV_Sun"
sun.data.energy = 3.5
sun.data.color = (1.0, 0.95, 0.85)
to_coll(sun)

world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("MV_World")
    bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.55, 0.72, 0.90, 1.0)
    bg.inputs[1].default_value = 1.0

target = add_empty("MV_CamTarget", (0, -1, 2.6))
bpy.ops.object.camera_add(location=(14, -16, 7))
cam = bpy.context.active_object
cam.name = "MV_Camera"
to_coll(cam)
tc = cam.constraints.new(type='TRACK_TO')
tc.target = target
bpy.context.scene.camera = cam

sc = bpy.context.scene
sc.frame_start = 1
sc.frame_end = 240
sc.render.fps = 24
sc.frame_set(1)

print("Mediterranean villa generated:",
      len(VILLA.objects), "objects — gate opens fr 10-100, shutters fr 20-90.")
