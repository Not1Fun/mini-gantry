"""加工几何与可追溯特征表；坐标为mm，板件局部Z为厚度方向。"""
from pathlib import Path
from itertools import product
import json
import math
import cadquery as cq

ROOT=Path(__file__).resolve().parent
CONFIG=json.loads((ROOT/'design.json').read_text(encoding='utf-8'))
DATUM=CONFIG['manufacturing_datums']
CATALOG=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))


def box(p,d):return cq.Solid.makeBox(*d,cq.Vector(*p))
def cyl(p,r,h,axis=(0,0,1)):return cq.Solid.makeCylinder(r,h,cq.Vector(*p),cq.Vector(*axis))
def pose(s,origin,u=(1,0,0),v=(0,1,0),w=(0,0,1)):
    plane=cq.Plane(origin=origin,xDir=u,normal=w)
    assert (plane.yDir-cq.Vector(*v)).Length<1e-8,'坐标系必须为右手系'
    return s.moved(cq.Location(plane))


def hole(u,v,d,kind='through',depth=None,cbore=None,csk=None,side='top',note=''):
    return dict(u=u,v=v,diameter=d,kind=kind,depth=depth,counterbore=cbore,countersink=csk,side=side,note=note)


def plate(name,size,origin,holes=(),outline=None,windows=(),axes=None,material='6061-T6',motion='fixed',notes=(),edge_holes=(),slots=()):
    a,b,t=size
    s=box((0,0,0),(a,b,t)) if outline is None else cq.Workplane('XY').polyline(outline).close().extrude(t).val()
    for u,v,ww,hh in windows:s=s.cut(box((u,v,0),(ww,hh,t)))
    for u,v,length,width,angle in slots:
        s=s.cut(cq.Workplane('XY').center(u,v).slot2D(length,width,angle).extrude(t).val())
    for h in holes:
        depth=t if h['kind']=='through' or h['depth'] is None else h['depth']
        z0=t-depth if h['side']=='top' else 0
        s=s.cut(cyl((h['u'],h['v'],z0),h['diameter']/2,depth))
        if h['counterbore']:
            dd,deep=h['counterbore'];zz=t-deep if h['side']=='top' else 0
            s=s.cut(cyl((h['u'],h['v'],zz),dd/2,deep))
        if h['countersink']:
            dd,angle=h['countersink'];deep=(dd-h['diameter'])/2/math.tan(math.radians(angle/2))
            recess=h.get('head_recess',0)
            if recess:s=s.cut(cyl((h['u'],h['v'],t-recess if h['side']=='top' else 0),(dd+.2)/2,recess))
            if h['side']=='top':
                cone=cq.Solid.makeCone(h['diameter']/2,dd/2,deep,cq.Vector(h['u'],h['v'],t-deep-recess))
            else:cone=cq.Solid.makeCone(dd/2,h['diameter']/2,deep,cq.Vector(h['u'],h['v'],recess))
            s=s.cut(cone)
    for h in edge_holes:s=s.cut(cyl(h['point'],h['diameter']/2,h['depth'],h['direction']))
    axes=axes or ((1,0,0),(0,1,0),(0,0,1))
    return dict(name=name,shape=pose(s,origin,*axes),kind='plate',motion=motion,
                mass_kg=round(s.Volume()*(7.85e-6 if material.startswith('Q235') else 2.7e-6),4),
                role='fabricated',spec=f'{material} / {a}x{b}x{t}',
                manufacturing=dict(type='plate',material=material,size_mm=size,origin_mm=origin,axes=axes,
                                   holes=list(holes),edge_holes=list(edge_holes),outline=outline,windows=list(windows),slots=list(slots),notes=list(notes)))


def rail(length):
    s=box((-7.5,0,0),(15,length,15))
    count=round((length-40)/60)+1
    assert abs(length-(count-1)*60-40)<1e-6
    for i in range(count):
        yy=20+60*i;s=s.cut(cyl((0,yy,0),2.25,15)).cut(cyl((0,yy,9.7),3.75,5.3))
    return s


def block():
    s=box((-17,-30.7,4.3),(34,61.4,23.7))
    s=s.cut(box((-7.65,-30.7,4.3),(15.3,61.4,11)))
    for u,v in product((-13,13),repeat=2):s=s.cut(cyl((u,v,23),2,5))
    return s


