import sys, types; import os; sys.path.insert(0, os.environ.get("LITTER_REPO", "."))
import numpy as np
from litter.objvol import Scene
# pycolmap 없이 gsd_at / focal_px 만 검사 (가짜 카메라: 1600 px 폭, 초점 1200 px)
sc = types.SimpleNamespace(cam=types.SimpleNamespace(width=1600, height=1200, params=np.array([1200.0, 800, 600]), focal_length_x=1200.0),
                           imgs=list(range(10)),
                           Cm=np.array([[7*np.cos(a), 7*np.sin(a), 7.0] for a in np.linspace(0, 6.28, 10)]))
print("focal_px", Scene.focal_px(sc))
sc.focal_px = lambda: Scene.focal_px(sc)
g = Scene.gsd_at(sc, [0, 0, 0.06], [0, 1, 2, 3], dense_px=1200)
print(f"gsd at 7 m orbit (거리 ≈ 9.9 m) = {g*100:.2f} cm/px  → 1 px 번짐 보정 = {g*100:.2f} cm")
# 0007 큰 상자 가로 61.6→60, 세로 49.2→45: 한쪽 0.8~2.1 cm → 1 GSD(≈1.1 cm) 보정이면 가로는 맞고 세로는 절반쯤
