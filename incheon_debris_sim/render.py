"""영상 렌더링: 배경지도 + 조류 흐름(스트리크) + 쓰레기 입자 + 집적 예상 해안(빨간 반투명 라인) → MP4.

구성 (30 fps)
  1부 타이틀 3 s → 2부 조류 흐름(한 조석주기 12.42 h 를 18 s 로) → 3부 쓰레기 이동·좌초 30일 타임랩스(36 s)
  → 4부 최종 집적 예상 지도(6 s)
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
N_TRACER, TRAIL, TRACER_AGE = 2600, 8, 110
DT_VIS = 150.0
SPEED_CMAP = LinearSegmentedColormap.from_list("flow", ["#7fb3ff", "#dff1ff", "#ffffff", "#fff4a0", "#ffb347"])
RED = "#ff2020"
RENDER_DATA = os.path.join(C.OUT_DIR, "_render_data.npz")
CHUNK_DIR = os.path.join(C.OUT_DIR, "_chunks")


# ---------------------------------------------------------------- 프레임 계획
def plan_frames(snap_t, model):
    """각 프레임의 (구간, 모의시각, 스냅샷 인덱스, 추적자 dt)"""
    # 조류 구간: 인천 저조 시각부터 한 주기
    tt = np.arange(0, 2 * C.M2_PERIOD, 60.0)
    eta = model.sea_level(tt)
    t_lw = float(tt[np.argmin(eta[: int(C.M2_PERIOD / 60)])])
    seg, t_sim, k_snap, dt_tr = [], [], [], []
    for f in range(N_TITLE):
        seg.append(0); t_sim.append(t_lw); k_snap.append(0); dt_tr.append(DT_VIS)
    for f in range(N_TIDE):
        seg.append(1); t_sim.append(t_lw + f / N_TIDE * C.M2_PERIOD); k_snap.append(0); dt_tr.append(C.M2_PERIOD / N_TIDE)
    for k in range(len(snap_t)):
        seg.append(2); t_sim.append(float(snap_t[k])); k_snap.append(k); dt_tr.append(DT_VIS)
    for f in range(N_FINAL):
        seg.append(3); t_sim.append(float(snap_t[-1])); k_snap.append(len(snap_t) - 1); dt_tr.append(DT_VIS)
    return np.array(seg), np.array(t_sim), np.array(k_snap), np.array(dt_tr)


# ---------------------------------------------------------------- 추적자(스트리크) 사전 계산
def precompute_tracers(dom, model, t_sim, dt_tr, seed=7):
    rng = np.random.default_rng(seed)
    g = dom["grid"]; water = dom["water"]
    cand = np.flatnonzero(water.ravel())

    def spawn(n):
        pick = rng.choice(cand, n)
        ii, jj = np.unravel_index(pick, g.shape)
        return (jj + rng.random(n)) * g.dx, (ii + rng.random(n)) * g.dx

    x, y = spawn(N_TRACER)
    age = rng.integers(0, TRACER_AGE, N_TRACER)
    nf = len(t_sim)
    pos = np.zeros((nf, N_TRACER, 2), np.float32)
    spd = np.zeros((nf, N_TRACER), np.float16)
    ages = np.zeros((nf, N_TRACER), np.int16)
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
        if f % 300 == 0:
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


# ---------------------------------------------------------------- 준비
def prepare(dom, model, res, an):
    seg, t_sim, k_snap, dt_tr = plan_frames(res["snap_t"], model)
    print(f"[render] 총 {len(seg)} 프레임 ({len(seg) / FPS:.0f} s)")
    print("[render] 추적자 사전계산")
    tr_pos, tr_spd, tr_age = precompute_tracers(dom, model, t_sim, dt_tr)
    disp_xy = tidal_average_positions(res["snap_xy"], res["snap_state"])
    # 집적 라인 진행도: 스냅샷별 밀도 / 최종 밀도
    polys = G.get_coast_polygons()
    segs = an["segs"]
    nseg = len(segs)
    g = dom["grid"]
    seg_cells = []
    for s in segs:
        i, j = g.cell_index(*G.lonlat_to_xy(s["lon"], s["lat"]))
        seg_cells.append((i, j))
    prog = np.zeros((len(res["snap_t"]), nseg), np.float32)
    for k in range(len(res["snap_t"])):
        d = A.coast_density_grid(dom, res["beach_hist"][k])
        for n, (i, j) in enumerate(seg_cells):
            prog[k, n] = d[i, j].mean()
    final = np.maximum(prog[-1], 1e-6)
    prog = np.clip(prog / final, 0, 1)
    eta_t = np.arange(0, (C.SIM_DAYS + 1) * 86400, 300.0)
    eta = model.sea_level(eta_t)
    np.savez(RENDER_DATA, seg=seg, t_sim=t_sim, k_snap=k_snap, tr_pos=tr_pos, tr_spd=tr_spd, tr_age=tr_age,
             disp_xy=disp_xy, snap_xy=res["snap_xy"], snap_state=res["snap_state"], snap_t=res["snap_t"],
             prog=prog, eta_t=eta_t, eta=eta, wind=res["wind"], src=res["src"],
             seg_lon=np.array([s["lon"] for s in segs], dtype=object), seg_lat=np.array([s["lat"] for s in segs], dtype=object),
             seg_level=np.array([s["level"] for s in segs]), offshore=an["offshore"], offshore_thr=an["offshore_thr"],
             rank_names=np.array([e["name"] for e in an["rank"][:6]]), rank_lon=np.array([e["lon"] for e in an["rank"][:6]]),
             rank_lat=np.array([e["lat"] for e in an["rank"][:6]]), thr=an["thr"])
    return len(seg)


# ---------------------------------------------------------------- 프레임 렌더러
class FrameRenderer:
    def __init__(self, dom, data):
        self.dom, self.d = dom, data
        g = dom["grid"]
        self.LON, self.LAT = g.LON, g.LAT
        img, _, self.credit = B.get_basemap(dom)
        self.model_stage = CU.TidalFlowModel(dom, verbose=False)
        fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor="#0b0f14")
        self.fig = fig
        map_h = 0.955
        map_w = map_h * H * ((C.LON_MAX - C.LON_MIN) * G.M_PER_DEG_LON) / ((C.LAT_MAX - C.LAT_MIN) * G.M_PER_DEG_LAT) / W
        ax = fig.add_axes([0.012, 0.0225, map_w, map_h])
        self.ax = ax
        ax.imshow(img, extent=[C.LON_MIN, C.LON_MAX, C.LAT_MIN, C.LAT_MAX], aspect=G.M_PER_DEG_LAT / G.M_PER_DEG_LON,
                  interpolation="bilinear", zorder=0)
        ax.set_xlim(C.LON_MIN, C.LON_MAX); ax.set_ylim(C.LAT_MIN, C.LAT_MAX)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_edgecolor("#3a4a5a")
        outline = [pe.withStroke(linewidth=3, foreground="black")]
        for name, lon, lat, fs in C.PLACE_LABELS:
            ax.text(lon, lat, name, color="white", fontsize=fs, ha="center", va="center", zorder=6,
                    path_effects=outline, alpha=0.92)
        # 축척
        lon0, lat0 = C.LON_MIN + 0.03, C.LAT_MIN + 0.03
        ax.plot([lon0, lon0 + 10000 / G.M_PER_DEG_LON], [lat0, lat0], color="white", lw=3, zorder=7, path_effects=outline)
        ax.text(lon0 + 5000 / G.M_PER_DEG_LON, lat0 + 0.008, "10 km", color="white", fontsize=10, ha="center", zorder=7, path_effects=outline)
        ax.text(C.LON_MAX - 0.01, C.LAT_MIN + 0.008, "배경: " + self.credit, color="white", fontsize=8, ha="right", zorder=7,
                path_effects=outline, alpha=0.8)
        # 스트리크
        self.lc_dim = LineCollection([], linewidths=0.9, alpha=0.35, zorder=3, capstyle="round")
        self.lc_bright = LineCollection([], linewidths=1.5, alpha=0.8, zorder=4, capstyle="round")
        ax.add_collection(self.lc_dim); ax.add_collection(self.lc_bright)
        # 쓰레기
        self.sc_float = ax.scatter([], [], s=7, c="#ffa726", edgecolors="none", alpha=0.9, zorder=5)
        self.sc_beach = ax.scatter([], [], s=2.5, c="#4a0a0a", edgecolors="none", alpha=0.45, zorder=5)
        # 발생원
        self.src_art = []
        for s in C.SOURCES:
            if s["kind"] == "point":
                lon, lat = s["lonlat"]
            elif s["kind"] == "han_inlet":
                lon, lat = 126.80, 37.60
            elif s["kind"] == "imjin_inlet":
                lon, lat = 126.72, 37.86
            else:
                lon, lat = 125.98, 37.30
            m, = ax.plot(lon, lat, marker="o", ms=9, mfc="#ffd54f", mec="black", mew=1.2, ls="none", zorder=8)
            t = ax.text(lon, lat - 0.018, "▲ " + s["name"], color="#ffe082", fontsize=9, ha="center", va="top", zorder=8, path_effects=outline)
            self.src_art += [m, t]
        # 집적 라인
        segs = [np.column_stack([lo, la]) for lo, la in zip(self.d["seg_lon"], self.d["seg_lat"])]
        self.nseg = len(segs)
        self.level = np.asarray(self.d["seg_level"], float)
        self.lc_glow = LineCollection(segs, linewidths=11, zorder=6, capstyle="round", joinstyle="round")
        self.lc_red = LineCollection(segs, linewidths=4.5, zorder=6, capstyle="round", joinstyle="round")
        ax.add_collection(self.lc_glow); ax.add_collection(self.lc_red)
        self.offshore_cs = None
        # 순위 라벨 (최종 구간)
        self.rank_texts = []
        for n, (name, lon, lat) in enumerate(zip(self.d["rank_names"], self.d["rank_lon"], self.d["rank_lat"])):
            t = ax.text(lon, lat + 0.012, f"{n + 1}", color="white", fontsize=13, fontweight="bold", ha="center", va="bottom", zorder=9,
                        bbox=dict(boxstyle="circle,pad=0.25", fc=RED, ec="white", lw=1.2, alpha=0.9))
            t.set_visible(False)
            self.rank_texts.append(t)
        # 타이틀 오버레이
        self.title_rect = Rectangle((C.LON_MIN, C.LAT_MIN), C.LON_MAX - C.LON_MIN, C.LAT_MAX - C.LAT_MIN, fc="black", alpha=0.55, zorder=20)
        ax.add_patch(self.title_rect)
        self.title_txt = ax.text(0.5, 0.56, "인천 · 강화도 연안\n조류 흐름과 해양쓰레기 집적 시뮬레이션", transform=ax.transAxes, color="white",
                                 fontsize=30, fontweight="bold", ha="center", va="center", zorder=21, linespacing=1.5)
        self.title_sub = ax.text(0.5, 0.40, "조석(M2+S2) 포텐셜 흐름 모델 · 라그랑주 입자추적 · 30일 모의", transform=ax.transAxes,
                                 color="#cfd8dc", fontsize=15, ha="center", va="center", zorder=21)
        self._build_panel()

    # ------------------------------------------------------------ 우측 패널
    def _build_panel(self):
        fig = self.fig
        x0 = 0.565
        fig.text(x0, 0.955, "인천·강화 연안 조류와 해양쓰레기 집적 시뮬레이션", color="white", fontsize=21, fontweight="bold", va="center")
        self.t_seg = fig.text(x0, 0.905, "", color="#80deea", fontsize=16, va="center", fontweight="bold")
        self.t_time = fig.text(x0, 0.862, "", color="white", fontsize=14, va="center")
        self.t_tide = fig.text(x0, 0.830, "", color="#b0bec5", fontsize=12.5, va="center")
        # 조위 그래프
        self.ax_eta = fig.add_axes([x0 + 0.005, 0.655, 0.405, 0.15], facecolor="#121a22")
        self.ax_eta.tick_params(colors="#90a4ae", labelsize=9)
        for sp in self.ax_eta.spines.values():
            sp.set_edgecolor("#37474f")
        self.ax_eta.set_title("모델 조위 (인천항, m)", color="#b0bec5", fontsize=10, loc="left", pad=4)
        self.eta_line, = self.ax_eta.plot([], [], color="#4fc3f7", lw=1.5)
        self.eta_dot, = self.ax_eta.plot([], [], "o", color="#ffeb3b", ms=7)
        self.ax_eta.axhline(0, color="#37474f", lw=0.8)
        # 바람 화살표
        self.ax_wind = fig.add_axes([x0 + 0.33, 0.50, 0.075, 0.13], facecolor="none")
        self.ax_wind.set_xlim(-1, 1); self.ax_wind.set_ylim(-1, 1); self.ax_wind.axis("off")
        self.ax_wind.add_patch(plt.Circle((0, 0), 0.95, fc="#121a22", ec="#37474f"))
        self.wind_arrow = self.ax_wind.annotate("", xy=(0.5, 0), xytext=(-0.5, 0), arrowprops=dict(arrowstyle="-|>", color="#80cbc4", lw=2.5))
        self.t_wind = fig.text(x0 + 0.3675, 0.49, "", color="#b0bec5", fontsize=10, ha="center", va="top")
        # 범례
        y = 0.615
        fig.text(x0, y, "범례", color="white", fontsize=13, fontweight="bold", va="center")
        items = [("line", "#dff1ff", "조류 흐름(스트리크, 색=유속)"), ("dot", "#ffa726", "부유 쓰레기 입자"),
                 ("dot", "#8e0000", "좌초(해안 집적) 입자"), ("redline", RED, "집적 예상 해안 (좌초 밀도 상위 15 %, 빨간 반투명 라인)"),
                 ("dash", RED, "해상 체류 밀도 상위 5 % (수렴역)"), ("src", "#ffd54f", "쓰레기 발생원")]
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
        # 유속 컬러바
        self.ax_cb = fig.add_axes([x0 + 0.005, 0.400, 0.25, 0.018])
        grad = np.linspace(0, 1, 256)[None, :]
        self.ax_cb.imshow(grad, aspect="auto", cmap=SPEED_CMAP, extent=[0, 2, 0, 1])
        self.ax_cb.set_yticks([]); self.ax_cb.tick_params(colors="#b0bec5", labelsize=9)
        self.ax_cb.set_xticks([0, 0.5, 1, 1.5, 2])
        for sp in self.ax_cb.spines.values():
            sp.set_edgecolor("#37474f")
        fig.text(x0 + 0.26, 0.409, "유속 (m/s)", color="#b0bec5", fontsize=10, va="center")
        # 통계 막대
        self.ax_bar = fig.add_axes([x0 + 0.075, 0.228, 0.33, 0.100], facecolor="none")
        self.ax_bar.set_xlim(0, 100); self.ax_bar.set_ylim(-0.6, 2.6); self.ax_bar.axis("off")
        self.bars = self.ax_bar.barh([2, 1, 0], [0, 0, 0], color=["#ffa726", "#c62828", "#78909c"], height=0.6)
        self.bar_txt = [self.ax_bar.text(1, k, "", color="white", fontsize=10.5, va="center") for k in (2, 1, 0)]
        for k, lab in zip((2, 1, 0), ("부유 중", "해안 좌초", "영역 밖 유출")):
            fig.text(x0, 0.228 + 0.100 * (k + 0.6) / 3.2, lab, color="#eceff1", fontsize=11, va="center")
        self.t_rel = fig.text(x0, 0.345, "", color="#b0bec5", fontsize=11, va="center")
        # 순위 목록
        self.t_rank_title = fig.text(x0, 0.200, "", color="white", fontsize=13, fontweight="bold", va="center")
        self.t_rank = fig.text(x0, 0.182, "", color="#ffcdd2", fontsize=11, va="top", linespacing=1.3)
        fig.text(x0, 0.042, "근거: 조류 = 연속방정식 기반 조석(M2+S2) 포텐셜 흐름 모델(GSHHG 해안선, 수심 모형, 한강·임진강 유량),\n"
                            "쓰레기 = 라그랑주 입자추적(RK4) + 풍압 1.5 % + 확산 10 m²/s + 갯벌 좌초/재부유 확률 모형.\n"
                            "교육용 모의 결과이며 실제 집적 위치는 실측 해류(국립해양조사원·CMEMS)·수심·바람 자료로 검증이 필요합니다.",
                 color="#78909c", fontsize=8.8, va="center", linespacing=1.5)

    # ------------------------------------------------------------ 프레임 갱신
    def draw(self, f):
        d = self.d
        seg, t, k = int(d["seg"][f]), float(d["t_sim"][f]), int(d["k_snap"][f])
        # 스트리크
        f0 = max(0, f - TRAIL + 1)
        P = d["tr_pos"][f0:f + 1]                     # (L, N, 2)
        age = d["tr_age"][f]
        L = P.shape[0]
        valid = np.minimum(age, L).astype(int)       # 리스폰 이후 길이
        spd = d["tr_spd"][f].astype(np.float32)
        cols = SPEED_CMAP(np.clip(spd / 2.0, 0, 1))
        segs_b, segs_d, cb, cd = [], [], [], []
        lonP = P[..., 0] / G.M_PER_DEG_LON + C.LON_MIN
        latP = P[..., 1] / G.M_PER_DEG_LAT + C.LAT_MIN
        for n in range(P.shape[1]):
            v = valid[n]
            if v < 2:
                continue
            pts = np.column_stack([lonP[L - v:, n], latP[L - v:, n]])
            segs_d.append(pts); cd.append(cols[n])
            segs_b.append(pts[-min(v, 3):]); cb.append(cols[n])
        self.lc_dim.set_segments(segs_d); self.lc_dim.set_color(cd)
        self.lc_bright.set_segments(segs_b); self.lc_bright.set_color(cb)
        # 쓰레기
        show_debris = seg >= 2
        st = d["snap_state"][k]
        if show_debris:
            xy = d["disp_xy"][k]
            fl = st == 1; be = st == 2
            self.sc_float.set_offsets(np.column_stack(G.xy_to_lonlat(xy[fl, 0], xy[fl, 1])) if fl.any() else np.empty((0, 2)))
            bxy = d["snap_xy"][k]
            self.sc_beach.set_offsets(np.column_stack(G.xy_to_lonlat(bxy[be, 0], bxy[be, 1])) if be.any() else np.empty((0, 2)))
        else:
            self.sc_float.set_offsets(np.empty((0, 2))); self.sc_beach.set_offsets(np.empty((0, 2)))
        for a in self.src_art:
            a.set_visible(show_debris)
        # 집적 라인 (진행도에 따라 서서히 나타남)
        if show_debris:
            pr = d["prog"][k]
            fade = np.clip((k - 36) / 72.0, 0, 1)   # 1일 이후부터 서서히
            a_main = np.clip(0.25 + 0.6 * self.level, 0.3, 0.85) * pr * fade
            self.lc_red.set_color([(1.0, 0.13, 0.13, a) for a in a_main])
            self.lc_glow.set_color([(1.0, 0.2, 0.2, 0.3 * a) for a in a_main])
            self.lc_red.set_visible(True); self.lc_glow.set_visible(True)
        else:
            self.lc_red.set_visible(False); self.lc_glow.set_visible(False)
        # 해상 수렴역 점선 (최종 구간)
        if seg == 3 and self.offshore_cs is None:
            self.offshore_cs = self.ax.contour(self.LON, self.LAT, d["offshore"], levels=[float(d["offshore_thr"])], colors=[RED],
                                               linestyles="--", linewidths=1.6, alpha=0.65, zorder=6)
            for tx in self.rank_texts:
                tx.set_visible(True)
        # 타이틀
        self.title_rect.set_visible(seg == 0); self.title_txt.set_visible(seg == 0); self.title_sub.set_visible(seg == 0)
        # 패널
        names = {0: "", 1: "1부 · 조류(밀물·썰물) 흐름 — 한 조석주기", 2: "2부 · 쓰레기 이동과 해안 좌초 — 30일 타임랩스",
                 3: "3부 · 집적 예상 해안 (빨간 반투명 라인)"}
        self.t_seg.set_text(names[seg])
        day = int(t // 86400); hh = int((t % 86400) // 3600); mm = int((t % 3600) // 60)
        speed_note = "(실시간의 2,500배)" if seg == 1 else "(1초 = 20시간)" if seg == 2 else ""
        self.t_time.set_text(f"모의 시간  D+{day:02d}  {hh:02d}:{mm:02d}  {speed_note}")
        stg, sn = self.model_stage.tide_stage(t)
        self.t_tide.set_text(f"조석 상태: {stg} · {sn}     한강 유량 {self.model_stage.han_discharge(t):,.0f} m³/s")
        # 조위
        if seg == 1:
            t0, t1 = d["t_sim"][N_TITLE], d["t_sim"][N_TITLE] + C.M2_PERIOD
        else:
            t0, t1 = t - 1.5 * 86400, t + 1.5 * 86400
        m = (d["eta_t"] >= t0) & (d["eta_t"] <= t1)
        self.eta_line.set_data(d["eta_t"][m] / 3600, d["eta"][m])
        self.eta_dot.set_data([t / 3600], [float(np.interp(t, d["eta_t"], d["eta"]))])
        self.ax_eta.set_xlim(t0 / 3600, t1 / 3600); self.ax_eta.set_ylim(-4.2, 4.2)
        self.ax_eta.set_xlabel("경과 시간 (h)", color="#90a4ae", fontsize=9)
        # 바람
        wx, wy = d["wind"][int(t // 3600) % len(d["wind"])]
        ws = float(np.hypot(wx, wy)); ang = np.arctan2(wy, wx)
        r = 0.75 * min(ws / 6.0, 1.0) + 0.1
        self.wind_arrow.xy = (r * np.cos(ang), r * np.sin(ang)); self.wind_arrow.set_position((-r * np.cos(ang), -r * np.sin(ang)))
        self.t_wind.set_text(f"바람 {ws:.1f} m/s\n(풍향 {self._wind_name(wx, wy)})")
        # 통계
        if show_debris:
            cnt = np.bincount(st, minlength=4); released = max(int(cnt[1:].sum()), 1)
            vals = [cnt[1], cnt[2], cnt[3]]
            for b, v, tx in zip(self.bars, vals, self.bar_txt):
                b.set_width(100 * v / released); tx.set_text(f"{100 * v / released:4.1f} %  ({v:,})")
            self.t_rel.set_text(f"방출 입자 {released:,} / {len(st):,}")
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
        buf = np.frombuffer(self.fig.canvas.buffer_rgba(), np.uint8).reshape(H, W, 4)[..., :3]
        return np.ascontiguousarray(buf)

    @staticmethod
    def _wind_name(wx, wy):
        # 바람이 불어오는 방향 (기상 관례)
        ang = (np.degrees(np.arctan2(-wx, -wy)) + 360) % 360   # 0=북에서, 90=동에서
        names = ["북", "북동", "동", "남동", "남", "남서", "서", "북서"]
        return names[int((ang + 22.5) // 45) % 8] + "풍"


# ---------------------------------------------------------------- 병렬 인코딩
def _render_chunk(args):
    cid, f0, f1 = args
    dom = G.build_domain(verbose=False)
    data = dict(np.load(RENDER_DATA, allow_pickle=True))
    r = FrameRenderer(dom, data)
    os.makedirs(CHUNK_DIR, exist_ok=True)
    out = os.path.join(CHUNK_DIR, f"chunk_{cid:02d}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(r.draw(f).tobytes())
        if (f - f0) % 100 == 0:
            print(f"  [chunk {cid}] frame {f}/{f1}", flush=True)
    p.stdin.close(); p.wait()
    return out


def render_video(nframes, workers=4, out_path=None):
    out_path = out_path or os.path.join(C.OUT_DIR, "incheon_debris_simulation.mp4")
    edges = np.linspace(0, nframes, workers + 1).astype(int)
    jobs = [(i, int(edges[i]), int(edges[i + 1])) for i in range(workers)]
    with mp.get_context("spawn").Pool(workers) as pool:
        chunks = pool.map(_render_chunk, jobs)
    lst = os.path.join(CHUNK_DIR, "list.txt")
    with open(lst, "w") as f:
        for c in chunks:
            f.write(f"file '{c}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", out_path], check=True)
    print(f"[render] 영상 저장: {out_path}")
    return out_path


def render_stills(frames, prefix="still"):
    dom = G.build_domain(verbose=False)
    data = dict(np.load(RENDER_DATA, allow_pickle=True))
    r = FrameRenderer(dom, data)
    from PIL import Image
    paths = []
    for f in frames:
        p = os.path.join(C.OUT_DIR, f"{prefix}_{f:05d}.png")
        Image.fromarray(r.draw(f)).save(p); paths.append(p)
    return paths


def hotspot_figure(dom, an, path=None):
    """최종 집적 예상 지도 (정지 이미지, 잔차류 수렴역 포함)."""
    path = path or os.path.join(C.OUT_DIR, "hotspot_map.png")
    img, _, credit = B.get_basemap(dom)
    fig, ax = plt.subplots(figsize=(13, 13.3), dpi=150)
    ax.imshow(img, extent=[C.LON_MIN, C.LON_MAX, C.LAT_MIN, C.LAT_MAX], aspect=G.M_PER_DEG_LAT / G.M_PER_DEG_LON, interpolation="bilinear")
    outline = [pe.withStroke(linewidth=3, foreground="black")]
    g = dom["grid"]
    if "div" in an:
        conv = -an["div"] * 86400   # 1/day
        ax.contourf(g.LON, g.LAT, np.where(conv > 0, conv, np.nan), levels=[0.05, 0.1, 0.2, 0.5, 5], colors=["#ff80ab", "#ff4081", "#f50057", "#c51162"], alpha=0.25)
        s = 10
        ax.quiver(g.LON[::s, ::s], g.LAT[::s, ::s], an["ures"][::s, ::s], an["vres"][::s, ::s], color="white", scale=1.5, width=0.0015, alpha=0.75)
    ax.contour(g.LON, g.LAT, an["offshore"], levels=[an["offshore_thr"]], colors=[RED], linestyles="--", linewidths=1.6, alpha=0.7)
    for s in an["segs"]:
        a = np.clip(0.25 + 0.6 * s["level"], 0.3, 0.85)
        ax.plot(s["lon"], s["lat"], color=RED, lw=11, alpha=0.3 * a, solid_capstyle="round")
        ax.plot(s["lon"], s["lat"], color=RED, lw=4.5, alpha=a, solid_capstyle="round")
    for name, lon, lat, fs in C.PLACE_LABELS:
        ax.text(lon, lat, name, color="white", fontsize=fs * 0.85, ha="center", va="center", path_effects=outline)
    for n, e in enumerate(an["rank"][:8]):
        ax.text(e["lon"], e["lat"] + 0.012, f"{n + 1}", color="white", fontsize=12, fontweight="bold", ha="center", va="bottom",
                bbox=dict(boxstyle="circle,pad=0.25", fc=RED, ec="white", lw=1.2, alpha=0.9))
    ax.set_xlim(C.LON_MIN, C.LON_MAX); ax.set_ylim(C.LAT_MIN, C.LAT_MAX)
    ax.set_xlabel("경도"); ax.set_ylabel("위도")
    ax.set_title("해양쓰레기 집적 예상 해안 (빨간 반투명 라인 = 좌초 밀도 상위 15 %)\n"
                 "점선 = 해상 체류 밀도 상위 5 %, 분홍 음영 = 조석 잔차류 수렴역(∇·u < 0), 흰 화살표 = 잔차류", fontsize=12)
    txt = "\n".join(f"{n + 1}. {e['name']}  ({e['length_km']:.1f} km)" for n, e in enumerate(an["rank"][:8]))
    ax.text(0.015, 0.015, "집적 예상 상위 해안 (좌초 밀도 순)\n" + txt, transform=ax.transAxes, va="bottom", fontsize=10.5, color="white",
            bbox=dict(fc="black", alpha=0.6, ec="none"))
    ax.text(0.99, 0.01, "배경: " + credit, transform=ax.transAxes, ha="right", fontsize=8, color="white", path_effects=outline)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[render] 집적 지도 저장: {path}")
    return path


if __name__ == "__main__":
    dom = G.build_domain(verbose=False)
    model = CU.TidalFlowModel(dom, verbose=False)
    res = dict(np.load(os.path.join(C.OUT_DIR, "sim_results.npz")))
    an = A.analyze(dom, res, model=model)
    hotspot_figure(dom, an)
    n = prepare(dom, model, res, an)
    if "--stills" in sys.argv:
        print(render_stills([30, N_TITLE + 200, N_TITLE + N_TIDE + 400, n - 10]))
    else:
        render_video(n, workers=int(os.environ.get("WORKERS", "4")))