def linear_components(tcp):
    x,y,z=tcp;yc=y+100;parts=[]
    def purchased(name,s,motion,spec,mass):
        parts.append(dict(name=name,shape=s,kind='rail' if '_rail_' in name else 'block',
                          motion=motion,role='catalog_part',spec=spec,mass_kg=mass))
    for i,xx in enumerate((20,880)):
        purchased(f'y_rail_{i}',rail(820).translate((xx,40,948)),'fixed','HIWIN HGR15R-820; E20/P60; M4x16',1.189)
        for j,dy in enumerate((-55,55)):
            purchased(f'y_block_{i}_{j}',block().translate((xx,yc+dy,948)),'Y','HIWIN HGH15CAZAC; 4-M4x5; 26x26',.18)
    xaxes=((0,0,-1),(1,0,0),(0,-1,0))
    for i,zc in enumerate((1022.5,1062.5)):
        purchased(f'x_rail_{i}',pose(rail(700),(100,yc-26,zc),*xaxes),'Y','HIWIN HGR15R-700; E20/P60; M4x16',1.015)
        for j,dx in enumerate((-40,40)):
            purchased(f'x_block_{i}_{j}',pose(block(),(x+dx,yc-26,zc),*xaxes),'XY','HIWIN HGH15CAZAC; 4-M4x5; 26x26',.18)
    zaxes=((-1,0,0),(0,0,1),(0,1,0))
    for i,dx in enumerate((-35,35)):
        purchased(f'z_rail_{i}',pose(rail(760),(x+dx,yc-107,z+220),*zaxes),'XYZ','HIWIN HGR15R-760; E20/P60; M4x16',1.102)
        for j,zz in enumerate((915,1045)):
            purchased(f'z_block_{i}_{j}',pose(block(),(x+dx,yc-107,zz),*zaxes),'XY','HIWIN HGH15CAZAC; 4-M4x5; 26x26',.18)
    return parts


