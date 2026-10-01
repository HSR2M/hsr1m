import sys, json; import os; sys.path.insert(0, os.environ.get("LITTER_REPO", "."))
import matplotlib; matplotlib.use("Agg")
from litter.fromvideo import check_company_units, fig_company_labels, company_weight
from pathlib import Path
# 업체 라벨 흉내: weight_kg = area × 계수(0.012 등) — 실제 파일 통계(42개, 합계 1.3188, 최대 0.2498)에 맞춘 합성
import random; random.seed(1)
coef = {"STY": 0.012, "ROP": 0.024, "FIS": 0.024, "PLA": 0.020}
codes = ["STY"]*37 + ["ROP"]*3 + ["FIS"] + ["PLA"]
feats = []
for i, c in enumerate(codes):
    a = round(random.uniform(0.1, 3.0), 3) if i else 20.8
    feats.append({"type": "Feature", "properties": {"detection_seq": i+1, "material_code": c, "area_sqm": a, "weight_kg": round(a*coef[c], 4)},
                  "geometry": {"type": "Polygon", "coordinates": [[[126.1, 37.2], [126.1001, 37.2], [126.1001, 37.2001], [126.1, 37.2001], [126.1, 37.2]]]}})
Path("t/labels_fake.json").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
uc = check_company_units("t/labels_fake.json")
print(json.dumps(uc, ensure_ascii=False, indent=1))
out = Path("t/cmp"); out.mkdir(exist_ok=True)
try:
    p, st = fig_company_labels(out, "t/labels_fake.json", 1.0); print("kg 그림", p, round(st["sum_kg"], 3), round(st["realistic_lo_kg"]), round(st["realistic_hi_kg"]))
    p, st = fig_company_labels(out, "t/labels_fake.json", 1000.0); print("t 그림 ", p, round(st["sum_kg"], 1))
except Exception as e:
    print("그림 생략(폰트/백엔드):", type(e).__name__, e)
it = {"cls": "eps_fragment", "area_m2": 0.2995}
print("company_weight kg:", company_weight(it), " t:", company_weight(it, 1000.0))
# 단위 정상 케이스
feats2 = [dict(f, properties=dict(f["properties"], weight_kg=f["properties"]["area_sqm"]*5.0)) for f in feats]
Path("t/labels_ok.json").write_text(json.dumps({"type": "FeatureCollection", "features": feats2}))
print(check_company_units("t/labels_ok.json")["verdict"])
