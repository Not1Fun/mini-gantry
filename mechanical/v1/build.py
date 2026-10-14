"""生成 V1 结构评审模型。运行：python mechanical/v1/build.py

依赖 CadQuery 2.8、numpy、matplotlib。采购件为简化包络，非加工发布。
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

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "design.json").read_text(encoding="utf-8"))
OUT = ROOT / "cad"
DRAW = ROOT / "drawings"
VERIFY = ROOT / "validation"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
COLORS = {"frame": "#b9c3cc", "rail": "#647784", "block": "#334b61",
          "plate": "#247c98", "belt": "#252b31", "motor": "#303b46",
          "screw": "#b9c7d3", "wrist": "#d6973e", "control": "#478a70",
          "safety": "#cf6254", "gripper": "#7a838e"}


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


def make_model(tcp=(450, 400, 370), yaw=0):
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
            add(f"y_pulley_{i}_{j}", ring((xx-7.5, yy, 984), yradius, 8 if j else 4, 15, (1,0,0)), "wrist", mass=.04, spec="3 mm 节距 / 30T / 15 mm；后轮16孔，节圆包络")
            add(f"y_bearing_mount_{i}_{j}", box((xx-24, yy-17, 964), (12, 34, 40)), "plate", mass=.08, spec="轴承/张紧座包络")
        for j, zz in enumerate((984-yradius, 984+yradius)):
            add(f"y_belt_{i}_{j}", box((xx-7.5, 60, zz-1), (15, 820, 2)), "belt", mass=.025, spec="3 mm 节距 / 15 mm 宽；环长约1730，采购复核")
        add(f"y_belt_clamp_{i}", box((xx-12, yc-20, 995), (24, 40, 10)), "plate", "Y", .025, "同步带夹块 / 接至桥架")
    add("y_sync_shaft", cylinder((75, 880, 984), 8, 750, (1,0,0)), "screw", mass=1.18, spec="贯通轴 D16 / L750，端部另加工")
    add("y_reducer", box((120, 845, 954), (32, 70, 115)), "motor", mass=.32, spec="同步带 3:1 减速组件包络")
    add("motor_Y_ZDT42V2", box((152, 859, 1023), (65, 42, 42)), "motor", mass=.42, spec="NEMA17 + V2 驱动；本体待实测")

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
        add(f"x_pulley_{i}", ring((xx,yc+20,1100),radius,4,15,(0,1,0)),"wrist","Y",.03,"3 mm / 20T / 15 mm")
        add(f"x_pulley_mount_{i}",box((xx-18,yc-20,1080),(36,40,35)),"plate","Y",.10,"皮带轮支座包络")
        add(f"x_pulley_axle_{i}",cylinder((xx,yc-5,1100),4,40,(0,1,0)),"screw","Y",.03,"带两端轴承的输出轴")
    for i, zz in enumerate((1100-radius,1100+radius)):
        add(f"x_belt_{i}",box((90,yc+20,zz-1),(720,15,2)),"belt","Y",.025,"3 mm / 15 mm；环长约 1500，采购复核")
    add("x_belt_clamp",box((x-20,yc-60,1085),(40,97,12)),"plate","XY",.126,"后上置同步带夹块与跨梁连接桥 / 接 X 滑座")
    add("x_reducer",box((65,yc+10,1080),(50,25,95)),"motor","Y",.30,"2:1 同步带减速组件包络")
    add("motor_X_ZDT42V2",box((69,yc+35,1129),(42,65,42)),"motor","Y",.42,"NEMA17 + V2 驱动；本体待实测")

    # Z 滑枕向上收回；固定滑块和固定螺母均装在 X 滑座上。
    add("z_ram_4080",tube((x-40,yc-130,z+190),(80,40,800),2),"frame","XYZ",2.00,"4080 / L800")
    for i, dx in enumerate((-30,30)):
        add(f"z_rail_{i}",box((x+dx-7.5,yc-90,z+230),(15,15,740)),"rail","XYZ",1.04,"HGR15 / L740，安装在随动滑枕")
        for j, zz in enumerate((920,1040)):
            add(f"z_block_{i}_{j}",box((x+dx-17,yc-89,zz-30.7),(34,19,61.4)),"block","XY",.18,"固定滑块 / 中心距120")
            add(f"z_block_spacer_{i}_{j}",box((x+dx-17,yc-70,zz-30.7),(34,10,61.4)),"plate","XY",spec="6061 / 34 x 61.4 x 10",role="custom_blank")
    add("z_screw_1605",cylinder((x,yc-74,z+195),8,850),"screw","XYZ",1.35,"1605 / 支承跨距790 / 顶端含制动轴伸，端部待加工")
    nut_housing=box((x-20.5,yc-88,955),(41,40,50)).cut(cylinder((x,yc-74,955),8,50))
    add("z_fixed_ballnut",nut_housing,"wrist","XY",.22,"1605 螺母及窄型固定座包络，具体螺母外径待核对")
    add("z_nut_rear_flange",box((x-70,yc-48,955),(140,6,50)),"plate","XY",spec="6061 / 140 x 50 x 6，螺母座连接 X 滑座的后法兰",role="custom_blank")
    for i, zz in enumerate((z+195,z+985)):
        block=box((x-30,yc-90,zz),(60,34,30)).cut(cylinder((x,yc-74,zz),8,30))
        add(f"z_screw_support_{i}",block,"plate","XYZ",.20,"固定/支承端组件包络，螺母随滑座固定")
    add("z_coupling",ring((x,yc-74,z+1045),12,2.5,25),"wrist","XYZ",.06,"联轴器 5/10 候选，实物轴径待核对")
    add("motor_Z_ZDT42V2",box((x-21,yc-95,z+1070),(42,42,65)),"motor","XYZ",.42,"NEMA17 + V2 驱动；本体待实测")
    brake=box((x-27,yc-101,z+1015),(54,54,30)).cut(cylinder((x,yc-74,z+1015),8,30))
    add("z_brake_reserve",brake,"safety","XYZ",.25,"丝杆轴伸上的独立失电制动器；壳体固定滑枕，不能装在驱动板尾部")
    motor_mount=box((x-40,yc-110,z+1063),(80,60,7)).cut(cylinder((x,yc-74,z+1063),12,7))
    for dx,dy in product((-15.5,15.5),repeat=2):
        motor_mount=motor_mount.cut(cylinder((x+dx,yc-74+dy,z+1063),1.75,7))
    add("z_motor_mount",motor_mount,"plate","XYZ",.09,"NEMA17 候选：31x31 / 4-D3.5 / 中心D24；实物复核",role="custom_interface")
    for i, dx in enumerate((-40,34)):
        add(f"z_motor_standoff_{i}",box((x+dx,yc-110,z+990),(6,60,73)),"plate","XYZ",spec="6061 / 6 x 60 x 73",role="custom_blank")

    # 腕部：独立轴承承担载荷，DM 转子只通过待定联轴盘驱动空心轴。
    wy=yc-100
    add("wrist_top_plate",box((x-47,wy-47,z+178),(94,94,12)),"plate","XYZ",spec="6061 / 94 x 94 x 12；电机孔待实测",role="custom_blank")
    for i, dx in enumerate((-47,41)):
        add(f"wrist_side_{i}",box((x+dx,wy-35,z+70),(6,70,108)),"plate","XYZ",spec="6061 / 6 x 70 x 108",role="custom_blank")
    add("DM_G6220",ring((x,wy,z+134),34,5,41.5),"wrist","XYZ",.4935,"厂家外形 D68 x 41.5；中心孔及安装细节未释放")
    add("wrist_motor_coupling",ring((x,wy,z+120),20,10,14),"wrist","XYZ",.06,"待按 DM 转子孔位加工的传扭联接盘")
    lower=box((x-47,wy-40,z+70),(94,80,8)).cut(cylinder((x,wy,z+70),11,8))
    add("wrist_lower_plate",lower,"plate","XYZ",spec="6061 / 94 x 80 x 8；中央D22；旋转盘与底板间隙2",role="custom_blank")
    housing=box((x-32,wy-32,z+78),(64,64,46)).cut(cylinder((x,wy,z+78),21,46))
    add("wrist_bearing_housing",housing,"plate","XYZ",spec="6061 / 64 x 64 x 46；示意贯通孔，肩位/预紧待详设",role="custom_blank")
    for i, zz in enumerate((z+82,z+104)):
        add(f"wrist_bearing_7004_{i}",ring((x,wy,zz),21,10,12),"rail","XYZ",.07,"7004 / 20 x 42 x 12，背对背组合；简化外包络")
    add("wrist_hollow_spindle",ring((x,wy,z+68),10,4,62),"screw","XYZ",.15,"空心轴 D20 / 内孔8；轴肩和锁紧待详设")
    flange=ring((x,wy,z+60),35,4,8)
    for angle in range(0,360,90):
        a=math.radians(angle)
        flange=flange.cut(cylinder((x+25*math.cos(a),wy+25*math.sin(a),z+60),2.25,8))
    flange=flange.rotate((x,wy,0),(x,wy,1),yaw)
    add("gripper_adapter",flange,"wrist","XYZ",spec="D70 x 8；PCD50 / 4-D4.5；中心D8",role="custom_interface")
    gripper=box((x-30,wy-20,z),(60,40,60)).rotate((x,wy,0),(x,wy,1),yaw)
    add("gripper_payload_ENVELOPE",gripper,"gripper","XYZ",CFG["assumptions"]["gripper_and_workpiece_kg"],"夹爪+物料 1 kg 假设；仅用于空间占位")

    add("controller_tray",box((560,900,180),(240,8,180)),"plate",spec="通用 240 x 180 托板；安装槽待详设",role="custom_blank")
    add("RM_A_or_RA6M5_RESERVE",box((570,908,190),(220,60,160)),"control",mass=.30,spec="控制板及端子/线缆空间，非真实板卡模型")
    for i, yy in enumerate((110,875)):
        add(f"Y_limit_{i}",box((45,yy,950),(15,10,20)),"safety",mass=.015,spec="限位开关占位")
    for i, xx in enumerate((100,785)):
        add(f"X_limit_{i}",box((xx,yc-50,1080),(15,10,20)),"safety","Y",.015,"限位开关占位")
    for i, zz in enumerate((880,1100)):
        add(f"Z_limit_{i}",box((x+65,yc-70,zz),(15,10,20)),"safety","XY",.015,"上下限位占位，触发挡块待详设")
    return parts


def assembly(parts):
    a=cq.Assembly(name="MiniGantry_V1_CONCEPT")
    for p in parts:
        h=COLORS[p["kind"]].lstrip("#")
        color=cq.Color(*(int(h[i:i+2],16)/255 for i in (0,2,4)))
        a.add(p["shape"],name=p["name"],color=color)
    return a


def render(parts, name, elev=19, azim=-64, zoom=None):
    fig=plt.figure(figsize=(12,11),facecolor="#f6f7f9")
    ax=fig.add_subplot(111,projection="3d",computed_zorder=True)
    ax.set_facecolor("#f6f7f9")
    for p in parts:
        if zoom and not p["name"].startswith(("wrist", "DM_", "gripper")):
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
        ax.set(xlim=(-30,980),ylim=(-30,1020),zlim=(0,1770))
        ax.set_box_aspect((1010,1050,1770),zoom=1.0)
        fig.text(.08,.94,"迷你龙门架  /  V1 结构布局",fontsize=22,color="#163348",weight="bold")
        fig.text(.08,.90,"XYZ 有效行程各 500 mm · 水平同步带 · 升降滑枕 · DM-G6220 旋转腕",fontsize=11,color="#5a6c78")
        fig.text(.08,.06,"结构评审版 · 尚未释放加工",fontsize=12,color="#a85830",weight="bold")
        fig.text(.08,.035,"橙色虚线为夹爪 TCP 工作范围。采购件为简化包络；负载暂按夹爪与物料合计 1 kg。",fontsize=10,color="#5a6c78")
    else:
        ax.set(xlim=zoom[0],ylim=zoom[1],zlim=zoom[2]); ax.set_box_aspect((140,140,220))
        fig.text(.08,.94,"独立支撑旋转腕  /  V1",fontsize=22,color="#163348",weight="bold")
        fig.text(.08,.90,"DM-G6220 传递转矩 · 双角接触轴承承载 · 空心输出轴",fontsize=11,color="#5a6c78")
        fig.text(.08,.055,"电机接口、轴肩、锁紧与预紧待详设；模型用于空间与载荷路径评审。",fontsize=10,color="#a85830")
    ax.view_init(elev=elev,azim=azim)
    ax.set_axis_off(); fig.subplots_adjust(0,.08,1,.91)
    fig.savefig(DRAW/name,dpi=150,facecolor=fig.get_facecolor())
    plt.close(fig)


def engineering(parts):
    a=CFG["assumptions"]
    masses={axis:sum(p["mass_kg"] for p in parts if axis in p["motion"].upper() and p["motion"]!="fixed") for axis in "XYZ"}
    checks={}
    for k,axis in enumerate("XYZ"):
        lead=.005 if axis=="Z" else .003*20/2
        eta=.9
        force=masses[axis]*(a["accel_xyz_mm_s2"][k]/1000+(9.81 if axis=="Z" else 0))+a["friction_xyz_N"][k]
        translational=force*lead/(2*math.pi*eta)
        inertia=0.000035 if axis=="Z" else 0.00002
        rotational=inertia*2*math.pi*(a["accel_xyz_mm_s2"][k]/1000)/lead
        raw=translational+rotational+(a["z_preload_torque_Nm"] if axis=="Z" else 0)
        checks[axis]={"moving_mass_estimate_kg":round(masses[axis],3),"speed_mm_s":a["speed_xyz_mm_s"][k],
                      "motor_rpm":round(a["speed_xyz_mm_s"][k]/(lead*1000)*60,1),
                      "linear_force_N":round(force,2),"motor_torque_raw_Nm":round(raw,4),
                      "motor_required_curve_torque_with_factor_Nm":round(raw*a["torque_factor"],4),
                      "motor_suitability":"UNVERIFIED: compare actual motor torque-speed curve and thermal rating",
                      "assumed_motor_side_rotating_inertia_kg_m2":inertia}
    span=820
    vertical=masses["X"]*9.81*span**3/(48*a["beam_elastic_modulus_N_mm2"]*a["beam_I_strong_mm4"])
    lateral=checks["X"]["linear_force_N"]*span**3/(48*a["beam_elastic_modulus_N_mm2"]*a["beam_I_weak_mm4"])
    critical=.8*2.71e8*.689*a["z_screw_root_diameter_mm"]/790**2
    report={"status":"PRELIMINARY_HAND_CALCULATION_NOT_LOAD_CERTIFICATION","axes":checks,
            "z_screw_permissible_speed_estimate_rpm":round(critical),
            "z_screw_support_assumption":"fixed-supported; root diameter 13.5 mm; unsupported span 790 mm",
            "bridge_simple_support_deflection_mm":{"vertical_point_load":round(vertical,4),"lateral_point_load":round(lateral,4)},
            "excluded_effects":["接头/支架柔度","型材实际截面","导轨安装误差","带伸长和齿隙","Z 滑枕和腕部偏心扭转","实际摩擦和预紧力","实际负载和热态电机性能"],
            "brake":{"minimum_holding_torque_candidate_Nm":round(2*masses["Z"]*9.81*.005/(2*math.pi),3),"status":"candidate only; verify brake location, shaft coupling and loss-of-power performance"},
            "payload_kg":a["gripper_and_workpiece_kg"],"mass_basis":"BOM estimates, not measured assembly mass"}
    dump(VERIFY/"engineering.json",report)
    return report


def validate(parts):
    invalid=[p["name"] for p in parts if not p["shape"].isValid() or p["shape"].Volume()<=0]
    poses=[]
    lo,hi=CFG["assumptions"]["tcp_min_mm"],CFG["assumptions"]["tcp_max_mm"]
    for x,y,z in product(*zip(lo,hi)):
        yc=y+100
        clearance={"Y_front_rail":yc-55-30.7-40,"Y_rear_rail":860-(yc+55+30.7),
                   "X_left_rail":x-40-30.7-100,"X_right_rail":800-(x+40+30.7),
                   "Z_lower_rail":920-30.7-(z+230),"Z_upper_rail":z+970-(1040+30.7),
                   "Z_nut_to_lower_support":955-(z+225),"Z_nut_to_upper_support":z+985-1005}
        poses.append({"tcp_mm":[x,y,z],"support_margins_mm":{k:round(v,2) for k,v in clearance.items()},"all_positive":min(clearance.values())>0})
    data={"status":"PASS_LAYOUT_CHECKS" if not invalid and all(p["all_positive"] for p in poses) else "FAIL",
          "invalid_solids":invalid,"component_count":len(parts),"unique_names":len(set(p["name"] for p in parts))==len(parts),
          "travel_mm":[b-a for a,b in zip(lo,hi)],"eight_corner_support_checks":poses,
          "maximum_z_mm":hi[2]+1135,"frame_plan_mm":[900,900],"controller_rear_extent_mm":968,
          "checks_not_performed":["完整装配干涉排除：导轨/滑块、支架包络存在有意重合","采购接口配合","所有线缆/拖链运动","紧固件可达性","FEA和物理承载试验"],
          "geometry_scope":CFG["model_scope"]}
    dump(VERIFY/"layout.json",data)
    if data["status"]!="PASS_LAYOUT_CHECKS" or not data["unique_names"]:
        raise RuntimeError(data)


def export_parts(parts):
    records=[]
    for p in parts:
        records.append({k:v for k,v in p.items() if k!="shape"}|{"bbox_mm":bounds(p["shape"]),"volume_mm3":round(p["shape"].Volume(),3)})
    dump(ROOT/"bom.json",{"stage":"结构 BOM；非采购放行清单","mass_note":"估算值；型材和采购件使用简化质量；未逐颗计紧固件", "items":records})
    cutlist=Counter(p["spec"] for p in parts if p["kind"]=="frame")
    dump(ROOT/"cutlist.json",{"status":"PRELIMINARY_CUT_LENGTHS_VERIFY_JOINTS_BEFORE_CUTTING", "items":[{"profile_and_length":k,"quantity":v} for k,v in cutlist.items()]})
    custom=OUT/"custom_parts"; custom.mkdir(exist_ok=True)
    for p in parts:
        if p["role"].startswith("custom"):
            b=p["shape"].BoundingBox()
            local=p["shape"].translate((-b.xmin,-b.ymin,-b.zmin))
            cq.exporters.export(local,str(custom/(p["name"]+".step")))
            if p["role"]=="custom_interface":
                wires=cq.Workplane("XY").newObject([local]).faces("<Z").wires()
                cq.exporters.export(wires,str(custom/(p["name"]+".dxf")))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--no-render",action="store_true")
    args=ap.parse_args()
    for p in (OUT,DRAW,VERIFY):p.mkdir(parents=True,exist_ok=True)
    parts=make_model(CFG["assumptions"]["illustration_pose_mm"])
    print("Geometry:",len(parts),"components",flush=True)
    validate(parts); engineering(parts); export_parts(parts)
    step=OUT/"mini_gantry_v1.step"
    assembly(parts).save(str(step))
    imported=cq.importers.importStep(str(step)).val()
    dump(VERIFY/"step_roundtrip.json",{"valid":imported.isValid(),"solids":len(imported.Solids()),
         "source_solids":sum(len(p["shape"].Solids()) for p in parts),"bbox_mm":bounds(imported),
         "source_volume_mm3":sum(p["shape"].Volume() for p in parts),"imported_volume_mm3":imported.Volume()})
    assert imported.isValid()
    assert len(imported.Solids())==sum(len(p["shape"].Solids()) for p in parts)
    assert abs(imported.Volume()-sum(p["shape"].Volume() for p in parts))<1
    cq.exporters.export(cq.Compound.makeCompound([p["shape"] for p in parts]),str(OUT/"mini_gantry_v1.stl"),tolerance=1.0,angularTolerance=.35)
    if not args.no_render:
        render(parts,"assembly.png")
        render(make_model((450,400,620)),"z_retracted.png")
        render(make_model((450,400,120)),"z_extended.png")
        render(parts,"wrist.png",elev=18,azim=-50,zoom=((380,520),(330,470),(350,580)))
    print("Build and STEP round-trip passed",flush=True)


if __name__=="__main__":main()
