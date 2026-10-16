"""零件坐标加工图、采购/切割表；PDF与DXF均来自发布特征表。"""
from pathlib import Path
import argparse,hashlib,json,math,shutil
import cadquery as cq
import ezdxf
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.pagesizes import A3,landscape

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'drawings';CACHE=ROOT/'cad'/'drawing_cache'
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'));FONT='STSong-Light';PAGE=landscape(A3)
LABELS={'size_mm':'外形尺寸','steps_mm':'轴段[起点,终点,直径]','bores_mm':'内孔[起点,终点,直径]',
        'center_bore':'中心孔','floor':'横板','back':'立板','window':'开口','service_window':'检修口','inner_radius':'内角R',
        'keyways':'键槽','threads':'螺纹段','mount_holes':'安装孔','face_slots':'立面长槽','shaft_hole':'轴孔',
        'bearing_pockets':'轴承孔','axis_local':'轴线基准点','axis_direction':'轴线方向','through_bore':'中心通孔',
        'foot':'底脚','tower':'轴承座体','mounting_holes':'底脚安装孔','face_holes':'端盖孔',
        'boss_diameter':'凸台直径','boss_length':'凸台长度','plate_thickness':'板厚','features':'加工特征',
        'blocks':'毛坯并体[x,y,z,dx,dy,dz]','stepped_bores':'阶梯孔','face_pockets':'正面铣槽',
        'hex_socket':'内六角[对边,深]','axial_range':'轴向范围','base_code':'采购基件','bore':'精加工内孔',
        'keyway_width':'键槽宽','hub_key_depth':'轮毂键槽径向深','radial_thread':'径向紧定螺纹','radial_thread_t':'径向孔轴向位置',
        'fork_inner_width':'双耳内距','fork_outer_width':'双耳外距','ear_u_range':'耳部U范围','ear_v_ranges':'耳部V范围',
        'ear_height':'耳部高度','axle_local':'轴孔局部基准','axle_diameter':'轴孔直径','push_wall':'调节承压凸台',
        'total_length':'总长','sections_mm':'轴段','threaded_working_section':'丝杆工作段','fixed_end':'固定端',
        'floating_end':'浮动端','motor_extension':'上端轴伸','plate_box':'板体','pivot_bosses':'俯角轴凸台','diameter':'外径'}


def num(v):return f'{v:.4f}'.rstrip('0').rstrip('.') if isinstance(v,float) else str(v)


def wrapped(text,width,font=9):
    lines=[];line=''
    for ch in str(text):
        if ch=='\n':lines.append(line);line='';continue
        if pdfmetrics.stringWidth(line+ch,FONT,font)>width:lines.append(line);line=ch
        else:line+=ch
    if line:lines.append(line)
    return lines


def feature_lines(m):
    out=['坐标单位mm。零件STEP保留图示局部原点；U=X、V=Y、W=Z。','正面=局部W最大面，背面=局部W最小面；边孔按方向向量钻入。']
    if m.get('size_mm'):out.append('毛坯/外包络：'+' x '.join(num(v) for v in m['size_mm']))
    if m.get('outline'):out.append('外轮廓(U,V)：'+json.dumps(m['outline'],ensure_ascii=False))
    for i,h in enumerate(m.get('holes',[]),1):
        u=h.get('u',h.get('x'));v=h.get('v',h.get('y'));kind=h.get('kind','through');d=h['diameter']
        line=f'H{i:02d}: ({num(u)}, {num(v)})  '+(f'{kind}-6H 有效牙深{num(h["depth"])}' if kind.startswith('M') else f'D{num(d)} '+('通孔' if kind=='through' else '深'+num(h.get('depth'))))
        if h.get('side')=='bottom':line+='，从背面'
        if h.get('counterbore'):line+='，沉孔D'+num(h['counterbore'][0])+' 深'+num(h['counterbore'][1])
        if h.get('countersink'):line+='，沉头D'+num(h['countersink'][0])+' /'+num(h['countersink'][1])+'度'
        if h.get('head_recess'):line+='，头部下沉'+num(h['head_recess'])+'（D6.5直壁后接沉头）'
        if h.get('note'):line+='；'+h['note']
        out.append(line)
    for i,h in enumerate(m.get('edge_holes',[]),1):
        line=f'E{i:02d}: P='+str(h['point'])+' 方向='+str(h['direction'])+'  '+(h['thread']+'-6H' if h.get('thread') else 'D'+num(h['diameter']))+' 深'+num(h['depth'])
        if h.get('counterbore'):line+=' 沉孔'+str(h['counterbore'])
        if h.get('countersink'):line+=' 沉头'+str(h['countersink'])
        if h.get('note'):line+='；'+h['note']
        out.append(line)
    for i,row in enumerate(m.get('slots',[]),1):out.append(f'S{i:02d}: 中心({num(row[0])},{num(row[1])}) 总长{num(row[2])} x 宽{num(row[3])}，角度{num(row[4])}度，贯穿')
    for i,row in enumerate(m.get('windows',[]),1):out.append(f'W{i:02d}: 起点({num(row[0])},{num(row[1])}) 宽{num(row[2])} x 高{num(row[3])}，贯穿')
    excluded={'type','material','size_mm','origin_mm','axes','module_placement','mirror_about_x_mm','mirror_about_z_mm','rotation_x_deg','holes','edge_holes','slots','windows','outline','notes'}
    for key,value in m.items():
        if key in excluded:continue
        if isinstance(value,list) and value and isinstance(value[0],dict):
            for i,row in enumerate(value,1):out.append(LABELS.get(key,key)+f' {i}: '+json.dumps(row,ensure_ascii=False,separators=(',',':')))
        else:out.append(LABELS.get(key,key)+': '+json.dumps(value,ensure_ascii=False,separators=(',',':')))
    out += ['工艺 '+str(i+1)+': '+note for i,note in enumerate(m.get('notes',[]))]
    out += ['通用：未注尺寸<=300为+/-0.1，>300为+/-0.2；CNC孔位+/-0.05；未注通孔+0.10/0。',
            '螺纹在STEP中以公称径简化。按6H底孔/螺纹加工，不得直接按模型大径钻孔；有效牙深为验收值。',
            '盲螺纹用底攻或螺纹铣削；工艺底孔应先核对剩余壁厚及交叉孔，薄壁处优先螺纹铣削。',
            '未注Ra3.2；安装面Ra1.6；去毛刺C0.3。阳极层不计入配合尺寸；轴承孔、螺纹与定位面遮蔽。']
    return out


