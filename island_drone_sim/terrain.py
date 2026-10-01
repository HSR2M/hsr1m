"""실제 섬 지형(DEM)을 내려받아 PyBullet heightfield로 올리는 모듈.

고도 데이터 출처: AWS Open Data "Terrain Tiles" (Mapzen Terrarium PNG 타일, 무료, API 키 불필요)
  https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png
한국 지역은 SRTM/ALOS 계열 30 m급 자료가 바탕이다.

좌표계: 월드 x = 동쪽(+), y = 북쪽(+), z = 해발고도(m). 해수면 이하는 0 m로 자른다.
"""
from __future__ import annotations

import math
import os
import urllib.request
from dataclasses import dataclass

import numpy as np
import pybullet as p
from PIL import Image
from scipy import ndimage

TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

# 섬 프리셋: (중심 위도, 중심 경도, 줌 레벨, 중심 타일 기준 ±span 타일)
ISLANDS = {
    # 월미도: z15 3x3 타일 ≈ 2.9 km x 2.9 km, 3.8 m/px (월미산 정상 약 108 m)
    "wolmido": dict(lat=37.4725, lon=126.5970, zoom=15, span=1),
    # 강화도: z12 3x3 타일 ≈ 23 km x 23 km, 30 m/px (마니산 472 m)
    "ganghwa": dict(lat=37.70, lon=126.45, zoom=12, span=1),
    # 아래는 위경도 범위(bbox)로 잘라내는 프리셋. 섬 전체가 화면에 들어오도록 바다 여유를 포함한다.
    # 교동도: 강화도 서북쪽, 동서 10 km, 화개산 260 m. 동쪽 가장자리에 강화도 해안 일부 포함.
    # 범위 가장자리는 edge_fade로 바다에 잠기게 하므로 섬 주위에 3~4 km 여유를 둔다.
    # center: 선회 중심(위도, 경도), radius: 선회 반경(m). 간석지 때문에 육지 덩어리 자동 추출이 불안정해 명시한다.
    "gyodong": dict(bbox=(37.720, 37.850, 126.190, 126.390), zoom=13, center=(37.783, 126.283), radius=4300),
    # 서검도: 교동도 서남쪽의 작은 섬(약 1.5 km). 7.5 m/px(z14)로 받는다.
    "seogeom": dict(bbox=(37.715, 37.775, 126.185, 126.270), zoom=14, center=(37.745, 126.224), radius=1200),
    # 석모도: 강화도 서쪽, 해명산~상봉산 능선 300 m급. 3D로 가장 입체적.
    "seongmo": dict(bbox=(37.630, 37.790, 126.230, 126.420), zoom=13, center=(37.705, 126.325), radius=5000),
}


def tile_xy(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    n = 2 ** zoom
    r = math.radians(lat)
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(r) + 1.0 / math.cos(r)) / math.pi) / 2.0 * n)
    return x, y


def meters_per_pixel(lat: float, zoom: int) -> float:
    return 156543.03 * math.cos(math.radians(lat)) / 2 ** zoom


def _decode_terrarium(png_path: str) -> np.ndarray:
    im = np.asarray(Image.open(png_path).convert("RGB")).astype(np.float64)
    return im[..., 0] * 256.0 + im[..., 1] + im[..., 2] / 256.0 - 32768.0


