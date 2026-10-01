"""시뮬레이션 설정 로더.

기본은 인천·강화(regions/incheon.py). 환경변수 REGION=hawaii 를 주면 regions/hawaii.py 가 같은 이름들을 덮어쓴다.
출력은 output/ (인천) 또는 output/<region>/ 에 저장된다.
"""
import os
import importlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REGION_ENV = os.environ.get("REGION", "incheon").lower()

from .regions.incheon import *  # noqa: F401,F403  (기본값)
if _REGION_ENV != "incheon":
    _mod = importlib.import_module(f".regions.{_REGION_ENV}", __package__)
    globals().update({k: v for k, v in vars(_mod).items() if not k.startswith("_")})
REGION = _REGION_ENV

DATA_DIR = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "output") if REGION == "incheon" else os.path.join(ROOT, "output", REGION)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)
