"""
삼각측량(전방교회) — 같은 쓰레기를 본 여러 프레임의 광선을 교차시켜 위치를 구한다.

기존 방식(orbit_map / video_map)은 프레임마다 "광선 ↔ 지면 평면(z=0)" 교차점을 구해
중앙값을 냈다. 이 방식은 ① 지면이 평평하고 ② 카메라 높이(고도)를 정확히 안다는 가정이
필요하다. SRT 고도가 이륙 지점 기준이라 틀린 경우(0010: 3.7 m 기록/실제 ~2 m, 0015: 1/5로
기록) 위치가 통째로 어긋났다.

여기서는 측량의 전방교회법처럼, 서로 다른 위치에서 쏜 광선들이 가장 가깝게 모이는 점을
최소제곱으로 푼다.

    p* = argmin Σ_i w_i ‖(I − d_i d_iᵀ)(p − c_i)‖²      c_i: 카메라 위치, d_i: 단위 광선
    ⇒ (Σ_i w_i (I − d_i d_iᵀ)) p = Σ_i w_i (I − d_i d_iᵀ) c_i      (3×3 선형식 하나)

흐름 (locate)
  1. 높이 추정  — 프레임이 다른 탐지 쌍마다 "같은 물체라면 카메라 높이가 얼마여야 두 광선이
                  지면에서 만나는가"를 풀어(2D 선형식) 투표. 최빈값 = 실제 높이 (입력 높이 검증)
  2. 묶기       — 입력 높이와 투표 높이 후보로 각각 근사 지면점을 만들어 같은 물체끼리 묶고,
                  삼각측량이 가장 잘 맞는(쓰인 광선 많고 잔차 작은) 후보를 채택
  3. 삼각측량   — 물체마다 광선 교차(Huber 가중, 이상치 배제). 시차 부족·비정상이면 평면 교차로 대체
  4. 오차 반경  — (선택) 텔레메트리 오차 몬테카를로 → r95

장점
  - 고도·평지 가정이 필요 없다 (물체 높이 z도 같이 나온다)
  - 프레임별 잡음이 평균되고, 잘못 묶인 탐지(이상치)는 Huber 가중치로 배제된다
  - 입력한 "지면에서 카메라 높이"가 틀려도 결과가 거의 안 변한다 — 오히려 실제 높이를 역산해 알려준다

한계
  - 모든 광선이 공유하는 오차(드론 GPS 편향, 영상-SRT 시각 어긋남, SRT 만 쓸 때 yaw 오차)는 못 없앤다
  - 시차(광선 사이 최대 각)가 min_angle_deg 미만이면 깊이가 불안정 → 평면 교차로 되돌아간다
  - 비행 방향으로 일렬·등간격으로 놓인 물체들은 쌍별 높이 투표에 잡음 표를 더한다 (최빈값·잔차 검사로 걸러짐)

사용: orbit_map.py(3D 카메라 자세) / video_map.py(SRT + 입력 높이) 가 locate() 를 부른다.
"""
import numpy as np

# 기본값 — CLI 에서 바꿀 수 있다
MIN_ANGLE_DEG = 5.0     # 광선 사이 최대 각이 이보다 작으면 삼각측량 포기 → 평면 교차
HUBER_M = 0.5           # 광선-교차점 수직거리가 이보다 크면 가중치를 줄인다 (이상치)
MAX_DZ_M = 3.0          # 교차점 높이가 지면에서 이보다 벗어나면 비정상 → 평면 교차
MIN_RANGE_M = 1.0       # 교차점이 카메라에서 이보다 가까우면 거부 (같은 위치 광선끼리 "교차"한 것)


def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n > 0, n, 1.0)


def max_pair_angle_deg(D):
    """광선 방향들 사이 가장 큰 각(도) = 시차. 2개 미만이면 0."""
    D = _unit(np.atleast_2d(D))
    if len(D) < 2:
        return 0.0
    c = np.clip(D @ D.T, -1.0, 1.0)
    return float(np.degrees(np.arccos(c.min())))


def ray_plane(C, D, z=0.0):
    """광선 ↔ 수평면 z 교차점 (N,3). 위를 향하거나 평행이면 NaN. (기존 방식·묶기용)"""
    C = np.atleast_2d(np.asarray(C, float))
    D = _unit(np.atleast_2d(D))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (z - C[:, 2]) / D[:, 2]
    t = np.where((t > 0) & np.isfinite(t), t, np.nan)
    return C + D * t[:, None]


