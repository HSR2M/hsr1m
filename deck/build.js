// 드론대장 붕붕이 × 3DLabs 제안 덱 — pptxgenjs 구조화 덱 (v2: 업체 데이터·실제 결과 반영)
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fs = require("fs");
const path = require("path");
const fa = require("react-icons/fa");
const { applyTheme } = require("/root/.claude/skills/synced/ec8afc1a-fc29-4544-923a-6847ae5fe3af_4620f687-7953-4a8a-abdc-10fb20607f83/pptx/scripts/apply_theme.js");

const THEME = {
  name: "Bungbungi Ocean",
  headFontFace: "Malgun Gothic",
  bodyFontFace: "Malgun Gothic",
  colors: {
    dk1: "10212E", lt1: "FFFFFF", dk2: "0B3C5D", lt2: "EEF3F6",
    accent1: "0B3C5D", accent2: "F26B21", accent3: "1C7293", accent4: "6F8794", accent5: "D5DEE4", accent6: "FFD9C2",
    hlink: "1C7293", folHlink: "6F8794",
  },
};
const H = THEME.colors; // hex-only options
const IMG_DIR = fs.existsSync(path.join(__dirname, "img")) ? path.join(__dirname, "img") : path.join(__dirname, "..", "site", "assets");
const img = (f) => path.join(IMG_DIR, f);

