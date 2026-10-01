"""실측 자료 내려받기 도우미 (인터넷이 되는 PC에서 실행).

사용 예
  python -m incheon_debris_sim.fetch_data basemap            # 위성 배경지도 (Esri World Imagery)
  python -m incheon_debris_sim.fetch_data basemap --source eox   # Sentinel-2 cloudless (EOX)
  python -m incheon_debris_sim.fetch_data cmems              # Copernicus Marine 표층 해류 (계정 필요)
  python -m incheon_debris_sim.fetch_data hycom              # HYCOM GOFS 3.1 표층 해류 (계정 불필요)

받은 해류 NetCDF 는  python -m incheon_debris_sim.simulate data/currents.nc  로 바로 사용할 수 있다.
"""
import os
import sys
import argparse
import datetime as dt

from . import config as C


def fetch_basemap(source="esri", zoom=12):
    from .basemap import fetch_satellite_basemap
    fetch_satellite_basemap(source=source, zoom=zoom)


def fetch_cmems(start, end, out):
    """Copernicus Marine Toolbox 사용 (pip install copernicusmarine, 무료 계정 등록 후 `copernicusmarine login`).
    자료: GLOBAL_ANALYSISFORECAST_PHY_001_024, 1/12°, 시간별 표층 해류(조석 포함) 'cmems_mod_glo_phy_anfc_0.083deg_PT1H-m'
    """
    import copernicusmarine
    copernicusmarine.subset(
        dataset_id="cmems_mod_glo_phy_anfc_0.083deg_PT1H-m",
        variables=["uo", "vo"],
        minimum_longitude=C.LON_MIN - 0.2, maximum_longitude=C.LON_MAX + 0.2,
        minimum_latitude=C.LAT_MIN - 0.2, maximum_latitude=C.LAT_MAX + 0.2,
        start_datetime=start, end_datetime=end,
        minimum_depth=0, maximum_depth=1,
        output_filename=out,
    )
    print("saved", out, " → var_map: uo/vo/latitude/longitude/time (ExternalCurrents 기본값)")


def fetch_hycom(start, end, out):
    """HYCOM GOFS 3.1 (GLBy0.08) NCSS 요청. 3시간 간격, 1/12°. 계정 불필요."""
    import requests
    url = ("https://ncss.hycom.org/thredds/ncss/GLBy0.08/expt_93.0/FMRC/GLBy0.08_930_FMRC_best.ncd"
           f"?var=water_u&var=water_v&north={C.LAT_MAX + 0.2}&west={C.LON_MIN - 0.2}&east={C.LON_MAX + 0.2}&south={C.LAT_MIN - 0.2}"
           f"&horizStride=1&time_start={start}&time_end={end}&timeStride=1&vertCoord=0&accept=netcdf4")
    r = requests.get(url, timeout=600)
    r.raise_for_status()
    with open(out, "wb") as f:
        f.write(r.content)
    print("saved", out, " → var_map: {'u':'water_u','v':'water_v','lat':'lat','lon':'lon','time':'time'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["basemap", "cmems", "hycom"])
    ap.add_argument("--source", default="esri")
    ap.add_argument("--zoom", type=int, default=12)
    ap.add_argument("--start", default=(dt.date.today() - dt.timedelta(days=40)).isoformat() + "T00:00:00")
    ap.add_argument("--end", default=(dt.date.today() - dt.timedelta(days=10)).isoformat() + "T00:00:00")
    ap.add_argument("--out", default=os.path.join(C.DATA_DIR, "currents.nc"))
    a = ap.parse_args()
    if a.what == "basemap":
        fetch_basemap(a.source, a.zoom)
    elif a.what == "cmems":
        fetch_cmems(a.start, a.end, a.out)
    else:
        fetch_hycom(a.start, a.end, a.out)


if __name__ == "__main__":
    main()
