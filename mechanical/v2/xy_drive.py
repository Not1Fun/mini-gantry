"""S3M减速级与输出轴支承；不建齿槽、滚珠及螺纹。局部d轴朝电机出轴方向。"""
from pathlib import Path
import json
import math
import cadquery as cq

CFG=json.loads(Path(__file__).with_name('design.json').read_text(encoding='utf-8'))['xy_reduction_detail']


def box(p,d):return cq.Solid.makeBox(*d,cq.Vector(*p))
def cyl(p,r,h,axis=(0,0,1)):return cq.Solid.makeCylinder(r,h,cq.Vector(*p),cq.Vector(*axis))
def ring(p,ro,ri,h,axis=(0,0,1)):return cyl(p,ro,h,axis).cut(cyl(p,ri,h,axis))


def belt_length(c,r,R):
    a=math.asin((R-r)/c)
    return 2*math.sqrt(c*c-(R-r)**2)+math.pi*(R+r)+2*(R-r)*a


def center_distance(axis):
    spec=CFG[axis];r,R=[n*CFG['pitch_mm']/(2*math.pi) for n in spec['teeth']]
    lo=R-r+.001;hi=spec['pitch_length_mm']/2
    for _ in range(60):
        m=(lo+hi)/2
        if belt_length(m,r,R)>spec['pitch_length_mm']:hi=m
        else:lo=m
    return (lo+hi)/2


CENTERS={a:center_distance(a) for a in ('X','Y')}


def motor_position(axis,yc):
    return (90,yc+CFG['X']['motor_face_y_from_yc_mm'],1100+CENTERS['X']) if axis=='X' else (152,880,984+CENTERS['Y'])


def locate(shape,axis,yc):
    if axis=='Y':shape=shape.rotate((0,0,0),(0,1,0),-90)
    shape=shape.rotate((0,0,0),(1,0,0),90)
    origin=(90,yc+60,1100) if axis=='X' else (152,880,984)
    return shape.translate(origin)


def belt_wire(c,r,R):
    a=math.asin((R-r)/c);co,si=math.cos(a),math.sin(a)
    return (cq.Workplane('XY').moveTo(R*co,R*si).lineTo(r*co,c+r*si)
            .threePointArc((0,c+r),(-r*co,c+r*si)).lineTo(-R*co,R*si)
            .threePointArc((0,-R),(R*co,R*si)).close().val())


def reduction_belt(axis):
    s=CFG[axis];r,R=[n*3/(2*math.pi) for n in s['teeth']];c=CENTERS[axis]
    inner=belt_wire(c,r-.381,R-.381);outer=belt_wire(c,r+1.719,R+1.719)
    face=cq.Face.makeFromWires(outer,[inner])
    return cq.Solid.extrudeLinear(face.outerWire(),face.innerWires(),cq.Vector(0,0,6)).translate((0,0,s['belt_axial_d_mm'][0]))


def reduction_pulley(axis,input_side):
    s=CFG[axis];n=s['teeth'][0 if input_side else 1];a=s['belt_axial_d_mm'][0]
    bore=2.5 if input_side else s['output_bore_mm']/2
    hub=7 if input_side else s['output_hub_diameter_mm']/2
    flange={20:11,40:22,60:30.5}[n];v=CENTERS[axis] if input_side else 0
    result=ring((0,v,a-1),n*3/(2*math.pi)-.381,bore,8)
    for d in (a-2,a+7):result=result.fuse(ring((0,v,d),flange,bore,1))
    result=result.fuse(ring((0,v,a-8),hub,bore,6))
    if input_side:
        # 两台电机D面经各自装配旋转后的方向不同。
        p=(0,v-hub,a-5) if axis=='X' else (-hub,v,a-5)
        direction=(0,1,0) if axis=='X' else (1,0,0)
        result=result.cut(cyl(p,1.5,hub,direction))
    else:result=result.cut(cyl((0,hub,a-5),2,hub,(0,-1,0)))
    return result


