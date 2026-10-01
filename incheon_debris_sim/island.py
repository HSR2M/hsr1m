"""섬 단위(교동도·서검도 등) 집적 분석과 영상 장면 구성.

- 지역 모의(sim_results*.npz) 결과에서 대상 섬 해안 셀의 좌초 입자만 추출해
  '섬 자체 해안선 기준' 상위 TOP_FRACTION 구간을 빨간 반투명 라인으로 표시한다.
- 구간 이름은 섬 중심 기준 8방위(북안·북동안·…)로 붙인다.
"""
import os
import json
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from . import config as C
from . import geodata as G
from . import accumulate as A

ISLANDS = {
    "gyodong": dict(name="교동도", center=(126.266, 37.786), radius_km=6.0, min_area_km2=10.0, margin_km=3.0,
                    labels=[("교동도", 126.266, 37.786, 17), ("석모도", 126.335, 37.722, 12), ("서검도", 126.233, 37.722, 10),
                            ("미법도", 126.266, 37.731, 9), ("강화도", 126.355, 37.775, 12), ("북한 연안", 126.21, 37.845, 10),
                            ("석모수로", 126.348, 37.752, 9), ("조강(한강하구)", 126.33, 37.835, 10)],
                    n_tracer=2000, scalebar_km=2, sigma_m=400.0, top_fraction=0.30, seg_km=1.5),
    "seogeom": dict(name="서검도", center=(126.233, 37.720), radius_km=2.5, min_area_km2=0.5, max_area_km2=5.0, margin_km=2.0,
                    labels=[("서검도", 126.233, 37.722, 17), ("미법도", 126.266, 37.733, 12), ("석모도", 126.305, 37.703, 12),
                            ("교동도", 126.25, 37.762, 12)],
                    n_tracer=1500, scalebar_km=1, sigma_m=250.0, top_fraction=0.30, seg_km=0.8),
}
SECTORS = ["북안", "북동안", "동안", "남동안", "남안", "남서안", "서안", "북서안"]


def find_island_polygons(polys, isl):
    """중심 좌표 근처(radius_km)이고 면적 조건을 만족하는 폴리곤."""
    out = []
    for lon, lat in polys:
        clon, clat = lon.mean(), lat.mean()
        d = np.hypot((clon - isl["center"][0]) * G.M_PER_DEG_LON, (clat - isl["center"][1]) * G.M_PER_DEG_LAT) / 1000
        area = abs(np.trapezoid(lat, lon)) * G.M_PER_DEG_LON * G.M_PER_DEG_LAT / 1e6
        if d <= isl["radius_km"] and area >= isl["min_area_km2"] and area <= isl.get("max_area_km2", 1e9):
            out.append((lon, lat))
    if not out:
        raise RuntimeError(f"{isl['name']} 폴리곤을 찾지 못했습니다")
    return out


def island_view(ipolys, margin_km):
    lon = np.concatenate([p[0] for p in ipolys]); lat = np.concatenate([p[1] for p in ipolys])
    mlon, mlat = margin_km * 1000 / G.M_PER_DEG_LON, margin_km * 1000 / G.M_PER_DEG_LAT
    return (max(C.LON_MIN, lon.min() - mlon), min(C.LON_MAX, lon.max() + mlon),
            max(C.LAT_MIN, lat.min() - mlat), min(C.LAT_MAX, lat.max() + mlat))


