import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pytest

from litter3d.classes import map_class
from litter3d.collect import (CollectParams, LitterObject, apply_estimate, cluster_by_matrix, estimate_2d, estimate_3d, estimate_count,
                              estimate_proxy, fill_proxies, load_geojson, make_collect_plan, material, save_plan_files, summary_markdown, tour_order)
from litter3d.plan import NIOSH_LIFT_LIMIT_KG
from litter3d.terrain import BARE, OUTSIDE, VEG, WATER, Terrain, classify_rgb


def _feature(seq, code, lon, lat, w_deg=0.00001, h_deg=0.00001, area=1.0, kg=0.012):
    ring = [[lon - w_deg, lat - h_deg], [lon + w_deg, lat - h_deg], [lon + w_deg, lat + h_deg], [lon - w_deg, lat + h_deg],
            [lon - w_deg, lat - h_deg]]
    return {"type": "Feature",
            "properties": {"survey_date": "2026-07-29", "region": "TST", "material_code": code, "detection_seq": seq,
                           "center_lon": lon, "center_lat": lat, "area_sqm": area, "weight_kg": kg,
                           "image_path": f"crops/TST_{seq:04d}_{code}.jpg"},
            "geometry": {"type": "Polygon", "coordinates": [ring]}}


def _obj(i, code, lon, lat, vol_L=None, conf="높음", crs="EPSG:5186", area=0.2):
    from pyproj import Transformer
    x, y = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform(lon, lat)
    m = material(code)
    o = LitterObject(obj_id=f"T{i:02d}", seq=i, code=m.code, class_name=m.class_name, class_ko=m.ko, lon=lon, lat=lat, x_m=x, y_m=y,
                     area_m2=area, w_m=0.4, h_m=0.3, company_kg=None, kg_min=0, kg_typ=0, kg_max=0, volume_m3=0, image_path=None, survey_date="2026-10-01")
    if vol_L is not None:
        o.height_m = 0.3; o.confidence = conf
        apply_estimate(o, estimate_3d(o.code, vol_L / 1000, conf))
    else:
        o.basis = "proxy"; o.volume_m3 = 0.0
    return o


@pytest.fixture
def geojson(tmp_path):
    feats = [_feature(1, "STY", 126.0800, 37.1700, area=1.5), _feature(2, "STY", 126.08015, 37.1700, area=0.8),
             _feature(3, "PLA", 126.0801, 37.17015, area=2.0),
             _feature(4, "STY", 126.0910, 37.1700, area=1.0), _feature(5, "ROP", 126.0911, 37.17005, area=20.0, kg=0.48)]
    p = tmp_path / "labels.json"
    p.write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
    return p


def test_class_mapping_covers_pipeline_names():
    assert map_class("cardboard box") == "cardboard"
    assert map_class("Styrofoam_Buoy_22") == "styrofoam_buoy"
    assert map_class("eps_fragment") == "styrofoam_fragment"
    assert map_class("plastic_other") == "other_plastic"
    assert map_class("STY") == "styrofoam_fragment" and map_class("FIS") == "net"
    assert map_class("PET_Bottle") == "pet_bottle"
    assert map_class("무엇인지 모름") == "unknown"
    assert material("STY").code == "styrofoam_fragment" and material("cardboard box").ko == "골판지 상자"


def test_estimate_3d_uses_apparent_density_and_confidence_range():
    e = estimate_3d("cardboard", 0.0524, "높음")
    assert e.basis == "3d" and e.kg_typ == pytest.approx(0.0524 * 30)
    assert e.vol_min == pytest.approx(0.0524 * 0.8) and e.vol_max == pytest.approx(0.0524 * 1.25)
    assert 0 < e.kg_min < e.kg_typ < e.kg_max
    low = estimate_3d("cardboard", 0.0524, "낮음(뷰 3)")
    assert low.kg_min < e.kg_min and low.kg_max > e.kg_max
    # 스티로폼: 재료 밀도(1000 배) 가 아니라 EPS 겉보기 밀도 20 kg/m³
    assert estimate_3d("styrofoam_buoy", 0.03).kg_typ == pytest.approx(0.6)


def test_estimate_2d_range_and_styrofoam_density():
    kmin, ktyp, kmax, vol, formula = estimate_2d("STY", 1.54)
    assert 0 < kmin < ktyp < kmax
    assert vol == pytest.approx(1.54 * 0.5 * 0.10)
    assert ktyp == pytest.approx(vol * 20)
    assert estimate_2d("XYZ", 1.0)[1] > 0
    assert estimate_count("pet_bottle").kg_typ == pytest.approx(0.0423)


def test_fill_proxies_uses_median_of_trusted_measurements():
    objs = [_obj(1, "cardboard", 126.08, 37.17, 20.6, "높음"), _obj(2, "cardboard", 126.0801, 37.17, 71.0, "높음"),
            _obj(3, "cardboard", 126.0802, 37.17, 283.1, "낮음(기울기 26°)"), _obj(4, "cardboard", 126.0803, 37.17, None),
            _obj(5, "pet_bottle", 126.0804, 37.17, None)]
    n = fill_proxies(objs)
    assert n == 2
    assert objs[3].basis == "proxy" and objs[3].volume_m3 == pytest.approx(np.median([0.0206, 0.071]))   # 낮음 은 제외
    assert objs[4].volume_m3 == pytest.approx(material("pet_bottle").default_vol_m3)                     # 같은 종류 측정 없음 → 기본 부피
    assert objs[3].kg_min < objs[3].kg_typ < objs[3].kg_max


