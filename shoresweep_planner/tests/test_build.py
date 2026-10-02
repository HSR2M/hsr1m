import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest

from litter3d.build import build_site, has_site_data

EX = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.parametrize("site", ["school_0015", "school_orbit"])
def test_build_example_site(tmp_path, site):
    r = build_site(EX / site, tmp_path / site, quiet=True)
    out = tmp_path / site
    for name in ("수거계획.html", "수거계획_공개용.html", "수거계획_지도.png", "plan.json", "zones.csv", "objects.csv", "summary.md", "수거계획.xlsx"):
        assert (out / name).exists(), name
    html = (out / "수거계획.html").read_text(encoding="utf-8")
    assert "window.PLAN=" in html and "Leaflet 1.9.4" in html        # 오프라인용 Leaflet 내장
    assert '"basis": "3d"' in html or '"basis":"3d"' in html
    d = json.loads((out / "plan.json").read_text(encoding="utf-8"))
    assert d["totals"]["zones"] == r.plan.totals["zones"] >= 1
    assert d["totals"]["basis_counts"].get("3d", 0) >= 3


def test_has_site_data(tmp_path):
    assert not has_site_data(tmp_path)
    (tmp_path / "objects.csv").write_text("kind,cls,lat,lon\n", encoding="utf-8")
    assert has_site_data(tmp_path)


def test_build_overrides(tmp_path):
    r = build_site(EX / "school_0015", tmp_path / "x", overrides={"workers": 4, "hours": 1.0, "codes": ["cardboard"], "teams": 2, "link": 25}, quiet=True)
    assert r.plan.params["workers"] == 4 and len(r.plan.teams) == 2
