# ShoreSweep Planner (hsr1m) — 드론 영상 파이프라인 결과 → 쓰레기 수거 계획 사이트

학교 곳곳에 쓰레기(상자)를 두고 드론으로 촬영한 영상을 **coastal litter pipeline**(aerodrone_hackathon `litter` 패키지)
이 처리하면 쓰레기의 **위치**와 **3D 부피**가 나온다. 이 프로그램은 그 결과를 `input/` 에 넣으면
부피 × 종류별 겉보기 밀도로 **무게**를 추정하고, **작업자용 수거 계획**(구역·순서·마대·시간·인원·일정)을 한 장짜리 웹 페이지로 만든다.
결과 HTML 은 그 자체가 계산기라서 인원·시간·종류·이동 방식·출발지를 바꾸면 브라우저 안에서 즉시 다시 계산된다.

팀 저장소 `feature/shoresweep-planner` 의 ShoreSweep Planner(업체 2D 라벨용) 형식을 그대로 따르되, 입력을 파이프라인 결과(3D) 로 바꾼 판이다.

```
드론 영상 + SRT ─▶ ① 탐지 ─▶ ② 3D 복원 ─▶ ③ 위치 ─▶ ④ 부피(SAM 2 투표 + 높이지도) ─▶ ⑤ 무게 ─▶ ⑥ 수거계획 (이 프로그램)
                                        objects.csv            objects3d.csv / objvol.json
→ 무게 추정 (3D 부피 × 겉보기 밀도, 측정 신뢰도별 범위; 측정 실패는 같은 종류 중앙값 대체; 면적만 있으면 2D 식)
→ (정사영상이 있으면) 색으로 물·숲·맨땅 10 m 격자 → 물체·출발지 사이 최단경로 (물 불가, 숲 ×3, 보트 모드 물 ×0.5)
→ 걷기 거리 link_m 안 물체를 한 구역으로 → 구역 순회 (최단 이동 / 무게 우선)
→ 구역별 마대·작업 시간·2인 운반 표시 → 운반 방식 (현장 적치 / 들고 이동) → 하루 작업시간으로 일차 분할
→ 수거계획.html (인터랙티브, 오프라인 가능) · 수거계획_지도.png (인쇄) · 수거계획.xlsx · csv · plan.json
```

## 빠른 시작 (Windows, VS Code)

```bat
cd shoresweep_planner
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python run.py --example       :: 샘플(학교 야간 비행 상자 30개 · 선회 시험) 로 먼저 보기 → outputs/examples/index.html 자동 열림
pytest tests -q               :: 테스트 (18개)
```

Linux/macOS 는 `python3 -m venv .venv && . .venv/bin/activate` 만 다르다.

## 학교 데이터를 받으면

1. 파이프라인 결과 파일을 `input/` 에 넣는다 (아래 표, 자세한 건 [input/README.md](input/README.md)).
   저장소 안에 있으면 영상 번호만으로 가져올 수 있다:
   ```bat
   python tools\import_pipeline.py --repo ..\..\aerodrone_hackathon --video 0021 --truth 42x32x39 --name "학교 캠퍼스"
   ```
2. `input/config.json` 에서 현장 이름·출발지(집결지)·정답 크기를 확인한다 (`input/config.example.json` 참고).
3. `python run.py` → `outputs/plan/수거계획.html` 이 브라우저로 열린다.
4. 현장에서 여러 사람이 같이 쓰려면 `python run.py --serve` (같은 와이파이의 휴대폰에서 접속, 완료 체크·출발지가 모두에게 공유).

| `input/` 에 넣는 파일 | 어디서 나오나 | 무게 근거 |
|---|---|---|
| **`objects3d.csv`** (+ `plan.json`, `objects.csv`) | `litter.batch3d` → `runs/orbit/<영상>_all/` | **3D 부피 × 겉보기 밀도** (가장 좋음) |
| `objvol.json` (+ `objects.csv`, `*_masks.jpg`) | `litter.objvol` → `runs/orbit/<영상>/objvol_v2/` | 3D 부피 |
| `summary.json` | `litter.fromvideo run` → `runs/plan/<영상>/` | 파이프라인 무게 그대로 |
| `items.csv` (+ `stops.csv`) | `litter run` / `report.write_tables` | 3D 또는 2D |
| `objects.csv` 만 | `litter.video_map` / `orbit_map` → `runs/map/<영상>/` | 개수 × 평균무게 (크기 없음) |
| `labels.json` | 업체 GeoJSON 라벨 | 면적 × 채움률 × 두께 × 밀도 (2D) |
| 선택: `photos/`, `masks/`, `ortho/mosaic.jpg + .jgw + .prj` | 사진 시트, `*_masks.jpg`, `litter.mosaic` 의 `mosaic.tif` | 사진 카드 · 정사영상 오버레이 + 지형 경로 |

