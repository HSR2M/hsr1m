"""배경 지도.

1) fetch_satellite_basemap(): 인터넷이 되는 PC에서 위성영상 타일(Esri World Imagery 또는 EOX Sentinel-2 cloudless)을
   내려받아 등장방형(lon/lat) 격자로 재투영한 PNG(output/basemap_satellite.png)를 만든다.
2) render_stylized_basemap(): 위성영상을 받을 수 없을 때 GSHHG 해안선 + 수심 모형으로 위성풍 모식 지도를 그린다.
3) get_basemap(): 위 둘 중 존재하는 것을 (RGB 배열, extent) 로 돌려준다 (위성 우선).
"""
import os
import io
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from . import config as C
from . import geodata as G

SAT_PATH = os.path.join(C.OUT_DIR, "basemap_satellite.png")
STY_PATH = os.path.join(C.OUT_DIR, "basemap_stylized.png")

TILE_SOURCES = {
    # 저작권 표시: "Esri, Maxar, Earthstar Geographics, and the GIS User Community"
    "esri": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    # 저작권 표시: "Sentinel-2 cloudless by EOX IT Services GmbH (Contains modified Copernicus Sentinel data)"
    "eox": "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/{z}/{y}/{x}.jpg",
}


# ---------------------------------------------------------------- 웹 메르카토르 타일 수학
def _lonlat_to_tile_px(lon, lat, z):
    n = 2 ** z * 256
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(math.radians(lat)) + 1.0 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def _lonlat_to_tile_px_arr(lon, lat, z):
    n = 2 ** z * 256
    x = (lon + 180.0) / 360.0 * n
    latr = np.radians(lat)
    y = (1.0 - np.log(np.tan(latr) + 1.0 / np.cos(latr)) / np.pi) / 2.0 * n
    return x, y


DEFAULT_BBOX = (C.LON_MIN, C.LON_MAX, C.LAT_MIN, C.LAT_MAX)


def _out_h(out_w, bbox):
    return int(round(out_w * (bbox[3] - bbox[2]) * G.M_PER_DEG_LAT / ((bbox[1] - bbox[0]) * G.M_PER_DEG_LON)))


def stitch_and_reproject(tile_getter, z, out_w=2400, verbose=True, bbox=DEFAULT_BBOX):
    """tile_getter(z,x,y)->PIL.Image 로 타일을 받아 bbox(lon0,lon1,lat0,lat1)를 덮는 모자이크를 만들고 lon/lat 격자로 재투영."""
    x0, y0 = _lonlat_to_tile_px(bbox[0], bbox[3], z)
    x1, y1 = _lonlat_to_tile_px(bbox[1], bbox[2], z)
    tx0, ty0, tx1, ty1 = int(x0 // 256), int(y0 // 256), int(x1 // 256), int(y1 // 256)
    W, H = (tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256
    mosaic = Image.new("RGB", (W, H), (20, 40, 60))
    ntile = (tx1 - tx0 + 1) * (ty1 - ty0 + 1)
    k = 0
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            k += 1
            try:
                im = tile_getter(z, tx, ty)
                mosaic.paste(im.convert("RGB"), ((tx - tx0) * 256, (ty - ty0) * 256))
            except Exception as e:  # noqa
                if verbose:
                    print(f"  tile {z}/{tx}/{ty} 실패: {e}")
            if verbose and k % 20 == 0:
                print(f"  타일 {k}/{ntile}")
    arr = np.asarray(mosaic).astype(np.float32)
    # 출력 등장방형 격자
    out_h = _out_h(out_w, bbox)
    LON, LAT = _fine_lonlat(out_w, out_h, bbox)
    px, py = _lonlat_to_tile_px_arr(LON, LAT, z)
    px -= tx0 * 256; py -= ty0 * 256
    out = np.stack([ndimage.map_coordinates(arr[..., c], [py, px], order=1, mode="nearest") for c in range(3)], -1)
    return np.clip(out, 0, 255).astype(np.uint8)


def fetch_satellite_basemap(source="esri", zoom=12, out_w=2400, path=SAT_PATH, bbox=DEFAULT_BBOX):
    """인터넷 연결이 필요. 성공 시 PNG 저장 후 경로 반환. 섬 상세 지도는 zoom 14~15, bbox 지정."""
    import requests
    url = TILE_SOURCES[source]
    sess = requests.Session()
    sess.headers["User-Agent"] = "incheon-debris-sim/1.0 (educational marine debris simulation)"

    def getter(z, x, y):
        r = sess.get(url.format(z=z, x=x, y=y), timeout=30)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content))

    img = stitch_and_reproject(getter, zoom, out_w, bbox=bbox)
    Image.fromarray(img).save(path)
    print(f"[basemap] 위성 배경지도 저장: {path}  (출처: {source})")
    return path


