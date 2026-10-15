"""共用孔板、可拆相机面板和电机法兰接口图。"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle,FancyBboxPatch
from pathlib import Path
from accessories import holes

ROOT=Path(__file__).resolve().parent
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'],'axes.unicode_minus':False,'svg.fonttype':'none'})
INK='#16384a';PI='#337c75';NANO='#b27a2d'


def dimension(ax,a,b,label):
    ax.annotate('',a,b,arrowprops={'arrowstyle':'<->','lw':.75,'color':INK})
    ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+2,label,ha='center',va='bottom',fontsize=9,color=INK,
            rotation=90 if a[0]==b[0] else 0)


def base(ax,title,xlim,ylim):
    ax.set_aspect('equal');ax.set_xlim(*xlim);ax.set_ylim(*ylim);ax.axis('off');ax.set_title(title,fontsize=14,color=INK,pad=16)


def main():
    fig,axs=plt.subplots(1,3,figsize=(16,8),facecolor='white')
    fig.subplots_adjust(left=.04,right=.97,top=.80,bottom=.20,wspace=.28)
    fig.text(.04,.94,'V2.1 安装接口｜尺寸单位 mm',fontsize=24,color=INK,weight='bold')
    fig.text(.04,.884,'Nano / Raspberry Pi 4B 二选一 · 摄像头独立可拆 · 电机接口按用户提供尺寸图',fontsize=12,color='#5a7281')
    a,b,c=axs
    base(a,'计算板共用托板  160×170×3',(-15,185),(-20,183))
    a.add_patch(Rectangle((0,0),160,170,facecolor='#f2f5f7',edgecolor=INK,lw=1))
    a.add_patch(Rectangle((56,88),48,34,facecolor='white',edgecolor=INK,lw=.7))
    for key,color in [('pi4b',PI),('jetson_nano',NANO)]:
        pts=holes(key)
        for x,y in pts:a.add_patch(Circle((x,y),1.45,fc='white',ec=color,lw=1.7))
        px=sorted(set(p[0] for p in pts));py=sorted(set(p[1] for p in pts))
        a.add_patch(Rectangle((px[0],py[0]),px[1]-px[0],py[1]-py[0],fill=False,ec=color,ls='--',lw=.7))
    for x in (30,130):a.add_patch(FancyBboxPatch((x-13,17.25),26,5.5,boxstyle='round,pad=0,rounding_size=2.75',fc='white',ec=INK,lw=.7))
    a.text(80,149,'Nano：86×58 / 4-Ø2.9',ha='center',fontsize=10,color=NANO)
    a.text(80,138,'Pi 4B：58×49 / 4-Ø2.9',ha='center',fontsize=10,color=PI)
    a.text(80,62,'孔组中心 (80,105)\n仅装对应的4只M2.5支柱\n板底间隔10',ha='center',va='center',fontsize=10,color=INK)
    a.text(80,32,'两处26×5.5机架固定长孔',ha='center',fontsize=9,color='#5a7281')
    dimension(a,(0,-9),(160,-9),'160');dimension(a,(173,0),(173,170),'170')
    base(b,'摄像头可拆面板  120×100×3',(-13,140),(-22,122))
    b.add_patch(Rectangle((0,0),120,100,facecolor='#f2f5f7',edgecolor=INK,lw=1))
    for x in (10,110):
        for y in (10,90):b.add_patch(Circle((x,y),1.7,fc='white',ec=INK,lw=1))
    b.add_patch(Rectangle((20,20),80,60,fill=False,ec='#b27a2d',ls='--'))
    b.text(60,52,'中央80×60自定义区\n用户打印相机适配板\n外部四孔接口统一',ha='center',va='center',fontsize=10,color=INK)
    dimension(b,(10,108),(110,108),'孔距100');dimension(b,(132,10),(132,90),'80')
    b.text(60,-16,'4-Ø3.4，4颗M3拆装；初始俯角30°',ha='center',fontsize=10,color=INK)
    base(c,'42电机安装接口',(-10,53),(-20,59))
    c.add_patch(Rectangle((0,0),42,42,fc='#f2f5f7',ec=INK,lw=1))
    for x in (5.5,36.5):
        for y in (5.5,36.5):c.add_patch(Circle((x,y),1.5,fc='white',ec=INK,lw=1))
    c.add_patch(Circle((21,21),11,fill=False,ec=INK,lw=1))
    c.add_patch(Circle((21,21),2.5,fill=False,ec=INK,lw=1))
    dimension(c,(5.5,47),(36.5,47),'31±0.1');dimension(c,(48,5.5),(48,36.5),'31±0.1')
    c.text(21,-7,'4-M3×0.5，孔深≥4\n止口Ø22，高2；默认Ø5轴',ha='center',va='center',fontsize=10,color=INK)
    c.text(21,-17,'机身按60 + 驱动板11预留',ha='center',fontsize=10,color=INK)
    fig.text(.04,.13,'安装说明：闲置板卡孔组不装支柱；不能把两块计算板叠装。Nano第三方载板和Orin Nano须另核孔位。',fontsize=11,color='#a25b2d')
    fig.text(.04,.083,'机身按用户确认的60mm预留；相机适配板由用户打印。面板拆装后应检查标定；本图不替代最终加工公差和供应商实物核验。',fontsize=10,color='#5a7281')
    fig.savefig(ROOT/'drawings/mounting_interfaces.svg')
    fig.savefig(ROOT/'drawings/mounting_interfaces.png',dpi=160)
    plt.close(fig)


if __name__=='__main__':main()
