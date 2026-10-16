"""检查Y双带相位微调时夹座、螺钉与相邻结构的净空。"""
from pathlib import Path
import json
from build import make_model,bounds
from audit_geometry import overlap,important


def main():
    parts=make_model((450,400,370));rows=[]
    for tcp_x in (180,720):
        for offset in (-3,3):
            active=[];others=[]
            for p in parts:
                dx=tcp_x-450 if 'X' in p['motion'] else 0
                moving=p['name'].startswith('y_clamp_') and '_M5_' not in p['name']
                item=dict(p,shape=p['shape'].translate((dx,offset if moving else 0,0)))
                (active if moving else others).append(item)
            boxes={p['name']:bounds(p['shape']) for p in others};hits=[]
            for a in active:
                aa=bounds(a['shape'])
                for b in others:
                    if not (important(b) or b['role']=='fastener'):continue
                    if not overlap(aa,boxes[b['name']]):continue
                    vol=a['shape'].intersect(b['shape']).Volume()
                    if vol>.05:hits.append(dict(a=a['name'],b=b['name'],volume_mm3=round(vol,3)))
            rows.append(dict(tcp_x=tcp_x,offset_mm=offset,collisions=hits));print(tcp_x,offset,len(hits),flush=True)
            for hit in hits:print(hit,flush=True)
    result=dict(status='PASS_Y_PHASE_ADJUSTMENT' if not any(r['collisions'] for r in rows) else 'FAIL',checks=rows,
                instruction='同侧前后夹座同向等量调整，保持桥架方正和两条带相同张力，然后锁紧M5；相位调节不改变额定行程')
    (Path(__file__).parent/'validation/belt_phase.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
