"""섬 상세 영상 제작: python -m incheon_debris_sim.make_island gyodong [seogeom ...] --results output/sim_results_dx100.npz --dx 100"""
import os
import sys
import argparse
import numpy as np

from . import config as C
from . import geodata as G
from . import currents as CU
from . import render as R
from . import island as I


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="+", choices=list(I.ISLANDS))
    ap.add_argument("--results", default=os.path.join(C.OUT_DIR, "sim_results_dx100.npz"))
    ap.add_argument("--dx", type=float, default=100.0)
    ap.add_argument("--stills", action="store_true", help="정지화면만 (영상 생략)")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    dom = G.build_domain(dx=a.dx, verbose=False)
    model = CU.TidalFlowModel(dom, verbose=False)
    res = dict(np.load(a.results))
    for key in a.keys:
        ian = I.analyze_island(dom, res, key)
        print(f"[{key}] 섬 해안 좌초 입자 {ian['n_beached_island']:.0f}, 구간 {len(ian['segs'])}, 순위: " +
              ", ".join(f"{e['name']}({e['length_km']:.1f}km)" for e in ian["rank"][:4]))
        R.island_figure(dom, ian, model=model)
        n, dpath = R.prepare(dom, model, res, R.island_scene(dom, res, ian))
        print(R.render_stills(dpath, [R.N_TITLE + 300, R.N_TITLE + R.N_TIDE + 250, R.N_TITLE + R.N_TIDE + 700, n - 10], prefix=f"frame_{key}"))
        if not a.stills:
            R.render_video(n, dpath, os.path.join(C.OUT_DIR, f"{key}_debris_simulation.mp4"), workers=a.workers)


if __name__ == "__main__":
    main()
