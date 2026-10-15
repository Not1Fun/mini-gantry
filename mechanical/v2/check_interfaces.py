"""校核双孔组、单板配置和摄像头面板拆卸通道。"""
import json
import math
import cadquery as cq
from build import ROOT, make_model, cylinder
from accessories import holes, compute_plate, camera_panel, camera_carrier, camera_pose


def main():
    plate=compute_plate();checks={};models={}
    for key in ('pi4b','jetson_nano'):
        pts=holes(key)
        checks[key+'_holes_clear']=all(plate.intersect(cylinder((u,v,0),1.40,3)).Volume()<1e-6 for u,v in pts)
        model=make_model(compute_board=key);models[key]=model
        checks[key+'_single_board']=len([p for p in model if p['name'].startswith('compute_board_')])==1
        checks[key+'_four_standoffs']=len([p for p in model if p['name'].startswith('compute_standoff_')])==4
        checks[key+'_no_DM']=not any(p['name'].startswith(('DM_','wrist_')) for p in model)
        checks[key+'_fixed_accessories']=all(p['motion']=='fixed' for p in model if p['name'].startswith(('camera_','compute_')))
    panel=camera_panel();carrier=camera_carrier()
    checks['camera_four_mount_holes']=all(panel.intersect(cylinder((u,v,5),1.65,3)).Volume()<1e-6 for u in (-50,50) for v in (-40,40))
    checks['camera_frame_panel_clear']=panel.intersect(carrier).Volume()<1e-6
    model=models['pi4b']
    moving=[p for p in model if p['name'] in ('camera_removable_panel','camera_body_ENVELOPE','camera_lens_ENVELOPE')]
    fixed=[p for p in model if p['name'].startswith('camera_') and p not in moving and not p['name'].startswith('camera_panel_screw_')]
    collisions=[]
    for distance in (0,10,30,60,100):
        delta=(0,-.5*distance,math.cos(math.pi/6)*distance)
        for a in moving:
            for b in fixed:
                v=a['shape'].translate(delta).intersect(b['shape']).Volume()
                if v>.1:collisions.append({'distance_mm':distance,'moving':a['name'],'fixed':b['name'],'volume_mm3':v})
    checks['camera_sampled_removal_path']=not collisions
    old=json.loads((ROOT.parent/'v1/validation/engineering.json').read_text(encoding='utf-8'))
    new=json.loads((ROOT/'validation/engineering.json').read_text(encoding='utf-8'))
    report={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'camera_removal_collisions':collisions,
            'pi4b_hole_centers_local_mm':holes('pi4b'),'nano_hole_centers_local_mm':holes('jetson_nano'),
            'z_mass_v1_kg':old['axes']['Z']['moving_mass_estimate_kg'],'z_mass_v2_kg':new['axes']['Z']['moving_mass_estimate_kg'],
            'z_mass_reduction_estimate_kg':round(old['axes']['Z']['moving_mass_estimate_kg']-new['axes']['Z']['moving_mass_estimate_kg'],3),
            'scope':'板卡孔位几何、互斥配置、移除4颗面板螺钉后的5个拆卸位置；不证明实际相机兼容、视野、线缆或板卡散热'}
    (ROOT/'validation/interfaces.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(report['status'],checks,flush=True)
    assert all(checks.values())


if __name__=='__main__':main()
