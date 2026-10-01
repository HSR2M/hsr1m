"""영상 렌더링: 배경지도 + 조류 흐름(스트리크) + 쓰레기 입자 + 집적 예상 해안(빨간 반투명 라인) → MP4.

장면(scene) 기반: 지역 전체(regional_scene) 와 섬 상세(island_scene) 가 같은 렌더러를 쓴다.
구성 (30 fps): 타이틀 3 s → 조류 흐름(한 조석주기 12.42 h 를 18 s 로) → 쓰레기 이동·좌초 30일 타임랩스(36 s) → 최종 집적 예상 지도(6 s)
"""
import os
import sys
import subprocess
import numpy as np
import multiprocessing as mp
import matplotlib
matplotlib.use("Agg")
import koreanize_matplotlib  # noqa: F401  (NanumGothic)
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib import patheffects as pe
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle

from . import config as C
from . import geodata as G
from . import currents as CU
from . import accumulate as A
from . import basemap as B

FPS = 30
W, H = 1920, 1080
N_TITLE, N_TIDE, N_FINAL = 90, 540, 180
TRAIL, TRACER_AGE = 8, 110
SPEED_CMAP = LinearSegmentedColormap.from_list("flow", ["#7fb3ff", "#dff1ff", "#ffffff", "#fff4a0", "#ffb347"])
RED = "#ff2020"
OUTLINE = [pe.withStroke(linewidth=3, foreground="black")]
FOOTNOTE = ("근거: 조류 = 연속방정식 기반 조석(M2+S2) 포텐셜 흐름 모델(GSHHG 해안선, 수심 모형, 한강·임진강 유량),\n"
            "쓰레기 = 라그랑주 입자추적(RK4) + 풍압 1.5 % + 확산 10 m²/s + 갯벌 좌초/재부유 확률 모형.\n"
            "교육용 모의 결과이며 실제 집적 위치는 실측 해류(국립해양조사원·CMEMS)·수심·바람 자료로 검증이 필요합니다.")


def data_path(name):
    return os.path.join(C.OUT_DIR, f"_render_data_{name}.npz")


# ---------------------------------------------------------------- 프레임 계획
def plan_frames(snap_t, model, dt_vis):
    tt = np.arange(0, 2 * C.M2_PERIOD, 60.0)
    eta = model.sea_level(tt)
    t_lw = float(tt[np.argmin(eta[: int(C.M2_PERIOD / 60)])])   # 인천 저조 시각
    seg, t_sim, k_snap, dt_tr = [], [], [], []
    for f in range(N_TITLE):
        seg.append(0); t_sim.append(t_lw); k_snap.append(0); dt_tr.append(dt_vis)
    for f in range(N_TIDE):
        seg.append(1); t_sim.append(t_lw + f / N_TIDE * C.M2_PERIOD); k_snap.append(0); dt_tr.append(C.M2_PERIOD / N_TIDE)
    for k in range(len(snap_t)):
        seg.append(2); t_sim.append(float(snap_t[k])); k_snap.append(k); dt_tr.append(dt_vis)
    for f in range(N_FINAL):
        seg.append(3); t_sim.append(float(snap_t[-1])); k_snap.append(len(snap_t) - 1); dt_tr.append(dt_vis)
    return np.array(seg), np.array(t_sim), np.array(k_snap), np.array(dt_tr)


# ---------------------------------------------------------------- 추적자(스트리크) 사전 계산
def precompute_tracers(dom, model, t_sim, dt_tr, view, n_tracer, seed=7):
    rng = np.random.default_rng(seed)
    g = dom["grid"]; water = dom["water"]
    x0, y0 = G.lonlat_to_xy(view[0], view[2]); x1, y1 = G.lonlat_to_xy(view[1], view[3])
    inview = water & (g.X > x0) & (g.X < x1) & (g.Y > y0) & (g.Y < y1)
    cand = np.flatnonzero(inview.ravel())

    def spawn(n):
        pick = rng.choice(cand, n)
        ii, jj = np.unravel_index(pick, g.shape)
        return (jj + rng.random(n)) * g.dx, (ii + rng.random(n)) * g.dx

    x, y = spawn(n_tracer)
    age = rng.integers(0, TRACER_AGE, n_tracer)
    nf = len(t_sim)
    pos = np.zeros((nf, n_tracer, 2), np.float32)
    spd = np.zeros((nf, n_tracer), np.float16)
    ages = np.zeros((nf, n_tracer), np.int16)
    for f in range(nf):
        t, dt = t_sim[f], dt_tr[f]
        uv = model.velocity(t)
        u1, v1 = model.velocity_at(t, x, y, uv)
        xm, ym = x + 0.5 * dt * u1, y + 0.5 * dt * v1
        u2, v2 = model.velocity_at(t, xm, ym, uv)
        xn, yn = x + dt * u2, y + dt * v2
        i, j = g.cell_index(xn, yn)
        bad = (i < 0)
        bad[~bad] |= ~water[i[~bad], j[~bad]]
        bad |= (xn < x0) | (xn > x1) | (yn < y0) | (yn > y1)
        bad |= age >= TRACER_AGE
        bad |= np.hypot(u2, v2) < 0.02
        if bad.any():
            xs, ys = spawn(int(bad.sum()))
            xn[bad] = xs; yn[bad] = ys; age[bad] = 0
        age += 1
        x, y = xn, yn
        pos[f, :, 0] = x; pos[f, :, 1] = y
        spd[f] = np.hypot(u2, v2)
        ages[f] = age
        if f % 500 == 0:
            print(f"  tracers {f}/{nf}")
    return pos, spd, ages


