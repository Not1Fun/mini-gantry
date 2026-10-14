"""检查不同运动组间的实体交叠；不是完整装配/公差检查。"""
from itertools import product
import json
from build import make_model, bounds, ROOT, CFG


def overlap(a,b):
    return all(min(a[k+3],b[k+3])-max(a[k],b[k])>1e-4 for k in range(3))


def expected_fit(a,b):
    pair=(a,b)
    fits=[("y_rail_","y_block_"),("x_rail_","x_block_"),("z_rail_","z_block_"),
          ("y_belt_","y_belt_clamp_"),("x_belt_","x_belt_clamp")]
    return any((a.startswith(p) and b.startswith(q)) or (b.startswith(p) and a.startswith(q)) for p,q in fits)


def main():
    poses=list(product(*zip(CFG["assumptions"]["tcp_min_mm"],CFG["assumptions"]["tcp_max_mm"])))
    poses.append(tuple(CFG["assumptions"]["illustration_pose_mm"]))
    collisions=[]; checked=0; excluded=0
    for pose in poses:
        parts=make_model(pose)
        bb=[bounds(p["shape"]) for p in parts]
        for i,a in enumerate(parts):
            for j in range(i+1,len(parts)):
                b=parts[j]
                if a["motion"]==b["motion"] or not overlap(bb[i],bb[j]):continue
                if expected_fit(a["name"],b["name"]):excluded+=1;continue
                checked+=1
                volume=a["shape"].intersect(b["shape"]).Volume()
                if volume>0.1:
                    collisions.append({"pose_mm":pose,"a":a["name"],"b":b["name"],"overlap_mm3":round(volume,3)})
        print("Checked pose",pose,flush=True)
    result={"status":"PASS_SAMPLED_CROSS_GROUP_CLEARANCE" if not collisions else "FAIL", "poses":poses,
            "exact_pairs_checked":checked,"expected_sliding_or_belt_fits_excluded":excluded,"collisions":collisions,
            "scope":"9 poses; only different motion groups; exclude simplified rail/block and belt/clamp fits; same-group attachments, bearings, fasteners, continuous swept motion and wiring are NOT certified"}
    (ROOT/"validation"/"motion_clearance.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(result["status"],len(collisions),"collisions",flush=True)
    if collisions:raise SystemExit(1)


if __name__=="__main__":main()