def intersect_rays(C, D, w=None):
    """가중 최소제곱 교차점. 반환 (p(3,), 광선별 수직거리(N,), A의 고유값(3,)).
    광선이 전부 평행하면 p 는 NaN."""
    C = np.atleast_2d(np.asarray(C, float))
    D = _unit(np.atleast_2d(D))
    n = len(C)
    w = np.ones(n) if w is None else np.asarray(w, float)
    M = np.eye(3)[None] - D[:, :, None] * D[:, None, :]          # (N,3,3) 광선에 수직인 성분 투영
    A = np.einsum("i,ijk->jk", w, M)
    b = np.einsum("i,ijk,ik->j", w, M, C)
    ev = np.linalg.eigvalsh(A)
    if not np.isfinite(ev).all() or ev[0] <= 1e-9 * max(ev[-1], 1e-12):
        return np.full(3, np.nan), np.full(n, np.nan), ev
    p = np.linalg.solve(A, b)
    dist = np.linalg.norm(np.einsum("ijk,ik->ij", M, p[None] - C), axis=1)
    return p, dist, ev


def intersect_rays_robust(C, D, huber_m=HUBER_M, w0=None, n_iter=10):
    """Huber 가중치를 반복(IRLS)해서 이상치 광선의 영향을 줄인다.
    반환 (p, 광선별 수직거리, 최종 가중치)."""
    C = np.atleast_2d(np.asarray(C, float))
    D = _unit(np.atleast_2d(D))
    w0 = np.ones(len(C)) if w0 is None else np.asarray(w0, float)
    w = w0.copy()
    p, dist = np.full(3, np.nan), np.full(len(C), np.nan)
    for _ in range(n_iter):
        p, dist, _ = intersect_rays(C, D, w)
        if not np.isfinite(p).all():
            break
        t = np.einsum("ij,ij->i", D, p[None] - C)   # 교차점이 카메라 뒤(t<=0)인 광선은 믿지 않는다
        wn = w0 * np.where(dist <= huber_m, 1.0, huber_m / np.maximum(dist, 1e-9)) * (t > 0)
        if wn.sum() <= 0 or np.allclose(wn, w):
            w = wn if wn.sum() > 0 else w
            break
        w = wn
    return p, dist, w


def triangulate(C, D, ground_z=0.0, min_angle_deg=MIN_ANGLE_DEG, huber_m=HUBER_M, w0=None, max_dz_m=MAX_DZ_M):
    """한 물체를 본 광선들 → 위치 하나.
    반환 dict: xyz, method('triangulation'|'plane'), reason, n_rays, n_used, max_angle_deg, rms_m, dist_m, weights
    - 시차 부족·교차 실패·높이 비정상이면 기존 방식(광선-평면 교차 중앙값)으로 되돌아간다."""
    C = np.atleast_2d(np.asarray(C, float))
    D = _unit(np.atleast_2d(D))
    n = len(C)
    res = {"n_rays": n, "max_angle_deg": max_pair_angle_deg(D), "reason": ""}

    def _plane(reason):
        P = ray_plane(C, D, ground_z)
        ok = np.isfinite(P).all(axis=1)
        xyz = np.r_[np.median(P[ok, :2], axis=0), ground_z] if ok.any() else np.full(3, np.nan)
        res.update(xyz=xyz, method="plane", reason=reason, n_used=int(ok.sum()), rms_m=np.nan,
                   dist_m=np.full(n, np.nan), weights=ok.astype(float))
        return res

    if n < 2:
        return _plane("광선 2개 미만")
    if res["max_angle_deg"] < min_angle_deg:
        return _plane(f"시차 {res['max_angle_deg']:.1f}° < {min_angle_deg}°")
    p, dist, w = intersect_rays_robust(C, D, huber_m, w0)
    if not np.isfinite(p).all():
        return _plane("교차 실패(광선 평행)")
    used = w > 0.5 * w.max()
    t = np.einsum("ij,ij->i", D, p[None] - C)           # 각 카메라에서 교차점까지 광선 거리
    if np.median(t[used]) < MIN_RANGE_M:
        return _plane(f"교차점이 카메라에 붙음 ({np.median(t[used]):.1f} m) — 같은 위치 광선")
    if max_dz_m is not None and abs(p[2] - ground_z) > max_dz_m:
        return _plane(f"교차점 높이 {p[2] - ground_z:+.1f} m 비정상")
    res.update(xyz=p, method="triangulation", n_used=int(used.sum()),
               rms_m=float(np.sqrt(np.mean(dist[used] ** 2))), dist_m=dist, weights=w)
    return res


