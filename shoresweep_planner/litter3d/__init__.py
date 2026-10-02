"""litter3d (ShoreSweep Planner, hsr1m 판) — 드론 영상 파이프라인 결과(쓰레기 위치 + 3D 부피 → 무게) → 작업자용 수거 계획.

모듈 구성
  classes         쓰레기 클래스, 겉보기 밀도표, 개당 평균무게표 (출처·가정값 표기)
  plan            마대·톤백·트럭 적재량, NIOSH 23 kg
  terrain         정사영상(파이프라인 모자이크·업체 정사영상) 색 → 물·숲·맨땅 격자 → 최단경로 (걷기 환산 거리, 보트 모드)
  pipeline_io     파이프라인 출력(objects.csv · objects3d.csv · objvol.json · summary.json · items.csv/stops.csv) 과 업체 GeoJSON 읽기
  collect         무게 추정(3D 부피 × 겉보기 밀도 / 2D 면적 / 대체값) → 구역 묶기 → 순회 최적화 → 운반 방식 → 일차 분할
  collect_report  인터랙티브 HTML(브라우저 안에서 재계산, 오프라인 Leaflet 내장) + 인쇄용 PNG 지도
  site            input/ 에 현장 폴더가 여러 개일 때 목록 index.html
"""
__version__ = "0.3.0"