def tidal_average_positions(snap_xy, snap_state, half=9):
    """부유 입자 표시 위치를 조석주기(±9 스냅샷 ≈ ±6 h) 이동평균으로 평활 (타임랩스 가독성)."""
    fl = (snap_state == 1).astype(np.float32)[..., None]
    S = np.cumsum(snap_xy.astype(np.float64) * fl, axis=0)
    N = np.cumsum(fl, axis=0)
    S = np.concatenate([np.zeros_like(S[:1]), S]); N = np.concatenate([np.zeros_like(N[:1]), N])
    n = len(snap_xy)
    out = snap_xy.copy()
    for k in range(n):
        a, b = max(0, k - half), min(n, k + half + 1)
        cnt = N[b] - N[a]
        mean = (S[b] - S[a]) / np.maximum(cnt, 1)
        full = (cnt[:, 0] >= (b - a)) & (snap_state[k] == 1)
        out[k, full] = mean[full].astype(np.float32)
    return out


# ---------------------------------------------------------------- 장면 정의
def regional_scene(dom, res, an):
    img, bbox, credit = B.get_basemap(dom)
    g = dom["grid"]
    return dict(name="regional", view=B.DEFAULT_BBOX, basemap=img, credit=credit, labels=C.PLACE_LABELS, show_sources=True,
                title="인천 · 강화도 연안\n조류 흐름과 해양쓰레기 집적 시뮬레이션",
                subtitle="조석(M2+S2) 포텐셜 흐름 모델 · 라그랑주 입자추적 · 30일 모의",
                panel_title="인천·강화 연안 조류와 해양쓰레기 집적 시뮬레이션", scalebar_km=10,
                segs=an["segs"], rank=an["rank"][:6], off_lon=g.x / G.M_PER_DEG_LON + C.LON_MIN, off_lat=g.y / G.M_PER_DEG_LAT + C.LAT_MIN,
                off_val=an["offshore"], off_thr=an["offshore_thr"], prog=_regional_prog(dom, res, an), idx=np.arange(res["snap_xy"].shape[1]),
                stats_mode="global", n_tracer=2600, dt_vis=150.0, line_fraction="상위 15 %")


def _regional_prog(dom, res, an):
    g = dom["grid"]
    seg_cells = [g.cell_index(*G.lonlat_to_xy(s["lon"], s["lat"])) for s in an["segs"]]
    prog = np.zeros((len(res["snap_t"]), len(seg_cells)), np.float32)
    for k in range(len(res["snap_t"])):
        d = A.coast_density_grid(dom, res["beach_hist"][k])
        for n, (i, j) in enumerate(seg_cells):
            prog[k, n] = d[i, j].mean()
    return np.clip(prog / np.maximum(prog[-1], 1e-6), 0, 1)


def island_scene(dom, res, ian):
    isl = ian["isl"]; view = ian["view"]
    img, bbox, credit = B.get_basemap(dom, bbox=view, tag=ian["key"], out_w=2000)
    # 화면에 한 번이라도 들어오는 입자만
    lon = res["snap_xy"][..., 0] / G.M_PER_DEG_LON + C.LON_MIN
    lat = res["snap_xy"][..., 1] / G.M_PER_DEG_LAT + C.LAT_MIN
    inv = (lon >= view[0]) & (lon <= view[1]) & (lat >= view[2]) & (lat <= view[3]) & (res["snap_state"] >= 1) & (res["snap_state"] <= 2)
    idx = np.flatnonzero(inv.any(axis=0))
    width_km = (view[1] - view[0]) * G.M_PER_DEG_LON / 1000
    dt_vis = float(np.clip(150.0 * width_km / 97.0 * 2.5, 20.0, 150.0))
    pct = int(round(isl["top_fraction"] * 100))
    return dict(name=ian["key"], view=view, basemap=img, credit=credit, labels=isl["labels"], show_sources=False,
                title=f"{isl['name']} 해안\n해양쓰레기 집적 시뮬레이션",
                subtitle="인천·강화 지역 모의(100 m 격자, 60,000 입자)에서 섬 주변을 확대 · 섬 자체 해안선 기준 집적 구간",
                panel_title=f"{isl['name']} 주변 조류와 해안 쓰레기 집적 시뮬레이션", scalebar_km=isl["scalebar_km"],
                segs=ian["segs"], rank=ian["rank"][:6], off_lon=ian["off_lon"], off_lat=ian["off_lat"], off_val=ian["off_val"],
                off_thr=ian["off_thr"], prog=ian["prog"], idx=idx, stats_mode="view", n_tracer=isl["n_tracer"], dt_vis=dt_vis,
                line_fraction=f"섬 해안 상위 {pct} %")