def rays_from_pose(K, pose, uv):
    """텔레메트리 자세(camera.Pose) + 픽셀 → (카메라 위치 c(3,), 단위 광선 d(N,3)).
    video_map 처럼 SRT 만 있을 때 쓴다. pose.alt 는 묶기·평면 대체에만 영향을 준다."""
    from .camera import camera_center, pixel_rays

    return camera_center(pose), _unit(pixel_rays(K, pose, uv))


def _rotate(v, axis, ang):
    """로드리게스 회전: v(N,3) 를 axis(N,3, 단위) 둘레로 ang(N,) 라디안."""
    c, s = np.cos(ang)[:, None], np.sin(ang)[:, None]
    return v * c + np.cross(axis, v) * s + axis * np.sum(axis * v, axis=1, keepdims=True) * (1 - c)


def uncertainty_mc(C, D, sig, ground_z=0.0, min_angle_deg=MIN_ANGLE_DEG, huber_m=HUBER_M, n=200, rng=None):
    """텔레메트리 오차를 몬테카를로로 흘려 위치 불확실성 반경(95 %, m)을 구한다.
    sig: config["georef"] (gps/alt/yaw/pitch 1σ). GPS 오차는 **모든 프레임에 공통인 편향**으로,
    yaw/pitch 오차는 프레임마다 독립으로 모델링한다 (삼각측량은 공통 편향을 못 없애므로 보수적).
    gps_jitter_m(기본 0.3): 프레임 간 GPS 흔들림 1σ."""
    rng = rng or np.random.default_rng(0)
    C = np.atleast_2d(np.asarray(C, float))
    D = _unit(np.atleast_2d(D))
    m = len(C)
    jit = sig.get("gps_jitter_m", 0.3)
    z = np.broadcast_to(np.array([0.0, 0.0, 1.0]), D.shape)
    pts = []
    for _ in range(n):
        common = np.r_[rng.normal(0, sig["gps_sigma_m"], 2), 0.0]
        Cj = C + common + rng.normal(0, [jit, jit, sig["alt_sigma_m"]], C.shape)
        Dj = _rotate(D, z, np.radians(rng.normal(0, sig["yaw_sigma_deg"], m)))
        ax = np.cross(Dj, z)
        nrm = np.linalg.norm(ax, axis=1, keepdims=True)
        ax = np.where(nrm > 1e-6, ax / np.where(nrm > 0, nrm, 1), np.array([1.0, 0.0, 0.0]))
        Dj = _rotate(Dj, ax, np.radians(rng.normal(0, sig["pitch_sigma_deg"], m)))
        r = triangulate(Cj, Dj, ground_z, min_angle_deg, huber_m, max_dz_m=None)
        pts.append(r["xyz"][:2])
    pts = np.array(pts)
    pts = pts[np.isfinite(pts).all(axis=1)]
    if len(pts) < n // 2:
        return float("inf")
    c = pts.mean(axis=0)
    return float(np.percentile(np.linalg.norm(pts - c, axis=1), 95))


def estimate_height_votes(hits, merge_m=1.0, max_pairs=3_000_000, bin_ratio=1.1, top=3):
    """쌍별 높이 투표 — 입력 높이 없이 '지면에서 카메라 높이'를 추정한다.

    광선의 수평 진행률 k = d_xy / |d_z| (1 m 내려갈 때 수평 이동). 카메라 높이가 h 이면 지면점은
    c_xy + h·k. 프레임이 다른 두 탐지 i, j 가 같은 물체라면  c_i + h k_i = c_j + h k_j  이므로
        h = −(Δc·Δk) / |Δk|²,   잔차 r = |Δc + h Δk|
    잔차가 merge_m 보다 작고 h>0 인 쌍만 투표하고, 로그 히스토그램의 봉우리를 돌려준다
    (같은 물체 쌍은 실제 높이에 모이고, 다른 물체 쌍은 흩어진다).
    반환: [(높이 m, 표 수), ...] 표 많은 순 top 개. 표가 3 미만이면 []."""
    hs = [h for h in hits if h["d"][2] < 0 and h.get("frame") is not None]
    if len(hs) < 2:
        return []
    kinds = np.array([h["kind"] for h in hs])
    fr = np.array([hash(h["frame"]) for h in hs])
    C = np.array([h["c"][:2] for h in hs])
    D = np.array([h["d"] for h in hs])
    Kk = D[:, :2] / (-D[:, 2:3])
    n = len(hs)
    if n * n > max_pairs:                       # 너무 많으면 균등 표본
        idx = np.random.default_rng(0).choice(n, int(np.sqrt(max_pairs)), replace=False)
        kinds, fr, C, Kk, n = kinds[idx], fr[idx], C[idx], Kk[idx], len(idx)
    iu, ju = np.triu_indices(n, 1)
    ok = (kinds[iu] == kinds[ju]) & (fr[iu] != fr[ju])
    iu, ju = iu[ok], ju[ok]
    dc = C[ju] - C[iu]
    dk = Kk[ju] - Kk[iu]
    nk = np.einsum("ij,ij->i", dk, dk)
    good = nk > 1e-9
    h = np.full(len(iu), np.nan)
    h[good] = -np.einsum("ij,ij->i", dc[good], dk[good]) / nk[good]
    r = np.linalg.norm(dc + h[:, None] * dk, axis=1)
    votes = h[(h > 0.3) & (r < merge_m)]
    if len(votes) < 3:
        return []
    lo = np.log(votes)
    edges = np.arange(lo.min(), lo.max() + np.log(bin_ratio), np.log(bin_ratio))
    cnt, _ = np.histogram(lo, edges)
    out = []
    for b in np.argsort(-cnt)[:top]:
        if cnt[b] == 0:
            break
        sel = votes[(lo >= edges[b]) & (lo < edges[b + 1] + 1e-12)]
        out.append((float(np.median(sel)), int(cnt[b])))
    return out


