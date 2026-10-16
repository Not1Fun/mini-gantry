"""可制造轴系；局部t轴沿轴线，采购件只表达安装外形。"""
import math
from itertools import product
import cadquery as cq
from fabrication import box,cyl,pose,hole,plate,CONFIG
from xy_drive import CENTERS,belt_wire


def ring(p,od,ind,length):return cyl(p,od/2,length).cut(cyl(p,ind/2,length))


def key_shape(width,start,end,bottom,height):
    s=box((-width/2,bottom,start+width/2),(width,height,end-start-width))
    for zz in (start+width/2,end-width/2):s=s.fuse(cyl((0,bottom,zz),width/2,height,(0,1,0)))
    return s


def part(name,s,motion,spec,material='6061-T6',manufacturing=None,mass=None,kind='drive'):
    return dict(name=name,shape=s,kind=kind,motion=motion,spec=spec,
                role='fabricated' if manufacturing else 'catalog_part',
                mass_kg=round(s.Volume()*(7.85e-6 if material in ('45钢','42CrMo','Q235B','轴承钢') else 1.2e-6 if material in ('PA66','PETG','PU90A') else 2.7e-6) if mass is None else mass,4),
                **({'manufacturing':dict(material=material,**manufacturing)} if manufacturing else {}))


def turned(name,steps,origin,motion,bores=(),axes=None,material='45钢',notes=(),extra=None):
    s=None
    for lo,hi,d in steps:
        a=cyl((0,0,lo),d/2,hi-lo);s=a if s is None else s.fuse(a)
    for lo,hi,d in bores:s=s.cut(cyl((0,0,lo),d/2,hi-lo))
    axes=axes or ((1,0,0),(0,1,0),(0,0,1))
    return part(name,pose(s,origin,*axes),motion,'车削件；尺寸见轴段表',material,
                dict(type='turned',steps_mm=steps,bores_mm=bores,origin_mm=origin,axes=axes,notes=list(notes),**(extra or {})),kind='screw')


def fastener(name,origin,direction,d,length,motion,washer=0,thread_depth=None,joint='',style='socket'):
    head_d={2.5:4.5,3:5.5,4:7,5:8.5,6:10,8:13}[d];head_h=d
    v=cq.Vector(*direction);p=cq.Vector(*origin)
    # origin是被连接件表面；垫圈位于负轴方向，螺杆长度从垫圈外侧开始。
    start=p-v*washer
    shaft=cq.Solid.makeCylinder(d/2,length,start,v)
    if style=='countersunk':
        head_d=2*d;head_h=(head_d-d)/2
        head=cq.Solid.makeCone(head_d/2,d/2,head_h,p,v)
        shaft=cq.Solid.makeCylinder(d/2,length-head_h,p+v*head_h,v)
    else:head=cq.Solid.makeCylinder(head_d/2,head_h,start-v*head_h,v)
    item=part(name,shaft.fuse(head),motion,f'M{d}x{length:g} '+('ISO10642沉头' if style=='countersunk' else 'ISO4762内六角'),material='45钢',kind='screw')
    item['role']='fastener';item['connection']=dict(diameter=d,length=length,washer=washer,engagement=thread_depth,joint=joint,style=style)
    out=[item]
    if washer:
        od=21 if d==8 and washer==3 else {2.5:6,3:7,4:9,5:10,6:12,8:16}[d]
        sh=cq.Solid.makeCylinder(od/2,washer,start,v).cut(cq.Solid.makeCylinder((d+.4)/2,washer,start,v))
        standard='DIN7349' if d==8 and washer==3 else 'ISO7089'
        out.append(part(name+'_washer',sh,motion,f'{standard} M{d} / {washer:g}厚','45钢',kind='screw'))
    return out


