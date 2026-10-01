"""
삼각측량 모듈 검증 — 정답을 아는 합성 상황에서 돌린다 (numpy 만 필요).

    python tests/test_triangulate.py            # 또는  pytest tests/test_triangulate.py

시나리오
  1) 직진 비행 + 수직 카메라, 입력 높이가 크게 틀림(3.7 m 입력 / 실제 20 m)
     → 삼각측량은 맞고, 기존 평면 교차는 비례해서 틀린다. 역산 높이 ≈ 20 m.
  2) 제자리 호버링(시차 없음) → 평면 교차로 자동 대체
  3) 잘못 묶인 광선 1개(이상치) → Huber 가중치로 배제
  4) 경사 촬영(짐벌 -60°) 선회 → 삼각측량 정상
  5) 몬테카를로 오차 반경이 유한하고 상식적
  6) min_angle_deg=inf 이면 기존 방식과 같다 (정확한 높이일 때 둘 다 맞음)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from litter.camera import Intrinsics, Pose, ground_to_pixel  # noqa: E402
from litter.triangulate import locate, rays_from_pose, triangulate, uncertainty_mc  # noqa: E402

K = Intrinsics.from_f35(3840, 2160, 24.0)
SIG = {"gps_sigma_m": 2.5, "alt_sigma_m": 1.0, "yaw_sigma_deg": 2.0, "pitch_sigma_deg": 1.0, "n_mc": 100}


def make_hits(objs, poses_true, alt_input, px_noise=3.0, seed=0, cls="box"):
    """정답 물체(xyz)들을 실제 자세로 투영해 픽셀을 만들고, 입력 고도(틀릴 수 있음)로 광선을 만든다."""
    rng = np.random.default_rng(seed)
    hits = []
    for k, pt in enumerate(poses_true):
        uv = ground_to_pixel(K, pt, objs)
        uv = uv + rng.normal(0, px_noise, uv.shape)
        for j, (u, v) in enumerate(uv):
            if not (0 <= u < K.width and 0 <= v < K.height):
                continue
            pin = Pose(pt.x, pt.y, alt_input, pt.yaw, pt.pitch, pt.roll)
            c, d = rays_from_pose(K, pin, [[u, v]])
            hits.append({"kind": "litter", "cls": cls, "score": 0.9 - 0.01 * j, "c": c, "d": d[0], "frame": k, "obj": j})
    return hits


def straight_pass(h=20.0, speed=5.0, dt=1.0, n=7, pitch=-90.0, yaw=90.0, x0=-15.0):
    return [Pose(x0 + speed * dt * k, 0.0, h, yaw, pitch) for k in range(n)]


def err_xy(objs, truth):
    """물체마다 가장 가까운 정답까지 거리."""
    return np.array([np.min(np.linalg.norm(truth[:, :2] - o["xyz"][:2], axis=1)) for o in objs])


def test_wrong_height_straight_pass():
    truth = np.array([[0.0, 3.0, 0.15], [0.0, 8.0, 0.15], [5.0, -4.0, 0.15], [-5.0, 6.0, 0.15]])
    hits = make_hits(truth, straight_pass(h=20.0), alt_input=3.7)
    objs, info = locate(hits, ground_z=0.0, merge_m=1.0, min_hits=3)
    assert len(objs) == 4, f"물체 수 {len(objs)} != 4 (묶기 실패)"
    assert all(o["method"] == "triangulation" for o in objs), [o["reason"] for o in objs]
    e = err_xy(objs, truth)
    assert e.max() < 0.3, f"삼각측량 오차 {e.round(2)} m"
    assert abs(info["cam_height_used_m"] - 20.0) < 0.5, info
    assert info.get("refined"), "틀린 높이를 역산해 다시 묶어야 함"
    # 같은 입력으로 기존 방식(평면 교차)만 쓰면 가로 거리가 3.7/20 로 줄어 틀린다
    old, _ = locate(hits, ground_z=0.0, merge_m=1.0, min_hits=3, min_angle_deg=np.inf, refine=False)
    e_old = err_xy(old, truth)
    assert len(old) == 0 or e_old.max() > 2.0, f"평면 교차가 틀려야 정상인데 {e_old.round(2)}"
    old_msg = "물체를 못 묶음(0개)" if len(old) == 0 else f"최대 오차 {e_old.max():.2f} m"
    return f"삼각측량 최대 오차 {e.max():.2f} m · 기존 방식 {old_msg} · 역산 높이 {info['cam_height_used_m']:.1f} m (입력 3.7)"


def test_along_track_objects_wrong_height():
    """비행 방향으로 일렬(간격 6 m, 드론 간격 5 m)인 물체 3개 + 입력 높이 2.5배 틀림(8 m 입력/실제 20 m)."""
    truth = np.array([[-6.0, 3.0, 0.1], [0.0, 3.0, 0.1], [6.0, 3.0, 0.1]])
    hits = make_hits(truth, straight_pass(h=20.0, n=9, x0=-20.0), alt_input=8.0)
    objs, info = locate(hits, ground_z=0.0, merge_m=1.0, min_hits=3)
    assert len(objs) == 3, f"물체 수 {len(objs)} != 3"
    e = err_xy(objs, truth)
    assert e.max() < 0.3 and all(o["method"] == "triangulation" for o in objs), (e, [o["reason"] for o in objs])
    assert abs(info["cam_height_used_m"] - 20.0) < 1.0, info
    return f"오차 {e.round(2)} m · 투표 {info['cam_height_votes'][:2]} · 사용 높이 {info['cam_height_used_m']:.1f} m"


def test_hover_fallback():
    truth = np.array([[2.0, 1.0, 0.1]])
    poses = [Pose(0.02 * k, 0.0, 10.0, 0.0, -90.0) for k in range(5)]   # 10 cm 안에서 호버링
    hits = make_hits(truth, poses, alt_input=10.0)
    objs, info = locate(hits, min_hits=3)
    assert len(objs) == 1 and objs[0]["method"] == "plane", objs[0].get("reason")
    assert err_xy(objs, truth)[0] < 0.3
    return f"시차 {objs[0]['max_angle_deg']:.2f}° → {objs[0]['reason']}, 오차 {err_xy(objs, truth)[0]:.2f} m"


def test_outlier_ray():
    truth = np.array([[0.0, 2.0, 0.1]])
    hits = make_hits(truth, straight_pass(h=15.0, n=6), alt_input=15.0)
    wrong = make_hits(np.array([[0.0, 5.0, 0.1]]), straight_pass(h=15.0, n=1, x0=0.0), alt_input=15.0)[0]
    wrong["score"] = 0.95   # 가장 자신있는 탐지가 엉뚱한 물체
    C = np.array([h["c"] for h in hits + [wrong]])
    D = np.array([h["d"] for h in hits + [wrong]])
    r = triangulate(C, D, w0=[h["score"] for h in hits + [wrong]])
    e = np.linalg.norm(r["xyz"][:2] - truth[0, :2])
    assert r["method"] == "triangulation" and e < 0.3, (r["method"], e)
    assert r["weights"][-1] < 0.3 * r["weights"][:-1].max(), r["weights"].round(2)
    return f"이상치 가중치 {r['weights'][-1]:.2f} (정상 {r['weights'][:-1].mean():.2f}), 오차 {e:.2f} m"


def test_oblique_orbit():
    truth = np.array([[0.0, 0.0, 0.2], [3.0, 1.0, 0.2]])
    poses = []
    for k in range(8):   # 반경 6 m 선회, 짐벌 -60° 로 중심을 본다
        a = np.radians(45 * k)
        x, y = 6 * np.sin(a), 6 * np.cos(a)
        yaw = (np.degrees(np.arctan2(-x, -y))) % 360
        poses.append(Pose(x, y, 7.0, yaw, -60.0))
    hits = make_hits(truth, poses, alt_input=7.0, px_noise=2.0)
    objs, info = locate(hits, merge_m=1.0, min_hits=3)
    assert len(objs) == 2 and all(o["method"] == "triangulation" for o in objs)
    e = err_xy(objs, truth)
    assert e.max() < 0.3, e
    assert all(abs(o["z"] - 0.2) < 0.3 for o in objs), [o["z"] for o in objs]
    return f"오차 {e.round(2)} m · 높이 {[round(o['z'], 2) for o in objs]} m"


def test_mc_radius():
    truth = np.array([[0.0, 3.0, 0.1]])
    hits = make_hits(truth, straight_pass(h=20.0), alt_input=20.0)
    C = np.array([h["c"] for h in hits])
    D = np.array([h["d"] for h in hits])
    r95 = uncertainty_mc(C, D, SIG, n=100)
    assert np.isfinite(r95) and 1.0 < r95 < 10.0, r95
    return f"r95 = {r95:.1f} m (GPS 1σ 2.5 m 가정)"


def test_same_as_old_when_height_right():
    truth = np.array([[0.0, 3.0, 0.1], [4.0, -2.0, 0.1]])
    hits = make_hits(truth, straight_pass(h=20.0), alt_input=20.0)
    new, _ = locate(hits, merge_m=1.0, min_hits=3)
    old, _ = locate(hits, merge_m=1.0, min_hits=3, min_angle_deg=np.inf, refine=False)
    assert err_xy(new, truth).max() < 0.3 and err_xy(old, truth).max() < 0.3
    return f"높이가 맞으면 둘 다 맞음: 새 {err_xy(new, truth).max():.2f} m · 기존 {err_xy(old, truth).max():.2f} m"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    fails = 0
    for t in tests:
        try:
            msg = t()
            print(f"PASS {t.__name__}: {msg}")
        except Exception as e:  # noqa: BLE001 — 실패 원인을 보여주고 계속
            fails += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - fails}/{len(tests)} 통과")
    sys.exit(1 if fails else 0)