# ---------------------------------------------------------------- 준비
def prepare(dom, model, res, scene):
    seg, t_sim, k_snap, dt_tr = plan_frames(res["snap_t"], model, scene["dt_vis"])
    print(f"[render:{scene['name']}] 총 {len(seg)} 프레임 ({len(seg) / FPS:.0f} s), 입자 {len(scene['idx'])}")
    tr_pos, tr_spd, tr_age = precompute_tracers(dom, model, t_sim, dt_tr, scene["view"], scene["n_tracer"])
    idx = scene["idx"]
    snap_xy = res["snap_xy"][:, idx]; snap_state = res["snap_state"][:, idx]
    disp_xy = tidal_average_positions(snap_xy, snap_state)
    view = scene["view"]
    lon = snap_xy[..., 0] / G.M_PER_DEG_LON + C.LON_MIN; lat = snap_xy[..., 1] / G.M_PER_DEG_LAT + C.LAT_MIN
    in_view = (lon >= view[0]) & (lon <= view[1]) & (lat >= view[2]) & (lat <= view[3])
    ever_in = np.logical_or.accumulate(in_view & (snap_state >= 1), axis=0)
    eta_t = np.arange(0, (C.SIM_DAYS + 1) * 86400, 300.0)
    stages = [model.tide_stage(t) for t in t_sim]
    segs = scene["segs"]
    np.savez(data_path(scene["name"]), seg=seg, t_sim=t_sim, k_snap=k_snap, tr_pos=tr_pos, tr_spd=tr_spd, tr_age=tr_age,
             disp_xy=disp_xy, snap_xy=snap_xy, snap_state=snap_state, in_view=in_view, ever_in=ever_in, snap_t=res["snap_t"],
             prog=scene["prog"], eta_t=eta_t, eta=model.sea_level(eta_t), wind=res["wind"],
             stage=np.array([s[0] for s in stages]), spring=np.array([s[1] for s in stages]),
             han_q=np.array([model.han_discharge(t) for t in t_sim]),
             seg_lon=np.array([s["lon"] for s in segs], dtype=object), seg_lat=np.array([s["lat"] for s in segs], dtype=object),
             seg_level=np.array([s["level"] for s in segs], float),
             rank_names=np.array([e["name"] for e in scene["rank"]]), rank_lon=np.array([e["lon"] for e in scene["rank"]], float),
             rank_lat=np.array([e["lat"] for e in scene["rank"]], float),
             off_lon=scene["off_lon"], off_lat=scene["off_lat"], off_val=scene["off_val"], off_thr=scene["off_thr"],
             view=np.array(view, float), basemap=scene["basemap"], credit=scene["credit"],
             label_text=np.array([l[0] for l in scene["labels"]]), label_lon=np.array([l[1] for l in scene["labels"]], float),
             label_lat=np.array([l[2] for l in scene["labels"]], float), label_fs=np.array([l[3] for l in scene["labels"]], float),
             show_sources=scene["show_sources"], title=scene["title"], subtitle=scene["subtitle"], panel_title=scene["panel_title"],
             scalebar_km=scene["scalebar_km"], stats_mode=scene["stats_mode"], line_fraction=scene["line_fraction"], n_total=res["snap_xy"].shape[1])
    return len(seg), data_path(scene["name"])