영상이 여러 개면 `input/0015/`, `input/0021/` 처럼 폴더를 나눠 넣는다. `run.py` 가 폴더마다 페이지를 만들고 목록 `outputs/site/index.html` 을 함께 만든다.

옵션이 필요하면 (한 현장):
```bat
python scripts\17_collection_plan.py --workers 4 --hours 3 --teams 2 --objective weight
python scripts\17_collection_plan.py --input examples\school_0015 --out outputs\test --codes cardboard --calib cardboard=0.8
python scripts\17_collection_plan.py --help
```

## 폴더 구조

```
run.py                        실행 (VS Code ▶). input/ → outputs/plan/ ; --example ; --serve
serve.py                      로컬 서버 (표준 라이브러리) — 같은 와이파이에서 접속·진행 공유 (/api/state, /api/positions)
input/                        파이프라인 결과를 넣는 곳 — input/README.md, config.example.json
examples/                     샘플 입력 2개 (학교 야간 비행 상자 30개 objects3d 형식 · 선회 시험 objvol 형식 + 정사영상)
litter3d/
  classes.py                  쓰레기 클래스 17종 + 골판지 상자, 겉보기 밀도표 (출처/가정값 표시), 파이프라인 클래스명 매핑
  plan.py                     마대·톤백·트럭 적재량, NIOSH 23 kg
  terrain.py                  정사영상 색 → 물·숲·맨땅 격자 → 8방향 최단경로 (걷기 환산 거리, 보트 모드)
  pipeline_io.py              파이프라인 출력 읽기 (objects3d.csv · objvol.json · summary.json · items.csv · objects.csv) + 사진 시트 자르기
  collect.py                  무게 추정(3D/대체/2D/개수) → 구역 → 순회 최적화 → 운반 방식 → 일차 분할 → xlsx/csv/json
  collect_report.py           인터랙티브 HTML (브라우저 안 다익스트라·재계산, ★ 출발지 끌기) + 인쇄용 PNG
  build.py                    input 폴더 → 산출물 한 벌 (run.py · 스크립트가 공통으로 씀)
  site.py                     현장이 여러 개일 때 목록 index.html
  assets/app.js · app.css     브라우저 앱 (파이썬과 같은 규칙) · leaflet.js/css (BSD, HTML 에 내장 → 인터넷 없이 지도 동작)
scripts/17_collection_plan.py 명령줄 버전
tools/import_pipeline.py      저장소에서 영상 번호로 결과 가져오기 → input/
tools/supabase_setup.sql      인터넷 공유용 테이블 (선택)
tests/                        pytest (가상 데이터 + examples)
outputs/                      결과 (git 제외)
```

## 결과 파일 (outputs/plan)

| 파일 | 내용 |
|---|---|
| 수거계획.html | 지도(위성 + 드론 정사영상 + 경로 + 번호) · 설정 패널 · 작업 순서 카드(사진) · 3D 측정 vs 정답 표 · 준비물 · 종류별 표. 조건을 바꾸면 즉시 재계산. Leaflet 내장이라 파일로 열어도 동작 (위성 타일만 인터넷 필요) |
| 수거계획_공개용.html | 같은 페이지의 인터넷 링크(claude.ai 아티팩트 등) 용 변형. 외부 지도 타일 대신 드론 영상만, 인쇄·내려받기 없음 |
| 수거계획_지도.png | 인쇄용 지도 (기본 설정 기준) |
| 수거계획.xlsx · zones.csv · objects.csv · plan.json · summary.md | 표·데이터 (기본 설정 기준). objects.csv 에 무게 근거·부피 범위·정답·신뢰도 열 포함 |
| 지형분류.png | 정사영상이 있을 때 물(파랑)·숲(초록)·맨땅(흰색) 격자 확인용 |

## 무게는 어떻게 나오나

| 근거 (`basis`) | 언제 | 식 |
|---|---|---|
| 3D 부피 측정 | objects3d.csv 의 `부피 OK`, objvol 의 `volume_heightmap_L` | 부피 × ρ(min/typ/max). 신뢰도 높음 ×0.8–1.25, 중간 ×0.6–1.5, 낮음 ×0.5–2 로 부피 범위 (가정값) |
| 같은 종류 측정값 대체 | 부피 실패 (바닥 평면 틀어짐·마스크 없음·점 부족) | 같은 종류의 신뢰 높음·중간 측정 부피 중앙값 (없으면 종류별 기본 부피) × ρ, 범위 ×0.5–2 |
| 면적 기반 (2D) | 업체 라벨, 정사영상 탐지 | 면적 × 채움률 × 두께(min/typ/max) × ρ |
| 개수 × 평균무게 | objects.csv 만 있을 때 | Andriolo 2024 종류별 평균무게 |
| 업체 방식 (비교용) | 항상 같이 계산 | 면적 × 고정계수 (스티로폼 0.012, 로프·어구 0.024, 플라스틱 0.020 kg/m²) — 실측이 아님을 보여 주기 위한 참고값 |

