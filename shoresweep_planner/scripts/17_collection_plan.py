"""파이프라인 결과(쓰레기 위치 + 3D 부피) → 작업자용 수거 계획 (한 현장).

input/ 폴더에 파일을 넣고 실행하면 된다 (input/README.md 참고):
  input/objects3d.csv (+ plan.json, objects.csv)     batch3d 결과         ┐
  input/objvol.json (+ objects.csv, *_masks.jpg)     objvol 결과          │ 이 중 하나
  input/summary.json | items.csv | objects.csv | labels.json             ┘
  input/photos/*.jpg · input/masks/*.jpg               물체 사진 (선택)
  input/ortho/mosaic.jpg + mosaic.jgw (+ .prj) 또는 GeoTIFF    정사영상 (선택: 드론 영상 오버레이 + 지형 최단경로)
  input/config.json                                    현장 이름·출발지·좌표계·정답 크기 (선택)

  python run.py                                   # 저장소 루트에서 한 번에 (여러 현장 폴더면 전부)
  python scripts/17_collection_plan.py --workers 4 --hours 6 --travel boat --carry carry --objective weight
  python scripts/17_collection_plan.py --input examples/school_0015 --out outputs/school_0015

출력 (--out 폴더, 기본 outputs/plan):
  수거계획.html      인터랙티브 (조건을 바꾸면 브라우저 안에서 즉시 재계산, ★ 출발지 끌기, 오프라인 가능)  ← 브라우저로 열기
  수거계획_공개용.html  인터넷 링크(claude.ai 아티팩트 등) 로 올리는 변형 — 외부 지도 타일 없이 드론 영상만, 인쇄·내려받기 없음
  수거계획_지도.png  인쇄용 지도 · 수거계획.xlsx / zones.csv / objects.csv / plan.json / summary.md / 지형분류.png
"""
from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from litter3d.build import OUTPUT_FILES, build_site  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=str(ROOT / "input"), help="입력 폴더")
    ap.add_argument("--out", default=None, help="출력 폴더 (기본 outputs/plan)")
    ap.add_argument("--site", default=None, help="현장 이름 (기본 config.json)")
    ap.add_argument("--ortho", default=None, help="정사영상 파일 (기본 input/ortho 에서 자동)")
    ap.add_argument("--depot", default=None, help="출발·집결지 경도,위도 ('none' → 무게중심). 기본 config.json")
    ap.add_argument("--depot-name", default=None)
    ap.add_argument("--workers", type=int, default=None, help="한 팀 인원 (기본 config defaults 또는 2)")
    ap.add_argument("--hours", type=float, default=None, help="하루 작업 시간 (기본 4)")
    ap.add_argument("--teams", type=int, default=None, help="동시에 투입하는 팀 수")
    ap.add_argument("--calib", default=None, help="실측 보정 계수 (예: cardboard=0.8,rope=1.5) — 3D 추정 무게에 곱함")
    ap.add_argument("--link", type=float, default=None, help="구역 묶기 거리 m (가정값, 기본 150 또는 config)")
    ap.add_argument("--detour", type=float, default=None, help="지형 없을 때 직선 → 실제 거리 배수 (가정값, 기본 1.4)")
    ap.add_argument("--walk", type=float, default=None, help="걷기 속도 km/h (가정값, 기본 3)")
    ap.add_argument("--weight", choices=["ours", "company"], default=None, help="계획에 쓰는 무게 (ours = 3D 부피 추정)")
    ap.add_argument("--one-way", action="store_true", help="출발지로 돌아오지 않음")
    ap.add_argument("--travel", choices=["walk", "boat"], default=None, help="이동 방식 (정사영상 있을 때 보트 지원 가능)")
    ap.add_argument("--carry", choices=["pile", "carry"], default=None, help="pile 현장 적치 / carry 들고 이동(적재량 넘으면 복귀)")
    ap.add_argument("--objective", choices=["distance", "weight"], default=None, help="최단 이동 / 무게 우선")
    ap.add_argument("--codes", default=None, help="수거할 종류만 (예: cardboard,pet_bottle 또는 STY,ROP)")
    ap.add_argument("--min-kg", type=float, default=None, help="이 계획 무게 미만 물체는 건너뜀")
    ap.add_argument("--no-terrain", action="store_true", help="지형 격자(물·숲·맨땅) 사용 안 함")
    ap.add_argument("--cell", type=float, default=None, help="지형 격자 셀 크기 m (기본 10)")
    ap.add_argument("--crs", default=None, help="거리 계산용 투영 좌표계 (기본 config.json 또는 EPSG:5186)")
    ap.add_argument("--no-open", action="store_true", help="끝나고 브라우저로 열지 않음")
    a = ap.parse_args()
    from litter3d.collect import material
    ov = {"site": a.site, "ortho": a.ortho, "depot": a.depot, "depot_name": a.depot_name, "workers": a.workers, "hours": a.hours, "teams": a.teams,
          "link": a.link, "detour": a.detour, "walk": a.walk, "weight": a.weight, "one_way": a.one_way or None, "travel": a.travel, "carry": a.carry,
          "objective": a.objective, "min_kg": a.min_kg, "no_terrain": a.no_terrain or None, "cell": a.cell, "crs": a.crs,
          "calib": ({material(k.strip()).code: float(v) for k, v in (kv.split("=") for kv in a.calib.split(","))} if a.calib else None),
          "codes": ([material(c.strip()).code for c in a.codes.split(",")] if a.codes else None)}
    inp = Path(a.input)
    if not inp.exists():
        sys.exit(f"입력 폴더가 없습니다: {inp}")
    out = Path(a.out) if a.out else ROOT / "outputs" / "plan"
    r = build_site(inp, out, overrides=ov)
    print("\n결과:")
    for name in OUTPUT_FILES:
        if (r.out / name).exists():
            print(f"  {r.out / name}")
    if not a.no_open:
        try:
            webbrowser.open((r.out / "수거계획.html").resolve().as_uri())
        except Exception:
            pass


if __name__ == "__main__":
    if os.name == "nt":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    main()
