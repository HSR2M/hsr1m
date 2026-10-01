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

TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

# 섬 프리셋: (중심 위도, 중심 경도, 줌 레벨, 중심 타일 기준 ±span 타일)
ISLANDS = {
    # 월미도: z15 3x3 타일 ≈ 2.9 km x 2.9 km, 3.8 m/px (월미산 정상 약 108 m)
    "wolmido": dict(lat=37.4725, lon=126.5970, zoom=15, span=1),
    # 강화도: z12 3x3 타일 ≈ 23 km x 23 km, 30 m/px (마니산 472 m)
    "ganghwa": dict(lat=37.70, lon=126.45, zoom=12, span=1),
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

    @property
    def rows(self) -> int:
        return self.heights.shape[0]

    @property
    def cols(self) -> int:
        return self.heights.shape[1]

    def world_xy(self, ix: float, iy: float) -> tuple[float, float]:
        return (ix - (self.cols - 1) / 2) * self.mpp, (iy - (self.rows - 1) / 2) * self.mpp

    def pixel(self, x: float, y: float) -> tuple[int, int]:
        ix = int(round(x / self.mpp + (self.cols - 1) / 2))
        iy = int(round(y / self.mpp + (self.rows - 1) / 2))
        return min(max(ix, 0), self.cols - 1), min(max(iy, 0), self.rows - 1)

    def height_at(self, x: float, y: float) -> float:
        ix, iy = self.pixel(x, y)
        return float(self.heights[iy, ix])

    def peak(self) -> tuple[float, float, float]:
        iy, ix = np.unravel_index(int(np.argmax(self.heights)), self.heights.shape)
        x, y = self.world_xy(ix, iy)
        return x, y, float(self.heights[iy, ix])

    def extent_m(self) -> tuple[float, float]:
        return self.cols * self.mpp, self.rows * self.mpp


def load_dem(name: str, cache_dir: str = "tiles") -> Terrain:
    """프리셋 섬의 Terrarium 타일 모자이크를 내려받아 Terrain으로 만든다."""
    cfg = ISLANDS[name]
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


def hypsometric_texture(t: Terrain, path: str) -> str:
    """위성영상 대신 고도 기반 색상(바다=파랑, 저지=초록, 고지=갈색/흰색) 텍스처 PNG 생성."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    h = t.heights
    land = (h - 0.5) / max(h.max() - 0.5, 1.0)
    cmap = plt.get_cmap("terrain")
    tex = (cmap(0.25 + 0.75 * np.clip(land, 0, 1))[..., :3] * 255).astype(np.uint8)
    tex[h <= 0.5] = (30, 90, 160)
    Image.fromarray(np.flipud(tex)).save(path)
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
