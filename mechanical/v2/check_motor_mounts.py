"""安装孔、连接接触面和传动布局保持性检查。"""
import json
from itertools import product
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from build import ROOT,CFG,make_model,bounds,cylinder
from motor_mounts import z_holes
from z_drive import TOP_PLATE_BOTTOM
from xy_drive import CENTERS


def distance(a,b):
    q=BRepExtrema_DistShapeShape(a.wrapped,b.wrapped);q.Perform();return q.Value()


def main():
    x,y,z=CFG['assumptions']['illustration_pose_mm'];yc=y+100
    model={p['name']:p for p in make_model((x,y,z))}
    s=lambda n:model[n]['shape']
    checks={};contract=CFG['unchanged_transmission_reference']
    for old in contract['items']:
        shape=s(old['name'])
        checks['unchanged_'+old['name']]=(max(abs(a-b) for a,b in zip(bounds(shape),old['bbox_mm']))<.0002 and abs(shape.Volume()-old['volume_mm3'])<.01)
    checks['xy_reduction_unchanged']=CFG['assumptions']['xy_motor_reduction']==contract['xy_ratio']
    for axis,name,face,normal in [('X','x_motor_bracket',(90,yc+57,1100+CENTERS["X"]),(0,1,0)),('Y','y_motor_bracket',(149,880,984+CENTERS["Y"]),(1,0,0)),('Z','z_motor_mount',(x,yc-74,z+TOP_PLATE_BOTTOM),(0,0,1))]:
        t=7 if axis=='Z' else 3
        for i,(a,b) in enumerate(product((-15.5,15.5),repeat=2)):
            p=(face[0]+a,face[1],face[2]+b) if axis=='X' else ((face[0],face[1]+a,face[2]+b) if axis=='Y' else (face[0]+a,face[1]+b,face[2]))
            checks[f'{axis}_mount_hole_{i}']=s(name).intersect(cylinder(p,1.70,t,normal)).Volume()<1e-5
        checks[axis+'_pilot_clear']=s(name).intersect(cylinder(face,11,t,normal)).Volume()<1e-5
        checks[axis+'_motor_no_bracket_overlap']=s(name).intersect(s('motor_'+axis+'_ZDT42V2')).Volume()<.01
    for a,b in [('x_motor_bracket','bridge_4080'),('y_motor_bracket','top_cross_1'),('z_motor_lower_saddle','z_ram_4080'),('z_motor_standoff_0','z_motor_mount'),('z_motor_standoff_1','z_motor_mount'),('z_motor_standoff_0','z_motor_lower_saddle'),('z_motor_standoff_1','z_motor_lower_saddle')]:
        checks[a+'_contacts_'+b]=distance(s(a),s(b))<1e-6
    for a,b in [('x_motor_bracket','x_pulley_0'),('x_motor_bracket','x_pulley_axle_0'),('x_motor_bracket','x_pulley_mount_0'),('y_motor_bracket','y_sync_shaft'),('z_motor_lower_saddle','z_screw_support_1')]:
        checks[a+'_clears_'+b]=s(a).intersect(s(b)).Volume()<.01
    for i,(xx,yy) in enumerate(z_holes(x,yc)):
        checks[f'Z_top_M4_{i}']=s('z_motor_mount').intersect(cylinder((xx,yy,z+TOP_PLATE_BOTTOM),2.20,7)).Volume()<1e-5
    result={'status':'PASS_MOTOR_MOUNT_INTERFACES' if all(checks.values()) else 'FAIL','checks':checks,
            'motor_thread_engagement_mm':{'X':6-3,'Y':6-3,'Z':10-7},
            'motor_minimum_thread_depth_from_user_image_mm':4,
            'scope':'支架接口检查；减速器和制动器/联轴器仍为占位，不包含焊缝强度、公差链或实物安装验收'}
    (ROOT/'validation/motor_mounts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(result['status'],{k:v for k,v in checks.items() if not v},flush=True)
    assert all(checks.values())


if __name__=='__main__':main()
