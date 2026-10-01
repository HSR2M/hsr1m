"""
비행 전/후 공역·규정 점검 (preflight) — "비행은 사람"이라도 계획 단계에서 규정을 코드로 확인한다.

점검 항목 (항공안전법·시행규칙의 초경량비행장치 조종자 준수사항 기준; 코드는 '확인'만 하고 승인 여부 판단은 사람이):
  1) 야간   : 일몰 후 ~ 일출 전 비행 → 특별비행승인 대상 (250 g 미만도 준수사항은 적용되는 것으로 보고 경고)
  2) 고도   : 지표·수면 기준 150 m 초과 → 비행승인 대상 (SRT 상대고도는 이륙점 기준이라 참고값)
  3) 공역   : 비행금지·제한구역·관제권 폴리곤/원 안에 궤적(또는 계획점)이 들어가는지
  4) 가시권 : 이륙점에서 최대 수평거리 (VLOS는 거리 규정이 아니라 참고값으로만)
  5) 사람   : 탐지 결과(objects.csv의 obstacle: person 등)가 있으면 '사람 위 비행' 경고

구역 데이터: GeoJSON FeatureCollection. Polygon이면 그대로, Point면 properties.radius_m 로 원.
  properties: name, kind(금지|제한|관제권|기타), note, max_alt_m(선택)
  ⚠️ 내장 SAMPLE_ZONES 는 **예시**(인천·김포 관제권 반경 9.3 km 원). 발표·실비행 전에
     드론원스탑(drone.onestop.go.kr)·공공데이터포털의 공식 공역 데이터로 교체할 것.

  python -m litter.airspace --srt DJI_0007.SRT --out runs/preflight/0007 [--zones zones.geojson] [--objects runs/map/0007/objects.csv]
  python -m litter.airspace --points "37.3843,126.6571;37.3850,126.6580" --time "2026-10-02 10:00" --alt 20 --out runs/preflight/plan
"""
import argparse
import csv
import json
import math
from pathlib import Path

from . import solar

ALT_LIMIT_M = 150.0          # 항공안전법 시행규칙: 150 m 이상 고도 비행은 승인 대상
PEOPLE = {"person", "bicycle", "motorcycle", "dog"}

SAMPLE_ZONES = [
    {"name": "인천국제공항 관제권 (예시)", "kind": "관제권", "center": [37.4602, 126.4407], "radius_m": 9300.0,
     "note": "예시 값 — 드론원스탑 공식 공역 데이터로 교체"},
    {"name": "김포국제공항 관제권 (예시)", "kind": "관제권", "center": [37.5583, 126.7906], "radius_m": 9300.0,
     "note": "예시 값 — 드론원스탑 공식 공역 데이터로 교체"},
]


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def load_zones(path=None):
    """GeoJSON → 구역 목록. path가 없으면 SAMPLE_ZONES(예시)."""
    if not path:
        return [dict(z, sample=True) for z in SAMPLE_ZONES]
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    feats = d["features"] if d.get("type") == "FeatureCollection" else [d]
    out = []
    for f in feats:
        g, p = f.get("geometry", {}), f.get("properties", {}) or {}
        z = {"name": p.get("name", "구역"), "kind": p.get("kind", "기타"), "note": p.get("note", ""),
             "max_alt_m": p.get("max_alt_m"), "sample": False}
        if g.get("type") == "Point":
            lon, lat = g["coordinates"][:2]
            z.update(center=[lat, lon], radius_m=float(p.get("radius_m", 9300.0)))
        elif g.get("type") == "Polygon":
            z["polygon"] = [(c[1], c[0]) for c in g["coordinates"][0]]   # GeoJSON은 [lon, lat]
        elif g.get("type") == "MultiPolygon":
            z["polygon"] = [(c[1], c[0]) for c in g["coordinates"][0][0]]
        else:
            continue
        out.append(z)
    return out


