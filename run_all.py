"""전체 파이프라인 실행: 지형 → (위성지도 시도) → 조류 모델 → 입자추적 → 집적 분석 → 영상.

python run_all.py                      # 모든 단계
python run_all.py --nc data/currents.nc  # 실측 해류(NetCDF) 사용
python run_all.py --skip-sim           # 기존 output/sim_results.npz 로 영상만 다시 제작
python run_all.py --islands gyodong seogeom   # 섬 상세 영상도 제작 (100 m 격자, 200,000 입자 모의 추가)
"""
import os
import sys
import argparse
import numpy as np

from incheon_debris_sim import config as C, geodata as G, currents as CU, accumulate as A, basemap as B, render as R
from incheon_debris_sim.simulate import main as simulate_main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nc", default=None, help="실측 해류 NetCDF (u,v,time,lat,lon)")
    ap.add_argument("--skip-sim", action="store_true")
    ap.add_argument("--no-satellite", action="store_true", help="위성타일 다운로드 시도 생략")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--islands", nargs="*", default=[], help="섬 상세 영상 (gyodong, seogeom)")
    ap.add_argument("--island-n", type=int, default=200000, help="섬 상세 모의 입자 수")
    a = ap.parse_args()

    dom = G.build_domain()
    if not a.no_satellite and not os.path.exists(B.SAT_PATH):
        try:
            B.fetch_satellite_basemap()
        except Exception as e:  # 인터넷 불가 등
            print(f"[run_all] 위성 배경지도 다운로드 실패({e}); GSHHG 기반 모식 지도로 대체")
    if not a.skip_sim:
        simulate_main(a.nc)
    model = CU.ExternalCurrents(a.nc, dom) if a.nc and os.path.exists(a.nc) else CU.TidalFlowModel(dom, verbose=False)
    res = dict(np.load(os.path.join(C.OUT_DIR, "sim_results.npz")))
    an = A.analyze(dom, res, model=model)
    R.hotspot_figure(dom, an)
    n, dpath = R.prepare(dom, model, res, R.regional_scene(dom, res, an))
    R.render_video(n, dpath, os.path.join(C.OUT_DIR, "incheon_debris_simulation.mp4"), workers=a.workers)
    if a.islands:
        from incheon_debris_sim import island as I
        island_res = os.path.join(C.OUT_DIR, "sim_results_dx100.npz")
        if not a.skip_sim or not os.path.exists(island_res):
            simulate_main(a.nc, dx=100.0, n=a.island_n, out=island_res)
        dom100 = G.build_domain(dx=100.0, verbose=False)
        model100 = CU.ExternalCurrents(a.nc, dom100) if a.nc and os.path.exists(a.nc) else CU.TidalFlowModel(dom100, verbose=False)
        res100 = dict(np.load(island_res))
        for key in a.islands:
            ian = I.analyze_island(dom100, res100, key)
            R.island_figure(dom100, ian, model=model100)
            n, dpath = R.prepare(dom100, model100, res100, R.island_scene(dom100, res100, ian))
            R.render_video(n, dpath, os.path.join(C.OUT_DIR, f"{key}_debris_simulation.mp4"), workers=a.workers)


if __name__ == "__main__":
    main()
