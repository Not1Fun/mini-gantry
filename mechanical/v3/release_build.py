"""从同一加工特征表导出零件、采购表和发布索引。"""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,hashlib,json,math,re,shutil
import cadquery as cq
from build import make_model,assembly,render,bounds,CFG,ROOT,OUT,DRAW,VERIFY,dump


def local_shape(p):
    s=p['shape'];m=p['manufacturing']
    for key,plane in [('mirror_about_x_mm','YZ'),('mirror_about_z_mm','XY')]:
        if key in m:s=s.mirror(plane,(m[key],0,0) if plane=='YZ' else (0,0,m[key]))
    if 'module_placement' in m:
        a=m['module_placement'];location=cq.Location(cq.Plane(origin=a['origin'],xDir=a['axes'][0],normal=a['axes'][2]));s=s.moved(location.inverse)
    axes=m.get('axes',[[1,0,0],[0,1,0],[0,0,1]])
    if 'rotation_x_deg' in m:
        a=math.radians(m['rotation_x_deg']);axes=[[1,0,0],[0,math.cos(a),math.sin(a)],[0,-math.sin(a),math.cos(a)]]
    location=cq.Location(cq.Plane(origin=m.get('origin_mm',[0,0,0]),xDir=axes[0],normal=axes[2]));return s.moved(location.inverse)


