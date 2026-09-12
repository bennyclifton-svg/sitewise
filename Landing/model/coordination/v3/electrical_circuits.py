"""Replace manifold-like branches with continuous, softly dressed cable circuits."""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
CEILINGS={'G':2.92,'L':5.64,'U':8.39}

def cable_points(waypoints):
    clean=[]
    for p in map(Vector,waypoints):
        if not clean or (p-clean[-1]).length>.00001:clean.append(p)
    rounded=[clean[0]]
    def span(end):
        start=rounded[-1]
        delta=end-start
        horizontal=abs(delta.z)<.01
        lateral=Vector((-delta.y,delta.x,0))
        if lateral.length:lateral.normalize()
        count=max(2,math.ceil(delta.length/.12))
        for j in range(1,count+1):
            t=j/count
            p=start.lerp(end,t)
            if horizontal:
                p+=lateral*.075*math.sin(math.pi*t)
                p.z-=.030*math.sin(math.pi*t)
            rounded.append(p)
    for a,b,c in zip(clean,clean[1:],clean[2:]):
        radius=min(.18,(b-a).length/3,(c-b).length/3)
        entry=b+(a-b).normalized()*radius
        exit_point=b+(c-b).normalized()*radius
        span(entry)
        for j in range(1,9):
            t=j/8
            rounded.append(entry*(1-t)**2+b*2*t*(1-t)+exit_point*t*t)
    span(clean[-1])
    return rounded