def input_module(axis,tcp):
    _,y,_=tcp;yc=y+100;tag=axis.lower();out=[];motion='Y' if axis=='X' else 'fixed'
    origin=(90,yc+75,1100+CENTERS['X']) if axis=='X' else (152,920,984+CENTERS['Y'])
    axes=((-1,0,0),(0,0,1),(0,1,0)) if axis=='X' else ((0,1,0),(0,0,1),(1,0,0))
    def transform(p):
        p['shape']=pose(p['shape'],origin,*axes)
        if 'manufacturing' in p:p['manufacturing']['module_placement']={'origin':origin,'axes':axes}
        return p
    def add(p):out.append(transform(p))
    hs=[hole(30,30,10.5)]
    hs += [hole(30+u,30+v,4,'M4',10,side='bottom',note='穿安装架及前盖M4x16') for u,v in product((-15.5,15.5),repeat=2)]
    hs += [hole(30+u,30+v,3,'M3',8,side=side) for u,v in product((-24,24),repeat=2) for side in ('top','bottom')]
    edges=[dict(point=[u,30+v,t-3],direction=[1 if u==0 else -1,0,0],diameter=4,depth=10,thread='M4') for u,v,t in product((0,60),(-20,20),(10,20))]
    p=plate(tag+'_input_housing',(60,60,24),(-30,-30,3),hs,edge_holes=edges,motion=motion,
            notes=['两端D22 H7沉孔各7深；两孔同轴度D0.015；前端固定、后端外圈可轴向滑动','轴承座前后基面平行度0.02；后盖D22.2x0.2避让提供外圈浮动'])
    for tt in (3,20):p['shape']=p['shape'].cut(cyl((0,0,tt),11,7))
    p['manufacturing']['stepped_bores']=[dict(u=30,v=30,diameter='22 H7',depth=7,side=s) for s in ('bottom','top')]
    add(p)
    for side,t,cd in [('front',0,14),('rear',27,20)]:
        hs=[hole(30,30,cd)]+[hole(30+u,30+v,3.4,csk=(6.3,90) if side=='front' else None,side='bottom' if side=='front' else 'top') for u,v in product((-24,24),repeat=2)]
        if side=='front':hs += [hole(30+u,30+v,4.5) for u,v in product((-15.5,15.5),repeat=2)]
        p=plate(tag+'_input_'+side+'_cover',(60,60,3),(-30,-30,t),hs,motion=motion)
        if side=='rear':
            p['shape']=p['shape'].cut(cyl((0,0,27),11.1,.2));p['manufacturing']['stepped_bores']=[dict(u=30,v=30,diameter=22.2,depth=.2,side='bottom')]
        add(p)
        for j,(u,v) in enumerate(product((-24,24),repeat=2)):
            for q in fastener(f'{tag}_input_cover_{side}_M3_{j}',(u,v,t if side=='front' else t+3),(0,0,1 if side=='front' else -1),3,10,motion,thread_depth=7,joint='端盖到输入座',style='countersunk' if side=='front' else 'socket'):add(q)
    for i,t in enumerate((3,20)):
        add(part(f'{tag}_input_608_{i}',ring((0,0,t),22,8,7),motion,'NSK 608ZZ / 8x22x7','轴承钢',mass=.0121,kind='block'))
    add(turned(tag+'_input_inner_spacer',[(10,20,10)],(0,0,0),motion,[(10,20,8.2)],notes=['L10 +/-0.005；两端平行度0.005；只接触轴承内圈']))
    steps=[(-27.5,-3.5,8),(-3.5,3,12),(3,27,8),(27,28,6.5),(28,37,8),(37,38,6.5),(38,52,8)]
    p=turned(tag+'_input_shaft',steps,(0,0,0),motion,[(-27.5,-19.5,3)],material='42CrMo',notes=['42CrMo调质后精加工；材质证明Rp0.2>=650MPa、Rm>=850MPa；轴承段D8 j5，联轴器段D8 h7，带轮段D8 h7','基准A为两轴承颈公共轴线；输出轴径圆跳动0.015；轴肩端跳0.01；R0.2，表面Ra0.8','M8x1.25-6g有效段t28~37；退刀D6.5；端部M3有效8，底孔10深','键槽2 P9，轴槽深1.2；配GB1096 A型键2x2x8；轮毂槽深1.0'],extra=dict(keyways=[dict(t0=-12.5,t1=-4.5,width=2,depth=1.2)],threads=[dict(t0=28,t1=37,thread='M8x1.25-6g')]))
    p['shape']=p['shape'].cut(key_shape(2,-12.5,-4.5,2.8,4));add(p)
    add(part(tag+'_input_key',key_shape(2,-12.5,-4.5,2.8,2),motion,'GB1096 A 2x2x8','45钢',kind='screw'))
    add(turned(tag+'_input_end_spacer',[(-27.5,-26.5,12)],(0,0,0),motion,[(-27.5,-26.5,8.2)],notes=['L1 +/-0.02']))
    add(turned(tag+'_input_end_retainer',[(-29.5,-27.5,14)],(0,0,0),motion,[(-29.5,-27.5,3.4)],notes=['端部压板，M3x8连接输入轴']))
    for q in fastener(tag+'_input_retainer_M3',(0,0,-29.5),(0,0,1),3,8,motion,thread_depth=6,joint='输入带轮轴端压板'):add(q)
    add(part(tag+'_input_lock_washer',ring((0,0,27),16,8.4,1.6),motion,'ISO7089 M8 /1.6','45钢',kind='screw'))
    for i,t in enumerate((28.6,32.6)):
        s=cq.Workplane('XY').polygon(6,13/math.cos(math.pi/6)).extrude(4).val().translate((0,0,t)).cut(cyl((0,0,t),4,4))
        add(part(f'{tag}_input_locknut_{i}',s,motion,'ISO4035 M8薄螺母，双螺母对锁','45钢',kind='screw'))
    for n,t,d,L in [('shaft',40,8,12),('spider',52,12,10),('motor',62,5,12)]:
        add(part(tag+'_input_coupling_'+n,ring((0,0,t),25,d,L),motion,'NBK MJC-25CS-RD-5-8，整套采购',mass=.006 if n=='spider' else .014))
    hs=[hole(30,30,24)]+[hole(30+u,30+v,3.5) for u,v in product((-15.5,15.5),repeat=2)]
    edges=[dict(point=[u,30+v,3.5],direction=[1 if u==0 else -1,0,0],diameter=4,depth=10,thread='M4') for u,v in product((0,60),(-20,20))]
    add(plate(tag+'_input_motor_plate',(60,60,7),(-30,-30,77.5),hs,edge_holes=edges,motion=motion,notes=['D24与输入轴承公共轴线同轴度D0.05；安装时用芯轴对中后锁侧板']))
    for i,u in enumerate((-36,30)):
        hs=[hole(t-3,v+25,4.5) for t,v in product((10,20,81),(-20,20))]
        add(plate(f'{tag}_input_side_{i}',(81.5,50,6),(u,25,3),hs,axes=((0,0,1),(0,-1,0),(1,0,0)),motion=motion))
        for j,(t,v) in enumerate(product((10,20,81),(-20,20))):
            for q in fastener(f'{tag}_input_side_{i}_M4_{j}',(-36 if i==0 else 36,v,t),(1 if i==0 else -1,0,0),4,16,motion,.8,9.2,'侧板连接输入座/电机板'):add(q)
    from build import stepper_shape
    add(part('motor_'+axis+'_ZDT42V2',stepper_shape().translate((0,0,84.5)),motion,'42步进本体60+驱动11，D5轴，31x31 M3',mass=.528,kind='motor'))
    for i,(u,v) in enumerate(product((-15.5,15.5),repeat=2)):
        for q in fastener(f'{tag}_motor_M3_{i}',(u,v,77.5),(0,0,1),3,10,motion,thread_depth=3,joint='电机到7mm顶板'):add(q)
    return out


