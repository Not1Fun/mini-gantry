"""核验张紧滑台全调节范围，含螺钉、垫圈和肩轴。"""
import json
from itertools import combinations
from pathlib import Path
from belt_fabrication import tensioners
from build import bounds
from audit_geometry import overlap


def main():
    parts=tensioners((450,400,370));rows=[]
    for prefix in ('x_tension_0','y_tension_0','y_tension_1'):
        selected=[p for p in parts if p['name'].startswith(prefix)]
        for shift in (-4,0,4):
            moved=[];direction=(1,0,0) if prefix.startswith('x') else (0,-1,0)
            for p in selected:
                suffix=p['name'][len(prefix):]
                movable=suffix in ('_fork','_idler','_axle','_axle_washer','_axle_nut') or suffix.startswith('_spacer_') or suffix=='_push_M6'
                delta=tuple(v*shift for v in direction) if movable else (0,0,0)
                moved.append(dict(p,shape=p['shape'].translate(delta)))
            boxes={p['name']:bounds(p['shape']) for p in moved};collisions=[]
            for a,b in combinations(moved,2):
                if not overlap(boxes[a['name']],boxes[b['name']]):continue
                v=a['shape'].intersect(b['shape']).Volume()
                if v>.05:collisions.append(dict(a=a['name'],b=b['name'],volume_mm3=round(v,3)))
            rows.append(dict(module=prefix,adjustment_mm=shift,collisions=collisions))
            print(prefix,shift,len(collisions),flush=True)
            for c in collisions:print(c,flush=True)
    result=dict(status='PASS_TENSIONER_RANGE' if not any(r['collisions'] for r in rows) else 'FAIL',checks=rows,
                scope='仅几何全调节范围；张力由实际皮带及张力计设定，不得把几何行程当作允许伸长')
    (Path(__file__).parent/'validation'/'tensioners.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
