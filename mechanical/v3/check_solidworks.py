"""独立核验原生总装的质心位置及引用是否自包含。"""
from pathlib import Path
import json
import pythoncom
from win32com.client import dynamic
import cadquery as cq
from build_solidworks import ROOT,OUT,PREFIX,ASSEMBLY_NAME,prop,doubles,open_native,standalone
from build import make_model,CFG


def main():
    pythoncom.CoInitialize();sw=dynamic.Dispatch('SldWorks.Application')
    pose=CFG['assumptions']['illustration_pose_mm'];original=make_model(pose)
    expected={p['name']:p['shape'] for p in original if standalone(p,pose)}
    for group in ('fixed','Y','XY','XYZ'):
        expected['module_'+group]=cq.Compound.makeCompound([p['shape'] for p in original if p['motion']==group and not standalone(p,pose)])
    doc,opened=open_native(sw,OUT/ASSEMBLY_NAME,2)
    mu=prop(sw,'GetMathUtility');mu._FlagAsMethod('CreatePoint')
    rows=[]
    for comp in doc.GetComponents(False):
        file=Path(prop(comp,'GetPathName'));part=prop(comp,'GetModelDoc2')
        pp=[b.GetMassProperties(1.0) for b in part.GetBodies2(0,False)]
        total=sum(v[3] for v in pp)
        center=[sum(v[k]*v[3] for v in pp)/total for k in range(3)]
        point=mu.CreatePoint(doubles(center)).MultiplyTransform(prop(comp,'Transform2'))
        actual=[v*1000 for v in prop(point,'ArrayData')]
        expected_shape=expected[file.stem.removeprefix(PREFIX)];target=expected_shape.Center().toTuple()
        error=max(abs(a-b) for a,b in zip(actual,target))
        assert error<.01,(file.name,actual,target)
        volume_error=abs(total*1e9-expected_shape.Volume())
        assert volume_error<max(.5,expected_shape.Volume()*1e-7),('volume mismatch',file.name,volume_error)
        deps=sw.GetDocumentDependencies2(str(file),True,True,False) or []
        assert not deps,('part external dependencies',file.name,deps)
        rows.append({'part':file.name,'bodies':len(pp),'centroid_error_mm':error,'volume_error_mm3':volume_error,'external_dependencies':0})
    expected_bodies=sum(len(p['shape'].Solids()) for p in original)
    assert len(rows)==len(expected) and sum(r['bodies'] for r in rows)==expected_bodies
    result={'status':'PASS_NATIVE_PLACEMENT_AND_SELF_CONTAINED_PARTS','reopen':opened,'parts':rows,
            'assembly_component_count':len(rows),'solid_body_count':expected_bodies,'max_centroid_error_mm':max(r['centroid_error_mm'] for r in rows),
            'scope':'原生文件位置与依赖核验；不代替机械公差、运动配合和实体样机验证'}
    (ROOT/'validation/solidworks_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(result['status'],result['max_centroid_error_mm'],flush=True)


if __name__=='__main__':main()
