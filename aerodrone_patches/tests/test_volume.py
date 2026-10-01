import sys; import os; sys.path.insert(0, os.environ.get("LITTER_REPO", "."))
import numpy as np
from litter.volume import volume_heightmap, to_metric_auto, to_metric
rng = np.random.default_rng(0)
# 1) 상자 60×45×12 cm 윗면 점 + 가장자리 번짐(halo) 1 cm + 바닥 근처 잡음 → 번짐 보정 효과
L, W, H = 0.60, 0.45, 0.12
top = np.c_[rng.uniform(0, L, 3000), rng.uniform(0, W, 3000), H + rng.normal(0, 0.004, 3000)]
halo_n = 900
side = rng.integers(0, 4, halo_n)
hx = np.where(side == 0, rng.uniform(-0.012, 0, halo_n), np.where(side == 1, rng.uniform(L, L + 0.012, halo_n), rng.uniform(0, L, halo_n)))
hy = np.where(side == 2, rng.uniform(-0.012, 0, halo_n), np.where(side == 3, rng.uniform(W, W + 0.012, halo_n), rng.uniform(0, W, halo_n)))
halo = np.c_[hx, hy, rng.uniform(0.04, H, halo_n)]
O = np.vstack([top, halo])
truth = L * W * H * 1000
for er in (0.0, 0.006, 0.01, 0.015):
    v, foot, cell = volume_heightmap(O, agg="median", erode_m=er)
    print(f"erode {er*100:4.1f} cm → 부피 {v*1000:6.2f} L ({(v*1000/truth-1)*100:+.0f}%), 발자국 {foot:.4f} m² (정답 {L*W:.4f}), 칸 {cell*100:.2f} cm")
# 과도한 침식 → 발자국이 비면 보정 없이 원래 값
v, foot, _ = volume_heightmap(O, agg="median", erode_m=0.5)
print(f"erode 50 cm (과도) → {v*1000:.2f} L  (보정 생략돼 원래 값과 같아야 함)")

# 2) 축척 선택: 합성 장면 — SfM 단위 = 1/s m, 카메라가 반경 R 선회, 바닥 z=0, SRT 고도가 틀린 경우(이륙점이 2 m 높음)
s_true = 2.5          # m per SfM unit
P = np.c_[rng.uniform(-5, 5, 4000), rng.uniform(-5, 5, 4000), rng.normal(0, 0.01, 4000)] / s_true   # 바닥
C_m = np.array([[6*np.cos(a), 6*np.sin(a), 7.0] for a in np.linspace(0, 2*np.pi, 60, endpoint=False)])  # 실제 m
C = C_m / s_true
D = np.array([[-c[0], -c[1], -c[2]] / np.linalg.norm(c) for c in C_m])
gps = C_m[:, :2] + rng.normal(0, 0.3, (60, 2))
alt_ok = np.full(60, 7.0)
alt_bad = np.full(60, 5.0)     # 이륙점이 2 m 높아 상대고도가 5 m로 기록됨 (실제 7 m)
for name, alt, mode in [("고도 정확/auto", alt_ok, "auto"), ("고도 틀림/auto(12m 이동→gps)", alt_bad, "auto"),
                        ("고도 틀림/alt 강제", alt_bad, "alt"), ("고도 틀림/gps 강제", alt_bad, "gps")]:
    T, R, s, info = to_metric_auto(P, C, D, alt, gps, min_track_m=10.0, scale=mode)
    print(f"{name:<30} 축척 {s:.3f} (정답 {s_true}) · 출처 {info['scale_source']} · 이동 {info['track_extent_m']:.1f} m"
          f" · GPS배율 {info.get('gps_scale_factor_check', float('nan')):.2f}" + (f"\n    ⚠️ {info['scale_warning']}" if info.get('scale_warning') else ""))
# 이동이 작은(제자리 선회 반경 1 m) 경우 → 교차검증 생략, 고도 사용
C_m2 = np.array([[1*np.cos(a), 1*np.sin(a), 7.0] for a in np.linspace(0, 2*np.pi, 60, endpoint=False)])
T, R, s, info = to_metric_auto(P, C_m2 / s_true, D, alt_ok, C_m2[:, :2] + rng.normal(0, 0.3, (60, 2)), scale="gps")
print(f"반경 1 m 선회/gps 강제 → 축척 {s:.3f} · 출처 {info['scale_source']} · {info.get('scale_warning')}")