def _in_polygon(lat, lon, ring):
    """레이 캐스팅 (작은 구역용, 위경도 그대로)."""
    inside = False
    n = len(ring)
    for i in range(n):
        y1, x1 = ring[i]
        y2, x2 = ring[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            x = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < x:
                inside = not inside
    return inside


def dist_to_zone_m(lat, lon, zone):
    """구역 경계까지 거리 (안이면 음수). 폴리곤은 꼭짓점까지 최소거리로 근사."""
    if "center" in zone:
        return haversine_m(lat, lon, *zone["center"]) - zone["radius_m"]
    d = min(haversine_m(lat, lon, a, b) for a, b in zone["polygon"])
    return -d if _in_polygon(lat, lon, zone["polygon"]) else d


def check_points(pts, zones, alts=None):
    """pts: [(lat, lon), ...]. 반환 {zones_hit: [...], nearest: {...}}."""
    hit, nearest = [], None
    for z in zones:
        ds = [dist_to_zone_m(a, b, z) for a, b in pts]
        inside = [i for i, d in enumerate(ds) if d <= 0]
        dmin = min(ds) if ds else float("inf")
        if inside:
            h = {"name": z["name"], "kind": z["kind"], "n_points": len(inside), "first_index": inside[0],
                 "sample": z.get("sample", False), "note": z.get("note", "")}
            if alts is not None and z.get("max_alt_m") is not None:
                h["max_alt_in_zone_m"] = float(max(alts[i] for i in inside))
                h["alt_over_zone_limit"] = h["max_alt_in_zone_m"] > z["max_alt_m"]
            hit.append(h)
        if nearest is None or dmin < nearest["distance_m"]:
            nearest = {"name": z["name"], "kind": z["kind"], "distance_m": round(dmin, 1), "sample": z.get("sample", False)}
    return {"zones_hit": hit, "nearest": nearest}


def _obstacles(objects_csv):
    if not objects_csv or not Path(objects_csv).exists():
        return None
    n = {}
    with open(objects_csv, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("kind") == "obstacle":
                n[r["cls"]] = n.get(r["cls"], 0) + 1
    return n


def check_track(tel, zones, tz_hours=9.0, alt_limit_m=ALT_LIMIT_M, objects_csv=None, alt_fix=None):
    """SRT 기록(telemetry.read_srt 결과) → 점검 보고 dict."""
    fx = [r for r in tel if "lat" in r and "lon" in r]
    if not fx:
        raise SystemExit("SRT에 위경도가 없음")
    pts = [(r["lat"], r["lon"]) for r in fx]
    alts = [alt_fix if alt_fix is not None else float(r.get("alt", 0) or 0) for r in fx]
    lat0, lon0 = pts[0]
    clat = sum(p[0] for p in pts) / len(pts)
    clon = sum(p[1] for p in pts) / len(pts)
    # 시각: SRT 현지 시각 문자열(dt_str) 우선, 없으면 dt(기계 시간대로 해석된 값)
    ts = []
    for r in fx:
        if r.get("dt_str"):
            ts.append(solar.local_to_utc(r["dt_str"], tz_hours))
        elif r.get("dt"):
            ts.append(float(r["dt"]))
    rep = {"n_fix": len(fx), "center_latlon": [round(clat, 6), round(clon, 6)],
           "takeoff_latlon": [round(lat0, 6), round(lon0, 6)],
           "max_rel_alt_m": round(max(alts), 1), "alt_limit_m": alt_limit_m,
           "max_dist_from_takeoff_m": round(max(haversine_m(lat0, lon0, a, b) for a, b in pts), 1),
           "track_length_m": round(sum(haversine_m(*pts[i], *pts[i + 1]) for i in range(len(pts) - 1)), 1)}
    if ts:
        t0, t1 = min(ts), max(ts)
        e0, _ = solar.solar_position(t0, clat, clon)
        e1, _ = solar.solar_position(t1, clat, clon)
        rise, sett = solar.sun_times(t0, clat, clon)
        rep.update(start_local=solar.fmt_local(t0, tz_hours), end_local=solar.fmt_local(t1, tz_hours),
                   duration_s=round(t1 - t0, 1), sun_elev_start_deg=round(e0, 1), sun_elev_end_deg=round(e1, 1),
                   sunrise_local=solar.fmt_local(rise, tz_hours) if rise else None,
                   sunset_local=solar.fmt_local(sett, tz_hours) if sett else None,
                   night=bool(e0 < -0.833 or e1 < -0.833))
    else:
        rep.update(night=None, note_time="SRT에 시각이 없어 야간 판정 불가")
    rep.update(check_points(pts, zones, alts))
    rep["obstacles"] = _obstacles(objects_csv)
    rep["verdicts"] = _verdicts(rep)
    return rep


def check_plan(points, zones, when_local=None, tz_hours=9.0, alt_m=None, alt_limit_m=ALT_LIMIT_M):
    """계획 경로점(lat, lon)으로 비행 전 점검."""
    clat = sum(p[0] for p in points) / len(points)
    clon = sum(p[1] for p in points) / len(points)
    rep = {"n_points": len(points), "center_latlon": [round(clat, 6), round(clon, 6)],
           "max_rel_alt_m": alt_m, "alt_limit_m": alt_limit_m}
    if when_local:
        t = solar.local_to_utc(when_local, tz_hours)
        e, _ = solar.solar_position(t, clat, clon)
        rise, sett = solar.sun_times(t, clat, clon)
        rep.update(start_local=solar.fmt_local(t, tz_hours), sun_elev_start_deg=round(e, 1), night=bool(e < -0.833),
                   sunrise_local=solar.fmt_local(rise, tz_hours) if rise else None,
                   sunset_local=solar.fmt_local(sett, tz_hours) if sett else None)
    else:
        rep["night"] = None
    rep.update(check_points(points, zones, [alt_m] * len(points) if alt_m is not None else None))
    rep["verdicts"] = _verdicts(rep)
    return rep


def _verdicts(rep):
    v = []
    if rep.get("night") is True:
        v.append({"item": "야간", "level": "승인필요", "msg": f"일몰 후 비행 (일몰 {rep.get('sunset_local')}) → 특별비행승인 없이는 불가"})
    elif rep.get("night") is False:
        v.append({"item": "야간", "level": "OK", "msg": f"주간 비행 (일출 {rep.get('sunrise_local')} · 일몰 {rep.get('sunset_local')})"})
    else:
        v.append({"item": "야간", "level": "확인", "msg": "비행 시각 정보 없음 — 수동 확인"})
    a, lim = rep.get("max_rel_alt_m"), rep.get("alt_limit_m")
    if a is None:
        v.append({"item": "고도", "level": "확인", "msg": "고도 정보 없음"})
    elif a > lim:
        v.append({"item": "고도", "level": "승인필요", "msg": f"최고 상대고도 {a} m > {lim:.0f} m"})
    else:
        v.append({"item": "고도", "level": "OK", "msg": f"최고 상대고도 {a} m (한계 {lim:.0f} m, 이륙점 기준 기압고도라 AGL과 다를 수 있음)"})
    hits = rep.get("zones_hit", [])
    if hits:
        names = ", ".join(f"{h['name']}[{h['kind']}]" for h in hits)
        v.append({"item": "공역", "level": "승인필요", "msg": f"구역 진입: {names}" + (" (예시 데이터 — 공식 데이터로 확인)" if any(h["sample"] for h in hits) else "")})
    else:
        nz = rep.get("nearest") or {}
        v.append({"item": "공역", "level": "OK", "msg": f"구역 진입 없음 · 가장 가까운 {nz.get('name')} 경계까지 {nz.get('distance_m')} m"
                  + (" (예시 데이터 — 공식 데이터로 확인)" if nz.get("sample") else "")})
    d = rep.get("max_dist_from_takeoff_m")
    if d is not None:
        v.append({"item": "가시권", "level": "OK" if d < 300 else "확인", "msg": f"이륙점에서 최대 {d} m (육안 확인 가능 거리인지 사람이 판단)"})
    ob = rep.get("obstacles")
    if ob:
        ppl = {k: n for k, n in ob.items() if k in PEOPLE}
        if ppl:
            v.append({"item": "사람", "level": "주의", "msg": f"비행 영상에서 사람·이륜차 탐지 {ppl} → 사람 위 비행 금지 준수 확인"})
    return v


def write_report(rep, out_dir, title="비행 점검"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "preflight.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# {title}", ""]
    for v in rep["verdicts"]:
        mark = {"OK": "✅", "주의": "⚠️", "확인": "❔", "승인필요": "⛔"}[v["level"]]
        lines.append(f"- {mark} **{v['item']}** ({v['level']}): {v['msg']}")
    lines += ["", f"- 기록 {rep.get('n_fix', rep.get('n_points'))}개 · 중심 {rep['center_latlon']}"]
    if rep.get("start_local"):
        lines.append(f"- 시각 {rep['start_local']} ~ {rep.get('end_local', '')} · 태양 고도 {rep.get('sun_elev_start_deg')}° → {rep.get('sun_elev_end_deg', '')}°")
    if rep.get("track_length_m") is not None:
        lines.append(f"- 궤적 {rep['track_length_m']} m · 최고 상대고도 {rep['max_rel_alt_m']} m")
    lines += ["", "> 구역 데이터가 '예시'면 드론원스탑 공식 공역으로 교체 후 다시 확인. 승인 여부 판단은 조종자 책임."]
    (out / "preflight.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out / "preflight.md"


def print_report(rep):
    for v in rep["verdicts"]:
        print(f"  [{v['level']:<4}] {v['item']}: {v['msg']}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="litter.airspace", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--srt", help="비행 기록 SRT (사후 점검)")
    ap.add_argument("--points", help="계획 경로점 'lat,lon;lat,lon;...' (사전 점검)")
    ap.add_argument("--time", help="계획 비행 시각 '2026-10-02 10:00' (현지)")
    ap.add_argument("--alt", type=float, help="계획 고도 m")
    ap.add_argument("--alt_fix", type=float, help="SRT 고도 대신 쓸 고정값 (SRT 고도가 흘렀을 때)")
    ap.add_argument("--zones", help="공역 GeoJSON (없으면 예시 관제권 2개)")
    ap.add_argument("--objects", help="orbit_map/video_map objects.csv — 사람 탐지 경고용")
    ap.add_argument("--tz", type=float, default=9.0, help="SRT 시각의 시간대 (KST 9)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    zones = load_zones(a.zones)
    if a.srt:
        from .telemetry import read_srt
        rep = check_track(read_srt(a.srt), zones, a.tz, objects_csv=a.objects, alt_fix=a.alt_fix)
        title = f"비행 점검 — {Path(a.srt).name}"
    elif a.points:
        pts = [tuple(float(v) for v in p.split(",")) for p in a.points.split(";") if p.strip()]
        rep = check_plan(pts, zones, a.time, a.tz, a.alt)
        title = "비행 전 점검 (계획 경로)"
    else:
        raise SystemExit("--srt 또는 --points 필요")
    print_report(rep)
    p = write_report(rep, a.out, title)
    print(f"→ {p} · preflight.json" + ("  (⚠️ 공역은 예시 데이터)" if not a.zones else ""))


if __name__ == "__main__":
    main()
