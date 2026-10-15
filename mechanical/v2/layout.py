"""生成结构布局和接口示意图；单位 mm。非零件加工图。"""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch

ROOT=Path(__file__).resolve().parent
plt.rcParams.update({"font.sans-serif":["Microsoft YaHei","SimHei","DejaVu Sans"],
                     "axes.unicode_minus":False,"svg.fonttype":"none"})
C={"frame":"#c9d1d8","plate":"#3986a0","rail":"#596f80","motor":"#334655","work":"#c7842f","ink":"#173548"}


def rect(ax,x,y,w,h,color,**kw):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=color,edgecolor="#405364",lw=.65,**kw))


def dim(ax,a,b,label,offset=0):
    ax.annotate("",a,b,arrowprops={"arrowstyle":"<->","lw":.8,"color":C["ink"]})
    ax.text((a[0]+b[0])/2+offset,(a[1]+b[1])/2+15,label,ha="center",va="bottom",fontsize=9,color=C["ink"],rotation=90 if a[0]==b[0] else 0)


def frame(ax,side=False):
    for xx in (0,860): rect(ax,xx,40,40,820,C["frame"])
    rect(ax,0,0,900,40,C["frame"])
    rect(ax,0,860,900,80 if side else 40,C["frame"])
    if side:
        ax.plot([60,840],[80,840],color=C["rail"],lw=1)
        ax.plot([60,840],[840,80],color=C["rail"],lw=1)
    rect(ax,150 if side else 200,120,500,500,"none",linestyle="--",linewidth=1.2)
    ax.text(400 if side else 450,300,"TCP 工作范围\n500 × 500",ha="center",color=C["work"],fontsize=11)
    ax.set_aspect("equal");ax.set_xlim(-120,1030);ax.set_ylim(-140,1850);ax.axis("off")
    dim(ax,(0,-60),(900,-60),"机架 900")
    dim(ax,(940,120),(940,620),"Z 行程 500",offset=35)
    ax.axhline(1761,xmin=.1,xmax=.9,color="#8596a2",ls="--",lw=.7)
    ax.text(100,1780,"Z 全收回最高 1761",fontsize=9,color="#526d7d")


