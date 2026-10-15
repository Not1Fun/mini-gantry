"""电机安装局部图与孔位图。分解位姿只用于说明，不改变总装位置。"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
from build import ROOT,CFG,make_model,render,box


def main():
    x,y,z=CFG['assumptions']['illustration_pose_mm'];yc=y+100
    parts=make_model((x,y,z));by_name={p['name']:p for p in parts}
    configs=[('x',('x_motor_','x_mount_','motor_X'),(0,55,0),((25,165),(yc-45,yc+170),(1060,1215)),30,-55),
             ('y',('y_motor_','y_mount_','motor_Y'),(55,0,0),((20,310),(815,950),(880,1110)),24,-135),
             ('z',('z_motor_','z_top_','z_base_','z_saddle_','motor_Z'),(0,0,55),((x-65,x+65),(yc-165,yc-20),(z+925,z+1210)),20,-65)]
    captions={'x':'支架底部2-M5接横梁上槽；电机4-M3；原带轮从下方Ø24口避让',
              'y':'支架底部2-M5接后横梁；原贯通轴穿过Ø18避让孔',
              'z':'下鞍座→侧支板→顶板→电机；先锁电机与顶板，再装4-M4'}
    for axis,prefixes,delta,limits,elev,azim in configs:
        scene=[]
        for p in parts:
            if p['name'].startswith(prefixes):
                q=dict(p)
                if p['name'].startswith('motor_'):q['shape']=p['shape'].translate(delta)
                scene.append(q)
        if axis=='x':
            q=dict(by_name['bridge_4080']);q['shape']=q['shape'].intersect(box((40,yc-20,1060),(100,40,20)))
        elif axis=='y':
            q=dict(by_name['top_cross_1']);q['shape']=q['shape'].intersect(box((40,860,880),(160,40,20)))
        else:
            q=dict(by_name['z_ram_4080']);q['shape']=q['shape'].intersect(box((x-40,yc-130,z+930),(80,40,60)))
        q['name']=axis+'_reference_frame';scene.append(q)
        prefixes=prefixes+(q['name'],)
        render(scene,f'{axis}_motor_mount.png',elev=elev,azim=azim,zoom=limits,prefixes=prefixes,
               title=f'{axis.upper()}轴电机安装座 / V2.1',
               subtitle='分解示意：电机退开55mm以露出孔位；'+captions[axis])
    fig,axes=plt.subplots(1,3,figsize=(16,9),facecolor='white')
    fig.subplots_adjust(left=.05,right=.95,top=.80,bottom=.23,wspace=.35)
    fig.text(.05,.94,'电机装在哪里｜三个轴的固定路径',fontsize=23,weight='bold',color='#16384a')
    fig.text(.05,.885,'60mm电机本体预留；安装孔31×31；四个M3孔入电机3mm。图示为安装面投影，单位mm。',fontsize=12,color='#577180')
    a,b,c=axes
    for ax in axes:ax.set_aspect('equal');ax.axis('off')
    a.set_title('X：加筋L座 → 横梁上槽',fontsize=14);a.set_xlim(-14,94);a.set_ylim(-35,120)
    a.add_patch(Rectangle((0,0),80,102,fc='#f6eee7',ec='#9c6035'))
    for cx,cy,r in [(40,67,12),(40,17,12)]+[(40+u,67+v,1.75) for u in (-15.5,15.5) for v in (-15.5,15.5)]:a.add_patch(Circle((cx,cy),r,fc='white',ec='#243f50'))
    a.annotate('4-Ø3.5 / 31×31',(55.5,82.5),(3,111),fontsize=10,arrowprops={'arrowstyle':'-'})
    a.text(40,-10,'板厚3；底座2-Ø5.5接M5 T螺母',ha='center',fontsize=10)
    a.text(40,-23,'下面Ø24避让原输出带轮',ha='center',fontsize=10)
    b.set_title('Y：加筋L座 → 后横梁上槽',fontsize=14);b.set_xlim(-15,95);b.set_ylim(-34,194)
    b.add_patch(Rectangle((0,0),80,177,fc='#f6eee7',ec='#9c6035'))
    for cx,cy,r in [(40,141,12),(40,81,9)]+[(40+u,141+v,1.75) for u in (-15.5,15.5) for v in (-15.5,15.5)]:b.add_patch(Circle((cx,cy),r,fc='white',ec='#243f50'))
    b.text(40,110,'31×31 / 4-Ø3.5',ha='center',fontsize=10)
    b.text(40,55,'Ø18原贯通轴避让',ha='center',fontsize=10)
    b.text(40,-13,'板厚3；底座2-M5 T螺母固定',ha='center',fontsize=10)
    c.set_title('Z：下鞍座 → 侧支板 → 顶板',fontsize=14);c.set_xlim(-10,90);c.set_ylim(-40,95)
    c.add_patch(Rectangle((0,0),80,60,fc='#e9f0f4',ec='#243f50'))
    for cx,cy,r in [(40,36,12)]+[(40+u,36+v,1.75) for u in (-15.5,15.5) for v in (-15.5,15.5)]:c.add_patch(Circle((cx,cy),r,fc='white',ec='#243f50'))
    for cx in (5,75):
        for cy in (7,48):c.add_patch(Circle((cx,cy),2.25,fc='white',ec='#bd7743',lw=1.7))
    c.text(40,78,'橙圈：4-Ø4.5，M4固定顶板',ha='center',fontsize=10,color='#9c6035')
    c.text(40,-12,'顶板7厚；电机用4-M3×10',ha='center',fontsize=10)
    c.text(40,-27,'下鞍座用4-M5接滑枕前槽',ha='center',fontsize=10)
    fig.text(.05,.15,'装配顺序：先将电机固定到安装面，再固定支架并装传动件；Z下部沉头螺钉须在装上滑枕前锁紧。',fontsize=11,color='#16384a')
    fig.text(.05,.105,'X/Y电机及带轮轴线、减速比保持不变。采购传动件、焊缝、公差和型材T螺母仍需核对；本版不是加工放行图。',fontsize=10,color='#a45c30')
    fig.savefig(ROOT/'drawings/motor_mounts.png',dpi=160)
    fig.savefig(ROOT/'drawings/motor_mounts.svg')
    plt.close(fig)


if __name__=='__main__':main()
