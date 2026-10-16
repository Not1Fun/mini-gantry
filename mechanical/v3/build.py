"""V3总装布局。运行：python mechanical/v3/build.py

先布置通用机架与采购外形，再由fabrication模块替换制造接口。
发布状态由release.json控制；不要单独导出遗留布局助手的几何。
坐标：X 左右，Y 前后，Z 向上；输入位置是夹爪 TCP，单位 mm。
"""
from pathlib import Path
from collections import Counter
from itertools import product
import json
import math
import argparse

import cadquery as cq
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
from accessories import BOARD_PATTERNS, holes, compute_plate, board_pose, camera_panel, camera_carrier, camera_pose
from motor_mounts import mounting_parts, z_top_plate
from z_drive import drive_parts, MOTOR_FACE
from xy_drive import drive_parts as xy_parts, motor_position, main_output_pulley

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "design.json").read_text(encoding="utf-8"))
OUT = ROOT / "cad"
DRAW = ROOT / "drawings"
VERIFY = ROOT / "validation"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
COLORS = {"frame": "#b9c3cc", "rail": "#647784", "block": "#334b61",
          "plate": "#247c98", "belt": "#252b31", "motor": "#303b46",
          "screw": "#b9c7d3", "drive": "#d6973e", "control": "#478a70",
          "safety": "#cf6254", "gripper": "#7a838e", "motor_mount":"#be7541"}


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def box(p, dims):
    return cq.Solid.makeBox(*dims, cq.Vector(*p))


def cylinder(p, r, h, axis=(0, 0, 1)):
    return cq.Solid.makeCylinder(r, h, cq.Vector(*p), cq.Vector(*axis))


def ring(p, ro, ri, h, axis=(0, 0, 1)):
    return cylinder(p, ro, h, axis).cut(cylinder(p, ri, h, axis))


def tube(p, dims, axis, wall=3):
    inner = list(dims)
    q = list(p)
    for i in range(3):
        if i != axis:
            inner[i] -= 2 * wall
            q[i] += wall
    return box(p, dims).cut(box(q, inner))


def rod(a, b, radius=4):
    d = np.array(b) - np.array(a)
    return cylinder(a, radius, float(np.linalg.norm(d)), tuple(d))


def bounds(shape):
    b = shape.BoundingBox()
    return [round(v, 4) for v in (b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax)]


def stepper_shape():
    length=CFG["stepper_interface"]["body_length_for_clearance_mm"]
    s=box((-21,-21,0),(42,42,length))
    for xx,yy in product((-15.5,15.5),repeat=2):
        s=s.cut(cylinder((xx,yy,0),1.5,4))
    shaft=cylinder((0,0,-22.5),2.5,20.5)
    shaft=shaft.cut(box((-3,2,-22.5),(6,1,18)))
    for shape in (cylinder((0,0,-2),11,2),shaft,
                  box((-19.5,-19.5,length),(39,39,11)),
                  box((-6.25,19.5,length),(12.5,4.7,11)),
                  box((19.5,-11.25,length),(4,22.5,11))):
        s=s.fuse(shape)
    return s