def z_floating(tcp):
    x,y,z=tcp;cy=y+18;out=[]
    hs=[hole(30,25,18)]
    edges=[dict(point=[30+dx,0,9],direction=[0,1,0],diameter=6.6,depth=34,thread=None) for dx in (-20,20)]
    hs += [hole(30+dx,25+dy,3,'M3',6,side='bottom') for dx,dy in product((-25,25),(-20,10))]
    p=plate('z_float_housing',(60,40,18),(x-30,cy-25,z+201),hs,edge_holes=edges,motion='XYZ',notes=['D26 H7孔从底面深14.15，外圈在206.85~215.15间浮动0.30','安装面Y0，轴心距25；座底到轴端肩距离14；孔轴线对安装面平行度0.02'])
    p['shape']=p['shape'].cut(cyl((x,cy,z+201),13,14.15))
    # 横向螺栓穿过完整座深，沉孔从外侧到Y+9，避免外侧头凸出过多。
    for dx in (-20,20):
        p['shape']=p['shape'].cut(cyl((x+dx,cy+9,z+210),5.5,6,(0,1,0)))
    p['manufacturing']['edge_holes']=[dict(point=[30+dx,40,9],direction=[0,-1,0],diameter=6.6,depth=40,counterbore=[11,6],thread=None) for dx in (-20,20)]
    p['manufacturing']['stepped_bores']=[dict(u=30,v=25,diameter='26 H7',depth=14.15,side='bottom')]
    # 重建横向通孔深度；只允许通孔连接背板M6。
    for dx in (-20,20):p['shape']=p['shape'].cut(cyl((x+dx,cy-25,z+210),3.3,40,(0,1,0)))
    out.append(p)
    hs=[hole(30,25,18)]+[hole(30+dx,25+dy,3.4) for dx,dy in product((-25,25),(-20,10))]
    out.append(plate('z_float_cover',(60,40,3),(x-30,cy-25,z+198),hs,motion='XYZ'))
    out.append(turned('z_float_outer_spacer',[(201,206.85,26)],(x,cy,z),'XYZ',[(201,206.85,18)],notes=['外径D26 g6；L5.85 +/-0.02；只接触外圈']))
    out.append(part('z_float_6000',ring((x,cy,z+207),26,10,8),'XYZ','NSK6000ZZ /10x26x8','轴承钢',mass=.019,kind='block'))
    clip=ring((x,cy,z+206),11.6,9.6,1).cut(box((x,cy-1,z+206),(7,2,1)))
    out.append(part('z_float_circlip',clip,'XYZ','DIN471 /10，槽D9.6/1.15','45钢',kind='screw'))
    for i,(dx,dy) in enumerate(product((-25,25),(-20,10))):out+=fastener(f'z_float_cover_M3_{i}',(x+dx,cy+dy,z+198),(0,0,1),3,8,'XYZ',thread_depth=5,joint='浮动座下盖')
    for i,dx in enumerate((-20,20)):out+=fastener(f'z_float_mount_M6_{i}',(x+dx,cy+9,z+210),(0,-1,0),6,40,'XYZ',thread_depth=6,joint='浮动座到Z背板')
    return out


