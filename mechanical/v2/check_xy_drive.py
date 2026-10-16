"""减速级节线闭合、标称干涉、长孔调节及检修通道。"""
from itertools import product
import json
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from build import ROOT,CFG,make_model,bounds,cylinder
from xy_drive import CFG as XY,CENTERS,belt_wire,locate,motor_position


def intersect(a,b):
    aa,bb=bounds(a),bounds(b)
    if not all(min(aa[k+3],bb[k+3])-max(aa[k],bb[k])>1e-5 for k in range(3)):return 0
    return a.intersect(b).Volume()


def distance(a,b):
    q=BRepExtrema_DistShapeShape(a.wrapped,b.wrapped);q.Perform();return q.Value()


def main():
    pose=CFG['assumptions']['illustration_pose_mm'];yc=pose[1]+100
    parts=make_model(pose);by={p['name']:p for p in parts}
    shape=lambda n:by[n]['shape']
    names={p['name'] for p in parts if p['role']=='xy_drive_interface'}|{'x_motor_bracket','y_motor_bracket','motor_X_ZDT42V2','motor_Y_ZDT42V2'}
    collisions=[]
    for i,a in enumerate(parts):
        for b in parts[i+1:]:
            if a['name'] not in names and b['name'] not in names:continue
            v=intersect(a['shape'],b['shape'])
            if v>.01:collisions.append({'a':a['name'],'b':b['name'],'overlap_mm3':round(v,5)})
    rows=[];tools=[];slots=[]
    import math
    for axis in ('X','Y'):
        s=XY[axis];r,R=[t*3/(2*math.pi) for t in s['teeth']];c=CENTERS[axis];a=s['belt_axial_d_mm'][0];tag=axis.lower()
        path=belt_wire(c,r,R)
        rows.append({'axis':axis,'teeth':s['teeth'],'ratio':s['teeth'][1]/s['teeth'][0],
                     'center_distance_mm':c,'cad_pitch_wire_length_mm':path.Length(),'belt_pitch_length_mm':s['pitch_length_mm'],
                     'small_pulley_wrap_degrees':180-2*math.degrees(math.asin((R-r)/c)),
                     'engaged_teeth_geometric':s['teeth'][0]*(math.pi-2*math.asin((R-r)/c))/(2*math.pi)})
        for delta in (-3,0,3):
            hits=[]
            moving=[by['motor_'+axis+'_ZDT42V2'],by[tag+'_reduction_input_pulley'],by[tag+'_reduction_input_set_screw']]+[p for p in parts if p['name'].startswith(tag+'_motor_m3_')]
            skip={p['name'] for p in moving}|{tag+'_reduction_belt'}
            for p in moving:
                shifted=p['shape'].translate((0,0,delta))
                for other in parts:
                    if other['name'] in skip:continue
                    v=intersect(shifted,other['shape'])
                    if v>.01:hits.append([p['name'],other['name'],round(v,5)])
            slots.append({'axis':axis,'z_offset_mm':delta,'collisions':hits})
        input_start=(0,c-7.5,a-5) if axis=='X' else (-7.5,c,a-5)
        input_axis=(0,-1,0) if axis=='X' else (-1,0,0)
        for name,start,direction in [('input',input_start,input_axis),('driven',(0,s['output_hub_diameter_mm']/2+.5,a-5),(0,1,0))]:
            corridor=locate(cylinder(start,2,18,direction),axis,yc)
            hits=[]
            for p in parts:
                v=intersect(corridor,p['shape'])
                if v>.01:hits.append([p['name'],round(v,4)])
            tools.append({'axis':axis,'hub':name,'tool_diameter_mm':4,'straight_approach_mm':18,'collisions':hits})
    supports=[('x_pulley_mount_0','bridge_4080'),('y_rear_support_0','top_cross_1'),('y_rear_support_1','top_cross_1')]
    contacts={a:distance(shape(a),shape(b)) for a,b in supports}
    checks={'old_black_boxes_removed':not any(n in by for n in ('x_reducer','y_reducer')),
            'ratios_2_and_3': [r['ratio'] for r in rows]==[2,3],
            'pitch_paths_match_catalogue_lengths':all(abs(r['cad_pitch_wire_length_mm']-r['belt_pitch_length_mm'])<1e-5 for r in rows),
            'nominal_interfaces_do_not_overlap':not collisions,
            'slot_travel_clear':all(not r['collisions'] for r in slots),
            'radial_tool_corridors_clear':all(not r['collisions'] for r in tools),
            'support_feet_contact_frame':max(contacts.values())<1e-6}
    result={'status':'PASS_XY_REDUCTION_INTERFACE_LAYOUT' if all(checks.values()) else 'FAIL','checks':checks,
            'belt_geometry':rows,'collisions':collisions,'motor_adjustment':slots,'tool_access':tools,'support_contact_distance_mm':contacts,
            'remaining':['带轮真实齿形/轮毂/紧定螺钉须以供应商CAD匹配','轴承座配合、轴向尺寸链和轴环夹紧未做公差/预紧校核','6mm减速带额定能力、预紧力及电机轴径向载荷待选型计算','主长带前端惰轮、夹块、全行程走线及防护仍需细化'],
            'scope':'标称几何与装配调节范围；不代表负载、寿命、连续运动或防护验收。长孔端点用于装带/张紧空间，不把±3mm解释为皮带可伸长。'}
    (ROOT/'validation/xy_drive.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(result['status'],{k:v for k,v in checks.items() if not v},flush=True)
    if not all(checks.values()):print(collisions,slots,tools,flush=True);raise SystemExit(1)


if __name__=='__main__':main()