def mounting_plates(tcp):
    x,y,z=tcp;yc=y+100;out=[]
    for i,xx in enumerate((20,880)):
        hs=[hole(16,20+60*j,4,'M4',8) for j in range(14)]
        hs += [hole(16,50+120*j,6.6,csk=(12.4,90),note='M6沉头固定到型材') for j in range(7)]
        out.append(plate(f'y_rail_base_{i}',(32,820,8),(xx-16,40,940),hs,notes=['安装面平面度0.05/820；M4孔与型材固定孔交错']))
    xaxes=((1,0,0),(0,0,1),(0,-1,0))
    for i,zc in enumerate((1022.5,1062.5)):
        hs=[hole(20+60*j,16,4,'M4',6) for j in range(12)]
        hs += [hole(50+120*j,13.5,5.5,csk=(10.4,90),note='M5沉头固定到型材') for j in range(6)]
        out.append(plate(f'x_rail_base_{i}',(700,32,6),(100,yc-20,zc-16),hs,axes=xaxes,motion='Y',notes=['安装面平面度0.05/700']))
    zaxes=((1,0,0),(0,0,1),(0,-1,0))
    hs=[hole(50+dx,50+60*j,4,'M4',8) for dx in (-35,35) for j in range(13)]
    hs += [hole(50+dx,v,6.6,csk=(12.4,90),side='bottom',note='M6沉头从导轨侧固定到型材两条槽') for dx in (-20,20) for v in (80,200,320,440,560,680,770)]
    hs += [hole(50+dx,v,6,'M6',8) for dx in (-23,23) for v in (824.5,837.5)]
    hs += [hole(50+dx,20,6,'M6',8,note='下浮动座固定') for dx in (-20,20)]
    outline=[(0,0),(100,0),(100,800),(82,800),(82,848),(18,848),(18,800),(0,800)]
    out.append(plate('z_rail_backplate',(100,848,8),(x-50,yc-107,z+190),hs,outline=outline,axes=zaxes,motion='XYZ',notes=['双导轨中心距70；上端64宽舌板固定BK12；上支承抬高20，给Z下越程留净空；安装面平面度0.05/800']))
    for i,px in enumerate((0,820)):
        block_x=20-px if i==0 else 880-px
        hs=[hole(block_x+dx,95+dy+dd,4.5,cbore=(9.5,.8)) for dx in (-13,13) for dy in (-55,55) for dd in (-13,13)]
        riser_center=60-px if i==0 else 840-px
        hs += [hole(riser_center+dx,95+dy,6.6,cbore=(12.5,1.6),side='bottom') for dx,dy in product((-10,10),repeat=2)]
        clamp_x=65-px if i==0 else 835-px
        hs += [hole(clamp_x,95+side*40.5+dd,5,'M5',12,note='Y夹板微调座连接，贯穿攻丝') for side in (-1,1) for dd in (-6,6)]
        edges=[dict(point=[0,v,6],direction=[1,0,0],diameter=3,depth=8,thread='M3',note='Y外侧钢靶连接') for v in (5,15,175,185)] if i==0 else []
        if i==1:edges += [dict(point=[80,v,6],direction=[-1,0,0],diameter=4,depth=10,thread='M4',note='Y拖链或线夹转接板预留') for v in (75,115)]
        out.append(plate(f'y_end_plate_{i}',(80,190,12),(px,yc-95,976),hs,motion='Y',edge_holes=edges,notes=['HGH15安装M4x16，垫圈沉入0.8深台阶；有效入牙4']))
        hs=[hole(20,20,9,cbore=(14,8),side='bottom')]+[hole(20+dx,20+dy,6,'M6',10,side='bottom') for dx,dy in product((-10,10),repeat=2)]
        out.append(plate(f'bridge_riser_{i}',(40,40,12),(40 if i==0 else 820,yc-20,988),hs,motion='Y',notes=['先将垫块装到横梁底槽，再固定到端板']))
    hs=[]
    for dx,zc in product((-40,40),(1022.5,1062.5)):
        hs += [hole(80+dx+du,zc-860+dv,4.5,cbore=(9.5,4.8),side='top',note='X滑块：M4x16，入牙4') for du,dv in product((-13,13),repeat=2)]
    for dx,zc in product((-35,35),(915,1045)):
        hs += [hole(80+dx+du,zc-860+dv,4.5,cbore=(9.5,4.8),side='bottom',note='Z隔块/滑块：M4x25，入牙4') for du,dv in product((-13,13),repeat=2)]
    hs += [hole(80+du,v-860,5.5,note='螺母托架：M5x25') for du in (-60,60) for v in (955,1000)]
    hs += [hole(80+du,zz-860,5,'M5',12,note='Z固定止挡，前面盲孔') for du,zz in product((60,70),(885,905,1075,1095))]
    hs += [hole(u,125,3,'M3',8,side='top',note='X限位钢靶，前面盲孔') for u in (5,15,145,155)]
    edges=[dict(point=[80+u,240,8],direction=[0,-1,0],diameter=5,depth=14,thread='M5',note='上跨梁板连接') for u in (-40,-28,28,40)]
    edges += [dict(point=[160,v,8],direction=[-1,0,0],diameter=4,depth=10,thread='M4',note='X线夹/拖链转接板预留') for v in (70,110)]
    outline=[(0,0),(160,0),(160,128),(148,128),(148,150),(160,150),(160,240),(0,240),(0,150),(12,150),(12,128),(0,128)]
    out.append(plate('x_z_carrier',(160,240,16),(x-80,yc-54,860),hs,outline=outline,windows=[(50,85,60,70)],axes=zaxes,motion='XY',edge_holes=edges,
                     notes=['A为背面；X滑块螺钉头从前面沉入，Z滑块螺钉头从背面沉入；先装X滑座再装Z机构','两侧12x22缺口用于X越程与Y夹座相位调节避让；缺口内角R<=1，不得用R3代替']))
    for i,dx in enumerate((-35,35)):
        for j,zz in enumerate((915,1045)):
            hs=[hole(17+u,30.7+v,4.5) for u,v in product((-13,13),repeat=2)]
            out.append(plate(f'z_block_spacer_{i}_{j}',(34,61.4,9),(x+dx-17,yc-70,zz-30.7),hs,axes=zaxes,motion='XY'))
    return out