def build(scene):
    audit=json.loads((HERE/'electrical-audit.json').read_text())
    endpoints={p['id']:p for p in audit['endpoints']}
    circuits=[c for c in audit['circuits'] if c['family'] in ('lighting','power')]
    circuit_ids={c['id'] for c in circuits}
    switches=audit['switches']
    material=scene.objects['V3 | Electrical | DB-01 main vertical service riser'].data.materials[0]
    # Keep the raycast-mounted switches and fittings; replace only their cable routes.
    for obj in list(scene.objects):
        if obj.name.startswith('Circuit |') or (obj.type=='CURVE' and obj.get('sw_circuit_id') in circuit_ids):
            bpy.data.objects.remove(obj,do_unlink=True)
    routes=[]
    schedules=[]
    nodes={p['id']:p['world_xyz'] for p in audit['endpoints']}
    nodes.update({p['id']:p['world_xyz'] for p in switches})
    def cable(cid,a,b,waypoints,role,switch_id=''):
        points=cable_points(waypoints)
        data=bpy.data.curves.new(f'Circuit | {cid} | {a} to {b}', 'CURVE')
        data.dimensions='3D';data.bevel_depth=.010 if 'LIGHT' in cid else .014
        data.bevel_resolution=2;data.use_fill_caps=True
        spline=data.splines.new('POLY');spline.points.add(len(points)-1)
        for p,xyz in zip(spline.points,points):p.co=(*xyz,1)
        obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj)
        data.materials.append(material)
        obj['sw_system']='electrical';obj['sw_circuit_id']=cid
        obj['sw_route_role']=role;obj['sw_from']=a;obj['sw_to']=b
        if switch_id:obj['sw_switch_group']=switch_id
        routes.append({'object':obj.name,'circuit':cid,'from':a,'to':b,'role':role,
                       'switch':switch_id,'points':[list(p) for p in points]})
        assert (points[0]-Vector(nodes[a])).length<.0001
        assert (points[-1]-Vector(nodes[b])).length<.0001

    for circuit in circuits:
        cid,level,family=circuit['id'],circuit['level'],circuit['family']
        ceiling=CEILINGS[level]+(.048 if family=='lighting' else .070)
        west,east,south,north=audit['audit']['floor_envelopes'][level]['inner']
        def ceiling_anchor(point):
            return (max(west+.10,min(east-.10,point.x)),
                    max(south+.10,min(north-.10,point.y)),ceiling)
        feed=cid+'-FEED'
        nodes[feed]=[-2.9,-9.48,max(ceiling,2.97)]
        order=[]
        if family=='lighting':
            remaining=[s for s in switches if s['circuit']==cid]
            here=Vector(nodes[feed])
            # Keep each room together, then move to the nearest next room.
            while remaining:
                switch=min(remaining,key=lambda s:min((Vector(endpoints[e]['world_xyz'])-here).length for e in s['fixture_ids']))
                remaining.remove(switch)
                lamps=list(switch['fixture_ids'])
                while lamps:
                    nearest=min(lamps,key=lambda e:(Vector(nodes[e])-here).length)
                    lamps.remove(nearest);order.append(nearest);here=Vector(nodes[nearest])
        else:
            remaining=list(circuit['endpoint_ids']);here=Vector(nodes[feed])
            while remaining:
                nearest=min(remaining,key=lambda e:(Vector(nodes[e])-here).length)
                remaining.remove(nearest);order.append(nearest);here=Vector(nodes[nearest])
        previous=feed
        for endpoint in order:
            a,b=Vector(nodes[previous]),Vector(nodes[endpoint])
            # Each GPO loops up its wall, across the ceiling, then down to the next GPO.
            # Luminaire links follow the ceiling from fitting to fitting, with gentle slack.
            ca,cb=ceiling_anchor(a),ceiling_anchor(b)
            waypoints=[a,(ca[0],ca[1],a.z),ca,cb,(cb[0],cb[1],b.z),b]
            group=endpoints[endpoint].get('switch_group','')
            cable(cid,previous,endpoint,waypoints,'lighting-loop' if family=='lighting' else 'power-loop',group)
            previous=endpoint
        room_switches=[]
        if family=='lighting':
            for switch in [s for s in switches if s['circuit']==cid]:
                first=next(e for e in order if e in switch['fixture_ids'])
                a,b=Vector(nodes[first]),Vector(nodes[switch['id']])
                ca,cb=ceiling_anchor(a),ceiling_anchor(b)
                cable(cid,first,switch['id'],[a,ca,cb,(cb[0],cb[1],b.z),b],
                      'switch-live-and-return',switch['id'])
                room_switches.append({'switch':switch['id'],'room':switch['room'],'lights':switch['fixture_ids']})
        schedules.append({'id':cid,'level':level,'family':family,'board':'DB-01',
                          'feed':feed,'sequence':order,'room_switches':room_switches})

    # Gently dress the existing dedicated-appliance runs without moving their endpoints.
    for obj in scene.objects:
        if obj.type!='CURVE' or not str(obj.get('sw_circuit_id','')).startswith('DB-01-AP-') or obj.get('sw_route_category')!='concealed':continue
        if obj.get('sw_soft_cable'):continue
        original=[Vector(p.co[:3]) for p in obj.data.splines[0].points]
        points=cable_points(original)
        obj.data.splines.clear();spline=obj.data.splines.new('POLY');spline.points.add(len(points)-1)
        for p,xyz in zip(spline.points,points):p.co=(*xyz,1)
        obj.data.bevel_depth=.014;obj['sw_soft_cable']=True

    # Validate connectivity using sampled geometry and ensure every light has a room control.
    for circuit in schedules:
        connected={circuit['feed']};pending=[r for r in routes if r['circuit']==circuit['id']]
        while pending:
            joined=[r for r in pending if r['from'] in connected]
            assert joined, f"Disconnected circuit {circuit['id']}"
            for r in joined:
                connected.add(r['to']);pending.remove(r)
        assert set(circuit['sequence'])<=connected
    controlled=[e for s in switches for e in s['fixture_ids']]
    luminaires=[e['id'] for e in endpoints.values() if e['kind']=='luminaire']
    assert sorted(controlled)==sorted(luminaires)
    assert len([e for c in schedules if c['family']=='power' for e in c['sequence']])==24
    metadata={'circuits':schedules,'routes':routes,'nodes':nodes,
              'validation':{'lights':len(luminaires),'gpos':24,'room_switches':len(switches),
                            'connected_circuits':len(schedules),'endpoint_error_below':.0001},
              'notes':'Physical loop-in cable routing; loads are parallel, not electrically in series. Appliance circuits retained. Illustrative, not a conductor or protection design.'}
    (HERE/'electrical-circuits.json').write_text(json.dumps(metadata,indent=2))
    print('ELECTRICAL_CIRCUITS',metadata['validation'],flush=True)

if __name__=='__main__':
    from export_web import export
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-detail-v4.blend'))
    build(bpy.context.scene)
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    export(bpy.context.scene)
