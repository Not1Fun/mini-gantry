"""加工包文件、零件索引和独立检查结果的一致性关卡。"""
from pathlib import Path
import hashlib,json
import fitz,ezdxf

ROOT=Path(__file__).resolve().parent


def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))


def main():
    m=read('manufacturing.json');bom=read('bom.json');g=read('validation/geometry_v3.json');n=read('validation/solidworks.json');a=read('validation/solidworks_audit.json')
    t=read('validation/tensioners.json');phase=read('validation/belt_phase.json');step=read('validation/step_roundtrip.json');pdf=read('validation/pdf_qa.json')
    assert g['status']=='PASS_SAMPLED_RIGID_CLEARANCE' and len(g['poses'])==27 and len(g['overtravel_checks'])==8
    assert not g['hardware_collisions'] and t['status']=='PASS_TENSIONER_RANGE' and phase['status']=='PASS_Y_PHASE_ADJUSTMENT'
    assert n['status']=='PASS_NATIVE_SAVE_REOPEN' and n.get('forced_rebuild_ok') and n.get('post_open_rebuild_ok')
    assert a['status']=='PASS_NATIVE_PLACEMENT_AND_SELF_CONTAINED_PARTS'
    assert step['valid'] and step['source_solids']==step['imported_solids']==a['solid_body_count']==n['body_count']==len(bom['items'])
    assert n['component_count']==a['assembly_component_count']==len(n['parts'])
    by_name={p['name']:p for p in bom['items']};members=[]
    for p in m['parts']:
        assert p['quantity']==len(p['members']) and (ROOT/p['file']).is_file()
        for name in p['members']:assert by_name[name]['part_number']==p['part_number'];members.append(name)
    assert len(members)==len(set(members))==sum(p['role']=='fabricated' for p in bom['items'])
    assert {p.name for p in (ROOT/'cad/parts').glob('*.step')}=={Path(p['file']).name for p in m['parts']}
    expected_dxf={p['part_number']+'.dxf' for p in m['parts'] if p['manufacturing']['type'] in ('plate','round_plate','camera_panel_blank')}
    assert {p.name for p in (ROOT/'cad/dxf').glob('*.dxf')}==expected_dxf
    for file in (ROOT/'cad/dxf').glob('*.dxf'):assert ezdxf.readfile(file).units==4
    assert pdf['status']=='PASS_PDF_TEXT_BOUNDS' and not any(p['text_bounds_errors'] for p in pdf['documents'])
    with fitz.open(ROOT/'drawings/manufacturing.pdf') as document:
        text='\n'.join(p.get_text() for p in document)
        assert all(row['part_number'] in text for row in m['parts'])
        drawing_pages=len(document)
    native_files={r['file'] for r in n['parts']}|{'mini_gantry_v3.SLDASM'}
    assert {p.name for p in (ROOT/'SolidWorksV3').glob('*.SLD*') if not p.name.startswith('~$')}==native_files
    assert (ROOT/'cad/camera_adapter_blank.stl').is_file()
    # 排除可重新生成的转换缓存、Python缓存及报告本身。
    inventory=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or any(x in p.parts for x in ('__pycache__','sw_import','drawing_cache')) or p.name.startswith('~$') or p.name=='release_audit.json':continue
        inventory.append(dict(file=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    result=dict(status='PASS_FABRICATION_PACKAGE_CONSISTENCY',revision=read('release.json')['revision'],
                manufactured_unique_parts=len(m['parts']),manufactured_instances=len(members),native_components=n['component_count'],solids=n['body_count'],
                working_positions_checked=27,overtravel_positions_checked=8,tensioner_positions_checked=len(t['checks']),belt_phase_positions_checked=len(phase['checks']),
                machining_pdf_pages=drawing_pages,dxf_files=len(expected_dxf),native_centroid_max_error_mm=a['max_centroid_error_mm'],
                native_open_warning=n.get('reopen'),native_rebuild_after_open=n['post_open_rebuild_ok'],files=inventory,
                scope='数字样机加工资料与装配几何验证；未进行实机带载、制动时序、急停回路或定位性能验收')
    (ROOT/'validation/release_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