def nut_components(tcp):
    x,y,z=tcp;yc=y+100;cy=yc-82
    c=CATALOG['ballnut']
    flange=cyl((x,cy,960),24,10).intersect(box((x-20,cy-25,960),(40,50,10)))
    nut=flange.fuse(cyl((x,cy,960),14,45)).cut(cyl((x,cy,960),8,45))
    angles=c['hole_angles_deg'];centers=[]
    for angle in angles:
        a=math.radians(angle);xx=x+19*math.cos(a);yy=cy+19*math.sin(a);centers.append((xx,yy))
        nut=nut.cut(cyl((xx,yy,960),2.75,10))
    floor=box((x-26.5,cy-25,950),(53,53,10))
    back=box((x-68,yc-54,945),(136,8,60))
    s=floor.fuse(back)
    fillet=box((x-26.5,yc-57,960),(53,3,3)).cut(cyl((x-26.5,yc-57,963),3,53,(1,0,0)))
    s=s.fuse(fillet).cut(cyl((x,cy,950),14.25,10))
    s=s.cut(box((x-25,yc-54,968),(50,8,32)))
    features=[]
    for xx,yy in centers:
        s=s.cut(cyl((xx,yy,950),2.5,10))
        features.append(dict(point=[xx-(x-68),yy-(cy-25),15],direction=[0,0,-1],diameter=5,depth=10,thread='M5',note='SFNU01605法兰固定，PCD38'))
    for dx,zz in product((-60,60),(955,1000)):
        s=s.cut(cyl((x+dx,yc-54,zz),2.5,8,(0,1,0)))
        features.append(dict(point=[68+dx,53,zz-945],direction=[0,1,0],diameter=5,depth=8,thread='M5',note='连接X滑座板'))
    return [dict(name='z_fixed_ballnut',shape=nut,kind='drive',motion='XY',mass_kg=.22,role='catalog_part',
                 spec='TBI SFNU01605-4；D28/L45；法兰48、对边40、PCD38/6-D5.5'),
            dict(name='z_nut_cradle',shape=s,kind='plate',motion='XY',mass_kg=round(s.Volume()*2.7e-6,4),role='fabricated',
                 spec='6061-T6一体螺母托架；136x61x60毛坯；底板10/后法兰8/内角R3',
                 manufacturing=dict(type='machined_angle',material='6061-T6',origin_mm=[x-68,cy-25,945],
                                    size_mm=[136,61,60],floor=dict(x=41.5,y=0,z=5,width=53,depth=53,thickness=10),
                                    back=dict(x=0,y=53,z=0,width=136,thickness=8,height=60),
                                    center_bore=dict(x=68,y=25,diameter=28.5,z=5,depth=10),
                                    service_window=dict(x=43,z=23,width=50,height=32),inner_radius=3,edge_holes=features,
                                    notes=['一体CNC，不允许分件焊接代替','先装螺母和润滑延长接头，再固定到X滑座；保留后部检修窗']))]


def head_parts(tcp):
    x,y,z=tcp;yc=y+100;out=[]
    hs=[hole(40+dx,25,9,note='M8x25+1.6垫圈，接滑枕端面M8x20') for dx in (-20,20)]
    hs += [hole(40+dx,60+dy,4.5,csk=(9,90)) for dx,dy in product((-27,27),(-12,12))]
    out.append(plate('fixed_head_top',(80,90,8),(x-40,yc-160,z+182),hs,motion='XYZ',notes=['滑枕下端2-M8攻丝20深；端面贴合本板A面']))
    side_axes=((0,1,0),(0,0,1),(1,0,0))
    for i,dx in enumerate((-30,24)):
        edges=[]
        for uu in (8,32):
            edges.append(dict(point=[uu,0,3],direction=[0,1,0],diameter=4,depth=14,thread='M4'))
            edges.append(dict(point=[uu,114,3],direction=[0,-1,0],diameter=4,depth=14,thread='M4'))
        out.append(plate(f'fixed_head_side_{i}',(40,114,6),(x+dx,yc-120,z+68),windows=[(10,20,20,76)],
                         axes=side_axes,motion='XYZ',edge_holes=edges,notes=['上下端面各2-M4x14，先钻底孔再攻丝']))
    s=cyl((x,y,z+60),35,8).cut(cyl((x,y,z+60),4,8));hs=[hole(35,35,8)]
    for angle in (0,90,180,270):
        a=math.radians(angle);xx=25*math.cos(a);yy=25*math.sin(a)
        s=s.cut(cyl((x+xx,y+yy,z+60),2.25,8));hs.append(hole(35+xx,35+yy,4.5,note='夹爪接口PCD50'))
    for dx,dy in product((-27,27),(-12,12)):
        s=s.cut(cyl((x+dx,y+dy,z+60),2.25,8)).cut(cyl((x+dx,y+dy,z+60),4.75,4.8))
        hs.append(hole(35+dx,35+dy,4.5,cbore=(9.5,4.8),side='bottom',note='M4x16+0.8垫圈，入侧板12'))
    out.append(dict(name='gripper_adapter',shape=s,kind='drive',motion='XYZ',role='fabricated',mass_kg=round(s.Volume()*2.7e-6,4),
                    spec='6061-T6 D70x8；PCD50夹爪接口；4-M4连接固定侧板',
                    manufacturing=dict(type='round_plate',material='6061-T6',size_mm=[70,70,8],diameter=70,
                                       origin_mm=[x-35,y-35,z+60],holes=hs,notes=['中孔D8；夹爪或夹爪转接件使用PCD50接口'])) )
    return out


