"""独立机械止挡、钢制感应片和M8常闭接近开关。"""
from itertools import product
from fabrication import box,cyl,plate,hole,pose
from drive_fabrication import part,fastener


def pad_hole(u,v,side='top'):
    return dict(hole(u,v,3.4,csk=(6.3,90),side=side),head_recess=2)


def sensor(name,face,direction,motion):
    # E2B-S08KS02-WP-C2 2M：M8x1，42总长/27螺纹长；面前1mm钢靶。
    s=cyl(face,4,42,direction)
    out=[part(name,s,motion,'OMRON E2B-S08KS02-WP-C2 2M /NPN常闭/2mm/屏蔽M8，钢靶工作间隙1mm',mass=.06,kind='safety')]
    for i,t in enumerate((9.5,23)):
        p=tuple(a+t*b for a,b in zip(face,direction));n=cyl(p,6.5,3.5,direction).cut(cyl(p,4,3.5,direction))
        out.append(part(name+f'_nut_{i}',n,motion,'传感器原配M8x1薄螺母，扭矩按OMRON手册','45钢',kind='screw'))
    return out


def machined(name,s,origin,motion,blocks,holes,notes):
    return part(name,s,motion,'6061-T6一体止挡座',manufacturing=dict(type='machined_union',origin_mm=origin,blocks=blocks,features=holes,
                notes=notes+['3D STEP给定未标注轮廓；孔位+/-0.05，垂直度0.05/100；内角允许R2，接触/安装面Ra1.6']))


