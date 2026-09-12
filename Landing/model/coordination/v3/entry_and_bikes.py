"""Highlight the sample entry and arrange the shared bin/bicycle store."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from replicate_dwellings import bounds
from export_web import export
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-services-v22.blend'))
scene=bpy.context.scene
audit=dict(entry=[],bins=[],bikes=[])
for suffix in ('007','008','009','010','011'):
    obj=scene.objects['SLA - 007_Concrete - Foundation_0.'+suffix]
    obj['sw_reveal_dwelling']=2;audit['entry'].append(obj.name)
for name in ('V3 | Garage apron 2','V3 | Garage pedestrian crossing 2'):
    scene.objects[name]['sw_reveal_dwelling']=2;audit['entry'].append(name)

# Split the shared path at the sample frontage, preserving its thickness.
path=scene.objects['V3 | Building-side pedestrian path'];lo,hi=bounds(path)
for i,(ya,yb) in enumerate(((lo.y,-10.6085),(-10.6085,-4.866),( -4.866,hi.y))):
    obj=path.copy();obj.data=path.data.copy();scene.collection.objects.link(obj)
    obj.name=f'Site v23 | Pedestrian path segment {i+1}'
    inv=obj.matrix_world.inverted()
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co;p.y=ya+(p.y-lo.y)/(hi.y-lo.y)*(yb-ya);v.co=inv@p
    if i==1:obj['sw_reveal_dwelling']=2;audit['entry'].append(obj.name)
bpy.data.objects.remove(path,do_unlink=True)

delta=Vector((7.2,1.1,0))
for name in ('Site electricity pillar','Site pillar access panel'):
    scene.objects['V3 | Electrical | '+name].location+=delta
for obj in scene.objects:
    if obj.type!='CURVE' or obj.get('sw_system')!='electrical':continue
    if 'individual underground feed' not in obj.name and 'Underground street service to site pillar' not in obj.name:continue
    obj.data=obj.data.copy();inv=obj.matrix_world.inverted()
    for spline in obj.data.splines:
        for p in spline.points:
            v=obj.matrix_world@p.co.xyz
            if abs(v.y+21)<.001:
                v.y+=delta.y
                if abs(v.x+5)<.001:v.x+=delta.x
                p.co=(*(inv@v),p.co.w)

bins=sorted((o for o in scene.objects if o.name.startswith('V3 | Relocated bin ')),key=lambda o:int(o.name.rsplit(' ',1)[1]))
for i,obj in enumerate(bins):
    low,high=bounds(obj);obj.location.x+=-5.08+i*.55-(low.x+high.x)/2
    if i in (1,6):obj['sw_reveal_dwelling']=2
    audit['bins'].append(dict(name=obj.name,blue=i in (1,6)))

mat=scene.objects['V3 | Relocated bin 1'].data.materials[0]
def tube(name,points,radius,cycle=False):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.bevel_depth=radius;curve.bevel_resolution=2
    spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
    for p,co in zip(spline.points,points):p.co=(*co,1)
    spline.use_cyclic_u=cycle
    obj=bpy.data.objects.new(name,curve);scene.collection.objects.link(obj);curve.materials.append(mat)
    obj['sw_system']='civil';obj['sw_civil_surface']=True;obj['sw_illustrative']=True
    return obj

for bike,x in enumerate((.55,1.2),1):
    prefix=f'Site v23 | Bicycle {bike} | '
    def point(y,z,dx=0):return (x+dx,-20.4+y,.1+z)
    rear=point(0,.34);front=point(1.05,.34);crank=point(.43,.30);seat=point(.32,.82);head=point(.88,.86)
    for j,hub in enumerate((rear,front)):
        ring=[(hub[0],hub[1]+.32*math.cos(a*math.tau/48),hub[2]+.32*math.sin(a*math.tau/48)) for a in range(48)]
        tube(prefix+f'Tyre {j}',ring,.025,True)
        tube(prefix+f'Rim {j}',[(px,hub[1]+(py-hub[1])*.9,hub[2]+(pz-hub[2])*.9) for px,py,pz in ring],.012,True)
        for a in range(12):tube(prefix+f'Spoke {j}-{a}',[hub,ring[a*4]],.003)
    for j,(a,b) in enumerate(((rear,seat),(seat,crank),(crank,rear),(seat,head),(head,crank),(head,front))):tube(prefix+f'Frame {j}',[a,b],.022)
    tube(prefix+'Saddle',[point(.22,.89),point(.44,.89)],.045)
    tube(prefix+'Seat post',[seat,point(.32,.89)],.016)
    tube(prefix+'Handlebar stem',[head,point(.91,1.02)],.018)
    tube(prefix+'Handlebars',[point(.91,1.02,-.24),point(.91,1.02,.24)],.016)
    tube(prefix+'Crank',[point(.39,.23,-.10),crank,point(.47,.37,.10)],.015)
    tube(prefix+'Left pedal',[point(.39,.23,-.16),point(.39,.23,-.07)],.024)
    tube(prefix+'Right pedal',[point(.47,.37,.07),point(.47,.37,.16)],.024)
    tube(prefix+'Kickstand',[crank,point(.38,.03,.18)],.012)
    audit['bikes'].append(prefix)
bpy.context.view_layer.update()
assert len(bins)==10 and sum(b['blue'] for b in audit['bins'])==2
for a,b in zip(bins,bins[1:]):assert bounds(b)[0].x-bounds(a)[1].x>.045
assert bounds(bins[-1])[1].x<.13
assert abs(bounds(scene.objects['V3 | Electrical | Site electricity pillar'])[0].x-1.925)<.001
audit['pillar_centre']=[2.2,-19.9,.65]
scene['sw_entry_v23']=json.dumps(audit)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-entry-bikes-v23.blend'))
(HERE/'entry-v23-audit.json').write_text(json.dumps(audit,indent=2))
export(scene)
print('ENTRY_V23_PASS',json.dumps(audit),flush=True)