def crop_indices(grid, view):
    x0, y0 = G.lonlat_to_xy(view[0], view[2]); x1, y1 = G.lonlat_to_xy(view[1], view[3])
    j0, j1 = int(max(0, x0 // grid.dx)), int(min(grid.nx, x1 // grid.dx + 1))
    i0, i1 = int(max(0, y0 // grid.dx)), int(min(grid.ny, y1 // grid.dx + 1))
    return i0, i1, j0, j1


def island_coast_cells(dom, ipolys, radius_m=300.0):
    """섬 폴리곤 꼭짓점에서 radius_m 이내의 해안 셀."""
    g = dom["grid"]
    pts = np.column_stack(G.lonlat_to_xy(np.concatenate([p[0] for p in ipolys]), np.concatenate([p[1] for p in ipolys])))
    # 꼭짓점 사이를 보간해 촘촘하게
    dense = [pts]
    for a, b in zip(pts[:-1], pts[1:]):
        n = int(np.hypot(*(b - a)) // 50)
        if n > 1:
            dense.append(a + (b - a) * np.linspace(0, 1, n, endpoint=False)[1:, None])
    pts = np.vstack(dense)
    tree = cKDTree(pts)
    coast = dom["coast"]
    ci, cj = np.nonzero(coast)
    d, _ = tree.query(np.column_stack([g.x[cj], g.y[ci]]))
    m = np.zeros(g.shape, bool)
    m[ci[d <= radius_m], cj[d <= radius_m]] = True
    return m


def sector_of(lon, lat, center):
    ang = (np.degrees(np.arctan2((lon - center[0]) * G.M_PER_DEG_LON, (lat - center[1]) * G.M_PER_DEG_LAT)) + 360) % 360
    return SECTORS[int((ang + 22.5) // 45) % 8]


def _density_from_counts(dom, counts_on_coast, cmask, sigma_cells, window):
    """섬 해안 셀의 좌초 수 → 윈도(i0,i1,j0,j1) 안에서 평활된 밀도."""
    i0, i1, j0, j1 = window
    grid = np.zeros(dom["grid"].shape, np.float32)
    grid.ravel()[np.flatnonzero(dom["coast"].ravel())] = counts_on_coast
    grid[~cmask] = 0
    sub = grid[i0:i1, j0:j1]; msub = cmask[i0:i1, j0:j1].astype(np.float32)
    num = ndimage.gaussian_filter(sub, sigma_cells); den = ndimage.gaussian_filter(msub, sigma_cells)
    out = np.zeros_like(grid); out[i0:i1, j0:j1] = num / np.maximum(den, 1e-4)
    return out


def analyze_island(dom, res, key, save=True):
    isl = ISLANDS[key]
    g = dom["grid"]
    polys = G.get_coast_polygons()
    ipolys = find_island_polygons(polys, isl)
    view = island_view(ipolys, isl["margin_km"])
    win = crop_indices(g, view)
    cmask = island_coast_cells(dom, ipolys)
    sig = isl["sigma_m"] / g.dx
    dens = _density_from_counts(dom, res["beach_hist"][-1], cmask, sig, win)
    vv = A.coast_vertex_values(dom, ipolys, dens)
    allv = np.concatenate(vv)
    thr = float(np.quantile(allv, 1 - isl["top_fraction"])); vmax = float(allv.max()) if allv.max() > 0 else 1.0
    thr = max(thr, 1e-6)
    segs = A.hotspot_segments(ipolys, vv, thr, vmax, min_pts=2)
    # 긴 구간을 seg_km 단위로 재분할 + 8방위 이름
    out_segs = []
    for s in segs:
        for lo, la, v in A._split_long(s["lon"], s["lat"], np.full(len(s["lon"]), s["mean"], np.float32), isl["seg_km"]):
            out_segs.append(dict(lon=lo, lat=la, mean=float(v.mean()), level=float(v.mean() / vmax)))
    segs = out_segs
    center = (np.mean([p[0].mean() for p in ipolys]), np.mean([p[1].mean() for p in ipolys]))
    rank = {}
    for s in segs:
        clon, clat = float(np.mean(s["lon"])), float(np.mean(s["lat"]))
        s["name"] = f"{isl['name']} {sector_of(clon, clat, center)}"
        s["length_km"] = float(np.sum(np.hypot(np.diff(s["lon"]) * G.M_PER_DEG_LON, np.diff(s["lat"]) * G.M_PER_DEG_LAT))) / 1000
        e = rank.setdefault(s["name"], dict(name=s["name"], length_km=0.0, score=0.0, lon=0.0, lat=0.0, n=0))
        e["length_km"] += s["length_km"]; e["score"] += s["mean"] * max(s["length_km"], 0.1)
        e["lon"] += clon; e["lat"] += clat; e["n"] += 1
    rank = sorted(rank.values(), key=lambda e: -e["score"])
    for e in rank:
        e["lon"] /= e["n"]; e["lat"] /= e["n"]
    # 해상 체류 밀도 (화면 내)
    i0, i1, j0, j1 = win
    off = ndimage.gaussian_filter(res["float_density"].astype(np.float32), sig)[i0:i1, j0:j1]
    wsub = dom["water"][i0:i1, j0:j1]
    off_thr = float(np.quantile(off[wsub], 0.95)) if wsub.any() else 1e9
    # 스냅샷별 진행도
    seg_cells = [g.cell_index(*G.lonlat_to_xy(s["lon"], s["lat"])) for s in segs]
    prog = np.zeros((len(res["snap_t"]), len(segs)), np.float32)
    for k in range(len(res["snap_t"])):
        d = _density_from_counts(dom, res["beach_hist"][k], cmask, sig, win)
        for n, (i, j) in enumerate(seg_cells):
            prog[k, n] = d[i, j].mean()
    prog = np.clip(prog / np.maximum(prog[-1], 1e-6), 0, 1)
    an = dict(key=key, isl=isl, ipolys=ipolys, view=view, window=win, cmask=cmask, dens=dens, thr=thr, vmax=vmax,
              segs=segs, rank=rank, off_lon=g.x[j0:j1] / G.M_PER_DEG_LON + C.LON_MIN, off_lat=g.y[i0:i1] / G.M_PER_DEG_LAT + C.LAT_MIN,
              off_val=off, off_thr=off_thr, prog=prog, center=center,
              n_beached_island=float(res["beach_hist"][-1][cmask.ravel()[np.flatnonzero(dom["coast"].ravel())]].sum()))
    if save:
        with open(os.path.join(C.OUT_DIR, f"hotspots_{key}_ranked.json"), "w", encoding="utf-8") as f:
            json.dump([{k2: (round(v, 3) if isinstance(v, float) else v) for k2, v in e.items() if k2 != "n"} for e in rank],
                      f, ensure_ascii=False, indent=1)
        feats = [dict(type="Feature", properties=dict(name=s["name"], level=round(s["level"], 3), length_km=round(s["length_km"], 2)),
                      geometry=dict(type="LineString", coordinates=np.column_stack([s["lon"], s["lat"]]).round(5).tolist())) for s in segs]
        with open(os.path.join(C.OUT_DIR, f"hotspots_{key}.geojson"), "w", encoding="utf-8") as f:
            json.dump(dict(type="FeatureCollection", features=feats), f, ensure_ascii=False)
    return an
