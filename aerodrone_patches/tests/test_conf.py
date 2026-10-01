import sys, csv; import os; sys.path.insert(0, os.environ.get("LITTER_REPO", "."))
from litter.batch3d import _confidence
truth_L = 52.4
rows = list(csv.DictReader(open(os.environ.get("LITTER_REPO", ".") + "/docs/figures/0015_objects3d.csv", encoding="utf-8-sig")))
print(f"{'box':>3} {'vol_med':>7} {'err':>6} {'이전':<28} {'새 플래그':<30}")
for r in rows:
    if r["vol_med_L"] == "":
        continue
    vol = {"volume_heightmap_L": float(r["vol_med_L"]), "volume_heightmap_median_L": float(r["vol_med_L"]),
           "volume_mask_box_L": float(r["vol_mask_L"]) if r["vol_mask_L"] else None,
           "points_object": int(r["points_object"]), "views_used": int(r["views_used"]), "ground_plane_tilt_deg": float(r["plane_tilt_deg"])}
    sfm = {"reg": int(r["frames_reg"]), "ext": int(r["frames_ext"]), "pts": int(r["sparse_pts"])}
    new = _confidence(vol, r["gps_rms_m"], sfm, r["scale_src"])
    err = (float(r["vol_med_L"]) / truth_L - 1) * 100
    print(f"{r['box']:>3} {r['vol_med_L']:>7} {err:+5.0f}% {r['confidence']:<28} {new:<30}")
# 0007 선회 (v2 json)
import json
for f in [os.environ.get("LITTER_REPO", ".") + "/docs/figures/0007_objvol_v2.json", os.environ.get("LITTER_REPO", ".") + "/docs/figures/0010_objvol_v2.json"]:
    for v in json.load(open(f, encoding="utf-8")):
        if "volume_heightmap_L" in v:
            print(f.split('/')[-1], v["tag"], "→", _confidence(v, 1.16 if "0007" in f else 0.51, {"reg": 100, "ext": 100, "pts": 28580 if "0007" in f else 91282}, "고도(SRT)" if "0007" in f else "GPS"))
