import sys, os, json, math
import os; sys.path.insert(0, os.environ.get("LITTER_REPO", "."))
import numpy as np, cv2, rasterio
from rasterio.transform import from_origin
from pyproj import Transformer
from pathlib import Path
import litter.sim_ortho as S

out = Path(os.environ.get("LITTER_TEST_OUT", "runs/test_sim")); out.mkdir(exist_ok=True)
# 1) 합성 정사영상 (EPSG:5186, 5 cm/px, 100×100 m)
x0, y1, res, n = 120800.0, 508100.0, 0.05, 2000
rng = np.random.default_rng(0)
img = rng.integers(90, 140, (3, n, n), dtype=np.uint8)
blobs = []
for i in range(6):
    cx, cy = rng.integers(200, n - 200, 2)
    img[:, cy - 8:cy + 8, cx - 8:cx + 8] = 240
    blobs.append((x0 + cx * res, y1 - cy * res))
ortho = out / "fake_ortho.tif"
with rasterio.open(ortho, "w", driver="GTiff", height=n, width=n, count=3, dtype="uint8", crs="EPSG:5186",
                   transform=from_origin(x0, y1, res, res), tiled=True, blockxsize=256, blockysize=256) as ds:
    ds.write(img)
    ds.build_overviews([2, 4, 8, 16])
# 2) 라벨 GeoJSON (위경도 폴리곤)
inv = Transformer.from_crs(5186, 4326, always_xy=True)
feats = []
for k, (bx, by) in enumerate(blobs):
    ring = [inv.transform(bx + dx, by + dy) for dx, dy in ((-0.4, -0.4), (0.4, -0.4), (0.4, 0.4), (-0.4, 0.4), (-0.4, -0.4))]
    feats.append({"type": "Feature", "properties": {"detection_seq": k + 1, "material_code": "STY", "area_sqm": 0.64},
                  "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in ring]]}})
labels = out / "fake_labels.json"
labels.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
# 3) 가짜 탐지기: 밝은 블롭이 프레임 안에 있으면 그 자리에 박스
class FakeDet:
    def __init__(self, *a, **k): pass
    def __call__(self, frame):
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        m = (g > 200).astype(np.uint8)
        nlab, lab, st, cen = cv2.connectedComponentsWithStats(m)
        outs = []
        for i in range(1, nlab):
            x, y, w, h, a = st[i]
            if a < 20: continue
            outs.append({"box": np.array([x, y, x + w, y + h], float), "cls": "Styrofoam", "score": float(rng.uniform(0.3, 0.9))})
        return outs
S.Detector = FakeDet
# 4) 창·키 입력 스텁 (헤드리스)
keys = iter([ord("w")] * 6 + [ord("d")] * 4 + [ord("e"), ord("r"), ord("w"), ord("w"), ord("v"), ord("h"), ord("f"), ord("s"), 27])
shown = {"n": 0}
cv2.namedWindow = lambda *a, **k: None
cv2.destroyWindow = lambda *a, **k: None
def fake_imshow(win, vis):
    shown["n"] += 1
    if shown["n"] == 5: cv2.imwrite(str(out / "manual_frame.jpg"), vis)
cv2.imshow = fake_imshow
cv2.waitKey = lambda ms=1: next(keys, 27)
fake_pt = out / "fake.pt"; fake_pt.write_bytes(b"x")
summ = S.run("t_manual", str(fake_pt), None, 60.0, alt=20.0, alt_low=8.0, out_root=out, ortho=ortho, labels_path=labels,
             manual=True, hide_labels=True, max_frames=80, gif_max=10, mission_time="2026-10-02 10:00")
print("MANUAL frames", summ["frames"], "objects", summ["objects_total"], "revisits", summ["revisits"], "flight_t", summ["flight_time_s"],
      "mission", summ["mission"]["sorties"], "airspace", [v["level"] for v in summ["airspace"]["verdicts"]], "shown", shown["n"])
print("eval", summ["eval"]["with_revisit"])
summ2 = S.run("t_auto", str(fake_pt), None, 60.0, alt=20.0, alt_low=8.0, out_root=out, ortho=ortho, labels_path=labels, max_frames=120, gif_max=10)
print("AUTO frames", summ2["frames"], "objects", summ2["objects_total"], "revisits", summ2["revisits"], "recall", summ2["eval"]["with_revisit"]["recall"])
print(sorted(p.name for p in (out / "t_manual").iterdir()))
