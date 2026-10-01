"""라그랑주 입자추적 (해양쓰레기 이동·좌초 모의).

dx/dt = u_current(x,t) + windage · W(t) + 확산(random walk)
- 시간적분: 4차 Runge-Kutta
- 좌초(beaching): 육지 셀 진입 시 확률 P_BEACH 로 좌초, 좌초 입자는 하루 P_REFLOAT 확률로 재부유
- 유출(exit): 계산영역 밖으로 나가면 추적 종료
"""
import numpy as np

from . import config as C
from . import geodata as G


from .currents import make_wind_series  # noqa: F401  (호환용)


class DebrisSimulation:
    def __init__(self, dom, model, n=C.N_PARTICLES, days=C.SIM_DAYS, dt=C.DT, seed=0, verbose=True):
        self.dom, self.model, self.grid = dom, model, dom["grid"]
        self.n, self.days, self.dt = n, days, dt
        self.rng = np.random.default_rng(seed)
        self.wind = getattr(model, "wind", None)
        if self.wind is None:
            self.wind = make_wind_series(days, seed + 1)
        self.verbose = verbose
        self._init_particles()
        self.river_grid = G.river_regions(self.grid)
        coast = dom["coast"]
        self.coast_flat = np.flatnonzero(coast.ravel())          # 해안 셀 1차원 인덱스
        self.coast_lookup = -np.ones(coast.size, int)
        self.coast_lookup[self.coast_flat] = np.arange(len(self.coast_flat))

    # ------------------------------------------------------------ 발생원
    def _init_particles(self):
        g, w = self.grid, self.dom["water"]
        n = self.n
        T = self.days * 86400.0
        fr = np.array([s["frac"] for s in C.SOURCES]); fr /= fr.sum()
        counts = np.round(fr * n).astype(int); counts[-1] = n - counts[:-1].sum()
        x = np.zeros(n); y = np.zeros(n); t_rel = np.zeros(n); src = np.zeros(n, np.int16)
        han, imjin = self.model.river_inlets() if hasattr(self.model, "river_inlets") else (np.zeros(g.shape, bool),) * 2
        k = 0
        for sid, (s, cnt) in enumerate(zip(C.SOURCES, counts)):
            sl = slice(k, k + cnt); k += cnt
            src[sl] = sid
            if s["kind"] in ("han_inlet", "imjin_inlet"):
                cells = han if s["kind"] == "han_inlet" else imjin
                if not cells.any():
                    cells = han
                ii, jj = np.nonzero(cells)
                pick = self.rng.integers(0, len(ii), cnt)
                x[sl] = (jj[pick] + self.rng.random(cnt)) * g.dx
                y[sl] = (ii[pick] + self.rng.random(cnt)) * g.dx
                if s["kind"] == "han_inlet":
                    # 장마 홍수 펄스: 기본 유입 + HAN_FLOOD_DAYS 구간 4배 집중
                    base = self.rng.random(cnt) * T
                    d0, d1 = C.HAN_FLOOD_DAYS
                    pulse = (d0 + (d1 - d0) * self.rng.random(cnt)) * 86400
                    t_rel[sl] = np.where(self.rng.random(cnt) < 0.6, pulse, base)
                else:
                    t_rel[sl] = self.rng.random(cnt) * T
            elif s["kind"] == "point":
                px, py = G.lonlat_to_xy(*s["lonlat"])
                # 지정 지점 주변 1.5 km 안의 물 셀에서 방출
                d = np.hypot(g.X - px, g.Y - py)
                cand = np.flatnonzero((w & (d < 1500)).ravel())
                if len(cand) == 0:
                    cand = np.array([np.argmin(np.where(w, d, np.inf).ravel())])
                pick = self.rng.choice(cand, cnt)
                ii, jj = np.unravel_index(pick, g.shape)
                x[sl] = (jj + self.rng.random(cnt)) * g.dx
                y[sl] = (ii + self.rng.random(cnt)) * g.dx
                t_rel[sl] = self.rng.random(cnt) * T
            elif s["kind"] == "inflow":   # 개방경계 띠에서 계속 유입 (외양 쓰레기)
                m = np.zeros(g.shape, bool)
                for lon0, lon1, lat0, lat1 in s["bands"]:
                    m |= (g.LON >= lon0) & (g.LON <= lon1) & (g.LAT >= lat0) & (g.LAT <= lat1)
                cand = np.flatnonzero((w & m).ravel())
                pick = self.rng.choice(cand, cnt)
                ii, jj = np.unravel_index(pick, g.shape)
                x[sl] = (jj + self.rng.random(cnt)) * g.dx
                y[sl] = (ii + self.rng.random(cnt)) * g.dx
                t_rel[sl] = self.rng.random(cnt) * T * 0.7
            elif s["kind"] == "ambient":  # 모의 시작 시 해역 전체에 떠 있는 쓰레기
                cand = np.flatnonzero(w.ravel())
                pick = self.rng.choice(cand, cnt)
                ii, jj = np.unravel_index(pick, g.shape)
                x[sl] = (jj + self.rng.random(cnt)) * g.dx
                y[sl] = (ii + self.rng.random(cnt)) * g.dx
                t_rel[sl] = self.rng.random(cnt) * 86400.0
            else:  # offshore: 서쪽 외해에 떠 있는 황해 유래 쓰레기 (인천)
                cand = np.flatnonzero((w & (g.LON < 126.25) & (g.LON > 125.90) & (g.LAT > 37.10)).ravel())
                pick = self.rng.choice(cand, cnt)
                ii, jj = np.unravel_index(pick, g.shape)
                x[sl] = (jj + self.rng.random(cnt)) * g.dx
                y[sl] = (ii + self.rng.random(cnt)) * g.dx
                t_rel[sl] = self.rng.random(cnt) * T * 0.8
        self.x, self.y, self.t_rel, self.src = x, y, t_rel, src
        self.state = np.zeros(n, np.int8)   # 0 미방출, 1 부유, 2 좌초, 3 유출
        self.beach_events = np.zeros(self.grid.shape, np.float32)

    # ------------------------------------------------------------ 물리
    def wind_at(self, t):
        h = int(t // 3600) % len(self.wind)
        return self.wind[h]

    def _cell_is_land(self, x, y):
        i, j = self.grid.cell_index(x, y)
        inside = i >= 0
        land = np.ones_like(inside)
        land[inside] = self.dom["land"][i[inside], j[inside]]
        return land, inside

    def step(self, t, uv0, uv1, uv2):
        """t → t+dt. uv0/1/2 = 유속장 at t, t+dt/2, t+dt."""
        dt = self.dt
        # 방출
        self.state[(self.state == 0) & (self.t_rel <= t)] = 1
        act = np.flatnonzero(self.state == 1)
        if len(act) == 0:
            self._refloat(t)
            return
        x, y = self.x[act], self.y[act]
        m = self.model
        k1 = m.velocity_at(t, x, y, uv0)
        k2 = m.velocity_at(t, x + 0.5 * dt * k1[0], y + 0.5 * dt * k1[1], uv1)
        k3 = m.velocity_at(t, x + 0.5 * dt * k2[0], y + 0.5 * dt * k2[1], uv1)
        k4 = m.velocity_at(t, x + dt * k3[0], y + dt * k3[1], uv2)
        ux = (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]) / 6
        uy = (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]) / 6
        wx, wy = self.wind_at(t) * C.WINDAGE
        sig = np.sqrt(2 * C.K_DIFF * dt)
        xn = x + dt * (ux + wx) + sig * self.rng.standard_normal(len(act))
        yn = y + dt * (uy + wy) + sig * self.rng.standard_normal(len(act))
        land, inside = self._cell_is_land(xn, yn)
        exited = ~inside
        hit = land & inside
        i0, j0 = self.grid.cell_index(x, y)
        in_river = self.river_grid[np.clip(i0, 0, None), np.clip(j0, 0, None)] & (i0 >= 0)
        p_beach = np.where(in_river, C.P_BEACH_RIVER, C.P_BEACH)
        beach = hit & (self.rng.random(len(act)) < p_beach)
        stay = hit & ~beach
        ok = ~hit & ~exited
        self.x[act[ok]] = xn[ok]; self.y[act[ok]] = yn[ok]
        self.state[act[exited]] = 3
        # 좌초: 직전 물 위치에 고정, 해당 해안 셀에 기록
        if beach.any():
            self.state[act[beach]] = 2
            i, j = self.grid.cell_index(x[beach], y[beach])
            np.add.at(self.beach_events, (i, j), 1.0)
        # 육지에 닿았지만 좌초하지 않은 입자: 제자리 (다음 스텝에 확산으로 이탈)
        self._refloat(t)

    def _refloat(self, t):
        b = np.flatnonzero(self.state == 2)
        if len(b):
            i, j = self.grid.cell_index(self.x[b], self.y[b])
            in_river = self.river_grid[np.clip(i, 0, None), np.clip(j, 0, None)]
            p = np.where(in_river, C.P_REFLOAT_RIVER, C.P_REFLOAT_PER_DAY) * self.dt / 86400.0
            r = b[self.rng.random(len(b)) < p]
            self.state[r] = 1

    # ------------------------------------------------------------ 실행
    def run(self, snap_dt=C.SNAP_DT, density_days=15):
        nsteps = int(round(self.days * 86400 / self.dt))
        snap_every = int(round(snap_dt / self.dt))
        nsnap = nsteps // snap_every + 1
        n = self.n
        snap_t = np.zeros(nsnap, np.float64)
        snap_xy = np.zeros((nsnap, n, 2), np.float32)
        snap_state = np.zeros((nsnap, n), np.int8)
        beach_hist = np.zeros((nsnap, len(self.coast_flat)), np.float32)
        float_density = np.zeros(self.grid.shape, np.float32)
        dens_start = (self.days - density_days) * 86400
        m = self.model
        uv0 = m.velocity(0.0)
        ks = 0
        for k in range(nsteps + 1):
            t = k * self.dt
            if k % snap_every == 0:
                snap_t[ks] = t
                snap_xy[ks, :, 0] = self.x; snap_xy[ks, :, 1] = self.y
                snap_state[ks] = self.state
                beach_hist[ks] = self._beached_hist()
                if t >= dens_start:
                    fl = self.state == 1
                    i, j = self.grid.cell_index(self.x[fl], self.y[fl])
                    np.add.at(float_density, (i[i >= 0], j[i >= 0]), 1.0)
                ks += 1
                if self.verbose and ks % 72 == 1:
                    st = np.bincount(self.state, minlength=4)
                    print(f"  day {t / 86400:5.1f}: floating {st[1]:5d} beached {st[2]:5d} exited {st[3]:5d} unreleased {st[0]:5d}")
            if k == nsteps:
                break
            uv1 = m.velocity(t + 0.5 * self.dt)
            uv2 = m.velocity(t + self.dt)
            self.step(t, uv0, uv1, uv2)
            uv0 = uv2
        return dict(snap_t=snap_t[:ks], snap_xy=snap_xy[:ks], snap_state=snap_state[:ks], beach_hist=beach_hist[:ks],
                    coast_flat=self.coast_flat, float_density=float_density, beach_events=self.beach_events,
                    src=self.src, t_rel=self.t_rel, wind=self.wind, final_state=self.state.copy(),
                    final_x=self.x.copy(), final_y=self.y.copy())

    def _beached_hist(self):
        b = self.state == 2
        i, j = self.grid.cell_index(self.x[b], self.y[b])
        flat = i * self.grid.nx + j
        ci = self.coast_lookup[flat]
        # 해안 셀이 아닌 곳에 좌초 기록된 경우(드묾) 가장 가까운 해안 셀 대신 무시
        return np.bincount(ci[ci >= 0], minlength=len(self.coast_flat)).astype(np.float32)
