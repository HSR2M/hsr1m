# aerodrone_hackathon `litter/` 패치 — 평가에서 나온 지적을 코드로 옮긴 것 (2026-10-01)

기준 코드: 브랜치 `feature/coastal-litter-pipeline`, 커밋 `1c3cd3ee` (업로드한 ALL_CODE_IN_ONE.txt).
원칙: **기존에 발표용으로 뽑아 둔 숫자는 하나도 바뀌지 않는다.** 모든 변경은 새 필드·새 옵션·경고 출력 추가다.
기본값으로 다시 돌려도 `objvol.json`·`summary.json`의 기존 키 값은 그대로이고 옆에 새 키가 붙는다.

## 적용 방법

```powershell
cd C:\Users\user\Desktop\드론\aerodrone_hackathon
git apply --check litter_changes.patch   # 충돌 없으면
git apply litter_changes.patch
# 또는 files\litter\*.py, files\docs\airspace\ 를 그대로 덮어쓰기 (새 파일: litter/solar.py, litter/airspace.py)
```
새 외부 의존성 없음 (solar는 순수 수식, airspace는 numpy만).

## 무엇이 바뀌었나 (발표 기준과 연결)

### 1. 업체 `weight_kg` 단위 점검 — `fromvideo.py`  ← 가장 먼저
- `check_company_units(labels)`: 라벨마다 `weight_kg ÷ area_sqm`(= 계수)를 재질별로 구해 **0.1 kg/m² 미만이면 "톤 단위 또는 자리 오류 가능성"** 경고.
  업체 계수 0.012·0.024·0.020을 ×1000 하면 12·24·20 kg/m² → 두께 10~40 cm 더미의 현실적인 면밀도와 같은 자릿수.
- `compare` 명령이 자동으로 점검을 돌리고, 의심되면 **톤으로 읽은 그림(`fig_compare_company_labels_as_tonnes.png`)도 같이** 만든다.
- `--company-unit kg|t` (run·compare 공통): 업체 방식 무게를 어느 단위로 계산할지. summary.json에 `company_unit` 기록.
- 발표 연결: 업체 확인 전까지 "1/112·1/180" 숫자는 보류하고 "면적만으론 두께를 모른다" 프레임으로.

```powershell
python -m litter.fromvideo compare --objvol runs/orbit/0007/objvol_v2/objvol.json --material "Plastic_Buoy_55:Styrofoam,Styrofoam_Buoy_22:Styrofoam" --labels data/company/MGD_labels.json --out runs/plan/compare
#   [단위 점검] ⚠️ ... 톤으로 읽으면 합계 1,319 kg ...   ← 이 줄과 (b′) 그림을 확인
```

### 2. 비행 전/후 규정 점검 — `airspace.py`(신규) + `solar.py`(신규) + `python -m litter preflight`
항공교통 교수 질문 대비. SRT(사후) 또는 계획 경로점(사전)으로:
- **야간**: 일몰 후~일출 전이면 "승인필요" (NOAA 태양 위치식, 인천 10-01 일출 06:28·일몰 18:17 — 실제와 1분 이내)
- **고도**: 상대고도 150 m 초과 → "승인필요" (SRT 상대고도는 이륙점 기준 기압고도라는 주석 포함)
- **공역**: GeoJSON 구역(폴리곤 또는 Point+radius_m 원) 진입 여부·가장 가까운 경계 거리
- **가시권**: 이륙점에서 최대 수평거리 (참고값)
- **사람**: objects.csv 의 obstacle(person 등) 있으면 "사람 위 비행 금지" 주의
- 결과 `preflight.md`·`preflight.json`. 슬라이드 한 장("공역 확인 → 비행 → 분석")의 근거.

```powershell
python -m litter preflight --srt ..\DJI_20261001151509_0007_D.SRT --objects runs\map\0007_sfm\objects.csv --out runs\preflight\0007
python -m litter preflight --srt ..\DJI_20261001205404_0015_D.SRT --out runs\preflight\0015     # → [승인필요] 야간
python -m litter preflight --points "37.2,126.1;37.21,126.11" --time "2026-10-02 10:00" --alt 30 --out runs\preflight\plan
```
⚠️ 내장 구역은 **예시**(인천·김포 관제권 9.3 km 원, `docs/airspace/zones_sample.geojson`). 드론원스탑 공식 데이터로 바꿔서 `--zones` 로 넘길 것.
문갑도(옹진군)는 서해 접경 공역 확인이 특히 필요.

### 3. 축척 교차검증 — `volume.py` `to_metric_auto(..., scale=)`, `objvol.py`·`orbit_map.py` `--scale auto|alt|gps`
- GPS 이동이 3 m 이상이면 선택과 무관하게 **GPS 경로 배율을 계산해 `gps_scale_factor_check`로 기록**하고,
  SRT 고도 기준과 25 % 이상 다르면 `scale_warning` 출력 ("SRT 상대고도가 지면고도와 다를 수 있음 → --scale gps").
