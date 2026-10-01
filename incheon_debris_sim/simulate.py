"""30일 해양쓰레기 입자추적 실행 → output/sim_results.npz"""
import os
import sys
import time
import numpy as np

from . import config as C
from . import geodata as G
from . import currents as CU
from .particles import DebrisSimulation


def build_model(dom, external_nc=None, var_map=None):
    if external_nc and os.path.exists(external_nc):
        print(f"[simulate] 외부 해류 자료 사용: {external_nc}")
        return CU.ExternalCurrents(external_nc, dom, var_map=var_map)
    return CU.TidalFlowModel(dom)


def main(external_nc=None, dx=C.DX, n=C.N_PARTICLES, out=None):
    t0 = time.time()
    dom = G.build_domain(dx=dx)
    model = build_model(dom, external_nc)
    sim = DebrisSimulation(dom, model, n=n)
    print(f"[simulate] 격자 {dx:.0f} m, {n} 입자, {C.SIM_DAYS}일, dt={C.DT:.0f}s 시작")
    res = sim.run()
    out = out or os.path.join(C.OUT_DIR, "sim_results.npz")
    np.savez_compressed(out, **res)
    st = np.bincount(res["final_state"], minlength=4)
    print(f"[simulate] 완료 {time.time() - t0:.0f}s → {out}")
    print(f"  최종: 부유 {st[1]}, 좌초 {st[2]}, 유출 {st[3]}, 미방출 {st[0]}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("nc", nargs="?", default=os.environ.get("CURRENT_NC"), help="실측 해류 NetCDF (선택)")
    ap.add_argument("--dx", type=float, default=C.DX, help="격자 간격 m (기본 200; 섬 상세 100)")
    ap.add_argument("--n", type=int, default=C.N_PARTICLES, help="입자 수")
    ap.add_argument("--out", default=None, help="결과 npz 경로")
    a = ap.parse_args()
    main(a.nc, dx=a.dx, n=a.n, out=a.out)
