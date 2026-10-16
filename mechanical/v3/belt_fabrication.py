"""开口主带与固定接口；夹板使用原厂齿形。"""
import math
from itertools import product
import cadquery as cq
from fabrication import box,cyl,pose,hole,plate,CONFIG,CATALOG
from drive_fabrication import part,fastener,turned


def main_belts(tcp):
    x,y,z=tcp;yc=y+100;out=[]
    for axis in 'XY':
        cfg=CONFIG['main_belt_detail'][axis];r=cfg['output_teeth']*3/(2*math.pi)
        starts=[(90,yc+27.5,1100)] if axis=='X' else [(95,59,984),(805,59,984)]
        C=cfg['center_distance'];moving=x-90 if axis=='X' else yc-59;gap=cfg.get('center_gap',CONFIG['main_belt_detail']['center_gap'])/2
        for index,org in enumerate(starts):
            axes=((1,0,0),(0,0,1),(0,-1,0)) if axis=='X' else ((0,1,0),(0,0,1),(1,0,0))
            tag=axis.lower()+f'_main_belt_{index}'
            bottom=box((0,-r-.479,-7.5),(C,.86,15))
            left=box((0,r-.381,-7.5),(moving-gap,.86,15))
            right=box((moving+gap,r-.381,-7.5),(C-moving-gap,.86,15))
            pieces=[bottom,left,right]
            for u,sgn in ((0,-1),(C,1)):
                s=cyl((u,0,-7.5),r+.479,15).cut(cyl((u,0,-7.5),r-.381,15))
                s=s.intersect(box((u-(r+2 if sgn==-1 else 0),-r-2,-7.5),(r+2,2*r+4,15)));pieces.append(s)
            for j,s in enumerate(pieces):out.append(part(tag+f'_{j}',pose(s,org,*axes),'Y' if axis=='X' else 'fixed',f"MISUMI HTBO-S3M150-{cfg['teeth']}；{cfg['cut_pitch_length']}mm；聚氨酯/钢芯，背厚0.86，齿形省略",mass=cfg['cut_pitch_length']/1000*.0243*1.5/5,kind='belt'))
    return out