- 0010(고도 3.7 m 기록, 실제 2 m)·0015(고도 1/5 기록)처럼 사람이 눈치채야 했던 것을 코드가 먼저 알려준다.
- 발표 연결: "기압 상대고도 vs AGL" 이야기의 코드 근거.

### 4. 조밀 복원 경계 번짐 보정 — `volume.volume_heightmap(erode_m=)`, `objvol.py` `--edge-erode-px`(기본 1.0)
- 0007 상자 가로·세로가 1~2 cm씩 크게 나온 원인(MVS 패치 창 번짐 ≈ 1 px)에 맞춰, 물체 위치 GSD × px 만큼 발자국을 안쪽으로 줄인 부피를 **새 키 `volume_heightmap_eroded_L`**로 추가. `gsd_obj_cm`, `edge_erode_m`, `footprint_eroded_m2` 함께 기록. 기존 `volume_heightmap_L`은 그대로.
- 합성 상자(60×45×12, 가장자리 1.2 cm 번짐)에서 보정 0 → +8 %, 1 cm → 0 %.
- 실데이터는 다시 돌려 봐야 함(0007 큰 상자 발자국 0.304 m² → 보정 후 약 0.28 m² 예상). 발표에 쓰려면 "보정 추정치"로 표기하고 기존 값과 나란히.
- `fromvideo --vol_key volume_heightmap_eroded_L` 로 작업카드에 반영 가능.

### 5. 태양 고도·그림자 길이 기록 — `objvol.py`
- SRT 시각(`telemetry.read_srt`가 `dt_str` 원문을 보존)과 GPS로 촬영 시각 태양 고도·방위를 계산해 `sun_elev_deg`·`sun_az_deg`·`shadow_len_m`(= 높이 / tan 고도)·`capture_local` 기록.
- 0007(15:15, 고도 33°)에서 12 cm 상자 그림자 ≈ 18 cm. "SAM 마스크에 그림자가 섞이면 발자국이 얼마나 커지나" 질문의 수치 답.
- 야간 영상이면 콘솔에 ⚠️ 일몰 후 표시.

### 6. 부피 신뢰 플래그 보강 — `batch3d._confidence`
0015 결과로 재검증: "높음"이었던 #6(−61 %)·#19(+73 %)·#9(+35 %)가 각각 **낮음(마스크/높이지도 4.1배)·중간·중간(희소점 1,077)**으로 내려가고, 0007 선회 두 상자는 높음 유지.
추가 기준: 마스크×높이 부피와 높이지도 부피 비율 [0.6, 1.6] 밖 → 낮음 · SfM 등록률 < 50 % 또는 희소점 < 2,000 → 중간 상한 · 높음은 점 ≥ 600·뷰 ≥ 10.
GPS 잔차는 **축척을 GPS에서 가져왔을 때만** 본다(0007은 고도 축척이라 잔차 1.16 m가 부피와 무관).

### 7. 시뮬 운용 지표 — `sim_ortho.py`
- `summary.json["mission"]`: 전후 겹침률(= 1 − 속도×간격/세로 발자국; 기본 설정 78 %), 횡 겹침, 배터리 사용률, 소티 수(`--endurance 1500`, `--reserve 0.25`), 평균 지상속도.
- `summary.json["airspace"]`: 영역 네 꼭짓점으로 공역·야간(`--mission-time`)·고도 점검을 계획 단계에서 실행해 콘솔에 출력.

### 8. SRT 자세 사용 — `video_map.py --srt-attitude`
Mini 4 Pro 이후 펌웨어처럼 SRT에 `gb_yaw`/`gb_pitch`가 있으면 이동방향 추정 대신 그 값을 쓴다. 0015 SRT에 있는지 먼저 확인(`[gb_yaw:` 검색).

## 검증한 것 / 못 한 것
- 검증: 모든 모듈 `py_compile` 통과. 합성 데이터로 solar(일출·일몰 실제값 대비 1분 이내), airspace(야간·150 m·구역 진입·사람 경고), volume(번짐 보정, 축척 auto/alt/gps + 경고, 이동 3 m 미만 폴백), batch3d 플래그(0015 CSV 11행 재생), fromvideo 단위 점검(계수 0.012 재현 → 경고, 정상 계수 → 통과), sim 지표.
- 못 한 것: pycolmap·SAM·ultralytics가 필요한 `objvol`·`orbit_map`·`sim_ortho` 실행 자체. 노트북에서 0007로 한 번 돌려 `volume_heightmap_eroded_L`·`sun_elev_deg`·`gps_scale_factor_check`가 찍히는지 확인할 것 (`--device cpu`로도 됨).

## 코드로 안 되는 것 (사람이 할 일)
1. 업체에 `weight_kg` 단위 확인 (전화 한 통). 확인 전에는 "1/100" 숫자 발표 보류.
2. 0015 야간·0010 골목 비행의 승인 여부 확인. 없으면 발표에서 제외.
3. `zones_sample.geojson`을 드론원스탑 공식 공역으로 교체.
4. 상자 저울 실측 → `--truth` 기준값 교체, 무대 시연.
5. 팀원 대시보드에 3D 결과 연결.