# ---------------------------------------------------------------- 모식 지도
def _noise(shape, scales, rng):
    f = np.zeros(shape, np.float32)
    for s, a in scales:
        f += a * ndimage.gaussian_filter(rng.standard_normal(shape).astype(np.float32), s) * s
    return f / (np.abs(f).max() + 1e-9)


def _box_mask(LON, LAT, boxes):
    m = np.zeros(LON.shape, bool)
    for lon0, lon1, lat0, lat1 in boxes:
        m |= (LON > lon0) & (LON < lon1) & (LAT > lat0) & (LAT < lat1)
    return m


def _sample_grid(field, grid, LON, LAT, order=1):
    """모델 격자 field(ny,nx) 를 임의 lon/lat 점에서 보간 (상단=북쪽인 이미지 좌표계용)."""
    X, Y = G.lonlat_to_xy(LON, LAT)
    return ndimage.map_coordinates(field.astype(np.float32), [Y / grid.dx - 0.5, X / grid.dx - 0.5], order=order, mode="nearest")


def render_stylized_basemap(dom, out_w=2400, path=STY_PATH, seed=3, bbox=DEFAULT_BBOX):
    """GSHHG 해안선·수심 모형 기반의 위성영상풍 지도 (실제 위성영상 아님). bbox 로 섬 상세 지도도 생성."""
    rng = np.random.default_rng(seed)
    polys = G.get_coast_polygons()
    out_h = _out_h(out_w, bbox)
    lon0, lon1, lat0, lat1 = bbox
    # 육지 마스크 (PIL 폴리곤 래스터화, 상단 = 북쪽)
    im = Image.new("L", (out_w, out_h), 0)
    dr = ImageDraw.Draw(im)
    for lon, lat in polys:
        if lon.max() < lon0 or lon.min() > lon1 or lat.max() < lat0 or lat.min() > lat1:
            continue
        px = (lon - lon0) / (lon1 - lon0) * out_w
        py = (lat1 - lat) / (lat1 - lat0) * out_h
        dr.polygon(list(zip(px.tolist(), py.tolist())), fill=255)
    land = np.asarray(im) > 127
    g = dom["grid"]
    LON, LAT = _fine_lonlat(out_w, out_h, bbox)
    water_model = _sample_grid(dom["water"], g, LON, LAT) > 0.5
    land &= ~(water_model & G.river_regions_ll(LON, LAT))   # 하천 폭 보정을 지도에도 반영
    m_per_px = (lon1 - lon0) * G.M_PER_DEG_LON / out_w
    dist_w = ndimage.distance_transform_edt(~land) * m_per_px   # 물 셀 → 해안 거리
    dist_l = ndimage.distance_transform_edt(land) * m_per_px    # 육지 셀 → 해안 거리
    depth = np.clip(_sample_grid(dom["depth"], g, LON, LAT), 0, 40)
    px_scale = 48.0 / m_per_px   # 노이즈 스케일을 m 단위로 고정 (지역 지도 기준 48 m/px)

    img = np.zeros((out_h, out_w, 3), np.float32)
    n1 = _noise((out_h, out_w), [(3 * px_scale, 1.0), (12 * px_scale, 1.0), (40 * px_scale, 1.0)], rng)
    n2 = _noise((out_h, out_w), [(2 * px_scale, 1.0), (8 * px_scale, 1.0)], rng)
    # --- 바다: 탁한 연안수(경기만 특유의 황갈색 부유사) → 외해 청색
    shallow = np.array([96, 128, 138]); deep = np.array([14, 44, 78])
    f = np.clip(depth / 30.0, 0, 1)[..., None]
    sea = shallow * (1 - f) + deep * f
    sea = sea * (1 + 0.10 * n1[..., None]) + 6 * n2[..., None]
    # --- 갯벌: 해안 거리 < 폭 (지역별 폭 다름)
    flat_boxes = [(126.33, 126.55, 37.555, 37.64), (126.37, 126.55, 37.49, 37.57), (126.33, 126.43, 37.40, 37.52),
                  (126.56, 126.70, 37.31, 37.47), (126.50, 126.78, 37.22, 37.33), (126.42, 126.62, 37.74, 37.80),
                  (126.20, 126.34, 37.60, 37.70), (126.10, 126.30, 37.72, 37.86)]
    fw = np.where(_box_mask(LON, LAT, flat_boxes), 2300.0, 650.0)
    fw = ndimage.gaussian_filter(fw, 25 * px_scale) * (1 + 0.35 * n1)
    flat = (~land) & (dist_w < fw)
    edge = np.clip((fw - dist_w) / np.maximum(0.35 * fw, 1), 0, 1)
    mud = np.array([150, 138, 112]) * (1 + 0.12 * n2[..., None])
    sea = np.where(flat[..., None], sea * (1 - edge[..., None]) + mud * edge[..., None], sea)
    img[~land] = sea[~land]
    # --- 육지: 식생 녹색/갈색 혼합 + 능선 음영 + 도시 회색
    veg = np.array([78, 104, 60]); soil = np.array([128, 118, 86]); urban = np.array([150, 150, 146])
    mix = np.clip(0.5 + 0.9 * n1, 0, 1)[..., None]
    landc = veg * (1 - mix) + soil * mix
    elev = ndimage.gaussian_filter(np.clip(dist_l, 0, 6000) / 6000.0 * (1 + 0.8 * n1), 4 * px_scale)
    gy, gx = np.gradient(elev)
    shade = np.clip(1 + 6.0 * (gx - gy), 0.6, 1.4)[..., None]
    landc = landc * shade
    ub = ndimage.gaussian_filter(_box_mask(LON, LAT, [(126.60, 126.76, 37.40, 37.56), (126.62, 126.82, 37.57, 37.70),
                                                        (126.58, 126.68, 37.35, 37.42), (126.42, 126.50, 37.44, 37.50),
                                                        (126.80, 126.95, 37.45, 37.60)]).astype(np.float32), 70 * px_scale)
    ub = np.clip(0.75 * ub * (0.7 + 0.8 * n1 + 0.4 * n2), 0, 0.85)[..., None]
    landc = landc * (1 - ub) + urban * ub
    # 해안 가까운 육지는 약간 밝게(모래/제방)
    coastal = np.clip(1 - dist_l / 250.0, 0, 1)[..., None]
    landc = landc * (1 - 0.35 * coastal) + np.array([170, 165, 140]) * 0.35 * coastal
    img[land] = landc[land]
    img = np.clip(img, 0, 255).astype(np.uint8)
    Image.fromarray(img).save(path)
    print(f"[basemap] 모식 배경지도 저장: {path}")
    return path


