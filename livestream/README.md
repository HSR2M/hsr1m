# DJI Mini 5 Pro 라이브 스트리밍 서버

DJI Fly(RTMP) → **MediaMTX** → 브라우저(WebRTC, 실패 시 LL-HLS) 구조의 셀프호스팅 구성입니다.
Caddy 가 웹 페이지와 영상 엔드포인트를 같은 도메인으로 제공합니다.

```
DJI Fly --RTMP:1935--> MediaMTX --WebRTC(/webrtc)--> 브라우저
                                \--LL-HLS(/hls)-----> (대체 경로)
                        Caddy: 80/443 -> web/index.html, /webrtc, /hls
```

## 1. 서버 준비
- 공인 IP 가 있는 VPS (Docker, Docker Compose 설치)
- 방화벽 오픈: `80/tcp`, `443/tcp`, `1935/tcp`, `8189/udp`
- (권장) 도메인을 서버 IP 에 연결 → HTTPS 자동 발급

## 2. 설정
```bash
cd livestream
cp .env.example .env        # PUBLIC_HOST, SITE_ADDRESS 수정
```
`mediamtx.yml` 의 송출 비밀번호 `CHANGE_ME` 를 **반드시** 바꾸세요.

```bash
docker compose up -d
docker compose logs -f mediamtx
```

도메인이 없으면 `.env` 에서 `SITE_ADDRESS=:80`, `PUBLIC_HOST=<서버 공인 IP>` 로 두면 HTTP 로 동작합니다.

## 3. DJI Fly 에서 송출
1. 조종기를 인터넷에 연결(RC 2: Wi-Fi/핫스팟, RC-N3: 연결된 폰의 네트워크)
2. DJI Fly 카메라 화면 → 설정(⋯) → 전송 → 라이브 스트리밍 플랫폼 → **RTMP**
3. RTMP 주소 입력
   ```
   rtmp://<도메인 또는 IP>/live?user=drone&pass=<비밀번호>
   ```
   DJI Fly 가 `?user=&pass=` 가 붙은 주소를 거부하면 `mediamtx.yml` 의 `drone` 계정의
   `user`/`pass` 를 비우고 `ips` 에 송출 네트워크의 고정 IP 를 넣는 방식으로 바꾸세요.
4. 해상도 선택 후 시작

## 4. 시청
`https://<도메인>/` 을 열면 송출이 시작될 때 자동으로 재생됩니다.
- WebRTC: 지연 약 1초 미만 (영상만, DJI 의 AAC 오디오는 WebRTC 미지원이라 소리 없음)
- HLS 대체 경로: 지연 수 초, 소리 포함

기존 사이트에 넣으려면 iframe 으로 임베드하면 됩니다.
```html
<iframe src="https://<도메인>/" width="960" height="540" allow="autoplay; fullscreen"></iframe>
```

## 5. 송출 없이 테스트
```bash
ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=30 -f lavfi -i sine \
  -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p -g 60 -c:a aac \
  -f flv "rtmp://localhost/live?user=drone&pass=<비밀번호>"
```

## 참고
- 시청은 누구나 가능합니다. 제한하려면 `mediamtx.yml` 의 `user: any` read 권한을 계정 방식으로 바꾸세요.
- 이 구성은 Docker 가 없는 환경에서 작성되어 실제 송출까지는 테스트되지 않았습니다. 첫 실행 시 `docker compose logs` 로 확인해 주세요.
