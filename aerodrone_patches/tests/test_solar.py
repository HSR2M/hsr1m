import sys; import os; sys.path.insert(0, os.environ.get("LITTER_REPO", "."))
from litter.solar import *
lat, lon = 37.3843, 126.6571   # 송도
for s in ["2026-10-01 12:22:00", "2026-10-01 15:15:09", "2026-10-01 18:00:00", "2026-10-01 18:30:00", "2026-10-01 20:54:04"]:
    t = local_to_utc(s, 9)
    e, a = solar_position(t, lat, lon)
    print(s, f"elev {e:6.2f}  az {a:6.1f}  night={is_night(t, lat, lon)}  shadow(12cm)={shadow_length(0.12, e)}")
r, st = sun_times(local_to_utc("2026-10-01 12:00:00", 9), lat, lon)
print("sunrise", fmt_local(r), "sunset", fmt_local(st))
r, st = sun_times(local_to_utc("2026-06-21 12:00:00", 9), lat, lon)
print("Jun21 sunrise", fmt_local(r), "sunset", fmt_local(st))
# 적도/남반구 샘플
e, a = solar_position(local_to_utc("2026-10-01 12:00:00", 0), 0.0, 0.0); print("equator noon", round(e,1), round(a,1))