async function icon(name, colorHex, size = 256) {
  const Comp = fa[name];
  if (!Comp) throw new Error("no icon " + name);
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + colorHex, size }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.author = "드론대장 붕붕이";
  pres.title = "추정이 틀리면 배차가 틀린다 — 드론 기반 해안쓰레기 측정·수거계획 플랫폼";
  const C = pres.SchemeColor;
  const ICON = {};
  for (const n of ["FaExclamationTriangle", "FaSatellite", "FaSearchLocation", "FaCubes", "FaRoute", "FaTruck", "FaChartBar", "FaWater",
    "FaMapMarkedAlt", "FaBalanceScale", "FaUsers", "FaCheckCircle", "FaFlask", "FaHandshake", "FaEye", "FaCamera", "FaWind", "FaCoins",
    "FaClipboardList", "FaPlane", "FaLayerGroup", "FaRulerCombined", "FaCrosshairs", "FaWalking", "FaSun", "FaBoxOpen", "FaDatabase", "FaMapMarkerAlt", "FaBullseye", "FaCalendarAlt", "FaCity", "FaBan", "FaTachometerAlt", "FaWeightHanging", "FaMoon"]) {
    ICON[n + "_w"] = await icon(n, "FFFFFF");
    ICON[n + "_n"] = await icon(n, H.dk2);
    ICON[n + "_o"] = await icon(n, H.accent2);
  }

  // ───────── 레이아웃 ─────────
  const footer = (dark) => [
    { text: "드론대장 붕붕이 · 3DLabs 제안 · 2026.10", options: { x: 0.6, y: 7.02, w: 6, h: 0.3, fontSize: 9, color: C.accent4, margin: 0, isTextBox: true } },
  ];
  pres.defineSlideMaster({
    title: "DARK_TITLE", background: { color: H.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 2.1, w: 7.2, h: 1.9, fontSize: 40, bold: true, color: C.background1, valign: "bottom", margin: 0, align: "left" } } },
      { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 4.15, w: 7.0, h: 1.4, fontSize: 16, color: C.accent5, valign: "top", margin: 0, align: "left" } } },
    ],
  });
  pres.defineSlideMaster({
    title: "SECTION", background: { color: H.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 3.0, w: 11.5, h: 1.3, fontSize: 40, bold: true, color: C.background1, valign: "bottom", margin: 0, align: "left" } } },
      { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.4, w: 11.0, h: 1.2, fontSize: 16, color: C.accent5, valign: "top", margin: 0, align: "left" } } },
      ...footer(true),
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT", background: { color: H.lt1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.42, w: 12.1, h: 0.95, fontSize: 28, bold: true, color: C.text1, valign: "middle", margin: 0, align: "left" } } },
      ...footer(false),
    ],
    slideNumber: { x: 12.3, y: 7.02, w: 0.5, h: 0.3, fontSize: 9, color: C.accent4, align: "right" },
  });
  pres.defineSlideMaster({
    title: "CONTENT_LT2", background: { color: H.lt2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.42, w: 12.1, h: 0.95, fontSize: 28, bold: true, color: C.text1, valign: "middle", margin: 0, align: "left" } } },
      ...footer(false),
    ],
    slideNumber: { x: 12.3, y: 7.02, w: 0.5, h: 0.3, fontSize: 9, color: C.accent4, align: "right" },
  });
  pres.defineSlideMaster({
    title: "DARK_CONTENT", background: { color: H.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.42, w: 12.1, h: 0.95, fontSize: 28, bold: true, color: C.background1, valign: "middle", margin: 0, align: "left" } } },
      ...footer(true),
    ],
    slideNumber: { x: 12.3, y: 7.02, w: 0.5, h: 0.3, fontSize: 9, color: C.accent5, align: "right" },
  });

  // ───────── 헬퍼 ─────────
  const shadow = () => ({ type: "outer", color: "0B3C5D", blur: 8, offset: 2, angle: 90, opacity: 0.10 });
  function tb(slide, text, o) { slide.addText(text, Object.assign({ isTextBox: true, margin: 0, fontSize: 13, color: C.text1 }, o)); }
  function sub(slide, text, w) { tb(slide, text, { x: 0.6, y: 1.32, w: w || 12.1, h: 0.45, fontSize: 14, color: C.accent4, objectName: "subtitle" }); }
  function source(slide, text, dark) { tb(slide, text, { x: 0.6, y: 6.62, w: 12.1, h: 0.36, fontSize: 9, color: dark ? C.accent5 : C.accent4, valign: "bottom", objectName: "source" }); }
  function tag(slide, text, x, y, dark, w) {
    w = w || 1.55;
    slide.addShape(pres.ShapeType.roundRect, { x, y, w, h: 0.3, fill: { color: dark ? H.accent2 : H.accent6 }, line: { color: dark ? H.accent2 : H.accent6 }, rectRadius: 0.15, objectName: "tag" });
    tb(slide, text, { x, y, w, h: 0.3, fontSize: 9.5, bold: true, color: dark ? C.background1 : C.text2, align: "center", valign: "middle" });
  }
  function card(slide, x, y, w, h, { icon, head, body, dark, fill, headSize, bodySize }) {
    slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill || (dark ? "124A6E" : H.lt1) }, line: { color: fill || (dark ? "124A6E" : H.lt1) }, rectRadius: 0.12, shadow: dark ? undefined : shadow(), objectName: "card " + head });
    let ty = y + 0.28;
    if (icon) {
      slide.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: y + 0.28, w: 0.62, h: 0.62, fill: { color: dark ? H.accent2 : H.dk2 }, line: { color: dark ? H.accent2 : H.dk2 }, objectName: "icon circle" });
      slide.addImage({ data: ICON[icon + "_w"], x: x + 0.45, y: y + 0.43, w: 0.32, h: 0.32, objectName: "icon " + icon });
      ty = y + 1.08;
    }
    tb(slide, head, { x: x + 0.3, y: ty, w: w - 0.6, h: 0.42, fontSize: headSize || 14.5, bold: true, color: dark ? C.background1 : C.text1, valign: "top" });
    tb(slide, body, { x: x + 0.3, y: ty + 0.48, w: w - 0.6, h: h - (ty - y) - 0.62, fontSize: bodySize || 11.5, color: dark ? C.accent5 : C.accent4, valign: "top", paraSpaceAfter: 4 });
  }
  function stat(slide, x, y, w, h, { value, unit, label, note, dark, color, valueSize }) {
    slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: dark ? "124A6E" : H.lt1 }, line: { color: dark ? "124A6E" : H.lt1 }, rectRadius: 0.12, shadow: dark ? undefined : shadow(), objectName: "stat " + label });
    tb(slide, label, { x: x + 0.28, y: y + 0.22, w: w - 0.5, h: 0.34, fontSize: 11, color: dark ? C.accent5 : C.accent4 });
    slide.addText([
      { text: value, options: { fontSize: valueSize || 34, bold: true, color: color || (dark ? C.background1 : C.text2) } },
      { text: unit ? " " + unit : "", options: { fontSize: 13, bold: true, color: dark ? C.accent5 : C.accent4 } },
    ], { x: x + 0.28, y: y + 0.55, w: w - 0.5, h: 0.75, isTextBox: true, margin: 0, valign: "middle" });
    if (note) tb(slide, note, { x: x + 0.28, y: y + 1.32, w: w - 0.5, h: h - 1.45, fontSize: 10.5, color: dark ? C.accent5 : C.accent4, valign: "top" });
  }
  function stat2(slide, x, y, w, h, { value, unit, label, note, color }) {
    slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "stat " + label });
    tb(slide, label, { x: x + 0.25, y: y + 0.16, w: w - 0.45, h: 0.3, fontSize: 10, color: C.accent4 });
    slide.addText([
      { text: value, options: { fontSize: 28, bold: true, color: color || C.text2 } },
      { text: unit ? " " + unit : "", options: { fontSize: 12, bold: true, color: C.accent4 } },
    ], { x: x + 0.25, y: y + 0.42, w: w - 0.45, h: 0.6, isTextBox: true, margin: 0, valign: "middle" });
    if (note) tb(slide, note, { x: x + 0.25, y: y + 1.0, w: w - 0.45, h: h - 1.08, fontSize: 9.5, color: C.accent4, valign: "top" });
  }
  function bullets(slide, items, o) {
    const arr = items.map((t, i) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, paraSpaceAfter: 6 } }));
    slide.addText(arr, Object.assign({ isTextBox: true, fontSize: 12.5, color: C.text1, valign: "top", margin: 0 }, o));
  }
  function refs(slide, text, x, y, w, h, dark) {
    tb(slide, text, { x, y, w, h, fontSize: 9.5, italic: true, color: dark ? C.accent5 : C.accent4, valign: "top", objectName: "refs" });
  }
  const hdr = (t) => ({ text: t, options: { bold: true, color: H.dk2, fill: { color: "DCE6EC" }, fontSize: 10 } });
  const chartBase = (extra) => Object.assign({
    chartColors: [H.accent1], showLegend: false, showTitle: false,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelFontFace: "+mn-lt", dataLabelColor: H.dk1,
    catAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: 10, catAxisLabelColor: H.accent4,
    valAxisLabelFontFace: "+mn-lt", valAxisLabelFontSize: 9, valAxisLabelColor: H.accent4,
    valGridLine: { color: "DDE3E8", size: 0.5 }, catGridLine: { style: "none" }, barGapWidthPct: 60,
    plotArea: { fill: { color: H.lt1 } },
  }, extra);

  // ═════════ 표지 ═════════
  pres.addSection({ title: "표지" });
  let s = pres.addSlide({ masterName: "DARK_TITLE", sectionTitle: "표지" });
  s.addImage({ path: img("hotspot_map_gyodong.jpg"), x: 8.1, y: 0, w: 5.233, h: 7.5, sizing: { type: "cover", w: 5.233, h: 7.5 }, objectName: "교동도 집적 예상 지도" });
  s.addShape(pres.ShapeType.rect, { x: 8.1, y: 0, w: 5.233, h: 7.5, fill: { color: H.dk2, transparency: 35 }, line: { color: H.dk2, transparency: 100 }, objectName: "image tint" });
  tb(s, "드론 기반 해안쓰레기 측정 · 수거계획 플랫폼 제안", { x: 0.7, y: 1.2, w: 7.2, h: 0.4, fontSize: 13, bold: true, color: C.accent2, charSpacing: 1 });
  s.addText("추정이 틀리면\n배차가 틀린다", { placeholder: "title" });
  s.addText("드론 영상 하나로 쓰레기를 찾고, 3D로 부피를 재고, 무게를 구간으로 내고,\n수거계획을 바꾸는 물체만 다시 날아 마대·트럭·인원을 확정합니다.", { placeholder: "body" });
  tb(s, "드론대장 붕붕이  ·  3DLabs 제안  ·  2026. 10", { x: 0.7, y: 6.5, w: 7.2, h: 0.4, fontSize: 11, color: C.accent5 });
  s.addNotes("표지. 한 문장: 수거계획의 입력(무게·위치)이 지금은 수십~수백 배 틀리고, 우리는 그 입력을 3D 부피와 예측구간으로 제공한다.");

  // ═════════ 한 장 요약 ═════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "표지" });
  s.addText("한 장 요약", { placeholder: "title" });
  sub(s, "문제 → 해법 → 검증 → 제안. 새로 발명한 알고리즘은 없고, 검증된 방법을 수거계획 하나로 이었습니다.");
  const sum = [
    ["FaExclamationTriangle", "문제: 추정이 곧 예산이다", "해양쓰레기 수거량은 5년간 19.8% 늘었고 90%를 지자체가 치웁니다. 업체 라벨 42개의 기록 무게는 합계 1.3 kg, 현실적 범위는 115~1,355 kg. 탐지 위치는 50 m씩 빗나갑니다."],
    ["FaRoute", "해법: 비행 한 번 = 수거계획서 한 부", "핫스팟 우선 경로 → 커버리지 비행 → 탐지 → 3D 위치 → SfM 부피 × 겉보기밀도 → 무게 예측구간 → 경계에 걸린 물체만 2차 선회 → 마대·트럭·인원·경로 작업카드."],
    ["FaFlask", "검증: 상자 3개, 영상 3편, 해안 1개", "크기 아는 상자 3개에서 부피 오차 −10~+20% (업체 방식은 1/112·1/180). 3D↔GPS 잔차 1.16 m. 재방문으로 재현율 0.71→0.86. 하와이 니하우 섬 5,476개·7.9~33.6 t 수거계획."],
    ["FaHandshake", "제안: 위성이 넓게, 드론이 자세히", "3DLabs의 위성 ARD로 광역 집적 패치·변화를 잡고, 드론이 재질·부피·위치를 확정해 지자체 수거계획으로 연결하는 B2G 공동 실증."],
  ];
  sum.forEach((c, i) => card(s, 0.6 + i * 3.075, 1.95, 2.9, 4.0, { icon: c[0], head: c[1], body: c[2], headSize: 15, bodySize: 12.5 }));
  s.addNotes("4블록으로 전체 흐름. 각 블록은 뒤에서 한 장 이상으로 풀린다.");

  // ═════════ 01 현황과 문제 ═════════
  pres.addSection({ title: "01 현황과 문제" });
  s = pres.addSlide({ masterName: "SECTION", sectionTitle: "01 현황과 문제" });
  tb(s, "01", { x: 0.8, y: 1.9, w: 3, h: 1.0, fontSize: 60, bold: true, color: C.accent2 });
  s.addText("현황과 문제", { placeholder: "title" });
  s.addText("수거량은 늘고 비용은 지자체 몫인데, 그 계획의 입력값은 믿을 수 없는 점 추정입니다.", { placeholder: "body" });

  // 현황: 수거량 추이
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "01 현황과 문제" });
  s.addText("해양쓰레기 수거량은 5년간 19.8% 늘었다", { placeholder: "title" });
  sub(s, "2021~2025년 전국 해양폐기물 수거량 (톤). 2025년 14.5만 톤은 연간 발생량 추정치(14.5만 톤)와 같은 규모입니다.");
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.95, w: 7.6, h: 4.5, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "연도별 해양폐기물 수거량 (톤)", { x: 0.9, y: 2.1, w: 7, h: 0.35, fontSize: 12, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "수거량(t)", labels: ["2021", "2022", "2023", "2024", "2025"], values: [120736, 126035, 131931, 132686, 144615] }],
    chartBase({ x: 0.8, y: 2.5, w: 7.2, h: 3.85, barDir: "col", valAxisMinVal: 0, valAxisMaxVal: 160000, valAxisLabelFormatCode: "#,##0", dataLabelFormatCode: "#,##0", catAxisLabelFontSize: 11 }));
  stat(s, 8.5, 1.95, 4.23, 1.4, { value: "14.5만", unit: "t / 년", label: "연간 해양쓰레기 발생량 추정", note: "육상 기인 65.3% · 해상 기인 34.7%" });
  stat(s, 8.5, 3.5, 4.23, 1.4, { value: "15.2만", unit: "t", label: "해양에 남아 있는 현존량", note: "침적 13.8만 · 해변 1.2만 · 부유 0.2만 t" });
  stat(s, 8.5, 5.05, 4.23, 1.4, { value: "1,114", unit: "억 원", label: "2026년 해양폐기물 처리 예산", note: "수거해도 현존량이 줄지 않는 구조", color: C.accent2 });
  source(s, "출처: 해양수산부 자료(김선교 의원실, 2026.09) 연도별 수거량 · 해양수산부 「해양폐기물 저감 대책」 발생량·현존량 추정 · 2026년 처리 예산 1,114억 원(해양수산부, 2026.09)");
  s.addNotes("수거량 증가는 문제가 커지는 신호이자 시장 신호. 2025년 수거량이 연간 발생량과 같아져 현존량은 제자리.");

  // 비용 구조
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "01 현황과 문제" });
  s.addText("수거 비용은 지자체 몫이고, 추정이 곧 예산이다", { placeholder: "title" });
  sub(s, "해안쓰레기가 수거량의 76%를 차지하고, 그 수거의 90%를 지자체가 수행합니다. 톤 단위 추정 오차가 곧 수천만 원입니다.");
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.95, w: 6.2, h: 4.5, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "유형별 수거량, 2021~2025 누계 (톤)", { x: 0.9, y: 2.1, w: 5.8, h: 0.35, fontSize: 12, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "수거량(t)", labels: ["해안쓰레기", "침적쓰레기", "부유쓰레기"], values: [499934, 119521, 36548] }],
    chartBase({ x: 0.8, y: 2.5, w: 5.8, h: 3.8, barDir: "bar", valAxisMinVal: 0, valAxisMaxVal: 600000, valAxisLabelFormatCode: "#,##0", dataLabelFormatCode: "#,##0", catAxisLabelFontSize: 11, catAxisOrientation: "maxMin" }));
  stat(s, 7.1, 1.95, 2.7, 2.15, { value: "3,654", unit: "억 원", label: "지자체 수거예산 2017~2022 누계", note: "같은 기간 3.5배 증가" });
  stat(s, 10.03, 1.95, 2.7, 2.15, { value: "50 : 50", unit: "", label: "수거비 국비 : 지방비", note: "지방비는 다시 도비·시군비로 나뉨" });
  stat(s, 7.1, 4.3, 2.7, 2.15, { value: "90", unit: "%", label: "지자체가 처리하는 수거량 비중", note: "공공기관 처리는 10%", color: C.accent2 });
  stat(s, 10.03, 4.3, 2.7, 2.15, { value: "50만", unit: "원/t", label: "처리 단가 (전남, 약)", note: "100 t 오차 = 5천만 원", valueSize: 30 });
  source(s, "출처: 유형별 수거량 해양수산부(2026.09) · 지자체 수거예산·국비 분담·처리 비중 에너지데일리(국회 자료, 2017~2022) · 처리 단가 한국일보(2018·2019, 전남 톤당 50만 원)");
  s.addNotes("작은 지자체일수록 '미리 재는 것'이 예산 그 자체. 수거 전 측정의 가치를 돈으로 환산하는 장.");

  // 거제 사례
  s = pres.addSlide({ masterName: "DARK_CONTENT", sectionTitle: "01 현황과 문제" });
  s.addText("추정이 틀리면 생기는 일: 거제, 2023년 7월 집중호우", { placeholder: "title" });
  tb(s, "유입량을 437 t으로 추정하고 굴삭기·차량을 투입했지만, 1주일 넘게 걸려 272 t만 수거했습니다. 처리비는 8천만 원 이상.", { x: 0.6, y: 1.32, w: 12.1, h: 0.45, fontSize: 14, color: C.accent5 });
  stat(s, 0.6, 2.0, 2.9, 2.0, { value: "437", unit: "t", label: "추정 유입량", note: "육안·경험 기반", dark: true });
  stat(s, 3.7, 2.0, 2.9, 2.0, { value: "272", unit: "t", label: "실제 수거량", note: "추정의 62%", dark: true, color: C.accent2 });
  stat(s, 6.8, 2.0, 2.9, 2.0, { value: "1주+", unit: "", label: "소요 기간", note: "장비·인력 상시 대기", dark: true });
  stat(s, 9.9, 2.0, 2.83, 2.0, { value: "8천만+", unit: "원", label: "처리 비용", note: "국비 지원 요청", dark: true });
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 4.25, w: 12.13, h: 2.1, fill: { color: "124A6E" }, line: { color: "124A6E" }, rectRadius: 0.12, objectName: "insight card" });
  s.addShape(pres.ShapeType.ellipse, { x: 0.95, y: 4.6, w: 0.7, h: 0.7, fill: { color: H.accent2 }, line: { color: H.accent2 }, objectName: "icon circle" });
  s.addImage({ data: ICON.FaTruck_w, x: 1.12, y: 4.77, w: 0.36, h: 0.36, objectName: "icon truck" });
  tb(s, "남는 트럭과 모자라는 트럭이 동시에 생긴다. 거제는 반복된다.", { x: 1.95, y: 4.55, w: 10.5, h: 0.45, fontSize: 16, bold: true, color: C.background1 });
  tb(s, "무게가 틀리면 마대·트럭 수가 틀리고, 위치가 틀리면 동선·인원이 틀립니다. 2011년 7월 낙동강 유입 쓰레기로 거제의 관광수입 손실은 2,900만~3,700만 달러로 추정됐고(Jang et al. 2014), 2026년 8월 폭우로도 경남 연안에 1,180 t이 유입돼 통영·거제가 80%를 차지했습니다. 작은 지자체일수록 수거 전에 재는 것이 예산 그 자체입니다.",
    { x: 1.95, y: 5.05, w: 10.5, h: 1.2, fontSize: 12.5, color: C.accent5, valign: "top" });
  source(s, "출처: 뉴시스 2023.07.25 「거제 해양쓰레기 437t 추정·272t 수거」 · Jang, Hong, Lee, Lee & Shim (2014) Marine Pollution Bulletin 81:49–54 · 서울신문 2026.09.09 「광복절 연휴 폭우 해양쓰레기, 경남 연안 96% 수거」", true);
  s.addNotes("실제 사례 한 장. 숫자 네 개만 크게. 2011·2026년 반복 사례로 '일회성 아님'을 보인다.");

  // 현행 방식의 한계
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "01 현황과 문제" });
  s.addText("지금 쓰는 세 가지 눈, 모두 무게를 못 본다", { placeholder: "title" });
  sub(s, "신고·순찰은 느리고, 위성은 패치만 보고, 2D 정사영상은 높이가 없어 무게를 못 냅니다.");
  const eyes = [
    ["FaEye", "사람 신고 · 순찰", "현존량의 90%가 침적·해변에 흩어져 있는데 탐지는 신고와 순찰에 의존합니다. 국가 해안쓰레기 모니터링은 2개월에 1회, 정점 40~60곳만 조사합니다.", "느리고 범위가 좁다"],
    ["FaSatellite", "위성 영상", "집적 패치의 위치와 변화는 잡지만 재질·부피는 확정하지 못합니다. 해상도 때문에 수십 cm 물체 하나하나의 무게로 내려가지 않습니다.", "넓게 보지만 재질·부피 불가"],
    ["FaCamera", "드론 2D 정사영상", "업체 자료는 3 cm/px 정사영상뿐이라 높이(DSM)가 없습니다. 그래서 무게를 '라벨 면적 × 고정 계수'로 계산하고, 위치는 드론 GPS 그대로 찍혀 50 m씩 빗나갑니다.", "가까이 보지만 높이가 없다"],
  ];
  eyes.forEach((e, i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.95, 3.9, 4.0, { icon: e[0], head: e[1], body: e[2], headSize: 15, bodySize: 12.5 });
    tag(s, e[3], x + 0.3, 5.5, false, 2.7);
  });
  source(s, "출처: 해양수산부 「해양폐기물 저감 대책」 현존량 구성 · 해양환경공단 국가 해안쓰레기 모니터링(2008~, 2개월 주기) · 업체 제보 및 라벨 자료(문갑도, 2026.09)");
  s.addNotes("세 가지 눈의 공통 결함: 무게를 못 본다. 위성은 3DLabs의 강점이므로 '넓게 보는 역할'로 존중하며 한계를 짚는다.");

  // 업체 데이터로 본 문제
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "01 현황과 문제" });
  s.addText("업체 라벨 42개: 기록 1.3 kg, 현실은 115~1,355 kg", { placeholder: "title" });
  sub(s, "문갑도 업체 라벨의 weight_kg는 실측이 아니라 '라벨 면적 × 재질 계수'입니다. 같은 면적에 현실적인 두께와 밀도를 주면 수십~수백 배 커집니다.");
  s.addImage({ path: img("fig_12_업체라벨_기록무게_vs_현실범위.jpg"), x: 0.6, y: 1.95, w: 7.9, h: 3.05, objectName: "업체 라벨 기록 무게 vs 현실 범위" });
  tb(s, "왼쪽: 업체 라벨 42개의 기록 무게 분포(합계 1.32 kg, 최대 0.25 kg). 오른쪽: 같은 면적의 현실적 범위(두께 2~35 cm × 재질 밀도, 로그 눈금).", { x: 0.6, y: 5.03, w: 7.9, h: 0.5, fontSize: 9.5, color: C.accent4, valign: "top" });
  card(s, 0.6, 5.55, 7.9, 0.95, { head: "원인은 하나: 높이(두께)가 없다", body: "3 cm/px 정사영상에는 DSM이 없어 부피를 잴 수 없습니다. 그래서 우리는 영상에서 3D를 만들어 높이를 직접 잽니다.", headSize: 12.5, bodySize: 11 });
  stat(s, 8.8, 1.95, 3.93, 1.5, { value: "0.018", unit: "kg", label: "1.54 m² 스티로폼 더미의 기록 무게", note: "현실적으로는 0.3~17 kg", color: C.accent2, valueSize: 30 });
  stat(s, 8.8, 3.6, 3.93, 1.5, { value: "50", unit: "m", label: "탐지 위치 오차 (업체 제보)", note: "드론 GPS를 쓰레기 위치로 기록 + 비스듬한 촬영", valueSize: 30 });
  card(s, 8.8, 5.25, 3.93, 1.25, { head: "업체 계수표 (kg/m²)", body: "스티로폼 0.012 · 로프·어망 0.024 · 플라스틱 0.020. 품목 수 × 평균무게 방식은 문헌에서도 약 40% 과대추정(Andriolo et al. 2024).", headSize: 12, bodySize: 10.5 });
  source(s, "출처: 업체 라벨 자료(문갑도 MGD, 42개)와 팀 분석(2026.09~10) · Andriolo et al. (2024) Marine Pollution Bulletin 202:116405");
  s.addNotes("업체 데이터로 문제를 숫자로 고정. 결론: 높이가 없으면 무게가 없다. 더 정확한 점 추정이 아니라 '3D 부피 + 얼마나 믿을 수 있는지'가 필요.");

  // ═════════ 02 솔루션 ═════════
  pres.addSection({ title: "02 솔루션" });
  s = pres.addSlide({ masterName: "SECTION", sectionTitle: "02 솔루션" });
  tb(s, "02", { x: 0.8, y: 1.9, w: 3, h: 1.0, fontSize: 60, bold: true, color: C.accent2 });
  s.addText("솔루션", { placeholder: "title" });
  s.addText("어디부터 날릴지, 어떤 거리에서 찍을지, 무엇이 어디에 얼마나 있는지, 그래서 트럭이 몇 대인지.", { placeholder: "body" });

  // 솔루션 개요: 파이프라인
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "02 솔루션" });
  s.addText("비행 한 번이 수거계획서 한 부가 된다", { placeholder: "title" });
  sub(s, "입력은 드론 영상(MP4)과 비행기록(SRT)뿐입니다. 비행은 사람이 하고, 나머지 7단계는 노트북 한 대가 자동으로 수행합니다.");
  const steps = [
    ["FaMapMarkedAlt", "핫스팟 경로", "과거 조사·집적 예측으로 배터리 안에서 많이 보는 경로"],
    ["FaPlane", "커버리지 비행", "고도 20 m 지그재그, 애매한 곳은 8 m 재방문"],
    ["FaSearchLocation", "탐지", "YOLO11-s, AI Hub 해안쓰레기 2~4 cm/px 학습"],
    ["FaCrosshairs", "위치", "3D 카메라 자세로 광선 교차 → GPS 정렬"],
    ["FaCubes", "부피", "SfM+MVS 점구름, SAM 2 마스크 투표, 높이지도"],
    ["FaRulerCombined", "무게 구간", "겉보기밀도 × 젖음·압축 계수, conformal 구간"],
    ["FaTruck", "수거계획", "정거장·마대·트럭·인력·경로 작업카드"],
  ];
  const sw = 1.66, sg = 0.075;
  steps.forEach((st, i) => {
    const x = 0.6 + i * (sw + sg);
    s.addShape(pres.ShapeType.roundRect, { x, y: 2.0, w: sw, h: 2.55, fill: { color: i === 6 ? H.dk2 : H.lt2 }, line: { color: i === 6 ? H.dk2 : H.lt2 }, rectRadius: 0.1, objectName: "step " + st[1] });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.53, y: 2.2, w: 0.6, h: 0.6, fill: { color: i === 6 ? H.accent2 : H.dk2 }, line: { color: i === 6 ? H.accent2 : H.dk2 }, objectName: "icon circle" });
    s.addImage({ data: ICON[st[0] + "_w"], x: x + 0.68, y: 2.35, w: 0.3, h: 0.3, objectName: "icon " + st[0] });
    tb(s, (i + 1) + ". " + st[1], { x: x + 0.1, y: 2.9, w: sw - 0.2, h: 0.35, fontSize: 12, bold: true, color: i === 6 ? C.background1 : C.text1, align: "center" });
    tb(s, st[2], { x: x + 0.12, y: 3.28, w: sw - 0.24, h: 1.2, fontSize: 10, color: i === 6 ? C.accent5 : C.accent4, align: "center", valign: "top" });
  });
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 4.75, w: 3.4, h: 0.55, fill: { color: H.accent6 }, line: { color: H.accent6 }, rectRadius: 0.1, objectName: "satellite input" });
  s.addImage({ data: ICON.FaSatellite_n, x: 0.78, y: 4.88, w: 0.3, h: 0.3, objectName: "icon satellite" });
  tb(s, "3DLabs 위성 ARD가 들어가는 자리: 집적 패치·변화 → 1단계 우선순위", { x: 1.18, y: 4.75, w: 2.8, h: 0.55, fontSize: 9.5, bold: true, color: C.text2, valign: "middle" });
  card(s, 0.6, 5.5, 6.0, 1.05, { head: "입력", body: "비행 영상(MP4) + 비행기록(SRT: 시각·GPS·고도). DJI 기본 기체. 1차 커버리지 1회 + 경계 물체만 2차 선회.", headSize: 12, bodySize: 11 });
  card(s, 6.73, 5.5, 6.0, 1.05, { head: "출력", body: "지도 핀(위치·오차반경) · 물체 목록(부피·무게 구간 CSV/GeoJSON) · 정거장별 작업카드(인력·마대·트럭·경로) · 2차 비행 경로(KMZ)", headSize: 12, bodySize: 11 });
  s.addNotes("7단계 파이프라인. 우리 기여는 5→7: 영상 하나로 3D 부피까지 가고, 수거계획을 바꾸는 불확실성만 줄인다.");

  // 촬영 거리
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "02 솔루션" });
  s.addText("촬영 거리는 물체 크기에서 역산했다", { placeholder: "title" });
  sub(s, "계획을 바꾸는 물체(어망·부표·스티로폼 더미, 수십 cm)는 20 m에서 잡히고, 부피를 재야 하는 물체는 3~8 m 선회에서 3D가 선다. 두 고도가 한 비행 안에 있습니다.");
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.95, w: 7.3, h: 3.15, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "gsd card" });
  tb(s, "고도별 지상 해상도와 물체 크기 (4K 3840 px, 24 mm 상당 화각 73.7° 기준 계산값)", { x: 0.85, y: 2.05, w: 6.9, h: 0.3, fontSize: 11.5, bold: true });
  s.addTable([
    [hdr("고도"), hdr("GSD (cm/px)"), hdr("2.5 cm 물체"), hdr("10 cm 물체"), hdr("40 cm 물체"), hdr("용도")],
    ["20 m", "0.78", "3 px", "13 px", "51 px", "1차 커버리지: 큰 물체 탐지"],
    ["8 m", "0.31", "8 px", "32 px", "128 px", "애매한 후보 재방문 확정"],
    ["3~4 m", "0.12~0.16", "16~21 px", "64~85 px", "250~340 px", "선회 3D 부피·무게"],
  ], { x: 0.85, y: 2.4, w: 6.8, colW: [0.75, 1.1, 1.0, 1.0, 1.05, 1.9], fontSize: 10, color: H.dk1, border: { type: "solid", color: "C9D6DE", pt: 0.5 }, fill: { color: H.lt1 }, rowH: 0.36, margin: 0.05, objectName: "gsd table" });
  tb(s, "문헌 권고 GSD 0.5~1.25 cm/px 안에 1차 비행(0.78)이 들어가고, 선회 비행은 그보다 4~6배 촘촘합니다. 매크로쓰레기 정의는 2.5 cm 이상, 해변 플라스틱 조각 중앙값은 약 9.7 cm입니다.", { x: 0.85, y: 4.25, w: 6.8, h: 0.8, fontSize: 10.5, color: C.accent4, valign: "top" });
  card(s, 8.2, 1.95, 4.53, 1.5, { head: "탐지: 권고 GSD 0.5~1.25 cm/px", body: "15개 드론 해안쓰레기 연구의 평균 고도 약 20 m. 10 m에서 5 cm 이상 물체 탐지 90% 초과, 2.5 cm는 73~81%.", headSize: 12.5, bodySize: 10.5 });
  card(s, 8.2, 3.6, 4.53, 1.5, { head: "3D 부피: 17 m·5 mm/px로 충분 (Kako 2020)", body: "우리는 더 가까운 3~8 m 선회. 1초 간격 3프레임 시차가 10 m에서 약 53°, 20 m에서 28°라 삼각측량·SfM이 안정적.", headSize: 12.5, bodySize: 10.5 });
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.3, w: 12.13, h: 1.2, fill: { color: H.dk2 }, line: { color: H.dk2 }, rectRadius: 0.12, objectName: "guide card" });
  s.addImage({ data: ICON.FaCamera_o, x: 0.95, y: 5.6, w: 0.5, h: 0.5, objectName: "icon camera" });
  tb(s, "선회 촬영 가이드 (실험으로 고정)", { x: 1.7, y: 5.42, w: 10.5, h: 0.35, fontSize: 13, bold: true, color: C.background1 });
  tb(s, "고도 3~4 m · 반경 3 m · 짐벌 45° 한 바퀴 + 수직 1장 · SRT 켜기 · 기준 물체 1개. 7 m 선회(0007)에서 무늬 없는 상자 윗면이 1.5~3.5 cm 높게 복원된 편향이 2 m(0010)에서는 −10%로 줄었습니다. 1차 커버리지는 20 m 통과 비행으로 충분합니다(야간 10분 비행에서 상자 30개 탐지·지도화).", { x: 1.7, y: 5.78, w: 10.8, h: 0.7, fontSize: 10.5, color: C.accent5, valign: "top" });
  refs(s, "근거: Andriolo, Topouzelis, van Emmerik et al. (2023) Marine Pollution Bulletin 195:115521 · Andriolo & Gonçalves (2022) Environmental Pollution 315:120370 · Kako, Morita & Taneda (2020) MPB 155:111127 · 팀 실험 0007·0010·0015", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("'왜 그 거리에서 찍나'에 대한 답. 탐지 권고 GSD와 3D 복원 조건을 동시에 만족하는 고도 두 단계. 숫자는 4K 24 mm 기준 계산값이며 실제 기체 스펙으로 확정 예정.");

  // 핫스팟 경로 (검증 수치)
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "02 솔루션" });
  s.addText("어디부터 날릴까: 몰리고, 다시 쌓이고, 과거로 짠 경로가 통한다", { placeholder: "title" });
  sub(s, "해안 전체를 매번 다 날 수 없습니다. 쓰레기는 소수 구간에 몰리고 치워도 다시 쌓이므로, 과거 조사로 '많고 중요한 곳'을 배터리 안에서 최대로 보는 경로를 짭니다.");
  s.addImage({ path: img("fig_hotspot_results.jpg"), x: 0.6, y: 1.95, w: 6.1, h: 4.47, objectName: "하와이·MDMAP 집적 검증" });
  stat2(s, 6.95, 1.95, 2.8, 1.45, { value: "75", unit: "%", label: "상위 10% 칸이 차지하는 비율", note: "하와이 2015 항공조사, 라벨 10,703개" });
  stat2(s, 9.93, 1.95, 2.8, 1.45, { value: "0.88", unit: "", label: "앞/뒤 기간 순위상관", note: "NOAA MDMAP 134곳 반복조사, 상위 20% 유지 74%" });
  stat2(s, 6.95, 3.52, 2.8, 1.45, { value: "61", unit: "% vs 36%", label: "예산 20%에서 다음 조사 쓰레기 커버", note: "텍사스 33곳, 앞 기간으로 계획 → 뒤 기간 채점", color: C.accent2 });
  stat2(s, 9.93, 3.52, 2.8, 1.45, { value: "69", unit: "%", label: "배터리 1개로 보는 비율", note: "몰로카이, 이륙 지점까지 알고리즘이 선택" });
  card(s, 6.95, 5.1, 5.78, 1.32, { head: "알고리즘: 오리엔티어링 문제", body: "구간 가치 = 기대 쓰레기량 × 중요도(어망·부표 5 … 조각 1) + 탐색 보너스. 삽입 휴리스틱 → 2-opt → 이륙 지점 선택 → 배터리별 반복. 미래를 안다고 가정한 상한과의 차이 최대 3.2%p.", headSize: 12.5, bodySize: 10.5 });
  refs(s, "자료: 하와이 항공 정사영상 칩 1,587장(Zenodo 8381113) · NOAA MDMAP 반복조사 · 팀 분석(hotspot/). 한국 검증은 국가 해안쓰레기 모니터링 정점 시계열로 같은 절차 적용 예정(1단계 로드맵).", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("핫스팟 우선의 세 근거(몰린다·다시 쌓인다·과거로 짠 경로가 통한다)와 드론 규모 시연. 모두 미국 공개 데이터이며 한국 검증은 로드맵 1단계.");

  // 한국 적용: 집적 예측 + 만입 해안
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "02 솔루션" });
  s.addText("한국 해안에 옮기기: 조류 집적 예측과 만입 해안", { placeholder: "title" });
  sub(s, "첫 조사 이력이 없는 해안은 조류·바람·하천 입자추적과 해안 형태(만입·풍향 노출)를 약한 사전값으로 쓰고, 조사 결과가 쌓이면 이력이 사전값을 대체합니다.");
  s.addImage({ path: img("hotspot_map_gyodong.jpg"), x: 0.6, y: 1.95, w: 5.4, h: 4.25, objectName: "교동도 집적 예상 지도" });
  tb(s, "교동도 집적 예상 구간(빨간 라인). 조석 연속방정식 조류 + 풍압 + 좌초·재부유, 100 m 격자 · 200,000 입자 · 30일.", { x: 0.6, y: 6.22, w: 5.4, h: 0.4, fontSize: 9, color: C.accent4 });
  s.addShape(pres.ShapeType.roundRect, { x: 6.3, y: 1.95, w: 6.43, h: 2.3, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "교동도 8방위 구간 좌초 밀도 점수 (섬 해안선 기준 상위 30%)", { x: 6.55, y: 2.05, w: 6.0, h: 0.3, fontSize: 11.5, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "점수", labels: ["서안", "북서안", "북안", "북동안"], values: [28.6, 24.5, 8.7, 5.4] }],
    chartBase({ x: 6.4, y: 2.35, w: 6.2, h: 1.85, barDir: "bar", valAxisMinVal: 0, valAxisMaxVal: 35, dataLabelFormatCode: "0", catAxisLabelFontSize: 10, catAxisOrientation: "maxMin", valAxisHidden: true, valGridLine: { style: "none" } }));
  card(s, 6.3, 4.4, 6.43, 2.1, { icon: "FaWater", head: "만입 해안이 더 모은다는 근거와 한계", body: "반폐쇄 하구만이 집적 핫스팟(Maiti et al. 2026), 헤드랜드로 막힌 포켓비치가 개방 해안보다 높은 집적(북사르데냐), 해안선 형태·바람이 집적을 지배(Critchell & Lambrechts 2016; Brabo et al. 2022). 단, 하와이에서는 무역풍 정면 1.6배도 섬마다 달라 조사 이력이 꼭 필요했습니다.", headSize: 12.5, bodySize: 10 });
  refs(s, "근거: Maiti et al. (2026) MPB 232:120031 · Critchell & Lambrechts (2016) Estuar. Coast. Shelf Sci. 171:111–122 · Brabo et al. (2022) MPB 174 · Dagestad et al. (2018) GMD 11:1405 · Onink et al. (2021) ERL 16:064053. 모식 조류·실측 검증 전.", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("한국 적용의 사전값: 조류 모델 + 해안 형태. 만입 해안 가설은 문헌 근거가 있으나 단일 변수로 쓰지 않고 이력으로 보정한다.");

  // 운용·시뮬레이터
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "02 솔루션" });
  s.addText("어떻게 날릴까: 비행은 사람, 나머지는 AI + 시뮬레이터", { placeholder: "title" });
  sub(s, "실기체(DJI Mini 5 Pro)는 SDK가 없어 자동비행이 안 됩니다. 그래서 업체 문갑도 정사영상을 가상 세계로 써서 커버리지·실시간 탐지·능동 재방문을 검증했습니다.");
  s.addImage({ path: img("wolmido_map.jpg"), x: 0.6, y: 1.95, w: 3.6, h: 4.4, objectName: "월미도 비행 시뮬레이션 지도" });
  tb(s, "실제 DEM 위 비행 시뮬(PyBullet), 경로 오차 ≤ 2.8 m", { x: 0.6, y: 6.38, w: 3.6, h: 0.3, fontSize: 9, color: C.accent4 });
  s.addShape(pres.ShapeType.roundRect, { x: 4.5, y: 1.95, w: 4.0, h: 2.6, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "능동 재방문 효과: 재현율 (문갑도 100×100 m, 라벨 7개)", { x: 4.75, y: 2.05, w: 3.6, h: 0.3, fontSize: 11.5, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "재현율", labels: ["커버리지만", "커버리지 + 재방문"], values: [0.71, 0.86] }],
    chartBase({ x: 4.6, y: 2.4, w: 3.8, h: 2.05, barDir: "col", valAxisMinVal: 0, valAxisMaxVal: 1, dataLabelFormatCode: "0.00", catAxisLabelFontSize: 10, valAxisLabelFormatCode: "0.0" }));
  stat(s, 8.73, 1.95, 4.0, 2.6, { value: "+697", unit: "m", label: "재방문으로 늘어난 비행거리", note: "20 m 커버리지 679 m → 8 m 재방문 25회 포함 1,718 m. 애매한 후보 25개 중 22개 기각·3개 확정.", color: C.accent2 });
  card(s, 4.5, 4.75, 8.23, 1.6, { head: "운용 구조", body: "핫스팟 경로를 KMZ 웨이포인트로 내보내 DJI Fly로 비행(실기체 확인 필요) → 영상+SRT 입력 → 노트북 한 대(RTX 4060 8 GB·RAM 16 GB)에서 탐지·3D·작업카드. 조밀 복원은 45분에서 3분 24초로 단축. 시뮬레이터는 월드·카메라·비행·탐지·지도·계획을 분리해 ROS 2/PX4로 이식 설계.", headSize: 12.5, bodySize: 11 });
  refs(s, "근거: Galceran & Carreras (2013) 커버리지 경로계획, Robot. Auton. Syst. 61(12):1258–1276 · Popović et al. (2020) 정보 경로계획(IPP), Auton. Robots 44:889–911 · 팀 sim_ortho 결과(figures/sim_aihub_*_summary.json)", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("IPP는 지도 전체의 불확실성을 줄이지만 우리는 수거계획이 바뀌는 불확실성만 줄인다. 재방문 25회 중 22회가 '한 프레임 우연 탐지' 기각.");

  // 탐지·위치
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "02 솔루션" });
  s.addText("무엇이 어디에: 운용 고도에 맞춘 탐지와 3D 위치", { placeholder: "title" });
  sub(s, "AI Hub 해안쓰레기 사진 1.2만 장을 운용 고도의 해상도(2~4 cm/px)로 축소해 학습했고, 위치는 3D 카메라 자세로 광선을 쏴서 GPS에 정렬합니다.");
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.95, w: 5.6, h: 2.35, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "탐지 재현율, 문갑도 업체 칩 48장 (정답 47)", { x: 0.85, y: 2.05, w: 5.2, h: 0.3, fontSize: 11.5, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "재현율", labels: ["공개 UAVVaste 모델", "AI Hub 거리별 학습 모델"], values: [0.28, 0.72] }],
    chartBase({ x: 0.7, y: 2.4, w: 5.4, h: 1.85, barDir: "bar", valAxisMinVal: 0, valAxisMaxVal: 1, dataLabelFormatCode: "0.00", catAxisLabelFontSize: 10, catAxisOrientation: "maxMin", valAxisHidden: true, valGridLine: { style: "none" } }));
  card(s, 0.6, 4.45, 5.6, 2.05, { head: "같은 모델이 다른 해안에서도", body: "하와이 항공 정사영상 420칩: 재학습 없이 0.24 → 현지 사진 10분 미세조정 0.58 → 8클래스·1024 px 0.69(AP50 0.62). 야간 10분 영상의 종이상자 30개는 개방형 탐지(YOLO-World)에 이름만 추가해 잡았습니다.", headSize: 13, bodySize: 11 });
  s.addImage({ path: img("fig_16_0015_야간_상자30개_지도.jpg"), x: 6.5, y: 1.95, w: 2.55, h: 2.9, objectName: "0015 야간 상자 30개 지도" });
  tb(s, "야간 10분 통과 비행(0015): 상자 30개 자동 지도화, 3D 뼈대 25/25 구간 성공", { x: 6.5, y: 4.9, w: 2.55, h: 0.45, fontSize: 9, color: C.accent4, valign: "top" });
  s.addShape(pres.ShapeType.roundRect, { x: 9.3, y: 1.95, w: 3.43, h: 2.9, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "table card" });
  tb(s, "위치 정확도 (실기체)", { x: 9.55, y: 2.05, w: 3.0, h: 0.3, fontSize: 11.5, bold: true });
  s.addTable([
    [hdr("영상"), hdr("3D ↔ GPS 잔차")],
    ["0007 송도 선회 7 m", "1.16 m"],
    ["0010 골목 왕복 2 m", "8.07 → 0.51 m*"],
    ["합성 7개 시나리오", "0.01~0.11 m"],
    ["r95 (GPS 1σ 2.5 m)", "5.2 m"],
  ], { x: 9.55, y: 2.4, w: 2.95, colW: [1.7, 1.25], fontSize: 9.5, color: H.dk1, border: { type: "solid", color: "C9D6DE", pt: 0.5 }, fill: { color: H.lt1 }, rowH: 0.34, margin: 0.04, objectName: "position accuracy" });
  tb(s, "* SRT 고도가 틀린 경우 GPS 경로로 축척을 자동 선택", { x: 9.55, y: 4.12, w: 3.0, h: 0.5, fontSize: 9, color: C.accent4, valign: "top" });
  card(s, 6.5, 5.4, 6.23, 1.12, { head: "위치 50 m 오차는 이렇게 사라진다", body: "드론 GPS 대신 3D 카메라 자세로 탐지 박스 → 광선 → 지면 교차. 호버링(시차 5° 미만)은 평면 교차로 자동 복귀, 물체마다 오차반경(r95) 기록.", headSize: 12, bodySize: 10 });
  refs(s, "근거: Martin et al. (2018) MPB 131:662–673 · Fallati et al. (2019) STOTEN 693:133581 · Hartley & Sturm (1997) CVIU 68(2):146–157 · 팀 교차평가(figures/cross_eval.json), 삼각측량 패치 docs/삼각측량_위치보정.md", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("운용 고도 GSD에 맞춘 학습셋이 차별점(0.28→0.72). 위치는 1장의 50 m가 GPS 자체 수준(1 m대)으로.");

  // 부피·무게
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "02 솔루션" });
  s.addText("얼마나 무거운가: 3D 부피 × 겉보기밀도, 그리고 구간", { placeholder: "title" });
  sub(s, "핵심 차별점. SAM 2 마스크를 여러 프레임에서 투표해 점구름에서 물체 점만 남기고, 지역 바닥 평면 기준 높이지도로 부피를 냅니다. 영상 하나로 정사영상·DSM 없이 끝납니다.");
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.95, w: 5.4, h: 4.45, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "크기 아는 상자 3개의 부피 오차 (실측 대비)", { x: 0.85, y: 2.05, w: 5, h: 0.3, fontSize: 11.5, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "부피 오차(%)", labels: ["0007 작은 상자 (7 m 선회)", "0007 큰 상자 (7 m 선회)", "0010 키 큰 상자 (2 m 왕복)"], values: [19, 20, -10] }],
    chartBase({ x: 0.7, y: 2.4, w: 5.2, h: 2.5, barDir: "col", valAxisMinVal: -30, valAxisMaxVal: 30, dataLabelFormatCode: "+0;-0", catAxisLabelFontSize: 9, valAxisLabelFormatCode: "0" }));
  s.addImage({ path: img("fig_13_0007_조밀_큰상자_마스크.jpg"), x: 0.85, y: 5.0, w: 4.9, h: 1.22, objectName: "0007 큰 상자 SAM 마스크 투표" });
  tb(s, "0007 큰 상자 32.4 L → 3D 38.8 L. 업체 방식은 같은 상자에서 기준의 1/112·1/180.", { x: 0.85, y: 6.22, w: 4.9, h: 0.2, fontSize: 8.5, color: C.accent4 });
  card(s, 6.3, 1.95, 6.43, 1.45, { head: "부피: SAM 2 투표 + 지역 바닥 평면 + 높이지도", body: "조밀 점 243만 개 중 24프레임 마스크 일치율 70% 이상인 점만. 바닥점(<3 cm)·뒤집힌 카메라 포즈 자동 제외. 볼록껍질은 +60% 과대라 폐기.", headSize: 12.5, bodySize: 10.5 });
  card(s, 6.3, 3.55, 6.43, 1.45, { head: "무게: 겉보기밀도 × 젖음·압축 계수 → 구간", body: "스티로폼 20~25, 플라스틱 60, 어망·로프 100~400 kg/m³에 젖음·마대 압축 계수. 실측 30개가 모이면 conformal 예측구간으로 교체(코드 완료), 지금은 ×/÷2 구간.", headSize: 12.5, bodySize: 10.5 });
  card(s, 6.3, 5.15, 6.43, 1.3, { head: "재방문 규칙: 계획을 바꾸는 불확실성만", body: "구간 상한이 1인 운반 한계 23 kg(NIOSH)·마대·트럭 적재 경계를 넘나드는 물체만 2차 선회. 묻힘 의심(면적 넓고 높이 없음) 태그.", headSize: 12.5, bodySize: 10.5 });
  refs(s, "근거: Westoby et al. (2012) SfM, Geomorphology 179:300–314 · Kako, Morita & Taneda (2020) MPB 155:111127 · Angelopoulos & Bates (2023) Found. Trends ML 16(4):494–591 · 팀 결과 figures/0007_objvol_v2.json, 11_업체방식_vs_3D", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("부피→무게→구간. 무게 실측은 아직 없어 기준값이 '정답 부피 × 가정 밀도'임을 질문 받으면 솔직히: 저울 실측이 로드맵 1단계.");

  // 수거계획: 니하우 실제 산출
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "02 솔루션" });
  s.addText("수거계획: 니하우 섬 해안 전체에서 나온 실제 산출", { placeholder: "title" });
  sub(s, "하와이 니하우 섬 항공 정사영상 칩 553장(2 cm/px)에 같은 파이프라인을 돌린 결과. 2D라 무게는 면적 × 두께 범위의 구간입니다.");
  s.addImage({ path: img("fig_18_하와이_niihau_지도_수거계획.jpg"), x: 0.6, y: 1.95, w: 7.3, h: 3.22, objectName: "니하우 지도·수거계획" });
  tb(s, "왼쪽: 섬 해안 물체 5,476개와 수거 경로 71.9 km. 오른쪽: 가장 밀집한 120×120 m 구간(423개), 점 색 = 재질.", { x: 0.6, y: 5.2, w: 7.3, h: 0.35, fontSize: 9, color: C.accent4 });
  const kp = [["탐지 물체", "5,476", "개", "플라스틱 3,966 · 부표 477 · 페트병 439 · 어망 214"], ["무게 예측구간", "7.9–33.6", "t", "추정 13.7 t · 업체 방식이면 69 kg"], ["정거장 · 경로", "331 · 71.9", "km", "정거장 반경 기반 클러스터, 2-opt"]];
  kp.forEach((k, i) => {
    const y = 1.95 + i * 1.1;
    s.addShape(pres.ShapeType.roundRect, { x: 8.2, y, w: 4.53, h: 1.0, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.1, shadow: shadow(), objectName: "kpi " + k[0] });
    tb(s, k[0], { x: 8.42, y: y + 0.08, w: 4.1, h: 0.25, fontSize: 10, color: C.accent4 });
    s.addText([{ text: k[1], options: { fontSize: 22, bold: true, color: i === 1 ? C.accent2 : C.text2 } }, { text: " " + k[2], options: { fontSize: 11, bold: true, color: C.accent4 } }], { x: 8.42, y: y + 0.3, w: 4.1, h: 0.42, isTextBox: true, margin: 0, valign: "middle" });
    tb(s, k[3], { x: 8.42, y: y + 0.72, w: 4.1, h: 0.25, fontSize: 9, color: C.accent4 });
  });
  const outs = [["마대", "1,082 장", "압축 후 부피 기준(무게 기준 687)"], ["1톤 트럭", "37 대", "부피 기준(무게 기준 14)"], ["인력 구분", "1인 5,294 · 2인 138 · 장비 44", "23 kg 규칙 · 묻힘 의심"]];
  outs.forEach((o, i) => {
    const x = 0.6 + i * 4.1;
    s.addShape(pres.ShapeType.roundRect, { x, y: 5.6, w: 3.9, h: 0.9, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.1, shadow: shadow(), objectName: "output " + o[0] });
    tb(s, o[0], { x: x + 0.2, y: 5.65, w: 3.5, h: 0.25, fontSize: 9.5, color: C.accent4 });
    tb(s, o[1], { x: x + 0.2, y: 5.88, w: 3.6, h: 0.35, fontSize: i === 2 ? 12.5 : 16, bold: true, color: C.text2 });
    tb(s, o[2], { x: x + 0.2, y: 6.22, w: 3.6, h: 0.25, fontSize: 8.5, color: C.accent4 });
  });
  source(s, "자료: 하와이 항공 정사영상(Zenodo 8381113, CC-BY) · 팀 결과 figures/hawaii_niihau_ft_summary.json · 송도 0007 작업카드: 정거장 1, 0.83 kg(상한 1.67), 1인×2, 마대 1, 트럭 1, 경로 20 m");
  s.addNotes("제품 출력의 실제 모습. 2D만으로도 계획이 나오지만 구간 폭이 4배(7.9~33.6 t)라 '그래서 3D가 필요하다'로 연결.");

  // 수거 경로
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "02 솔루션" });
  s.addText("수거 경로: 사람이 갈 수 있는 길로, 지자체 조건에 맞춰", { placeholder: "title" });
  sub(s, "정거장별 인력·마대·트럭을 계산한 뒤 집하장에서 출발하는 순회 경로(최근접 이웃 + 2-opt)를 냅니다. 접근로·로드뷰 반영은 설계 단계입니다.", 10.4);
  tag(s, "일부 설계 중", 11.18, 1.4, true);
  const rt = [
    ["FaCity", "지자체 조건 입력", "인원·차량(트럭 적재량)·작업 시간·마대 규격. 지자체마다 다르므로 설정값으로 둡니다."],
    ["FaWalking", "통행 가능 구역 마스킹", "해안 접근로·로드뷰 기반 진입 지점. 해변은 차량 진입이 제한되므로 하역 지점을 따로 둡니다. (설계 중)"],
    ["FaRoute", "정거장 순회 경로", "물체 위치·무게 구간·집하장을 넣어 정거장별 동선과 왕복 횟수를 계산합니다. 니하우 331 정거장·71.9 km. (구현)"],
    ["FaClipboardList", "작업카드 · 대시보드", "정거장별 HTML 카드(썸네일·위경도·추정/최대 kg·인력·휴대폰 길찾기). 현장 '못 찾음·수거 완료' 체크로 다음 비행을 보정합니다."],
  ];
  rt.forEach((r, i) => card(s, 0.6 + i * 3.075, 1.95, 2.9, 3.3, { icon: r[0], head: r[1], body: r[2], headSize: 13.5, bodySize: 11.5 }));
  card(s, 0.6, 5.45, 12.13, 1.0, { head: "왜 드론 단계와 분리하는가", body: "드론은 공중에서 '어디에 얼마나'를 재고, 수거 동선은 지상의 제약(접근로·적재·인원)을 받습니다. 두 마스킹이 다르므로 같은 지도 위에서 계층을 나눠 둡니다.", headSize: 12.5, bodySize: 11 });
  s.addNotes("plan.py·report.py는 구현됨. 접근로 마스킹과 팀 대시보드 연결은 설계 단계로 정직하게 표시.");

  // ═════════ 03 검증 ═════════
  pres.addSection({ title: "03 검증" });
  s = pres.addSlide({ masterName: "SECTION", sectionTitle: "03 검증" });
  tb(s, "03", { x: 0.8, y: 1.9, w: 3, h: 1.0, fontSize: 60, bold: true, color: C.accent2 });
  s.addText("검증", { placeholder: "title" });
  s.addText("상자 3개, 영상 3편, 공개 해안 데이터 2종. 결과가 없는 항목은 '진행 중', 가정은 '가정'이라고 썼습니다.", { placeholder: "body" });

  // 검증 요약표
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "03 검증" });
  s.addText("검증 요약: 가설 · 설계 · 결과", { placeholder: "title" });
  sub(s, "완료 7건, 진행 중 3건. 수치는 모두 저장소의 로그·JSON에서 재현됩니다.");
  const okc = { text: "완료", options: { bold: true, color: "0A7A2F", fontSize: 9.5, align: "center" } };
  const runc = { text: "진행 중", options: { bold: true, color: "B35A00", fontSize: 9.5, align: "center" } };
  s.addTable([
    [hdr("실험"), hdr("가설"), hdr("설계"), hdr("결과"), hdr("상태")],
    ["A 부피", "영상 3D로 잰 부피가 실측과 ±20% 안에 든다", "크기 아는 상자 3개, 7 m 선회(0007)·2 m 왕복(0010)", "+19% / +20% / −10%. 업체 방식은 1/112·1/180", okc],
    ["B 위치", "3D 자세로 계산한 위치가 GPS와 수 m 안", "0007·0010 실기체 + 합성 7개 시나리오", "1.16 m · 8.07→0.51 m(축척 자동) · 합성 0.01~0.11 m", okc],
    ["C 탐지", "운용 고도 GSD로 학습하면 현장 재현율이 오른다", "문갑도 칩 48·하와이 420칩·튀니지 179장 교차평가", "문갑도 0.28→0.72 · 하와이 0.24→0.69(미세조정)", okc],
    ["D 재방문", "애매한 후보만 재방문하면 짧은 추가 비행으로 재현율↑", "문갑도 정사영상 가상비행 100×100 m, 라벨 7개", "0.71→0.86, +697 m (25회 중 22회 기각)", okc],
    ["E 야간 통과", "통과 비행만으로 탐지·지도·3D 뼈대가 된다", "0015 야간 10분, 4K 60 fps, 상자 ~28개", "탐지 30개 · 3D 뼈대 25/25 · 부피는 선회 필요", okc],
    ["F 핫스팟", "몰리고, 다시 쌓이고, 과거로 짠 경로가 통한다", "하와이 2015 항공조사 · NOAA MDMAP 134곳 · 텍사스 33곳", "상위 10% 칸 75% · 순위상관 0.88 · 61% vs 36%", okc],
    ["G 해안 적용", "같은 파이프라인이 다른 해안에서 수거계획을 낸다", "니하우 섬 칩 553장, 10분 미세조정", "5,476개 · 7.9~33.6 t · 마대 1,082 · 트럭 37", okc],
    ["무게 실측", "부피 × 밀도 무게가 저울 무게와 맞는다", "상자 3개 + 문갑도 실측 30개 저울", "기준값 교체 전 (지금은 정답 부피 × 가정 밀도)", runc],
    ["한국 핫스팟", "국내 정점 시계열에서도 순위상관·커버율이 재현된다", "국가 해안쓰레기 모니터링 정점(2008~) 앞/뒤 기간", "자료 요청 단계", runc],
    ["예측구간", "종류별 밀도 분포로 포함확률 90% 구간", "실측 쌍 30개 이상, split-conformal", "코드 완료, 데이터 대기", runc],
  ], { x: 0.6, y: 1.95, w: 12.13, colW: [1.25, 3.3, 3.3, 3.35, 0.93], fontSize: 9.5, color: H.dk1, border: { type: "solid", color: "C9D6DE", pt: 0.5 }, fill: { color: H.lt1 }, rowH: 0.41, margin: 0.04, valign: "middle", objectName: "validation summary" });
  source(s, "저장소: dohun415/aerodrone_hackathon (docs/파이프라인_결과정리.md, figures/*.json, hotspot/) · HSR2M/hsr1m (island_drone_sim, 삼각측량 패치, incheon_debris_sim)");
  s.addNotes("한 표로 신뢰성. 결과 없는 항목을 숨기지 않는 것이 이 장의 메시지.");

  // 한계와 대응
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "03 검증" });
  s.addText("정직한 한계와 대응", { placeholder: "title" });
  sub(s, "질문 받을 것을 먼저 적었습니다. 각각 어떻게 줄이는지까지.");
  const lim = [
    ["FaWeightHanging", "무게 실측이 아직 없다", "부피는 검증됐지만 무게 기준값은 '정답 부피 × 가정 밀도'입니다. 상자 3개 저울 실측(1분)과 문갑도 실측 30개로 밀도·구간을 교체합니다."],
    ["FaMapMarkerAlt", "절대 위치의 바닥은 GPS", "드론 GPS가 2 m 밀리면 모든 광선이 같이 밀립니다(r95 ≈ 5 m). RTK, 좌표를 아는 기준 표식, 또는 정사영상↔위성(SkySat) 정합(인라이어 85%, 5~8 m)으로 보정합니다."],
    ["FaCamera", "7 m 선회의 윗면 편향", "무늬 없는 상자 윗면이 1.5~3.5 cm 높게 복원되고 마스크가 그림자를 포함해 +13~28%. 3~4 m 선회 + 수직 1장 가이드로 줄이며, 3·5·7 m 통제 실험이 남았습니다."],
    ["FaWater", "핫스팟·조류는 한국 미검증", "핫스팟 수치는 미국 공개 데이터, 조류는 조석 연속방정식 모델입니다. 국가 해안쓰레기 모니터링 정점 시계열과 KHOA·KOOS 실측 해류로 같은 절차를 돌립니다."],
  ];
  lim.forEach((l, i) => card(s, 0.6 + i * 3.075, 1.95, 2.9, 4.0, { icon: l[0], head: l[1], body: l[2], headSize: 14, bodySize: 12 }));
  s.addNotes("한계를 먼저 말하면 질문이 줄어든다. 각 항목에 대응책이 붙어 있다.");

  // ═════════ 04 제안 ═════════
  pres.addSection({ title: "04 제안" });
  s = pres.addSlide({ masterName: "SECTION", sectionTitle: "04 제안" });
  tb(s, "04", { x: 0.8, y: 1.9, w: 3, h: 1.0, fontSize: 60, bold: true, color: C.accent2 });
  s.addText("3DLabs와의 결합 제안", { placeholder: "title" });
  s.addText("위성이 넓게 보고, 드론이 자세히 재고, 지자체가 배차합니다.", { placeholder: "body" });

  // 결합 구조
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "04 제안" });
  s.addText("위성이 넓게 보고, 드론이 자세히 재고, 지자체가 배차한다", { placeholder: "title" });
  sub(s, "3DLabs의 위성 지상국·ARD 플랫폼 위에 드론 측정 계층을 얹어, 활용 분야(도시·산림·항만·수체변화)에 '해안쓰레기 수거계획'을 추가합니다.");
  const roles = [
    ["FaSatellite", "3DLabs · 위성 계층", ["위성 지상국 운영, 1:5,000 도엽 정사영상·ARD(Analysis Ready Data) 생산", "광역 집적 패치 탐지와 시계열 변화 → 핫스팟 경로의 사전값", "B2G 공급 채널(공공 활용 플랫폼)"], H.dk2, true],
    ["FaPlane", "붕붕이 · 드론 계층", ["핫스팟 경로, 커버리지·재방문 비행, 탐지·3D 위치·SfM 부피", "무게 예측구간과 23 kg·마대·트럭 경계 재방문 규칙", "정거장별 작업카드(인력·마대·트럭·경로), 대시보드"], "124A6E", true],
    ["FaUsers", "고객 · 지자체 계층", ["시군 해양수산 부서: 예산·배차", "수거 용역업체: 동선·인원", "해양환경공단: 반복 모니터링 데이터(핫스팟 이력)"], H.lt2, false],
  ];
  roles.forEach((r, i) => {
    const x = 0.6 + i * 4.1;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.95, w: 3.9, h: 3.35, fill: { color: r[3] }, line: { color: r[3] }, rectRadius: 0.12, shadow: r[4] ? undefined : shadow(), objectName: "role " + r[1] });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: 2.25, w: 0.62, h: 0.62, fill: { color: r[4] ? H.accent2 : H.dk2 }, line: { color: r[4] ? H.accent2 : H.dk2 }, objectName: "icon circle" });
    s.addImage({ data: ICON[r[0] + "_w"], x: x + 0.45, y: 2.4, w: 0.32, h: 0.32, objectName: "icon " + r[0] });
    tb(s, r[1], { x: x + 0.3, y: 3.05, w: 3.3, h: 0.4, fontSize: 14.5, bold: true, color: r[4] ? C.background1 : C.text1 });
    bullets(s, r[2], { x: x + 0.3, y: 3.5, w: 3.3, h: 1.7, fontSize: 11, color: r[4] ? C.accent5 : C.text1 });
    if (i < 2) { s.addShape(pres.ShapeType.rightArrow, { x: x + 3.92, y: 3.35, w: 0.17, h: 0.4, fill: { color: H.accent2 }, line: { color: H.accent2 }, objectName: "arrow" }); }
  });
  tb(s, "시장 신호", { x: 0.6, y: 5.5, w: 3, h: 0.3, fontSize: 11.5, bold: true });
  const sig = [["전남도 2026년 해양쓰레기 저감 441억 원, AI·드론 관리 강화", "뉴스핌 2026.03"], ["해양환경공단 8개 무역항 드론 모니터링, 드론 탐지+AI 판독+수상로봇 'KOEM-ARK' 현장 운용", "이투데이 · 뉴스핌 2026.07"], ["전국 해양폐기물 처리 예산 1,114억 원(2026), 5년 수거량 65.6만 t", "해양수산부 2026.09"]];
  sig.forEach((g, i) => {
    const x = 0.6 + i * 4.1;
    s.addShape(pres.ShapeType.roundRect, { x, y: 5.85, w: 3.9, h: 0.72, fill: { color: H.accent6 }, line: { color: H.accent6 }, rectRadius: 0.1, objectName: "signal " + i });
    tb(s, g[0], { x: x + 0.18, y: 5.9, w: 3.55, h: 0.45, fontSize: 9.5, bold: true, color: C.text2, valign: "top" });
    tb(s, g[1], { x: x + 0.18, y: 6.33, w: 3.55, h: 0.2, fontSize: 8, color: C.accent4 });
  });
  source(s, "3DLabs 소개: 인하대 공간정보공학 스핀오프(2011), 위성 지상국·전처리·ARD·드론 영상처리(회사 소개) · 전남도 441억(뉴스핌 2026.03.22) · KOEM 드론·KOEM-ARK(이투데이, 뉴스핌 2026.07.07)");
  s.addNotes("상대의 강점(위성·ARD·B2G 채널)을 앞에 두고 우리를 계층으로 끼운다. 시장 신호 세 개는 모두 2026년.");

  // 로드맵
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "04 제안" });
  s.addText("공동 실증 로드맵 (제안)", { placeholder: "title" });
  sub(s, "세 단계, 각 단계의 끝에 숫자로 확인할 수 있는 결과를 두었습니다.");
  const ph = [
    ["1", "2026 4분기", "데이터 보정", ["상자 3개 + 문갑도 실측 30개 저울 → 밀도·예측구간(포함확률 90%) 교체", "국가 해안쓰레기 모니터링 정점 시계열로 핫스팟 순위상관·커버율 재현", "위성 ARD 샘플 2~3개 해안으로 집적 사전값 vs 실제 패치 비교"], "산출: 실측 기반 무게 구간, 한국 핫스팟 검증 보고"],
    ["2", "2027 상반기", "지자체 시범", ["시군 1곳(인천 옹진 또는 전남 도서) 해안 3구간, 2회 이상 반복 비행", "실측 해류(KHOA·KOOS) 교체, RTK 또는 기준 표식 도입", "비행 1회 → 작업카드 → 실제 수거량·마대·트럭과 대조"], "산출: 추정 vs 실제 수거량 오차, 마대·트럭 적중률"],
    ["3", "2027 하반기", "위성 결합 · 상용", ["위성 변화 탐지로 비행 시점·구간 자동 추천", "KOEM 2개월 모니터링과 연동한 반복 조사 상품(이력 갱신)", "B2G 플랫폼 활용 분야에 '해안쓰레기' 추가"], "산출: 구독형 수거계획 서비스, 레퍼런스 1곳"],
  ];
  ph.forEach((p, i) => {
    const x = 0.6 + i * 4.1;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.95, w: 3.9, h: 4.45, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "phase " + p[0] });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: 2.25, w: 0.62, h: 0.62, fill: { color: i === 2 ? H.accent2 : H.dk2 }, line: { color: i === 2 ? H.accent2 : H.dk2 }, objectName: "phase circle" });
    tb(s, p[0], { x: x + 0.3, y: 2.25, w: 0.62, h: 0.62, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle" });
    tb(s, p[1], { x: x + 1.1, y: 2.27, w: 2.5, h: 0.28, fontSize: 10, color: C.accent4 });
    tb(s, p[2], { x: x + 1.1, y: 2.52, w: 2.5, h: 0.4, fontSize: 15, bold: true });
    bullets(s, p[3], { x: x + 0.3, y: 3.15, w: 3.3, h: 2.2, fontSize: 11 });
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.3, y: 5.45, w: 3.3, h: 0.75, fill: { color: H.lt2 }, line: { color: H.lt2 }, rectRadius: 0.08, objectName: "phase output" });
    tb(s, p[4], { x: x + 0.45, y: 5.45, w: 3.0, h: 0.75, fontSize: 10, bold: true, color: C.text2, valign: "middle" });
  });
  s.addNotes("일정은 제안이며 상대의 위성 ARD 제공 시점에 맞춰 조정.");

  // 요청사항·맺음
  s = pres.addSlide({ masterName: "DARK_CONTENT", sectionTitle: "04 제안" });
  s.addText("함께 검증하고 싶은 것", { placeholder: "title" });
  tb(s, "세 가지를 요청드립니다. 모두 1단계(2026 4분기) 안에 결과를 숫자로 돌려드릴 수 있는 범위입니다.", { x: 0.6, y: 1.32, w: 12.1, h: 0.45, fontSize: 14, color: C.accent5 });
  const asks = [
    ["FaDatabase", "위성 ARD 샘플", "대상 해안 2~3곳(인천·강화 도서 또는 전남 도서)의 정사영상·시계열. 집적 사전값과 실제 패치를 대조하고 핫스팟 경로의 입력으로 씁니다."],
    ["FaHandshake", "시범 지자체 소개", "B2G 채널로 연결된 시군 1곳. 비행 1회로 작업카드를 내고 실제 수거량·마대·트럭과 대조합니다."],
    ["FaLayerGroup", "데이터 연동 규격 협의", "ARD → 핫스팟 사전값 입력, 드론 결과(GeoJSON·CSV·작업카드) → 플랫폼 활용 분야 등록. 양방향 포맷을 먼저 맞춥니다."],
  ];
  asks.forEach((a, i) => card(s, 0.6 + i * 4.1, 1.95, 3.9, 3.0, { icon: a[0], head: a[1], body: a[2], dark: true, headSize: 15, bodySize: 12 }));
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.2, w: 12.13, h: 1.25, fill: { color: H.accent2 }, line: { color: H.accent2 }, rectRadius: 0.12, objectName: "closing" });
  tb(s, "추정이 틀리면 배차가 틀린다.  위성이 넓게 보고, 드론이 자세히 재면, 지자체는 맞게 배차할 수 있습니다.", { x: 0.95, y: 5.2, w: 11.4, h: 0.8, fontSize: 17, bold: true, color: C.background1, valign: "middle" });
  tb(s, "드론대장 붕붕이 · 저장소 dohun415/aerodrone_hackathon, HSR2M/hsr1m · 발표 사이트: 한 페이지 스크롤 버전 별도 제공", { x: 0.95, y: 5.95, w: 11.4, h: 0.4, fontSize: 10.5, color: C.background1 });
  s.addNotes("요청 3개를 명확히. 마지막 문장은 표지 문장의 반복.");

  const out = path.join(__dirname, "붕붕이_3DLabs_제안.pptx");
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("written", out);
})().catch((e) => { console.error(e); process.exit(1); });