def pulley(name,code,n,bw,bore,boss,flange,start,motion,origin,axes,style='B',key=4):
    # start为远离轮毂的端面；钢挡边为1mm包络，齿面按厂家OD表示。
    W=11 if bw==10 else 17;K=10 if style=='C' else 8
    r=n*3/(2*math.pi)-.381
    face_start=start+2;face_end=face_start+W
    s=ring((0,0,start),2*r,bore,W+4)
    s=s.fuse(ring((0,0,start),flange,bore,1))
    if style=='B':s=s.fuse(ring((0,0,face_end+1),flange,bore,1))
    hub_start=face_end if style=='C' else face_end+2
    s=s.fuse(ring((0,0,hub_start),boss,bore,K))
    hub_depth={2:1.,4:1.8,5:2.3}[key]
    s=s.cut(box((-key/2,bore/2-.05,start),(key,hub_depth+.05,hub_start+K-start)))
    set_d=3 if key==2 or boss-bore<=6 else 4
    radial=[]
    for side in (-1,1):
        point=[side*boss/2,0,hub_start+K/2];direction=[-side,0,0]
        s=s.cut(cyl(point,set_d/2,(boss-bore)/2+1,direction))
        radial.append(dict(point=point,direction=direction,thread=f'M{set_d}',depth=(boss-bore)/2+1))
    return part(name,pose(s,origin,*axes),motion,code+' / 成品孔键槽二次加工',material='原厂铝合金',manufacturing=dict(type='purchased_finish',base_code=code,
                origin_mm=origin,axes=axes,bore=f'{bore} H7',keyway_width=f'{key} JS9',hub_key_depth=hub_depth,
                axial_range=[start,hub_start+K],radial_thread=f'M{set_d}',radial_thread_t=hub_start+K/2,radial_holes=radial,
                notes=['采购原厂成品齿形及挡边，禁止按CAD光圆外形制造齿形','按孔径/键槽/紧定孔要求订制成品轮；齿槽中心与孔轴线圆跳动0.03','键承担扭矩；两个径向紧定孔避开键槽，螺钉限制轴向窜动并用中强度螺纹防松剂','28T小轮薄壁处使用M3；紧定螺钉不代替平键']))


