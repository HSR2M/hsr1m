# input/ — 파이프라인 결과를 여기에 넣으면 됩니다

`coastal litter pipeline`(aerodrone_hackathon `litter` 패키지) 이 만든 **쓰레기 위치 + 3D 부피** 파일을 넣고
`python run.py` 를 실행하면 `outputs/plan/수거계획.html` 이 생깁니다.

```
input/
  config.json                 현장 이름 · 출발지 · 좌표계 · 정답 크기 (config.example.json 복사해서 수정)
  ── 아래 중 하나 이상 (있는 것을 자동으로 알아봄; config "format" 으로 고정 가능) ──
  objects3d.csv               batch3d 결과 (runs/orbit/<영상>_all/)  ← 위치·크기·부피·신뢰도. 가장 좋음
  plan.json / objects.csv     (선택) 같은 폴더의 상자 목록 / video_map·orbit_map 탐지 (종류 보강)
  objvol.json (+ *_masks.jpg)  objvol v2 결과 (runs/orbit/<영상>/objvol_v2/) — 위경도가 없으면 옆에 objects.csv
  summary.json                fromvideo run 결과 (runs/plan/<영상>/) — 무게까지 들어 있음
  items.csv (+ stops.csv)     litter run 결과 (report.write_tables)
  objects.csv                 탐지 위치만 (video_map / orbit_map) — 크기 정보가 없어 개수 × 평균무게로 추정
  labels.json                 업체 GeoJSON 라벨 (문갑도 형식)
  ── 선택 ──
  photos/01.jpg …             물체 사진 (번호 순). config "photo_pattern" 로 이름 규칙 지정
  masks/01.jpg …              3D 마스크 그림 (objvol *_masks.jpg)
  ortho/mosaic.jpg + .jgw + .prj   정사영상 (파이프라인 mosaic.tif 를 jpg + 월드파일로; 또는 GeoTIFF 그대로)
                              → 드론 영상 오버레이 + 물·숲·맨땅 지형 최단경로가 켜짐
```

저장소에서 바로 가져오려면 (영상 번호만 주면 위 파일을 찾아 복사하고 config.json 을 만든다):

```
python tools/import_pipeline.py --repo ../aerodrone_hackathon --video 0015 --truth 42x32x39
python run.py
```

여러 현장(영상) 을 한 번에 만들려면 `input/` 안에 현장별 폴더를 두면 된다 (`input/0015/`, `input/0021/` …).
`run.py` 가 폴더마다 수거계획.html 을 만들고 목록 페이지 `outputs/site/index.html` 을 함께 만든다.

## config.json 항목

| 키 | 뜻 | 기본 |
|---|---|---|
| `site` | 현장 이름 (제목) | 폴더 이름 |
| `crs` | 거리 계산용 투영 좌표계 | EPSG:5186 (남한). 정사영상 .prj 가 있으면 그것 |
| `depot` | `{"lon","lat","name"}` 출발·집결지 | 없으면 쓰레기 무게중심 |
| `format` | objects3d / objvol / summary / stops / objects / geojson | 자동 판별 |
| `default_class` | objects3d 에서 종류를 모를 때 | cardboard |
| `class_map` | 탐지 클래스명 → 우리 클래스 바꾸기 `{"Styrofoam_Buoy": "cardboard"}` | — |
| `material` | objvol 태그별 재질 `{"Plastic_Buoy_55": "cardboard"}` | 태그 이름으로 추정 |
| `truth` | 정답 크기 `{"default_cm": "42x32x39"}` 또는 `{"by_id": {"19": "42x32x39"}}` | — |
| `photo_pattern`, `mask_pattern` | 사진 파일 이름 규칙 (`{seq:02d}`, `{id}`) | photos/{seq:02d}.jpg |
| `ortho` | 정사영상 경로 | ortho/ 안에서 자동 |
| `defaults` | `{"workers","hours","link","walk","detour","teams"}` 초기 설정 | 2명·4시간·150 m·3 km/h·×1.4 |
| `zone_word` | 구역 이름 뒤 단어 ("북쪽 구역 ①") | 해안 |
| `shared` | 인터넷 공유(Supabase) 설정 — README 참고 | 없음 |

예시 입력은 `examples/school_0015` (야간 비행 상자 30개, objects3d 형식) 과 `examples/school_orbit` (선회 시험, objvol 형식 + 정사영상) 에 있다.
