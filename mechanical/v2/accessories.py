"""可替换计算板托板与可拆摄像头面板；局部坐标单位 mm。"""
import cadquery as cq

BOARD_PATTERNS = {
    "pi4b": {"pitch": (58,49), "name":"Raspberry Pi 4B", "source":"https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-mechanical-drawing.pdf"},
    "jetson_nano": {"pitch": (86,58), "name":"Jetson Nano official developer carrier footprint", "source":"https://cdn.shopifycdn.net/s/files/1/0604/5905/7341/files/Holybro_X650_Assembly_Guide_V1.1.pdf?v=1718154187"}
}


def holes(key):
    px,py=BOARD_PATTERNS[key]["pitch"]
    return [(80+dx*px/2,105+dy*py/2) for dx in (-1,1) for dy in (-1,1)]


def slot(cx,cy,length,width,height):
    return cq.Workplane("XY").center(cx,cy).slot2D(length,width).extrude(height).val()


def compute_plate():
    s=cq.Workplane("XY").box(160,170,3,centered=(False,False,False)).val()
    for key in BOARD_PATTERNS:
        for x,y in holes(key):
            s=s.cut(cq.Solid.makeCylinder(1.45,3,cq.Vector(x,y,0)))
    for x in (30,130):s=s.cut(slot(x,20,26,5.5,3))
    s=s.cut(cq.Solid.makeBox(48,34,3,cq.Vector(56,88,0)))
    return s


def board_pose(s):
    return s.rotate((0,0,0),(1,0,0),90).translate((140,903,160))


def camera_carrier():
    s=cq.Solid.makeBox(120,100,5,cq.Vector(-60,-50,0))
    s=s.cut(cq.Solid.makeBox(90,70,5,cq.Vector(-45,-35,0)))
    for x in (-50,50):
        for y in (-40,40):s=s.cut(cq.Solid.makeCylinder(1.7,5,cq.Vector(x,y,0)))
    for x in (-62,52):
        boss=cq.Solid.makeCylinder(7,10,cq.Vector(x,0,-4),cq.Vector(1,0,0))
        boss=boss.cut(cq.Solid.makeCylinder(2.75,10,cq.Vector(x,0,-4),cq.Vector(1,0,0)))
        s=s.fuse(boss)
    return s


def camera_panel():
    s=cq.Solid.makeBox(120,100,3,cq.Vector(-60,-50,5))
    for x in (-50,50):
        for y in (-40,40):s=s.cut(cq.Solid.makeCylinder(1.7,3,cq.Vector(x,y,5)))
    return s


def camera_pose(s):
    return s.rotate((0,0,0),(1,0,0),30).translate((450,-25,980))
