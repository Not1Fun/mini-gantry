"""SolidWorks 2024：原生板件草图/拉伸、采购件导入实体、固定评审位姿总装。

仅创建/关闭本脚本自己的文档，不关闭用户其他文档。需要 Windows、pywin32 和已安装的 SolidWorks。
"""
from pathlib import Path
import json
import math
import os
import hashlib
import gc
import shutil
import pythoncom
import win32com.client
from win32com.client import dynamic
import cadquery as cq
from build import ROOT, CFG, COLORS, make_model, bounds
from accessories import holes

OUT=ROOT/'SolidWorks'
IMPORT=ROOT/'cad'/'sw_import'
TEMPLATES=Path(os.environ.get('PROGRAMDATA',r'C:\ProgramData'))/'SOLIDWORKS'/'SOLIDWORKS 2024'/'templates'
SW_SESSION=None


def prop(obj,name):
    v=getattr(obj,name)
    return v() if callable(v) and not hasattr(v,'_oleobj_') else v


def doubles(values):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,values)


def null():
    return win32com.client.VARIANT(pythoncom.VT_DISPATCH,None)


def save(doc,path):
    ext=doc.Extension
    ok,e,w=ext._oleobj_.InvokeTypes(ext._oleobj_.GetIDsOfNames('SaveAs'),0,1,(11,0),
        ((8,1),(3,1),(3,1),(9,1),(16387,2),(16387,2)),str(path),0,1,None)
    if not ok or e or not path.exists():raise RuntimeError(('SaveAs',path.name,ok,e,w))
    return {'errors':e,'warnings':w,'bytes':path.stat().st_size}


def open_native(sw,path,kind):
    doc,e,w=sw._oleobj_.InvokeTypes(sw._oleobj_.GetIDsOfNames('OpenDoc6'),0,1,(9,0),
        ((8,1),(3,1),(3,1),(8,1),(16387,2),(16387,2)),str(path),kind,1,'')
    if doc is None or e:raise RuntimeError(('OpenDoc6',path.name,e,w))
    return dynamic.Dispatch(doc),{'errors':e,'warnings':w}


def activate(sw,title):
    doc,e=sw._oleobj_.InvokeTypes(sw._oleobj_.GetIDsOfNames('ActivateDoc3'),0,1,(9,0),
        ((8,1),(11,1),(3,1),(16387,2)),title,False,0)
    if doc is None or e:raise RuntimeError(('ActivateDoc3',title,e))


