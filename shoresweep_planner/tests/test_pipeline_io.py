import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest

from litter3d.pipeline_io import crop_sheet, detect_format, load_site_objects

EX = Path(__file__).resolve().parents[1] / "examples"


def test_objects3d_example_loads_with_proxies():
    cfg = json.loads((EX / "school_0015" / "config.json").read_text(encoding="utf-8"))
    objs, fmt = load_site_objects(EX / "school_0015", cfg, cfg["crs"])
    assert fmt == "objects3d" and len(objs) == 30
    basis = {o.basis for o in objs}
    assert basis == {"3d", "proxy"}
    assert all(o.truth_m3 == pytest.approx(0.42 * 0.32 * 0.39) for o in objs)
    ok = [o for o in objs if o.basis == "3d"]
    assert 8 <= len(ok) <= 12 and all(o.volume_m3 > 0 and o.height_m > 0 for o in ok)
    assert all(o.volume_m3 > 0 for o in objs)                      # 대체 부피가 들어감
    assert all(o.image_path and (EX / "school_0015" / o.image_path).exists() for o in objs)
    assert all(o.company_kg is not None and o.company_kg < 0.1 for o in objs)   # 업체 방식 비교값


def test_objvol_example_loads_with_truth_and_masks():
    cfg = json.loads((EX / "school_orbit" / "config.json").read_text(encoding="utf-8"))
    objs, fmt = load_site_objects(EX / "school_orbit", cfg, cfg["crs"])
    assert fmt == "objvol" and len(objs) == 6
    assert all(o.code == "cardboard" for o in objs)           # config material 로 바로잡음
    measured = [o for o in objs if o.basis == "3d"]
    assert len(measured) == 4 and all(o.image_path for o in measured)
    small = next(o for o in objs if o.obj_id.endswith("Plastic_Buoy_55"))
    assert small.truth_m3 == pytest.approx(0.003128) and small.volume_m3 == pytest.approx(0.0036945, rel=1e-3)


def test_detect_format_and_objects_only(tmp_path):
    with pytest.raises(FileNotFoundError):
        detect_format(tmp_path, {})
    with open(tmp_path / "objects.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["kind", "cls", "lat", "lon", "seen_frames", "best_score", "first_frame"])
        w.writerow(["litter", "PET_Bottle", 37.38, 126.65, 5, 0.8, 100]); w.writerow(["obstacle", "person", 37.38, 126.65, 5, 0.9, 100])
        w.writerow(["litter", "Net", 37.3801, 126.6501, 3, 0.5, 200])
    objs, fmt = load_site_objects(tmp_path, {}, "EPSG:5186")
    assert fmt == "objects" and [o.code for o in objs] == ["pet_bottle", "net"] and all(o.basis == "count" for o in objs)


def test_items_csv_small_and_aggregated(tmp_path):
    cols = ["item_id", "stop_id", "cls", "cls_raw", "lat", "lon", "area_m2", "length_m", "h_p90_m", "volume_m3", "valid_3d",
            "weight_est_kg", "weight_lo_kg", "weight_hi_kg", "weight_method", "crew", "image"]
    rows = []
    for i in range(12):
        rows.append([f"it{i}", f"S{i // 3:03d}", "eps_fragment", "styrofoam", 37.38 + i * 1e-4, 126.65, 0.3, 0.6, 0.0, 0.009, "False", 0.2, 0.1, 0.6, "2d", "1인", ""])
    with open(tmp_path / "items.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    with open(tmp_path / "stops.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["visit_order", "stop_id", "lat", "lon", "n_items", "kg_est", "kg_hi", "max_item_kg_hi", "crew", "tools", "bulk_m3", "r95_m", "buried_suspect", "classes"])
        for s in range(4):
            w.writerow([s + 1, f"S{s:03d}", 37.38 + s * 3e-4, 126.65, 3, 0.6, 1.8, 0.6, "1인", "", 0.027, 1.2, "False", "eps_fragment"])
    objs, fmt = load_site_objects(tmp_path, {}, "EPSG:5186")
    assert fmt == "stops" and len(objs) == 12 and objs[0].basis == "2d" and objs[0].kg_typ == pytest.approx(0.2)
    objs2, _ = load_site_objects(tmp_path, {"max_objects": 5}, "EPSG:5186")
    assert len(objs2) == 4 and objs2[0].basis == "agg" and objs2[0].n_items == 3 and objs2[0].kg_typ == pytest.approx(0.6)
    assert objs2[0].kg_by["styrofoam_fragment"][5] == 3


def test_crop_sheet(tmp_path):
    import cv2
    import numpy as np
    img = np.zeros((360, 960, 3), np.uint8); img[:, :, 1] = 120
    cv2.imencode(".jpg", img)[1].tofile(str(tmp_path / "sheet.jpg"))
    paths = crop_sheet(tmp_path / "sheet.jpg", tmp_path / "photos", cols=3, rows=2, n=5)
    assert len(paths) == 5 and paths[0].name == "01.jpg"