def signature(p,shape):
    exclude={'origin_mm','axes','module_placement','mirror_about_x_mm','mirror_about_z_mm','rotation_x_deg'}
    spec={k:v for k,v in p['manufacturing'].items() if k not in exclude}
    geometry=dict(volume=round(shape.Volume(),4),vertices=sorted(tuple(round(q,5) for q in v.Center().toTuple()) for v in shape.Vertices()),
                  edges=sorted(round(e.Length(),5) for e in shape.Edges()))
    return hashlib.sha256(json.dumps([spec,geometry],sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def engineering(parts):
    mass={a:sum(p['mass_kg'] for p in parts if a in p['motion'] and p['motion']!='fixed') for a in 'XYZ'}
    speeds=[100,100,20];accel=[300,300,100];friction=[8,12,15];checks={}
    for i,axis in enumerate('XYZ'):
        lead=[42,36,5][i]/1000;force=mass[axis]*(accel[i]/1000+(9.81 if axis=='Z' else 0))+friction[i]
        inertia=[.00002,.00003,.00006][i];raw=force*lead/(2*math.pi*.9)+inertia*2*math.pi*(accel[i]/1000)/lead+(.05 if axis=='Z' else 0)
        checks[axis]=dict(moving_mass_estimate_kg=round(mass[axis],3),linear_force_N=round(force,3),speed_mm_s=speeds[i],acceleration_mm_s2=accel[i],
                          motor_mm_per_rev=lead*1000,motor_rpm=speeds[i]/(lead*1000)*60,required_motor_torque_Nm_with_factor_2=round(raw*2,4),
                          status='TORQUE_CURVE_OR_BENCH_TEST_REQUIRED_BEFORE_POWERED_1KG_OPERATION')
    E=69000;span=820;I=719000;weak=198000
    beam_vertical=mass['X']*9.81*span**3/(48*E*I);beam_side=checks['X']['linear_force_N']*span**3/(48*E*weak)
    # 双608输入轴是小径过悬负载控制项；44N安装上限计算，另加驱动力差。
    input_F=100;input_M=input_F*25.5;input_sigma=32*input_M/(math.pi*8**3)*2.2
    output_M=math.hypot(150*18.5,100*51);output_sigma=32*output_M/(math.pi*12**3)*2.2
    zforce=mass['Z']*9.81;hold=zforce*.005/(2*math.pi)
    drop_t=.04;v=.02;drop=v*drop_t+9.81*drop_t**2/2;energy=mass['Z']*9.81*drop+mass['Z']*v*v/2
    data=dict(status='CALCULATED_PROTOTYPE_DESIGN_BASIS_NOT_LOAD_CERTIFICATION',payload_gripper_plus_item_kg=1,
              axes=checks,frame=dict(span_mm=span,E_N_mm2=E,Istrong_mm4=I,Iweak_mm4=weak,
              bridge_gravity_deflection_mm=beam_vertical,bridge_lateral_deflection_mm=beam_side,
              note='简支梁上界估算；不包含接头、导轨安装误差和皮带柔度，不能据此承诺重复定位精度'),
              shafts=dict(input_D8=dict(radial_design_N=input_F,overhang_mm=25.5,bending_with_notch_factor_2_2_MPa=input_sigma,
                   minimum_material_yield_MPa=650,static_factor=650/input_sigma,
                   fatigue_basis='Rm>=850，估算耐久极限0.5Rm，表面/尺寸/可靠性折减0.75*0.85*0.9；与缺口放大应力比较',
                   estimated_endurance_margin=850*.5*.75*.85*.9/input_sigma),
                   X_D12=dict(two_plane_bending_Nmm=output_M,bending_with_notch_factor_2_2_MPa=output_sigma,required_yield_MPa=355,static_factor=355/output_sigma),
                   Y_D16=dict(radial_conservative_N=350,overhang_mm=70,bending_notch_MPa=32*350*70/(math.pi*16**3)*2.2,
                   note='减速轮到左轴承过悬与主带合成保守校核；右支承外圈0.6mm轴向浮动，容纳热伸长')),
              Z_brake=dict(rated_static_torque_Nm=1,gravity_backdrive_torque_Nm=hold,static_margin=1/hold,
                   allowed_single_brake_energy_J=2,assumed_total_power_loss_to_engagement_s=drop_t,computed_drop_mm=drop*1000,computed_energy_J=energy,
                   requirement='40ms包含驱动、线圈消磁和机械闭合；必须实测。超时或能量超过2J时禁止以当前电路进行垂直运行；不是已验证的防坠结果'),
              screw=dict(root_diameter_mm=13,unsupported_length_mm=793,elastic_modulus_N_mm2=206000,
                   euler_N=math.pi**2*206000*(math.pi*13**4/64)/(793**2),note='按两端铰支压杆保守估计；低速240rpm，丝杆厂家仍须保证C7端加工同轴'),
              main_belt=dict(preload_target_per_span_N=60,preload_tolerance_N=5,installation_method='配套张力计，左右Y带保持同张力；不靠顶丝扭矩估张力',
                   X_cut_pitch_length_mm=1470,Y_each_cut_pitch_length_mm=1770,clamp_teeth_each_end=7,idler_adjustment_mm=[-4,4]),
              reduction_belt=dict(preload_per_span_N=40,tolerance_N=4,manufacturer_10mm_range_N=[35.1,47.4],
                   X='100S3M192',Y='100S3M246',source='https://global.mitsuboshi.com/assetFiles/timing_belt_design_manual_en.pdf'),
              limitations=['数值是设计校核，未进行实体载荷/疲劳/重复定位试验','端部限位和缓冲件是越程保护；正常轨迹必须在工作边界前完成减速','走线拖链、急停回路和动力接口不在机械加工图中完成电气验证'])
    dump(VERIFY/'engineering_v3.json',data);return data


def procurement(parts):
    rows=defaultdict(lambda:dict(quantity=0,members=[]));seen=set()
    for p in parts:
        n=p['name'];group=None
        if p['role'] in ('fabricated','cut_profile'):
            if p.get('manufacturing',{}).get('type') not in ('purchased_finish','ballscrew_end_machining'):continue
        if 'ENVELOPE' in n or n in ('RM_A_or_RA6M5_RESERVE','compute_component_clearance'):continue
        if n in ('z_screw_1605','z_fixed_ballnut'):group='z_ball_screw_set';spec='TBI 1605-C7 + SFNU01605-4 成套；按V3轴端图定制893.5总长，螺母预装交货'
        elif '_coupling_' in n:group=n.split('_coupling_')[0]+'_coupling';spec='NBK MJC-25CS-RD-5-8 整套'
        elif n in ('z_brake_stator','z_brake_hub'):group='z_brake';spec='MIKI BXW-03-10H-24V-8 整套，含原配轮毂'
        elif n in ('z_screw_support_1','z_screw_locknut'):group='z_BK12';spec='HIWIN BK12-C7原厂总成，含锁紧件'
        elif re.match(r'[xy]_main_belt_\d_\d$',n):group=n.rsplit('_',1)[0];spec=p['spec']
        elif p['kind']=='motor' and n.startswith('motor_'):spec='张大头42 V2；31x31/4-M3，D5轴，本体不超过60mm；运行力矩见校核表'
        elif n.startswith('compute_standoff_') and p['role']!='fastener' and not n.endswith('_washer'):spec='M2.5x10双内牙绝缘支柱'
        else:spec=p['spec']
        if group and group in seen:
            rows[spec]['members'].append(n);continue
        if group:seen.add(group)
        rows[spec]['quantity']+=1;rows[spec]['members'].append(n)
    pattern=re.compile(r'^(frame_corner_.*_M8_\d|accessory_cross_joint_.*_M8_\d|(?:side|rear)_brace_.*_M8_\d|[xy]_bracket_M6_\d|y_support_\d_M6_\d|[xy]_tension_\d_frame_M6_\d|[XY]_stop_.*_M6_\d|Y_sensor_mount_\d_M6_\d|y_base_.*_M6_\d|x_base_.*_M5_\d|z_backplate_M6_\d|z_saddle_M5_\d|bridge_riser_\d_M8|compute_tray_M5_\d|controller_tray_M6_\d|camera_frame_M5_\d|Z_striker_\d_M6_\d)$')
    nuts=Counter(p['connection']['diameter'] for p in parts if p['role']=='fastener' and pattern.match(p['name']) and '端面M8' not in p['connection']['joint'])
    for d,q in nuts.items():rows[f'MISUMI HNTT8-{d:g} 预装T螺母']['quantity']=q
    return [dict(spec=k,**v) for k,v in sorted(rows.items())]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--no-render',action='store_true');ap.add_argument('--no-assembly',action='store_true');args=ap.parse_args()
    for d in (OUT,DRAW,VERIFY,OUT/'parts'):d.mkdir(parents=True,exist_ok=True)
    parts=make_model(CFG['assumptions']['illustration_pose_mm']);print('MODEL',len(parts),flush=True)
    assert len(parts)==len({p['name'] for p in parts}) and all(p['shape'].isValid() for p in parts)
    groups={};mapping={};records=[]
    for p in sorted(parts,key=lambda p:p['name']):
        if p['role']!='fabricated':continue
        shape=local_shape(p);key=signature(p,shape)
        if key not in groups:
            number=f'MG3-{len(groups)+1:03d}';filename=number+'_'+p['name']+'.step'
            cq.exporters.export(shape,str(OUT/'parts'/filename))
            groups[key]=dict(part_number=number,representative=p['name'],file='cad/parts/'+filename,quantity=0,members=[],
                             manufacturing=p['manufacturing'],local_bbox_mm=bounds(shape),geometry_signature=key,volume_mm3=shape.Volume())
        r=groups[key];r['quantity']+=1;r['members'].append(p['name']);mapping[p['name']]=r['part_number']
        if p['name']=='camera_removable_panel':cq.exporters.export(shape,str(OUT/'camera_adapter_blank.stl'),tolerance=.05,angularTolerance=.15)
    for p in parts:records.append({k:v for k,v in p.items() if k!='shape'}|dict(bbox_mm=bounds(p['shape']),part_number=mapping.get(p['name']),volume_mm3=p['shape'].Volume()))
    expected={Path(r['file']).name for r in groups.values()};scratch=ROOT.parents[2]/'v3_obsolete_exports';scratch.mkdir(exist_ok=True)
    for path in (OUT/'parts').glob('*.step'):
        if path.name in expected:continue
        assert path.resolve().parent==(OUT/'parts').resolve()
        dest=scratch/path.name;count=0
        while dest.exists():count+=1;dest=scratch/(str(count)+'_'+path.name)
        assert dest.resolve().parent==scratch.resolve();shutil.move(str(path),str(dest))
    release=json.loads((ROOT/'release.json').read_text(encoding='utf-8'))
    manifest=dict(revision=release['revision'],status=release['status'],units='mm',general_tolerances=dict(linear_up_to_300_mm='+/-0.1',linear_over_300_mm='+/-0.2',CNC_hole_position_mm='+/-0.05',
                  through_hole_diameter='+0.10/0 unless specified',threads='内螺纹6H，外螺纹6g；盲孔按有效牙深，底孔深度由工艺避让控制',
                  edges='去毛刺，未注锐边C0.3；不倒导轨安装定位边',surface='未注Ra3.2；定位/贴合面Ra1.6；轴承颈Ra0.8',
                  finish='6061无色阳极5~10um，配合孔/轴承面/螺纹遮蔽；45钢和42CrMo发黑薄油；Q235B感应片镀锌'),
                  model_policy='STEP为名义几何。螺纹牙型、皮带齿形及采购内部省略；螺纹必须按标注加工，不按名义大径钻孔。装配几何不作公差依据。',parts=list(groups.values()))
    dump(ROOT/'manufacturing.json',manifest);dump(ROOT/'bom.json',dict(stage=release['status'],items=records,procurement=procurement(parts)))
    cut=Counter((p['manufacturing']['profile'],p['manufacturing']['length_mm']) for p in parts if p['role']=='cut_profile')
    dump(ROOT/'cutlist.json',dict(items=[dict(profile=a,length_mm=b,quantity=q,tolerance_mm=.2) for (a,b),q in sorted(cut.items())],
                                end_work='940长的两根4040底侧梁与两根4080顶侧梁，两端截面(20,20)芯孔各M8有效18/底孔22；4080从截面下边计只攻下排孔。Z滑枕800长件下端两个芯孔M8有效20/底孔24。其余端面不攻丝。'))
    engineering(parts)
    if not args.no_assembly:
        dest=OUT/'mini_gantry_v3.step';assembly(parts).save(str(dest));loaded=cq.importers.importStep(str(dest)).val()
        checks=dict(valid=loaded.isValid(),source_solids=sum(len(p['shape'].Solids()) for p in parts),imported_solids=len(loaded.Solids()),
                    volume_difference_mm3=loaded.Volume()-sum(p['shape'].Volume() for p in parts))
        dump(VERIFY/'step_roundtrip.json',checks);assert checks['valid'] and checks['source_solids']==checks['imported_solids'] and abs(checks['volume_difference_mm3'])<1
    if not args.no_render:
        visible=[p for p in parts if p['role']!='fastener' and not p['name'].endswith('_washer')]
        render(visible,'assembly.png')
        for name,box_,prefixes in [('z_drive_stack.png',((350,580),(310,470),(1250,1570)),('z_','motor_Z')),('xy_reduction.png',((30,350),(800,1010),(860,1150)),('y_','motor_Y')),('camera_mount.png',((350,550),(-110,80),(870,1060)),('camera',))]:
            render(visible,name,zoom=box_,prefixes=prefixes,title='V3 加工接口',subtitle='以正式加工图与零件编号为准')
    dump(VERIFY/'neutral_build.json',dict(status='PASS_NEUTRAL_EXPORT',components=len(parts),fabricated_unique_parts=len(groups),fabricated_instances=len(mapping)))
    print('EXPORT',len(groups),'unique manufactured parts',flush=True)


if __name__=='__main__':main()
