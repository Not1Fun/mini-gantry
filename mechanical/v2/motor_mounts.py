"""V2.2 电机安装件。保留X/Y接口；Z顶板加高30mm以容纳传动连接。

X/Y：3mm钢板焊接L座；Z：铝制下鞍座、侧支板和顶板。
紧固件只建包络，不建螺纹；采购传动件仍须单独详设。
"""
from itertools import product
import cadquery as cq
from z_drive import TOP_PLATE_BOTTOM, MOTOR_FACE


def box(p,d):return cq.Solid.makeBox(*d,cq.Vector(*p))
def cyl(p,r,h,axis=(0,0,1)):return cq.Solid.makeCylinder(r,h,cq.Vector(*p),cq.Vector(*axis))


def triangle(plane,points,thickness):
    return cq.Workplane(plane).polyline(points).close().extrude(thickness).val()


def x_bracket(yc):
    base=box((50,yc-20,1080),(80,55,3))
    face=box((50,yc+32,1083),(80,3,102))
    face=face.cut(cyl((90,yc+32,1150),12,3,(0,1,0)))
    face=face.cut(cyl((90,yc+32,1100),12,3,(0,1,0)))
    for dx,dz in product((-15.5,15.5),repeat=2):
        face=face.cut(cyl((90+dx,yc+32,1150+dz),1.75,3,(0,1,0)))
    for xx in (65,115):base=base.cut(cyl((xx,yc,1080),2.75,3))
    base=base.cut(box((71,yc-20,1080),(38,41,3)))
    solid=base.fuse(face)
    for xx in (50,127):
        plane=cq.Plane(origin=(xx,yc-10,1083),xDir=(0,1,0),normal=(1,0,0))
        solid=solid.fuse(triangle(plane,[(0,0),(42,0),(42,47)],3))
    return solid


def y_bracket():
    base=box((40,840,900),(112,80,3))
    face=box((149,840,903),(3,80,177))
    for zz,rr in ((1044,12),(984,9)):
        face=face.cut(cyl((149,880,zz),rr,3,(1,0,0)))
    for dy,dz in product((-15.5,15.5),repeat=2):
        face=face.cut(cyl((149,880+dy,1044+dz),1.75,3,(1,0,0)))
    for xx in (65,125):base=base.cut(cyl((xx,880,900),2.75,3))
    solid=base.fuse(face)
    for yy in (840,917):
        plane=cq.Plane(origin=(50,yy+3,903),xDir=(1,0,0),normal=(0,-1,0))
        solid=solid.fuse(triangle(plane,[(0,0),(99,0),(99,119)],3))
    return solid


def z_holes(x,yc):
    return [(x+dx,yc+dy) for dx in (-35,35) for dy in (-103,-62)]


def z_top_plate(x,yc,z):
    s=box((x-40,yc-110,z+TOP_PLATE_BOTTOM),(80,60,7)).cut(cyl((x,yc-74,z+TOP_PLATE_BOTTOM),12,7))
    for dx,dy in product((-15.5,15.5),repeat=2):
        s=s.cut(cyl((x+dx,yc-74+dy,z+TOP_PLATE_BOTTOM),1.75,7))
    for xx,yy in z_holes(x,yc):s=s.cut(cyl((xx,yy,z+TOP_PLATE_BOTTOM),2.25,7))
    return s


def z_saddle(x,yc,z):
    base=box((x-40,yc-136,z+990),(80,86,6))
    base=base.cut(box((x-30.5,yc-90.5,z+990),(61,35,6)))
    front=box((x-40,yc-136,z+950),(80,6,40))
    for dx,dz in product((-20,20),(960,980)):
        front=front.cut(cyl((x+dx,yc-136,z+dz),2.75,6,(0,1,0)))
    for xx,yy in z_holes(x,yc):
        base=base.cut(cyl((xx,yy,z+990),2.25,6))
        base=base.cut(cq.Solid.makeCone(4,2.25,2,cq.Vector(xx,yy,z+990)))
    return base.fuse(front)


def z_side(x,yc,z,right):
    xx=x+30 if right else x-40
    s=box((xx,yc-110,z+996),(10,60,TOP_PLATE_BOTTOM-996))
    cx=x+35 if right else x-35
    for yy in (yc-103,yc-62):
        s=s.cut(cyl((cx,yy,z+996),2,10))
        s=s.cut(cyl((cx,yy,z+TOP_PLATE_BOTTOM-10),2,10))
    return s


