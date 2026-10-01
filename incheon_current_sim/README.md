# incheon_current_sim — 인천 앞바다 조류 흐름 시뮬레이션

인천·경기만 일대에서 조석에 따라 **창조류(밀물)와 낙조류(썰물)가 되풀이되는 모습**을
고도 자료로 만든 음영기복 지형 위에 입자 애니메이션으로 보여주는 단일 HTML 페이지다.
국립해양조사원 조류예보(시계열) 자료를 내장하면 실제 예보로 재생되고, 없으면 개념 모형으로 동작한다.

```
index.html        빌드된 결과. 브라우저에서 바로 열면 된다 (서버 불필요)
template.html     페이지 원본 (배경·마스크·자료 자리표시자 __RELIEF__ __MASK__ __KHOA__)
build_page.py     template + assets + data -> index.html
fetch_khoa.py     국립해양조사원 Open API 로 조류예보·조석예보를 받아 data/khoa_currents.json 저장
build_relief.py   Terrarium 고도 타일(줌 12) 다운로드·모자이크 -> E.npy
render_relief.py  E.npy -> assets/relief.jpg(음영기복 배경), assets/mask.json(육지 마스크 400x414)
assets/           relief.jpg, mask.json
data/             khoa_currents.json (수집 후 생성), raw/ (원본 응답, git 제외)
```

## 실제 조류예보 자료 넣기

1. [바다누리 해양정보 Open API](https://www.khoa.go.kr/oceangrid/khoa/intro.do)에서 발급받은 ServiceKey 를 준비한다.
   키는 저장소에 넣지 말고 명령줄 인자나 환경변수로만 쓴다.
2. 지점 목록을 먼저 확인한다.
   ```bash
   python fetch_khoa.py --key <ServiceKey> --list-only
   ```
3. 원하는 날짜부터 이틀치를 받아 빌드한다.
   ```bash
   python fetch_khoa.py --key <ServiceKey> --start 20261001 --days 2
   python build_page.py
   ```
   `fetch_khoa.py` 는 ObsServiceObj(지점 목록), fcTidalCurrent(조류예보 시계열), tideObsPreTab(조석예보 고저조, 인천 DT_0001)
   API 를 쓴다. API 필드명은 문서 개정으로 바뀔 수 있어 여러 후보 이름을 받아들이며, 응답 원본은 `data/raw/` 에 남긴다.
   **이 스크립트는 네트워크가 차단된 환경에서 작성되어 실제 API 응답으로 검증되지 않았다.** 지점이 0곳이면
   `data/raw/ObsServiceObj_.json` 을 열어 필드명(`obs_post_id`, `obs_lat`, `data_type` 등)을 확인하고 `pick()` 의 후보 이름을 보태면 된다.

### 자료 형식 (`data/khoa_currents.json`)

```json
{"fetched":"2026-10-01 23:00","dates":["20261001","20261002"],
 "stations":[{"id":"...","name":"인천항","lat":37.455,"lon":126.59,
              "series":[["2026-10-01T00:00:00+09:00", 85.3, 231], ...]}],
 "tide":{"station":"DT_0001","name":"인천","series":[["2026-10-01T03:06:00+09:00", 412.0], ...]}}
```
series 는 `[시각, 유속(cm/s), 유향(도, 흘러가는 방향, 북 기준 시계방향)]`, 조석은 `[시각, 조위(cm, 평균 기준)]` 이다.
다른 출처의 자료도 이 형식으로 만들면 그대로 쓸 수 있다.

## 화면 구성

- **해도**: Terrarium 고도 타일(SRTM 계열)로 만든 음영기복. 해안선과 섬(강화·교동·석모·영종·무의·장봉·영흥·대부·덕적·문갑·굴업·자월 등)은
  고도 자료에서 추출했고, 바다 음영은 실제 수심이 아니라 해안 거리로 만든 가상 수심이다. 위경도 0.2° 격자, 10 km 축척, 북쪽 표시.
- **입자**: 물 입자가 흘러가는 방향으로 움직이며 유속(0 ~ 1.2 m/s 이상)에 따라 5단계 밝기로 구분된다.
- **조석 패널**: 조위 곡선과 기준 지점 유속 곡선, 현재 위상(정조 → 창조류 → 정조 → 낙조류), 시각, 반복 횟수.
- **조작**: 재생/일시정지, 재생 속도(12시간 25분당 10~120초), 입자 수(500~10000), 자취 길이, 유향·유속 화살표 격자, 예보 지점 표시.
- **툴팁**: 바다 위에 마우스를 올리면 그 지점의 위경도, 유속(cm/s), 흘러가는 방향(16방위)이 나온다.

## 흐름 계산

- **실제 자료 모드**: 각 예보 지점의 유향·유속을 시각에 맞춰 선형 보간하고, 격자마다 역거리 제곱 가중으로 섞는다.
  해안 가까이에서는 유속을 줄이고, 육지에 닿은 입자는 바다에 다시 뿌린다. 자료 기간(기본 이틀)을 끝없이 반복한다.
- **개념 모형 모드**: M2 조석(12시간 25분)에 유속 ∝ sin(ωt), 조위 ∝ −cos(ωt)(경기만의 정상파 성격: 고조·저조 때 정조)를 두고,
  염하수로 1.7, 조강 1.3, 외해 접근 수로 1.1, 석모수로·영종 북쪽 0.9, 남쪽 수로 0.8, 배경 0.45 m/s 의 수로별 가중 유속장에
  한강 담수 유출 잔차류를 더한 것이다. 실측이 아니다.
- 입자 이동 거리는 보기 쉽게 과장되어 있다.

## 배경 다시 만들기

```bash
pip install numpy pillow scipy
python build_relief.py 1600      # 타일 다운로드 (s3.amazonaws.com/elevation-tiles-prod) 후 E.npy 생성
python render_relief.py          # assets/relief.jpg, assets/mask.json 생성
python build_page.py
```
