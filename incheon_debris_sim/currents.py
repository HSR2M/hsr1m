"""해류(조류) 모델.

(1) TidalFlowModel : 실측 해류 자료가 없을 때 쓰는 '연속방정식 기반 조석 포텐셜 흐름' 모델
    ∂η/∂t + ∇·(h u) = R ,  u = -∇Φ  →  ∇·(h∇Φ) = ∂η/∂t - R
    - η(x,y,t): 조위 (M2 + S2 조화상수, 외해에서 내만으로 전파되며 진폭 증가·위상 지연)
    - h: 수심, R: 하천 유입(한강·임진강)
    - 개방경계(서·남) Φ = 0, 해안에서는 법선 유속 0
    선형 문제이므로 (M2 cos, M2 sin, S2 cos, S2 sin, 하천) 5개의 정상 해를 한 번만 구한 뒤
    임의 시각의 유속장을 즉시 합성한다.

(2) ExternalCurrents : Copernicus Marine / HYCOM / 국립해양조사원 등 NetCDF (u, v, time, lat, lon)
    자료를 격자에 보간해 같은 인터페이스(velocity(t), sea_level(t))로 제공.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu

from . import config as C
from . import geodata as G


def make_wind_series(days, seed=1):
    """시간별 바람(동향, 북향 m/s): 평균 + AR(1) 일변동 (상관시간 2일)."""
    rng = np.random.default_rng(seed)
    n = int(days * 24) + 48
    a = np.exp(-1.0 / 48.0)
    s = C.WIND_SIGMA * np.sqrt(1 - a * a)
    w = np.zeros((n, 2))
    for k in range(1, n):
        w[k] = a * w[k - 1] + s * rng.standard_normal(2)
    w[:, 0] += C.WIND_MEAN[0]; w[:, 1] += C.WIND_MEAN[1]
    return w  # index = hour


def bilinear(field, x, y, dx):
    """셀 중심 격자 field(ny,nx) 를 점 (x,y)[m] 에서 이중선형 보간. 영역 밖은 0."""
    ny, nx = field.shape
    fx = x / dx - 0.5
    fy = y / dx - 0.5
    j0 = np.floor(fx).astype(int)
    i0 = np.floor(fy).astype(int)
    tx = fx - j0
    ty = fy - i0
    j0c = np.clip(j0, 0, nx - 1); j1c = np.clip(j0 + 1, 0, nx - 1)
    i0c = np.clip(i0, 0, ny - 1); i1c = np.clip(i0 + 1, 0, ny - 1)
    v = ((1 - tx) * (1 - ty) * field[i0c, j0c] + tx * (1 - ty) * field[i0c, j1c]
         + (1 - tx) * ty * field[i1c, j0c] + tx * ty * field[i1c, j1c])
    inside = (x >= 0) & (x <= nx * dx) & (y >= 0) & (y <= ny * dx)
    return np.where(inside, v, 0.0)


class TidalFlowModel:
    CONSTITUENTS = tuple(C.CONSTITUENTS)

    def __init__(self, dom, river=True, verbose=True, wind=None):
        self.dom = dom
        self.grid = dom["grid"]
        self.water = dom["water"]
        self.depth = dom["depth"]
        self.dx = self.grid.dx
        self.wind = wind if wind is not None else make_wind_series(C.SIM_DAYS, 1)
        tau = C.PHASE_SCALE * np.nan_to_num(dom["travel"], nan=0.0)   # 조석 위상 지연 시간(s)
        self.tau = tau
        self.amp_m2 = C.A_M2_OFFSHORE * (1.0 + C.A_M2_INNER_GAIN * (1.0 - np.exp(-tau / 3600.0)))
        self._build_operator()
        rhs = []
        self.comp = []   # (omega, phase-type) 순서 기록
        for name, T, ratio in self.CONSTITUENTS:
            w = 2 * np.pi / T
            A = ratio * self.amp_m2
            phi = w * tau
            rhs.append(A * w * np.sin(phi))      # cos(wt) 계수
            rhs.append(-A * w * np.cos(phi))     # sin(wt) 계수
            self.comp += [(name, w, "cos"), (name, w, "sin")]
        if river and (C.HAN_RIVER_Q > 0 or C.IMJIN_RIVER_Q > 0):
            rhs.append(-self.river_source())
            self.comp.append(("river", 0.0, "const"))
        self.U, self.V = [], []
        for s in rhs:
            u, v = self._solve_velocity(s)
            self.U.append(u.astype(np.float32)); self.V.append(v.astype(np.float32))
        if C.BACKGROUND_FLOW:
            for name, u, v in self._background_components():
                self.U.append(u.astype(np.float32)); self.V.append(v.astype(np.float32))
                self.comp.append((name, 0.0, "bg"))
        self.U = np.array(self.U); self.V = np.array(self.V)
        self._regularize()
        if verbose:
            sp = np.hypot(self.U[0], self.V[0]) + np.hypot(self.U[1], self.V[1])
            print(f"[currents] M2 current amplitude (approx) p50/p90/max = "
                  f"{np.percentile(sp[self.water], 50):.2f}/{np.percentile(sp[self.water], 90):.2f}/{sp.max():.2f} m/s")

    def _regularize(self):
        """1셀 폭 틈새의 비현실적 스파이크 억제: 성분별 가벼운 평활화 + 조류 진폭 상한."""
        from scipy import ndimage
        w = self.water.astype(np.float32)
        for k in range(len(self.U)):
            for F in (self.U, self.V):
                sm = ndimage.gaussian_filter(F[k] * w, 1.0) / np.maximum(ndimage.gaussian_filter(w, 1.0), 1e-3)
                F[k] = np.where(self.water, sm, 0.0).astype(np.float32)
        amp = np.zeros(self.grid.shape, np.float32)
        for k, (name, wv, kind) in enumerate(self.comp):
            if kind in ("cos", "sin"):
                amp += np.hypot(self.U[k], self.V[k])
        scale = np.where(amp > C.MAX_SPEED, C.MAX_SPEED / np.maximum(amp, 1e-6), 1.0).astype(np.float32)
        self.U *= scale; self.V *= scale

    # ---------------------------------------------------------------- 하천
    def river_inlets(self):
        """한강(동쪽 끝)·임진강(북쪽 끝) 유입 셀 인덱스."""
        g = self.grid; w = self.water
        han = w & (g.LON > 126.80) & (g.LAT > 37.45) & (g.LAT < 37.65)
        if han.any():
            jmax = np.max(np.flatnonzero(han.any(axis=0)))
            han &= np.arange(g.nx)[None, :] >= jmax - 3
        imjin = w & (g.LAT > 37.80) & (g.LON > 126.60) & (g.LON < 126.82)
        if imjin.any():
            imax = np.max(np.flatnonzero(imjin.any(axis=1)))
            imjin &= np.arange(g.ny)[:, None] >= imax - 3
        return han, imjin

    def river_source(self):
        R = np.zeros(self.grid.shape)
        han, imjin = self.river_inlets()
        A = self.dx ** 2
        if han.any():
            R[han] += C.HAN_RIVER_Q / (han.sum() * A)
        if imjin.any():
            R[imjin] += C.IMJIN_RIVER_Q / (imjin.sum() * A)
        return R

    # ---------------------------------------------------------------- 선형계
    def _build_operator(self):
        ny, nx = self.grid.shape
        water, h, dx = self.water, self.depth, self.dx
        dirichlet = self.dom["open_bnd"]
        unknown = water & ~dirichlet
        idx = -np.ones((ny, nx), int)
        self.unk = np.flatnonzero(unknown.ravel())
        idx.ravel()[self.unk] = np.arange(len(self.unk))
        n = len(self.unk)
        rows, cols, vals = [], [], []
        diag = np.zeros(n)
        hw = np.where(water, h, 0.0)
        # 면 전도도 (조화평균) 저장: x-면 (i, j+1/2), y-면 (i+1/2, j)
        self.Cx = np.zeros((ny, nx - 1)); self.Cy = np.zeros((ny - 1, nx))
        for axis in (0, 1):
            if axis == 1:
                a_idx, b_idx = idx[:, :-1], idx[:, 1:]
                ha, hb = hw[:, :-1], hw[:, 1:]
                wa, wb = water[:, :-1], water[:, 1:]
            else:
                a_idx, b_idx = idx[:-1, :], idx[1:, :]
                ha, hb = hw[:-1, :], hw[1:, :]
                wa, wb = water[:-1, :], water[1:, :]
            both = wa & wb
            cond = np.where(both, 2 * ha * hb / np.maximum(ha + hb, 1e-9), 0.0) / dx ** 2
            if axis == 1:
                self.Cx = cond * dx ** 2
            else:
                self.Cy = cond * dx ** 2
            # a 가 미지수인 경우
            m = both & (a_idx >= 0)
            np.add.at(diag, a_idx[m], -cond[m])
            mb = m & (b_idx >= 0)
            rows.append(a_idx[mb]); cols.append(b_idx[mb]); vals.append(cond[mb])
            # b 가 미지수인 경우
            m = both & (b_idx >= 0)
            np.add.at(diag, b_idx[m], -cond[m])
            ma = m & (a_idx >= 0)
            rows.append(b_idx[ma]); cols.append(a_idx[ma]); vals.append(cond[ma])
        rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(diag)
        A = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()
        self.lu = splu(A)

    def _solve_velocity(self, source):
        """∇·(h∇Φ) = source 를 풀고 u=-∇Φ 를 셀 중심에서 반환 (해안 면 유속 0)."""
        phi = np.zeros(self.grid.shape)
        phi.ravel()[self.unk] = self.lu.solve(source.ravel()[self.unk])
        dx = self.dx
        water = self.water
        # 면 유속 (물-물 면에서만)
        ux = -(phi[:, 1:] - phi[:, :-1]) / dx * (water[:, 1:] & water[:, :-1])
        vy = -(phi[1:, :] - phi[:-1, :]) / dx * (water[1:, :] & water[:-1, :])
        u = np.zeros_like(phi); v = np.zeros_like(phi)
        u[:, 1:-1] = 0.5 * (ux[:, 1:] + ux[:, :-1]); u[:, 0] = ux[:, 0]; u[:, -1] = ux[:, -1]
        v[1:-1, :] = 0.5 * (vy[1:, :] + vy[:-1, :]); v[0, :] = vy[0, :]; v[-1, :] = vy[-1, :]
        u[~water] = 0; v[~water] = 0
        return u, v

    # ---------------------------------------------------------------- 시각별 합성
    @staticmethod
    def river_factor(t):
        """한강 홍수 펄스: HAN_FLOOD_DAYS 구간에서 유량이 HAN_FLOOD_Q 까지 sin 모양으로 증가."""
        t0, t1 = C.HAN_FLOOD_DAYS[0] * 86400.0, C.HAN_FLOOD_DAYS[1] * 86400.0
        if C.HAN_RIVER_Q > 0 and t0 <= t <= t1:
            return 1.0 + (C.HAN_FLOOD_Q / C.HAN_RIVER_Q - 1.0) * np.sin(np.pi * (t - t0) / (t1 - t0))
        return 1.0

    def han_discharge(self, t):
        return C.HAN_RIVER_Q * self.river_factor(t)

    def background_uv(self, t):
        """시각 t 의 균일 배경 유속 (북적도해류 + 바람 표류, m/s)."""
        bf = C.BACKGROUND_FLOW
        wx, wy = self.wind[int(t // 3600) % len(self.wind)]
        th = np.radians(bf["wind_drift_rot"])
        dx_, dy_ = bf["wind_drift"] * (wx * np.cos(th) - wy * np.sin(th)), bf["wind_drift"] * (wx * np.sin(th) + wy * np.cos(th))
        return bf["nec"][0] + dx_, bf["nec"][1] + dy_

    def coeffs(self, t):
        c = []
        bg = self.background_uv(t) if C.BACKGROUND_FLOW else (0.0, 0.0)
        for name, w, kind in self.comp:
            if kind == "cos":
                c.append(np.cos(w * t))
            elif kind == "sin":
                c.append(np.sin(w * t))
            elif kind == "bg":
                c.append({"bgx": bg[0], "bgy": bg[1], "bgfixed": 1.0}[name])
            else:
                c.append(self.river_factor(t))
        return np.array(c, dtype=np.float32)

    # ---------------------------------------------------------------- 배경 해류 (유선함수)
    def _analytic_psi(self, X, Y, U=0.0, V=0.0, fixed=False):
        """자유 공간 유선함수 ψ (u=∂ψ/∂y, v=-∂ψ/∂x): 균일류 + 반류 + 소용돌이."""
        psi = U * Y - V * X
        if fixed:
            bf = C.BACKGROUND_FLOW
            cc = bf.get("countercurrent")
            if cc:
                yc = (cc["lat"] - C.LAT_MIN) * G.M_PER_DEG_LAT
                wy = cc["width_deg"] * G.M_PER_DEG_LAT
                xmax = (cc["lon_max"] - C.LON_MIN) * G.M_PER_DEG_LON
                xfade = cc["lon_fade"] * G.M_PER_DEG_LON
                taper = 0.5 * (1 - np.tanh((X - xmax) / xfade))
                # ∫ s·exp(-((y-yc)/w)^2) dy = s·w·√π/2·erf((y-yc)/w)
                from scipy.special import erf
                psi = psi + cc["speed"] * wy * np.sqrt(np.pi) / 2 * erf((Y - yc) / wy) * taper
            for e in bf.get("eddies", []):
                xe = (e["lonlat"][0] - C.LON_MIN) * G.M_PER_DEG_LON; ye = (e["lonlat"][1] - C.LAT_MIN) * G.M_PER_DEG_LAT
                R = e["radius_km"] * 1000.0
                A = e["sign"] * e["vmax"] * R * np.exp(0.5)
                psi = psi + A * np.exp(-((X - xe) ** 2 + (Y - ye) ** 2) / (2 * R * R))
        return psi

    def _background_components(self):
        """∇²ψ = ∇²ψ_a 를 섬 경계(ψ=상수)·개방경계(ψ=ψ_a) 조건으로 풀어 섬을 우회하는 흐름을 만든다.
        성분: bgx(단위 동향류), bgy(단위 북향류), bgfixed(반류+소용돌이)."""
        from scipy import ndimage
        from scipy.sparse import coo_matrix
        from scipy.sparse.linalg import splu
        g, water, dx = self.grid, self.water, self.dx
        ny, nx = g.shape
        land = ~water
        lab, nlab = ndimage.label(land)
        cents = ndimage.center_of_mass(land, lab, range(1, nlab + 1))
        open_bnd = self.dom["open_bnd"]
        unknown = water & ~open_bnd
        idx = -np.ones((ny, nx), int)
        unk = np.flatnonzero(unknown.ravel()); idx.ravel()[unk] = np.arange(len(unk)); n = len(unk)
        # 라플라시안 (물-물 면 + 알려진 이웃은 RHS 로)
        rows, cols, vals = [], [], []
        diag = np.zeros(n)
        known_terms = []   # (unknown index, neighbor i, neighbor j) for RHS
        for di, dj in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            a = idx; 
            I, J = np.nonzero(unknown)
            I2, J2 = I + di, J + dj
            ok = (I2 >= 0) & (I2 < ny) & (J2 >= 0) & (J2 < nx)
            I, J, I2, J2 = I[ok], J[ok], I2[ok], J2[ok]
            ai = idx[I, J]; bi = idx[I2, J2]
            np.add.at(diag, ai, -1.0)
            m = bi >= 0
            rows.append(ai[m]); cols.append(bi[m]); vals.append(np.ones(m.sum()))
            known_terms.append((ai[~m], I2[~m], J2[~m]))
        rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(diag)
        Amat = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()
        lu = splu(Amat)
        X, Y = g.X, g.Y
        out = []
        for name, U, V, fixed in (("bgx", 1.0, 0.0, False), ("bgy", 0.0, 1.0, False), ("bgfixed", 0.0, 0.0, True)):
            psi_a = self._analytic_psi(X, Y, U, V, fixed)
            # 섬별 상수 = 섬 중심의 자유공간 ψ
            psi_known = psi_a.copy()
            for k, (ci, cj) in enumerate(cents, start=1):
                xc, yc = (cj + 0.5) * dx, (ci + 0.5) * dx
                psi_known[lab == k] = self._analytic_psi(np.array(xc), np.array(yc), U, V, fixed)
            lap = np.zeros(g.shape)
            lap[1:-1, 1:-1] = (psi_a[1:-1, 2:] + psi_a[1:-1, :-2] + psi_a[2:, 1:-1] + psi_a[:-2, 1:-1] - 4 * psi_a[1:-1, 1:-1])
            rhs = lap.ravel()[unk].copy()
            for ai, I2, J2 in known_terms:
                np.add.at(rhs, ai, -psi_known[I2, J2])
            psi = psi_known.copy()
            psi.ravel()[unk] = lu.solve(rhs)
            # u = ∂ψ/∂y, v = -∂ψ/∂x (면 → 셀 중심), 해안 면 유속 0
            ww = water
            uy = (psi[1:, :] - psi[:-1, :]) / dx * (ww[1:, :] & ww[:-1, :])     # y-면의 u
            vx = -(psi[:, 1:] - psi[:, :-1]) / dx * (ww[:, 1:] & ww[:, :-1])    # x-면의 v
            u = np.zeros(g.shape); v = np.zeros(g.shape)
            u[1:-1, :] = 0.5 * (uy[1:, :] + uy[:-1, :]); u[0, :] = uy[0, :]; u[-1, :] = uy[-1, :]
            v[:, 1:-1] = 0.5 * (vx[:, 1:] + vx[:, :-1]); v[:, 0] = vx[:, 0]; v[:, -1] = vx[:, -1]
            u[~water] = 0; v[~water] = 0
            out.append((name, u, v))
        return out

    def velocity(self, t):
        """시각 t(s)의 (u, v) 격자장 [m/s]."""
        c = self.coeffs(t)
        return np.tensordot(c, self.U, 1), np.tensordot(c, self.V, 1)

    def velocity_at(self, t, x, y, uv=None):
        if uv is None:
            uv = self.velocity(t)
        return bilinear(uv[0], x, y, self.dx), bilinear(uv[1], x, y, self.dx)

    def sea_level(self, t, lon=None, lat=None):
        """지정 지점(기본: 설정의 TIDE_STATION)의 모델 조위(m, 평균해면 기준)."""
        if lon is None:
            lon, lat = C.TIDE_STATION[1], C.TIDE_STATION[2]
        i, j = self.grid.cell_index(*G.lonlat_to_xy(lon, lat))
        if not self.water[i, j]:
            ii, jj = np.nonzero(self.water); k = np.argmin((ii - i) ** 2 + (jj - j) ** 2); i, j = ii[k], jj[k]
        tau = self.tau[i, j]; A = self.amp_m2[i, j]
        eta = 0.0
        for name, T, ratio in self.CONSTITUENTS:
            w = 2 * np.pi / T
            eta = eta + ratio * A * np.cos(w * (np.asarray(t) - tau))
        return eta

    def tide_stage(self, t):
        """창조(밀물)/낙조(썰물), 대조/소조 판정용 문자열."""
        e0, e1 = self.sea_level(t), self.sea_level(t + 600)
        rising = e1 > e0
        has_s2 = any(nm == "S2" for nm, _, _ in self.CONSTITUENTS)
        beat = np.cos(2 * np.pi * (1 / C.S2_PERIOD - 1 / C.M2_PERIOD) * t) if has_s2 else 0.0   # +1 대조, -1 소조
        return ("창조(밀물)" if rising else "낙조(썰물)"), ("대조기" if beat > 0.33 else "소조기" if beat < -0.33 else "중간")


class ExternalCurrents:
    """NetCDF 표층 해류 자료(u,v)를 격자에 보간. 변수명은 var_map 으로 지정.
    예) Copernicus: {"u":"uo","v":"vo","lat":"latitude","lon":"longitude","time":"time"}
        HYCOM    : {"u":"water_u","v":"water_v","lat":"lat","lon":"lon","time":"time"}
    """

    def __init__(self, path, dom, var_map=None, t0_index=0):
        import netCDF4
        from scipy.interpolate import RegularGridInterpolator
        vm = {"u": "uo", "v": "vo", "lat": "latitude", "lon": "longitude", "time": "time"}
        vm.update(var_map or {})
        ds = netCDF4.Dataset(path)
        lat = np.asarray(ds.variables[vm["lat"]][:]); lon = np.asarray(ds.variables[vm["lon"]][:])
        tv = ds.variables[vm["time"]]
        tsec = netCDF4.num2date(tv[:], tv.units)
        self.times = np.array([(d - tsec[t0_index]).total_seconds() for d in tsec])
        U = ds.variables[vm["u"]][:]; V = ds.variables[vm["v"]][:]
        if U.ndim == 4:   # (time, depth, lat, lon) → 표층
            U, V = U[:, 0], V[:, 0]
        U = np.ma.filled(U, 0.0); V = np.ma.filled(V, 0.0)
        self.grid = dom["grid"]; self.water = dom["water"]; self.dx = self.grid.dx; self.dom = dom
        pts = np.column_stack([self.grid.LAT.ravel(), self.grid.LON.ravel()])
        self.U = np.zeros((len(self.times),) + self.grid.shape, np.float32)
        self.V = np.zeros_like(self.U)
        for k in range(len(self.times)):
            fu = RegularGridInterpolator((lat, lon), U[k], bounds_error=False, fill_value=0.0)
            fv = RegularGridInterpolator((lat, lon), V[k], bounds_error=False, fill_value=0.0)
            self.U[k] = fu(pts).reshape(self.grid.shape) * self.water
            self.V[k] = fv(pts).reshape(self.grid.shape) * self.water

    def velocity(self, t):
        k = np.searchsorted(self.times, t) - 1
        k = int(np.clip(k, 0, len(self.times) - 2))
        f = np.clip((t - self.times[k]) / (self.times[k + 1] - self.times[k]), 0, 1)
        return (1 - f) * self.U[k] + f * self.U[k + 1], (1 - f) * self.V[k] + f * self.V[k + 1]

    def velocity_at(self, t, x, y, uv=None):
        if uv is None:
            uv = self.velocity(t)
        return bilinear(uv[0], x, y, self.dx), bilinear(uv[1], x, y, self.dx)

    def sea_level(self, t, **kw):
        return 0.0 * np.asarray(t)

    def tide_stage(self, t):
        return ("실측/모델 해류", "")
