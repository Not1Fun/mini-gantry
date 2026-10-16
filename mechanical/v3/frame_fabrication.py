"""型材切长、角连接板、交叉拉带及附件固定。"""
import math
from itertools import product
import cadquery as cq
from fabrication import plate,hole,box,cyl,pose
from drive_fabrication import turned,fastener,part


def extend_frame(parts):
    from build import tube
    for p in parts:
        n=p['name']
        if n in ('base_side_0','base_side_1','top_side_0','top_side_1'):
            xx=0 if n.endswith('0') else 860;top=n.startswith('top');hh=80 if top else 40
            p['shape']=tube((xx,0,860 if top else 0),(40,940,hh),1)
            p['spec']='MISUMI HFS8-'+('4080' if top else '4040')+'-940，槽口10'
            p['mass_kg']=.94*(3 if top else 1.7)
        if n in ('base_cross_1','top_cross_1','column_0_1','column_1_1','rear_accessory_crossbar','controller_tray','RM_A_or_RA6M5_RESERVE') or n.startswith('compute_'):
            p['shape']=p['shape'].translate((0,40,0))
        if p['kind']=='frame':
            bb=p['shape'].BoundingBox();size=[bb.xlen,bb.ylen,bb.zlen];length=max(size)
            profile='4080' if n.startswith('top_side') or n in ('bridge_4080','z_ram_4080') else '4040'
            p['spec']=f'MISUMI HFS8-{profile}-{length:g} /槽口10 /HNTT8螺母'
            p['mass_kg']=length/1000*(3 if profile=='4080' else 1.7)
            p['role']='cut_profile'
            p['manufacturing']=dict(type='profile_cut',material='MISUMI HFS8铝型材',profile='HFS8-'+profile,length_mm=length,
                                  notes=['切长+/-0.2；两端垂直度0.1/100；去毛刺；标准槽型不得按等效薄壁CAD截面制造','角连接和板件固定采用HNTT8相应螺纹螺母；先放螺母再封闭框架'])
            if n=='z_ram_4080':p['manufacturing']['end_threads']={'face':'下端','holes':[[-20,0],[20,0]],'thread':'M8','full_thread_depth':20,'pilot_depth':24}
            if n.startswith(('base_side_','top_side_')):
                p['manufacturing']['end_threads']={'face':'两端','section_datum':'40宽x40或80高截面左下角','holes':[[20,20]],'thread':'M8','full_thread_depth':18,'pilot_depth':22,'note':'4080只攻下排芯孔；前后角板中心孔接端面，不使用T螺母'}
    return parts


def corners():
    out=[];outline=[(0,0),(120,0),(120,40),(40,40),(40,120),(0,120)];centers=[(20,20),(60,20),(100,20),(20,60),(20,100)]
    for plane in ('front','rear','left','right'):
        for end,upper in product((0,1),(False,True)):
            if plane in ('front','rear'):
                org=(0 if end==0 else 900,-6 if plane=='front' else 946,900 if upper else 0)
                u=(1 if end==0 else -1,0,0);v=(0,0,-1 if upper else 1)
            else:
                org=(-6 if plane=='left' else 906,0 if end==0 else 940,900 if upper else 0)
                u=(0,1 if end==0 else -1,0);v=(0,0,-1 if upper else 1)
            w=cq.Vector(*u).cross(cq.Vector(*v)).toTuple()
            # 板厚应朝框架；若坐标系法向朝外，将厚度原点移动到框架面。
            inward=(0,1,0) if plane=='front' else (0,-1,0) if plane=='rear' else (1,0,0) if plane=='left' else (-1,0,0)
            if sum(a*b for a,b in zip(w,inward))<0:org=tuple(a+6*b for a,b in zip(org,inward))
            name=f'frame_corner_{plane}_{end}_{int(upper)}'
            p=plate(name,(120,120,6),org,[hole(u,v,9) for u,v in centers],outline=outline,axes=(u,v,w),notes=['6061-T6角连接板；外缘倒角C0.5；孔位置度D0.15对两直边','M8x20+DIN7349厚3垫圈；型材槽内投影11mm；按对角线调整方正后锁紧'])
            out.append(p)
            for j,(uu,vv) in enumerate(centers):
                point=cq.Vector(*org)+cq.Vector(*u)*uu+cq.Vector(*v)*vv
                if sum(a*b for a,b in zip(w,inward))<0:point=point+cq.Vector(*w)*6
                joint='角板接侧梁端面M8x18' if plane in ('front','rear') and j==0 else '角板到HNTT8-8'
                out+=fastener(name+f'_M8_{j}',point.toTuple(),inward,8,20,'fixed',3,11,joint)
    for side in (0,1):
        origin=(0 if side==0 else 900,946,140);u=(1 if side==0 else -1,0,0);w=(0,-1 if side==0 else 1,0)
        if side:origin=(900,940,140)
        hs=[hole(20,20,9),hole(20,60,9),hole(60,40,9)]
        out.append(plate(f'accessory_cross_joint_{side}',(80,80,6),origin,hs,axes=(u,(0,0,1),w),notes=['后附件横梁与后立柱连接；3-M8x20加3厚DIN7349垫圈/HNTT8-8']))
        for j,(uu,vv) in enumerate(((20,20),(20,60),(60,40))):
            xx=uu if side==0 else 900-uu
            out+=fastener(f'accessory_cross_joint_{side}_M8_{j}',(xx,946,140+vv),(0,-1,0),8,20,'fixed',3,11,'后附件横梁接立柱')
    return out


