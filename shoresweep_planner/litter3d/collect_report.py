"""수거 계획 → 작업자용 지도·작업 지시서 (인터랙티브 HTML + 인쇄용 PNG).

  build_collect_html()  한 장짜리 HTML 앱 (assets/app.js · app.css · Leaflet 을 전부 안에 넣어 인터넷 없이도 열림).
                        인원·시간·종류·이동/운반 방식·무게 기준·출발지(별 끌기) 를 바꾸면 브라우저 안에서
                        지형 최단경로(다익스트라)·구역·순서·마대·시간을 즉시 다시 계산한다.
                        지도는 Leaflet 위성(인터넷) + 드론 정사영상 오버레이; 오프라인이면 정사영상·지형·경로만.
  draw_static_map()     인쇄용 PNG 지도 (matplotlib). 기본 파라미터 계획(파이썬) 기준.
  Basemap               정사영상 축소본 + 월드파일 (위경도 재투영, 지형 분류 입력)
"""
from __future__ import annotations

import base64
import html
import json
import math
from pathlib import Path

import cv2
import numpy as np

from .collect import BASIS_KO, CollectPlan, material, materials_js

DAY_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#8e44ad", "#eda100", "#e34948", "#0097a7", "#6d4c41"]
ASSETS = Path(__file__).with_name("assets")


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def _b64_file(path: Path, max_px: int | None = None) -> str | None:
    try:
        if max_px:
            img = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                return None
            h, w = img.shape[:2]
            s = min(1.0, max_px / max(h, w))
            if s < 1:
                img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
        data = path.read_bytes()
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        return f"data:{mime};base64," + base64.b64encode(data).decode()
    except OSError:
        return None


# ─────────────────────────── 정사영상 축소본 ───────────────────────────
class Basemap:
    """정사영상 축소본 + 월드파일. world = {x0, y0, px, py} (왼쪽 위 모서리, px>0, py<0), full_px = 원본 (W, H)."""

    def __init__(self, image_path: str | Path, world: dict, full_px: tuple[int, int], crs_m: str = "EPSG:5186"):
        self.path = Path(image_path)
        self.img = cv2.imdecode(np.fromfile(str(self.path), np.uint8), cv2.IMREAD_COLOR)
        if self.img is None:
            raise FileNotFoundError(image_path)
        self.world, self.full_px, self.crs_m = world, full_px, crs_m
        self.sx = self.img.shape[1] / full_px[0]
        self.sy = self.img.shape[0] / full_px[1]

    @classmethod
    def from_array(cls, img: np.ndarray, world: dict, full_px: tuple[int, int], crs_m: str = "EPSG:5186") -> "Basemap":
        self = cls.__new__(cls)
        self.path = None; self.img = img; self.world = world; self.full_px = full_px; self.crs_m = crs_m
        self.sx = img.shape[1] / full_px[0]; self.sy = img.shape[0] / full_px[1]
        return self

    @property
    def extent_m(self) -> tuple[float, float, float, float]:
        w = self.world
        return (w["x0"], w["x0"] + self.full_px[0] * w["px"], w["y0"] + self.full_px[1] * w["py"], w["y0"])

    def nodata_mask(self, img: np.ndarray | None = None) -> np.ndarray:
        img = self.img if img is None else img
        m = (img.sum(axis=2) < 24).astype(np.uint8)
        return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool)

    def to_wgs84(self, out_w: int = 2400, quality: int = 78, nodata_fn=None) -> tuple[str, tuple[float, float, float, float]]:
        """위경도 격자로 재투영 → (data URL(webp, 투명 nodata), (south, west, north, east))."""
        from pyproj import Transformer
        to_ll = Transformer.from_crs(self.crs_m, "EPSG:4326", always_xy=True)
        to_m = Transformer.from_crs("EPSG:4326", self.crs_m, always_xy=True)
        xmin, xmax, ymin, ymax = self.extent_m
        cs = [to_ll.transform(x, y) for x, y in ((xmin, ymin), (xmin, ymax), (xmax, ymin), (xmax, ymax))]
        west, east = min(c[0] for c in cs), max(c[0] for c in cs)
        south, north = min(c[1] for c in cs), max(c[1] for c in cs)
        lat0 = math.radians((south + north) / 2)
        out_w = min(out_w, max(self.img.shape[1] * 2, 400))
        out_h = int(out_w * (north - south) / ((east - west) * math.cos(lat0)))
        lons = west + (np.arange(out_w) + 0.5) / out_w * (east - west)
        lats = north - (np.arange(out_h) + 0.5) / out_h * (north - south)
        LON, LAT = np.meshgrid(lons, lats)
        X, Y = to_m.transform(LON, LAT)
        w = self.world
        mapx = ((X - w["x0"]) / w["px"] * self.sx).astype(np.float32)
        mapy = ((Y - w["y0"]) / w["py"] * self.sy).astype(np.float32)
        interp = cv2.INTER_NEAREST if nodata_fn is not None else cv2.INTER_LINEAR
        warped = cv2.remap(self.img, mapx, mapy, interp, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        nd = nodata_fn(warped) if nodata_fn is not None else self.nodata_mask(warped)
        alpha = np.where(nd, 0, 255).astype(np.uint8)
        bgra = cv2.merge([warped[:, :, 0], warped[:, :, 1], warped[:, :, 2], alpha])
        ok, buf = cv2.imencode(".webp", bgra, [cv2.IMWRITE_WEBP_QUALITY, quality])
        if not ok:
            ok, buf = cv2.imencode(".png", bgra)
            return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode(), (south, west, north, east)
        return "data:image/webp;base64," + base64.b64encode(buf.tobytes()).decode(), (south, west, north, east)


def fit_affine(crs_m: str, lon_range: tuple[float, float], lat_range: tuple[float, float]) -> dict:
    """위경도 ↔ 투영좌표(m) 를 작은 영역에서 아핀으로 근사 (브라우저 계산용). 반환 {fwd, inv, max_err_m}."""
    from pyproj import Transformer
    to_m = Transformer.from_crs("EPSG:4326", crs_m, always_xy=True)
    lons = np.linspace(lon_range[0], lon_range[1], 12); lats = np.linspace(lat_range[0], lat_range[1], 12)
    LON, LAT = np.meshgrid(lons, lats); X, Y = to_m.transform(LON, LAT)
    A = np.c_[LON.ravel(), LAT.ravel(), np.ones(LON.size)]
    cx = np.linalg.lstsq(A, X.ravel(), rcond=None)[0]
    cy = np.linalg.lstsq(A, Y.ravel(), rcond=None)[0]
    err = float(np.max(np.hypot(A @ cx - X.ravel(), A @ cy - Y.ravel())))
    M = np.array([[cx[0], cx[1]], [cy[0], cy[1]]]); Mi = np.linalg.inv(M)
    return {"fwd": [float(v) for v in (cx[0], cx[1], cx[2], cy[0], cy[1], cy[2])],
            "inv": [float(v) for v in (Mi[0, 0], Mi[0, 1], Mi[1, 0], Mi[1, 1])], "max_err_m": err}


# ─────────────────────────── 정적 PNG 지도 ───────────────────────────
def _korean_font():
    import matplotlib
    from matplotlib import font_manager
    import logging
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)   # "font weight bold" 안내 숨김
    for f in [r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\NanumGothic.ttf", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
              "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/System/Library/Fonts/AppleSDGothicNeo.ttc"]:
        if Path(f).exists():
            try:
                for extra in (Path(f), Path(f).with_name(Path(f).stem + "Bold" + Path(f).suffix), Path(f).with_name(Path(f).stem + "bd" + Path(f).suffix)):
                    if extra.exists():
                        font_manager.fontManager.addfont(str(extra))
                matplotlib.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
                break
            except Exception:  # noqa: BLE001
                continue
    matplotlib.rcParams["axes.unicode_minus"] = False