- **출처 있음**: EPS 밀도 11–32 kg/m³, 개당 평균무게 (Andriolo et al. 2024), NIOSH 23 kg.
- **가정값**: 골판지 상자·속 빈 플라스틱·로프·그물의 겉보기 밀도, 부피 신뢰도별 범위, 2D 채움률·두께, 걷기 속도, 작업 시간, 마대·운반 적재량, 숲·보트 통행 배수.
  코드와 HTML 하단에 "가정값" 으로 적혀 있고, 현장에서 마대를 저울로 재면 "실측 보정" 으로 종류별 계수가 바뀐다.
- 샘플(학교 야간 비행 상자 30개, 정답 42×32×39 cm = 52.4 L): 3D 측정 10개 부피 합 740 L vs 정답 524 L (+41 %; 바닥 평면이 기운 상자 1개가 283 L 로 크게 튐),
  선회 시험 상자 3개는 +18 / +20 / −10 %. 측정 실패 20개는 중앙값 43.6 L 로 대체 (정답 −17 %).
- 결과는 검출 누락을 반영하지 않은 **최소 추정치**다.

## 현장에서 쓰는 기능 (수거계획.html)

| 기능 | 어떻게 쓰나 | 동작 |
|---|---|---|
| 구역 상세 패널 | 지도의 구역 번호나 작업 순서 카드를 누름 | 그 구역의 물체 목록: 사진·3D 마스크·종류·크기(cm)·부피(L)·정답·무게(범위)·근거·신뢰도·2인 표시, 물체별 완료 체크, 길찾기 |
| 진행 체크 | "완료 ✓", 물체 체크박스, 점 팝업 | 완료를 빼고 남은 구역만으로 경로·시간·마대 재계산. 브라우저에 저장 |
| 내 위치 | "📍 내 위치" | GPS 로 현재 위치와 가장 가까운 남은 구역·거리·시간 (HTTPS 또는 localhost 필요) |
| 여러 팀 | 설정 "팀 수" | 순회를 시간 균형으로 나눠 팀별 경로(색)·시간·일차 |
| 실측 보정 | "실측 보정" 카드 | 구역의 저울 무게 ÷ 예상 → 그 종류 보정 계수를 모든 구역에 적용 |
| 시나리오 비교 | 버튼 | 도보/보트, 인원 2배, 팀 2개, 들고 이동, 무게 우선, 최소/최대, ×0.5/×1.5 민감도 한 표 |
| 출발지 변경 | ★ 끌기 | 즉시 재계산 (정사영상이 있으면 땅·해안 근처만) |
| 공유 | `python run.py --serve` 또는 `python serve.py` | 같은 와이파이의 모든 접속자가 완료 체크·보정·출발지·작업자 위치를 같이 봄 (`/api/state/<현장>`) |

## 인터넷 페이지·연동으로 확장하기 (다음 단계)

- **지금**: 로컬에서 `run.py` → HTML. `serve.py` 로 같은 네트워크 공유. HTML 은 외부 자원 없이 동작 (위성 타일만 인터넷).
- **인터넷 페이지**: `outputs/plan/수거계획.html` 을 GitHub Pages 등에 올리면 그대로 열린다. 여러 사람 실시간 공유는 `input/config.json` 에
  `shared` (Supabase, [tools/supabase_setup.sql](tools/supabase_setup.sql)) 를 넣으면 `serve.py` 와 같은 형식(완료·보정·출발지·작업자 위치)으로 동기화된다.
  `수거계획_공개용.html` 은 claude.ai 아티팩트처럼 외부 타일이 막힌 곳용.
- **파이프라인 연동**: 입력 계약이 파이프라인 출력 파일 그대로이므로, 파이프라인 끝에 `python shoresweep_planner/run.py --input <결과 폴더> --no-open`
  한 줄을 붙이면 영상 처리 → 수거계획 페이지까지 자동이다. `serve.py` 의 `/api/sites` 로 만들어진 페이지 목록을 받을 수 있다.

## 참고

- 선행연구·방법 선택 근거·가정값 표는 팀 저장소 `feature/shoresweep-planner` 의 README 를 따른다 (Kako 2020, Andriolo 2024, NIOSH 등).
- Leaflet 1.9.4 (BSD 2-Clause) 를 `litter3d/assets/` 에 포함 (라이선스 파일 동봉).
