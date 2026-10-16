"""可拆摄像头、单计算板和通用控制托板的加工连接。"""
import math
from itertools import product
from fabrication import plate,hole,box,cyl,pose
from drive_fabrication import part,fastener,turned
from accessories import holes,camera_carrier,camera_panel,camera_pose,compute_plate


def accessories(board='pi4b'):
    out=[]
    hs=[hole(xx-375,60,5.5) for xx in (400,500)]
    hs += [hole(xx-375,yy+40,4.5,csk=(9,90),side='bottom') for xx,yy in product((383,517),(-33,-17))]
    out.append(plate('camera_base',(150,80,4),(375,-40,900),hs,notes=['M5x16+1垫圈固定前横梁；4-M4x14沉头从下方固定两耳板']))
    pivot_z=980-4*math.cos(math.pi/6);pivot_y=-23
    for i,xx in enumerate((380,514)):
        hs=[hole(17,pivot_z-904,5.5)]
        edges=[dict(point=[u,0,3],direction=[0,1,0],diameter=4,depth=12,thread='M4') for u in (7,23)]
        out.append(plate(f'camera_pivot_ear_{i}',(30,92,6),(xx,-40,904),hs,axes=((0,1,0),(0,0,1),(1,0,0)),edge_holes=edges,
                       notes=['底部两M4x12有效牙，底孔15深；支承耳平行度0.1；支承轴孔同高+/-0.03']))
        for j,yy in enumerate((-33,-17)):out+=fastener(f'camera_ear_{i}_M4_{j}',(xx+3,yy,900),(0,0,1),4,14,'fixed',0,10,'耳板到底座',style='countersunk')
        direction=1 if i==0 else -1;outer=380 if i==0 else 520
        out+=fastener(f'camera_pivot_M5_{i}',(outer,pivot_y,pivot_z),(direction,0,0),5,30,'fixed',1,8,'俯角轴，M5锁紧螺母；两侧同步夹紧')
        sp_x=386 if i==0 else 512
        s=cyl((sp_x,pivot_y,pivot_z),6,2,(1,0,0)).cut(cyl((sp_x,pivot_y,pivot_z),2.7,2,(1,0,0)))
        out.append(part(f'camera_pivot_spacer_{i}',s,'fixed','PA66 D12/D5.4/L2摩擦隔套',material='PA66',manufacturing=dict(type='turned',steps_mm=[[0,2,12]],bores_mm=[[0,2,5.4]],origin_mm=[sp_x,pivot_y,pivot_z],axes=[[0,1,0],[0,0,1],[1,0,0]],notes=['PA66；厚度2 +/-0.03；按相机重量调节锁紧，不挤坏支耳'])))
        nut_x=398 if i==0 else 497
        s=cyl((nut_x,pivot_y,pivot_z),5,5,(1,0,0)).cut(cyl((nut_x,pivot_y,pivot_z),2.5,5,(1,0,0)))
        out.append(part(f'camera_pivot_nut_{i}',s,'fixed','ISO10511 M5锁紧螺母','45钢',kind='screw'))
    for i,xx in enumerate((400,500)):out+=fastener(f'camera_frame_M5_{i}',(xx,20,904),(0,0,-1),5,16,'fixed',1,11,'相机底板接HNTT8-5')
    p=part('camera_tilt_carrier',camera_pose(camera_carrier()),'fixed','6061-T6俯角载架',manufacturing=dict(type='camera_carrier',origin_mm=[450,-25,980],rotation_x_deg=30,size_mm=[124,100,16],
           plate_box=[-60,-50,0,120,100,5],window=[-45,-35,90,70],holes=[dict(x=u,y=v,diameter=3.4) for u,v in product((-50,50),(-40,40))],
           pivot_bosses=[dict(x=a,length=10,axis_y=0,axis_z=-4,diameter=14,bore=5.5) for a in (-62,52)],
           notes=['整体CNC；两端轴孔同轴D0.05，轴线平行板面0.05；中窗90x70','面板4-M3x14配0.5垫圈及M3锁紧螺母；拆面板不影响俯角载架']))
    out.append(p)
    out.append(part('camera_removable_panel',camera_pose(camera_panel()),'fixed','PETG打印面板毛坯 /120x100x3 /100x80四D3.4；中心80x60适配相机',material='PETG',
                    manufacturing=dict(type='camera_panel_blank',size_mm=[120,100,3],holes=[dict(u=u,v=v,diameter=3.4) for u,v in product((10,110),(10,90))],origin_mm=[-60,-50,5],
                    module_placement=dict(origin=[450,-25,980],axes=[[1,0,0],[0,math.cos(math.pi/6),.5],[0,-.5,math.cos(math.pi/6)]]),
                    notes=['仅统一可拆接口；中央80x60由用户按相机自行设计打印；不预设相机型号','PETG，层高0.2，4层壁，5层顶底，40%填充；安装孔打印后D3.4清孔；支柱处加垫圈'])) )
    for j,(u,v) in enumerate(product((-50,50),(-40,40))):
        for p in fastener(f'camera_panel_M3_{j}',(u,v,8),(0,0,-1),3,14,'fixed',.5,3,'可拆面板/俯角载架/锁紧螺母'):
            p['shape']=camera_pose(p['shape']);out.append(p)
        s=cyl((u,v,-3),3.2,3).cut(cyl((u,v,-3),1.5,3));out.append(part(f'camera_panel_nut_{j}',camera_pose(s),'fixed','M3薄型锁紧螺母','45钢',kind='screw'))
    axes=((1,0,0),(0,0,1),(0,-1,0))
    hs=[hole(u,v,2.9) for board in ('pi4b','jetson_nano') for u,v in holes(board)]
    out.append(plate('compute_combo_plate',(160,170,3),(140,943,160),hs,windows=[(56,88,48,34)],slots=[(30,20,26,5.5,0),(130,20,26,5.5,0)],axes=axes,
                    notes=['Pi4B孔距58x49；Nano官方100x80载板孔距86x58；一次只装一套4个M2.5x10绝缘支柱','两安装槽用M5x14+1垫圈接后横梁槽；可由M5x16修短至14；采购异形Nano载板时另做转接板']))
    for j,xx in enumerate((170,270)):out+=fastener(f'compute_tray_M5_{j}',(xx,943,180),(0,-1,0),5,14,'fixed',1,10,'计算板托板接HNTT8-5')
    for j,(u,v) in enumerate(holes(board)):
        out+=fastener(f'compute_standoff_M25_{j}',(140+u,940,160+v),(0,1,0),2.5,6,'fixed',thread_depth=3,joint='托板接M2.5x10双内牙绝缘支柱')
        out+=fastener(f'compute_board_M25_{j}',(140+u,954.6,160+v),(0,-1,0),2.5,6,'fixed',.5,3.9,'PCB接M2.5x10绝缘支柱')
    hs=[hole(u,20,6.6) for u in (20,220)]
    sl=[(u,v,50,5.5,0) for u,v in product((60,180),(70,130))]
    out.append(plate('controller_tray',(240,180,8),(560,948,160),hs,slots=sl,axes=axes,
                    notes=['通用控制托板，50x5.5长槽供RM A或最小系统板的绝缘转接载板固定','不假定不同控制板共用孔距；载板与接线端子置于预留220x60x160空间内','2-M6x20+1.6垫圈接HNTT8-6，槽内投影10.4；电源入口与动力线应有独立线夹']))
    for j,xx in enumerate((580,780)):out+=fastener(f'controller_tray_M6_{j}',(xx,948,180),(0,-1,0),6,20,'fixed',1.6,10.4,'控制托板接HNTT8-6')
    return out