def draw_static_map(plan: CollectPlan, out_png: str | Path, basemap: Basemap | None = None, dpi: int = 150,
                    title: str | None = None, crs_m: str = "EPSG:5186") -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import FancyBboxPatch
    from pyproj import Transformer
    _korean_font()
    to_m = Transformer.from_crs("EPSG:4326", crs_m, always_xy=True)

    objs = [o for o in plan.objects if o.included]
    xs = [o.x_m for o in plan.objects] + [plan.depot["x_m"]]; ys = [o.y_m for o in plan.objects] + [plan.depot["y_m"]]
    pad = max((max(xs) - min(xs)), (max(ys) - min(ys))) * 0.06 + 10
    xmin, xmax, ymin, ymax = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    if basemap is not None:
        e = basemap.extent_m
        xmin, xmax, ymin, ymax = min(xmin, e[0]), max(xmax, e[1]), min(ymin, e[2]), max(ymax, e[3])
    aspect = (ymax - ymin) / (xmax - xmin)
    fig = plt.figure(figsize=(17, max(9, 12.5 * aspect + 1.2)), facecolor="white")
    gs = fig.add_gridspec(1, 2, width_ratios=[3.1, 1], wspace=0.02, left=0.02, right=0.99, top=0.93, bottom=0.03)
    ax = fig.add_subplot(gs[0]); side = fig.add_subplot(gs[1]); side.axis("off")
    if basemap is not None:
        img = cv2.cvtColor(basemap.img, cv2.COLOR_BGR2RGB).copy()
        img[basemap.nodata_mask()] = (236, 240, 244)
        e = basemap.extent_m
        ax.imshow(img, extent=(e[0], e[1], e[2], e[3]), interpolation="bilinear", zorder=0)
    ax.set_facecolor("#eceff3"); ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("#c9ced6")

    by_id = {o.obj_id: o for o in plan.objects}
    for z in plan.zones:
        col = DAY_COLORS[(z.day - 1) % len(DAY_COLORS)]
        pts = [to_m.transform(lo, la) for lo, la in z.path_lonlat]
        if not pts:
            continue
        first = by_id[z.objects[0]]
        k = min(range(len(pts)), key=lambda i: math.hypot(pts[i][0] - first.x_m, pts[i][1] - first.y_m))
        for seg, ls in ((pts[:k + 1], (0, (5, 3))), (pts[k:], "solid")):
            if len(seg) > 1:
                ax.plot([p[0] for p in seg], [p[1] for p in seg], color="white", lw=5, solid_capstyle="round", zorder=2, alpha=0.9)
                ax.plot([p[0] for p in seg], [p[1] for p in seg], color=col, lw=2.4, ls=ls, solid_capstyle="round", zorder=3)
    if plan.params.get("round_trip") and plan.zones and plan.route_lonlat:
        last = by_id[plan.zones[-1].objects[-1]]
        pts = [to_m.transform(lo, la) for lo, la in plan.route_lonlat]
        near = [i for i in range(len(pts)) if math.hypot(pts[i][0] - last.x_m, pts[i][1] - last.y_m) < 1.0]
        back = pts[max(near):] if near else []
        if len(back) > 1:
            ax.plot([p[0] for p in back], [p[1] for p in back], color="white", lw=5, zorder=2, alpha=0.9)
            ax.plot([p[0] for p in back], [p[1] for p in back], color=DAY_COLORS[(plan.zones[-1].day - 1) % len(DAY_COLORS)],
                    lw=2.4, ls=(0, (4, 3)), zorder=3)
    for o in plan.objects:
        if not o.included:
            ax.scatter(o.x_m, o.y_m, s=26, c="#bbb", edgecolors="#666", linewidths=0.6, zorder=4)
    for o in objs:
        ax.scatter(o.x_m, o.y_m, s=90 if o.heavy else 46, c=material(o.code).color, edgecolors="black", linewidths=0.8,
                   zorder=5, marker="D" if o.heavy else "o")
    for z in plan.zones:
        col = DAY_COLORS[(z.day - 1) % len(DAY_COLORS)]
        ax.scatter(z.cx_m, z.cy_m, s=560, c="white", edgecolors=col, linewidths=2.6, zorder=6)
        ax.text(z.cx_m, z.cy_m, str(z.step), ha="center", va="center", fontsize=12, fontweight="bold", color=col, zorder=7)
    ax.scatter(plan.depot["x_m"], plan.depot["y_m"], s=700, marker="*", c="#ffffff", edgecolors="#111", linewidths=1.5, zorder=8)
    ax.annotate(plan.depot["name"], (plan.depot["x_m"], plan.depot["y_m"]), xytext=(14, -4), textcoords="offset points",
                fontsize=11, fontweight="bold", zorder=8, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#333", lw=0.8))
    span = xmax - xmin
    sb = 10 ** math.floor(math.log10(span / 5)); sb = sb * (5 if span / 5 / sb >= 5 else 2 if span / 5 / sb >= 2 else 1)
    x0s, y0s = xmin + span * 0.04, ymin + (ymax - ymin) * 0.04
    ax.plot([x0s, x0s + sb], [y0s, y0s], color="black", lw=4, zorder=9)
    ax.text(x0s + sb / 2, y0s + (ymax - ymin) * 0.012, f"{sb:g} m", ha="center", fontsize=11, fontweight="bold", zorder=9)
    ax.annotate("N", xy=(xmax - span * 0.05, ymax - (ymax - ymin) * 0.04), xytext=(xmax - span * 0.05, ymax - (ymax - ymin) * 0.11),
                ha="center", fontsize=14, fontweight="bold", arrowprops=dict(arrowstyle="-|>", lw=2, color="black"), zorder=9)
    handles = [Line2D([], [], marker="o", ls="", ms=9, mfc=d["color"], mec="black", label=f"{d['ko']} {d['count']}개")
               for c, d in sorted(plan.by_code.items(), key=lambda kv: -kv[1]["count"])]
    handles.append(Line2D([], [], marker="D", ls="", ms=9, mfc="white", mec="black", label="2인 운반(무거움)"))
    for d in sorted({z.day for z in plan.zones}):
        handles.append(Line2D([], [], color=DAY_COLORS[(d - 1) % len(DAY_COLORS)], lw=3, label=f"{d}일차 경로"))
    handles.append(Line2D([], [], color="#555", lw=2, ls=(0, (5, 3)), label="구역 사이 이동" + (" (지형 최단경로)" if plan.terrain_used else " (직선)")))
    ax.legend(handles=handles, loc="upper left", fontsize=10, framealpha=0.95, title="범례", title_fontsize=10)
    t = plan.totals
    fig.suptitle(title or f"{plan.site} 쓰레기 수거 작업 지도", fontsize=20, fontweight="bold", x=0.02, ha="left", y=0.985)
    bc = " · ".join(f"{BASIS_KO.get(k, k)} {v}" for k, v in t.get("basis_counts", {}).items())
    ax.set_title(f"조사일 {plan.survey_date} · 쓰레기 {t['items']}개 ({bc}) · 구역 {t['zones']}곳 · 예상 {t['kg_plan']:.1f} kg "
                 f"(범위 {t['kg_min']:.1f}–{t['kg_max']:.1f}) · 마대 {t['bags']}장 · 이동 {plan.route_len_m / 1000:.2f} km · "
                 f"총 {plan.total_min / 60:.1f}시간({plan.params['workers']}명) · {max((x['days'] for x in plan.teams), default=0)}일 · "
                 f"{'지형 반영' if plan.terrain_used else '직선×우회'}", fontsize=10.5, loc="left", color="#333")
    lines = [("순서", "구역", "개수", "kg", "마대", "분")]
    for z in plan.zones:
        lines.append((str(z.step), z.name + ("  [2인]" if z.heavy_ids else ""), str(z.n_items), f"{z.kg_plan:.1f}", str(z.bags), f"{z.walk_min + z.work_min:.0f}"))
    side.set_xlim(0, 1); side.set_ylim(0, 1)
    y = 0.98
    side.text(0, y, "작업 순서 (출발지 → 번호 순)", fontsize=13, fontweight="bold", va="top"); y -= 0.045
    colx = [0.0, 0.11, 0.62, 0.72, 0.84, 0.93]
    rowh = min(0.034, 0.9 / (len(lines) + 2))
    for i, row in enumerate(lines):
        bold = i == 0
        if i > 0:
            z = plan.zones[i - 1]; col = DAY_COLORS[(z.day - 1) % len(DAY_COLORS)]
            side.add_patch(FancyBboxPatch((0, y - rowh * 0.8), 0.085, rowh * 0.72, boxstyle="round,pad=0.002", fc=col, ec="none"))
            side.text(0.042, y - rowh * 0.44, row[0], color="white", fontsize=9.5, fontweight="bold", ha="center", va="center")
        for cx, txt in zip(colx[1:] if i > 0 else colx, row[1:] if i > 0 else row):
            side.text(cx, y - rowh * 0.44, txt, fontsize=9.5 if not bold else 10, fontweight="bold" if bold else "normal", va="center",
                      ha="left" if cx < 0.7 else "right" if cx > 0.9 else "center")
        y -= rowh
    y -= 0.02
    side.text(0, y, "준비물", fontsize=12, fontweight="bold", va="top"); y -= 0.035
    for e in plan.equipment:
        side.text(0.01, y, "[  ] " + e, fontsize=9.5, va="top", wrap=True); y -= 0.03
    y -= 0.01
    side.text(0, y, "※ 무게는 3D 부피 × 겉보기 밀도 추정(가정값 포함).\n   현장에서 탐지에 없는 쓰레기도 함께 수거.", fontsize=8.5, va="top", color="#555")
    out = Path(out_png); out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi, facecolor="white"); plt.close(fig)
    return out