def group(hits, merge_m=1.0, ground_z=0.0):
    """같은 물체를 본 탐지들을 묶는다 (같은 kind + 근사 지면점이 merge_m 안 + 한 프레임엔 한 번).
    hits: [{kind, cls, score, c(3,), d(3,), frame, ...}, ...]. 근사 지면점은 광선-평면 교차라
    ground_z(=카메라 높이 가정)가 틀리면 같은 물체도 프레임마다 다른 자리에 찍혀 묶이지 않는다
    → locate() 가 높이 후보를 여러 개 시험한다."""
    for h in hits:
        h["approx"] = ray_plane(h["c"][None], h["d"][None], ground_z)[0, :2]
    hits = [h for h in hits if np.isfinite(h["approx"]).all()]
    objs = []
    for h in sorted(hits, key=lambda h: -h["score"]):
        fr = h.get("frame")
        for o in objs:
            if o["kind"] != h["kind"] or (fr is not None and fr in o["frames"]):
                continue
            if np.linalg.norm(o["approx"] - h["approx"]) < merge_m:
                o["hits"].append(h)
                o["frames"].add(fr)
                o["approx"] = np.median([q["approx"] for q in o["hits"]], axis=0)
                break
        else:
            objs.append({"kind": h["kind"], "hits": [h], "frames": {fr}, "approx": h["approx"].copy()})
    return objs