def clamps(tcp):
    x,y,z=tcp;yc=y+100;out=[]
    for axis in 'XY':
        clamp_center=37.5 if axis=='X' else 40.5
        r=CONFIG['main_belt_detail'][axis]['output_teeth']*3/(2*math.pi)
        root=(1100 if axis=='X' else 984)+r-.381
        if axis=='X':
            # 下表面1100；两处沉台深度由带轮节圆与夹板4mm厚决定。
            hs=[hole(50+u,8,5.5) for u in (-40,-28,28,40)]
            hs += [hole(50+side*37.5+u,97.5+v,3,'M3',10) for side,u,v in product((-1,1),(-7.5,7.5),(-10,10))]
            p=plate('x_belt_bridge',(100,114,10),(x-50,yc-70,1100),hs,windows=[(31,0,38,8.5)],motion='XY',notes=['4-M5x20+1垫圈连接滑座顶边；两齿板座为21x30沉台，底Z由表给出','前缘38x8.5避让口给Z最低位BK12窄台留空间','两端各夹持21mm/7齿；夹板内端间隔54mm；压板浮动压紧，不设厚度硬止口'])
            depth=1110-(root-4)
            for side in (-1,1):p['shape']=p['shape'].cut(box((x+side*37.5-10.5,yc+12.5,root-4),(21,30,depth)))
            p['manufacturing']['face_pockets']=[dict(u=50+s*37.5-10.5,v=82.5,width=21,height=30,depth=depth) for s in (-1,1)]
            out.append(p)
            for i,u in enumerate((-40,-28,28,40)):out+=fastener(f'x_bridge_M5_{i}',(x+u,yc-62,1110),(0,0,-1),5,20,'XY',1,9,'主带跨梁板接X滑座')
        for lane,axiscenter in enumerate((yc+27.5,) if axis=='X' else (95,805)):
            for side in (-1,1):
                tag=axis.lower()+f'_clamp_{lane}_{side}'
                if axis=='X':org=(x+side*clamp_center,yc+27.5,root-4);axes=((1,0,0),(0,1,0),(0,0,1));motion='XY'
                else:
                    # u沿Y，v沿-X：右手坐标，安装孔镜像由连接座统一定义。
                    org=(axiscenter,yc+side*clamp_center,root-4);axes=((0,1,0),(-1,0,0),(0,0,1));motion='Y'
                    base_x=55 if lane==0 else 790
                    thick=root-4-988
                    hs=[hole(axiscenter-base_x+v,15+u,3,'M3',thick) for u,v in product((-7.5,7.5),(-10,10))]
                    slots=[((65 if lane==0 else 835)-base_x,15,23.5,5.5,90)]
                    out.append(plate(tag+'_carrier',(55,30,thick),(base_x,yc+side*clamp_center-15,988),hs,slots=slots,motion=motion,
                              notes=['两M5x20+1垫圈共用23.5x5.5长槽接端板，入牙约10.2；四M3接齿板与压板','长槽沿Y微调+/-3，用于双边同步带相位校正；同侧前后两座必须同方向等量调整','先固定桥架方正、保持两带相同张力，再锁紧四M5；不能靠扭转贯通轴强迫桥架对齐','厚度精铣+/-0.03，使两侧夹持高度一致']))
                    for j,v in enumerate((-6,6)):out+=fastener(tag+f'_M5_{j}',(65 if lane==0 else 835,yc+side*clamp_center+v,root-4),(0,0,-1),5,20,motion,1,20-1-thick,'Y夹板相位微调槽连接端板')
                hs=[hole(10.5+u,15+v,3.4) for u,v in product((-7.5,7.5),(-10,10))]
                local=plate(tag+'_toothed',(21,30,4),(-10.5,-15,0),hs,motion=motion)
                local['shape']=pose(local['shape'],org,*axes);local['role']='catalog_part';local.pop('manufacturing');local['spec']='MISUMI C-TBCR-S3M150 /21x30x4，原厂齿形，未画齿槽';out.append(local)
                p=plate(tag+'_cap',(21,30,3),(-10.5,-15,4.86),hs,motion=motion,notes=['浮动压板；安装面Ra1.6，边缘倒钝R0.3；4-M3x16加0.5垫圈交叉均匀压紧','按HTBO聚氨酯带背厚0.86建立名义位置；压板浮动，确认7齿完全啮合'])
                p['shape']=pose(p['shape'],org,*axes);p['manufacturing']['module_placement']={'origin':org,'axes':axes};out.append(p)
                for j,(u,v) in enumerate(product((-7.5,7.5),(-10,10))):
                    for q in fastener(tag+f'_M3_{j}',(u,v,7.86),(0,0,-1),3,16,motion,.5,7.64,'浮动压板/原厂齿板/基座'):
                        q['shape']=pose(q['shape'],org,*axes);out.append(q)
    return out


