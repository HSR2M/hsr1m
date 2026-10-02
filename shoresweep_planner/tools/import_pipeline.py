"""aerodrone_hackathon 저장소(coastal litter pipeline) 의 한 영상 결과를 input/ 으로 가져온다.

  python tools/import_pipeline.py --repo ../aerodrone_hackathon --video 0015
  python tools/import_pipeline.py --repo ../aerodrone_hackathon --video 0007 --out input/0007 --truth "Plastic_Buoy_55:23x17x8"
  python tools/import_pipeline.py --repo ../aerodrone_hackathon --video 0015 --name "학교 캠퍼스" --depot 126.6565,37.3851 --depot-name 이륙지점

저장소 안에서 찾는 것 (있는 것만, 작은 csv/json/썸네일만 — 영상·점구름은 가져오지 않음)
  runs/orbit/<영상>_all/{objects3d.csv, plan.json, masks_sheet.jpg}       batch3d 결과 → format objects3d
  runs/orbit/<영상>*/objvol_v2|objvol_dense|objvol/{objvol.json, *_masks.jpg}  objvol 결과 → format objvol
  runs/plan/<영상>/summary.json                                          fromvideo run 결과 → format summary
  runs/map/<영상>*/objects.csv                                           탐지 위치 (video_map / orbit_map) → 종류 보강 또는 format objects
  runs/map/<영상>*/{box_sheet.jpg, sheet.jpg}                            사진 시트 → photos/NN.jpg (격자는 자동 추정, --sheet-grid 6x5 로 지정 가능)
  runs/map/<영상>*/mosaic.tif                                            정사영상(1 cm/px, UTM) → ortho/mosaic.jpg + .jgw + .prj
config.json 은 없을 때만 새로 쓴다 (--force 로 덮어씀). 그 뒤  python run.py  로 사이트를 만든다.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

UTM_PRJ = ('PROJCS["WGS 84 / UTM zone {z}N",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
           'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],'
           'PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",{cm}],PARAMETER["scale_factor",0.9996],'
           'PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1],AUTHORITY["EPSG","{epsg}"]]')


def _copy(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  {src.relative_to(src.parents[len(src.parents) - 1]) if False else src.name:<22} ← {src}")
    return True


def _litter_rows(csv_path: Path) -> int:
    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            return sum(1 for r in csv.DictReader(f) if r.get("kind", "litter") == "litter")
    except OSError:
        return 0


def find_map_dir(repo: Path, video: str) -> Path | None:
    """runs/map/<영상>* 중 쓰레기 탐지가 가장 많은 폴더."""
    cands = [d for d in (repo / "runs/map").glob(f"{video}*") if (d / "objects.csv").exists()]
    if not cands:
        return None
    return max(cands, key=lambda d: (_litter_rows(d / "objects.csv"), d.name))


def find_objvol(repo: Path, video: str) -> Path | None:
    for d in sorted((repo / "runs/orbit").glob(f"{video}*")):
        for sub in ("objvol_v2", "objvol_dense", "objvol"):
            p = d / sub / "objvol.json"
            if p.exists():
                return p
    return None


def guess_grid(w: int, h: int, n: int) -> tuple[int, int]:
    """16:9 프레임을 격자로 붙인 시트에서 (열, 행) 추정: n 개 이상 들어가면서 칸 비율이 16:9 에 가장 가까운 것."""
    best = None
    for cols in range(1, 13):
        rows = math.ceil(n / cols)
        ratio = (w / cols) / (h / rows)
        score = abs(math.log(ratio / (16 / 9)))
        if best is None or score < best[0]:
            best = (score, cols, rows)
    return best[1], best[2]


def export_ortho(tif: Path, out: Path) -> bool:
    from PIL import Image
    try:
        im = Image.open(tif)
        sx, sy, _ = im.tag_v2[33550]; tp = im.tag_v2[33922]
        x0, y0 = tp[3], tp[4]
        ascii_ = str(im.tag_v2.get(34737, ""))
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ mosaic.tif 좌표 태그를 읽지 못함 ({e}) → 정사영상 생략")
        return False
    m = re.search(r"UTM zone (\d+)([NS])", ascii_)
    if not m:
        print(f"  ⚠ 좌표계 {ascii_!r} 는 UTM 이 아니라 생략 (QGIS 로 jpg + 월드파일을 만들어 ortho/ 에 넣으세요)")
        return False
    zone = int(m.group(1)); epsg = (32600 if m.group(2) == "N" else 32700) + zone
    (out / "ortho").mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(out / "ortho/mosaic.jpg", quality=85)
    (out / "ortho/mosaic.jgw").write_text(f"{sx}\n0\n0\n{-sy}\n{x0 + sx / 2}\n{y0 - sy / 2}\n", encoding="utf-8")
    (out / "ortho/mosaic.prj").write_text(UTM_PRJ.format(z=zone, cm=zone * 6 - 183, epsg=epsg), encoding="utf-8")
    print(f"  ortho/mosaic.jpg {im.size[0]}×{im.size[1]} px ({sx * 100:g} cm/px, EPSG:{epsg})")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="aerodrone_hackathon 체크아웃 폴더")
    ap.add_argument("--video", required=True, help="영상 번호 (예: 0015) — runs/orbit, runs/map 폴더 이름 앞부분")
    ap.add_argument("--out", default=str(ROOT / "input"), help="넣을 폴더 (기본 input/)")
    ap.add_argument("--name", default=None, help="현장 이름")
    ap.add_argument("--depot", default=None, help="출발·집결지 경도,위도 (없으면 첫 탐지 위치)")
    ap.add_argument("--depot-name", default="집결지")
    ap.add_argument("--date", default=None, help="촬영일 표시 문구")
    ap.add_argument("--truth", default=None, help="정답 크기: '42x32x39' (전부) 또는 '태그:23x17x8,태그2:60x45x12'")
    ap.add_argument("--default-class", default="cardboard", help="objects3d 형식에서 종류를 모를 때 (cardboard, styrofoam_fragment …)")
    ap.add_argument("--sheet-grid", default=None, help="사진 시트 격자 '열x행' (없으면 자동 추정)")
    ap.add_argument("--crs", default=None, help="거리 계산 좌표계 (기본: 정사영상 좌표계 또는 EPSG:5186)")
    ap.add_argument("--force", action="store_true", help="config.json 덮어쓰기")
    a = ap.parse_args()
    repo = Path(a.repo).resolve(); out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    video = a.video
    print(f"[{video}] {repo} → {out}")
    cfg: dict = {"site": a.name or f"학교 캠퍼스 영상 {video}", "format": None, "crs": a.crs or "EPSG:5186",
                 "id_prefix": f"V{video}", "survey_date": a.date or f"영상 {video}", "zone_word": "구역",
                 "defaults": {"workers": 2, "hours": 2.0, "link": 25, "walk": 4.0, "detour": 1.3},
                 "source": f"aerodrone_hackathon runs/* ({video})"}
    n_objs = 0
    # 1) batch3d
    orbit_all = repo / "runs/orbit" / f"{video}_all"
    mapdir = find_map_dir(repo, video)
    if (orbit_all / "objects3d.csv").exists():
        cfg["format"] = "objects3d"; cfg["default_class"] = a.default_class
        _copy(orbit_all / "objects3d.csv", out / "objects3d.csv"); _copy(orbit_all / "plan.json", out / "plan.json")
        with open(out / "objects3d.csv", encoding="utf-8-sig", newline="") as f:
            n_objs = sum(1 for _ in csv.DictReader(f))
        if mapdir:
            _copy(mapdir / "objects.csv", out / "objects.csv")
        masks = orbit_all / "masks_sheet.jpg"
        if masks.exists() and n_objs:
            import cv2
            import numpy as np
            img = cv2.imdecode(np.fromfile(str(masks), np.uint8), cv2.IMREAD_COLOR)
            H, W = img.shape[:2]
            cols, rows = (int(v) for v in a.sheet_grid.lower().split("x")) if a.sheet_grid else guess_grid(W, H, n_objs)
            cw, ch = W / cols, H / rows
            (out / "masks").mkdir(exist_ok=True); kept = 0
            for k in range(n_objs):
                r, c = divmod(k, cols)
                crop = img[int(r * ch) + 24:int((r + 1) * ch), int(c * cw):int((c + 1) * cw)]
                if crop.size == 0 or crop.mean() < 45:
                    continue
                ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 82])
                if ok:
                    buf.tofile(str(out / "masks" / f"{k + 1:02d}.jpg")); kept += 1
            cfg["mask_pattern"] = "masks/{seq:02d}.jpg"
            print(f"  masks/ {kept}장 (masks_sheet.jpg {cols}×{rows} 자름)")
    # 2) objvol
    elif (ov := find_objvol(repo, video)) is not None:
        cfg["format"] = "objvol"; cfg["objvol"] = ["objvol.json"]
        _copy(ov, out / "objvol.json")
        for m in ov.parent.glob("*_masks.jpg"):
            _copy(m, out / m.name)
        if mapdir:
            _copy(mapdir / "objects.csv", out / "objects.csv")
        n_objs = len(json.loads((out / "objvol.json").read_text(encoding="utf-8")))
    # 3) fromvideo summary
    elif (repo / "runs/plan" / video / "summary.json").exists():
        cfg["format"] = "summary"; _copy(repo / "runs/plan" / video / "summary.json", out / "summary.json")
        n_objs = len(json.loads((out / "summary.json").read_text(encoding="utf-8")).get("items", []))
    # 4) 탐지 위치만
    elif mapdir:
        cfg["format"] = "objects"; _copy(mapdir / "objects.csv", out / "objects.csv"); n_objs = _litter_rows(out / "objects.csv")
    else:
        sys.exit(f"  영상 {video} 의 결과를 찾지 못했습니다 (runs/orbit/{video}_all, runs/orbit/{video}*/objvol*, runs/plan/{video}, runs/map/{video}*)")
    # 사진 시트 → photos/
    if mapdir:
        for sheet_name in ("box_sheet.jpg", "sheet.jpg", "litter_sheet.jpg"):
            sheet = mapdir / sheet_name
            if sheet.exists() and n_objs and cfg["format"] in ("objects3d", "objects"):
                from litter3d.pipeline_io import crop_sheet
                from PIL import Image
                W, H = Image.open(sheet).size
                cols, rows = (int(v) for v in a.sheet_grid.lower().split("x")) if a.sheet_grid else guess_grid(W, H, n_objs)
                n = len(crop_sheet(sheet, out / "photos", cols=cols, rows=rows, n=min(n_objs, cols * rows)))
                cfg["photo_pattern"] = "photos/{seq:02d}.jpg"
                print(f"  photos/ {n}장 ({sheet_name} {cols}×{rows} 자름)")
                break
        tif = mapdir / "mosaic.tif"
        if tif.exists() and export_ortho(tif, out):
            cfg["ortho"] = "ortho/mosaic.jpg"
            prj = (out / "ortho/mosaic.prj").read_text(encoding="utf-8")
            m = re.search(r'AUTHORITY\["EPSG","(\d+)"\]\]$', prj)
            if m and not a.crs:
                cfg["crs"] = f"EPSG:{m.group(1)}"
    # 출발지
    if a.depot:
        lon, lat = (float(v) for v in a.depot.split(","))
        cfg["depot"] = {"lon": lon, "lat": lat, "name": a.depot_name}
    else:
        first = None
        if (out / "plan.json").exists():
            b = json.loads((out / "plan.json").read_text(encoding="utf-8")).get("boxes")
            if b:
                first = (b[0]["lon"], b[0]["lat"])
        if first is None and (out / "objects.csv").exists():
            with open(out / "objects.csv", encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    if r.get("kind", "litter") == "litter":
                        first = (float(r["lon"]), float(r["lat"])); break
        if first:
            cfg["depot"] = {"lon": first[0], "lat": first[1], "name": a.depot_name + " (첫 탐지 위치 — 확인 필요)"}
    if a.truth:
        if ":" in a.truth:
            cfg["truth"] = {"by_id": dict(kv.split(":") for kv in a.truth.split(","))}
        else:
            cfg["truth"] = {"default_cm": a.truth}
    p = out / "config.json"
    if p.exists() and not a.force:
        print(f"  config.json 유지 (덮어쓰려면 --force): {p}")
    else:
        p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  config.json 작성 (format={cfg['format']}, 물체 {n_objs}개)")
    print(f"완료. 다음:  python run.py" + ("" if out == ROOT / "input" else f" --input {out}"))


if __name__ == "__main__":
    main()