def limits(tcp):
    x,y,z=tcp;yc=y+100;out=[]
    # X止挡在横梁顶部，感应区延伸到滑座背面，避开承力碰撞面。
    for i in (0,1):
        def mirror(p):
            if i:
                p['shape']=p['shape'].mirror('YZ',(450,0,0))
                if 'manufacturing' in p:p['manufacturing']['mirror_about_x_mm']=450
            return p
        s=box((82,yc-110,970),(18,130,10)).fuse(box((100,yc-44,970),(30,64,10))).fuse(box((82,yc-20,980),(48,40,20))).fuse(box((100,yc-110,970),(30,30,10))).fuse(box((100,yc-95,980),(30,10,20)))
        features=[]
        for xx in (92,120):s=s.cut(cyl((xx,yc,970),3.3,30));features.append(dict(point=[xx-82,110,0],direction=[0,0,1],diameter=6.6,depth=30))
        s=s.cut(cyl((115,yc-95,988),4.25,10,(0,1,0)))
        features.append(dict(point=[33,15,18],direction=[0,1,0],diameter=8.5,depth=10,note='M8传感器孔；触发位置装配标定'))
        for yy in (yc-66,yc-58):s=s.cut(cyl((100,yy,975),1.5,10,(-1,0,0)));features.append(dict(point=[18,yy-(yc-110),5],direction=[-1,0,0],diameter=3,depth=10,thread='M3'))
        p=machined(f'X_stop_{i}',s,[82,yc-110,970],'Y',[[0,0,0,18,130,10],[18,66,0,30,64,10],[0,90,10,48,40,20],[18,0,0,30,30,10],[18,15,10,30,10,20]],features,
                   ['左金属止挡面X100，右X800；配5mm聚氨酯垫，首次接触TCP185/715，金属极限180/720','正常工作TCP200~700；限位名义195/705；首次上电标定实际触发位置，保证到软垫至少8mm制动距离'])
        out.append(mirror(p))
        for j,xx in enumerate((92,120)):
            for p in fastener(f'X_stop_{i}_M6_{j}',(xx,yc,970),(0,0,1),6,40,'Y',1.6,8.4,'X止挡接横梁底槽HNTT8-6'):out.append(mirror(p))
        p=plate(f'X_bumper_{i}',(16,10,5),(100,yc-70,970),[pad_hole(4,5),pad_hole(12,5)],axes=((0,1,0),(0,0,1),(1,0,0)),material='PU90A',motion='Y',notes=['90A聚氨酯板；M3头低于缓冲面2；D6.5直壁深2后加工90度沉头；设计压缩不超过1mm'])
        out.append(mirror(p))
        for j,yy in enumerate((yc-66,yc-58)):
            for p in fastener(f'X_bumper_{i}_M3_{j}',(103,yy,975),(-1,0,0),3,12,'Y',thread_depth=9,joint='X缓冲垫固定，头下沉2',style='countersunk'):out.append(mirror(p))
        for p in sensor(f'X_limit_{i}',(115,yc-72,988),(0,-1,0),'Y'):out.append(mirror(p))
        xx=x-80 if i==0 else x+60
        hs=[hole(u,10,3.4) for u in (5,15)]
        p=plate(f'X_target_{i}',(20,20,1),(xx,yc-70,975),hs,axes=((1,0,0),(0,0,1),(0,-1,0)),material='Q235B',motion='XY',notes=['钢制感应片镀锌；装在X滑座前面；与传感面间隙1 +/-0.2'])
        out.append(p)
        for j,u in enumerate((5,15)):out+=fastener(f'X_target_{i}_M3_{j}',(xx+u,yc-71,985),(0,1,0),3,8,'XY',.5,6.5,'钢靶接滑座前面M3')
    # Y止挡在两侧型材内侧，四个金属承力点；只在左侧安装前后传感器。
    for side,i in product((0,1),repeat=2):
        yy=105 if i==0 else 865
        def mirror(p):
            if side:
                p['shape']=p['shape'].mirror('YZ',(450,0,0))
                if 'manufacturing' in p:p['manufacturing']['mirror_about_x_mm']=450
            return p
        s=box((40,yy,870),(8,30,118)).fuse(box((48,yy,976),(32,30,12)))
        features=[]
        for zz in (880,920):s=s.cut(cyl((40,yy+15,zz),3.3,8,(1,0,0)));features.append(dict(point=[0,15,zz-870],direction=[1,0,0],diameter=6.6,depth=8))
        contact=yy+30 if i==0 else yy;sgn=-1 if i==0 else 1
        for xx in (58,70):s=s.cut(cyl((xx,contact,982),1.5,10,(0,sgn,0)));features.append(dict(point=[xx-40,contact-yy,112],direction=[0,sgn,0],diameter=3,depth=10,thread='M3'))
        blocks=[[0,0,0,8,30,118],[8,0,106,32,30,12]]
        out.append(mirror(machined(f'Y_stop_{side}_{i}',s,[40,yy,870],'fixed',blocks,features,
                           ['金属面Y135/865，TCP极限130/670；5mm垫首次接触135/665','正常工作150~650；名义限位145/655；Y轴两侧止挡必须调至同时接触，误差不大于0.2'])))
        for j,zz in enumerate((880,920)):
            for p in fastener(f'Y_stop_{side}_{i}_M6_{j}',(48,yy+15,zz),(-1,0,0),6,20,'fixed',1.6,10.4,'Y止挡接侧型材HNTT8-6'):out.append(mirror(p))
        org=(54,contact+(5 if i==0 else -5),976)
        p=plate(f'Y_bumper_{side}_{i}',(20,12,5),org,[pad_hole(u,6,side='bottom' if i==0 else 'top') for u in (4,16)],axes=((1,0,0),(0,0,1),(0,-1,0)),material='PU90A',notes=['90A聚氨酯板；M3头下沉2，D6.5直壁深2后加工90度沉头；设计压缩不超过1mm'])
        if i:p['shape']=p['shape'].translate((0,5,0));p['manufacturing']['origin_mm']=[54,contact,976]
        out.append(mirror(p))
        for j,xx in enumerate((58,70)):
            for p in fastener(f'Y_bumper_{side}_{i}_M3_{j}',(xx,contact-sgn*3,982),(0,sgn,0),3,12,'fixed',thread_depth=9,joint='Y缓冲垫，头下沉2',style='countersunk'):out.append(mirror(p))
    for i in (0,1):
        sy=150 if i==0 else 850
        s=box((-8,sy-20,908),(8,40,52)).fuse(box((-25,sy-20,950),(25,40,10))).fuse(box((-25,sy-15,960),(10,30,40)))
        fs=[]
        for yy in (sy-10,sy+10):s=s.cut(cyl((-8,yy,920),3.3,8,(1,0,0)));fs.append(dict(point=[17,yy-sy+20,12],direction=[1,0,0],diameter=6.6,depth=8))
        s=s.cut(cyl((-25,sy,984),4.25,10,(1,0,0)));fs.append(dict(point=[0,20,76],direction=[1,0,0],diameter=8.5,depth=10))
        out.append(machined(f'Y_sensor_mount_{i}',s,[-25,sy-20,908],'fixed',[[17,0,0,8,40,52],[0,0,42,25,40,10],[0,5,52,10,30,40]],fs,['Y传感器位于左侧框架外面，避免与X轴下置止挡交叉；面前1mm钢靶']))
        for j,yy in enumerate((sy-10,sy+10)):out+=fastener(f'Y_sensor_mount_{i}_M6_{j}',(-8,yy,920),(1,0,0),6,20,'fixed',1.6,10.4,'Y传感器支架接外侧HNTT8-6')
        out+=sensor(f'Y_limit_{i}',(-2,sy,984),(-1,0,0),'fixed')
        yy=yc-95 if i==0 else yc+75
        out.append(plate(f'Y_target_{i}',(20,20,1),(-1,yy,976),[hole(u,6,3.4) for u in (5,15)],axes=((0,1,0),(0,0,1),(1,0,0)),material='Q235B',motion='Y',notes=['钢靶须朝上延伸至Z996；装配间隙1 +/-0.2']))
        for j,u in enumerate((5,15)):out+=fastener(f'Y_target_{i}_M3_{j}',(-1,yy+u,982),(1,0,0),3,8,'Y',.5,6.5,'钢靶接Y端板外侧边')
    # Z固定止挡伸到滑枕右侧；移动触块直接连接滑枕侧槽。
    for i in (0,1):
        level=890 if i==0 else 1080;sense=882 if i==0 else 1098
        s=box((x+55,yc-78,level-10),(30,8,30)).fuse(box((x+55,yc-155,level),(55,77,10)))
        tabz=872 if i==0 else 1090;s=s.fuse(box((x+100,yc-150,tabz),(10,30,20)))
        features=[]
        for xx,zz in product((x+60,x+70),(level-5,level+15)):
            s=s.cut(cyl((xx,yc-78,zz),2.75,8,(0,1,0)));features.append(dict(point=[xx-(x+55),77,zz-(level-10)],direction=[0,1,0],diameter=5.5,depth=8))
        s=s.cut(cyl((x+100,yc-135,sense),4.25,10,(1,0,0)));features.append(dict(point=[45,20,sense-(level-10)],direction=[1,0,0],diameter=8.5,depth=10))
        for yy in (yc-145,yc-125):s=s.cut(cyl((x+70,yy,level),1.5,10));features.append(dict(point=[15,yy-(yc-155),10],direction=[0,0,1],diameter=3,depth=10,thread='M3'))
        out.append(machined(f'Z_stop_{i}',s,[x+55,yc-155,level-10],'XY',[[0,77,0,30,8,30],[0,0,10,55,77,10],[45,5,tabz-level+10,10,30,20]],features,
                   ['金属极限Z110/640，5mm垫首次接触Z115/635；正常工作120~620','Z名义限位118/632；Z调试速度上限20mm/s，急停反应和制动距离实测后设定']))
        for j,(xx,zz) in enumerate(product((x+60,x+70),(level-5,level+15))):out+=fastener(f'Z_stop_{i}_M5_{j}',(xx,yc-78,zz),(0,1,0),5,20,'XY',1,11,'Z止挡接滑座前面M5')
        out+=sensor(f'Z_limit_{i}',(x+87,yc-135,sense),(1,0,0),'XY')
        padz=level-5 if i==0 else level+10
        out.append(plate(f'Z_bumper_{i}',(30,40,5),(x+55,yc-155,padz),[pad_hole(15,v,side='bottom' if i==0 else 'top') for v in (10,30)],material='PU90A',motion='XY',notes=['90A聚氨酯；M3头下沉2，D6.5直壁深2后加工90度沉头；设计压缩不超过1mm']))
        for j,yy in enumerate((yc-145,yc-125)):out+=fastener(f'Z_bumper_{i}_M3_{j}',(x+70,yy,padz+2 if i==0 else padz+3),(0,0,1 if i==0 else -1),3,12,'XY',thread_depth=9,joint='Z缓冲垫，头下沉2',style='countersunk')
        rel=240 if i==0 else 980
        s=box((x+40,yc-155,z+rel-40),(8,40,40)).fuse(box((x+40,yc-155,z+rel),(45,40,10)))
        feats=[]
        for dz in (rel-30,rel-10):s=s.cut(cyl((x+40,yc-135,z+dz),3.3,8,(1,0,0)));feats.append(dict(point=[0,20,dz-rel+40],direction=[1,0,0],diameter=6.6,depth=8))
        for yy in (yc-145,yc-125):s=s.cut(cyl((x+85,yy,z+rel+5),1.5,8,(-1,0,0)));feats.append(dict(point=[45,yy-yc+155,45],direction=[-1,0,0],diameter=3,depth=8,thread='M3'))
        out.append(machined(f'Z_striker_{i}',s,[x+40,yc-155,z+rel-40],'XYZ',[[0,0,0,8,40,40],[0,0,40,45,40,10]],feats,['移动触块接滑枕侧槽；上下位置按Z基准从滑枕底端190量取；锁紧后画见证线']))
        for j,dz in enumerate((rel-30,rel-10)):out+=fastener(f'Z_striker_{i}_M6_{j}',(x+48,yc-135,z+dz),(-1,0,0),6,20,'XYZ',1.6,10.4,'Z触块接HNTT8-6')
        startz=z+rel-10 if i==0 else z+rel
        out.append(plate(f'Z_target_{i}',(30,20,1),(x+85,yc-150,startz),[hole(u,15 if i==0 else 5,3.4) for u in (5,25)],axes=((0,1,0),(0,0,1),(1,0,0)),material='Q235B',motion='XYZ',notes=['钢靶与移动触块共装；下方钢靶上沿为rel250，上方钢靶下沿为rel980']))
        for j,yy in enumerate((yc-145,yc-125)):out+=fastener(f'Z_target_{i}_M3_{j}',(x+86,yy,z+rel+5),(-1,0,0),3,8,'XYZ',.5,6.5,'Z钢靶接移动触块')
    return out