def z_motor_structure(tcp):
    x,y,z=tcp;cy=y+18;out=[]
    hs=[hole(45,35,24)]
    hs += [hole(45+a,35+b,3.5) for a,b in product((-15.5,15.5),repeat=2)]
    hs += [hole(45+a,35+b,4.5) for a,b in product((-40,40),(-28,28))]
    out.append(plate('z_motor_mount',(90,70,7),(x-45,cy-35,z+1123),hs,motion='XYZ',notes=['电机4-M3x10，入牙3；侧板4-M4x16，入牙9']))
    side_axes=((0,1,0),(0,0,1),(1,0,0))
    for i,dx in enumerate((-45,35)):
        hs=[hole(35+yy,29,4.5,cbore=(9.5,.8),side='bottom' if i==0 else 'top') for yy in (-26,26)]
        edges=[]
        for u in (7,63):
            edges.append(dict(point=[u,0,5],direction=[0,1,0],diameter=4,depth=12,thread='M4'))
            edges.append(dict(point=[u,107,5],direction=[0,-1,0],diameter=4,depth=12,thread='M4'))
        out.append(plate(f'z_motor_standoff_{i}',(70,107,10),(x+dx,cy-35,z+1016),hs,
                         axes=side_axes,motion='XYZ',edge_holes=edges,slots=[(35,67,70,30,90)],notes=['侧面两孔固定制动器横板；端面四孔连接上下板','30x70检修长孔用于制动轮毂和联轴器紧固；保留两侧20宽连续腹板']))
    hs=[hole(35,35,30)]
    hs += [hole(35+24*math.cos(math.radians(a)),35+24*math.sin(math.radians(a)),3,'M3',10) for a in (90,210,330)]
    edges=[dict(point=[u,35+yy,5],direction=[1 if u==0 else -1,0,0],diameter=4,depth=12,thread='M4') for u,yy in product((0,70),(-26,26))]
    out.append(plate('z_brake_carrier',(70,70,10),(x-35,cy-35,z+1040),hs,motion='XYZ',edge_holes=edges,
                     notes=['BXW-03-10H-24V-8，3-V孔对准3-M3；M3x40穿入本板至少8，允许背面露出不超过1.5','制动器原厂3-S装配螺钉不拆；先装制动器再装电机顶板']))
    # 下鞍座背板贴滑枕后面，横板避让导轨背板舌部及BK12。
    base=box((x-45,y+100-161,z+1010),(90,114,6))
    base=base.cut(box((x-32.5,y+100-116,z+1010),(65,53,6)))
    back=box((x-45,y+100-161,z+950),(90,6,60));s=base.fuse(back)
    feats=[]
    for dx,dz in product((-20,20),(960,980)):
        s=s.cut(cyl((x+dx,y+100-161,z+dz),2.75,6,(0,1,0)))
        feats.append(dict(point=[45+dx,0,dz-950],direction=[0,1,0],diameter=5.5,depth=6,thread=None,note='M5接滑枕后槽'))
    for dx,yy in product((-40,40),(-28,28)):
        s=s.cut(cyl((x+dx,cy+yy,z+1010),2.25,6))
        s=s.cut(cq.Solid.makeCone(4.5,2.25,2.25,cq.Vector(x+dx,cy+yy,z+1010)))
        feats.append(dict(point=[45+dx,cy+yy-(y+100-161),60],direction=[0,0,1],diameter=4.5,depth=6,countersink=[9,90],thread=None,note='M4x14沉头，上侧板入牙8'))
    out.append(dict(name='z_motor_lower_saddle',shape=s,kind='plate',motion='XYZ',role='fabricated',mass_kg=round(s.Volume()*2.7e-6,4),
                    spec='6061-T6一体下鞍座；90宽/背板6/横板6；上面避让口65x53',
                    manufacturing=dict(type='machined_angle',material='6061-T6',origin_mm=[x-45,y+100-161,z+950],
                                       size_mm=[90,114,66],back=dict(x=0,y=0,z=0,width=90,thickness=6,height=60),
                                       floor=dict(x=0,y=0,z=60,width=90,depth=114,thickness=6),window=dict(x=12.5,y=45,width=65,depth=53),
                                       edge_holes=feats,notes=['整体CNC；先锁沉头螺钉再固定到滑枕；横板下平面不得留凸起螺钉头'])))
    return out