def native_profile(sw,name,rectangles,circles,slots,thickness):
    doc=sw.NewDocument(str(TEMPLATES/'gb_part.prtdot'),0,0,0)
    if doc is None:raise RuntimeError('part template unavailable')
    f=prop(doc,'FirstFeature')
    while f is not None and prop(f,'GetTypeName2')!='RefPlane':f=prop(f,'GetNextFeature')
    if f is None or not f.Select2(False,0):raise RuntimeError('reference plane')
    sm=doc.SketchManager;sm.InsertSketch(True);sm.AddToDB=True
    for x,y,w,h in rectangles:
        pts=[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
        for a,b in zip(pts,pts[1:]+pts[:1]):sm.CreateLine(a[0]/1000,a[1]/1000,0,b[0]/1000,b[1]/1000,0)
    for x,y,r in circles:sm.CreateCircleByRadius(x/1000,y/1000,0,r/1000)
    for x,y,length,width in slots:
        radius=width/2;left=x-(length-width)/2;right=x+(length-width)/2
        sm.CreateLine(left/1000,(y+radius)/1000,0,right/1000,(y+radius)/1000,0)
        sm.CreateArc(right/1000,y/1000,0,right/1000,(y+radius)/1000,0,right/1000,(y-radius)/1000,0,-1)
        sm.CreateLine(right/1000,(y-radius)/1000,0,left/1000,(y-radius)/1000,0)
        sm.CreateArc(left/1000,y/1000,0,left/1000,(y-radius)/1000,0,left/1000,(y+radius)/1000,0,-1)
    sm.AddToDB=False;sm.InsertSketch(True)
    sketch=doc.FeatureByPositionReverse(0);sketch.Name='外形与孔位_'+name
    doc.ClearSelection2(True);sketch.Select2(False,0)
    feature=doc.FeatureManager.FeatureExtrusion2(True,False,False,0,0,thickness/1000,0,
        False,False,False,False,0,0,False,False,False,False,True,True,True,0,0,False)
    if feature is None:raise RuntimeError(('Extrusion',name))
    feature.Name='板厚_'+str(thickness)+'mm'
    return doc


def feature_spec(name,pose):
    x,y,z=pose;yc=y+100
    identity=[1,0,0,0,1,0,0,0,1]
    if name=='compute_combo_plate':
        cs=[(u,v,1.45) for k in ('pi4b','jetson_nano') for u,v in holes(k)]
        return [(0,0,160,170),(56,88,48,34)],cs,[(30,20,26,5.5),(130,20,26,5.5)],3,[1,0,0,0,0,1,0,-1,0],[140,903,160]
    if name=='camera_removable_panel':
        panel=name=='camera_removable_panel';r=[(0,0,120,100)]
        if not panel:r.append((15,15,90,70))
        cs=[(u,v,1.7) for u in (10,110) for v in (10,90)]
        c=math.cos(math.pi/6);s=.5;dz=5 if panel else 0
        return r,cs,[],3 if panel else 5,[1,0,0,0,c,s,0,-s,c],[390,-25-50*c-dz*s,980-50*s+dz*c]
    if name=='z_motor_mount':
        cs=[(40,36,12)]+[(40+a,36+b,1.75) for a in (-15.5,15.5) for b in (-15.5,15.5)]
        return [(0,0,80,60)],cs,[],7,identity,[x-40,yc-110,z+1063]
    if name=='gripper_adapter':
        cs=[(35,35,35),(35,35,4)]+[(35+25*math.cos(a*math.pi/2),35+25*math.sin(a*math.pi/2),2.25) for a in range(4)]
        return [],cs,[],8,identity,[x-35,y-35,z+60]
    return None


def main():
    global SW_SESSION
    pythoncom.CoInitialize()
    try:sw=dynamic.Dispatch(pythoncom.GetActiveObject('SldWorks.Application'))
    except Exception:sw=dynamic.Dispatch('SldWorks.Application')
    SW_SESSION=sw
    sw.Visible=True;sw.UserControl=True;sw.CommandInProgress=True
    OUT.mkdir(exist_ok=True);IMPORT.mkdir(parents=True,exist_ok=True)
    old_path=ROOT/'validation'/'solidworks.json'
    old=json.loads(old_path.read_text(encoding='utf-8')) if old_path.exists() else {}
    cached={p['name']:p for p in old.get('parts',[])}
    for own in (prop(sw,'GetDocuments') or []):
        path=prop(own,'GetPathName')
        if path and (Path(path).parent==OUT or Path(path).parent==IMPORT):sw.CloseDoc(prop(own,'GetTitle'))
    report={'status':'BUILDING','solidworks_revision':str(prop(sw,'RevisionNumber')),'parts':[],
            'assembly_constraints':'全部组件固定在评审位姿；未建立可驱动运动配合',
            'model_scope':'4个关键接口板采用原生草图拉伸；其余按固定机架及XYZ运动组导入多实体模组；参数化再生成源为build.py'}
    report_path=ROOT/'validation'/'solidworks.json'
    def checkpoint():report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    pose=CFG['assumptions']['illustration_pose_mm'];original=make_model(pose)
    parts=[p for p in original if feature_spec(p['name'],pose)]
    for group in ('fixed','Y','XY','XYZ'):
        members=[p for p in original if p['motion']==group and not feature_spec(p['name'],pose)]
        parts.append({'name':'module_'+group,'shape':cq.Compound.makeCompound([p['shape'] for p in members]),
                      'kind':'frame' if group=='fixed' else 'plate','spec':group+' 运动模组 / 简化实体',
                      'members':[p['name'] for p in members]})
    report['source_component_count']=len(original)
    for i,p in enumerate(parts):
        name=p['name'];path=OUT/(name+'.SLDPRT');spec=feature_spec(name,pose)
        vv,ff=p['shape'].tessellate(.2,.15)
        triangles=sorted(tuple(sorted(tuple(round(q,6) for q in vv[j].toTuple()) for j in face)) for face in ff)
        shape_hash=hashlib.sha256(json.dumps(triangles,separators=(',',':')).encode()).hexdigest()
        expected_method='native_sketch_extrusion' if spec else 'imported_envelope'
        if path.exists() and name in cached and cached[name].get('geometry_sha256')==shape_hash and cached[name]['method']==expected_method:
            report['parts'].append(cached[name]);checkpoint();continue
        if spec:
            rects,circles,slots,t,rotation,xyz=spec
            doc=native_profile(sw,name,rects,circles,slots,t)
            method='native_sketch_extrusion'
        else:
            bb=bounds(p['shape']);xyz=bb[:3];rotation=[1,0,0,0,1,0,0,0,1]
            local=p['shape'].translate(tuple(-v for v in xyz))
            src=IMPORT/(name+'.step');cq.exporters.export(local,str(src))
            data=sw.GetImportFileData(str(src))
            if data is not None:data.MapConfigurationData=False
            obj,e=sw._oleobj_.InvokeTypes(sw._oleobj_.GetIDsOfNames('LoadFile4'),0,1,(9,0),
                ((8,1),(8,1),(9,1),(16387,2)),str(src),'r',data)
            if obj is None or e:raise RuntimeError(('LoadFile4',name,e))
            doc=dynamic.Dispatch(obj);method='imported_envelope'
            if prop(doc,'GetType')==2:
                imported_title=prop(doc,'GetTitle')
                previous=sw.GetUserPreferenceIntegerValue(201)
                try:
                    sw.SetUserPreferenceIntegerValue(201,1)
                    save(doc,path)
                finally:sw.SetUserPreferenceIntegerValue(201,previous)
                sw.CloseDoc(imported_title)
                doc,_=open_native(sw,path,1)
        color=COLORS[p['kind']].lstrip('#')
        rgb=[int(color[i:i+2],16)/255 for i in (0,2,4)]
        doc.MaterialPropertyValues=doubles(rgb+[.5,.75,.25,.15,0,0])
        pm=doc.Extension.CustomPropertyManager('')
        pm.Add3('DesignStatus',30,'V2_REVIEW_ONLY_NOT_RELEASED',1)
        pm.Add3('FeatureMethod',30,method,1)
        pm.Add3('PartRole',30,p['spec'],1)
        bodies=doc.GetBodies2(0,False) or []
        volume=sum(b.GetMassProperties(1.0)[3]*1e9 for b in bodies)
        expected=p['shape'].Volume()
        if abs(volume-expected)>max(.5,expected*1e-6):raise RuntimeError(('volume',name,volume,expected))
        doc.ForceRebuild3(False)
        rec=save(doc,path)
        rec.update(name=name,file=path.name,method=method,bodies=len(bodies),volume_mm3=volume,
                   expected_volume_mm3=expected,rotation=rotation,xyz_mm=xyz,geometry_sha256=shape_hash,
                   members=p.get('members',[name]))
        report['parts'].append(rec);checkpoint()
        sw.CloseDoc(prop(doc,'GetTitle'))
        doc=None;bodies=None;gc.collect()
        print('PART',i+1,'/',len(parts),name,flush=True)
    doc=sw.NewDocument(str(TEMPLATES/'gb_assembly.asmdot'),0,0,0)
    if doc is None:raise RuntimeError('assembly template unavailable')
    mu=prop(sw,'GetMathUtility');mu._FlagAsMethod('CreateTransform')
    view=doc.ActiveView;view.EnableGraphicsUpdate=False
    for i,r in enumerate(report['parts']):
        path=OUT/r['file'];source,opened=open_native(sw,path,1);title=prop(source,'GetTitle')
        activate(sw,prop(doc,'GetTitle'))
        comp=doc.AddComponent5(str(path),0,'',False,'',0,0,0)
        if comp is None:raise RuntimeError(('AddComponent5',path.name))
        if not comp.Select4(False,null(),False):raise RuntimeError('Select component')
        prop(doc,'UnfixComponent')
        values=r['rotation']+[v/1000 for v in r['xyz_mm']]+[1,0,0,0]
        comp.Transform2=mu.CreateTransform(doubles(values))
        actual=list(prop(comp,'Transform2').ArrayData)
        if max(abs(a-b) for a,b in zip(actual[:13],values[:13]))>1e-8:raise RuntimeError(('transform',r['name']))
        comp.Select4(False,null(),False);prop(doc,'FixComponent');comp.Name2=r['name']
        doc.ClearSelection2(True);sw.CloseDoc(title)
        if (i+1)%20==0:print('ASSEMBLY',i+1,flush=True)
    view.EnableGraphicsUpdate=True;doc.ForceRebuild3(False)
    doc.ShowNamedView2('*Isometric',7);prop(doc,'ViewZoomtofit2')
    final=OUT/'mini_gantry_v2.SLDASM';report['save']=save(doc,final)
    sw.CloseDoc(prop(doc,'GetTitle'))
    opened,state=open_native(sw,final,2)
    comps=opened.GetComponents(False) or []
    if len(comps)!=len(parts):raise RuntimeError(('component count',len(comps),len(parts)))
    for c in comps:
        path=Path(prop(c,'GetPathName')).resolve()
        if path.parent!=OUT.resolve() or not path.exists():raise RuntimeError(('reference',path.name))
        if prop(c,'GetModelDoc2') is None:raise RuntimeError(('unresolved',path.name))
    report.update(status='PASS_NATIVE_SAVE_REOPEN',component_count=len(comps),reopen=state,
                  native_feature_parts=sum(p['method']=='native_sketch_extrusion' for p in report['parts']),
                  body_count=sum(p['bodies'] for p in report['parts']))
    checkpoint()
    scratch=ROOT.parents[2]/'sw-v2-intermediates';scratch.mkdir(exist_ok=True)
    keep={p['file'] for p in report['parts']}
    for path in OUT.glob('*.SLDPRT'):
        if path.name not in keep:
            destination=scratch/path.name
            assert path.resolve().parent==OUT.resolve() and destination.resolve().parent==scratch.resolve()
            if destination.exists():destination=destination.with_name('previous_'+destination.name)
            shutil.move(str(path),str(destination))
    for path in IMPORT.glob('*.step'):
        if path.stem not in {p['name'] for p in parts if p['name'].startswith('module_')}:
            destination=scratch/(path.stem+'_import.step')
            if not destination.exists():shutil.move(str(path),str(destination))
    sw.Visible=True;sw.UserControl=True
    opened.ShowNamedView2('*Isometric',7);prop(opened,'ViewZoomtofit2')
    print('PASS_NATIVE_SAVE_REOPEN',len(comps),flush=True)


if __name__=='__main__':
    try:main()
    finally:
        if SW_SESSION is not None:
            try:SW_SESSION.CommandInProgress=False
            except Exception:pass
