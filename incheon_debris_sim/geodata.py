"""지형 데이터: GSHHG 해안선(basemap-data-hires) → 격자, 육지마스크, 해안거리, 수심 모형.

실측 수심(GEBCO/국립해양조사원 수치해도)이 있으면 `load_external_depth()`로 교체할 수 있다.
"""
import os
import pickle
import numpy as np
from scipy import ndimage
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from matplotlib.path import Path

from . import config as C

COAST_CACHE = os.path.join(C.DATA_DIR, "coast_polygons_gshhs_f.pkl")

# ---------------------------------------------------------------- 좌표 변환
M_PER_DEG_LAT = 111_000.0
M_PER_DEG_LON = 111_320.0 * np.cos(np.radians(C.LAT0))


def lonlat_to_xy(lon, lat):
    return (np.asarray(lon) - C.LON_MIN) * M_PER_DEG_LON, (np.asarray(lat) - C.LAT_MIN) * M_PER_DEG_LAT


def xy_to_lonlat(x, y):
    return np.asarray(x) / M_PER_DEG_LON + C.LON_MIN, np.asarray(y) / M_PER_DEG_LAT + C.LAT_MIN


# ---------------------------------------------------------------- 해안선
def get_coast_polygons(margin=0.15):
    """GSHHG 전해상도('f') 해안 폴리곤 [(lon array, lat array), ...] (육지 폴리곤만)."""
    if os.path.exists(COAST_CACHE):
        with open(COAST_CACHE, "rb") as f:
            return pickle.load(f)
    from mpl_toolkits.basemap import Basemap  # 느림(~1분), 결과를 캐시
    m = Basemap(projection="cyl", llcrnrlon=C.LON_MIN - margin, llcrnrlat=C.LAT_MIN - margin,
                urcrnrlon=C.LON_MAX + margin, urcrnrlat=C.LAT_MAX + margin, resolution="f")
    polys = [(np.asarray(x), np.asarray(y)) for (x, y), t in zip(m.coastpolygons, m.coastpolygontypes) if t == 1]
    with open(COAST_CACHE, "wb") as f:
        pickle.dump(polys, f)
    return polys


# ---------------------------------------------------------------- 격자
class Grid:
    def __init__(self, dx=C.DX):
        self.dx = dx
        W, H = lonlat_to_xy(C.LON_MAX, C.LAT_MAX)
        self.nx, self.ny = int(round(W / dx)), int(round(H / dx))
        self.x = (np.arange(self.nx) + 0.5) * dx    # 셀 중심
        self.y = (np.arange(self.ny) + 0.5) * dx
        self.X, self.Y = np.meshgrid(self.x, self.y)
        self.LON, self.LAT = xy_to_lonlat(self.X, self.Y)
        self.extent = [C.LON_MIN, C.LON_MAX, C.LAT_MIN, C.LAT_MAX]

    @property
    def shape(self):
        return (self.ny, self.nx)

    def cell_index(self, x, y):
        """좌표(m) → (row, col). 영역 밖은 -1."""
        i = np.floor(np.asarray(y) / self.dx).astype(int)
        j = np.floor(np.asarray(x) / self.dx).astype(int)
        bad = (i < 0) | (i >= self.ny) | (j < 0) | (j >= self.nx)
        i = np.where(bad, -1, i)
        j = np.where(bad, -1, j)
        return i, j


def rasterize_land(grid, polys):
    pts = np.column_stack([grid.LON.ravel(), grid.LAT.ravel()])
    land = np.zeros(grid.nx * grid.ny, dtype=bool)
    for lon, lat in polys:
        if lon.max() < C.LON_MIN or lon.min() > C.LON_MAX or lat.max() < C.LAT_MIN or lat.min() > C.LAT_MAX:
            continue
        land |= Path(np.column_stack([lon, lat])).contains_points(pts)
    return land.reshape(grid.shape)


def _carve_channels(grid, land, half_width_m=250.0):
    """주요 수로 중심선을 따라 격자 해상도 때문에 막힌 수로를 열어 준다 (폭 2*half_width)."""
    X, Y = grid.X, grid.Y
    carved = np.zeros_like(land)
    for pts in C.CHANNELS.values():
        xs, ys = lonlat_to_xy(*np.array(pts).T)
        for (x0, y0, x1, y1) in zip(xs[:-1], ys[:-1], xs[1:], ys[1:]):
            d = _dist_to_segment(X, Y, x0, y0, x1, y1)
            carved |= d < half_width_m
    return land & ~carved


def river_regions(grid):
    """한강(김포~행주)·임진강 하류 구간 (GSHHG 에서는 1~2셀 폭의 선으로만 표현되어 보정 필요)."""
    return river_regions_ll(grid.LON, grid.LAT)


def river_regions_ll(LON, LAT):
    han = (LON > 126.58) & (LAT > 37.48) & (LAT < 37.80) & (LON - 126.58 > (37.80 - LAT) * 0.2)
    imjin = (LON > 126.60) & (LON < 126.82) & (LAT > 37.78)
    return han | imjin


def _widen_rivers(grid, land, widen_m=400.0):
    """하천 구간의 물 셀을 양쪽으로 widen_m 만큼 확장 (실제 한강 하류 폭 ~1 km, 수심 5 m 이상)."""
    region = river_regions(grid)
    water = ~land
    cells = max(1, int(round(widen_m / grid.dx)))
    wide = ndimage.binary_dilation(water & region, iterations=cells) & region
    return land & ~wide


def _dist_to_segment(X, Y, x0, y0, x1, y1):
    vx, vy = x1 - x0, y1 - y0
    L2 = vx * vx + vy * vy
    t = np.clip(((X - x0) * vx + (Y - y0) * vy) / L2, 0, 1)
    return np.hypot(X - (x0 + t * vx), Y - (y0 + t * vy))