def braces():
    out=[]
    cases=[]
    for side in (0,1):
        for diag in (0,1):
            xx=40 if side==0 else 860;normal=(1,0,0) if side==0 else (-1,0,0)
            cases.append((f'side_brace_{side}_{diag}',(xx,20,120 if diag==0 else 800),(xx,920,800 if diag==0 else 120),normal,1 if diag==0 else 5))
    for diag in (0,1):cases.append((f'rear_brace_{diag}',(20,900,80 if diag==0 else 840),(880,900,840 if diag==0 else 80),(0,-1,0),50 if diag==0 else 54))
    for name,a,b,normal,gap in cases:
        A,B=cq.Vector(*a),cq.Vector(*b);u=(B-A).normalized();w=cq.Vector(*normal);v=w.cross(u);distance=(B-A).Length;L=distance+24
        org=(A-u*12-v*15+w*gap).toTuple();axes=(u.toTuple(),v.toTuple(),w.toTuple())
        bolt_length=(16 if gap==1 else 20) if gap<10 else (65 if gap==50 else 70)
        p=plate(name,(L,30,3),org,[hole(12,15,9)],slots=[(L-12,15,17,9,0)],axes=axes,
                notes=['6061-T6拉带30x3；两端中心距按图，单端9x17长槽；外角R3倒圆；只承受拉力','先调框架对角线，再使交叉拉带平直、消除松弛后锁紧；不得强拉使型材弯曲','两条拉带以1/5隔套错层；M8x16/20+1.6垫圈，槽内投影10.4'])
        p['manufacturing']['notes'][-1]=f'隔套{gap}mm；M8x{bolt_length}+1.6垫圈；后撑向内错开避免与侧撑相撞'
        out.append(p)
        for j,pt in enumerate((A,B)):
            od=20 if gap<10 else 25;material='6061-T6' if gap<10 else '45钢'
            spacer=cq.Solid.makeCylinder(od/2,gap,pt,w).cut(cq.Solid.makeCylinder(4.25,gap,pt,w))
            out.append(part(name+f'_spacer_{j}',spacer,'fixed',f'{material} D{od}/D8.5/L{gap}隔套',material=material,manufacturing=dict(type='turned',steps_mm=[[0,gap,od]],bores_mm=[[0,gap,8.5]],origin_mm=pt.toTuple(),axes=axes,notes=['长度+/-0.05；两端平行度0.03；钢隔套发黑防锈'])))
            out+=fastener(name+f'_M8_{j}',(pt+w*(gap+3)).toTuple(),(-w).toTuple(),8,bolt_length,'fixed',1.6,bolt_length-gap-4.6,'交叉拉带接HNTT8-8')
    return out