def z_purchased_and_shaft(tcp):
    x,y,z=tcp;cy=y+18;out=[]
    def add(name,s,kind,spec,mass,role='catalog_part',manufacturing=None):
        p=dict(name=name,shape=s,kind=kind,motion='XYZ',role=role,spec=spec,mass_kg=mass)
        if manufacturing:p['manufacturing']=manufacturing
        out.append(p)
    sections=[(204,215,10),(215,1008,16),(1008,1044,12),(1044,1097.5,8)]
    shaft=None
    for lo,hi,d in sections:
        s=cyl((x,cy,z+lo),d/2,hi-lo);shaft=s if shaft is None else shaft.fuse(s)
    groove=cyl((x,cy,z+205.85),5.2,1.15).cut(cyl((x,cy,z+205.85),4.8,1.15))
    shaft=shaft.cut(groove)
    add('z_screw_1605',shaft,'screw','TBI 1605-C7配SFNU01605-4；上BK12，下6000浮动座；上伸D8h7',1.432,
        role='fabricated',manufacturing=dict(type='ballscrew_end_machining',material='TBI原厂16x5滚珠丝杆',origin_mm=[x,cy,z+204],
            total_length=893.5,sections_mm=[[a-204,b-204,d] for a,b,d in sections],threaded_working_section=[11,804],
            fixed_end=dict(journal_diameter='12 g6',journal_length=24,thread='M12x1-6g',thread_length=12),
            floating_end=dict(diameter='10 h6',length=11,groove_diameter='9.6 h11',groove_from_end=1.85,groove_width='1.15 +0.14/0'),
            motor_extension=dict(diameter='8 h7',length=53.5),
            notes=['螺母由丝杆厂装配交货，不得自行拆下滚珠螺母','两端加工只允许丝杆厂家按轴端图处理退刀槽/轴肩R≤0.3；淬硬工作段不得损伤','上端螺纹区在本图局部Z828~840；3D模型不画螺纹牙型'] ))
    z+=20
    # BK12外形和已公布接口。轴承/密封/锁紧件作为采购总成，不制造其内部。
    body=box((x-30,cy-25,z+988.5),(60,32.5,25)).fuse(box((x-17,cy+7.5,z+988.5),(34,10.5,25)))
    body=body.cut(cyl((x,cy,z+988.5),6,25))
    for dx,zz in product((-23,23),(994.5,1007.5)):
        body=body.cut(cyl((x+dx,cy-25,z+zz),3.3,32.5,(0,1,0)))
        body=body.cut(cyl((x+dx,cy+6,z+zz),5.4,1.5,(0,1,0)))
    add('z_screw_support_1',body,'block','HIWIN BK12-C7原厂总成，4-M6x40底座安装；不得拆调预紧轴承',.45)
    lock=cyl((x,cy,z+1016),11,8).cut(cyl((x,cy,z+1016),6,8))
    add('z_screw_locknut',lock,'screw','BK12原配M12x1锁紧螺母，按HIWIN安装方法锁止',.015)
    # 制动器仅表达公开安装外形和转子轮毂；内部工作气隙不由加工方调整。
    brake=cyl((x,cy,z+1030),28,31.9).cut(cyl((x,cy,z+1030),12,31.9))
    for angle in (90,210,330):
        a=math.radians(angle);brake=brake.cut(cyl((x+24*math.cos(a),cy+24*math.sin(a),z+1030),1.7,31.9))
    add('z_brake_stator',brake,'safety','MIKI BXW-03-10H-24V-8；3-V固定，24V/9W，失电保持1N.m',.36)
    hub=box((x-7,cy-7,z+1049.9),(14,14,12)).cut(cyl((x,cy,z+1049.9),4,12))
    add('z_brake_hub',hub,'drive','BXW原配D8H8轮毂；J19.9/L12，用原配2-M3锁紧，按手册防松',.04)
    for name,lo,hi,bore in [('screw',1065.5,1077.5,4),('center',1077.5,1087.5,6),('motor',1087.5,1099.5,2.5)]:
        s=cyl((x,cy,z+lo),12.5,hi-lo).cut(cyl((x,cy,z+lo),bore,hi-lo))
        add('z_coupling_'+('center_ENVELOPE' if name=='center' else name+'_hub'),s,'drive',
            'NBK MJC-25CS-RD-5-8；D25/W34，两轴各插入12；按厂家1.5N.m夹紧',.006 if name=='center' else .014)
    return out