def _fine_lonlat(out_w, out_h, bbox=DEFAULT_BBOX):
    lon = bbox[0] + (np.arange(out_w) + 0.5) / out_w * (bbox[1] - bbox[0])
    lat = bbox[3] - (np.arange(out_h) + 0.5) / out_h * (bbox[3] - bbox[2])
    return np.meshgrid(lon, lat)


def get_basemap(dom=None, prefer_satellite=True, bbox=None, tag=None, out_w=2400):
    """(RGB uint8 배열, bbox, 출처 문자열). bbox/tag 를 주면 해당 영역(섬) 전용 지도 파일을 사용/생성."""
    bbox = tuple(bbox) if bbox is not None else DEFAULT_BBOX
    sat = SAT_PATH if tag is None else os.path.join(C.OUT_DIR, f"basemap_satellite_{tag}.png")
    sty = STY_PATH if tag is None else os.path.join(C.OUT_DIR, f"basemap_stylized_{tag}.png")
    if prefer_satellite and os.path.exists(sat):
        return np.asarray(Image.open(sat).convert("RGB")), bbox, "위성영상 (Esri World Imagery / EOX Sentinel-2 cloudless)"
    if not os.path.exists(sty):
        if dom is None:
            dom = G.build_domain(verbose=False)
        render_stylized_basemap(dom, out_w=out_w, path=sty, bbox=bbox)
    return np.asarray(Image.open(sty).convert("RGB")), bbox, "GSHHG 해안선 기반 모식도 (위성영상 대체)"