def xy_pulleys(tcp):
    _,y,_=tcp;yc=y+100;out=[]
    for axis in 'XY':
        tag=axis.lower();motion='Y' if axis=='X' else 'fixed'
        axes=((-1,0,0),(0,0,1),(0,1,0)) if axis=='X' else ((0,1,0),(0,0,1),(1,0,0))
        virtual=(90,yc+75,1100) if axis=='X' else (152,920,984)
        c=CENTERS[axis];motororigin=(virtual[0],virtual[1],virtual[2]+c)
        out.append(pulley(tag+'_reduction_input_pulley','P20S3M0100CAL',20,10,8,23,23,-26.5,motion,motororigin,axes,'C',2))
        n,bore,boss,fd,key=(40,12,30,44,4) if axis=='X' else (60,16,39,61,5)
        out.append(pulley(tag+'_reduction_driven_pulley',f'P{n}S3M0100BAL',n,10,bore,boss,fd,-26.5,motion,virtual,axes,key=key))
        r,R=20*3/(2*math.pi),n*3/(2*math.pi)
        inside=belt_wire(c,r-.381,R-.381);outside=belt_wire(c,r+.579,R+.579)
        f=cq.Face.makeFromWires(outside,[inside]);s=cq.Solid.extrudeLinear(f.outerWire(),f.innerWires(),cq.Vector(0,0,10)).translate((0,0,-24))
        out.append(part(tag+'_reduction_belt',pose(s,virtual,*axes),motion,'100S3M'+('192' if axis=='X' else '246')+'；10宽，静预紧40 +/-4N',mass=.018,kind='belt'))
    axes=((-1,0,0),(0,0,1),(0,1,0))
    out.append(pulley('x_pulley_0','P28S3M0150BAL',28,15,12,18,31,17,'Y',(90,yc,1100),axes,key=4))
    axes=((0,1,0),(0,0,1),(1,0,0))
    p=pulley('y_pulley_0_1','P36S3M0150BAL',36,15,16,26,40,84.5,'fixed',(0,920,984),axes,key=5);out.append(p)
    q=dict(p);q['name']='y_pulley_1_1';q['shape']=p['shape'].mirror('YZ',(450,0,0));q['manufacturing']=dict(p['manufacturing'],mirror_about_x_mm=450);out.append(q)
    for p in list(out):
        m=p.get('manufacturing',{})
        if m.get('type')!='purchased_finish':continue
        d=int(m['radial_thread'][1:]);bore=float(m['bore'].split()[0]);wall=m['radial_holes'][0]['depth']-1
        length=max(L for L in (3,4,5,6,8,10) if L<=wall)
        for i,side in enumerate((-1,1)):
            s=cyl((side*bore/2,0,m['radial_thread_t']),d/2,length,(side,0,0));s=pose(s,m['origin_mm'],*m['axes'])
            if 'mirror_about_x_mm' in m:s=s.mirror('YZ',(m['mirror_about_x_mm'],0,0))
            out.append(part(p['name']+f'_set_{i}',s,p['motion'],f'DIN913 M{d}x{length}平端紧定；M3初装0.35N.m/M4初装0.8N.m，中强防松','45钢',kind='screw'))
    return out