def locate(hits, ground_z=0.0, merge_m=1.0, min_hits=3, min_angle_deg=MIN_ANGLE_DEG, huber_m=HUBER_M,
           sig=None, refine=True, max_dz_m=MAX_DZ_M):
    """탐지 목록 → 물체 목록 (삼각측량). 반환 (objs, info).

    hits 의 각 항목: kind('litter'|'obstacle'), cls, score, frame, c(3,) 카메라 위치, d(3,) 광선, 그 외
    (thumb, box ...) 는 가장 신뢰도 높은 탐지 것이 물체에 복사된다.
    ground_z: 지면 높이 가정 (orbit_map 의 3D 좌표계는 0; video_map 도 0 = "카메라 높이 = pose.alt").
    refine: 쌍별 높이 투표로 실제 높이 후보를 만들고, 삼각측량이 가장 잘 맞는 후보로 묶는다.
    sig: config["georef"] 를 주면 물체마다 r95_m (오차 반경) 을 계산한다.

    물체 dict: kind, cls, score, n, n_used, xyz(3,), x, y, z, method, reason, max_angle_deg, rms_m,
               frames, hits, (r95_m)
    info: n_hits, cam_height_in_m, cam_height_votes[(m, 표)], cam_height_used_m, cam_height_est_m(삼각측량 역산),
          ground_z_used, n_triangulated, n_plane"""
    hits = [h for h in hits if np.isfinite(h["c"]).all() and np.isfinite(h["d"]).all()]
    info = {"ground_z_in": float(ground_z), "n_hits": len(hits)}
    if not hits:
        return [], info

    def _pass(gz, dz):
        out = []
        for g in group(hits, merge_m, gz):
            if len(g["hits"]) < min_hits:
                continue
            hs = g["hits"]
            C = np.array([h["c"] for h in hs])
            D = np.array([h["d"] for h in hs])
            r = triangulate(C, D, gz, min_angle_deg, huber_m, w0=[h["score"] for h in hs], max_dz_m=dz)
            if not np.isfinite(r["xyz"]).all():
                continue
            best = max(hs, key=lambda h: h["score"])
            names = [h["cls"] for h in hs]
            o = {k: v for k, v in best.items() if k not in ("c", "d", "approx", "score", "cls", "kind")}
            o.update(kind=g["kind"], cls=max(set(names), key=names.count), score=float(best["score"]),
                     n=len(hs), n_used=r["n_used"], xyz=r["xyz"], x=float(r["xyz"][0]), y=float(r["xyz"][1]),
                     z=float(r["xyz"][2]), method=r["method"], reason=r["reason"],
                     max_angle_deg=r["max_angle_deg"], rms_m=r["rms_m"], frames=[h.get("frame") for h in hs],
                     hits=hs)
            out.append(o)
        return out

    def _score(objs):   # 삼각측량에 쓰인 광선이 많고 잔차가 작을수록 좋다
        tri = [o for o in objs if o["method"] == "triangulation"]
        rms = float(np.median([o["rms_m"] for o in tri])) if tri else np.inf
        return (sum(o["n_used"] for o in tri), -rms)

    cam_z = float(np.median([h["c"][2] for h in hits]))
    h_in = cam_z - ground_z
    info["cam_height_in_m"] = h_in
    cands = [h_in]
    if refine:
        votes = estimate_height_votes(hits, merge_m)
        info["cam_height_votes"] = votes
        cands += [v[0] for v in votes if abs(np.log(max(v[0], 1e-6) / max(h_in, 1e-6))) > 0.05]
    best = None
    for h in cands:                                   # 후보마다 묶어 보고 가장 자기일관적인 것을 채택
        objs = _pass(cam_z - h, None)
        key = _score(objs)
        if best is None or key > best[0]:
            best = (key, h, objs)
    _, h_used, objs = best
    gz_used = cam_z - h_used
    tri = [o for o in objs if o["method"] == "triangulation"]
    if tri:                                           # 삼각측량 교차점 높이로 지면을 한 번 더 다듬는다
        gz_est = float(np.median([o["z"] for o in tri]))
        info["cam_height_est_m"] = cam_z - gz_est
        if abs(gz_est - gz_used) < 0.5 * max(h_used, 1.0):
            gz_used = gz_est
    info.update(cam_height_used_m=cam_z - gz_used, ground_z_used=gz_used,
                refined=abs(gz_used - ground_z) > 0.2 * max(h_in, 1.0))
    objs = _pass(gz_used, max_dz_m)                   # 최종: 높이 검사까지 적용
    info["n_triangulated"] = sum(o["method"] == "triangulation" for o in objs)
    info["n_plane"] = len(objs) - info["n_triangulated"]
    if sig:
        for o in objs:
            C = np.array([h["c"] for h in o["hits"]])
            D = np.array([h["d"] for h in o["hits"]])
            o["r95_m"] = uncertainty_mc(C, D, sig, gz_used, min_angle_deg, huber_m, n=sig.get("n_mc", 200))
    return objs, info


def summary(objs, info):
    """콘솔 출력용 요약."""
    lines = [f"삼각측량 {info.get('n_triangulated', 0)}개 · 평면교차 대체 {info.get('n_plane', 0)}개 (탐지 {info.get('n_hits', 0)}건)"]
    if "cam_height_in_m" in info:
        s = f"카메라 높이: 입력 {info['cam_height_in_m']:.1f} m"
        if info.get("cam_height_votes"):
            s += " · 쌍별 투표 " + ", ".join(f"{h:.1f} m({n}표)" for h, n in info["cam_height_votes"])
        if "cam_height_est_m" in info:
            s += f" · 삼각측량 역산 {info['cam_height_est_m']:.1f} m"
        s += f" → 사용 {info.get('cam_height_used_m', info['cam_height_in_m']):.1f} m"
        if info.get("refined"):
            s += "  ⚠️ 입력 높이와 20 % 이상 다름 (SRT/입력 고도 확인)"
        lines.append(s)
    for o in objs:
        tag = f"{o['cls']} ({o['n']}프레임, 시차 {o['max_angle_deg']:.0f}°"
        tag += f", 잔차 {o['rms_m']:.2f} m" if np.isfinite(o["rms_m"]) else f", {o['reason']}"
        tag += f", ±{o['r95_m']:.1f} m" if "r95_m" in o and np.isfinite(o["r95_m"]) else ""
        lines.append("  " + tag + ")")
    return "\n".join(lines)
