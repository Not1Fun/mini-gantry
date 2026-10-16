"""由BOM和发布校核结果生成工艺、采购与装配册。"""
from pathlib import Path
import json
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parent
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
S=getSampleStyleSheet()
S.add(ParagraphStyle(name='CN',fontName='STSong-Light',fontSize=9,leading=14,spaceAfter=6))
S.add(ParagraphStyle(name='CNtitle',parent=S['CN'],fontSize=20,leading=26,spaceAfter=18))
S.add(ParagraphStyle(name='CNhead',parent=S['CN'],fontSize=13,leading=18,spaceBefore=12,spaceAfter=8))
S.add(ParagraphStyle(name='CNsmall',parent=S['CN'],fontSize=7.5,leading=11))


def main():
    bom=json.loads((ROOT/'bom.json').read_text(encoding='utf-8'));m=json.loads((ROOT/'manufacturing.json').read_text(encoding='utf-8'))
    e=json.loads((ROOT/'validation/engineering_v3.json').read_text(encoding='utf-8'));r=json.loads((ROOT/'release.json').read_text(encoding='utf-8'))
    cut=json.loads((ROOT/'cutlist.json').read_text(encoding='utf-8'));catalog=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'));story=[]
    def p(text,style='CN'):story.append(Paragraph(escape(str(text)).replace('\n','<br/>'),S[style]))
    def h(text):p(text,'CNhead')
    def table(rows,widths):
        cells=[[Paragraph(escape(str(c)),S['CNsmall']) for c in row] for row in rows]
        t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef1')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#b7c4cb')),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.append(t);story.append(Spacer(1,10))
    p('迷你龙门架\nV3 样机加工与装配册','CNtitle')
    p('版本 '+r['revision']+' | '+r['status'])
    p('设计输入：XYZ有效行程500 x 500 x 500 mm；夹爪与物料合计1 kg；张大头42 V2、本体60 mm预留；取消DM云台电机。')
    p('机架外廓900 x 940 mm；最大高度约1821 mm。外置限位、相机、线缆与控制托板超出机架外廓。计算板只安装Pi4B或Nano其中一块。')
    p('负载边界：1 kg是夹爪、转接件及工件的合计。水平偏心限制为TCP轴线两侧各50 mm；负载重心在夹爪安装法兰下方不超过100 mm。超出边界须重新校核。')
    p('文件优先级：同版release.json确定放行状态；manufacturing.pdf给出尺寸、公差与工艺；同号STEP定义名义轮廓；SLDPRT/SLDASM用于检查装配；SW导入零件局部原点可能不同，孔坐标以同号STEP为准。不得将V2.3文件混入V3加工。')
    p('公差与线程：3D采购件不画内部滚珠，所有螺纹以公称孔径/轴径简化。有效牙深、配合、公差和齿形以图纸及原厂型号为准。严禁把简化光圆轮廓当作同步带齿形制造。')
    h('加工路线')
    p('铝制连接件、轴承座、止挡与电机L座采用6061-T6整体CNC。V3电机L座采用8 mm一体铣削件，无需薄钢板焊接；这使安装面垂直度和轴孔位置更容易控制。轴件车削、键槽铣削，热处理先于轴承颈精加工。1 mm钢感应片激光切割后清孔、去毛刺并镀锌。聚氨酯缓冲垫切割后加工沉孔。摄像头适配面板由用户按相机自行打印。')
    p('通用尺寸：<=300 mm为+/-0.1，>300 mm为+/-0.2；CNC孔位置+/-0.05；未注通孔直径+0.10/0；未注Ra3.2、安装面Ra1.6、轴承颈Ra0.8。明确标注的公差优先。内螺纹6H、外螺纹6g。所有锐边去毛刺C0.3。')
    p('6061无色阳极5~10 um，配合孔、基准安装面及螺纹遮蔽。钢轴发黑薄油，轴承颈不得带厚涂层。外购轴承保持洁净，压装时只对相应配合圈施力。')
    h('型材定长切割')
    table([['型材','长度mm','数量']]+[[x['profile'],x['length_mm'],x['quantity']] for x in cut['items']],[230,140,130])
    p(cut['end_work'])
    p('使用MISUMI HFS8-4040/HFS8-4080系列、槽口10 mm、HNTT8螺母。8系列表示螺栓系列，不能替换成槽口8 mm而不改接口。型材CAD为外形与等效内部包络，实际槽型必须使用原厂截面。')
    story.append(PageBreak());h('装配顺序与调整')
    steps=[
      '框架：按切割表备料。预先滑入T螺母，连接底框、四柱、顶框和后附件横梁。安装角连接板，先轻锁，调整两侧框与底框对角线差不大于0.5 mm。再安装交叉拉带，消除松弛后锁紧，禁止把薄拉带当压杆或过度拉紧使型材弯曲。',
      '导轨基面：装Y导轨8 mm基板和X导轨6 mm基板，用直尺/千分表检查贴合与直线。两Y导轨平行偏差目标不大于0.05/500，端板能够全程手推；以实际滑块预压和厂家安装要求复核，不用电机强拉不平行轨道。',
      '桥架：先用M8x14将垫高块连接横梁底槽，再将垫高块用四M6连接端板。装Y四滑块与端板，保持左右端板齐平。M8x14可由16 mm螺钉修短、倒角后使用。',
      'X滑座：先固定两根X导轨和四个HGH15滑块，再从滑座前面沉孔装M4x16。Z隔板/滑块的M4x25从背面安装，应在螺母托架和跨梁板挡住工具前完成。沉孔内0.8 mm垫圈不得遗漏。',
      'Z滑枕：装导轨背板、两根760 mm导轨、上下轴支承、丝杆及由丝杆厂家预装的SFNU01605-4螺母。螺母不得直接滑出丝杆。下6000ZZ外圈保留0.30 mm轴向浮动；上BK12按厂家说明锁止。螺母六M5先装到一体托架，再把托架连接X滑座。',
      'Z驱动：先把电机、顶板、两侧板和下鞍座预组；装MIKI失电制动器及原配D8轮毂，3-V固定孔对准底座，不拆原厂3-S装配螺钉。制动器轮毂和联轴器不得靠顶紧形成轴向预载。联轴器两轴各插入12 mm，按NBK 1.5 N.m锁紧；电机D轴平面避开夹缝。',
      'XY输入模块：输入轴、608内圈隔套、两轴承和端盖先装壳体。前轴承定位、后外圈可浮动。双薄螺母消隙后对锁，不额外预压深沟轴承。装键、输入轮与端部压板，再通过联轴器连接电机；同轴找正后固定侧板。电机不直接承受减速带预紧力。',
      '输出轴：X轴使用双6001和12 mm轴，主带轮28T，减速40T；Y采用两端6202与16 mm同步轴，主轮36T、减速60T。右6202外圈保留0.6 mm浮动。平键传扭，轴端锁紧件限制窜动，轴承应能无卡滞转动。',
      '皮带：X减速带100S3M192、Y减速带100S3M246，静态单跨预紧40+/-4 N。三条主开口带单跨预紧60+/-5 N；X用HTBO-S3M150-490（1470 mm），Y每条HTBO-S3M150-590（1770 mm）。两端各夹21 mm/7齿，X中央间断54 mm、Y中央间断60 mm。张紧行程+/-4 mm用于装配与弹性伸长，不能据此任意改切长。',
      '夹板与张紧：原厂齿板与带齿完全啮合后均匀锁紧四M3；夹板压板浮动，不使用固定高度把皮带夹成硬止口。X轴外置M6拉紧螺钉、Y轴M6顶丝调到需要位置后，锁紧滑台四M6；顶丝不承担运行剪力。左右Y带张力相同；先保持桥架方正，再用Y夹座的+/-3 mm长槽消除齿相误差，同侧前后两座同向等量调整后锁紧。禁止靠扭转贯通轴强迫桥架方正。',
      '止挡与限位：先装缓冲垫和钢感应片，再装6只OMRON常闭传感器。钢靶到传感面间隙1+/-0.2 mm，不能用铝板代替钢靶。用手推和低速点动校准触发位置，不用理论感应边缘代替实测。',
      '附件：摄像头底座先装耳板，再装俯角载架与2 mm摩擦隔套，调整角度后对称锁紧。可拆面板统一120x100、孔距100x80，中央区域由用户适配相机。计算托板只能装一套4个M2.5x10支柱；Pi4B用58x49孔组，Nano官方载板用86x58孔组。',
      '走线：Y端板外侧和X滑座侧边已预留M4接口；Z滑枕侧槽可装线夹。拖链支架可通过这些接口连接。运动线束要独立应力释放，弯曲半径按实际线缆/拖链要求；接插件与运动件全程不得受拉。电源、急停和控制器接线需在首次上电前完成专门检查。'
    ]
    for i,t in enumerate(steps,1):p(str(i)+'. '+t)
    p('末端固定座先在台面装好上板、侧板和圆盘，再用两M8从后下方连接滑枕端面，避免背板挡住上板沉头螺钉的工具路径。Z电机架两侧30x70检修孔用于制动器轮毂和联轴器紧固。')
    h('初装紧固基准')
    p('下列是洁净干燥8.8级螺钉的样机初装目标，原厂件紧固要求优先；不得对滑块、制动器或联轴器擅自套用统一扭矩。M8型材连接12 N.m，M6型材/滑台5 N.m，M5铝连接2 N.m，M4滑块连接1.5 N.m，M4铝导轨基板0.8 N.m，M3铝连接0.5 N.m。皮带夹板先用0.35 N.m交叉均匀锁紧，再以防滑移试验确认。所有复核点做见证线。')
    h('行程、止挡与运动换算')
    table([['轴','工作TCP范围','限位名义点','缓冲垫首次接触','金属极限','mm/电机转'],['X','200~700','195 / 705','185 / 715','180 / 720','42'],['Y','150~650','145 / 655','135 / 665','130 / 670','36'],['Z','120~620','118 / 632','115 / 635','110 / 640','5']],[30,94,94,100,90,92])
    p('正常轨迹在工作边界内完成减速。缓冲垫设计压缩不超过1 mm，螺钉头低于垫面2 mm；金属极限是基座几何边界，不是允许撞击位置。传感器与止挡之间的余程不增加额定500 mm行程。初次调试不超过X/Y 100 mm/s、Z 20 mm/s；断电、失步、传感器断线均不属于正常连续运行方式。')
    h('1 kg设计校核')
    table([['轴','估计移动质量kg','目标速度mm/s','转速rpm','所需电机曲线力矩N.m（含2倍系数）']]+[[a,f"{v['moving_mass_estimate_kg']:.2f}",v['speed_mm_s'],f"{v['motor_rpm']:.1f}",v['required_motor_torque_Nm_with_factor_2']] for a,v in e['axes'].items()],[30,100,100,90,180])
    p('X梁简支估算重力挠度约'+f"{e['frame']['bridge_gravity_deflection_mm']:.3f}"+' mm；这不包含接头和皮带柔度，不能作为定位精度承诺。D8输入轴采用42CrMo调质，要求材料证明Rp0.2>=650 MPa、Rm>=850 MPa。设计径向载荷100 N、过悬25.5 mm、缺口系数2.2，估算弯曲应力'+f"{e['shafts']['input_D8']['bending_with_notch_factor_2_2_MPa']:.1f}"+' MPa。')
    p('Z制动器静态保持力矩1 N.m，估计重力回驱力矩'+f"{e['Z_brake']['gravity_backdrive_torque_Nm']:.3f}"+' N.m。目录单次制动能量上限2 J。按总闭合延迟40 ms估算，跌落与动能约'+f"{e['Z_brake']['computed_energy_J']:.2f}"+' J；40 ms必须包含控制延迟、线圈消磁和机械动作，不能当成已测值。')
    h('加工验收与上电验收分开')
    p('加工件按图检尺寸、孔位、牙深、轴颈配合、导轨安装面平面度、毛刺与表面处理。按采购代码核对原厂件。完成这些即可进入样机装配，不需要先做不存在样机的载荷测试。')
    p('装配后：先手动检查全行程和止挡；逐轴低速找零，断线检查常闭限位；测试急停与Z断电保持，并实测制动闭合时间；再空载、0.5 kg、1 kg分级试验，检查滑移、松动、温升与重复定位。实际电机型号/电压/电流下的力矩曲线尚未获得，额定1 kg运行能力必须通过该试验确认。')
    story.append(PageBreak());h('自制件下单索引')
    table([['编号','名称','材料','数量']]+[[v['part_number'],v['representative'],v['manufacturing']['material'],v['quantity']] for v in m['parts']],[60,285,110,45])
    story.append(PageBreak());h('采购与紧固件清单')
    p('原厂总成内含件合并采购，避免重复买制动轮毂、BK12锁紧件或联轴器零件。电子板、相机、夹爪由用户自备；本表不代替控制接线设计。不得用外形相似的其他系列替换后直接加工。')
    table([['规格/加工要求','数量']]+[[v['spec'],v['quantity']] for v in bom['procurement']],[455,45])
    h('尺寸来源')
    seen=set()
    for name,v in catalog.items():
        url=v.get('source')
        if url and url not in seen:p(name+': '+url,'CNsmall');seen.add(url)
    p('电机安装尺寸来自用户提供的张大头商品尺寸图：31x31四M3、D22x2止口、D5轴、22.5轴伸，60本体+11驱动板空间。Nano孔组对应官方开发载板外形，其他载板通过转接板适配。','CNsmall')
    dest=ROOT/'drawings'/'assembly_and_procurement.pdf'
    def footer(c,doc):c.setFont('STSong-Light',8);c.drawString(36,22,r['revision']+' | '+r['status']);c.drawRightString(A4[0]-36,22,str(doc.page))
    SimpleDocTemplate(str(dest),pagesize=A4,rightMargin=36,leftMargin=36,topMargin=38,bottomMargin=38).build(story,onFirstPage=footer,onLaterPages=footer)
    print(dest,flush=True)


if __name__=='__main__':main()