def apply(parts,tcp):
    """逐步替换布局件；release.json保持未放行，直到全体接口验证闭合。"""
    x,y,z=tcp;yc=y+100
    from drive_fabrication import input_module,z_floating,xy_pulleys,x_output,xy_brackets,y_output
    from belt_fabrication import main_belts,clamps,tensioners
    from frame_fabrication import extend_frame,corners,braces
    from joints import structural_fasteners
    from accessory_fabrication import accessories
    from travel_limits import limits
    replacements=linear_components(tcp)+mounting_plates(tcp)+nut_components(tcp)+head_parts(tcp)+z_motor_structure(tcp)+z_purchased_and_shaft(tcp)
    replacements+=input_module('X',tcp)+input_module('Y',tcp)+z_floating(tcp)+xy_pulleys(tcp)+x_output(tcp)+xy_brackets(tcp)+y_output()+main_belts(tcp)+clamps(tcp)+tensioners(tcp)+corners()+braces()
    board='jetson_nano' if any(p['name']=='compute_board_jetson_nano' for p in parts) else 'pi4b'
    replacements+=structural_fasteners(tcp)+accessories(board)+limits(tcp)
    names={p['name'] for p in replacements}
    removed={'z_nut_rear_flange','z_brake_reserve','z_screw_support_0','x_pulley_mount_0','x_pulley_axle_0','x_main_pulley_set_screw','x_belt_clamp',
             'x_pulley_1','x_pulley_mount_1','x_pulley_axle_1','y_pulley_0_0','y_pulley_1_0','x_output_spacer_4'}
    result=[p for p in parts if p['name'] not in names and p['name'] not in removed
            and not p['name'].startswith(('z_top_m4_','z_base_m4_','z_saddle_m5_','x_motor_m3_','y_motor_m3_',
                'x_output_bearing_','x_output_collar_','x_reduction_input_set_','y_reduction_input_set_',
                'x_reduction_driven_set_','y_reduction_driven_set_','x_mount_m5_','y_mount_m5_',
                'x_belt_','y_belt_','y_rear_collar_','y_main_pulley_set_','y_bearing_mount_',
                'side_brace_','rear_brace_','X_limit_','Y_limit_','Z_limit_','camera_pivot_screw_','camera_panel_screw_'))]
    for p in result:
        if p['name']=='z_ram_4080':p['shape']=p['shape'].translate((0,-25,0));p['mass_kg']=2.4
        if p['name']=='motor_Z_ZDT42V2' or p['name'].startswith('z_motor_m3_'):p['shape']=p['shape'].translate((0,-8,20))
        if p['name'].startswith('z_motor_m3_'):
            p.update(role='fastener',spec='M3x10 ISO4762内六角',connection=dict(diameter=3,length=10,washer=0,engagement=3,joint='Z电机接7mm顶板',style='socket'))
    return extend_frame(result)+replacements
