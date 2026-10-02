"""input/ 에 현장 폴더가 여러 개일 때의 목록 페이지 (index.html)."""
from __future__ import annotations

import html
from pathlib import Path

from .collect import BASIS_KO

CSS = """
:root{--bg:#f4f6f9;--card:#fff;--ink:#17202a;--ink2:#4a5563;--muted:#7a8494;--border:#dfe3e9;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f1419;--card:#1a2027;--ink:#eef1f5;--ink2:#b8c0cb;--muted:#8691a0;--border:#2b343f}}
:root[data-theme=dark]{--bg:#0f1419;--card:#1a2027;--ink:#eef1f5;--ink2:#b8c0cb;--muted:#8691a0;--border:#2b343f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:"Malgun Gothic","Apple SD Gothic Neo","Noto Sans KR","NanumGothic",system-ui,sans-serif;font-size:16px;line-height:1.5}
.wrap{max-width:1100px;margin:0 auto;padding:16px}h1{font-size:28px;margin:8px 0 4px;font-weight:800}p.lead{color:var(--ink2);margin:0 0 14px}
.chain{font-size:13px;color:var(--ink2);background:var(--card);border:1px solid var(--border);border-radius:12px;padding:10px 12px;margin:0 0 18px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:16px;display:flex;flex-direction:column;gap:8px}
.card h2{font-size:19px;margin:0;font-weight:800}.card h2 a{color:var(--ink);text-decoration:none}.card h2 a:hover{color:var(--accent)}
.card .sub{color:var(--ink2);font-size:14px;margin:0}.card img{width:100%;border-radius:10px;border:1px solid var(--border);object-fit:cover;max-height:220px}
.facts{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.fact{background:var(--bg);border-radius:10px;padding:6px 8px;text-align:center}
.fact b{display:block;font-size:19px;line-height:1.2}.fact span{font-size:11.5px;color:var(--ink2)}
.btn{display:inline-block;font-size:14px;padding:7px 14px;border-radius:999px;background:var(--accent);color:#fff;text-decoration:none;font-weight:700;align-self:flex-start}
.foot{color:var(--muted);font-size:13px;margin:20px 0}
"""


def build_index(entries: list[dict], out_html: str | Path, title: str = "쓰레기 수거 계획 — 현장 목록") -> Path:
    """entries: [{id, title, href, png (data url 또는 경로), totals, n, survey, basis_counts, description}]"""
    esc = lambda s: html.escape(str(s), quote=True)  # noqa: E731
    cards = []
    for e in entries:
        t = e.get("totals", {})
        bc = " · ".join(f"{BASIS_KO.get(k, k)} {v}" for k, v in (e.get("basis_counts") or {}).items())
        cards.append(f"""<div class="card"><h2><a href="{esc(e['href'])}">{esc(e['title'])}</a></h2>
<p class="sub">조사일 {esc(e.get('survey', ''))}{(' · ' + esc(bc)) if bc else ''}</p>
{f'<a href="{esc(e["href"])}"><img src="{e["png"]}" alt=""></a>' if e.get('png') else ''}
<div class="facts"><div class="fact"><b>{t.get('items', 0)}</b><span>개</span></div><div class="fact"><b>{t.get('kg_plan', 0):.1f}</b><span>kg (대표)</span></div><div class="fact"><b>{t.get('zones', 0)}</b><span>구역</span></div></div>
{f'<p class="sub">{esc(e["description"])}</p>' if e.get('description') else ''}
<a class="btn" href="{esc(e['href'])}">수거계획 열기 →</a></div>""")
    doc = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{CSS}</style></head>
<body><div class="wrap"><h1>{esc(title)}</h1><p class="lead">드론 영상에서 파이프라인이 찾은 쓰레기 위치와 3D 부피로 만든 현장별 수거 계획입니다. 현장을 고르면 지도·작업 순서·마대·시간이 나오고, 조건을 바꾸면 바로 다시 계산됩니다.</p>
<div class="chain">드론 영상 + SRT → ① 탐지(YOLO) → ② 3D 복원(COLMAP) → ③ 위치 → ④ 부피(SAM 2 투표 + 높이지도) → ⑤ 무게(겉보기 밀도) → <b>⑥ 수거계획 (이 사이트)</b></div>
<div class="grid">{''.join(cards)}</div><p class="foot">ShoreSweep Planner (hsr1m) · 입력: input/&lt;현장&gt;/ · 생성: python run.py</p></div></body></html>"""
    out = Path(out_html); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return out