def main_output_pulley(axis,position,yc):
    if axis=='X':
        s=ring((90,yc+20,1100),3*20/(2*math.pi),4,15,(0,1,0))
        return s.cut(cyl((90,yc+27.5,1110),1.5,7,(0,0,-1)))
    xx=position
    s=ring((xx-7.5,880,984),3*30/(2*math.pi),8,15,(1,0,0))
    return s.cut(cyl((xx,880,999),1.5,8,(0,0,-1)))


def x_shaft(yc):
    s=cyl((90,yc-31,1100),4,93,(0,1,0))
    for lo,hi in ((20,35),(47,53)):
        s=s.cut(box((85,yc+lo,1103.5),(10,hi-lo,2)))
    return s


def y_shaft():
    s=cyl((55,880,984),7.5,790,(1,0,0))
    s=s.fuse(cyl((87.5,880,984),8,725,(1,0,0)))
    for lo,hi in ((87.5,102.5),(141,147),(797.5,812.5)):
        s=s.cut(box((lo,870,991.5),(hi-lo,20,2)))
    return s


def x_housing(yc):
    s=box((72,yc-20,1080),(36,35,35))
    s=s.cut(cyl((90,yc-20,1100),5.25,35,(0,1,0)))
    for yy in (yc-20,yc+8):s=s.cut(cyl((90,yy,1100),11,7,(0,1,0)))
    for xx in (78,102):
        s=s.cut(cyl((xx,yc,1080),2.75,35))
        s=s.cut(cyl((xx,yc,1107),4.25,8))
    for yy,direction in ((yc-20,1),(yc+15,-1)):
        for xx in (78,102):
            for zz in (1088,1112):s=s.cut(cyl((xx,yy,zz),1.5,8,(0,direction,0)))
    return s


def x_cover(yc,back):
    yy=yc+15 if back else yc-23
    s=box((74,yy,1084),(32,3,32)).cut(cyl((90,yy,1100),6,3,(0,1,0)))
    for xx in (78,102):
        for zz in (1088,1112):s=s.cut(cyl((xx,yy,zz),1.75,3,(0,1,0)))
    return s


def y_support():
    s=box((42,860,900),(43,40,6)).fuse(box((65,856,906),(20,48,106)))
    s=s.cut(cyl((65,880,984),10.5,20,(1,0,0)))
    s=s.cut(cyl((65,880,984),17.5,16,(1,0,0)))
    for xx in (50,60):s=s.cut(cyl((xx,880,900),2.75,6))
    for yy in (860,900):
        for zz in (964,1004):s=s.cut(cyl((65,yy,zz),1.5,8,(1,0,0)))
    return s


def y_cover():
    s=box((62,856,960),(3,48,48)).fuse(cyl((65,880,984),17.5,5,(1,0,0)))
    s=s.cut(cyl((62,880,984),10.5,8,(1,0,0)))
    for yy in (860,900):
        for zz in (964,1004):s=s.cut(cyl((62,yy,zz),1.75,3,(1,0,0)))
    return s


