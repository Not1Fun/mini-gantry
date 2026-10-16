"""当前模型生成的X/Y减速级局部视图，三角面统一排序以改善遮挡显示。"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from build import ROOT,CFG,COLORS,make_model,box
from xy_drive import CENTERS


def draw(ax,parts,limits,origin,elev,azim):
    triangles=[];colors=[];clip=box(tuple(v[0] for v in limits),tuple(v[1]-v[0] for v in limits))
    light=np.array([-.3,-.5,.8]);light/=np.linalg.norm(light)
    for p in parts:
        s=p['shape'].intersect(clip)
        if s.Volume()<.01:continue
        vv,ff=s.tessellate(.5,.22)
        arr=(np.array([v.toTuple() for v in vv])-origin)[np.array(ff)]
        normals=np.cross(arr[:,1]-arr[:,0],arr[:,2]-arr[:,0]);length=np.linalg.norm(normals,axis=1);length[length<1e-12]=1
        shade=.62+.38*np.clip((normals/length[:,None])@light,0,1)
        triangles.extend(arr);colors.extend(shade[:,None]*np.array(to_rgb(COLORS[p['kind']])))
    mesh=Poly3DCollection(triangles,facecolors=colors,edgecolors='none',zsort='average',rasterized=True)
    ax.add_collection3d(mesh)
    ranges=[(a-origin[i],b-origin[i]) for i,(a,b) in enumerate(limits)]
    ax.set(xlim=ranges[0],ylim=ranges[1],zlim=ranges[2]);ax.set_box_aspect([b-a for a,b in ranges])
    ax.view_init(elev,azim);ax.set_axis_off();ax.set_facecolor('#f7f9fa')


def main():
    x,y,z=CFG['assumptions']['illustration_pose_mm'];yc=y+100;parts=make_model((x,y,z))
    fig=plt.figure(figsize=(17,11),facecolor='#f7f9fa')
    fig.text(.045,.95,'X / Y 减速传动细化 / V2.3',fontsize=25,color='#16384a',weight='bold')
    fig.text(.045,.91,'20齿电机轮 + 闭环S3M同步带 + 独立输出轴支承；原整体占位块已移除。',fontsize=12,color='#577180')
    a=fig.add_axes([.02,.28,.47,.56],projection='3d');b=fig.add_axes([.51,.28,.47,.56],projection='3d')
    xp=('x_reduction_','x_output_','x_motor_','x_mount_','motor_X','x_pulley_0','x_pulley_mount_0','x_pulley_axle_0','x_main_pulley_')
    yp=('y_reduction_','y_motor_','y_mount_','motor_Y','y_rear_support_0','y_rear_cover_0','y_rear_bearing_0','y_rear_spacer_0','y_rear_collar_0','y_pulley_0_1','y_sync_shaft','y_main_pulley_set_screw_0')
    xs=[p for p in parts if p['name'].startswith(xp)]
    ys=[p for p in parts if p['name'].startswith(yp)]
    for src,scene,clip in [('bridge_4080',xs,box((40,yc-20,1060),(110,40,20))),('top_cross_1',ys,box((40,860,880),(190,40,20)))]:
        q=dict(next(p for p in parts if p['name']==src));q['shape']=q['shape'].intersect(clip);scene.append(q)
    draw(a,xs,((40,145),(yc-35,yc+140),(1060,1195)),np.array([90,yc,1100]),23,-55)
    draw(b,ys,((40,230),(835,925),(880,1090)),np.array([130,880,984]),20,-135)
    a.set_title(f'X：20T → 40T / 2:1 / 中心距 {CENTERS["X"]:.3f}',fontsize=14,color='#16384a')
    b.set_title(f'Y：20T → 60T / 3:1 / 中心距 {CENTERS["Y"]:.3f}',fontsize=14,color='#16384a')
    fig.text(.055,.23,'192S3M × 6宽；双608输出座；主带轮与减速轮沿轴向分开',fontsize=11,color='#16384a')
    fig.text(.535,.23,'246S3M × 6宽；后梁6202支承；D16贯通轴两端加工D15',fontsize=11,color='#16384a')
    fig.text(.055,.185,'两轴电机均用3.5×9.5竖槽，安装/张紧可调±3mm；X右侧加筋板开窗避让主带。',fontsize=11,color='#16384a')
    fig.text(.055,.140,'灰色：轴/轴环/隔套；金色：带轮；黑色：闭环带；橙色：电机座；蓝色：轴承座及端盖。',fontsize=10,color='#577180')
    fig.text(.055,.095,'通过节线长度、标称局部干涉、长孔端点与径向工具通道检查。图中轴承、轮毂、齿槽和螺纹采用简化表达。',fontsize=10,color='#577180')
    fig.text(.055,.055,'尚待：供应商CAD、轴承配合/轴向公差、带宽与预紧选型、紧定锁紧能力、主长带端部和防护。当前非加工放行图。',fontsize=10,color='#a45c30')
    for ext in ('png','svg'):fig.savefig(ROOT/'drawings'/('xy_reduction.'+ext),dpi=170,facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__=='__main__':main()
