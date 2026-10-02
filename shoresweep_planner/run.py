"""한 번에 실행: input/ 의 파이프라인 결과 → outputs/plan/수거계획.html (브라우저 자동 열림).

  python run.py                 input/ 에 바로 파일이 있으면 한 현장 → outputs/plan/
                                input/ 안에 현장 폴더가 여러 개면 전부 → outputs/site/<현장>/ + 목록 outputs/site/index.html
  python run.py --example       examples/ 의 샘플(학교 야간 비행 상자 30개, 선회 시험) 로 만들어 보기 → outputs/examples/
  python run.py --input 폴더    다른 폴더 하나
  python run.py --serve         만든 뒤 로컬 서버(serve.py) 로 열기 → 같은 와이파이의 휴대폰에서 접속·진행 공유
옵션이 더 필요하면  python scripts/17_collection_plan.py --help
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from litter3d.build import build_site, has_site_data  # noqa: E402
from litter3d.site import build_index  # noqa: E402


def site_folders(root: Path) -> list[Path]:
    return sorted(d for d in root.iterdir() if d.is_dir() and not d.name.startswith((".", "_")) and has_site_data(d))


def build_many(folders: list[Path], out_root: Path, quiet: bool = False) -> Path:
    entries = []
    for f in folders:
        print(f"\n===== {f.name} =====")
        r = build_site(f, out_root / f.name, site_id=f.name, index_href="../index.html", quiet=quiet)
        png = r.out / "수거계획_지도.png"
        thumb = None
        try:
            import cv2
            import numpy as np
            img = cv2.imdecode(np.fromfile(str(png), np.uint8), cv2.IMREAD_COLOR)
            s = 900 / max(img.shape[:2]); img = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
            thumb = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode() if ok else None
        except Exception:  # noqa: BLE001
            pass
        t = r.plan.totals
        entries.append({"id": f.name, "title": r.plan.site, "href": f"{f.name}/수거계획.html", "png": thumb, "totals": t,
                        "survey": r.plan.survey_date, "basis_counts": t.get("basis_counts"), "description": r.cfg.get("description", "")})
    return build_index(entries, out_root / "index.html")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=None, help="입력 폴더 (기본 input/)")
    ap.add_argument("--out", default=None, help="출력 폴더")
    ap.add_argument("--example", action="store_true", help="examples/ 샘플로 만들어 보기")
    ap.add_argument("--serve", action="store_true", help="만든 뒤 로컬 서버로 열기")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    if a.example:
        folders = site_folders(ROOT / "examples"); out_root = Path(a.out) if a.out else ROOT / "outputs" / "examples"
        target = build_many(folders, out_root); rel = "examples/index.html"
    else:
        inp = Path(a.input) if a.input else ROOT / "input"
        if has_site_data(inp):
            out = Path(a.out) if a.out else ROOT / "outputs" / "plan"
            r = build_site(inp, out, site_id=inp.name if a.input else "input")
            target = r.out / "수거계획.html"; rel = "plan/수거계획.html"
        else:
            folders = site_folders(inp) if inp.exists() else []
            if not folders:
                sys.exit(f"{inp} 에 파이프라인 결과가 없습니다.\n  objects3d.csv / objvol.json / summary.json / items.csv / objects.csv / labels.json 중 하나를 넣으세요 (input/README.md)\n"
                         f"  샘플로 먼저 보려면:  python run.py --example")
            out_root = Path(a.out) if a.out else ROOT / "outputs" / "site"
            target = build_many(folders, out_root); rel = "site/index.html"
    print(f"\n결과: {target}")
    if a.serve:
        from serve import serve
        serve(ROOT / "outputs", a.port, open_path=rel if not a.no_open else None)
    elif not a.no_open:
        try:
            webbrowser.open(target.resolve().as_uri())
        except Exception:
            pass


if __name__ == "__main__":
    if os.name == "nt":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    main()
