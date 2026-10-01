# island_drone_sim — 실제 섬 지형 위 드론 비행 시뮬레이션 (gym-pybullet-drones)

[learnsyslab/gym-pybullet-drones](https://github.com/learnsyslab/gym-pybullet-drones)의
Crazyflie 2.x 모델과 PID 제어기를 **실제 월미도·강화도 고도 데이터(DEM)** 위에서 비행시키는 최소 구현이다.
위성영상 텍스처는 없고(네트워크 정책으로 타일 서버 차단), 고도에 따른 색상으로 지형을 표현한다.

```
terrain.py        Terrarium 고도 타일 다운로드 -> numpy DEM -> PyBullet heightfield(충돌+시각) + 검증
island_aviary.py  CtrlAviary 서브클래스: plane.urdf 대신 heightfield를 지면으로 사용
fly_island.py     산 정상을 중심으로 선회 비행 + 로그/지도/영상 생성
```

## 설치

```bash
git clone https://github.com/learnsyslab/gym-pybullet-drones
python3.12 -m venv venv && . venv/bin/activate          # 저장소가 Python ^3.12를 요구
pip install -r requirements.txt
pip install --no-deps -e gym-pybullet-drones             # RL용 torch/SB3는 건너뜀
```

GPU나 디스플레이가 없어도 된다(PyBullet DIRECT 모드 + 소프트웨어 렌더러).

## 실행

```bash
cd island_drone_sim
python fly_island.py --island wolmido --agl 60 --radius 500  --speed 10 --video --video_fps 1
python fly_island.py --island ganghwa --agl 80 --radius 1500 --speed 10 --video --video_fps 0.5
python fly_island.py --island wolmido --gui        # PyBullet GUI로 직접 보기(로컬 PC)
```

| 인자 | 기본값 | 의미 |
|---|---|---|
| `--island` | wolmido | `terrain.ISLANDS` 프리셋 (wolmido: 3.8 m/px 2.9 km², ganghwa: 30 m/px 23 km²) |
| `--agl` | 60 | 지형 위 비행고도(m). 경로의 z는 평활화된 지형 + agl |
| `--radius` | 500 | 최고점 기준 선회 반경(m) |
| `--speed` | 10 | 순항속도(m/s). cf2x PID는 10 m/s까지 안정, 15 m/s는 뒤집힘 |
| `--max_err` | 1.5 | 드론과 목표점 사이 최대 거리(m). 이보다 멀면 PID가 과도하게 기울어 추락 |
| `--video` | off | 추적 카메라 프레임 저장 후 ffmpeg로 mp4 생성 (프레임당 약 0.7 s) |

출력은 `results/<island>_path.csv`, `results/<island>_map.png`, `results/<island>_flight.mp4`.

## 데이터

- 고도: AWS Open Data **Terrain Tiles** (Mapzen Terrarium PNG, 무료, 키 불필요).
  한국은 SRTM/ALOS 30 m급이 바탕이라 월미도 z15 타일(3.8 m/px)은 보간된 값이다.
  더 정밀한 자료가 필요하면 국토지리정보원 DEM(공개 90 m, 5 m는 신청) GeoTIFF를
  `Terrain.heights`에 넣으면 그대로 동작한다.
- 건물: 포함하지 않았다. 브이월드 3D 건물(glb/obj) 또는 OSM 건물을 URDF/메시로 올리면 된다.
- 위성영상: 이 환경에서는 ESRI/VWorld/Google 타일이 모두 차단되어 고도 색상으로 대체했다.
  로컬에서는 `hypsometric_texture()` 대신 같은 범위의 정사영상 PNG를 `texture_path`로 주면 된다.

## 동작 원리

1. `load_dem()`이 중심 좌표 기준 3x3 타일을 받아 (768x768) 고도 배열을 만든다. 해수면 이하는 0 m.
2. `add_terrain_to_pybullet()`이 `GEOM_HEIGHTFIELD`로 충돌체를 만들고, Bullet이 heightfield를
   (min+max)/2 높이에 중심을 두므로 최저점이 z=0이 되게 올린다. `verify_terrain()`이 레이캐스트로
   DEM과 일치하는지 확인한다(오차 0.00 m).
3. `IslandAviary._housekeeping()`이 매 reset마다 기본 평면을 지우고 지형을 다시 올린다.
4. `fly_island.py`는 경로를 따라 "진행거리 s"를 속도 v로 전진시키고, 드론에서 `max_err` 이내로
   잘라낸 점을 `DSLPIDControl`에 목표로 준다. 속도는 `--accel`로 램프업한다.

## 한계

- Crazyflie 모델(수십 g)이라 실제 산업용 드론의 공력·바람은 반영되지 않는다. `Physics.PYB_DRAG`,
  `PYB_GND_DRAG_DW`로 항력·지면효과를 켤 수 있다.
- PyBullet 소프트웨어 렌더러는 heightfield 삼각형 118만 개를 매 프레임 그리므로 영상 생성이 느리다.
  실시간 시각화는 `--gui`(로컬) 또는 Unreal/Unity+Cesium 쪽이 맞다.
- 센서(카메라/라이다) 시뮬, PX4/ArduPilot 연동이 필요하면 PX4 + Gazebo(heightmap DEM) 또는
  Colosseum(AirSim) 쪽으로 가야 한다.