@dataclass
class Terrain:
    name: str
    heights: np.ndarray      # (rows, cols), row 0 = 남쪽, col 0 = 서쪽, 단위 m
    mpp: float               # 픽셀당 미터
    lat: float
    lon: float
    zoom: int
    body_id: int = -1
    land: np.ndarray | None = None   # (rows, cols) bool, True=육지. None이면 heights<=0.5를 바다로 본다
    center_xy: tuple[float, float] | None = None   # 프리셋이 지정한 선회 중심(월드 좌표)
    orbit_radius: float | None = None              # 프리셋이 지정한 선회 반경(m)

    @property
    def rows(self) -> int:
        return self.heights.shape[0]

    @property
    def cols(self) -> int:
        return self.heights.shape[1]

    def latlon_to_xy(self, lat: float, lon: float) -> tuple[float, float]:
        """위경도 -> 월드 좌표(m). 지형 중심 기준 웹메르카토르 근사."""
        k = 156543.03 / 2 ** self.zoom * 256 / 360.0           # deg -> px (x)
        n = 2 ** self.zoom

        def merc_y(la):
            r = math.radians(la)
            return (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n * 256

        dx_px = (lon - self.lon) * n * 256 / 360.0
        dy_px = merc_y(self.lat) - merc_y(lat)                   # 북쪽이 +
        return dx_px * self.mpp, dy_px * self.mpp

    def world_xy(self, ix: float, iy: float) -> tuple[float, float]:
        return (ix - (self.cols - 1) / 2) * self.mpp, (iy - (self.rows - 1) / 2) * self.mpp

    def pixel(self, x: float, y: float) -> tuple[int, int]:
        ix = int(round(x / self.mpp + (self.cols - 1) / 2))
        iy = int(round(y / self.mpp + (self.rows - 1) / 2))
        return min(max(ix, 0), self.cols - 1), min(max(iy, 0), self.rows - 1)

    def height_at(self, x: float, y: float) -> float:
        ix, iy = self.pixel(x, y)
        return float(self.heights[iy, ix])

    def surface_z(self, x: float, y: float, client: int) -> float:
        """PyBullet heightfield의 실제 표면 높이(삼각형 보간)를 레이캐스트로 구한다.
        height_at()은 가장 가까운 픽셀 값이라 30 m/px 지형에서는 수 m~수십 m 어긋날 수 있다."""
        hit = p.rayTest([x, y, 10000.0], [x, y, -100.0], physicsClientId=client)[0]
        return float(hit[3][2]) if hit[0] == self.body_id else self.height_at(x, y)

    def sea_mask(self) -> np.ndarray:
        return ~self.land if self.land is not None else self.heights <= 0.5

    def land_centroid(self) -> tuple[float, float]:
        """가장 큰 육지 덩어리의 중심 월드 좌표 (섬 주위 선회 중심으로 사용)."""
        land = ~self.sea_mask()
        lab, n = ndimage.label(land)
        if n == 0:
            return 0.0, 0.0
        sizes = ndimage.sum(land, lab, range(1, n + 1))
        iy, ix = ndimage.center_of_mass(lab == (1 + int(np.argmax(sizes))))
        return self.world_xy(ix, iy)

    def land_extent_m(self) -> float:
        """가장 큰 육지 덩어리의 긴 변 길이(m)."""
        land = ~self.sea_mask()
        lab, n = ndimage.label(land)
        if n == 0:
            return max(self.extent_m())
        sizes = ndimage.sum(land, lab, range(1, n + 1))
        ys, xs = np.nonzero(lab == (1 + int(np.argmax(sizes))))
        return float(max(xs.max() - xs.min(), ys.max() - ys.min()) * self.mpp)

    def peak(self) -> tuple[float, float, float]:
        iy, ix = np.unravel_index(int(np.argmax(self.heights)), self.heights.shape)
        x, y = self.world_xy(ix, iy)
        return x, y, float(self.heights[iy, ix])

    def extent_m(self) -> tuple[float, float]:
        return self.cols * self.mpp, self.rows * self.mpp


def _fetch_tile(zoom: int, x: int, y: int, cache_dir: str) -> np.ndarray:
    f = os.path.join(cache_dir, f"t_{zoom}_{x}_{y}.png")
    if not os.path.exists(f):
        urllib.request.urlretrieve(TILE_URL.format(z=zoom, x=x, y=y), f)
    return _decode_terrarium(f)


def load_dem_bbox(lat0: float, lat1: float, lon0: float, lon1: float, zoom: int, cache_dir: str = "tiles",
                  name: str = "bbox", edge_fade_px: int = 35) -> Terrain:
    """위경도 범위를 덮는 타일을 받아 정확히 그 범위로 잘라낸 Terrain. 바다(<=0 m)는 0 m, land 마스크 포함.
    edge_fade_px: 범위 가장자리에서 이 폭만큼 고도를 0으로 서서히 낮춰(바다로 잠기게) 절단면 절벽을 없앤다."""
    os.makedirs(cache_dir, exist_ok=True)
    n = 2 ** zoom
    x0, y1 = tile_xy(lat0, lon0, zoom)
    x1, y0 = tile_xy(lat1, lon1, zoom)
    rows = [np.hstack([_fetch_tile(zoom, x, y, cache_dir) for x in range(x0, x1 + 1)]) for y in range(y0, y1 + 1)]
    h = np.vstack(rows)                                     # row 0 = 북쪽

    def px(lat, lon):
        r = math.radians(lat)
        return ((lon + 180.0) / 360.0 * n - x0) * 256, ((1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n - y0) * 256

    cx0, cy0 = px(lat1, lon0)                               # 좌상(북서)
    cx1, cy1 = px(lat0, lon1)                               # 우하(남동)
    h = h[int(cy0):int(cy1), int(cx0):int(cx1)]
    # 해안선 정리: 평활 -> 가는 돌기 제거 -> 작은 조각(바다 위 잡음) 제거 -> 내부 구멍 메움
    # 간석지에서는 0~0.5 m 값이 해안을 따라 줄무늬로 나타나므로 0.5 m 이상만 육지로 본다
    land = ndimage.gaussian_filter((h > 0.5).astype(float), 2.0) > 0.5
    land = ndimage.binary_opening(land, structure=np.ones((3, 3)))
    lab, n = ndimage.label(land)
    if n:
        sizes = ndimage.sum(land, lab, range(1, n + 1))
        land = np.isin(lab, 1 + np.where(sizes >= 300)[0])
    land = ndimage.binary_fill_holes(land)
    h = np.where(land, np.maximum(h, 0.0), 0.0)
    if edge_fade_px > 0:
        ry, rx = np.arange(h.shape[0]), np.arange(h.shape[1])
        dy = np.minimum(ry, ry[::-1])[:, None]
        dx = np.minimum(rx, rx[::-1])[None, :]
        ramp = np.clip(np.minimum(dy, dx) / edge_fade_px, 0, 1)
        ramp = ramp * ramp * (3 - 2 * ramp)
        h = h * ramp
        land = land & (ramp > 0.5)
    lat_c, lon_c = (lat0 + lat1) / 2, (lon0 + lon1) / 2
    return Terrain(name, np.flipud(h), meters_per_pixel(lat_c, zoom), lat_c, lon_c, zoom, land=np.flipud(land))


def load_dem(name: str, cache_dir: str = "tiles") -> Terrain:
    """프리셋 섬의 Terrarium 타일 모자이크를 내려받아 Terrain으로 만든다."""
    cfg = ISLANDS[name]
    if "bbox" in cfg:
        t = load_dem_bbox(*cfg["bbox"], cfg["zoom"], cache_dir, name=name)
        if "center" in cfg:
            t.center_xy = t.latlon_to_xy(*cfg["center"])
        t.orbit_radius = cfg.get("radius")
        return t
    lat, lon, zoom, span = cfg["lat"], cfg["lon"], cfg["zoom"], cfg["span"]
    os.makedirs(cache_dir, exist_ok=True)
    cx, cy = tile_xy(lat, lon, zoom)
    rows = []
    for dy in range(-span, span + 1):          # 북쪽(작은 y) -> 남쪽
        row = []
        for dx in range(-span, span + 1):      # 서쪽 -> 동쪽
            x, y = cx + dx, cy + dy
            f = os.path.join(cache_dir, f"t_{zoom}_{x}_{y}.png")
            if not os.path.exists(f):
                urllib.request.urlretrieve(TILE_URL.format(z=zoom, x=x, y=y), f)
            row.append(_decode_terrarium(f))
        rows.append(np.hstack(row))
    h = np.vstack(rows)
    h = np.clip(h, 0.0, None)                   # 바다/노이즈 -> 해수면 0 m
    h = np.flipud(h)                            # row 0 = 남쪽 (PyBullet +y = 북쪽)
    return Terrain(name, h, meters_per_pixel(lat, zoom), lat, lon, zoom)


def hillshade(h: np.ndarray, mpp: float, azimuth_deg: float = 315.0, altitude_deg: float = 45.0) -> np.ndarray:
    """0~1 음영. 북서쪽 태양 기준 표준 hillshade."""
    dzdy, dzdx = np.gradient(h, mpp)
    slope = np.arctan(np.hypot(dzdx, dzdy))
    aspect = np.arctan2(-dzdx, dzdy)
    az, alt = np.radians(azimuth_deg), np.radians(altitude_deg)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(shade, 0, 1)


def hypsometric_texture(t: Terrain, path: str, shade: bool = True, coast_m: float = 400.0) -> str:
    """위성영상 대신 고도 기반 색상 텍스처 PNG 생성.
    육지: 초록(저지)->갈색/흰색(고지) + hillshade 음영. 바다: 해안에서 coast_m까지 얕은 물빛 -> 짙은 남색."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    h = t.heights
    sea = t.sea_mask()
    land = h / max(h.max(), 1.0)
    cmap = plt.get_cmap("terrain")
    tex = cmap(0.25 + 0.75 * np.clip(land, 0, 1))[..., :3]
    if shade:
        s = hillshade(h, t.mpp)
        tex = tex * (0.55 + 0.45 * s)[..., None]
    dist = ndimage.distance_transform_edt(sea) * t.mpp
    w = np.clip(dist / coast_m, 0, 1)[..., None]
    shallow, deep = np.array([0.30, 0.56, 0.72]), np.array([0.10, 0.28, 0.55])
    tex[sea] = (shallow * (1 - w) + deep * w)[sea]
    tex = (tex * 255).astype(np.uint8)
    # PyBullet heightfield의 UV는 (i=0, j=0)이 이미지의 오른쪽 아래에 오도록 매핑된다.
    # heights는 row 0 = 남쪽, col 0 = 서쪽이므로 좌우만 뒤집어 저장해야 지오메트리와 일치한다
    # (위에서 내려본 렌더와 텍스처의 상관계수로 검증: 0.97).
    Image.fromarray(np.fliplr(tex)).save(path)
    return path


def add_terrain_to_pybullet(t: Terrain, client: int, texture_path: str | None = None) -> int:
    """Terrain을 PyBullet heightfield 강체(질량 0)로 추가하고 body id를 돌려준다."""
    h = t.heights
    data = h.flatten(order="C").tolist()        # index = ix + iy * cols  (PyBullet: i + j * numRows)
    shape = p.createCollisionShape(
        p.GEOM_HEIGHTFIELD,
        meshScale=[t.mpp, t.mpp, 1.0],
        heightfieldData=data,
        numHeightfieldRows=t.cols,
        numHeightfieldColumns=t.rows,
        physicsClientId=client,
    )
    body = p.createMultiBody(0, shape, physicsClientId=client)
    # Bullet은 heightfield를 (min+max)/2 높이에 중심을 두므로 최저점이 z=0(해수면)이 되도록 올린다.
    p.resetBasePositionAndOrientation(body, [0, 0, (h.max() + h.min()) / 2], [0, 0, 0, 1], physicsClientId=client)
    if texture_path:
        tid = p.loadTexture(texture_path, physicsClientId=client)
        p.changeVisualShape(body, -1, textureUniqueId=tid, rgbaColor=[1, 1, 1, 1], physicsClientId=client)
    else:
        p.changeVisualShape(body, -1, rgbaColor=[0.45, 0.6, 0.35, 1], physicsClientId=client)
    t.body_id = body
    return body


def verify_terrain(t: Terrain, client: int, n: int = 200, seed: int = 0) -> float:
    """무작위 지점에서 레이캐스트 높이와 DEM 값을 비교해 최대 오차(m)를 돌려준다."""
    rng = np.random.default_rng(seed)
    worst = 0.0
    for ix, iy in rng.integers(2, min(t.cols, t.rows) - 2, size=(n, 2)):
        x, y = t.world_xy(ix, iy)
        hit = p.rayTest([x, y, 5000], [x, y, -50], physicsClientId=client)[0]
        worst = max(worst, abs(hit[3][2] - t.heights[iy, ix]))
    return worst