def main():
    out=ROOT/"drawings";out.mkdir(exist_ok=True)
    fig=plt.figure(figsize=(16,11.3),facecolor="white")
    fig.text(.04,.95,"迷你龙门架 V2.1｜总布置与接口",fontsize=23,color=C["ink"],weight="bold")
    fig.text(.04,.914,"三轴有效行程 500 × 500 × 500 mm · 固定夹爪接口 · 夹爪与物料暂按 1 kg",fontsize=12,color="#536e7f")
    a=fig.add_axes([.04,.20,.32,.68]); frame(a)
    a.set_title("正视包络图  /  X–Z",fontsize=12,color=C["ink"])
    rect(a,40,1000,820,80,C["frame"])
    for xx in (20,880):rect(a,xx-17,940,34,40,C["rail"])
    rect(a,370,860,160,240,C["plate"])
    rect(a,410,560,80,800,C["frame"])
    for xx in (420,480):a.plot([xx,xx],[600,1340],color=C["rail"],lw=2)
    rect(a,429,1440,42,71,C["motor"])
    rect(a,423,1385,54,30,"#ce6a58")
    rect(a,410,554,80,6,C["plate"])
    rect(a,420,438,4,116,C["plate"])
    rect(a,476,438,4,116,C["plate"])
    rect(a,415,430,70,8,C["work"])
    rect(a,140,160,160,170,"#478a70")
    rect(a,390,960,120,8,C["plate"])
    rect(a,420,370,60,60,C["motor"])
    rect(a,410,810,80,800,"none",linestyle="--")
    dim(a,(200,90),(700,90),"X 行程 500")
    a.annotate("双侧机械同步 Y 轴",(810,980),(580,1240),fontsize=9,arrowprops={"arrowstyle":"-","color":C["ink"]})
    a.annotate("上伸式 Z 滑枕",(410,1250),(80,1540),fontsize=9,arrowprops={"arrowstyle":"-","color":C["ink"]})
    a.annotate("轻量固定夹爪座",(420,480),(60,700),fontsize=9,arrowprops={"arrowstyle":"-","color":C["ink"]})

    b=fig.add_axes([.37,.20,.32,.68]);frame(b,True)
    b.set_title("侧视包络图  /  Y–Z",fontsize=12,color=C["ink"])
    rect(b,40,940,820,15,C["rail"])
    rect(b,405,968,190,12,C["plate"])
    rect(b,480,1000,40,80,C["frame"])
    rect(b,440,860,12,240,C["plate"])
    rect(b,370,560,40,800,C["frame"])
    b.plot([426,426],[565,1405],color=C["rail"],lw=2)
    rect(b,405,1440,42,71,C["motor"])
    rect(b,399,1385,54,30,"#ce6a58")
    rect(b,370,554,60,6,C["plate"])
    rect(b,380,438,40,116,C["plate"])
    rect(b,365,430,70,8,C["work"])
    rect(b,-70,950,95,8,C["plate"])
    rect(b,-50,925,40,25,C["motor"])
    rect(b,380,370,40,60,C["motor"])
    rect(b,900,180,68,180,"#478a70")
    dim(b,(150,90),(650,90),"Y 行程 500")
    b.annotate("控制板与接线预留",(940,300),(620,720),fontsize=9,arrowprops={"arrowstyle":"-","color":C["ink"]})
    b.annotate("固定螺母 / 随动丝杆",(426,980),(590,1260),fontsize=9,arrowprops={"arrowstyle":"-","color":C["ink"]})
    b.annotate("独立失电制动器",(426,1390),(570,1540),fontsize=9,arrowprops={"arrowstyle":"-","color":C["ink"]})

    t=fig.add_axes([.72,.24,.25,.64]);t.axis("off")
    lines=[("结构基准",True),
        ("机架：900 × 900 mm；背部预留至 968 mm",False),
        ("最高点：1761 mm；另留走线检修空间",False),
        ("4040 框架 + 4080 上梁与滑枕",False),
        ("Y：双 820 导轨 / 双带 / 30T / 3:1",False),
        ("X：双 700 导轨 / 单带 / 20T / 2:1",False),
        ("Z：双 740 导轨 / 1605 丝杆",False),
        ("XYZ 速度暂定：150 / 100 / 25 mm/s",False),
        ("轻量末端与计算板",True),
        ("取消旋转电机，使用开窗固定支架",False),
        ("电机：31×31孔距 / Ø22止口 / Ø5轴",False),
        ("机身按60mm + 11mm驱动板预留",False),
        ("Pi4B：58×49；Nano：86×58",False),
        ("同一托板，两组孔，每次只装一块",False),
        ("控制与接口",True),
        ("首选 RM A 板，预留替换托板",False),
        ("CAN1：张大头 42 V2.1 × 3",False),
        ("前上方120×100可拆摄像头面板",False),
        ("RA6M5 候选需核对型号及收发器",False),
        ("4颗M3固定；用户打印相机适配板",False)]
    yy=1
    for s,bold in lines:
        t.text(0,yy,s,fontsize=11 if bold else 9.4,weight="bold" if bold else "normal",color=C["ink"] if bold else "#526d7d",va="top")
        yy-=.058 if bold else .044
    fig.text(.04,.14,"设计边界",fontsize=12,color="#a85830",weight="bold")
    fig.text(.04,.109,"这是结构布局评审模型，采购件为简化包络。没有完成全装配干涉排除、紧固件详设、供应商孔位、公差链或实物承载验收。",fontsize=10,color="#526d7d")
    fig.text(.04,.080,"下料前需确认负载和电机力矩曲线，并冻结导轨、丝杆支承、皮带轮、制动器及夹爪型号。参数与证据记录在同目录 design.json / validation。",fontsize=10,color="#526d7d")
    fig.text(.04,.038,"单位 mm｜图示非加工比例｜V2.1｜2026-10-15",fontsize=10,color="#526d7d")
    fig.savefig(out/"layout.svg",facecolor="white")
    fig.savefig(out/"layout.png",dpi=160,facecolor="white")
    plt.close(fig)


if __name__=="__main__":main()
