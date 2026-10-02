"""로컬 서버: outputs/ 를 같은 와이파이의 휴대폰·노트북에 보여 주고, 완료 체크·보정·출발지·작업자 위치를 접속한 모두에게 공유한다.

  python serve.py                      # http://<이 컴퓨터 IP>:8765/  (outputs/plan/수거계획.html 등)
  python serve.py --port 8000 --root outputs
표준 라이브러리만 쓴다 (설치 없음). 공유 상태는 outputs/_state/<현장>.json 에 저장되어 서버를 다시 켜도 남는다.

API (수거계획.html 이 자동으로 씀; 인터넷 버전은 같은 형식을 Supabase 로)
  GET  /api/state/<현장>        {done:[], calib:{}, depot:{}, updatedAt, byName}
  PUT  /api/state/<현장>        같은 형식으로 저장
  GET  /api/positions           최근 10분 작업자 위치 [{id,name,lat,lon,acc,updated_at}]
  POST /api/positions           {id,name,lat,lon,acc,updated_at}
  DELETE /api/positions/<id>
  GET  /api/sites               현장 목록
"""
from __future__ import annotations

import argparse
import json
import socket
import threading
import time
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
POSITIONS: dict[str, dict] = {}
LOCK = threading.Lock()


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except OSError:
        return "127.0.0.1"


def make_handler(root: Path):
    state_dir = root / "_state"; state_dir.mkdir(parents=True, exist_ok=True)

    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(root), **k)

        def log_message(self, fmt, *args):  # 평소엔 조용히, 오류(4xx·5xx) 만 표시
            if fmt.startswith("code "):
                super().log_message(fmt, *args)

        def _json(self, code: int, body) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data))); self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers(); self.wfile.write(data)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}

        def _site_file(self, site: str) -> Path:
            safe = "".join(ch for ch in unquote(site) if ch.isalnum() or ch in "-_.가-힣") or "site"
            return state_dir / f"{safe}.json"

        def do_OPTIONS(self):
            self.send_response(204); self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS"); self.send_header("Access-Control-Allow-Headers", "Content-Type"); self.end_headers()

        def do_GET(self):
            p = urlparse(self.path).path
            if p.startswith("/api/state/"):
                f = self._site_file(p[len("/api/state/"):])
                return self._json(200, json.loads(f.read_text(encoding="utf-8")) if f.exists() else {})
            if p == "/api/positions":
                cut = datetime.now(timezone.utc) - timedelta(minutes=10)
                with LOCK:
                    rows = [r for r in POSITIONS.values() if datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00")) > cut]
                return self._json(200, rows)
            if p == "/api/sites":
                sites = sorted(str(h.relative_to(root)).replace("\\", "/") for h in root.rglob("수거계획.html"))
                return self._json(200, {"sites": sites})
            if p == "/":
                pages = sorted(str(h.relative_to(root)).replace("\\", "/") for h in root.rglob("*.html") if h.name in ("수거계획.html", "index.html"))
                body = "<!doctype html><meta charset=utf-8><title>ShoreSweep Planner</title><body style='font-family:system-ui,sans-serif;padding:24px'><h1>수거계획 페이지</h1><ul>" + \
                       "".join(f"<li><a href='/{h}'>{h}</a></li>" for h in pages) + "</ul><p style='color:#777'>휴대폰에서는 이 컴퓨터의 IP 주소로 접속하세요.</p>"
                data = body.encode("utf-8"); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
            return super().do_GET()

        def do_PUT(self):
            p = urlparse(self.path).path
            if p.startswith("/api/state/"):
                body = self._body(); body["updatedAt"] = int(time.time() * 1000)
                keep = {k: body.get(k) for k in ("done", "calib", "depot", "updatedAt", "byName")}
                self._site_file(p[len("/api/state/"):]).write_text(json.dumps(keep, ensure_ascii=False), encoding="utf-8")
                return self._json(200, keep)
            return self._json(404, {"error": "not found"})

        def do_POST(self):
            p = urlparse(self.path).path
            if p == "/api/positions":
                row = self._body()
                if not row.get("id"):
                    return self._json(400, {"error": "id 필요"})
                row.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
                with LOCK:
                    POSITIONS[row["id"]] = row
                return self._json(200, row)
            if p.startswith("/api/state/"):
                return self.do_PUT()
            return self._json(404, {"error": "not found"})

        def do_DELETE(self):
            p = urlparse(self.path).path
            if p.startswith("/api/positions/"):
                with LOCK:
                    POSITIONS.pop(unquote(p[len("/api/positions/"):]), None)
                return self._json(200, {"ok": True})
            return self._json(404, {"error": "not found"})

    return H


def serve(root: Path, port: int = 8765, open_path: str | None = None, host: str = "0.0.0.0") -> None:
    root = Path(root).resolve()
    srv = ThreadingHTTPServer((host, port), make_handler(root))
    ip = _lan_ip()
    print(f"서버 시작: http://{ip}:{port}/  (이 컴퓨터: http://localhost:{port}/)  루트 {root}  — 끝내려면 Ctrl+C")
    if open_path:
        threading.Timer(0.8, lambda: webbrowser.open(f"http://localhost:{port}/{open_path}")).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(ROOT / "outputs"))
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--open", default=None, help="시작하면서 열 경로 (예: plan/수거계획.html)")
    a = ap.parse_args()
    serve(Path(a.root), a.port, a.open, a.host)
