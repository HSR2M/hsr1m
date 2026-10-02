"""input 폴더(파이프라인 결과 + config.json) → 수거계획 산출물 한 벌. run.py 와 scripts/17_collection_plan.py 가 이것을 부른다."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .collect import CollectParams, CollectPlan, make_collect_plan, save_plan_files, summary_markdown
from .collect_report import Basemap, build_collect_html, draw_static_map
from .pipeline_io import load_site_objects
from .plan import PlanParams
from .terrain import Terrain, save_class_png

IMG_EXT = (".jpg", ".jpeg", ".png")
WORLD_EXT = {".jpg": [".jgw", ".jpgw", ".wld"], ".jpeg": [".jgw", ".jpegw", ".wld"], ".png": [".pgw", ".pngw", ".wld"],
             ".tif": [".tfw", ".tifw", ".wld"], ".tiff": [".tfw", ".wld"]}
OUTPUT_FILES = ["수거계획.html", "수거계획_공개용.html", "수거계획_지도.png", "수거계획.xlsx", "zones.csv", "objects.csv", "plan.json", "summary.md"]


def read_world_file(path: Path) -> dict | None:
    """월드파일(픽셀 중심 기준) → 왼쪽 위 모서리 기준 {x0, y0, px, py}."""
    if not path.exists():
        return None
    v = [float(x) for x in path.read_text().split()]
    a, d, b, e, c, f = v[:6]
    return {"x0": c - a / 2, "y0": f - e / 2, "px": a, "py": e}


def read_crs(img: Path, default: str) -> str:
    prj = img.with_suffix(".prj")
    if prj.exists():
        try:
            from pyproj import CRS
            crs = CRS.from_wkt(prj.read_text())
            epsg = crs.to_epsg() or crs.to_epsg(min_confidence=25)
            if epsg:
                return f"EPSG:{epsg}"
            print(f"  .prj 에 EPSG 코드가 없어 config 의 좌표계 {default} 사용 ({crs.name})")
        except Exception:  # noqa: BLE001
            pass
    return default


def load_basemap(ortho: Path | None, crs_default: str, max_px: int = 3200) -> tuple[Basemap | None, str]:
    """ortho 의 GeoTIFF 또는 (jpg/png + 월드파일) → Basemap. 반환 (basemap 또는 None, crs)."""
    if ortho is None or not ortho.exists():
        return None, crs_default
    suf = ortho.suffix.lower()
    if suf in (".tif", ".tiff"):
        try:
            import numpy as np
            import rasterio
            with rasterio.open(ortho) as ds:
                s = max(1, int(max(ds.width, ds.height) / max_px))
                arr = ds.read([1, 2, 3], out_shape=(3, ds.height // s, ds.width // s))
                img = np.ascontiguousarray(arr.transpose(1, 2, 0)[:, :, ::-1])     # RGB → BGR
                t = ds.transform
                world = {"x0": t.c, "y0": t.f, "px": t.a, "py": t.e}
                crs = f"EPSG:{ds.crs.to_epsg()}" if ds.crs and ds.crs.to_epsg() else crs_default
                return Basemap.from_array(img, world, (ds.width, ds.height), crs), crs
        except ImportError:
            print("  ⚠ GeoTIFF 를 읽으려면 rasterio 가 필요합니다 (pip install rasterio) — 또는 tools/import_pipeline.py 가 만든 jpg + .jgw 사용")
            return None, crs_default
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ GeoTIFF 읽기 실패 ({e}) → 정사영상 없이 진행")
            return None, crs_default
    world = None
    for ext in WORLD_EXT.get(suf, [".wld"]):
        world = read_world_file(ortho.with_suffix(ext))
        if world:
            break
    if world is None:
        print(f"  ⚠ {ortho.name} 의 월드파일(.jgw/.pgw/.wld) 이 없어 정사영상 없이 진행")
        return None, crs_default
    crs = read_crs(ortho, crs_default)
    try:
        import cv2
        import numpy as np
        img = cv2.imdecode(np.fromfile(str(ortho), np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("이미지를 읽을 수 없음")
        full = (img.shape[1], img.shape[0])
        s = max(1.0, max(full) / max_px)
        if s > 1:
            img = cv2.resize(img, (int(full[0] / s), int(full[1] / s)), interpolation=cv2.INTER_AREA)
        return Basemap.from_array(img, world, full, crs), crs   # 월드파일이 원본 이미지 기준
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ 정사영상 읽기 실패 ({e})")
        return None, crs_default


def find_ortho(inp: Path, hint: str | None) -> Path | None:
    if hint:
        p = Path(hint)
        if not p.is_absolute():
            p = inp / hint
        if p.exists():
            return p
    ortho_dir = inp / "ortho"
    if not ortho_dir.exists():
        return None
    for pat in ("*.tif", "*.tiff", "mosaic.jpg", "overview.jpg", "*.jpg", "*.jpeg", "*.png"):
        for p in sorted(ortho_dir.glob(pat)):
            return p
    return None


def has_site_data(folder: Path) -> bool:
    return any((folder / f).exists() for f in ("objects3d.csv", "objvol.json", "summary.json", "items.csv", "objects.csv", "labels.json")) \
        or (folder / "config.json").exists() and bool(json.loads((folder / "config.json").read_text(encoding="utf-8")).get("objvol"))


@dataclass
class BuildResult:
    plan: CollectPlan
    out: Path
    site_id: str
    cfg: dict
    fmt: str
    terrain_used: bool
    basemap_used: bool


def build_site(input_dir: str | Path, out_dir: str | Path, *, overrides: dict | None = None, site_id: str | None = None,
               index_href: str | None = None, quiet: bool = False) -> BuildResult:
    """overrides: CLI 값 (None 이 아닌 것만 config.defaults 보다 우선). 키: workers hours teams link detour walk weight one_way travel carry
    objective codes min_kg no_terrain cell crs depot depot_name site calib"""
    ov = {k: v for k, v in (overrides or {}).items() if v is not None}
    inp = Path(input_dir); out = Path(out_dir)
    log = (lambda *a: None) if quiet else print
    cfg = json.loads((inp / "config.json").read_text(encoding="utf-8")) if (inp / "config.json").exists() else {}
    site_id = site_id or inp.name
    d = cfg.get("defaults", {})
    site = ov.get("site") or cfg.get("site") or inp.name
    crs_default = ov.get("crs") or cfg.get("crs", "EPSG:5186")
    if "depot" in ov:
        depot = None if str(ov["depot"]).lower() == "none" else tuple(float(v) for v in str(ov["depot"]).split(","))
        depot_name = ov.get("depot_name") or "출발지"
    elif cfg.get("depot"):
        depot = (float(cfg["depot"]["lon"]), float(cfg["depot"]["lat"])); depot_name = ov.get("depot_name") or cfg["depot"].get("name", "출발지")
    else:
        depot = None; depot_name = ov.get("depot_name") or "무게중심"
    log(f"[1] 입력 폴더: {inp}")
    ortho = find_ortho(inp, ov.get("ortho") or cfg.get("ortho"))
    basemap, crs = load_basemap(ortho, crs_default)
    objs, fmt = load_site_objects(inp, cfg, crs)
    if not objs:
        raise SystemExit(f"{inp}: 읽은 물체가 없습니다 (format={fmt})")
    from collections import Counter
    log(f"    형식 {fmt} · {len(objs)}개 · 종류 " + ", ".join(f"{material_ko(c)} {n}" for c, n in Counter(o.code for o in objs).most_common()) +
        " · 무게 근거 " + ", ".join(f"{k} {n}" for k, n in Counter(o.basis for o in objs).items()) + f" · 좌표계 {crs}" +
        (f" · 정사영상 {ortho.name}" if basemap else " · 정사영상 없음"))

    params = CollectParams(
        link_m=float(ov.get("link", d.get("link", 150.0))), detour=float(ov.get("detour", d.get("detour", 1.4))),
        walk_kmh=float(ov.get("walk", d.get("walk", 3.0))), workers=int(ov.get("workers", d.get("workers", 2))),
        hours_per_day=float(ov.get("hours", d.get("hours", 4.0))), round_trip=not ov.get("one_way", False),
        weight_source=ov.get("weight", "ours"), depot_lonlat=depot, depot_name=depot_name,
        travel=ov.get("travel", d.get("travel", "walk")), carry=ov.get("carry", d.get("carry", "pile")),
        objective=ov.get("objective", d.get("objective", "distance")), min_kg=float(ov.get("min_kg", 0.0)),
        teams=int(ov.get("teams", d.get("teams", 1))), calib=ov.get("calib"), include_codes=ov.get("codes"),
        zone_word=cfg.get("zone_word", "해안"), bag=PlanParams())

    center = None; terrain = None
    terrain_cfg = cfg.get("terrain") or {}
    if basemap is not None:
        e = basemap.extent_m
        center = ((e[0] + e[1]) / 2, (e[2] + e[3]) / 2)
        log(f"[2] 정사영상 축소본 {basemap.img.shape[1]}×{basemap.img.shape[0]} px, {basemap.world['px'] * basemap.full_px[0] / basemap.img.shape[1]:.3f} m/px")
        if not ov.get("no_terrain") and terrain_cfg.get("type", "ortho") != "none":
            cell = float(ov.get("cell", terrain_cfg.get("cell_m", 10.0)))
            extent = max(e[1] - e[0], e[3] - e[2])
            if extent < cell * 4:
                log(f"[2b] 정사영상 범위({extent:.0f} m)가 격자 셀({cell:g} m)에 비해 작아 지형 격자는 쓰지 않음 (config terrain.cell_m 으로 조정)")
            else:
                terrain = Terrain.from_basemap(basemap, cell)
                log(f"[2b] 지형 격자 {terrain.nr}×{terrain.nc} ({cell:g} m): " + ", ".join(f"{k} {v}" for k, v in terrain.summary().items()))
    else:
        log("[2] 정사영상 없음 → 위성 지도만, 거리는 직선 × 우회 배수 (input/ortho 에 mosaic.jpg + .jgw 또는 GeoTIFF 를 넣으면 지형 반영)")

    log("[3] 구역 묶기 · 경로 최적화 · 시간 계산")
    plan = make_collect_plan(objs, params, site=site, center_xy=center, crs_m=crs, terrain=terrain)
    t = plan.totals
    log(f"    구역 {t['zones']}곳 · 예상 {t['kg_plan']:.1f} kg (범위 {t['kg_min']:.1f}–{t['kg_max']:.1f}) · 부피 {t['volume_m3'] * 1000:.0f} L · "
        f"마대 {t['bags']}장 · 이동 {plan.route_len_m / 1000:.2f} km ({'지형' if terrain else '직선×우회'}, {params.travel}/{params.carry}) · "
        f"총 {plan.total_min / 60:.1f}시간 ({len(plan.teams)}팀 × {params.workers}명) → 최대 {max((x['days'] for x in plan.teams), default=0)}일" + (f" · 제외 {plan.n_skipped}개" if plan.n_skipped else ""))
    if t.get("truth") and t["truth"]["n_measured"]:
        tr = t["truth"]
        log(f"    정답 비교: 측정 {tr['n_measured']}/{tr['n']}개, 부피 합 {tr['measured_m3'] * 1000:.1f} L vs 정답 {tr['truth_m3'] * 1000:.1f} L ({(tr['measured_m3'] / tr['truth_m3'] - 1) * 100:+.0f} %)")

    log(f"[4] 저장: {out}")
    out.mkdir(parents=True, exist_ok=True)
    save_plan_files(plan, out)
    (out / "summary.md").write_text(summary_markdown(plan), encoding="utf-8")
    if terrain is not None:
        save_class_png(terrain, out / "지형분류.png")
    png = draw_static_map(plan, out / "수거계획_지도.png", basemap=basemap, crs_m=crs)
    shared_cfg = cfg.get("shared")
    if shared_cfg:                      # "NEXT_PUBLIC_SUPABASE_URL=https://..." 처럼 이름=값 으로 붙여 넣어도 값만 쓴다
        for key in ("url", "anon_key"):
            v = str(shared_cfg.get(key, "")).strip().strip('"').strip("'")
            if "=" in v and v.split("=", 1)[0].isupper():
                v = v.split("=", 1)[1].strip().strip('"').strip("'")
            shared_cfg[key] = v.rstrip("/")
    if shared_cfg and (str(shared_cfg.get("url", "")).startswith("<") or str(shared_cfg.get("anon_key", "")).startswith("<")
                       or not str(shared_cfg.get("url", "")).startswith("https://")):
        log("    공유 저장: config.json 의 shared.url / anon_key 가 아직 자리값(<...>) 이라 끄고 진행 (Supabase 값을 넣으면 켜짐)")
        shared_cfg = None
    if shared_cfg and shared_cfg.get("provider") == "supabase" and shared_cfg.get("url") and shared_cfg.get("anon_key"):
        log(f"    공유 저장: Supabase {shared_cfg['url']} (테이블 {shared_cfg.get('table', 'shared_state')})")
    common = dict(photos_dir=inp, mask_pattern=cfg.get("mask_pattern"), basemap=basemap, static_png=png, terrain=terrain, center_xy=center,
                  crs_m=crs, site_id=site_id, description=cfg.get("description", ""), source=cfg.get("source", ""),
                  truth_note=(cfg.get("truth") or {}).get("note", ""), index_href=index_href)
    build_collect_html(plan, out / "수거계획.html", shared_cfg=shared_cfg, **common)
    build_collect_html(plan, out / "수거계획_공개용.html", artifact=True, **common)   # claude.ai 아티팩트 등 공개 링크용
    for z in plan.zones:
        comp = ", ".join(f"{material_ko(k)} {v}" for k, v in z.by_code.items())
        flag = " ⚠2인" if z.heavy_ids else ""
        log(f"    {'ABCDEF'[z.team - 1] + '팀 ' if len(plan.teams) > 1 else ''}{z.day}일차 {z.step:>2}. {z.name:<10} {z.n_items:>2}개 ({comp}) {z.kg_plan:6.1f} kg 마대 {z.bags:>2} 접근 {z.dist_from_prev_m:5.0f} m "
            f"이동 {z.walk_min:3.0f}분 작업 {z.work_min:3.0f}분{flag}" + (f" 복귀 {z.returns}회" if z.returns else ""))
    return BuildResult(plan=plan, out=out, site_id=site_id, cfg=cfg, fmt=fmt, terrain_used=terrain is not None, basemap_used=basemap is not None)


def material_ko(code: str) -> str:
    from .collect import material
    return material(code).ko