def drive_parts(tcp):
    _,y,_=tcp;yc=y+100;parts=[]
    def add(name,s,kind,motion,spec,mass=None):
        density=7.85e-6 if kind in ('screw','block') else 2.7e-6
        parts.append(dict(name=name,shape=s,kind=kind,motion=motion,spec=spec,
                          mass_kg=round(s.Volume()*density if mass is None else mass,4),role='xy_drive_interface'))
    for axis in ('X','Y'):
        tag=axis.lower();motion='Y' if axis=='X' else 'fixed';s=CFG[axis]
        for input_side in (True,False):
            label='input' if input_side else 'driven'
            add(f'{tag}_reduction_{label}_pulley',locate(reduction_pulley(axis,input_side),axis,yc),'drive',motion,
                f"S3M {s['teeth'][0 if input_side else 1]}T；轮毂/紧定孔为接口约束，未建齿槽")
        add(f'{tag}_reduction_belt',locate(reduction_belt(axis),axis,yc),'belt',motion,
            f"S3M / {s['pitch_length_mm']}节线长 / 6宽 / {s['belt_teeth']}齿；弹性与预紧未仿真",.012)
        d=s['belt_axial_d_mm'][0]-5;c=CENTERS[axis]
        start=(0,c-6,d) if axis=='X' else (-6,c,d)
        direction=(0,1,0) if axis=='X' else (1,0,0)
        add(f'{tag}_reduction_input_set_screw',locate(cyl(start,1.35,4,direction),axis,yc),'screw',motion,
            'M3x4平端紧定螺钉包络，顶到电机D面；实际拧紧扭矩/防松待厂商确认')
        flat=3.5 if axis=='X' else 7.5;length=10 if axis=='X' else 8
        add(f'{tag}_reduction_driven_set_screw',locate(cyl((0,flat,d),1.8,length,(0,1,0)),axis,yc),'screw',motion,
            f'M4x{length}平端紧定螺钉包络；轮毂及轴平面锁紧能力待确认')
    add('x_main_pulley_set_screw',cyl((90,yc+27.5,1103.5),1.35,4),'screw','Y','M3x4平端紧定；拆主带后检修，防松方案待确认')
    for i,xx in enumerate((95,805)):
        add(f'y_main_pulley_set_screw_{i}',cyl((xx,880,991.5),1.35,5),'screw','fixed','M3x5平端紧定；拆主带后检修，防松方案待确认')
    add('x_pulley_mount_0',x_housing(yc),'plate','Y','6061双608轴承座；2-M5沉孔接横梁顶槽；轴承座与盖孔公差待冻结')
    add('x_pulley_axle_0',x_shaft(yc),'screw','Y','D8输出轴L93；主带轮和减速轮毂位置铣0.5平面')
    for i,yy in enumerate((yc-20,yc+8)):
        add(f'x_output_bearing_{i}',ring((90,yy,1100),11,4,7,(0,1,0)),'block','Y','608 / 8x22x7；密封/游隙/配合待确认',.0121)
        add(f'x_output_cover_{i}',x_cover(yc,bool(i)),'plate','Y','32x32x3端盖 / 4-M3x8，锁外圈，D12孔避让内圈隔套')
    for i,(lo,hi) in enumerate(((-24,-20),(-13,8),(15,20),(35,37),(53,55))):
        add(f'x_output_spacer_{i}',ring((90,yc+lo,1100),5,4,hi-lo,(0,1,0)),'screw','Y','D10/D8内圈隔套，长度按轴向尺寸链；公差/预紧待确认')
    for i,lo in enumerate((-30,55)):
        add(f'x_output_collar_{i}',ring((90,yc+lo,1100),7,4,6,(0,1,0)),'screw','Y','D8夹紧轴环14外径/6宽约束，夹紧螺钉未详建')
    add('y_sync_shaft',y_shaft(),'screw','fixed','D16中段725；两端D15轴颈各32.5；总长790；三轮毂处0.5平面')
    for i in (0,1):
        mirror=lambda s:s if i==0 else s.mirror('YZ',(450,0,0))
        add(f'y_rear_support_{i}',mirror(y_support()),'plate','fixed','6061一体支承座；脚板2-M5接后横梁顶槽；6202孔位需加工同轴')
        add(f'y_rear_cover_{i}',mirror(y_cover()),'plate','fixed','6202外圈定位盖/4-M3x8；D21孔避让D20内圈隔套')
        add(f'y_rear_bearing_{i}',mirror(ring((70,880,984),17.5,7.5,11,(1,0,0))),'block','fixed','6202 / 15x35x11；安装配合和密封待确认',.045)
        for j,(lo,hi) in enumerate(((60,70),(81,87.5))):
            add(f'y_rear_spacer_{i}_{j}',mirror(ring((lo,880,984),10,7.5,hi-lo,(1,0,0))),'screw','fixed','D20/D15隔套；承靠6202内圈，避免轴肩D16过小')
        add(f'y_rear_collar_{i}',mirror(ring((55,880,984),12,7.5,5,(1,0,0))),'screw','fixed','D15夹紧轴环/24外径/5宽约束；夹紧螺钉未详建')
    return parts