def tensioners(tcp):
    _,y,_=tcp;yc=y+100;out=[]
    for axis,index in [('X',0),('Y',0),('Y',1)]:
        tag=axis.lower()+f'_tension_{index}';motion='Y' if axis=='X' else 'fixed'
        origin=(810,yc+27.5,1080) if axis=='X' else (95 if index==0 else 805,59,900)
        axes=((1,0,0),(0,1,0),(0,0,1)) if axis=='X' else ((0,-1,0),(1,0,0),(0,0,1))
        h=20 if axis=='X' else 84;cat=CATALOG['main_idler_'+axis];d=cat['shaft_bore'];screw_d=5 if axis=='X' else 8
        def add(p):
            p['shape']=pose(p['shape'],origin,*axes)
            if 'manufacturing' in p:p['manufacturing']['module_placement']={'origin':origin,'axes':axes}
            out.append(p)
        v0=-47.5 if axis=='X' else -30;bw=80 if axis=='X' else 60
        fixing=[(-38,-27.5),(38,-27.5)] if axis=='X' else [(39,-15),(39,15)]
        hs=[hole(50+u,v-v0,6.6,csk=(12.4,90)) for u,v in fixing]
        hs += [hole(50+u,v-v0,6,'M6',10) for u,v in product((-24,24),(-20,20))]
        hs += [hole(94 if axis=='X' else 6,v-v0,4,'M4',10) for v in (-20,20)]
        window=[(32,-12.6-v0,36,25.2)] if axis=='X' else []
        add(plate(tag+'_base',(100,bw,10),(-50,v0,0),hs,windows=window,motion=motion,
                  notes=['基板与滑台贴合面Ra1.6；四M6连接滑台，沿u调节+/-4；调好后锁紧','X基板中窗用于让位惰轮下缘，禁止填实；M6x20沉头接型材，进入槽10；头部不得高于基板']))
        for j,(u,v) in enumerate(fixing):
            for p in fastener(tag+f'_frame_M6_{j}',(u,v,10),(0,0,-1),6,20,motion,thread_depth=10,joint='张紧底板到HNTT8-6，沉头避让滑台',style='countersunk'):add(p)
        slots=[(36+u,28+v,14.6,6.6,0) for u,v in product((-24,24),(-20,20))]
        p=plate(tag+'_fork',(72,56,6),(-36,-28,10),windows=[(18,15.4,36,25.2)],slots=slots,motion=motion)
        sh=p['shape'].fuse(box((28 if axis=='X' else -36,-12,16),(8,24,10)))
        if axis=='X':
            sh=sh.cut(cyl((36,0,20),3,8,(-1,0,0)))
            p['manufacturing']['edge_holes']=[dict(point=[72,28,10],direction=[-1,0,0],diameter=6,depth=8,thread='M6',note='X外置拉紧螺钉')]
        for v in (-18.6,12.6):sh=sh.fuse(box((-12,v,16),(24,6,h+12-16))).cut(cyl((0,v,h),d/2,6,(0,1,0)))
        if axis=='X':
            sh=sh.cut(box((-6,-28,14),(12,56,2)))
            p['manufacturing']['face_pockets']=[dict(u=30,v=0,width=12,height=56,depth=2)]
        p['shape']=sh;p['mass_kg']=round(sh.Volume()*2.7e-6,4)
        p['manufacturing'].update(type='fork_carriage',fork_inner_width=25.2,fork_outer_width=37.2,ear_u_range=[24,48],ear_v_ranges=[[9.4,15.4],[40.6,46.6]],ear_height=h+12-10,
                                   axle_local=[36,0,h-10],axle_diameter=f'{d} H7',push_wall=[64 if axis=='X' else 0,16,6,8,24,10],
                                   notes=['整体CNC；双耳轴孔一次装夹铰削，同轴D0.02；内距25.2 +/-0.03','肩轴定位双耳，禁止用普通全牙螺栓直接夹紧两侧轴承内圈','惰轮及两隔套合计25.0；保留0.15~0.25轴向游隙，轴承不施加轴向预紧；调好后检查自由转动'])
        add(p)
        for j,(u,v) in enumerate(product((-24,24),(-20,20))):
            for p in fastener(tag+f'_clamp_M6_{j}',(u,v,16),(0,0,-1),6,16,motion,1.6,8.4,'张紧滑台到基板'):add(p)
        # 只改变轴向位置，不自行拆卸采购惰轮的压装轴承。
        wheel=cyl((0,-10.5,h),cat['OD']/2,21,(0,1,0))
        for v in (-10.5,9.5):wheel=wheel.fuse(cyl((0,v,h),cat['flange_D']/2,1,(0,1,0)))
        wheel=wheel.cut(cyl((0,-10.5,h),d/2,21,(0,1,0)))
        add(part(tag+'_idler',wheel,motion,cat['model']+'，带原装轴承；不拆压装轴承',mass=.045 if axis=='X' else .075))
        axle_axes=((1,0,0),(0,0,-1),(0,1,0))
        steps=[(-22.6,-18.6,d+4),(-18.6,18.6,d),(18.6,30.6,screw_d)]
        axle=turned(tag+'_axle',steps,(0,0,h),motion,axes=axle_axes,notes=[f'45钢调质；肩轴D{d} g6，肩长37.2 +0.02/0；端部M{screw_d}x1' if screw_d==5 else '45钢调质；肩轴D10 g6，肩长37.2 +0.02/0；端部M8x1.25',
                  '两肩端面平行度0.01；过渡退刀宽0.6，圆角R0.2；肩轴端面承靠垫圈限制夹紧量','头部开4mm六角内孔3深；轴承颈Ra0.8，头和螺纹端不喷漆'],extra=dict(threads=[dict(t0=18.6,t1=30.6,thread=f'M{screw_d}')],hex_socket=[4,3]))
        socket=cq.Workplane(cq.Plane(origin=(0,-22.6,h),xDir=(1,0,0),normal=(0,1,0))).polygon(6,4/math.cos(math.pi/6)).extrude(3).val()
        axle['shape']=axle['shape'].cut(socket);add(axle)
        for j,t in enumerate((-12.5,10.5)):
            add(turned(tag+f'_spacer_{j}',[(t,t+2,d+3)],(0,0,h),motion,[(t,t+2,d+.2)],axes=axle_axes,notes=['L2 +/-0.01，平行度0.01；仅接触轴承内圈']))
        washer_t=1 if screw_d==5 else 1.6
        add(part(tag+'_axle_washer',pose(cyl((0,0,18.6),(screw_d+5)/2,washer_t).cut(cyl((0,0,18.6),(screw_d+.3)/2,washer_t)),(0,0,h),*axle_axes),motion,f'ISO7089 M{screw_d}','45钢',kind='screw'))
        nut=cyl((0,18.6+washer_t,h),(screw_d+5)/2,screw_d,(0,1,0)).cut(cyl((0,18.6+washer_t,h),screw_d/2,screw_d,(0,1,0)))
        add(part(tag+'_axle_nut',nut,motion,f'ISO10511 M{screw_d}尼龙锁紧螺母','45钢',kind='screw'))
        hs=[hole(4,25+v,4.5) for v in (-20,20)]
        edge=[dict(point=[0,25,10],direction=[1,0,0],diameter=6.6 if axis=='X' else 6,depth=8,thread=None if axis=='X' else 'M6')]
        add(plate(tag+'_adjuster',(8,50,20),(40 if axis=='X' else -48,-25,10),hs,edge_holes=edge,motion=motion,notes=['X中孔6.6通孔配M6x30拉紧螺钉；Y中孔M6配顶丝；四M6锁紧承担运行剪力']))
        for j,v in enumerate((-20,20)):
            for p in fastener(tag+f'_adjuster_M4_{j}',(44 if axis=='X' else -44,v,30),(0,0,-1),4,30,motion,.8,9.2,'调节块到基板'):add(p)
        if axis=='X':
            for p in fastener(tag+'_pull_M6',(48,0,20),(-1,0,0),6,30,motion,1.6,8,'X外置拉紧螺钉，向+X张紧'):add(p)
        else:
            for p in fastener(tag+'_push_M6',(-66,0,20),(1,0,0),6,30,motion,joint='Y调节顶丝，顶端到u-36'):add(p)
            nut=cyl((-53,0,20),5,5,(1,0,0)).cut(cyl((-53,0,20),3,5,(1,0,0)))
            add(part(tag+'_push_locknut',nut,motion,'ISO4032 M6 /5厚，锁紧调节螺钉','45钢',kind='screw'))
    return out
