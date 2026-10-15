"""由当前几何生成Z传动局部图与轴向尺寸链。"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from build import ROOT,CFG,COLORS,make_model,box
from z_drive import MOTOR_FACE,COUPLER_TOP,COUPLER_BOTTOM,SCREW_TIP


def main():
    x,y,z=CFG['assumptions']['illustration_pose_mm'];cy=y+26
    fig=plt.figure(figsize=(17,10),facecolor='#f7f9fa')
    fig.text(.045,.945,'Z轴传动接口细化 / V2.2',fontsize=24,weight='bold',color='#16384a')
    fig.text(.045,.900,'机架与500mm行程保持；电机台加高30mm；尺寸单位mm，相对夹爪TCP标高。',fontsize=12,color='#577180')
    ax=fig.add_axes([.015,.12,.49,.73],projection='3d',computed_zorder=True)
    ax.set_facecolor('#f7f9fa')
    clip=box((x-55,cy-70,z+980),(110,120,200))
    selected=('z_motor_','z_coupling_','z_brake_','z_screw_','z_top_','z_base_','z_saddle_','motor_Z','z_ram_')
    light=np.array([-.4,-.5,.8]);light/=np.linalg.norm(light)
    all_triangles=[];all_colors=[]
    for p in make_model((x,y,z)):
        if not p['name'].startswith(selected):continue
        shape=p['shape'].intersect(clip)
        if shape.Volume()<.001:continue
        vertices,faces=shape.tessellate(.3,.18)
        vv=np.array([v.toTuple() for v in vertices])-[x,cy,z]
        triangles=vv[np.array(faces)]
        normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        lengths=np.linalg.norm(normals,axis=1);lengths[lengths<1e-12]=1
        normals/=lengths[:,None]
        shade=.60+.40*np.clip(normals@light,0,1)
        rgb=np.array(to_rgb(COLORS[p['kind']]))
        all_triangles.extend(triangles);all_colors.extend(shade[:,None]*rgb)
    ax.add_collection3d(Poly3DCollection(all_triangles,facecolors=all_colors,edgecolors='none',zsort='average'))
    ax.set(xlim=(-55,55),ylim=(-65,50),zlim=(980,1180));ax.set_box_aspect((110,115,200))
    ax.view_init(17,55);ax.set_axis_off()
    ax.set_title('局部装配：联轴器与支承分开显示',fontsize=13,color='#16384a')
    a=fig.add_axes([.55,.20,.40,.64]);a.set_xlim(-55,130);a.set_ylim(978,1180);a.axis('off')
    def rect(x0,z0,w,h,color):a.add_patch(Rectangle((x0,z0),w,h,fc=color,ec='#344a5c',lw=.7))
    def note(text,pt,target):a.annotate(text,pt,target,fontsize=10,va='center',color='#16384a',arrowprops={'arrowstyle':'-','lw':.7,'color':'#78909c'})
    rect(-21,MOTOR_FACE,42,60,COLORS['motor']);rect(-19.5,MOTOR_FACE+60,39,11,'#647784')
    for xx in (-40,12):rect(xx,MOTOR_FACE-7,28,7,COLORS['motor_mount'])
    for xx in (-40,30):rect(xx,996,10,MOTOR_FACE-7-996,COLORS['motor_mount'])
    rect(-11,MOTOR_FACE-2,22,2,COLORS['screw'])
    rect(-2.5,MOTOR_FACE-22.5,5,20.5,COLORS['screw'])
    for xx in (-12.5,2.5):rect(xx,COUPLER_TOP-12,10,12,COLORS['drive'])
    for xx in (-12.5,6):rect(xx,COUPLER_BOTTOM+12,6.5,10,COLORS['safety'])
    for xx in (-12.5,5):rect(xx,COUPLER_BOTTOM,7.5,12,COLORS['drive'])
    rect(-6,985,12,38,COLORS['screw']);rect(-5,1023,10,SCREW_TIP-1023,COLORS['screw'])
    for xx in (-27,5):rect(xx,1023,22,30,'#e1b1a8')
    for xx in (-11,6):rect(xx,1015,5,6,'#a7b3bd')
    for xx in (-30,6):rect(xx,985,24,30,'#b6d2dc')
    note('60mm本体 + 11mm尾板',(21,1140),(51,1150))
    note('电机安装面 1100\n原位置上移30',(21,1100),(51,1112))
    note('顶板间隙3.5；止口间隙8.5',(12.5,COUPLER_TOP),(51,1092))
    note('D25 × 34 联轴器\nD5 / D10，两端各插入12',(12.5,1073),(51,1071))
    note('制动器至联轴器间隙2.5',(27,1053),(51,1050))
    note('制动器30高预留\n真实壳体和反力固定待定',(27,1035),(51,1030))
    note('锁紧螺母与制动器间隙2',(11,1021),(51,1008))
    note('上支承D12轴颈\n轴承组与轴肩待厂家图纸',(30,992),(51,985))
    a.plot([0,0],[980,1180],ls='--',lw=.6,color='#78909c')
    fig.text(.55,.155,'装配：先锁紧丝杆支承，再装制动器；两半联轴器先分别固定到轴，最后装电机顶板。',fontsize=9.8,color='#16384a')
    fig.text(.045,.080,'尺寸依据：NBK MJC-25CS系列目录。上图为接口包络，未表达联轴器齿爪、夹紧缝和轴承内部结构。',fontsize=10,color='#577180')
    fig.text(.045,.045,'本轮通过标称局部干涉与工具通道检查；X/Y减速组件、Z制动器反力固定和采购件公差仍待细化。',fontsize=10,color='#a45c30')
    for ext in ('png','svg'):fig.savefig(ROOT/'drawings'/('z_drive_stack.'+ext),dpi=170,facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__=='__main__':main()