def water_connected_to_sea(water):
    """서쪽·남쪽 경계에서 연결된 물만 남긴다 (고립 호수 → 육지 취급)."""
    lab, n = ndimage.label(water)
    keep = set(lab[:, 0][water[:, 0]]) | set(lab[0, :][water[0, :]])
    keep.discard(0)
    return np.isin(lab, list(keep))


def build_domain(dx=C.DX, verbose=True):
    """격자 + 마스크 + 수심 + 조석 위상/진폭 보조장 생성 (캐시)."""
    cache = os.path.join(C.DATA_DIR, f"domain_dx{int(dx)}.npz")
    if os.path.exists(cache):
        d = dict(np.load(cache))
        grid = Grid(dx)
        d["grid"] = grid
        return d
    grid = Grid(dx)
    polys = get_coast_polygons()
    land = rasterize_land(grid, polys)
    land = _carve_channels(grid, land)
    land = _widen_rivers(grid, land)
    water = water_connected_to_sea(~land)
    land = ~water
    # 해안 거리 (물 셀에서 가장 가까운 육지까지, m)
    dist = ndimage.distance_transform_edt(water) * dx
    depth = synthetic_depth(grid, dist)
    depth[land] = 0.0
    # 개방 경계: 서쪽(열 0)·남쪽(행 0)의 물 셀
    open_bnd = np.zeros(grid.shape, bool)
    open_bnd[:, 0] = water[:, 0]
    open_bnd[0, :] = water[0, :]
    # 조석 전파 시간 (개방경계에서 얕은물 파속으로 Dijkstra)
    travel = tidal_travel_time(grid, water, depth, open_bnd)
    # 해안 셀 (육지에 인접한 물 셀)
    coast = water & ndimage.binary_dilation(land, structure=np.ones((3, 3)))
    d = dict(land=land, water=water, dist=dist, depth=depth, open_bnd=open_bnd, travel=travel, coast=coast)
    np.savez_compressed(cache, **d)
    d["grid"] = grid
    if verbose:
        print(f"[geodata] grid {grid.ny}x{grid.nx} @ {dx:.0f} m, water cells {water.sum()}, coast cells {coast.sum()}")
    return d


def synthetic_depth(grid, dist):
    """해안거리 기반 수심 모형 + 서쪽으로 갈수록 깊어짐 + 주요 수로 최소수심 보장."""
    h = C.DEPTH_MIN + (C.DEPTH_MAX - C.DEPTH_MIN) * (1.0 - np.exp(-dist / C.DEPTH_SCALE))
    west = (C.LON_MAX - grid.LON) / (C.LON_MAX - C.LON_MIN)   # 0(동) ~ 1(서)
    h = h * (0.75 + 0.5 * west)
    X, Y = grid.X, grid.Y
    for pts in C.CHANNELS.values():
        xs, ys = lonlat_to_xy(*np.array(pts).T)
        dmin = np.full(grid.shape, np.inf)
        for (x0, y0, x1, y1) in zip(xs[:-1], ys[:-1], xs[1:], ys[1:]):
            dmin = np.minimum(dmin, _dist_to_segment(X, Y, x0, y0, x1, y1))
        boost = C.CHANNEL_DEPTH * np.exp(-(dmin / 900.0) ** 2)
        h = np.maximum(h, boost)
    h = np.where(river_regions(grid), np.maximum(h, C.RIVER_DEPTH), h)
    return h


def tidal_travel_time(grid, water, depth, open_bnd):
    """얕은물 파속 c=sqrt(g h)로 개방경계로부터의 최소 전파시간(s)을 계산 (조석 위상장용)."""
    ny, nx = grid.shape
    idx = -np.ones(grid.shape, int)
    wi = np.flatnonzero(water.ravel())
    idx.ravel()[wi] = np.arange(len(wi))
    c = np.sqrt(9.81 * np.maximum(depth, 1.0))
    rows, cols, w = [], [], []
    for di, dj in ((0, 1), (1, 0)):
        a = idx[: ny - di, : nx - dj]
        b = idx[di:, dj:]
        ok = (a >= 0) & (b >= 0)
        cm = 0.5 * (c[: ny - di, : nx - dj] + c[di:, dj:])
        rows.append(a[ok]); cols.append(b[ok]); w.append(grid.dx / cm[ok])
    rows, cols, w = map(np.concatenate, (rows, cols, w))
    n = len(wi)
    G = csr_matrix((np.r_[w, w], (np.r_[rows, cols], np.r_[cols, rows])), shape=(n, n))
    src = idx[open_bnd]
    src = src[src >= 0]
    t = dijkstra(G, directed=False, indices=src, min_only=True)
    travel = np.full(grid.shape, np.nan)
    travel.ravel()[wi] = t
    return travel


def load_external_depth(path, grid, varname="elevation"):
    """GEBCO 등 NetCDF 수심(음수=바다)을 격자에 보간. netCDF4 필요."""
    import netCDF4
    from scipy.interpolate import RegularGridInterpolator
    ds = netCDF4.Dataset(path)
    lat = ds.variables["lat"][:]
    lon = ds.variables["lon"][:]
    z = ds.variables[varname][:]
    f = RegularGridInterpolator((lat, lon), z, bounds_error=False, fill_value=np.nan)
    zi = f(np.column_stack([grid.LAT.ravel(), grid.LON.ravel()])).reshape(grid.shape)
    return np.clip(-zi, C.DEPTH_MIN, None)


if __name__ == "__main__":
    d = build_domain()
    print("depth stats (water):", np.percentile(d["depth"][d["water"]], [5, 50, 95]))
    print("travel time (h) max:", np.nanmax(d["travel"]) / 3600)
