"""
태양 위치·일출/일몰 — NOAA 근사식 (외부 의존성 없음).

쓰는 곳:
  - airspace.py : 비행 시각이 야간(일몰 후~일출 전)인지 → 특별비행승인 대상 여부
  - objvol.py   : 촬영 시각의 태양 고도로 물체 그림자 길이(= 높이 / tan 고도) 예상 → 발자국 과대 설명

  >>> from litter.solar import solar_position, sun_times, local_to_utc
  >>> t = local_to_utc("2026-10-01 15:15:09", tz_hours=9)
  >>> elev, az = solar_position(t, 37.3843, 126.6571)      # 도, 방위각은 북 0° 시계방향

정확도: 고도·방위 ±0.1° 수준 (대기 굴절 미보정). 야간 판정·그림자 길이에는 충분.
"""
import math
from datetime import datetime, timedelta, timezone


def local_to_utc(dt_str, tz_hours=9.0):
    """'2026-10-01 15:15:09[.123]' (SRT의 현지 시각) → UNIX 초(UTC). 기본 KST(+9)."""
    s = str(dt_str).strip().replace("T", " ").replace(",", ".").replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"시각 형식을 모름: {dt_str!r} (예: 2026-10-02 10:00)")
    return d.replace(tzinfo=timezone(timedelta(hours=tz_hours))).timestamp()


def _params(ts_utc):
    """율리우스 세기 T → (이심률 e, 평균근점이각 M°, 평균황경 L0°, 적위 δ°, 균시차 EoT 분)."""
    jd = ts_utc / 86400.0 + 2440587.5
    T = (jd - 2451545.0) / 36525.0
    L0 = (280.46646 + T * (36000.76983 + 0.0003032 * T)) % 360
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    Mr = math.radians(M)
    C = ((1.914602 - T * (0.004817 + 0.000014 * T)) * math.sin(Mr)
         + (0.019993 - 0.000101 * T) * math.sin(2 * Mr) + 0.000289 * math.sin(3 * Mr))
    omega = math.radians(125.04 - 1934.136 * T)
    lam = math.radians(L0 + C - 0.00569 - 0.00478 * math.sin(omega))
    eps0 = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60
    eps = math.radians(eps0 + 0.00256 * math.cos(omega))
    decl = math.degrees(math.asin(math.sin(eps) * math.sin(lam)))
    y = math.tan(eps / 2) ** 2
    L0r = math.radians(L0)
    eot = 4 * math.degrees(y * math.sin(2 * L0r) - 2 * e * math.sin(Mr) + 4 * e * y * math.sin(Mr) * math.cos(2 * L0r)
                           - 0.5 * y * y * math.sin(4 * L0r) - 1.25 * e * e * math.sin(2 * Mr))
    return e, M, L0, decl, eot


def solar_position(ts_utc, lat, lon):
    """(고도각°, 방위각° 북0 시계방향). 고도각 < -0.833이면 태양이 지평선 아래(야간)."""
    _, _, _, decl, eot = _params(ts_utc)
    minutes = (ts_utc % 86400) / 60.0
    tst = (minutes + eot + 4 * lon) % 1440
    ha = tst / 4 - 180
    if ha < -180:
        ha += 360
    latr, decr, har = math.radians(lat), math.radians(decl), math.radians(ha)
    cos_z = math.sin(latr) * math.sin(decr) + math.cos(latr) * math.cos(decr) * math.cos(har)
    zen = math.acos(max(-1.0, min(1.0, cos_z)))
    elev = 90 - math.degrees(zen)
    if math.sin(zen) < 1e-9:
        return elev, 180.0
    c = (math.sin(latr) * math.cos(zen) - math.sin(decr)) / (math.cos(latr) * math.sin(zen))
    a = math.degrees(math.acos(max(-1.0, min(1.0, c))))
    az = (a + 180) % 360 if ha > 0 else (540 - a) % 360
    return elev, az


def sun_times(date_ts_utc, lat, lon, zenith=90.833):
    """해당 날짜의 일출·일몰 UNIX 초(UTC). zenith 96 = 시민박명. 극야/백야면 (None, None)."""
    day0 = math.floor(date_ts_utc / 86400) * 86400
    _, _, _, decl, eot = _params(day0 + 43200)
    latr, decr = math.radians(lat), math.radians(decl)
    c = math.cos(math.radians(zenith)) / (math.cos(latr) * math.cos(decr)) - math.tan(latr) * math.tan(decr)
    if c < -1 or c > 1:
        return None, None
    ha0 = math.degrees(math.acos(c))
    rise = 720 - 4 * (lon + ha0) - eot   # 분, UTC
    sett = 720 - 4 * (lon - ha0) - eot
    return day0 + rise * 60, day0 + sett * 60


def is_night(ts_utc, lat, lon):
    """항공안전법의 '야간' = 일몰 후 ~ 일출 전. 태양 고도 −0.833° 기준."""
    return solar_position(ts_utc, lat, lon)[0] < -0.833


def shadow_length(height_m, elev_deg):
    """높이 h 물체의 그림자 길이. 태양 고도 3° 미만이면 None (무한대에 가까움)."""
    if elev_deg is None or elev_deg < 3:
        return None
    return height_m / math.tan(math.radians(elev_deg))


def fmt_local(ts_utc, tz_hours=9.0):
    return datetime.fromtimestamp(ts_utc, timezone(timedelta(hours=tz_hours))).strftime("%Y-%m-%d %H:%M")
