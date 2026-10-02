"""파이프라인(aerodrone_hackathon `litter` 패키지) 출력 → LitterObject.

입력 폴더(input/<현장>/) 에 들어 있는 파일을 보고 자동으로 판단한다 (config.json 의 "format" 으로 고정할 수도 있음).

  objects.csv + objects3d.csv         video_map/orbit_map 탐지 위치 + batch3d 3D 부피 (학교 야간 10분 비행, 상자 30개)
  objvol.json (+ objects.csv)         objvol v2 결과 (선회 시험 0007 · 골목 0010). 부피·크기·위경도·정답
  summary.json (fromvideo run)        items[] 에 무게까지 들어 있음
  items.csv + stops.csv               litter run / litter.report.write_tables 결과. 물체가 아주 많으면 정거장(stop) 단위로 묶는다
  labels.json                         업체 GeoJSON (문갑도) → collect.load_geojson

사진: photos/<ID>.jpg 가 있으면 쓰고, 없으면 config.json 의 "sheet" (격자 시트 jpg + 열·행 수) 에서 번호 순으로 잘라 쓴다.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

from .classes import map_class
from .collect import (COMPANY_KG_PER_M2, LitterObject, apply_estimate, company_code_of, estimate_2d_full, estimate_3d,
                      estimate_count, fill_proxies, material)


def _f(v, default=None):
    try:
        if v is None or str(v).strip() in ("", "nan", "None"):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _transformer(crs_m: str):
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:4326", crs_m, always_xy=True)


def _truth_m3(cfg: dict, obj_id: str, seq: int, tag: str = "") -> tuple[float | None, str]:
    """config.json 의 truth: {"default_cm": "42x32x39", "by_id": {"19": "42x32x39"}, "note": "..."}"""
    t = cfg.get("truth") or {}
    s = (t.get("by_id") or {}).get(str(obj_id)) or (t.get("by_id") or {}).get(str(seq)) or (t.get("by_id") or {}).get(tag) or t.get("default_cm")
    if not s:
        return None, ""
    try:
        l, w, h = (float(v) / 100 for v in str(s).lower().replace("×", "x").split("x"))
        return l * w * h, str(s)
    except ValueError:
        return None, ""


def _company_kg(code: str, area_m2: float) -> float:
    return area_m2 * COMPANY_KG_PER_M2[company_code_of(code)]


def _new(obj_id, seq, raw_cls, lon, lat, tr, *, area=0.0, w=0.0, h=0.0, image=None, date=None, source="", cfg=None) -> LitterObject:
    cls = (cfg or {}).get("class_map", {}).get(raw_cls, raw_cls)
    m = material(cls)
    x, y = tr.transform(lon, lat)
    return LitterObject(obj_id=str(obj_id), seq=int(seq), code=m.code, class_name=m.class_name, class_ko=m.ko, lon=float(lon), lat=float(lat),
                        x_m=float(x), y_m=float(y), area_m2=float(area), w_m=float(w), h_m=float(h), company_kg=None,
                        kg_min=0, kg_typ=0, kg_max=0, volume_m3=0, image_path=image, survey_date=date, source=source)


# ─────────────────────────── (1) objects.csv + objects3d.csv (학교 야간 비행) ───────────────────────────
def load_objects3d(folder: Path, cfg: dict, crs_m: str) -> list[LitterObject]:
    """objects3d.csv (batch3d: box, lat, lon, L_cm, W_cm, H_cm, vol_med_L, confidence, status, reason, mask_img)
    + 선택 plan.json (boxes: id, lat, lon, seen, score, t) + 선택 objects.csv (video_map: kind, cls, lat, lon, seen_frames, best_score)."""
    tr = _transformer(crs_m)
    date = cfg.get("survey_date")
    default_cls = cfg.get("default_class", "cardboard")
    rows = _read_csv(folder / "objects3d.csv")
    boxes = {}
    if (folder / "plan.json").exists():
        for b in json.loads((folder / "plan.json").read_text(encoding="utf-8")).get("boxes", []):
            boxes[str(b.get("id"))] = b
    # objects.csv 로 종류(cls) 를 보강: 가장 가까운 탐지 (10 m 안)
    dets = []
    if (folder / "objects.csv").exists():
        for r in _read_csv(folder / "objects.csv"):
            if r.get("kind", "litter") == "litter":
                dets.append((float(r["lat"]), float(r["lon"]), r["cls"], _f(r.get("best_score"), 0.0)))
    out = []
    for r in rows:
        bid = str(r["box"]); seq = int(float(bid)) if bid.replace(".", "").isdigit() else len(out) + 1
        lat, lon = _f(r.get("lat")), _f(r.get("lon"))
        if lat is None or lon is None:
            b = boxes.get(bid)
            if not b:
                continue
            lat, lon = b["lat"], b["lon"]
        raw_cls = default_cls
        if dets:
            near = min(dets, key=lambda d: math.hypot((d[0] - lat) * 111320, (d[1] - lon) * 111320 * math.cos(math.radians(lat))))
            if math.hypot((near[0] - lat) * 111320, (near[1] - lon) * 111320 * math.cos(math.radians(lat))) < float(cfg.get("class_match_m", 2.5)):
                raw_cls = near[2]
        L, W, H = _f(r.get("L_cm")), _f(r.get("W_cm")), _f(r.get("H_cm"))
        vol_L = _f(r.get("vol_med_L")) or _f(r.get("vol_max_L"))
        status = r.get("status", ""); conf = r.get("confidence", "") or ""
        img = cfg.get("photo_pattern", "photos/{seq:02d}.jpg").format(seq=seq, id=bid)
        o = _new(f"{cfg.get('id_prefix', 'BOX')}_{seq:02d}", seq, raw_cls, lon, lat, tr, image=img, date=date,
                 source=f"objects3d.csv #{bid} · {status}" + (f" ({r.get('reason')})" if r.get("reason") else "") +
                        (f" · 위치 {r.get('latlon_src')}" if r.get("latlon_src") else ""), cfg=cfg)
        truth, tnote = _truth_m3(cfg, o.obj_id, seq, bid)
        o.truth_m3 = truth
        ok_vol = vol_L is not None and vol_L > 0.05 and status.startswith("부피 OK") and (H or 0) > 0.03
        if ok_vol:
            o.w_m, o.h_m, o.height_m = (L or 0) / 100, (W or 0) / 100, (H or 0) / 100
            o.area_m2 = o.w_m * o.h_m
            o.confidence = conf
            apply_estimate(o, estimate_3d(o.code, vol_L / 1000, conf))
            o.note += f" · 측정 {o.dims_cm}"
        else:
            o.basis = "proxy"; o.volume_m3 = 0.0; o.confidence = conf or ("실패" if status else "")
        if r.get("viewer"):
            o.source += f" · {r['viewer']}"
        out.append(o)
    n_proxy = fill_proxies(out)
    for o in out:
        if o.basis == "proxy":           # 대체 부피에서 대략 크기·면적도 채움 (작업 시간·2인 판단용)
            side = o.volume_m3 ** (1 / 3)
            o.w_m, o.h_m, o.height_m = side, side, side
            o.area_m2 = side * side
        o.company_kg = _company_kg(o.code, o.area_m2)
    return out


# ─────────────────────────── (2) objvol.json (선회 시험·골목) ───────────────────────────
def load_objvol(folder: Path, cfg: dict, crs_m: str) -> list[LitterObject]:
    """objvol.json 하나 또는 여러 개 (config "objvol": ["a/objvol.json", ...]). 태그·위경도·크기·부피·정답.
    위경도가 없으면 같은 폴더 objects.csv 의 '클래스_프레임수' 로 찾는다."""
    tr = _transformer(crs_m)
    date = cfg.get("survey_date")
    files = cfg.get("objvol") or ["objvol.json"]
    out = []
    seq = 0
    for rel in files:
        path = folder / rel
        if not path.exists():
            continue
        recs = json.loads(path.read_text(encoding="utf-8"))
        ll = {}
        ocsv = path.parent / "objects.csv"
        if ocsv.exists():
            for r in _read_csv(ocsv):
                ll[f"{r['cls']}_{r['seen_frames']}"] = (float(r["lat"]), float(r["lon"]))
        prefix = path.parent.name if len(files) > 1 else cfg.get("id_prefix", "OBJ")
        for rec in recs:
            tag = rec["tag"]
            lat, lon = _f(rec.get("lat")), _f(rec.get("lon"))
            if lat is None:
                lat, lon = ll.get(tag, (None, None))
            if lat is None:
                continue
            seq += 1
            raw = (cfg.get("material") or {}).get(tag) or (cfg.get("material") or {}).get(f"{prefix}:{tag}") or tag
            mask = path.parent / f"{tag}_masks.jpg"
            o = _new(f"{prefix}_{tag}", seq, raw, lon, lat, tr, image=str(mask.relative_to(folder)) if mask.exists() else None,
                     date=date, source=f"{rel} · {tag}", cfg=cfg)
            if rec.get("truth_L"):
                o.truth_m3 = rec["truth_L"] / 1000
            else:
                o.truth_m3 = _truth_m3(cfg, o.obj_id, seq, tag)[0]
            vol_L = rec.get("volume_heightmap_L")
            views = rec.get("views_used", 0) or 0
            H = rec.get("height_m") or 0
            if vol_L and vol_L > 0 and H > 0.03:
                o.w_m, o.h_m, o.height_m = rec.get("length_m", 0) or 0, rec.get("width_m", 0) or 0, H
                o.area_m2 = rec.get("mask_area_m2") or (o.w_m * o.h_m)
                tilt = rec.get("ground_plane_tilt_deg", 0) or 0
                o.confidence = "높음" if (views >= 8 and tilt < 15) else ("중간" if views >= 4 else f"낮음(뷰 {views})")
                apply_estimate(o, estimate_3d(o.code, vol_L / 1000, o.confidence))
                o.note += f" · 측정 {o.dims_cm} · 프레임 {views}장"
            else:
                o.basis = "proxy"; o.volume_m3 = 0.0; o.confidence = "실패"
            out.append(o)
    fill_proxies(out)
    for o in out:
        if o.basis == "proxy":
            side = o.volume_m3 ** (1 / 3)
            o.w_m, o.h_m, o.height_m, o.area_m2 = side, side, side, side * side
        o.company_kg = _company_kg(o.code, o.area_m2)
    return out


# ─────────────────────────── (3) fromvideo summary.json ───────────────────────────
def load_summary_items(folder: Path, cfg: dict, crs_m: str) -> list[LitterObject]:
    tr = _transformer(crs_m)
    d = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    out = []
    for i, it in enumerate(d.get("items", []), 1):
        o = _new(it["item_id"], i, it.get("material_raw") or it.get("cls"), it["lon"], it["lat"], tr,
                 area=it.get("area_m2", 0), w=it.get("length_m", 0), h=it.get("width_m", 0), date=cfg.get("survey_date"),
                 source="fromvideo summary.json", cfg=cfg)
        o.height_m = it.get("h_p90_m", 0) or 0
        o.truth_m3 = it.get("truth_m3")
        vol = it.get("volume_m3") or 0
        if vol > 0 and "3d" in str(it.get("weight_method", "")):
            o.confidence = "중간"
            apply_estimate(o, estimate_3d(o.code, vol, "중간"))
        elif o.area_m2 > 0:
            apply_estimate(o, estimate_2d_full(o.code, o.area_m2))
        else:
            apply_estimate(o, estimate_count(o.code))
        if it.get("company_kg") is not None:
            o.company_kg = it["company_kg"]
        out.append(o)
    return out


# ─────────────────────────── (4) items.csv + stops.csv (litter run 결과) ───────────────────────────
def load_stops(folder: Path, cfg: dict, crs_m: str, *, max_objects: int = 400) -> list[LitterObject]:
    """litter.report 의 stops.csv(정거장) + items.csv(물체). 물체가 max_objects 보다 많으면 정거장을 한 물체(basis='agg') 로 묶는다.
    정거장 무게는 파이프라인 값(weight_lo/est/hi, 면적 × 두께범위 × 밀도) 을 종류별로 합쳐 둔다 (보정 계수는 종류별로 곱함)."""
    tr = _transformer(crs_m)
    items = _read_csv(folder / "items.csv")
    stops = _read_csv(folder / "stops.csv") if (folder / "stops.csv").exists() else []
    date = cfg.get("survey_date")
    by_stop: dict[str, list[dict]] = {}
    for it in items:
        by_stop.setdefault(it.get("stop_id", ""), []).append(it)
    out = []
    if len(items) <= max_objects or not stops:
        for i, it in enumerate(items, 1):
            o = _new(it["item_id"], i, it.get("cls_raw") or it["cls"], it["lon"], it["lat"], tr, area=_f(it.get("area_m2"), 0),
                     w=_f(it.get("length_m"), 0), h=_f(it.get("length_m"), 0), image=it.get("image") or None, date=date,
                     source="items.csv", cfg=cfg)
            if str(it.get("valid_3d", "")).lower() == "true" and _f(it.get("volume_m3"), 0) > 0:
                o.height_m = _f(it.get("h_p90_m"), 0)
                apply_estimate(o, estimate_3d(o.code, _f(it["volume_m3"]), "중간")); o.confidence = "중간"
            elif _f(it.get("weight_est_kg")):
                lo, est, hi = _f(it.get("weight_lo_kg"), 0), _f(it["weight_est_kg"]), _f(it.get("weight_hi_kg"), 0)
                vol = _f(it.get("volume_m3"), 0) or material(o.code).default_vol_m3
                o.kg_min, o.kg_typ, o.kg_max = lo, est, hi
                o.vol_min_m3, o.volume_m3, o.vol_max_m3 = vol * 0.5, vol, vol * 2
                o.basis = "2d"; o.item_kg_max = hi
                o.note = f"파이프라인 2D 추정 ({it.get('weight_method', '')})"
            else:
                apply_estimate(o, estimate_2d_full(o.code, o.area_m2))
            o.company_kg = _company_kg(o.code, o.area_m2)
            out.append(o)
        return out
    # 정거장 묶음
    for i, s in enumerate(stops, 1):
        its = by_stop.get(s["stop_id"], [])
        if not its:
            continue
        kg_by: dict[str, list[float]] = {}
        members = []
        item_kg_max = 0.0
        for it in its:
            m = material(it.get("cls_raw") or it["cls"]); c = m.code
            lo, est, hi = _f(it.get("weight_lo_kg"), 0), _f(it.get("weight_est_kg"), 0), _f(it.get("weight_hi_kg"), 0)
            vol = _f(it.get("volume_m3"), 0) or m.default_vol_m3
            area = _f(it.get("area_m2"), 0)
            v = kg_by.setdefault(c, [0.0, 0.0, 0.0, 0.0, 0.0, 0])
            v[0] += lo; v[1] += est; v[2] += hi; v[3] += vol; v[4] += area; v[5] += 1
            item_kg_max = max(item_kg_max, hi)
            members.append({"cls": c, "ko": m.ko, "kg": round(est, 3), "kg_hi": round(hi, 3), "area": round(area, 3), "crew": it.get("crew", "")})
        dom = max(kg_by.items(), key=lambda kv: kv[1][1])[0]
        o = _new(s["stop_id"], i, dom, s["lon"], s["lat"], tr, area=sum(v[4] for v in kg_by.values()), date=date,
                 source=f"stops.csv {s['stop_id']} (물체 {len(its)}개, 파이프라인 {s.get('crew', '')})", cfg=cfg)
        o.basis = "agg"; o.n_items = len(its); o.kg_by = kg_by; o.members = members
        o.kg_min = sum(v[0] for v in kg_by.values()); o.kg_typ = sum(v[1] for v in kg_by.values()); o.kg_max = sum(v[2] for v in kg_by.values())
        o.volume_m3 = sum(v[3] for v in kg_by.values()); o.vol_min_m3 = o.volume_m3 * 0.5; o.vol_max_m3 = o.volume_m3 * 2
        o.item_kg_max = item_kg_max
        side = math.sqrt(max(o.area_m2, 0.01)); o.w_m = o.h_m = side
        o.company_kg = sum(_company_kg(c, v[4]) for c, v in kg_by.items())
        o.note = f"정거장(반경 5 m) {len(its)}개 묶음 · 파이프라인 2D 추정(면적 × 두께범위 × 겉보기밀도) 종류별 합"
        out.append(o)
    return out


# ─────────────────────────── (5) objects.csv 만 (크기 없음) ───────────────────────────
def load_objects_csv(folder: Path, cfg: dict, crs_m: str) -> list[LitterObject]:
    tr = _transformer(crs_m)
    out = []
    for i, r in enumerate(_read_csv(folder / "objects.csv"), 1):
        if r.get("kind", "litter") != "litter":
            continue
        o = _new(f"{cfg.get('id_prefix', 'DET')}_{i:03d}_{r['cls']}", i, r["cls"], r["lon"], r["lat"], tr, date=cfg.get("survey_date"),
                 source=f"objects.csv ({r.get('seen_frames', '?')}프레임, 신뢰도 {r.get('best_score', '?')})", cfg=cfg)
        apply_estimate(o, estimate_count(o.code))
        side = o.volume_m3 ** (1 / 3); o.w_m = o.h_m = side; o.area_m2 = side * side
        o.company_kg = _company_kg(o.code, o.area_m2)
        out.append(o)
    return out


# ─────────────────────────── 자동 판별 ───────────────────────────
def detect_format(folder: Path, cfg: dict) -> str:
    fmt = cfg.get("format")
    if fmt:
        return fmt
    if (folder / "labels.json").exists():
        return "geojson"
    if (folder / "objects3d.csv").exists():
        return "objects3d"
    if cfg.get("objvol") or (folder / "objvol.json").exists():
        return "objvol"
    if (folder / "items.csv").exists():
        return "stops"
    if (folder / "summary.json").exists():
        return "summary"
    if (folder / "objects.csv").exists():
        return "objects"
    raise FileNotFoundError(f"{folder}: labels.json / objects3d.csv / objvol.json / items.csv / summary.json / objects.csv 중 하나가 필요합니다")


def load_site_objects(folder: str | Path, cfg: dict, crs_m: str) -> tuple[list[LitterObject], str]:
    folder = Path(folder)
    fmt = detect_format(folder, cfg)
    if fmt == "geojson":
        from .collect import load_geojson
        objs = load_geojson(folder / cfg.get("labels", "labels.json"), crs_m=crs_m)
    elif fmt == "objects3d":
        objs = load_objects3d(folder, cfg, crs_m)
    elif fmt == "objvol":
        objs = load_objvol(folder, cfg, crs_m)
    elif fmt == "stops":
        objs = load_stops(folder, cfg, crs_m, max_objects=int(cfg.get("max_objects", 400)))
    elif fmt == "summary":
        objs = load_summary_items(folder, cfg, crs_m)
    elif fmt == "objects":
        objs = load_objects_csv(folder, cfg, crs_m)
    else:
        raise ValueError(f"알 수 없는 format: {fmt}")
    return objs, fmt


# ─────────────────────────── 사진 시트 자르기 ───────────────────────────
def crop_sheet(sheet: str | Path, out_dir: str | Path, cols: int, rows: int, n: int, pattern: str = "{seq:02d}.jpg",
               label_h: int = 0, max_px: int = 320) -> list[Path]:
    """격자 시트(jpg) 를 번호 순(왼쪽 위 → 오른쪽) 으로 잘라 photos/01.jpg … 로 저장."""
    import cv2
    img = cv2.imdecode(np.fromfile(str(sheet), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(sheet)
    H, W = img.shape[:2]
    cw, ch = W / cols, H / rows
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    paths = []
    for k in range(n):
        r, c = divmod(k, cols)
        x0, y0 = int(c * cw), int(r * ch) + label_h
        crop = img[y0:int((r + 1) * ch), x0:int((c + 1) * cw)]
        s = min(1.0, max_px / max(crop.shape[:2]))
        if s < 1:
            crop = cv2.resize(crop, (int(crop.shape[1] * s), int(crop.shape[0] * s)), interpolation=cv2.INTER_AREA)
        p = out / pattern.format(seq=k + 1)
        ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if ok:
            buf.tofile(str(p)); paths.append(p)
    return paths
