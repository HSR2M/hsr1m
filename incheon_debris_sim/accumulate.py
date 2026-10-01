"""쓰레기 집적 지점 산정.

A. 해안 집적(beaching) 밀도: 좌초 입자 수를 해안을 따라 가우시안 평활(σ≈1 km)한 '해안 1 km 당 좌초 입자 수'
   → 상위 구간을 빨간 반투명 라인으로 표시.
B. 해상 체류 밀도: 마지막 15일 동안 부유 입자 밀도의 시간평균 → 상위 5 % 등고선(해상 수렴역, 점선).
C. 오일러 잔차류 수렴: 조석 2주기 동안의 라그랑주 잔차류 u_res 의 발산 ∇·u_res < 0 인 곳 (물리적 근거 보조 자료).
"""
import os
import json
import numpy as np
from scipy import ndimage

from . import config as C
from . import geodata as G

SIGMA_CELLS = 5          # 평활 반경 (셀) → 1 km
TOP_FRACTION = 0.15      # 해안선 중 상위 15 % 를 '집적 예상 구간'으로 표시
MIN_SEG_PTS = 4


MAX_SEG_KM = 6.0         # 구간 분할 길이 (지명 부여·투명도 산정 단위)


def sea_coast(dom):
    """분석 대상 해안 셀: 하천(한강·임진강 하류) 제방 구간 제외."""
    return dom["coast"] & ~G.river_regions(dom["grid"])


def coast_density_grid(dom, counts_on_coast, sigma=SIGMA_CELLS):
    """해안 셀별 좌초 수 → 전체 격자에서 평활된 '해안 셀 당 밀도' (해안 아닌 곳은 외삽값)."""
    coast = dom["coast"]
    grid = np.zeros(dom["grid"].shape, np.float32)
    grid.ravel()[np.flatnonzero(coast.ravel())] = counts_on_coast
    keep = sea_coast(dom)
    grid[~keep] = 0.0
    num = ndimage.gaussian_filter(grid, sigma)
    den = ndimage.gaussian_filter(keep.astype(np.float32), sigma)
    return num / np.maximum(den, 1e-4)


def coast_vertex_values(dom, polys, dens):
    """GSHHG 해안선 꼭짓점마다 가장 가까운 격자 셀의 밀도값."""
    g = dom["grid"]
    out = []
    for lon, lat in polys:
        x, y = G.lonlat_to_xy(lon, lat)
        i, j = g.cell_index(x, y)
        v = np.zeros(len(lon), np.float32)
        ok = i >= 0
        v[ok] = dens[i[ok], j[ok]]
        v[G.river_regions_ll(lon, lat)] = 0.0
        out.append(v)
    return out


def _split_long(lon, lat, v, max_km=MAX_SEG_KM):
    """긴 구간을 max_km 단위로 분할."""
    d = np.hypot(np.diff(lon) * G.M_PER_DEG_LON, np.diff(lat) * G.M_PER_DEG_LAT) / 1000
    cum = np.r_[0, np.cumsum(d)]
    nparts = max(1, int(np.ceil(cum[-1] / max_km)))
    edges = np.linspace(0, cum[-1], nparts + 1)
    for a, b in zip(edges[:-1], edges[1:]):
        m = (cum >= a) & (cum <= b + 1e-9)
        if m.sum() >= 2:
            yield lon[m], lat[m], v[m]


def hotspot_threshold(dom, dens, top_fraction=TOP_FRACTION):
    vals = dens[sea_coast(dom)]
    return float(np.quantile(vals, 1 - top_fraction)), float(vals.max())


def hotspot_segments(polys, vertex_vals, thr, vmax, min_pts=MIN_SEG_PTS):
    """임계값 이상인 연속 꼭짓점 구간 → [{'lon','lat','level','mean'}...] (level = 0~1)."""
    segs = []
    for (lon, lat), v in zip(polys, vertex_vals):
        mark = v >= thr
        if not mark.any():
            continue
        # 폴리곤은 닫힌 고리: 시작점이 표시된 경우 회전시켜 연속 구간이 끊기지 않게 함
        if mark.all():
            for lo, la, vv in _split_long(lon, lat, v):
                segs.append(dict(lon=lo, lat=la, mean=float(vv.mean()), level=float(vv.mean() / vmax)))
            continue
        start = np.argmin(mark)      # 첫 번째 False
        mark_r = np.roll(mark, -start); lon_r = np.roll(lon, -start); lat_r = np.roll(lat, -start); v_r = np.roll(v, -start)
        d = np.diff(np.r_[0, mark_r.astype(int), 0])
        for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
            if b - a >= min_pts:
                for lo, la, vv in _split_long(lon_r[a:b], lat_r[a:b], v_r[a:b]):
                    segs.append(dict(lon=lo, lat=la, mean=float(vv.mean()), level=float(vv.mean() / vmax)))
    return segs