# ─────────────────────────── HTML 앱 ───────────────────────────
def _control_panel(d: dict, mats: dict, terrain: bool, present_codes: list[str], artifact: bool, company_label: str, has_company: bool) -> str:
    esc = _esc
    def seg(name, opts, cur):
        return f'<div class="seg" data-name="{name}">' + "".join(
            f'<button data-v="{v}" class="{"on" if v == cur else ""}">{esc(t)}</button>' for v, t in opts) + "</div>"
    codes = "".join(f'<label><input type="checkbox" value="{c}" checked><i style="background:{mats[c]["color"]}"></i>{esc(mats[c]["ko"])}</label>'
                    for c in present_codes)
    cal = "".join(f'<label><b>{esc(mats[c]["ko"])} 보정 계수</b><input type="number" id="c-cal-{c}" min="0.05" max="20" step="0.05" value="1"></label>'
                  for c in present_codes)
    travel_opts = [("walk", "도보"), ("boat", "보트 지원")] if terrain else [("walk", "도보 (지형 없음)")]
    wsrc = seg('wsrc', [('ours', '3D 부피 추정'), ('company', company_label)], d['weight_source']) if has_company else seg('wsrc', [('ours', '3D 부피 추정')], 'ours')
    return f"""
<div class="panel"><h2><span>조건 바꾸기 → 바로 다시 계산</span><span><span id="status">…</span><span id="sync" style="display:block;font-size:12px;color:var(--ok);font-weight:600"></span><input id="c-name" placeholder="내 이름 (변경 표시용)" style="display:none;font:inherit;font-size:12px;padding:3px 8px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--ink);width:150px;margin-top:4px" oninput="setMyName(this.value)"><button class="fold" onclick="toggleSide()" title="설정 접기">◀ 접기</button></span></h2>
<div class="ctrl">
 <label><b>팀당 인원</b><input type="number" id="c-workers" min="1" max="30" step="1" value="{d['workers']}"></label>
 <label><b>팀 수 (동시 투입)</b><input type="number" id="c-teams" min="1" max="6" step="1" value="{d['teams']}"></label>
 <label><b>하루 작업 시간</b><input type="number" id="c-hours" min="0.5" max="12" step="0.5" value="{d['hours_per_day']}"></label>
 <label><b>이동 방식</b>{seg('travel', travel_opts, d['travel'])}</label>
 <label><b>운반 방식</b>{seg('carry', [('pile', '현장 적치'), ('carry', '들고 이동')], d['carry'])}</label>
 <label><b>최적화 목표</b>{seg('objective', [('distance', '최단 이동'), ('weight', '무게 우선')], d['objective'])}</label>
 <label><b>무게 기준</b>{wsrc}</label>
 <label><b>추정 범위 (3D 추정일 때)</b>{seg('wstat', [('min', '최소'), ('typ', '대표'), ('max', '최대')], d['weight_stat'])}</label>
 <label><b>최소 무게(kg) 미만 건너뜀</b><input type="number" id="c-minkg" min="0" step="0.1" value="{d['min_kg']}"></label>
 <label><b>완료한 구역 제외</b><input type="checkbox" id="c-exdone" checked style="width:22px;height:22px"></label>
 <label style="grid-column:1/-1"><b>수거할 종류</b><div class="codes">{codes}</div></label>
</div>
<details class="adv"><summary>고급 설정 (가정값) · 실측 보정 계수</summary><div class="ctrl" style="margin-top:8px">
 <label><b>구역 묶기 거리 (m)</b><input type="number" id="c-link" min="5" max="2000" step="5" value="{d['link_m']}"></label>
 <label><b>걷기 속도 (km/h)</b><input type="number" id="c-walk" min="1" max="6" step="0.1" value="{d['walk_kmh']}"></label>
 <label><b>물체당 시간 (분)</b><input type="number" id="c-item" min="0" max="30" step="0.5" value="{d['item_min']}"></label>
 <label><b>면적 1 m² 당 시간 (분)</b><input type="number" id="c-m2" min="0" max="20" step="0.1" value="{d['min_per_m2']}"></label>
 <label><b>1인 운반 무게 (kg)</b><input type="number" id="c-ckg" min="1" max="50" step="1" value="{d['carry_kg_per_person']}"></label>
 <label><b>1인 운반 마대 수</b><input type="number" id="c-cbags" min="1" max="10" step="1" value="{d['carry_bags_per_person']}"></label>
 <label><b>마대 적재 무게 (kg)</b><input type="number" id="c-bagkg" min="1" max="100" step="1" value="{d['bag_kg']}"></label>
 <label><b>마대 부피 (L)</b><input type="number" id="c-bagl" min="10" max="1000" step="10" value="{d['bag_l']}"></label>
 <label><b>숲 통과 배수</b><input type="number" id="c-veg" min="1" max="20" step="0.5" value="{d['veg_cost']}"></label>
 <label><b>보트 이동 배수 (물)</b><input type="number" id="c-boat" min="0.1" max="3" step="0.1" value="{d['boat_cost']}"></label>
 <label><b>우회 배수 (지형 없을 때)</b><input type="number" id="c-detour" min="1" max="3" step="0.1" value="{d['detour']}"></label>
 <label><b>출발지 왕복</b><input type="checkbox" id="c-round" {"checked" if d['round_trip'] else ""} style="width:22px;height:22px"></label>
 {cal}
</div></details>
<div class="btns"><button class="primary" onclick="recompute()">다시 계산</button><button onclick="resetAll()">초기화</button><button onclick="compareScenarios();document.getElementById('scen').scrollIntoView({{behavior:'smooth'}})">시나리오 비교</button>{'' if artifact else '<button onclick="downloadCsv()">작업순서 CSV</button><button onclick="downloadJson()">설정·결과 JSON</button><button onclick="window.print()">인쇄</button>'}</div>
</div>"""