def x_output(tcp):
    _,y,_=tcp;yc=y+100;out=[];org=(90,yc,1100);axes=((-1,0,0),(0,0,1),(0,1,0))
    # 本模块自制座采用Y为轴向，底面Z1080贴梁；底脚承托电机L座。
    s=box((50,yc-24,1080),(80,40,6)).fuse(box((69,yc-24,1086),(42,37,35)))
    s=s.cut(cyl((90,yc-24,1100),8.5,37,(0,1,0)))
    for yy in (yc-24,yc+5):s=s.cut(cyl((90,yy,1100),14,8,(0,1,0)))
    for xx in (60,120):s=s.cut(cyl((xx,yc,1080),3.3,6))
    features=[]
    for yy,sgn in ((yc-24,1),(yc+13,-1)):
        for xx,zz in product((74,106),(1090,1115)):
            s=s.cut(cyl((xx,yy,zz),1.5,8,(0,sgn,0)))
            features.append(dict(point=[xx-50,yy-(yc-24),zz-1080],direction=[0,sgn,0],diameter=3,depth=8,thread='M3'))
    out.append(part('x_output_housing',s,'Y','6061一体双6001支承座',manufacturing=dict(type='bearing_pedestal',origin_mm=[50,yc-24,1080],size_mm=[80,40,41],
             foot=[0,0,0,80,40,6],tower=[19,0,6,42,37,35],axis_local=[40,0,20],axis_direction=[0,1,0],
             through_bore=17,bearing_pockets=[dict(start=0,length=8,diameter='28 H7'),dict(start=29,length=8,diameter='28 H7')],edge_holes=features,
             mounting_holes=[dict(point=[u,24,0],diameter=6.6,depth=6) for u in (10,70)],notes=['两D28 H7轴承孔同轴D0.015；底面平面度0.02；轴线对底面平行度0.02','前端盖固定外圈，后端盖留0.20轴向浮动；本座与电机L座共用2-M6x25接横梁T螺母'])))
    for i,t in enumerate((-24,5)):
        out.append(part(f'x_output_6001_{i}',pose(ring((0,0,t),28,12,8),org,*axes),'Y','NSK6001ZZ /12x28x8','轴承钢',mass=.022,kind='block'))
    for i,t in enumerate((-27,13)):
        hs=[hole(21,14,18)]+[hole(u,v,3.4) for u,v in product((5,37),(4,29))]
        p=plate(f'x_output_cover_{i}',(42,35,3),(111,yc+t,1086),hs,axes=axes,motion='Y')
        if i:
            p['shape']=p['shape'].cut(cyl((90,yc+13,1100),14.1,.2,(0,1,0)));p['manufacturing']['stepped_bores']=[dict(u=21,v=14,diameter=28.2,depth=.2,side='bottom')]
        out.append(p)
        for j,(xx,zz) in enumerate(product((74,106),(1090,1115))):
            out+=fastener(f'x_output_cover_{i}_M3_{j}',(xx,yc+(t+3 if i else t),zz),(0,-1 if i else 1,0),3,10,'Y',thread_depth=7,joint='输出轴端盖')
    out.append(turned('x_output_shaft',[(-29,-24,16),(-24,73.5,12),(73.5,89,12)],org,'Y',axes=axes,
             notes=['45钢调质HB220-260；两轴承颈-24~-16、5~13为D12 j5，其余轮毂段D12 h6；轴颈同轴D0.015','轴肩端跳0.01；轴承颈Ra0.8；轴肩R0.3','轴末端M12x1-6g：73.5~89；两ISO8675 M12x1薄螺母对锁；垫圈ISO7089 M12/2.5厚；无外圈预压','4 P9键槽，深2.5；两个槽38~46和63.5~71.5，配4x4x8键'],extra=dict(keyways=[dict(t0=a,t1=b,width=4,depth=2.5) for a,b in ((38,46),(63.5,71.5))],threads=[dict(t0=73.5,t1=89,thread='M12x1-6g')])))
    shaft=out[-1]
    for i,(a,b) in enumerate(((38,46),(63.5,71.5))):
        shaft['shape']=shaft['shape'].cut(pose(key_shape(4,a,b,3.5,4),org,*axes))
        out.append(part(f'x_output_key_{i}',pose(key_shape(4,a,b,3.5,4),org,*axes),'Y','GB1096 A 4x4x8','45钢',kind='screw'))
    for i,(a,b,od) in enumerate(((-16,5,16),(13,17,16),(46,48.5,16),(71.5,73.5,18))):
        out.append(turned(f'x_output_spacer_{i}',[(a,b,od)],org,'Y',[(a,b,12.2)],axes=axes,notes=['内圈隔套，端面平行度0.005；长度+/-0.01；不接触外圈']))
    out.append(part('x_output_washer',pose(ring((0,0,73.5),24,13,2.5),org,*axes),'Y','ISO7089 M12 /D24/D13/2.5厚','45钢',kind='screw'))
    for i,t in enumerate((76,82)):
        s=cq.Workplane('XY').polygon(6,18/math.cos(math.pi/6)).extrude(6).val().translate((0,0,t)).cut(cyl((0,0,t),6,6))
        out.append(part(f'x_output_nut_{i}',pose(s,org,*axes),'Y','ISO8675 M12x1 /AF18/6厚，双螺母对锁','45钢',kind='screw'))
    return out