def test_load_geojson_and_plan_zones(geojson):
    objs = load_geojson(geojson)
    assert len(objs) == 5 and objs[0].code == "styrofoam_fragment" and objs[0].basis == "2d"
    assert objs[4].company_kg == pytest.approx(0.48)
    assert objs[4].kg_typ > NIOSH_LIFT_LIMIT_KG
    p = CollectParams(depot_lonlat=(126.0790, 37.1700), depot_name="테스트 출발지", link_m=150, zone_word="구역")
    plan = make_collect_plan(objs, p, site="테스트", crs_m="EPSG:5186")
    assert plan.totals["zones"] == 2
    assert plan.zones[0].step == 1 and plan.zones[0].dist_from_prev_m > 0
    assert plan.totals["heavy"] == 1 and plan.zones[-1].heavy_ids or plan.zones[0].heavy_ids
    assert all("구역" in z.name for z in plan.zones)
    assert plan.route_len_m > 0 and plan.total_min > 0
    # 기업값으로 계획하면 무게가 아주 작아진다
    plan2 = make_collect_plan(objs, CollectParams(depot_lonlat=(126.0790, 37.1700), weight_source="company"), site="t", crs_m="EPSG:5186")
    assert plan2.totals["kg_plan"] < 2.0


def test_plan_with_3d_objects_and_truth(tmp_path):
    objs = [_obj(i, "cardboard", 126.08 + i * 0.0003, 37.17, 50.0 + i, "높음") for i in range(1, 7)]
    for o in objs:
        o.truth_m3 = 0.0524
    p = CollectParams(depot_lonlat=(126.0795, 37.1700), link_m=25, zone_word="구역", workers=2, hours_per_day=2)
    plan = make_collect_plan(objs, p, site="3D 테스트", crs_m="EPSG:5186")
    assert plan.totals["basis_counts"] == {"3d": 6}
    assert plan.totals["truth"]["n_measured"] == 6
    assert plan.totals["kg_plan"] == pytest.approx(sum(o.kg_typ for o in objs))
    files = save_plan_files(plan, tmp_path)
    assert (tmp_path / "plan.json").exists() and (tmp_path / "objects.csv").exists()
    d = json.loads((tmp_path / "plan.json").read_text(encoding="utf-8"))
    assert d["objects"][0]["basis"] == "3d" and "dims" in d["objects"][0]
    md = summary_markdown(plan)
    assert "3D 부피 측정 6개" in md and "정답" in md


def test_calibration_and_filters():
    objs = [_obj(1, "cardboard", 126.08, 37.17, 50.0), _obj(2, "pet_bottle", 126.0801, 37.17, 1.2)]
    base = make_collect_plan(objs, CollectParams(depot_lonlat=(126.0795, 37.17)), site="t", crs_m="EPSG:5186").totals["kg_plan"]
    cal = make_collect_plan(objs, CollectParams(depot_lonlat=(126.0795, 37.17), calib={"cardboard": 2.0}), site="t", crs_m="EPSG:5186").totals["kg_plan"]
    assert cal == pytest.approx(base + objs[0].kg_typ)
    only = make_collect_plan(objs, CollectParams(depot_lonlat=(126.0795, 37.17), include_codes=["pet_bottle"]), site="t", crs_m="EPSG:5186")
    assert only.n_objects == 1 and only.n_skipped == 1
    teams = make_collect_plan([_obj(i, "cardboard", 126.08 + i * 0.001, 37.17, 50.0) for i in range(1, 9)],
                              CollectParams(depot_lonlat=(126.0795, 37.17), teams=2, link_m=20), site="t", crs_m="EPSG:5186")
    assert len(teams.teams) == 2 and sum(len(t["zones"]) for t in teams.teams) == teams.totals["zones"]


def test_cluster_and_tour():
    D = np.array([[0, 10, 500, 510], [10, 0, 495, 505], [500, 495, 0, 12], [510, 505, 12, 0]], float)
    assert cluster_by_matrix(D, 150) == [0, 0, 1, 1]
    full = np.array([[0, 1, 5, 9], [1, 0, 2, 7], [5, 2, 0, 3], [9, 7, 3, 0]], float)
    assert tour_order(full, 0, [1, 2, 3], round_trip=False) == [1, 2, 3]
    big = np.random.default_rng(0).random((12, 12)) * 100; big = (big + big.T) / 2; np.fill_diagonal(big, 0)
    order = tour_order(big, 0, list(range(1, 12)))
    assert sorted(order) == list(range(1, 12))


def test_terrain_classification_and_paths():
    img = np.zeros((60, 60, 3), np.uint8)
    img[:, :, :] = (235, 235, 235)                 # 맨땅
    img[:, 25:35, :] = (200, 120, 30)              # 물 띠 (BGR: 파랑)
    img[:, 0:5, :] = (40, 160, 40)                 # 숲
    img[0:3, :, :] = 0                             # 영상 밖 (테두리)
    cls = classify_rgb(img)
    assert (cls[30, 30] == WATER) and (cls[30, 10] == BARE) and (cls[30, 2] == VEG) and (cls[1, 10] == OUTSIDE)
    t = Terrain(cls, 1.0, 0.0, 60.0, cell_m=2.0)
    D = t.matrix([(10, 30), (50, 30)], "walk")
    assert not np.isfinite(D[0, 1])                # 물을 못 건넘
    Db = t.matrix([(10, 30), (50, 30)], "boat")
    assert np.isfinite(Db[0, 1]) and Db[0, 1] > 40
    path = t.path((10, 30), (50, 30), "boat")
    assert len(path) > 2
    js = t.to_js()
    assert js["nr"] * js["nc"] == t.grid.size
