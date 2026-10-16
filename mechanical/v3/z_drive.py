"""Z轴传动接口布局；采购件只表达目录外形和轴孔，不表达内部齿爪/轴承。"""
from pathlib import Path
import json
import cadquery as cq

CONFIG=json.loads((Path(__file__).with_name('design.json')).read_text(encoding='utf-8'))['z_drive_detail']
MOTOR_FACE=CONFIG['motor_face_z_from_tcp_mm']
TOP_PLATE_BOTTOM=MOTOR_FACE-7
COUPLER_TOP=MOTOR_FACE-22.5+CONFIG['coupling']['insertion_mm']
COUPLER_BOTTOM=COUPLER_TOP-CONFIG['coupling']['length_mm']
SCREW_TIP=COUPLER_BOTTOM+CONFIG['coupling']['insertion_mm']


def cyl(x,y,z,r,h):return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z))
def ring(x,y,z,ro,ri,h):return cyl(x,y,z,ro,h).cut(cyl(x,y,z,ri,h))


def stepped_screw(x,y,z):
    sections=[(195,225,10),(225,985,16),(985,1023,12),(1023,SCREW_TIP,10)]
    result=None
    for lo,hi,d in sections:
        s=cyl(x,y,z+lo,d/2,hi-lo)
        result=s if result is None else result.fuse(s)
    return result


def drive_parts(tcp):
    x,y,z=tcp;cy=y+26;parts=[]
    def add(name,s,kind,spec,mass):
        parts.append(dict(name=name,shape=s,kind=kind,motion='XYZ',mass_kg=mass,
                          spec=spec,role='z_drive_interface'))
    add('z_screw_1605',stepped_screw(x,cy,z),'screw',
        '1605螺纹工作段760；下D10支承段30；上D12轴颈及锁紧段38；D10延长轴伸；轴肩/螺纹/公差待支承供应商冻结',1.35)
    for i,(lo,bore) in enumerate(((195,5),(985,6))):
        s=cq.Solid.makeBox(60,34,30,cq.Vector(x-30,cy-16,z+lo))
        s=s.cut(cyl(x,cy,z+lo,bore,30))
        add(f'z_screw_support_{i}',s,'plate',
            ('下浮动端D10' if i==0 else '上固定端D12')+'；60x34x30接口包络，不是已确认的BK/BF采购模型',.20)
    add('z_screw_locknut',ring(x,cy,z+1015,11,6,6),'screw',
        '上端锁紧螺母D22x6包络，M12x1候选；须随固定端轴承组确认',.012)
    add('z_coupling_screw_hub',ring(x,cy,z+COUPLER_BOTTOM,12.5,5,12),'drive',
        'NBK MJC-25CS尺寸候选：D25，丝杆孔D10，轴插入12；夹紧缝和齿爪未详建',.014)
    add('z_coupling_center_ENVELOPE',ring(x,cy,z+COUPLER_BOTTOM+12,12.5,6,10),'safety',
        '梅花联轴器中间啮合区域包络10；目录弹性体8及两侧C=1，不代表完整齿爪形状',.006)
    add('z_coupling_motor_hub',ring(x,cy,z+COUPLER_TOP-12,12.5,2.5,12),'drive',
        'NBK MJC-25CS尺寸候选：电机孔D5，轴插入12；D形轴方位按厂家夹紧说明核对',.014)
    brake=cq.Solid.makeBox(54,54,30,cq.Vector(x-27,cy-27,z+1023))
    brake=brake.cut(cyl(x,cy,z+1023,5,30))
    add('z_brake_reserve',brake,'safety',
        '54x54x30失电制动器预留；D10轴连接，距联轴器2.5；真实制动器/反力支架及固定孔尚待选型',.25)
    return parts