def make_model(tcp=(450, 400, 370), compute_board="pi4b"):
    if compute_board not in BOARD_PATTERNS:
        raise ValueError("同一位置只能选择 pi4b 或 jetson_nano 中的一块")
    x, y, z = tcp
    yc = y + 100
    parts = []

    def add(name, shape, kind, motion="fixed", mass=None, spec="", role="envelope"):
        if mass is None:
            mass = shape.Volume() * (7.85e-6 if kind in ("rail", "screw") else 2.70e-6)
        parts.append({"name": name, "shape": shape, "kind": kind, "motion": motion,
                      "mass_kg": round(mass, 4), "spec": spec, "role": role})

    # 型材截面是等效薄壁截面，具体槽型与截面惯性矩待供应商确认。
    for i, yy in enumerate((0, 860)):
        add(f"base_cross_{i}", tube((40, yy, 0), (820, 40, 40), 0), "frame", mass=1.23, spec="4040 / L820")
        add(f"top_cross_{i}", tube((40, yy, 860), (820, 40, 40), 0), "frame", mass=1.23, spec="4040 / L820")
    for i, xx in enumerate((0, 860)):
        add(f"base_side_{i}", tube((xx, 0, 0), (40, 900, 40), 1), "frame", mass=1.35, spec="4040 / L900")
        add(f"top_side_{i}", tube((xx, 0, 860), (40, 900, 80), 1), "frame", mass=2.25, spec="4080 / L900")
        for j, yy in enumerate((0, 860)):
            add(f"column_{i}_{j}", tube((xx, yy, 40), (40, 40, 820), 2), "frame", mass=1.23, spec="4040 / L820")
    for i, xx in enumerate((20, 880)):
        add(f"side_brace_a_{i}", rod((xx, 60, 80), (xx, 840, 840)), "screw", mass=.45, spec="M8 拉杆交叉撑 / 待定长")
        add(f"side_brace_b_{i}", rod((xx, 60, 840), (xx, 840, 80)), "screw", mass=.45, spec="M8 拉杆交叉撑 / 待定长")
    add("rear_brace_a", rod((60, 882, 80), (840, 882, 840)), "screw", mass=.45, spec="M8 拉杆交叉撑 / 待定长")
    add("rear_brace_b", rod((60, 888, 840), (840, 888, 80)), "screw", mass=.45, spec="M8 拉杆交叉撑 / 待定长")

    # Y 两轨四滑块，左右皮带由贯通轴同步。
    for i, xx in enumerate((20, 880)):
        add(f"y_rail_{i}", box((xx-7.5, 40, 940), (15, 820, 15)), "rail", mass=1.15, spec="HGR15 / L820")
        for j, dy in enumerate((-55, 55)):
            add(f"y_block_{i}_{j}", box((xx-17, yc+dy-30.7, 949), (34, 61.4, 19)), "block", "Y", .18, "15 级滑块 / 采购接口待确认")
        px = 0 if i == 0 else 820
        add(f"y_end_plate_{i}", box((px, yc-95, 968), (80, 190, 12)), "plate", "Y", spec="6061 / 80 x 190 x 12", role="custom_blank")
        add(f"bridge_riser_{i}", box((40 if i == 0 else 820, yc-20, 980), (40, 40, 20)), "plate", "Y", spec="6061 / 40 x 40 x 20", role="custom_blank")
    add("bridge_4080", tube((40, yc-20, 1000), (820, 40, 80), 0), "frame", "Y", 2.05, "4080 / L820")

    yradius = 3 * 30 / (2 * math.pi)
    for i, xx in enumerate((95, 805)):
        for j, yy in enumerate((60, 880)):
            add(f"y_pulley_{i}_{j}", main_output_pulley("Y",xx,yc) if j else ring((xx-7.5, yy, 984), yradius,4,15,(1,0,0)), "drive", mass=.04, spec="3 mm 节距 / 30T / 15 mm；后轮16孔，节圆包络")
            if j==0:add(f"y_bearing_mount_{i}_{j}", box((xx-24, yy-17, 964), (12, 34, 40)), "plate", mass=.08, spec="轴承/张紧座包络")
        for j, zz in enumerate((984-yradius, 984+yradius)):
            add(f"y_belt_{i}_{j}", box((xx-7.5, 60, zz-1), (15, 820, 2)), "belt", mass=.025, spec="3 mm 节距 / 15 mm 宽；环长约1730，采购复核")
        add(f"y_belt_clamp_{i}", box((xx-12, yc-20, 995), (24, 40, 10)), "plate", "Y", .025, "同步带夹块 / 接至桥架")
    add("motor_Y_ZDT42V2",stepper_shape().rotate((0,0,0),(0,1,0),90).translate(motor_position("Y",yc)),"motor",mass=.528,spec="42ZDT60A 预留：42x42x60 + 11驱动板；具体机身待确认")

    # X 双轨四滑块；轨道/滑块嵌合体积不用于干涉结论。
    for i, zz in enumerate((1015, 1055)):
        add(f"x_rail_{i}", box((100, yc-35, zz), (700, 15, 15)), "rail", "Y", .98, "HGR15 / L700")
        for j, dx in enumerate((-40,40)):
            add(f"x_block_{i}_{j}", box((x+dx-30.7, yc-48, zz-9.5), (61.4, 19, 34)), "block", "XY", .18, "15 级滑块 / 采购接口待确认")
    carrier = box((x-80, yc-60, 860), (160, 12, 240))
    carrier = carrier.cut(box((x-22,yc-61,950),(44,14,60)))
    add("x_z_carrier", carrier, "plate", "XY", spec="6061 / 160 x 240 x 12 / 中央44x60螺母避让窗", role="custom_blank")
    radius = 3 * 20 / (2 * math.pi)
    for i, xx in enumerate((90,810)):
        add(f"x_pulley_{i}",main_output_pulley("X",xx,yc) if i==0 else ring((xx,yc+20,1100),radius,4,15,(0,1,0)),"drive","Y",.03,"3 mm / 20T / 15 mm")
        if i==1:add(f"x_pulley_mount_{i}",box((xx-18,yc-20,1080),(36,40,35)),"plate","Y",.10,"皮带轮支座包络")
        if i==1:add(f"x_pulley_axle_{i}",cylinder((xx,yc-5,1100),4,40,(0,1,0)),"screw","Y",.03,"带两端轴承的输出轴")
    for i, zz in enumerate((1100-radius,1100+radius)):
        add(f"x_belt_{i}",box((90,yc+20,zz-1),(720,15,2)),"belt","Y",.025,"3 mm / 15 mm；环长约 1500，采购复核")
    add("x_belt_clamp",box((x-20,yc-60,1085),(40,97,12)),"plate","XY",.126,"后上置同步带夹块与跨梁连接桥 / 接 X 滑座")
    add("motor_X_ZDT42V2",stepper_shape().rotate((0,0,0),(1,0,0),-90).translate(motor_position("X",yc)),"motor","Y",.528,"42ZDT60A 尺寸预留；5mm D轴，接口按用户尺寸图")

    parts.extend(xy_parts(tcp))

    # Z 滑枕向上收回；固定滑块和固定螺母均装在 X 滑座上。
    add("z_ram_4080",tube((x-40,yc-130,z+190),(80,40,800),2),"frame","XYZ",2.00,"4080 / L800")
    for i, dx in enumerate((-30,30)):
        add(f"z_rail_{i}",box((x+dx-7.5,yc-90,z+230),(15,15,740)),"rail","XYZ",1.04,"HGR15 / L740，安装在随动滑枕")
        for j, zz in enumerate((920,1040)):
            add(f"z_block_{i}_{j}",box((x+dx-17,yc-89,zz-30.7),(34,19,61.4)),"block","XY",.18,"固定滑块 / 中心距120")
            add(f"z_block_spacer_{i}_{j}",box((x+dx-17,yc-70,zz-30.7),(34,10,61.4)),"plate","XY",spec="6061 / 34 x 61.4 x 10",role="custom_blank")
    nut_housing=box((x-20.5,yc-88,955),(41,40,50)).cut(cylinder((x,yc-74,955),8,50))
    add("z_fixed_ballnut",nut_housing,"drive","XY",.22,"1605 螺母及窄型固定座包络，具体螺母外径待核对")
    add("z_nut_rear_flange",box((x-70,yc-48,955),(140,6,50)),"plate","XY",spec="6061 / 140 x 50 x 6，螺母座连接 X 滑座的后法兰",role="custom_blank")
    parts.extend(drive_parts(tcp))
    add("motor_Z_ZDT42V2",stepper_shape().translate((x,yc-74,z+MOTOR_FACE)),"motor","XYZ",.528,"42ZDT60A尺寸预留；Z平台上移30mm，轴端与联轴器按12mm插入")
    add("z_motor_mount",z_top_plate(x,yc,z),"motor_mount","XYZ",spec="6061/7mm：31x31 / 4-D3.5 / D24；新增4-D4.5连接侧支板",role="custom_interface")
    parts.extend(mounting_parts(tcp))

    # 固定轻量夹爪接口，保留 TCP 高度与原有三轴行程。
    wy=yc-100
    add("fixed_head_top",box((x-40,wy-30,z+184),(80,60,6)),"plate","XYZ",spec="6061 / 80 x 60 x 6；固定夹爪转接座",role="custom_blank")
    for i,dx in enumerate((-30,26)):
        side=box((x+dx,wy-20,z+68),(4,40,116))
        side=side.cut(box((x+dx,wy-10,z+88),(4,20,76)))
        add(f"fixed_head_side_{i}",side,"plate","XYZ",spec="6061 / 4 x 40 x 116；20 x 76 减重窗",role="custom_blank")
    flange=ring((x,wy,z+60),35,4,8)
    for angle in range(0,360,90):
        a=math.radians(angle)
        flange=flange.cut(cylinder((x+25*math.cos(a),wy+25*math.sin(a),z+60),2.25,8))
    add("gripper_adapter",flange,"drive","XYZ",spec="D70 x 8；PCD50 / 4-D4.5；中心D8",role="custom_interface")
    gripper=box((x-30,wy-20,z),(60,40,60))
    add("gripper_payload_ENVELOPE",gripper,"gripper","XYZ",CFG["assumptions"]["gripper_and_workpiece_kg"],"夹爪+物料 1 kg 假设；仅用于空间占位")

    add("controller_tray",box((560,900,180),(240,8,180)),"plate",spec="通用 240 x 180 托板；安装槽待详设",role="custom_blank")
    add("RM_A_or_RA6M5_RESERVE",box((570,908,190),(220,60,160)),"control",mass=.30,spec="控制板及端子/线缆空间，非真实板卡模型")
    add("rear_accessory_crossbar",tube((40,860,160),(820,40,40),0),"frame",mass=1.23,spec="4040 / L820；计算板及控制托板安装横梁")
    add("compute_combo_plate",board_pose(compute_plate()),"plate",spec="160 x 170 x 3；Nano 86x58 + Pi4B 58x49 共用孔板",role="custom_board_interface")
    for i,(u,v) in enumerate(holes(compute_board)):
        add(f"compute_standoff_{i}",board_pose(ring((u,v,-10),2.5,1.25,10)),"plate",mass=.003,spec="M2.5 / 10 mm 绝缘支柱；仅安装当前孔组4只")
    if compute_board=="pi4b":
        pcb=box((47.5,77,-11.6),(85,56,1.6))
        ports=box((47.5,77,-41.6),(85,56,30))
    else:
        pcb=box((30,65,-11.6),(100,80,1.6))
        ports=box((30,65,-56.6),(100,80,45))
    for u,v in holes(compute_board):pcb=pcb.cut(cylinder((u,v,-11.6),1.35,1.6))
    add("compute_board_"+compute_board,board_pose(pcb),"control",mass=.05 if compute_board=="pi4b" else .14,spec="选定计算板简化外形；同时只安装一块")
    add("compute_component_clearance",board_pose(ports),"control",mass=.08,spec="散热器/接口包络，实际壳体与散热方案待核对")
    base=box((380,-40,900),(140,80,4))
    for xx in (400,500):base=base.cut(cylinder((xx,20,900),2.75,4))
    add("camera_base",base,"plate",spec="顶部前横梁固定底座 / 140 x 80 x 4 / 2-D5.5",role="custom_interface")
    for i,xx in enumerate((380,514)):
        ear=box((xx,-40,904),(6,30,92)).cut(cylinder((xx,-23,980-4*math.cos(math.pi/6)),2.75,6,(1,0,0)))
        add(f"camera_pivot_ear_{i}",ear,"plate",spec="6 x 30 x 92；M5 俯角夹紧轴孔",role="custom_blank")
        add(f"camera_pivot_screw_{i}",cylinder((xx,-23,980-4*math.cos(math.pi/6)),2.5,18,(1 if i==0 else -1,0,0)),"screw",mass=.006,spec="M5俯角夹紧轴，侧板与载架间2mm垫片空间")
    add("camera_tilt_carrier",camera_pose(camera_carrier()),"plate",spec="120 x 100 x 5；30度初始俯角；90x70通窗",role="custom_camera_interface")
    add("camera_removable_panel",camera_pose(camera_panel()),"plate",spec="统一打印适配板接口：120x100外框，4-D3.4/100x80；中心80x60由用户打印适配多种相机",role="custom_camera_interface")
    for xx in (-50,50):
        for yy in (-40,40):
            add(f"camera_panel_screw_{xx}_{yy}",camera_pose(cylinder((xx,yy,8),2.75,3)),"screw",mass=.002,spec="M3 可拆面板螺钉头包络；螺母与螺杆未详建")
    add("camera_body_ENVELOPE",camera_pose(box((-20,-20,-30),(40,40,35))),"motor",mass=.10,spec="相机外形占位；型号待定，不代表已确认安装孔")
    add("camera_lens_ENVELOPE",camera_pose(cylinder((0,0,-45),7,15)),"motor",mass=.025,spec="镜头朝向工作区，FOV和遮挡待实机验证")
    for i, yy in enumerate((110,875)):
        add(f"Y_limit_{i}",box((45,yy,950),(15,10,20)),"safety",mass=.015,spec="限位开关占位")
    for i, xx in enumerate((100,785)):
        add(f"X_limit_{i}",box((xx,yc-50,1080),(15,10,20)),"safety","Y",.015,"限位开关占位")
    for i, zz in enumerate((880,1100)):
        add(f"Z_limit_{i}",box((x+65,yc-70,zz),(15,10,20)),"safety","XY",.015,"上下限位占位，触发挡块待详设")
    from fabrication import apply
    return apply(parts,tcp)