def xy_brackets(tcp):
    _,y,_=tcp;yc=y+100;out=[]
    for axis in 'XY':
        if axis=='X':
            # 局部u沿X，v沿Y，w沿Z；L座从底脚朝后延伸。
            origin=(45,yc-20,1086);width=90;depth=95;height=108;axis_u=45;axis_z=14;motor_z=14+CENTERS['X'];motion='Y'
            s=box((0,0,0),(width,depth,8)).fuse(box((0,depth-8,8),(width,8,height-8)))
            s=s.cut(box((21,0,0),(48,90,8)))
            mounts=[(15,20),(75,20)];window=[21,0,48,90];axis_hole=32
        else:
            # 与X相同的局部接口：u沿-Y，v沿+X，w沿Z。
            origin=(40,960,906);width=80;depth=112;height=172;axis_u=40;axis_z=78;motor_z=78+CENTERS['Y'];motion='fixed'
            s=box((0,0,0),(width,depth,8)).fuse(box((0,depth-8,8),(width,8,height-8)))
            s=s.cut(box((16,0,0),(48,48,8))).cut(box((64,0,0),(16,10,8)));mounts=[(40,70),(40,95)];window=[16,0,48,48];axis_hole=42
        s=s.cut(cyl((axis_u,depth-8,axis_z),axis_hole/2,8,(0,1,0)))
        slots=[(axis_u,motor_z,30,24)]+[(axis_u+a,motor_z+b,10.5,4.5) for a,b in product((-15.5,15.5),repeat=2)]
        for u,v,L,W in slots:
            cut=cq.Workplane('XY').center(u,v).slot2D(L,W,90).extrude(8).val()
            s=s.cut(pose(cut,(0,depth,0),(1,0,0),(0,0,1),(0,-1,0)))
        for u,v in mounts:s=s.cut(cyl((u,v,0),3.3,8))
        axes=((1,0,0),(0,1,0),(0,0,1)) if axis=='X' else ((0,-1,0),(1,0,0),(0,0,1))
        out.append(part(axis.lower()+'_motor_bracket',pose(s,origin,*axes),motion,'6061-T6 一体CNC L座 /8厚',manufacturing=dict(type='machined_motor_angle',origin_mm=origin,axes=axes,size_mm=[width,depth,height],thickness=8,
                 additional_base_reliefs=[] if axis=='X' else [[64,0,16,10,8]],
                 window=window,mount_holes=[dict(u=u,v=v,diameter=6.6) for u,v in mounts],face_slots=[dict(u=u,v=v,length=L,width=W) for u,v,L,W in slots],shaft_hole=dict(u=axis_u,v=axis_z,diameter=axis_hole),
                 notes=['内底角允许R3，插接件不经过内角；安装底面与输入座贴面垂直度0.05/100','输入座沿竖槽调节+/-3；先张紧后锁4-M4x20，保持皮带两轮共面0.1','底部2-M6连接HNTT8-6；X穿8+6底脚用M6x25；Y穿8用M6x20，均加1.6垫圈'])))
        # 钢架改为一体CNC铝L座，避免薄钢架焊接变形；接口保持一致。
        for j,(u,v) in enumerate(mounts):
            pt=pose(cyl((u,v,8),.1,.1),origin,*axes).Center().toTuple();pt=(pt[0],pt[1],pt[2]-.05)
            out+=fastener(axis.lower()+f'_bracket_M6_{j}',pt,(0,0,-1),6,25,motion,1.6,9.4,'电机L座经6mm支承底脚到型材')
        for j,(u,v) in enumerate(product((-15.5,15.5),repeat=2)):
            pt=(90+u,yc+67,1100+CENTERS['X']+v) if axis=='X' else (144,920+u,984+CENTERS['Y']+v)
            out+=fastener(axis.lower()+f'_cartridge_M4_{j}',pt,(0,1,0) if axis=='X' else (1,0,0),4,20,motion,.8,8.2,'输入模块经11mm座板连接壳体')
    return out