def cap_screw(point,axis,diameter,length,head_diameter,head_height):
    v=cq.Vector(*axis);p=cq.Vector(*point)
    # point 是头下承压面；杆沿 axis 插入，头向反方向延伸。
    return cq.Solid.makeCylinder(diameter/2,length,p,v).fuse(
        cq.Solid.makeCylinder(head_diameter/2,head_height,p-v*head_height,v))


def mounting_parts(tcp):
    x,y,z=tcp;yc=y+100;parts=[]
    def add(name,shape,motion,spec,steel=False,role='custom_motor_bracket'):
        parts.append({'name':name,'shape':shape,'kind':'motor_mount' if role.startswith('custom') else 'screw',
                      'motion':motion,'mass_kg':round(shape.Volume()*(7.85e-6 if steel else 2.7e-6),4),
                      'spec':spec,'role':role})
    add('x_motor_bracket',x_bracket(yc),'Y','3mm钢板焊接L座；4-D3.5/31x31；上下D24分别避让止口和原带轮；2-D5.5接横梁上槽',True)
    add('y_motor_bracket',y_bracket(),'fixed','3mm钢板焊接加筋L座；4-D3.5/31x31；D18避让原D16贯通轴；2-D5.5固定到后横梁',True)
    add('z_motor_lower_saddle',z_saddle(x,yc,z),'XYZ','6061/6mm下鞍座；4-D5.5连接滑枕前槽；4-M4沉头孔连接侧支板')
    for i in (0,1):add(f'z_motor_standoff_{i}',z_side(x,yc,z,bool(i)),'XYZ','6061/10x60x97；上下各2-M4，示意螺纹深10')
    for i,(a,b) in enumerate(product((-15.5,15.5),repeat=2)):
        add(f'x_motor_m3_{i}',cap_screw((90+a,yc+32,1150+b),(0,1,0),2.7,6,5.5,3),'Y','M3x6，不加垫片：穿过3mm板后入电机3mm',True,'fastener_envelope')
        add(f'y_motor_m3_{i}',cap_screw((149,880+a,1044+b),(1,0,0),2.7,6,5.5,3),'fixed','M3x6，不加垫片：穿过3mm板后入电机3mm',True,'fastener_envelope')
        add(f'z_motor_m3_{i}',cap_screw((x+a,yc-74+b,z+TOP_PLATE_BOTTOM),(0,0,1),2.7,10,5.5,3),'XYZ','M3x10：先在台面把电机锁到顶板，再安装顶板',True,'fastener_envelope')
    for i,(xx,yy) in enumerate(z_holes(x,yc)):
        add(f'z_top_m4_{i}',cap_screw((xx,yy,z+MOTOR_FACE),(0,0,-1),3.6,16,7.5,3),'XYZ','M4x16，顶板7mm+入侧支板9mm，示意牙深10',True,'fastener_envelope')
        head=cq.Solid.makeCone(3.75,1.8,1.85,cq.Vector(xx,yy,z+990))
        shaft=cyl((xx,yy,z+991.8),1.8,12.2)
        add(f'z_base_m4_{i}',head.fuse(shaft),'XYZ','M4x14沉头，头部不低于下鞍座底面；装到滑枕前先组装',True,'fastener_envelope')
    for i,xx in enumerate((65,115)):
        add(f'x_mount_m5_{i}',cap_screw((xx,yc,1083),(0,0,-1),4.6,10,8.5,4),'Y','M5示意紧固件；连接4080上槽，螺栓长度和T螺母按实际槽型确定',True,'fastener_envelope')
    for i,xx in enumerate((65,125)):
        add(f'y_mount_m5_{i}',cap_screw((xx,880,903),(0,0,-1),4.6,10,8.5,4),'fixed','M5示意紧固件；连接后横梁上槽',True,'fastener_envelope')
    for i,(dx,dz) in enumerate(product((-20,20),(960,980))):
        add(f'z_saddle_m5_{i}',cap_screw((x+dx,yc-136,z+dz),(0,1,0),4.6,14,8.5,4),'XYZ','M5示意紧固件；下鞍座连接滑枕前面两条槽，实际槽距待供应商确认',True,'fastener_envelope')
    return parts