def assembly(parts):
    a=cq.Assembly(name="MiniGantry_V3_PROTOTYPE")
    for p in parts:
        h=COLORS[p["kind"]].lstrip("#")
        color=cq.Color(*(int(h[i:i+2],16)/255 for i in (0,2,4)))
        a.add(p["shape"],name=p["name"],color=color)
    return a


def render(parts, name, elev=19, azim=-64, zoom=None, prefixes=None, title=None, subtitle=None):
    fig=plt.figure(figsize=(12,11),facecolor="#f6f7f9")
    ax=fig.add_subplot(111,projection="3d",computed_zorder=True)
    ax.set_facecolor("#f6f7f9")
    for p in parts:
        if zoom and not p["name"].startswith(prefixes or ("fixed_head", "gripper")):
            continue
        vertices,faces=p["shape"].tessellate(1.5,0.35)
        vv=np.array([(v.x,v.y,v.z) for v in vertices])
        mesh=Poly3DCollection(vv[np.array(faces)],facecolors=COLORS[p["kind"]],
                              linewidths=.10,edgecolors="#283949",alpha=1,zsort="average")
        ax.add_collection3d(mesh)
    lo=CFG["assumptions"]["tcp_min_mm"]; hi=CFG["assumptions"]["tcp_max_mm"]
    if not zoom:
        corners=list(product(*zip(lo,hi)))
        edges=[[a,b] for i,a in enumerate(corners) for b in corners[i+1:] if sum(u!=v for u,v in zip(a,b))==1]
        ax.add_collection3d(Line3DCollection(edges,colors="#e29e42",linewidths=1.5,linestyles="dashed"))
        ax.set(xlim=(-80,980),ylim=(-110,1050),zlim=(0,1860))
        ax.set_box_aspect((1010,1050,1770),zoom=1.0)
        fig.text(.08,.94,"迷你龙门架  /  V3 样机加工模型",fontsize=22,color="#163348",weight="bold")
        fig.text(.08,.90,"XYZ 各 500 mm · 开口主带、独立输入轴与可调支承 · 可拆摄像头接口",fontsize=11,color="#5a6c78")
        fig.text(.08,.06,"加工状态以同版 release.json 为准",fontsize=12,color="#a85830",weight="bold")
        fig.text(.08,.035,"橙色虚线为夹爪 TCP 工作范围。采购件为简化包络；夹爪与物料合计 1 kg 设计上限。",fontsize=10,color="#5a6c78")
    else:
        ax.set(xlim=zoom[0],ylim=zoom[1],zlim=zoom[2]); ax.set_box_aspect(tuple(b-a for a,b in zoom))
        fig.text(.08,.94,title or "固定轻量夹爪接口  /  V2",fontsize=22,color="#163348",weight="bold")
        fig.text(.08,.90,subtitle or "取消旋转电机和轴承组件，保留500mm三轴行程",fontsize=11,color="#5a6c78")
        fig.text(.08,.055,"结构评审版；实际采购件、紧固方式与制造公差仍需核对。",fontsize=10,color="#a85830")
    ax.view_init(elev=elev,azim=azim)
    ax.set_axis_off(); fig.subplots_adjust(0,.08,1,.91)
    fig.savefig(DRAW/name,dpi=150,facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__=='__main__':
    from release_build import main
    main()