def _resolve_photo(base: Path | None, rel: str | None, max_px: int = 260) -> str | None:
    if not base or not rel:
        return None
    cand = [base / rel, base / Path(rel).name, base / "photos" / Path(rel).name, base / "crops" / Path(rel).name]
    p = next((c for c in cand if c.exists()), None)
    return _b64_file(p, max_px=max_px) if p else None


def build_collect_html(plan: CollectPlan, out_html: str | Path, *, photos_dir: str | Path | None = None, mask_pattern: str | None = None,
                       basemap: Basemap | None = None, static_png: str | Path | None = None, terrain=None,
                       center_xy: tuple[float, float] | None = None, title: str | None = None, site_id: str | None = None,
                       crs_m: str = "EPSG:5186", artifact: bool = False, shared_cfg: dict | None = None, local_sync: bool = True,
                       description: str = "", source: str = "", truth_note: str = "", index_href: str | None = None) -> Path:
    """plan 은 기본 파라미터로 만든 계획 (초기값·가정 문구용). 실제 숫자는 브라우저에서 다시 계산한다.
    photos_dir: 물체 image_path 의 기준 폴더 (input/). mask_pattern: 3D 마스크 그림 이름 규칙 ("masks/{seq:02d}.jpg").
    artifact=True: 인터넷 공개용(claude.ai 아티팩트) 변형 — 문서 뼈대 없이, 외부 타일 없이 드론 정사영상만, 인쇄·내려받기 없음.
    shared_cfg: {"provider": "supabase", ...} 이면 Supabase 로 완료 체크·보정·출발지를 모두에게 공유 (tools/supabase_setup.sql).
    local_sync=True 이면 serve.py 로 열었을 때 /api 로 같은 와이파이 안에서 공유 (파일로 열면 자동으로 꺼짐)."""
    title = title or f"{plan.site} 쓰레기 수거 작업 계획"
    base = Path(photos_dir) if photos_dir else None
    pp = plan.params
    site_id = site_id or plan.site or "site"

    objs_js = []
    for o in plan.objects:
        img = _resolve_photo(base, o.image_path)
        img2 = _resolve_photo(base, mask_pattern.format(seq=o.seq, id=o.obj_id), 320) if mask_pattern else None
        if img is None and img2 is not None:
            img, img2 = img2, None
        objs_js.append({"id": o.obj_id, "seq": o.seq, "code": o.code, "ko": o.class_ko, "color": material(o.code).color, "lon": o.lon, "lat": o.lat,
                        "x": o.x_m, "y": o.y_m, "area": o.area_m2, "w": o.w_m, "h": o.h_m, "hgt": o.height_m, "ckg": o.company_kg,
                        "kmin": o.kg_min, "ktyp": o.kg_typ, "kmax": o.kg_max, "vol": o.volume_m3, "img": img, "img2": img2,
                        "basis": o.basis, "conf": o.confidence, "truth": o.truth_m3, "n": o.n_items, "ikmax": o.item_kg_max,
                        "kgby": o.kg_by, "members": o.members, "src": o.source, "dims": o.dims_cm})
    present_codes = sorted({o.code for o in plan.objects} | {c for o in plan.objects for c in (o.kg_by or {})},
                           key=lambda c: -sum(o.n_items for o in plan.objects if o.code == c))
    mats = materials_js(present_codes)
    has_company = any(o.company_kg is not None for o in plan.objects)
    company_label = "기업 제공값" if any("업체 라벨" in o.source for o in plan.objects) else "업체 방식(면적×계수)"

    lons = [o.lon for o in plan.objects] + [plan.depot["lon"]]; lats = [o.lat for o in plan.objects] + [plan.depot["lat"]]
    bm = None; terrain_png = None; depot_in_basemap = False
    if basemap is not None:
        url, bounds = basemap.to_wgs84()
        bm = {"url": url, "bounds": list(bounds)}
        lons += [bounds[1], bounds[3]]; lats += [bounds[0], bounds[2]]
        depot_in_basemap = bounds[0] <= plan.depot["lat"] <= bounds[2] and bounds[1] <= plan.depot["lon"] <= bounds[3]
    affine = fit_affine(crs_m, (min(lons) - 0.005, max(lons) + 0.005), (min(lats) - 0.005, max(lats) + 0.005))
    terrain_js = None
    if terrain is not None:
        terrain_js = terrain.to_js()
        tmp = Basemap.from_array(terrain.class_image(1), {"x0": terrain.x0, "y0": terrain.y0, "px": terrain.cell, "py": -terrain.cell},
                                 (terrain.nc, terrain.nr), crs_m)
        url, bounds = tmp.to_wgs84(out_w=1200, quality=60, nodata_fn=lambda img: img.sum(axis=2) < 10)
        terrain_png = {"url": url, "bounds": list(bounds), "opacity": 0.45, "on": False}
    if center_xy is None:
        center_xy = (float(np.mean([o.x_m for o in plan.objects])), float(np.mean([o.y_m for o in plan.objects])))
    defaults = {"workers": pp["workers"], "teams": pp.get("teams", 1), "hours_per_day": pp["hours_per_day"], "link_m": pp["link_m"], "walk_kmh": pp["walk_kmh"],
                "item_min": pp["item_min"], "min_per_m2": pp["min_per_m2"], "heavy_extra_min": pp["heavy_extra_min"], "load_slow": pp["load_slow"],
                "carry_kg_per_person": pp["carry_kg_per_person"], "carry_bags_per_person": pp["carry_bags_per_person"],
                "min_kg": pp["min_kg"], "bag_kg": pp["bag"]["bag_kg"], "bag_l": round(pp["bag"]["bag_m3"] * 1000), "detour": pp["detour"],
                "veg_cost": 3.0, "boat_cost": 0.5, "round_trip": pp["round_trip"], "travel": pp["travel"], "carry": pp["carry"],
                "objective": pp["objective"], "weight_source": pp["weight_source"], "weight_stat": pp["weight_stat"]}
    if terrain is not None:
        from .terrain import COST, VEG, WATER
        defaults["veg_cost"] = COST["walk"][VEG]; defaults["boat_cost"] = COST["boat"][WATER]
    control_defaults = {"c-workers": defaults["workers"], "c-teams": defaults["teams"], "c-hours": defaults["hours_per_day"], "c-link": defaults["link_m"], "c-walk": defaults["walk_kmh"],
                        "c-item": defaults["item_min"], "c-m2": defaults["min_per_m2"], "c-ckg": defaults["carry_kg_per_person"],
                        "c-cbags": defaults["carry_bags_per_person"], "c-minkg": defaults["min_kg"], "c-bagkg": defaults["bag_kg"],
                        "c-bagl": defaults["bag_l"], "c-veg": defaults["veg_cost"], "c-boat": defaults["boat_cost"], "c-detour": defaults["detour"],
                        "c-round": defaults["round_trip"]}
    seg_defaults = {"travel": defaults["travel"], "carry": defaults["carry"], "objective": defaults["objective"],
                    "wsrc": defaults["weight_source"] if has_company else "ours", "wstat": defaults["weight_stat"]}
    supabase = ({"url": shared_cfg["url"], "key": shared_cfg["anon_key"], "table": shared_cfg.get("table", "shared_state")}
                if (shared_cfg and not artifact and shared_cfg.get("provider") == "supabase" and shared_cfg.get("url") and shared_cfg.get("anon_key")) else None)
    data = {"site": plan.site, "site_id": site_id, "survey": plan.survey_date, "depot": plan.depot, "depot_in_basemap": depot_in_basemap, "objects": objs_js, "mats": mats,
            "terrain": terrain_js, "terrain_png": terrain_png, "affine": affine, "basemap": bm, "day_colors": DAY_COLORS,
            "center": {"x": center_xy[0], "y": center_xy[1]}, "zone_word": pp.get("zone_word", "해안"), "basis_ko": BASIS_KO,
            "company_label": company_label,
            "bag": {"bulk": pp["bag"]["bulk_factor"], "tonbag_kg": pp["bag"]["tonbag_kg"], "tonbag_m3": pp["bag"]["tonbag_m3"]},
            "defaults": defaults, "control_defaults": control_defaults, "seg_defaults": seg_defaults, "no_tiles": artifact, "shared": artifact,
            "supabase": supabase, "local_sync": ({"api": "/api"} if (local_sync and not artifact and not supabase) else None)}
    fallback = _b64_file(Path(static_png), max_px=2200) if static_png and Path(static_png).exists() else None
    css = (ASSETS / "app.css").read_text(encoding="utf-8")
    app_js = (ASSETS / "app.js").read_text(encoding="utf-8")
    leaflet_css = (ASSETS / "leaflet.css").read_text(encoding="utf-8")
    leaflet_js = (ASSETS / "leaflet.js").read_text(encoding="utf-8")
    if artifact:
        head = (f'<meta charset="utf-8"><title>{_esc(title)}</title>\n<style>{leaflet_css}</style><script>{leaflet_js}</script>\n'
                f'<style>{css}\n#map{{background:#8fb3c9}}</style>\n<div class="wrap">')
        tail = "</div>"
    else:
        head = (f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)}</title>