def name_segments(segs):
    """구간 중심에 가장 가까운 지명 부여 후, 지명별 합산 순위."""
    names = {}
    for s in segs:
        clon, clat = float(np.mean(s["lon"])), float(np.mean(s["lat"]))
        best = min(C.COAST_PLACES, key=lambda p: (p[1] - clon) ** 2 + ((p[2] - clat) * 1.26) ** 2)
        d = np.hypot((best[1] - clon) * G.M_PER_DEG_LON, (best[2] - clat) * G.M_PER_DEG_LAT)
        s["name"] = best[0] if d < 9000 else f"({clon:.2f}E, {clat:.2f}N)"
        length_km = float(np.sum(np.hypot(np.diff(s["lon"]) * G.M_PER_DEG_LON, np.diff(s["lat"]) * G.M_PER_DEG_LAT))) / 1000
        s["length_km"] = length_km
        e = names.setdefault(s["name"], dict(name=s["name"], length_km=0.0, score=0.0, lon=0.0, lat=0.0, n=0))
        e["length_km"] += length_km; e["score"] += s["mean"] * max(length_km, 0.2)
        e["lon"] += clon; e["lat"] += clat; e["n"] += 1
    rank = sorted(names.values(), key=lambda e: -e["score"])
    for e in rank:
        e["lon"] /= e["n"]; e["lat"] /= e["n"]
    return rank


def offshore_density(float_density, sigma=SIGMA_CELLS):
    return ndimage.gaussian_filter(float_density.astype(np.float32), sigma)


def residual_convergence(dom, model, t0=0.0, cycles=2, dt=300.0):
    """라그랑주 잔차류: 모든 물 셀에서 출발한 추적자의 조석 2주기 순변위 / 시간. 수렴 = -div."""
    from .currents import bilinear
    g = dom["grid"]; w = dom["water"]
    X, Y = g.X[w].astype(np.float64), g.Y[w].astype(np.float64)
    x, y = X.copy(), Y.copy()
    T = cycles * C.M2_PERIOD
    n = int(round(T / dt))
    uv0 = model.velocity(t0)
    for k in range(n):
        t = t0 + k * dt
        uv1 = model.velocity(t + 0.5 * dt); uv2 = model.velocity(t + dt)
        k1 = (bilinear(uv0[0], x, y, g.dx), bilinear(uv0[1], x, y, g.dx))
        k2 = (bilinear(uv1[0], x + .5 * dt * k1[0], y + .5 * dt * k1[1], g.dx), bilinear(uv1[1], x + .5 * dt * k1[0], y + .5 * dt * k1[1], g.dx))
        k3 = (bilinear(uv1[0], x + .5 * dt * k2[0], y + .5 * dt * k2[1], g.dx), bilinear(uv1[1], x + .5 * dt * k2[0], y + .5 * dt * k2[1], g.dx))
        k4 = (bilinear(uv2[0], x + dt * k3[0], y + dt * k3[1], g.dx), bilinear(uv2[1], x + dt * k3[0], y + dt * k3[1], g.dx))
        x = x + dt * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]) / 6
        y = y + dt * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]) / 6
        uv0 = uv2
    ures = np.zeros(g.shape, np.float32); vres = np.zeros(g.shape, np.float32)
    ures[w] = (x - X) / T; vres[w] = (y - Y) / T
    # 개방경계(서·남) 6 km 이내와 영역을 벗어난 추적자는 경계조건의 영향이라 제외
    near_bnd = (g.X < 6000) | (g.Y < 6000)
    left = np.zeros(g.shape, bool); left[w] = (x < 0) | (y < 0) | (x > g.nx * g.dx) | (y > g.ny * g.dx)
    bad = near_bnd | left
    ures[bad] = 0; vres[bad] = 0
    us = ndimage.gaussian_filter(ures, 2); vs = ndimage.gaussian_filter(vres, 2)
    div = (np.gradient(us, g.dx, axis=1) + np.gradient(vs, g.dx, axis=0))
    # 해안 800 m 이내는 격자 경계 효과(유속 0)로 생기는 가짜 수렴이라 제외
    div[~w | bad | (dom["dist"] < 800)] = np.nan
    ures[bad] = np.nan; vres[bad] = np.nan
    return ures, vres, div


def analyze(dom, res, model=None, save=True):
    polys = G.get_coast_polygons()
    final_counts = res["beach_hist"][-1]
    dens = coast_density_grid(dom, final_counts)
    thr, vmax = hotspot_threshold(dom, dens)
    vv = coast_vertex_values(dom, polys, dens)
    segs = hotspot_segments(polys, vv, thr, vmax)
    rank = name_segments(segs)
    off = offshore_density(res["float_density"])
    out = dict(dens=dens, thr=thr, vmax=vmax, segs=segs, rank=rank, offshore=off,
               offshore_thr=float(np.quantile(off[dom["water"]], 0.95)))
    if model is not None:
        ures, vres, div = residual_convergence(dom, model)
        out.update(ures=ures, vres=vres, div=div)
    if save:
        with open(os.path.join(C.OUT_DIR, "hotspots_ranked.json"), "w", encoding="utf-8") as f:
            json.dump([{k: (round(v, 3) if isinstance(v, float) else v) for k, v in e.items() if k != "n"} for e in rank],
                      f, ensure_ascii=False, indent=1)
        feats = [dict(type="Feature", properties=dict(name=s["name"], level=round(s["level"], 3), length_km=round(s["length_km"], 2)),
                      geometry=dict(type="LineString", coordinates=np.column_stack([s["lon"], s["lat"]]).round(5).tolist()))
                 for s in segs]
        with open(os.path.join(C.OUT_DIR, "hotspots.geojson"), "w", encoding="utf-8") as f:
            json.dump(dict(type="FeatureCollection", features=feats), f, ensure_ascii=False)
    return out