def header(c,title,subtitle,page_label,status):
    W,H=PAGE;c.setFillColorRGB(.10,.17,.22);c.setFont(FONT,18);c.drawString(36,H-38,title)
    c.setFont(FONT,9);c.drawString(36,H-58,subtitle);c.setStrokeColorRGB(.2,.3,.35);c.line(36,H-70,W-36,H-70)
    c.setFont(FONT,8);c.drawString(36,25,status);c.drawRightString(W-36,25,page_label)


def vector_views(shape,key):
    CACHE.mkdir(parents=True,exist_ok=True);paths=[]
    for label,direction in [('ISO',(1,-1,1)),('TOP',(0,0,1)),('FRONT',(0,-1,0))]:
        path=CACHE/('line3_'+key[:16]+'_'+label+'.pdf')
        if not path.exists():
            svg=cq.exporters.getSVG(shape,{'width':800,'height':500,'marginLeft':25,'marginTop':25,'projectionDir':direction,
                'showAxes':False,'showHidden':True,'strokeWidth':-1,'strokeColor':(25,45,55),'hiddenColor':(170,180,185)})
            doc=fitz.open(stream=svg.encode(),filetype='svg');path.write_bytes(doc.convert_to_pdf());doc.close()
        paths.append(path)
    return paths


def dxf(row):
    m=row['manufacturing']
    if m['type'] not in ('plate','camera_panel_blank','round_plate'):return
    doc=ezdxf.new('R2010');doc.units=4;ms=doc.modelspace()
    for name,color in [('OUTLINE',7),('THROUGH',3),('TAP_PILOT',1),('REFERENCE_CBORE',4),('REFERENCE_CSK',5),('NOTES',2)]:doc.layers.new(name,dxfattribs={'color':color})
    a,b,t=m['size_mm']
    if m.get('diameter'):ms.add_circle((a/2,b/2),m['diameter']/2,dxfattribs={'layer':'OUTLINE'})
    else:ms.add_lwpolyline(m.get('outline') or [(0,0),(a,0),(a,b),(0,b)],close=True,dxfattribs={'layer':'OUTLINE'})
    for u,v,w,h in m.get('windows',[]):ms.add_lwpolyline([(u,v),(u+w,v),(u+w,v+h),(u,v+h)],close=True,dxfattribs={'layer':'OUTLINE'})
    for cx,cy,L,W,angle in m.get('slots',[]):
        aa=(L-W)/2;r=W/2;rad=math.radians(angle);pts=[]
        for u,v,bulge in [(-aa,-r,0),(aa,-r,1),(aa,r,0),(-aa,r,1)]:pts.append((cx+u*math.cos(rad)-v*math.sin(rad),cy+u*math.sin(rad)+v*math.cos(rad),bulge))
        ms.add_lwpolyline(pts,format='xyb',close=True,dxfattribs={'layer':'THROUGH'})
    pilots={2.5:2.05,3:2.5,4:3.3,5:4.2,6:5,8:6.8}
    for h in m.get('holes',[]):
        center=(h.get('u',h.get('x')),h.get('v',h.get('y')));thread=h.get('kind','').startswith('M');dd=pilots.get(h['diameter'],h['diameter']) if thread else h['diameter']
        ms.add_circle(center,dd/2,dxfattribs={'layer':'TAP_PILOT' if thread else 'THROUGH'})
        for key,layer in [('counterbore','REFERENCE_CBORE'),('countersink','REFERENCE_CSK')]:
            if h.get(key):ms.add_circle(center,h[key][0]/2,dxfattribs={'layer':layer})
    ms.add_text(row['part_number']+' - mm - SEE PDF FOR DEPTH, THREADS AND SIDE HOLES',dxfattribs={'height':3,'layer':'NOTES','insert':(0,-8)})
    dest=ROOT/'cad'/'dxf';dest.mkdir(exist_ok=True);doc.saveas(dest/(row['part_number']+'.dxf'))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int);args=ap.parse_args()
    manifest=json.loads((ROOT/'manufacturing.json').read_text(encoding='utf-8'));release=json.loads((ROOT/'release.json').read_text(encoding='utf-8'))
    OUT.mkdir(exist_ok=True);W,H=PAGE;temp=OUT/'manufacturing_text.tmp.pdf';c=canvas.Canvas(str(temp),pagesize=PAGE)
    c.setTitle('迷你龙门架 V3 零件加工图');placements=[];page=0;rows=manifest['parts'][:args.limit]
    for index,row in enumerate(rows):
        s=cq.importers.importStep(str(ROOT/row['file'])).val();assert s.isValid()
        assert abs(s.Volume()-row['volume_mm3'])<max(.05,row['volume_mm3']*1e-7),(row['part_number'],'STEP volume')
        views=vector_views(s,row['geometry_signature']);text=[]
        for line in feature_lines(row['manufacturing']):text.extend(wrapped(line,W-620,9))
        cursor=0;partpage=0
        while cursor<len(text):
            partpage+=1;header(c,row['part_number']+'  '+row['representative'],f"材料：{row['manufacturing']['material']}    数量：{row['quantity']}    单位：mm    同号STEP为名义三维数模；图示非等比例打印",f"{release['revision']} / {row['part_number']} / {partpage}",release['status'])
            if partpage==1:
                boxes=[(36,90,550,382),(36,410,282,655),(302,410,550,655)]
                for label,box_,src in zip(('轴测图','正面俯视：局部W方向','侧视：局部-V方向'),boxes,views):
                    x0,y0,x1,y1=box_;c.setStrokeColorRGB(.75,.8,.82);c.rect(x0,H-y1,x1-x0,y1-y0);c.setFont(FONT,9);c.drawString(x0,H-y0+8,label)
                    placements.append((page,box_,src))
                bb=row['local_bbox_mm'];c.setFont(FONT,9)
                c.drawString(36,H-680,'局部包络起点：'+', '.join(num(q) for q in bb[:3]))
                c.drawString(36,H-699,'局部包络终点：'+', '.join(num(q) for q in bb[3:]))
                c.drawString(36,H-718,'零件文件：'+Path(row['file']).name)
                x0=582;top=H-92;bottom=42
            else:x0=36;top=H-92;bottom=42
            if partpage>1:
                remaining=[]
                for t in text[cursor:]:remaining.extend(wrapped(t,W-72,9))
                # 原条目已按窄栏断行；续页保留逐行顺序便于追溯。
            c.setFont(FONT,9);c.setFillColorRGB(.05,.09,.12)
            yy=top
            while cursor<len(text) and yy>=bottom:
                c.drawString(x0,yy,text[cursor]);yy-=13;cursor+=1
            c.showPage();page+=1
        dxf(row)
        if (index+1)%10==0:print('DRAWINGS',index+1,'/',len(rows),flush=True)
    c.save();doc=fitz.open(temp)
    for page,rect,src in placements:
        with fitz.open(src) as view:doc[page].show_pdf_page(fitz.Rect(*rect),view,0,keep_proportion=True)
    dest=OUT/'manufacturing.pdf';doc.save(dest,garbage=4,deflate=True);doc.close();temp.unlink()
    expected={r['part_number']+'.dxf' for r in rows if r['manufacturing']['type'] in ('plate','camera_panel_blank','round_plate')}
    if not args.limit:
        scratch=ROOT.parents[2]/'v3_obsolete_exports';scratch.mkdir(exist_ok=True)
        for path in (ROOT/'cad'/'dxf').glob('*.dxf'):
            if path.name in expected:continue
            assert path.resolve().parent==(ROOT/'cad'/'dxf').resolve();target=scratch/path.name;count=0
            while target.exists():count+=1;target=scratch/(str(count)+'_'+path.name)
            assert target.resolve().parent==scratch.resolve();shutil.move(str(path),str(target))
    check=fitz.open(dest);qa=ROOT.parents[2]/'qa_v3'/'drawings';qa.mkdir(parents=True,exist_ok=True)
    for i,p in enumerate(check):p.get_pixmap(matrix=fitz.Matrix(.65,.65),alpha=False).save(qa/f'page-{i+1:03d}.png')
    (ROOT/'validation'/'drawing_export.json').write_text(json.dumps(dict(status='PDF_EXPORTED_PENDING_VISUAL_REVIEW',parts=len(rows),pages=len(check),pdf='drawings/manufacturing.pdf',qa='local rendered previews, not packaged'),ensure_ascii=False,indent=2),encoding='utf-8')
    print('PDF',len(check),'pages',flush=True)


if __name__=='__main__':main()