<style>{leaflet_css}</style>
<script>{leaflet_js}</script>
{'<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js" crossorigin=""></script>' if supabase else ''}
<style>{css}</style></head><body><div class="wrap">""")
        tail = "</body></html>"

    t = plan.totals
    bc = t.get("basis_counts", {})
    basis_txt = " · ".join(f"{BASIS_KO.get(k, k)} {v}개" for k, v in bc.items())
    chain = "드론 영상 + SRT → ① 탐지 → ② 3D 복원 → ③ 위치 → ④ 부피(SAM 2 투표) → ⑤ 무게(겉보기 밀도) → <b>⑥ 수거계획(이 페이지)</b>"
    story = (f'<div class="card"><h2>이 계획의 입력</h2><div class="story"><div><p class="sub" style="margin:0 0 6px">{_esc(description) if description else "coastal litter pipeline 이 드론 영상에서 뽑은 쓰레기 위치와 3D 부피를 읽어, 종류별 겉보기 밀도로 무게를 추정하고 수거 계획을 짰습니다."}</p>'
             f'<p class="sub" style="margin:0">자료: {_esc(source) if source else "input/"} · 무게 근거: {basis_txt}'
             + (f' · 크기를 아는 시험 물체 {t["truth"]["n"]}개 (아래 "측정 vs 정답")' if t.get("truth") else '') + '</p></div>'
             f'<div class="chain">{chain}</div></div></div>')
    truth_card = ""
    if t.get("truth"):
        tr = t["truth"]
        truth_card = ('<div class="card"><h2>3D 부피 측정 vs 정답</h2><p class="sub">크기를 아는 시험 물체(줄자로 잰 상자) 의 측정 부피와 정답. '
                      + (_esc(truth_note) + " " if truth_note else "")
                      + (f'측정 성공 {tr["n_measured"]}/{tr["n"]}개, 측정 부피 합 {tr["measured_m3"] * 1000:.1f} L vs 정답 {tr["truth_m3"] * 1000:.1f} L ({(tr["measured_m3"] / tr["truth_m3"] - 1) * 100:+.0f} %). ' if tr["n_measured"] else '측정에 성공한 물체가 없습니다. ')
                      + '측정 실패·신뢰 낮음 물체는 같은 종류의 측정 중앙값으로 대체했습니다.</p><div style="overflow:auto;max-height:420px"><table><thead><tr><th>ID</th><th>측정 크기</th><th class="num">측정 L</th><th class="num">정답 L</th><th class="num">오차</th><th>근거</th><th>출처</th></tr></thead><tbody id="truthtab"></tbody></table></div></div>')
    crumb = f'<div class="crumb"><a href="{_esc(index_href)}">← 현장 목록</a></div>' if index_href else ""
    H = [head + f"""
