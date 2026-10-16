"""承力连接紧固件及可检查的入牙尺寸。"""
from itertools import product
import math
from drive_fabrication import fastener


def structural_fasteners(tcp):
    x,y,z=tcp;yc=y+100;cy=y+18;out=[]
    def bolt(name,p,axis,d,L,motion,washer=0,eng=None,joint='',style='socket'):
        out.extend(fastener(name,p,axis,d,L,motion,washer,eng,joint,style))
    for i,xx in enumerate((20,880)):
        for j in range(14):bolt(f'y_rail_{i}_M4_{j}',(xx,60+60*j,957.7),(0,0,-1),4,16,'fixed',eng=6.3,joint='Y导轨接8mm基板')
        for j in range(7):bolt(f'y_base_{i}_M6_{j}',(xx,90+120*j,948),(0,0,-1),6,16,'fixed',eng=8,joint='Y导轨基板接HNTT8-6',style='countersunk')
        for j,(dy,du,dv) in enumerate(product((-55,55),(-13,13),(-13,13))):bolt(f'y_block_{i}_M4_{j}',(xx+du,yc+dy+dv,987.2),(0,0,-1),4,16,'Y',.8,4,'Y端板接HGH15')
        xx=60 if i==0 else 840
        for j,(du,dv) in enumerate(product((-10,10),repeat=2)):bolt(f'bridge_riser_{i}_M6_{j}',(xx+du,yc+dv,977.6),(0,0,1),6,20,'Y',1.6,8,'端板接垫高块')
        bolt(f'bridge_riser_{i}_M8',(xx,yc,996),(0,0,1),8,14,'Y',eng=10,joint='垫块接横梁底槽；M8x16截短至14并修倒角')
    for i,zz in enumerate((1022.5,1062.5)):
        for j in range(12):bolt(f'x_rail_{i}_M4_{j}',(120+60*j,yc-35.7,zz),(0,1,0),4,14,'Y',eng=4.3,joint='X导轨接6mm基板；M4x14')
        for j in range(6):bolt(f'x_base_{i}_M5_{j}',(150+120*j,yc-26,zz-2.5),(0,1,0),5,16,'Y',eng=10,joint='X导轨基板接HNTT8-5',style='countersunk')
        for j,(dx,du,dv) in enumerate(product((-40,40),(-13,13),(-13,13))):bolt(f'x_block_{i}_M4_{j}',(x+dx+du,yc-65.2,zz+dv),(0,1,0),4,16,'XY',.8,4,'X滑座接HGH15')
    for i,dx in enumerate((-35,35)):
        for j in range(13):bolt(f'z_rail_{i}_M4_{j}',(x+dx,yc-97.3,z+240+60*j),(0,-1,0),4,16,'XYZ',eng=6.3,joint='Z导轨接8mm背板')
        for j,(zz,du,dv) in enumerate(product((915,1045),(-13,13),(-13,13))):bolt(f'z_block_{i}_M4_{j}',(x+dx+du,yc-58.8,zz+dv),(0,-1,0),4,25,'XY',.8,4,'滑座经9mm隔板接Z滑块')
    for j,(dx,dz) in enumerate(product((-20,20),(80,200,320,440,560,680,770))):bolt(f'z_backplate_M6_{j}',(x+dx,yc-107,z+190+dz),(0,-1,0),6,16,'XYZ',eng=8,joint='Z背板接HNTT8-6',style='countersunk')
    for j,(dx,zz) in enumerate(product((-60,60),(955,1000))):bolt(f'nut_cradle_M5_{j}',(x+dx,yc-70,zz),(0,1,0),5,25,'XY',1,8,'螺母托架接X滑座')
    for j,a in enumerate((45,90,135,225,270,315)):
        a=math.radians(a);bolt(f'ballnut_M5_{j}',(x+19*math.cos(a),cy+19*math.sin(a),970),(0,0,-1),5,20,'XY',1,9,'螺母法兰接托架')
    for j,(dx,dz) in enumerate(product((-23,23),(1014.5,1027.5))):bolt(f'z_BK12_M6_{j}',(x+dx,cy+6,z+dz),(0,-1,0),6,40,'XYZ',eng=8,joint='BK12接Z背板；最多外露1mm')
    for j,(dx,dy) in enumerate(product((-40,40),(-28,28))):
        bolt(f'z_motor_top_M4_{j}',(x+dx,cy+dy,z+1130),(0,0,-1),4,16,'XYZ',eng=9,joint='电机顶板接侧板')
        bolt(f'z_motor_bottom_M4_{j}',(x+dx,cy+dy,z+1010),(0,0,1),4,14,'XYZ',eng=8,joint='下鞍座接侧板',style='countersunk')
    for j,(dx,dz) in enumerate(product((-20,20),(960,980))):bolt(f'z_saddle_M5_{j}',(x+dx,yc-161,z+dz),(0,1,0),5,16,'XYZ',1,9,'下鞍座接HNTT8-5')
    for j,(sgn,dy) in enumerate(product((-1,1),(-26,26))):bolt(f'z_brake_carrier_M4_{j}',(x+sgn*44.2,cy+dy,z+1045),(-sgn,0,0),4,20,'XYZ',.8,10,'侧板接抱闸横板')
    for j,a in enumerate((90,210,330)):
        a=math.radians(a);bolt(f'z_brake_M3_{j}',(x+24*math.cos(a),cy+24*math.sin(a),z+1081.9),(0,0,-1),3,40,'XYZ',eng=8.1,joint='抱闸原厂3-V孔接底板')
    for j,dx in enumerate((-20,20)):bolt(f'head_to_ram_M8_{j}',(x+dx,yc-135,z+182),(0,0,1),8,25,'XYZ',1.6,15.4,'夹爪座接滑枕下端M8x20')
    for j,(dx,dy) in enumerate(product((-27,27),(-12,12))):
        bolt(f'head_top_M4_{j}',(x+dx,y+dy,z+190),(0,0,-1),4,20,'XYZ',eng=12,joint='夹爪上板接侧板，沉头避让Z背板',style='countersunk')
        bolt(f'head_bottom_M4_{j}',(x+dx,y+dy,z+64.8),(0,0,1),4,16,'XYZ',.8,12,'夹爪圆板接侧板')
    return out
