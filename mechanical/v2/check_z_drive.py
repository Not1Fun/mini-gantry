"""Z局部同组干涉、插入深度与工具通道检查；X/Y占位问题单独列出。"""
from itertools import combinations
import json
from build import ROOT,CFG,make_model,bounds,cylinder
from z_drive import MOTOR_FACE,COUPLER_BOTTOM,COUPLER_TOP,SCREW_TIP


def main():
    x,y,z=CFG['assumptions']['illustration_pose_mm'];cy=y+26
    parts=make_model((x,y,z));p={v['name']:v for v in parts};shape=lambda n:p[n]['shape']
    drive=[v['name'] for v in parts if v['role']=='z_drive_interface']+['motor_Z_ZDT42V2']
    structure=[n for n in p if n.startswith(('z_motor_','z_top_','z_base_','z_saddle_')) or n=='z_ram_4080']
    pairs=set(tuple(sorted(v)) for v in combinations(drive,2))
    pairs.update(tuple(sorted((a,b))) for a in drive for b in structure if a!=b)
    checked=[]
    for a,b in sorted(pairs):
        aa,bb=bounds(shape(a)),bounds(shape(b))
        if not all(min(aa[k+3],bb[k+3])>=max(aa[k],bb[k]) for k in range(3)):continue
        v=shape(a).intersect(shape(b)).Volume()
        checked.append({'a':a,'b':b,'overlap_mm3':round(v,6)})
    motor_hub=bounds(shape('z_coupling_motor_hub'))
    screw_hub=bounds(shape('z_coupling_screw_hub'))
    screw=bounds(shape('z_screw_1605'))
    insert_motor=motor_hub[5]-(z+MOTOR_FACE-22.5)
    insert_screw=screw[5]-screw_hub[2]
    clearances={
        'motor_boss_to_coupling_axial':MOTOR_FACE-2-COUPLER_TOP,
        'top_plate_to_coupling_axial':MOTOR_FACE-7-COUPLER_TOP,
        'brake_to_coupling_axial':COUPLER_BOTTOM-1053,
        'locknut_to_brake_axial':1023-1021,
        'shaft_end_to_end_axial':MOTOR_FACE-22.5-SCREW_TIP,
        'coupling_to_side_plate_radial':30-12.5}
    tool_rows=[]
    for name,zz in [('lower_hub',COUPLER_BOTTOM+6),('upper_hub',COUPLER_TOP-6)]:
        corridor=cylinder((x+9,cy+13,z+zz),2.5,60,(0,1,0))
        hits=[]
        for part in parts:
            overlap=corridor.intersect(part['shape']).Volume()
            if overlap>.01:hits.append({'name':part['name'],'volume_mm3':round(overlap,4)})
        tool_rows.append({'hub':name,'tool_diameter_mm':5,'approach_length_mm':60,
                          'approach':'+Y开放侧；联轴器转到夹紧螺钉可达方位','hits':hits})
    checks={
        'local_rigid_parts_no_intersection':all(r['overlap_mm3']<.01 for r in checked),
        'motor_hub_insertion_12mm':abs(insert_motor-12)<.001,
        'screw_hub_insertion_12mm':abs(insert_screw-12)<.001,
        'positive_separation_margins':min(clearances.values())>0,
        'open_side_tool_corridors_clear':all(not r['hits'] for r in tool_rows),
        'valid_z_solids':all(shape(n).isValid() for n in drive),
        '500mm_each_axis_preserved':[b-a for a,b in zip(CFG['assumptions']['tcp_min_mm'],CFG['assumptions']['tcp_max_mm'])]==[500,500,500]}
    xy=[]
    for axis in ('x','y'):
        xy.append({'axis':axis.upper(),'state':'PENDING_REAL_REDUCTION_ASSEMBLY',
                   'envelope_vs_bracket_overlap_mm3':round(shape(axis+'_reducer').intersect(shape(axis+'_motor_bracket')).Volume(),3),
                   'reason':'减速组件仍是整体空间占位，不能按此黑盒加工；需拆为带轮/皮带/轴承/轴及张紧机构后检查'})
    result={'status':'PASS_Z_DRIVE_INTERFACE_LAYOUT' if all(checks.values()) else 'FAIL',
            'checks':checks,'clearance_mm':clearances,'shaft_insertion_mm':{'motor':insert_motor,'screw':insert_screw},
            'checked_local_pairs':checked,'tool_access':tool_rows,'xy_followup':xy,
            'remaining_interfaces':['Z支承座外形及轴肩/锁紧螺纹待真实供应商图纸冻结','制动器转子与D10轴的连接、反力支架和壳体固定孔尚未细化','联轴器为目录尺寸包络；真实夹紧缝、螺钉及齿爪应以厂家CAD核对'],
            'scope':'标称刚体几何检查；不是连续运动、公差、强度、制动可靠性或实物装配验收'}
    (ROOT/'validation/z_drive.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(result['status'],{k:v for k,v in checks.items() if not v},flush=True)
    assert all(checks.values()),[r for r in checked if r['overlap_mm3']>.01]


if __name__=='__main__':main()