<header>{crumb}<h1>{_esc(title)}</h1><p>조사일 {_esc(plan.survey_date)} · 출발·집결지 <b>{_esc(plan.depot['name'])}</b> (지도의 ★ 를 끌어서 바꿀 수 있음) · {'지형(물·숲·맨땅) 최단경로 반영' if terrain is not None else '직선 거리 × 우회 배수'}</p></header>""",
         '<div class="layout" id="layout"><aside class="side"><button class="side-open" onclick="toggleSide()">설정 열기 ▶</button>' + _control_panel(defaults, mats, terrain is not None, present_codes, artifact, company_label, has_company) + '</aside><main class="main">',
         '<div class="tiles" id="tiles"></div>',
         story,
         '<div class="card"><h2>수거 지도</h2><p class="sub" id="maphint">번호 순서대로 이동합니다. 번호를 누르면 그 구역에서 수거할 물체 목록(사진·종류·크기·부피·무게)이 패널로 뜨고, 점을 누르면 물체 하나의 정보가 나옵니다. ★ 출발지는 끌어서 옮기면 경로가 다시 계산됩니다.</p>',
         '<div class="mapbtns" id="daybtns"></div>',
         f'<div id="map"><img id="fallback" class="fallback" style="display:none" src="{fallback or ""}" alt="수거 지도"><div class="busy" id="busy">계산 중…</div><div class="zpanel" id="zpanel"></div></div>',
         '<div class="legend" id="legend"></div></div>',
         '<div class="card"><h2>작업 순서</h2><p class="sub">출발지에서 번호 순서대로 돕니다. 시간은 이동 + 줍기·담기 예상값입니다. 카드를 누르면 지도가 그 구역으로 가고, 완료 ✓ 를 누르면 남은 구역만으로 다시 계산됩니다. 길찾기 링크는 휴대폰에서 지도 앱으로 열립니다.</p><div id="steps"></div></div>',
         truth_card,
         '<div class="card"><h2>진행 현황</h2><p class="sub">구역 카드의 "완료 ✓" 를 누르면 그 구역이 완료 처리되고(이 브라우저에 저장; serve.py 또는 공유 설정으로 열면 접속한 모두에게 반영), 남은 구역만으로 경로·시간이 다시 계산됩니다. 지도의 점을 눌러 물체 하나씩 완료할 수도 있습니다.</p><div id="progress"></div></div>\n<div class="card"><h2>실측 보정</h2><p class="sub">현장에서 한 구역의 마대를 저울로 재면, 예상 무게와 비교해 그 종류의 보정 계수를 자동으로 구하고 모든 구역에 적용합니다 (3D 부피 추정 무게에만 곱함, 이 브라우저에 저장).</p>\n<div class="cal"><label><b>실측한 구역</b><select id="cal-zone"></select></label><label><b>실측 무게 (kg)</b><input type="number" id="cal-kg" min="0" step="0.1" placeholder="예: 12.5"></label><label><b>&nbsp;</b><button class="primary" style="font:inherit;padding:8px 12px;border-radius:9px;border:0;background:var(--accent);color:#fff;cursor:pointer" onclick="applyMeasured()">보정 계수 계산·적용</button></label><label><b>&nbsp;</b><button style="font:inherit;padding:8px 12px;border-radius:9px;border:1px solid var(--border);background:var(--card);color:var(--ink);cursor:pointer" onclick="resetCalib()">보정 해제</button></label></div><div id="cal-msg"></div></div>\n<div class="card"><h2>시나리오 비교 · 민감도</h2><p class="sub">버튼을 누르면 현재 설정에서 조건을 하나씩 바꾼 결과를 한 표로 보여 줍니다.</p><div class="btns" style="margin:0 0 10px"><button class="primary" onclick="compareScenarios()">시나리오 비교 계산</button></div><div id="scen" style="overflow:auto"></div></div>',
         '<div class="card"><h2>준비물 체크리스트</h2><ul class="check" id="equip"></ul></div>',
         f'<div class="card"><h2>종류별 요약과 다루는 법</h2><div style="overflow:auto"><table><thead><tr><th>종류</th><th class="num">개수</th><th class="num">면적 m²</th><th class="num">부피 L</th><th class="num">예상 kg</th><th class="num">범위 kg</th><th class="num">{_esc(company_label)} kg</th><th>무게 근거</th><th>다루는 법</th></tr></thead><tbody id="bycode"></tbody></table></div></div>',
         f'<div class="card"><details><summary>전체 쓰레기 목록 (수거 순서)</summary><div style="overflow:auto;max-height:520px"><table><thead><tr><th>순서</th><th>ID</th><th>종류</th><th class="num">크기</th><th class="num">면적 m²</th><th class="num">부피 L (/정답)</th><th class="num">예상 kg</th><th class="num">범위</th><th class="num">{_esc(company_label)} kg</th><th>근거</th><th>비고</th></tr></thead><tbody id="objtab"></tbody></table></div></details></div>',
         '<div class="card"><h2>이 숫자는 어떻게 나왔나 (가정과 한계)</h2><ul class="note">' + "".join(f"<li>{_esc(a)}</li>" for a in plan.assumptions) +
         f'<li>무게 계산식 예: {_esc(plan.objects[0].note) if plan.objects else ""}</li><li id="assume-params"></li></ul></div>',
         '</main></div><p class="foot">ShoreSweep Planner (hsr1m) · litter3d collect · 파일: plan.json, zones.csv, objects.csv, 수거계획.xlsx, 수거계획_지도.png (기본 설정 기준)</p></div>',
         f'<script>window.PLAN={json.dumps(data, ensure_ascii=False)};</script><script>{app_js}</script>' + tail]
    out = Path(out_html); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(H), encoding="utf-8")
    return out
