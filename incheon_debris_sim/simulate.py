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


def main(external_nc=None):
    t0 = time.time()
    dom = G.build_domain()
    model = build_model(dom, external_nc)
    sim = DebrisSimulation(dom, model)
    print(f"[simulate] {C.N_PARTICLES} 입자, {C.SIM_DAYS}일, dt={C.DT:.0f}s 시작")
    res = sim.run()
    out = os.path.join(C.OUT_DIR, "sim_results.npz")
    np.savez_compressed(out, **res)
    st = np.bincount(res["final_state"], minlength=4)
    print(f"[simulate] 완료 {time.time() - t0:.0f}s → {out}")
    print(f"  최종: 부유 {st[1]}, 좌초 {st[2]}, 유출 {st[3]}, 미방출 {st[0]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CURRENT_NC"))