# ---------------------------------------------------------------- 프레임 렌더러
class FrameRenderer:
    def __init__(self, data):
        self.d = d = data
        view = tuple(float(v) for v in d["view"])
        self.view = view
        self.stats_mode = str(d["stats_mode"])
        fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor="#0b0f14")
        self.fig = fig
        aspect = ((view[1] - view[0]) * G.M_PER_DEG_LON) / ((view[3] - view[2]) * G.M_PER_DEG_LAT)   # 가로/세로
        map_h = 0.955
        map_w = map_h * H * aspect / W
        if map_w > 0.535:
            map_w = 0.535; map_h = map_w * W / (H * aspect)
        ax = fig.add_axes([0.012, 0.5 - map_h / 2, map_w, map_h])
        self.ax = ax
        ax.imshow(d["basemap"], extent=[view[0], view[1], view[2], view[3]], aspect=G.M_PER_DEG_LAT / G.M_PER_DEG_LON,
                  interpolation="bilinear", zorder=0)
        ax.set_xlim(view[0], view[1]); ax.set_ylim(view[2], view[3])
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_edgecolor("#3a4a5a")
        for name, lon, lat, fs in zip(d["label_text"], d["label_lon"], d["label_lat"], d["label_fs"]):
            if view[0] < lon < view[1] and view[2] < lat < view[3]:
                ax.text(lon, lat, str(name), color="white", fontsize=float(fs), ha="center", va="center", zorder=6, path_effects=OUTLINE, alpha=0.92)
        # 축척
        km = float(d["scalebar_km"])
        lon0 = view[0] + 0.03 * (view[1] - view[0]); lat0 = view[2] + 0.03 * (view[3] - view[2])
        ax.plot([lon0, lon0 + km * 1000 / G.M_PER_DEG_LON], [lat0, lat0], color="white", lw=3, zorder=7, path_effects=OUTLINE)
        ax.text(lon0 + km * 500 / G.M_PER_DEG_LON, lat0 + 0.008 * (view[3] - view[2]) / 0.9, f"{km:g} km", color="white", fontsize=10, ha="center", zorder=7, path_effects=OUTLINE)
        ax.text(view[1] - 0.01 * (view[1] - view[0]), view[2] + 0.008 * (view[3] - view[2]), "배경: " + str(d["credit"]), color="white", fontsize=8,
                ha="right", zorder=7, path_effects=OUTLINE, alpha=0.8)
        # 스트리크
        self.lc_dim = LineCollection([], linewidths=0.9, alpha=0.35, zorder=3, capstyle="round")
        self.lc_bright = LineCollection([], linewidths=1.5, alpha=0.8, zorder=4, capstyle="round")
        ax.add_collection(self.lc_dim); ax.add_collection(self.lc_bright)
        # 쓰레기
        self.sc_float = ax.scatter([], [], s=7, c="#ffa726", edgecolors="none", alpha=0.9, zorder=5)
        self.sc_beach = ax.scatter([], [], s=2.5, c="#4a0a0a", edgecolors="none", alpha=0.45, zorder=5)
        # 발생원
        self.src_art = []
        if bool(d["show_sources"]):
            for s in C.SOURCES:
                lon, lat = {"point": s.get("lonlat"), "han_inlet": (126.80, 37.60), "imjin_inlet": (126.72, 37.86), "offshore": (125.98, 37.30)}[s["kind"]]
                m, = ax.plot(lon, lat, marker="o", ms=9, mfc="#ffd54f", mec="black", mew=1.2, ls="none", zorder=8)
                t = ax.text(lon, lat - 0.018, "▲ " + s["name"], color="#ffe082", fontsize=9, ha="center", va="top", zorder=8, path_effects=OUTLINE)
                self.src_art += [m, t]
        # 집적 라인
        segs = [np.column_stack([lo, la]) for lo, la in zip(d["seg_lon"], d["seg_lat"])]
        self.level = np.asarray(d["seg_level"], float)
        self.lc_glow = LineCollection(segs, linewidths=11, zorder=6, capstyle="round", joinstyle="round")
        self.lc_red = LineCollection(segs, linewidths=4.5, zorder=6, capstyle="round", joinstyle="round")
        ax.add_collection(self.lc_glow); ax.add_collection(self.lc_red)
        self.offshore_cs = None
        # 순위 라벨 (최종 구간)
        self.rank_texts = []
        for n, (name, lon, lat) in enumerate(zip(d["rank_names"], d["rank_lon"], d["rank_lat"])):
            t = ax.text(lon, lat + 0.012 * (view[3] - view[2]) / 0.9, f"{n + 1}", color="white", fontsize=13, fontweight="bold", ha="center", va="bottom", zorder=9,
                        bbox=dict(boxstyle="circle,pad=0.25", fc=RED, ec="white", lw=1.2, alpha=0.9))
            t.set_visible(False)
            self.rank_texts.append(t)
        # 타이틀 오버레이
        self.title_rect = Rectangle((view[0], view[2]), view[1] - view[0], view[3] - view[2], fc="black", alpha=0.55, zorder=20)
        ax.add_patch(self.title_rect)
        self.title_txt = ax.text(0.5, 0.56, str(d["title"]), transform=ax.transAxes, color="white", fontsize=30, fontweight="bold",
                                 ha="center", va="center", zorder=21, linespacing=1.5)
        self.title_sub = ax.text(0.5, 0.40, str(d["subtitle"]), transform=ax.transAxes, color="#cfd8dc", fontsize=14, ha="center", va="center",
                                 zorder=21, wrap=True)
        self._build_panel()

    # ------------------------------------------------------------ 우측 패널
    def _build_panel(self):
        fig = self.fig; d = self.d
        x0 = 0.565
        fig.text(x0, 0.955, str(d["panel_title"]), color="white", fontsize=20, fontweight="bold", va="center")
        self.t_seg = fig.text(x0, 0.905, "", color="#80deea", fontsize=16, va="center", fontweight="bold")
        self.t_time = fig.text(x0, 0.862, "", color="white", fontsize=14, va="center")
        self.t_tide = fig.text(x0, 0.830, "", color="#b0bec5", fontsize=12.5, va="center")
        self.ax_eta = fig.add_axes([x0 + 0.005, 0.655, 0.405, 0.15], facecolor="#121a22")
        self.ax_eta.tick_params(colors="#90a4ae", labelsize=9)
        for sp in self.ax_eta.spines.values():
            sp.set_edgecolor("#37474f")
        self.ax_eta.set_title("모델 조위 (인천항, m)", color="#b0bec5", fontsize=10, loc="left", pad=4)
        self.eta_line, = self.ax_eta.plot([], [], color="#4fc3f7", lw=1.5)
        self.eta_dot, = self.ax_eta.plot([], [], "o", color="#ffeb3b", ms=7)
        self.ax_eta.axhline(0, color="#37474f", lw=0.8)
        self.ax_wind = fig.add_axes([x0 + 0.33, 0.50, 0.075, 0.13], facecolor="none")
        self.ax_wind.set_xlim(-1, 1); self.ax_wind.set_ylim(-1, 1); self.ax_wind.axis("off")
        self.ax_wind.add_patch(plt.Circle((0, 0), 0.95, fc="#121a22", ec="#37474f"))
        self.wind_arrow = self.ax_wind.annotate("", xy=(0.5, 0), xytext=(-0.5, 0), arrowprops=dict(arrowstyle="-|>", color="#80cbc4", lw=2.5))
        self.t_wind = fig.text(x0 + 0.3675, 0.49, "", color="#b0bec5", fontsize=10, ha="center", va="top")
        y = 0.615
        fig.text(x0, y, "범례", color="white", fontsize=13, fontweight="bold", va="center")
        items = [("line", "#dff1ff", "조류 흐름(스트리크, 색=유속)"), ("dot", "#ffa726", "부유 쓰레기 입자"),
                 ("dot", "#8e0000", "좌초(해안 집적) 입자"), ("redline", RED, f"집적 예상 해안 (좌초 밀도 {d['line_fraction']}, 빨간 반투명 라인)"),
                 ("dash", RED, "해상 체류 밀도 상위 5 % (수렴역)")]
        if bool(d["show_sources"]):
            items.append(("src", "#ffd54f", "쓰레기 발생원"))
        for n, (kind, col, label) in enumerate(items):
            yy = y - 0.028 * (n + 1)
            if kind == "line":
                fig.add_artist(plt.Line2D([x0 + 0.005, x0 + 0.03], [yy, yy], color=col, lw=2))
            elif kind == "redline":
                fig.add_artist(plt.Line2D([x0 + 0.005, x0 + 0.03], [yy, yy], color=col, lw=6, alpha=0.6))
            elif kind == "dash":
                fig.add_artist(plt.Line2D([x0 + 0.005, x0 + 0.03], [yy, yy], color=col, lw=1.8, ls="--", alpha=0.8))
            elif kind == "dot":
                fig.add_artist(plt.Line2D([x0 + 0.0175], [yy], marker="o", color=col, ms=6, ls="none"))
            else:
                fig.add_artist(plt.Line2D([x0 + 0.0175], [yy], marker="o", mfc=col, mec="black", ms=8, ls="none"))
            fig.text(x0 + 0.04, yy, label, color="#eceff1", fontsize=11, va="center")
        self.ax_cb = fig.add_axes([x0 + 0.005, 0.400, 0.25, 0.018])
        self.ax_cb.imshow(np.linspace(0, 1, 256)[None, :], aspect="auto", cmap=SPEED_CMAP, extent=[0, 2, 0, 1])
        self.ax_cb.set_yticks([]); self.ax_cb.tick_params(colors="#b0bec5", labelsize=9)
        self.ax_cb.set_xticks([0, 0.5, 1, 1.5, 2])
        for sp in self.ax_cb.spines.values():
            sp.set_edgecolor("#37474f")
        fig.text(x0 + 0.26, 0.409, "유속 (m/s)", color="#b0bec5", fontsize=10, va="center")
        self.ax_bar = fig.add_axes([x0 + 0.075, 0.228, 0.33, 0.100], facecolor="none")
        self.ax_bar.set_xlim(0, 100); self.ax_bar.set_ylim(-0.6, 2.6); self.ax_bar.axis("off")
        self.bars = self.ax_bar.barh([2, 1, 0], [0, 0, 0], color=["#ffa726", "#c62828", "#78909c"], height=0.6)
        self.bar_txt = [self.ax_bar.text(1, k, "", color="white", fontsize=10.5, va="center") for k in (2, 1, 0)]
        labs = ("부유 중", "해안 좌초", "영역 밖 유출") if self.stats_mode == "global" else ("화면 내 부유", "화면 내 좌초", "통과·이탈")
        for k, lab in zip((2, 1, 0), labs):
            fig.text(x0, 0.228 + 0.100 * (k + 0.6) / 3.2, lab, color="#eceff1", fontsize=11, va="center")
        self.t_rel = fig.text(x0, 0.345, "", color="#b0bec5", fontsize=11, va="center")
        self.t_rank_title = fig.text(x0, 0.200, "", color="white", fontsize=13, fontweight="bold", va="center")
        self.t_rank = fig.text(x0, 0.182, "", color="#ffcdd2", fontsize=11, va="top", linespacing=1.3)
        fig.text(x0, 0.042, FOOTNOTE, color="#78909c", fontsize=8.8, va="center", linespacing=1.5)

    # ------------------------------------------------------------ 프레임 갱신
    def draw(self, f):
        d = self.d
        seg, t, k = int(d["seg"][f]), float(d["t_sim"][f]), int(d["k_snap"][f])
        f0 = max(0, f - TRAIL + 1)
        P = d["tr_pos"][f0:f + 1]
        age = d["tr_age"][f]; L = P.shape[0]
        valid = np.minimum(age, L).astype(int)
        cols = SPEED_CMAP(np.clip(d["tr_spd"][f].astype(np.float32) / 2.0, 0, 1))
        lonP = P[..., 0] / G.M_PER_DEG_LON + C.LON_MIN; latP = P[..., 1] / G.M_PER_DEG_LAT + C.LAT_MIN
        segs_b, segs_d, cb, cd = [], [], [], []
        for n in range(P.shape[1]):
            v = valid[n]
            if v < 2:
                continue
            pts = np.column_stack([lonP[L - v:, n], latP[L - v:, n]])
            segs_d.append(pts); cd.append(cols[n]); segs_b.append(pts[-min(v, 3):]); cb.append(cols[n])
        self.lc_dim.set_segments(segs_d); self.lc_dim.set_color(cd)
        self.lc_bright.set_segments(segs_b); self.lc_bright.set_color(cb)
        show_debris = seg >= 2
        st = d["snap_state"][k]
        if show_debris:
            xy = d["disp_xy"][k]; fl = st == 1; be = st == 2
            self.sc_float.set_offsets(np.column_stack(G.xy_to_lonlat(xy[fl, 0], xy[fl, 1])) if fl.any() else np.empty((0, 2)))
            bxy = d["snap_xy"][k]
            self.sc_beach.set_offsets(np.column_stack(G.xy_to_lonlat(bxy[be, 0], bxy[be, 1])) if be.any() else np.empty((0, 2)))
        else:
            self.sc_float.set_offsets(np.empty((0, 2))); self.sc_beach.set_offsets(np.empty((0, 2)))
        for a in self.src_art:
            a.set_visible(show_debris)
        if show_debris:
            pr = d["prog"][k]; fade = np.clip((k - 36) / 72.0, 0, 1)
            a_main = np.clip(0.25 + 0.6 * self.level, 0.3, 0.85) * pr * fade
            self.lc_red.set_color([(1.0, 0.13, 0.13, a) for a in a_main]); self.lc_glow.set_color([(1.0, 0.2, 0.2, 0.3 * a) for a in a_main])
            self.lc_red.set_visible(True); self.lc_glow.set_visible(True)
        else:
            self.lc_red.set_visible(False); self.lc_glow.set_visible(False)
        if seg == 3 and self.offshore_cs is None:
            LONo, LATo = np.meshgrid(d["off_lon"], d["off_lat"])
            self.offshore_cs = self.ax.contour(LONo, LATo, d["off_val"], levels=[float(d["off_thr"])], colors=[RED], linestyles="--",
                                               linewidths=1.6, alpha=0.65, zorder=6)
            for tx in self.rank_texts:
                tx.set_visible(True)
        self.title_rect.set_visible(seg == 0); self.title_txt.set_visible(seg == 0); self.title_sub.set_visible(seg == 0)
        names = {0: "", 1: "1부 · 조류(밀물·썰물) 흐름 — 한 조석주기", 2: "2부 · 쓰레기 이동과 해안 좌초 — 30일 타임랩스", 3: "3부 · 집적 예상 해안 (빨간 반투명 라인)"}
        self.t_seg.set_text(names[seg])
        day = int(t // 86400); hh = int((t % 86400) // 3600); mm = int((t % 3600) // 60)
        speed_note = "(실시간의 2,500배)" if seg == 1 else "(1초 = 20시간)" if seg == 2 else ""
        self.t_time.set_text(f"모의 시간  D+{day:02d}  {hh:02d}:{mm:02d}  {speed_note}")
        self.t_tide.set_text(f"조석 상태: {d['stage'][f]} · {d['spring'][f]}     한강 유량 {float(d['han_q'][f]):,.0f} m³/s")
        if seg == 1:
            t0, t1 = d["t_sim"][N_TITLE], d["t_sim"][N_TITLE] + C.M2_PERIOD
        else:
            t0, t1 = t - 1.5 * 86400, t + 1.5 * 86400
        m = (d["eta_t"] >= t0) & (d["eta_t"] <= t1)
        self.eta_line.set_data(d["eta_t"][m] / 3600, d["eta"][m]); self.eta_dot.set_data([t / 3600], [float(np.interp(t, d["eta_t"], d["eta"]))])
        self.ax_eta.set_xlim(t0 / 3600, t1 / 3600); self.ax_eta.set_ylim(-4.2, 4.2); self.ax_eta.set_xlabel("경과 시간 (h)", color="#90a4ae", fontsize=9)
        wx, wy = d["wind"][int(t // 3600) % len(d["wind"])]
        ws = float(np.hypot(wx, wy)); ang = np.arctan2(wy, wx); r = 0.75 * min(ws / 6.0, 1.0) + 0.1
        self.wind_arrow.xy = (r * np.cos(ang), r * np.sin(ang)); self.wind_arrow.set_position((-r * np.cos(ang), -r * np.sin(ang)))
        self.t_wind.set_text(f"바람 {ws:.1f} m/s\n(풍향 {self._wind_name(wx, wy)})")
        if show_debris:
            if self.stats_mode == "global":
                cnt = np.bincount(st, minlength=4); base = max(int(cnt[1:].sum()), 1); vals = [cnt[1], cnt[2], cnt[3]]
                self.t_rel.set_text(f"방출 입자 {base:,} / {int(d['n_total']):,}")
            else:
                iv = d["in_view"][k]; ev = d["ever_in"][k]
                fl_in = int((iv & (st == 1)).sum()); be_in = int((iv & (st == 2)).sum()); base = max(int(ev.sum()), 1)
                vals = [fl_in, be_in, base - fl_in - be_in]
                self.t_rel.set_text(f"화면 진입 입자 {base:,} / 전체 {int(d['n_total']):,}")
            for b, v, tx in zip(self.bars, vals, self.bar_txt):
                b.set_width(100 * v / base); tx.set_text(f"{100 * v / base:4.1f} %  ({v:,})")
        else:
            for b, tx in zip(self.bars, self.bar_txt):
                b.set_width(0); tx.set_text("")
            self.t_rel.set_text("")
        if seg == 3:
            self.t_rank_title.set_text("집적 예상 상위 해안 (좌초 밀도 순)")
            self.t_rank.set_text("\n".join(f"{n + 1}. {nm}" for n, nm in enumerate(d["rank_names"])))
        else:
            self.t_rank_title.set_text(""); self.t_rank.set_text("")
        self.fig.canvas.draw()
        return np.ascontiguousarray(np.frombuffer(self.fig.canvas.buffer_rgba(), np.uint8).reshape(H, W, 4)[..., :3])

    @staticmethod
    def _wind_name(wx, wy):
        ang = (np.degrees(np.arctan2(-wx, -wy)) + 360) % 360
        return ["북", "북동", "동", "남동", "남", "남서", "서", "북서"][int((ang + 22.5) // 45) % 8] + "풍"


# ---------------------------------------------------------------- 병렬 인코딩
def _render_chunk(args):
    cid, f0, f1, dpath, chunk_dir = args
    data = dict(np.load(dpath, allow_pickle=True))
    r = FrameRenderer(data)
    os.makedirs(chunk_dir, exist_ok=True)
    out = os.path.join(chunk_dir, f"chunk_{cid:02d}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(r.draw(f).tobytes())
        if (f - f0) % 100 == 0:
            print(f"  [chunk {cid}] frame {f}/{f1}", flush=True)
    p.stdin.close(); p.wait()
    return out


def render_video(nframes, dpath, out_path, workers=4, crf_final=26):
    name = os.path.splitext(os.path.basename(out_path))[0]
    chunk_dir = os.path.join(C.OUT_DIR, f"_chunks_{name}")
    edges = np.linspace(0, nframes, workers + 1).astype(int)
    jobs = [(i, int(edges[i]), int(edges[i + 1]), dpath, chunk_dir) for i in range(workers)]
    with mp.get_context("spawn").Pool(workers) as pool:
        chunks = pool.map(_render_chunk, jobs)
    lst = os.path.join(chunk_dir, "list.txt")
    with open(lst, "w") as f:
        for c in chunks:
            f.write(f"file '{c}'\n")
    raw = os.path.join(chunk_dir, "concat.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", raw], check=True)
    # 최종: 용량 절감 재인코딩 (저장소 커밋용)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-c:v", "libx264", "-preset", "slow", "-crf", str(crf_final),
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path], check=True)
    print(f"[render] 영상 저장: {out_path}")
    return out_path


def render_stills(dpath, frames, prefix="still"):
    data = dict(np.load(dpath, allow_pickle=True))
    r = FrameRenderer(data)
    from PIL import Image
    paths = []
    for f in frames:
        p = os.path.join(C.OUT_DIR, f"{prefix}_{f:05d}.png")
        Image.fromarray(r.draw(f)).save(p); paths.append(p)
    return paths


# ---------------------------------------------------------------- 정지 지도
def hotspot_figure(dom, an, path=None):
    """지역 전체 최종 집적 예상 지도 (잔차류 수렴역 포함)."""
    path = path or os.path.join(C.OUT_DIR, "hotspot_map.png")
    img, _, credit = B.get_basemap(dom)
    fig, ax = plt.subplots(figsize=(13, 13.3), dpi=150)
    ax.imshow(img, extent=[C.LON_MIN, C.LON_MAX, C.LAT_MIN, C.LAT_MAX], aspect=G.M_PER_DEG_LAT / G.M_PER_DEG_LON, interpolation="bilinear")
    g = dom["grid"]
    _draw_residual(ax, g, an)
    ax.contour(g.LON, g.LAT, an["offshore"], levels=[an["offshore_thr"]], colors=[RED], linestyles="--", linewidths=1.6, alpha=0.7)
    _draw_segs(ax, an["segs"])
    for name, lon, lat, fs in C.PLACE_LABELS:
        ax.text(lon, lat, name, color="white", fontsize=fs * 0.85, ha="center", va="center", path_effects=OUTLINE)
    _draw_rank(ax, an["rank"][:8], 0.012)
    ax.set_xlim(C.LON_MIN, C.LON_MAX); ax.set_ylim(C.LAT_MIN, C.LAT_MAX)
    ax.set_xlabel("경도"); ax.set_ylabel("위도")
    ax.set_title("해양쓰레기 집적 예상 해안 (빨간 반투명 라인 = 좌초 밀도 상위 15 %)\n"
                 "점선 = 해상 체류 밀도 상위 5 %, 분홍 음영 = 조석 잔차류 수렴역(∇·u < 0), 흰 화살표 = 잔차류", fontsize=12)
    txt = "\n".join(f"{n + 1}. {e['name']}  ({e['length_km']:.1f} km)" for n, e in enumerate(an["rank"][:8]))
    ax.text(0.015, 0.015, "집적 예상 상위 해안 (좌초 밀도 순)\n" + txt, transform=ax.transAxes, va="bottom", fontsize=10.5, color="white",
            bbox=dict(fc="black", alpha=0.6, ec="none"))
    ax.text(0.99, 0.01, "배경: " + credit, transform=ax.transAxes, ha="right", fontsize=8, color="white", path_effects=OUTLINE)
    fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print(f"[render] 집적 지도 저장: {path}")
    return path


def island_figure(dom, ian, model=None, path=None):
    """섬 상세 최종 집적 예상 지도."""
    key, isl, view = ian["key"], ian["isl"], ian["view"]
    path = path or os.path.join(C.OUT_DIR, f"hotspot_map_{key}.png")
    img, _, credit = B.get_basemap(dom, bbox=view, tag=key, out_w=2000)
    g = dom["grid"]
    aspect = ((view[1] - view[0]) * G.M_PER_DEG_LON) / ((view[3] - view[2]) * G.M_PER_DEG_LAT)
    fig, ax = plt.subplots(figsize=(12, 12 / aspect + 1.2), dpi=150)
    ax.imshow(img, extent=[view[0], view[1], view[2], view[3]], aspect=G.M_PER_DEG_LAT / G.M_PER_DEG_LON, interpolation="bilinear")
    if model is not None:
        ures, vres, div = A.residual_convergence(dom, model, bbox=view)
        _draw_residual(ax, g, dict(ures=ures, vres=vres, div=div), step=max(2, int(round(600 / g.dx))), scale=0.8)
    LONo, LATo = np.meshgrid(ian["off_lon"], ian["off_lat"])
    ax.contour(LONo, LATo, ian["off_val"], levels=[ian["off_thr"]], colors=[RED], linestyles="--", linewidths=1.6, alpha=0.7)
    _draw_segs(ax, ian["segs"])
    for name, lon, lat, fs in isl["labels"]:
        if view[0] < lon < view[1] and view[2] < lat < view[3]:
            ax.text(lon, lat, name, color="white", fontsize=fs * 0.9, ha="center", va="center", path_effects=OUTLINE)
    _draw_rank(ax, ian["rank"][:8], 0.012 * (view[3] - view[2]) / 0.9)
    ax.set_xlim(view[0], view[1]); ax.set_ylim(view[2], view[3])
    ax.set_xlabel("경도"); ax.set_ylabel("위도")
    pct = int(round(isl["top_fraction"] * 100))
    ax.set_title(f"{isl['name']} 해양쓰레기 집적 예상 해안 (빨간 반투명 라인 = 섬 해안 좌초 밀도 상위 {pct} %)\n"
                 "점선 = 해상 체류 밀도 상위 5 %, 분홍 음영 = 조석 잔차류 수렴역, 흰 화살표 = 잔차류", fontsize=11.5)
    txt = "\n".join(f"{n + 1}. {e['name']}  ({e['length_km']:.1f} km)" for n, e in enumerate(ian["rank"][:8]))
    ax.text(0.015, 0.015, "집적 예상 상위 해안 (좌초 밀도 순)\n" + txt, transform=ax.transAxes, va="bottom", fontsize=10.5, color="white",
            bbox=dict(fc="black", alpha=0.6, ec="none"))
    ax.text(0.99, 0.01, "배경: " + credit, transform=ax.transAxes, ha="right", fontsize=8, color="white", path_effects=OUTLINE)
    fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print(f"[render] 섬 집적 지도 저장: {path}")
    return path


def _draw_residual(ax, g, an, step=10, scale=1.5):
    if "div" not in an:
        return
    conv = -an["div"] * 86400
    ax.contourf(g.LON, g.LAT, np.where(conv > 0, conv, np.nan), levels=[0.05, 0.1, 0.2, 0.5, 5], colors=["#ff80ab", "#ff4081", "#f50057", "#c51162"], alpha=0.25)
    s = step
    ax.quiver(g.LON[::s, ::s], g.LAT[::s, ::s], an["ures"][::s, ::s], an["vres"][::s, ::s], color="white", scale=scale, width=0.0015, alpha=0.75)


def _draw_segs(ax, segs):
    for s in segs:
        a = np.clip(0.25 + 0.6 * s["level"], 0.3, 0.85)
        ax.plot(s["lon"], s["lat"], color=RED, lw=11, alpha=0.3 * a, solid_capstyle="round")
        ax.plot(s["lon"], s["lat"], color=RED, lw=4.5, alpha=a, solid_capstyle="round")


def _draw_rank(ax, rank, dy):
    for n, e in enumerate(rank):
        ax.text(e["lon"], e["lat"] + dy, f"{n + 1}", color="white", fontsize=12, fontweight="bold", ha="center", va="bottom",
                bbox=dict(boxstyle="circle,pad=0.25", fc=RED, ec="white", lw=1.2, alpha=0.9))


if __name__ == "__main__":
    dom = G.build_domain(verbose=False)
    model = CU.TidalFlowModel(dom, verbose=False)
    res = dict(np.load(os.path.join(C.OUT_DIR, "sim_results.npz")))
    an = A.analyze(dom, res, model=model)
    hotspot_figure(dom, an)
    n, dpath = prepare(dom, model, res, regional_scene(dom, res, an))
    if "--stills" in sys.argv:
        print(render_stills(dpath, [30, N_TITLE + 200, N_TITLE + N_TIDE + 400, n - 10]))
    else:
        render_video(n, dpath, os.path.join(C.OUT_DIR, "incheon_debris_simulation.mp4"), workers=int(os.environ.get("WORKERS", "4")))
