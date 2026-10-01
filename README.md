# 삼각측량 위치 보정 패치 — aerodrone_hackathon `litter/` 용

`dohun415/aerodrone_hackathon` 저장소 `feature/coastal-litter-pipeline` 브랜치(커밋 1c3cd3e)의
위치 계산을 **광선 교차 삼각측량**으로 보완한 파일 묶음이다. 원리·사용법·검증 결과는
[`docs/삼각측량_위치보정.md`](docs/삼각측량_위치보정.md).

## 적용 방법

```
aerodrone_hackathon/
├─ litter/
│  ├─ triangulate.py   ← 새 파일 복사
│  ├─ orbit_map.py     ← 덮어쓰기 (기존 동작은 --no-tri 로 유지)
│  └─ video_map.py     ← 덮어쓰기 (--height 옵션 추가)
└─ tests/
   └─ test_triangulate.py   ← 새 파일 복사
```

그 다음 `python tests/test_triangulate.py` 로 7개 합성 시나리오가 통과하는지 확인하고,

```powershell
& $py -m litter.video_map --video DJI_0020.MP4 --srt DJI_0020.SRT --out runs/map/0020 `
    --weights runs/seg/aihub_gsd_det_s/weights/best.pt --height 20 --pitch -90 --every 1 --min-hits 3 --r95
```

처럼 돌리면 `objects.csv` 에 위경도와 함께 방식(`method`), 시차, 잔차, 오차 반경이 기록된다.
새로 추가된 의존성은 없다 (numpy 만 사용).