def y_output():
    out=[];org=(0,920,984);axes=((0,1,0),(0,0,1),(1,0,0))
    shaft=turned('y_sync_shaft',[(44,55,15),(55,56,13.5),(56,84.5,15),(84.5,815.5,16),(815.5,844,15),(844,845,13.5),(845,856,15)],org,'fixed',axes=axes,
          notes=['45钢调质HB220-260；总长812；中段D16 h6，两轴承颈67~78/822~833为D15 j5','两端M15x1-6g，各11长；55~56与844~845退刀D13.5；轴颈同轴D0.02，端肩跳动0.01','三键槽5 P9，深3；配5x5平键；轴承颈Ra0.8；轴肩R0.3','左右内圈分别靠中段轴肩与隔套定位；左右各2-KM2对锁，先贴合消隙再对锁，不施加额外轴承预紧；右外圈允许0.6轴向浮动'],extra=dict(keyways=[dict(t0=a,t1=b,width=5,depth=3) for a,b in ((101.5,113.5),(140.5,148.5),(786.5,798.5))],threads=[dict(t0=44,t1=55,thread='M15x1-6g'),dict(t0=845,t1=856,thread='M15x1-6g')]))
    for i,(a,b) in enumerate(((101.5,113.5),(140.5,148.5),(786.5,798.5))):
        shaft['shape']=shaft['shape'].cut(pose(key_shape(5,a,b,5,5),org,*axes))
        out.append(part(f'y_output_key_{i}',pose(key_shape(5,a,b,5,5),org,*axes),'fixed',f'GB1096 A 5x5x{b-a:g}','45钢',kind='screw'))
    out.append(shaft)
    for i in (0,1):
        def mirror(p):
            if i:
                p['shape']=p['shape'].mirror('YZ',(450,0,0))
                if 'manufacturing' in p:p['manufacturing']['mirror_about_x_mm']=450
            return p
        s=box((40,900,900),(112,40,6)).fuse(box((62,896,906),(20,48,106)))
        s=s.cut(cyl((62,920,984),10.5,20,(1,0,0))).cut(cyl((62,920,984),17.5,16.3 if i else 16,(1,0,0)))
        for xx in (52,110,135):s=s.cut(cyl((xx,920,900),3.3,6))
        feats=[]
        for yy,zz in product((900,940),(964,1004)):
            s=s.cut(cyl((62,yy,zz),1.5,8,(1,0,0)));feats.append(dict(point=[22,yy-896,zz-900],direction=[1,0,0],diameter=3,depth=8,thread='M3'))
        p=part(f'y_rear_support_{i}',s,'fixed','6061一体后轴支承座；6202',manufacturing=dict(type='bearing_pedestal',origin_mm=[40,896,900],size_mm=[112,48,112],
               foot=[0,4,0,112,40,6],tower=[22,0,6,20,48,106],axis_local=[22,24,84],axis_direction=[1,0,0],through_bore=21,
               bearing_pockets=[dict(start=22,length=16.3 if i else 16,diameter='35 H7')],edge_holes=feats,
               mounting_holes=[dict(point=[u,24,0],diameter=6.6,depth=6) for u in (12,70,95)],
               notes=['右件为左件关于X450镜像；右座孔台阶比左座深0.3，右盖定位台阶比左短0.3','底面平面度0.03；轴线高度84 +/-0.02，孔轴线与底面平行度0.02；两座装配用芯轴找正','左座远端2孔与电机L座共用M6x25；外端用M6x16；右座三孔均M6x16，配1.6垫圈/HNTT8-6']))
        out.append(mirror(p))
        depth=4.7 if i else 5
        s=box((59,896,960),(3,48,48)).fuse(cyl((62,920,984),17.5,depth,(1,0,0)))
        s=s.cut(cyl((59,920,984),10.5,3+depth,(1,0,0)))
        for yy,zz in product((900,940),(964,1004)):s=s.cut(cyl((59,yy,zz),1.7,3,(1,0,0)))
        out.append(mirror(part(f'y_rear_cover_{i}',s,'fixed','6202外圈定位盖',manufacturing=dict(type='boss_cover',origin_mm=[59,896,960],size_mm=[3+depth,48,48],plate_thickness=3,axis_direction=[1,0,0],center=[0,24,24],boss_diameter='35 g6',boss_length=depth,through_bore=21,
                    face_holes=[dict(u=u,v=v,diameter=3.4) for u,v in product((4,44),repeat=2)],notes=['左凸台5，右凸台4.7；右外圈轴向总游隙0.6，不加预紧垫片']))))
        out.append(mirror(part(f'y_rear_bearing_{i}',cyl((67,920,984),17.5,11,(1,0,0)).cut(cyl((67,920,984),7.5,11,(1,0,0))),'fixed','NSK6202ZZ /15x35x11','轴承钢',mass=.045,kind='block')))
        for j,(a,b) in enumerate(((57,67),(78,84.5))):out.append(mirror(turned(f'y_rear_spacer_{i}_{j}',[(a,b,20)],org,'fixed',[(a,b,15.2)],axes=axes,notes=['只接触内圈；长度+/-0.01；两端平行度0.005'])))
        out.append(mirror(turned(f'y_rear_washer_{i}',[(55,57,24)],org,'fixed',[(55,57,15.3)],axes=axes,notes=['45钢轴端垫圈2厚'])) )
        for j,t in enumerate((45,50)):
            s=ring((0,0,t),25,15,5)
            for a in (0,90,180,270):s=s.cut(box((-2,10.5,t),(4,3,5)).rotate((0,0,0),(0,0,1),a))
            out.append(mirror(part(f'y_rear_KM2_{i}_{j}',pose(s,org,*axes),'fixed','SKF KM2 /M15x1/25x5，成对对锁','45钢',mass=.009,kind='screw')))
        for j,(yy,zz) in enumerate(product((900,940),(964,1004))):
            for p in fastener(f'y_cover_{i}_M3_{j}',(59,yy,zz),(1,0,0),3,10,'fixed',thread_depth=7,joint='后支承外圈盖'):out.append(mirror(p))
        for j,xx in enumerate((52,) if i==0 else (52,110,135)):
            for p in fastener(f'y_support_{i}_M6_{j}',(xx,920,906),(0,0,-1),6,16,'fixed',1.6,8.4,'后支承到型材'):out.append(mirror(p))
    return out
