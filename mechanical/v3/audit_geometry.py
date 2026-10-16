"""静态实体与多姿态干涉核验；报告明确排除采购内部和螺纹配合。"""
from pathlib import Path
from itertools import product
from collections import Counter
import argparse,json
from build import make_model,CFG,bounds
from belt_fabrication import main_belts

ROOT=Path(__file__).resolve().parent


def important(p):
    return p['role'] in ('fabricated','cut_profile') or p['kind'] in ('motor','rail','block','drive','safety','gripper')


def overlap(a,b):return all(min(a[k+3],b[k+3])-max(a[k],b[k])>.002 for k in range(3))


def scan(parts,skip_same=False):
    ps=[p for p in parts if important(p)];bbs=[bounds(p['shape']) for p in ps];result=[]
    for i,a in enumerate(ps):
        for j in range(i+1,len(ps)):
            b=ps[j]
            if skip_same and a['motion']==b['motion']:continue
            if not overlap(bbs[i],bbs[j]):continue
            # 采购机内包络与用户负载仅用于外部净空，不比较其组成包络。
            if a['name'].startswith('camera_') and b['name'].startswith('camera_') and ('ENVELOPE' in a['name'] or 'ENVELOPE' in b['name']):continue
            volume=a['shape'].intersect(b['shape']).Volume()
            if volume>.05:result.append(dict(a=a['name'],b=b['name'],volume_mm3=round(volume,3)))
    return result


def hardware_scan(parts):
    receivers=[p for p in parts if p['role']=='fabricated'];boxes={p['name']:bounds(p['shape']) for p in receivers};out=[]
    for a in parts:
        if a['role']!='fastener':continue
        aa=bounds(a['shape'])
        for b in receivers:
            if not overlap(aa,boxes[b['name']]):continue
            vol=a['shape'].intersect(b['shape']).Volume()
            if vol>.1:out.append(dict(fastener=a['name'],receiver=b['name'],volume_mm3=round(vol,3)))
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--corners',action='store_true');ap.add_argument('--hardware',action='store_true');ap.add_argument('--grid',action='store_true');ap.add_argument('--overtravel',action='store_true');args=ap.parse_args()
    reference=CFG['assumptions']['illustration_pose_mm'];parts=make_model(reference)
    report=dict(status='IN_PROGRESS',part_count=len(parts),invalid=[p['name'] for p in parts if not p['shape'].isValid()],
                duplicate_names=[n for n,c in Counter(p['name'] for p in parts).items() if c>1],poses=[],
                scope='对结构加工件、型材外形和采购安装外形做布尔交集；排除螺纹、标准紧固件和带的弹性/齿啮合；不是运动配合仿真或实机测试')
    folder=ROOT/'validation';folder.mkdir(exist_ok=True)
    def save(): (folder/'geometry_v3.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    collisions=scan(parts);report['poses'].append(dict(tcp=reference,collisions=collisions));save()
    print('CENTER',len(parts),'collisions',len(collisions),flush=True)
    for c in collisions:print(c,flush=True)
    if args.hardware:
        report['hardware_collisions']=hardware_scan(parts);save();print('HARDWARE',len(report['hardware_collisions']),flush=True)
        for c in report['hardware_collisions']:print(c,flush=True)
    if args.corners or args.grid:
        spans=list(zip(CFG['assumptions']['tcp_min_mm'],CFG['assumptions']['tcp_max_mm']))
        positions=product(*[(a,(a+b)/2,b) if args.grid else (a,b) for a,b in spans])
        for tcp in positions:
            if list(tcp)==reference:continue
            moved=[]
            for p in parts:
                delta=tuple(tcp[i]-reference[i] if 'XYZ'[i] in p['motion'] and p['motion']!='fixed' else 0 for i in range(3))
                moved.append(dict(p,shape=p['shape'].translate(delta)))
            collisions=scan(moved,skip_same=True);report['poses'].append(dict(tcp=tcp,collisions=collisions));save()
            print('POSE',tcp,'collisions',len(collisions),flush=True)
            for c in collisions:print(c,flush=True)
    if args.overtravel:
        report['overtravel_checks']=[]
        for tcp in product((180,720),(130,670),(110,640)):
            moved=[]
            for p in parts:
                delta=tuple(tcp[i]-reference[i] if 'XYZ'[i] in p['motion'] and p['motion']!='fixed' else 0 for i in range(3))
                moved.append(dict(p,shape=p['shape'].translate(delta)))
            raw=scan(moved,skip_same=True);unexpected=[];contacts=[]
            for c in raw:
                names=(c['a'],c['b'])
                intended=(any(n.startswith('X_bumper_') for n in names) and 'x_z_carrier' in names) or (any(n.startswith('Y_bumper_') for n in names) and any(n.startswith('y_end_plate_') for n in names)) or (any(n.startswith('Z_bumper_') for n in names) and any(n.startswith('Z_striker_') for n in names))
                (contacts if intended else unexpected).append(c)
            report['overtravel_checks'].append(dict(tcp=tcp,designed_buffer_compression_contacts=contacts,unexpected_collisions=unexpected))
            save();print('OVERTRAVEL',tcp,'unexpected',len(unexpected),flush=True)
            for c in unexpected:print(c,flush=True)
        report['overtravel_scope']='金属基座几何极限的结构核验；只排除指定缓冲垫压缩接触与标准紧固件，不表示允许撞击或实际可用行程'
    report['status']='PASS_SAMPLED_RIGID_CLEARANCE' if not report['invalid'] and not report['duplicate_names'] and not report.get('hardware_collisions') and not any(p['collisions'] for p in report['poses']) and not any(p['unexpected_collisions'] for p in report.get('overtravel_checks',[])) else 'FAIL'
    save();print(report['status'],flush=True)


if __name__=='__main__':main()
