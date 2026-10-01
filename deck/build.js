// 드론대장 붕붕이 × 3DLabs 제안 덱 — pptxgenjs 구조화 덱
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
  const W = 13.333, SH = 7.5;
  const ICON = {};
  for (const n of ["FaExclamationTriangle", "FaSatellite", "FaSearchLocation", "FaCubes", "FaRoute", "FaTruck", "FaChartBar", "FaWater",
    "FaMapMarkedAlt", "FaBalanceScale", "FaUsers", "FaCheckCircle", "FaFlask", "FaHandshake", "FaEye", "FaCamera", "FaWind", "FaCoins",
    "FaClipboardList", "FaPlane", "FaLayerGroup", "FaRulerCombined", "FaCrosshairs", "FaWalking", "FaSun", "FaBoxOpen", "FaDatabase", "FaMapMarkerAlt", "FaBullseye", "FaCalendarAlt", "FaCity", "FaBan"]) {
    ICON[n + "_w"] = await icon(n, "FFFFFF");
    ICON[n + "_n"] = await icon(n, H.dk2);
    ICON[n + "_o"] = await icon(n, H.accent2);
  }

  // ───────── 레이아웃 ─────────
  const footer = (dark) => [
    { text: "드론대장 붕붕이 · 3DLabs 제안 · 2026.10", options: { x: 0.6, y: 7.02, w: 6, h: 0.3, fontSize: 9, color: dark ? C.accent4 : C.accent4, margin: 0, isTextBox: true } },
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
  function bullets(slide, items, o) {
    const arr = items.map((t, i) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, paraSpaceAfter: 6 } }));
    slide.addText(arr, Object.assign({ isTextBox: true, fontSize: 12.5, color: C.text1, valign: "top", margin: 0 }, o));
  }
  function refs(slide, text, x, y, w, h, dark) {
    tb(slide, text, { x, y, w, h, fontSize: 9.5, italic: true, color: dark ? C.accent5 : C.accent4, valign: "top", objectName: "refs" });
  }
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
  s.addText("드론 한 번 비행으로 구간별 무게와 위치를 예측구간과 함께 내고,\n수거계획을 실제로 바꾸는 물체만 다시 날아 계획을 확정합니다.", { placeholder: "body" });
  tb(s, "드론대장 붕붕이  ·  3DLabs 제안  ·  2026. 10", { x: 0.7, y: 6.5, w: 7.2, h: 0.4, fontSize: 11, color: C.accent5 });
  s.addNotes("표지. 한 문장: 수거계획의 입력(무게·위치)이 지금은 수십 배씩 틀리고, 우리는 그 입력을 예측구간과 함께 제공한다.");

  // ═════════ 한 장 요약 ═════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "표지" });
  s.addText("한 장 요약", { placeholder: "title" });
  sub(s, "문제 → 해법 → 검증 → 제안. 새로 발명한 알고리즘은 없고, 검증된 방법을 수거계획 하나로 이었습니다.");
  const sum = [
    ["FaExclamationTriangle", "문제: 추정이 곧 예산이다", "해양쓰레기 수거량은 5년간 19.8% 늘었고 90%를 지자체가 치웁니다. 같은 42개 물체가 계수 방식 1.3 kg, 3D 부피 기준 101 kg. 위치는 50 m씩 빗나갑니다."],
    ["FaRoute", "해법: 비행 한 번 = 수거계획서 한 부", "조류 집적 예측으로 구간 우선순위 → 커버리지 비행 → 탐지·삼각측량 → SfM 부피 × 겉보기밀도 → 무게 예측구간 → 경계에 걸린 물체만 2차 비행 → 마대·트럭·인원."],
    ["FaFlask", "검증: 세 실험과 두 시뮬레이션", "선회 비행 부피 오차 −3%/+19% (경사통과는 실패), 3D↔GPS 잔차 1.16 m, 재방문으로 재현율 0.71→0.86 (+697 m). 지형 비행·집적 예측 시뮬레이션 포함."],
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
  tb(s, "남는 트럭과 모자라는 트럭이 동시에 생긴다", { x: 1.95, y: 4.55, w: 10.5, h: 0.45, fontSize: 16, bold: true, color: C.background1 });
  tb(s, "무게가 틀리면 마대·트럭 수가 틀리고, 위치가 틀리면 동선·인원이 틀립니다. 같은 일이 2026년 8월에도 반복됐습니다. 광복절 연휴 폭우로 경남 연안에 1,180 t이 유입됐고 통영·거제가 80%를 차지했습니다. 작은 지자체일수록 수거 전에 재는 것이 예산 그 자체입니다.",
    { x: 1.95, y: 5.05, w: 10.5, h: 1.2, fontSize: 12.5, color: C.accent5, valign: "top" });
  source(s, "출처: 뉴시스 2023.07.25 「거제 해양쓰레기 437t 추정·272t 수거」 · 서울신문 2026.09.09 「광복절 연휴 폭우 해양쓰레기, 경남 연안 96% 수거」", true);
  s.addNotes("실제 사례 한 장. 숫자 네 개만 크게. 2026년 8월 반복 사례로 '일회성 아님'을 보인다.");

  // 현행 방식의 한계
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "01 현황과 문제" });
  s.addText("지금 쓰는 세 가지 눈, 모두 무게를 못 본다", { placeholder: "title" });
  sub(s, "신고·순찰은 느리고, 위성은 패치만 보고, 드론 2D 사진은 크기와 위치를 잘못 잽니다.");
  const eyes = [
    ["FaEye", "사람 신고 · 순찰", "현존량의 90%가 침적·해변에 흩어져 있는데 탐지는 신고와 순찰에 의존합니다. 국가 해안쓰레기 모니터링은 2개월에 1회, 선정 해안만 조사합니다.", "느리고 범위가 좁다"],
    ["FaSatellite", "위성 영상", "집적 패치의 위치와 변화는 잡지만 재질·부피는 확정하지 못합니다. 촬영각과 해상도 때문에 수십 cm 물체 하나하나의 무게로 내려가지 않습니다.", "넓게 보지만 재질·부피 불가"],
    ["FaCamera", "드론 2D 사진", "카메라 높이·평지를 가정한 위치 계산은 고도 입력이 틀리면 50 m씩 빗나가고, 품목 수 × 평균무게 계수는 크기가 제각각인 물체에서 수십 배 벌어집니다.", "가까이 보지만 위치·무게가 틀림"],
  ];
  eyes.forEach((e, i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.95, 3.9, 4.0, { icon: e[0], head: e[1], body: e[2], headSize: 15, bodySize: 12.5 });
    tag(s, e[3], x + 0.3, 5.5, false, 2.7);
  });
  source(s, "출처: 해양수산부 「해양폐기물 저감 대책」 현존량 구성 · 해양환경공단 국가 해안쓰레기 모니터링(2개월 주기) · 팀 현장 조사(2026.09, 위치 오차·무게 계수)");
  s.addNotes("세 가지 눈의 공통 결함: 무게를 못 본다. 위성은 3DLabs의 강점이므로 '넓게 보는 역할'로 존중하며 한계를 짚는다.");

  // 숫자로 본 문제
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "01 현황과 문제" });
  s.addText("같은 42개 물체, 1.3 kg과 101 kg", { placeholder: "title" });
  sub(s, "문갑도 현장 조사. 업체의 품목 계수 합계와 드론 3D 부피 × 겉보기밀도가 78배 벌어졌습니다.");
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.95, w: 6.4, h: 4.5, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "문갑도 42개 물체의 총 무게, 두 가지 추정 (kg)", { x: 0.9, y: 2.1, w: 6, h: 0.35, fontSize: 12, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "무게(kg)", labels: ["업체 품목 계수", "3D 부피 × 겉보기밀도"], values: [1.3, 101] }],
    chartBase({ x: 0.8, y: 2.5, w: 6.0, h: 3.0, barDir: "bar", valAxisMinVal: 0, valAxisMaxVal: 120, dataLabelFormatCode: "0.0", catAxisLabelFontSize: 11, catAxisOrientation: "maxMin", chartColors: [H.accent2] }));
  tb(s, "계수 방식은 '품목 1개 = 평균 몇 g'으로 셉니다. 어망 뭉치·젖은 스티로폼처럼 크기가 제각각인 물체에서 차이가 폭발합니다.", { x: 0.9, y: 5.55, w: 5.9, h: 0.8, fontSize: 11, color: C.accent4, valign: "top" });
  stat(s, 7.3, 1.95, 2.6, 2.15, { value: "50", unit: "m", label: "탐지 위치 오차 (평면 교차 방식)", note: "수거 인력이 현장에서 못 찾는 거리" });
  stat(s, 10.13, 1.95, 2.6, 2.15, { value: "실패", unit: "", label: "경사 통과 비행의 3D 복원", note: "한 방향 촬영은 부피를 못 냄", color: C.accent2 });
  card(s, 7.3, 4.3, 5.43, 2.15, { icon: "FaBalanceScale", head: "계수 방식은 문헌에서도 약 40% 과대추정", body: "드론 영상 무게 추정 세 방법을 비교한 Andriolo et al. (2024, Marine Pollution Bulletin 202:116405)은 현장 평균무게 계수 방식이 약 40% 과대추정한다고 보고했습니다. 무게는 부피에서 와야 합니다.", headSize: 13, bodySize: 11 });
  source(s, "출처: 팀 현장 조사(문갑도, 2026.09) · Andriolo et al. (2024) Marine Pollution Bulletin 202:116405");
  s.addNotes("우리 데이터로 문제를 숫자로 고정. 결론: 더 정확한 점 추정이 아니라 '얼마나 믿을 수 있는지가 붙은 추정'이 필요.");

  // ═════════ 02 솔루션 ═════════
  pres.addSection({ title: "02 솔루션" });
  s = pres.addSlide({ masterName: "SECTION", sectionTitle: "02 솔루션" });
  tb(s, "02", { x: 0.8, y: 1.9, w: 3, h: 1.0, fontSize: 60, bold: true, color: C.accent2 });
  s.addText("솔루션", { placeholder: "title" });
  s.addText("어디부터 날릴지, 어떻게 날릴지, 무엇이 어디에 얼마나 있는지, 그래서 트럭이 몇 대인지.", { placeholder: "body" });

  // 솔루션 개요: 파이프라인
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "02 솔루션" });
  s.addText("비행 한 번이 수거계획서 한 부가 된다", { placeholder: "title" });
  sub(s, "입력은 드론 영상과 자막 로그(SRT)뿐입니다. 특별한 장비 없이 DJI 기본 기체로 7단계를 자동 수행합니다.");
  const steps = [
    ["FaMapMarkedAlt", "집적 예측", "조류·바람·하천 입자추적으로 구간 우선순위"],
    ["FaPlane", "커버리지 비행", "선회 패턴, 고도 20~40 m, 짐벌 −90°"],
    ["FaSearchLocation", "탐지", "AI-Hub 해안쓰레기 학습 YOLO"],
    ["FaCrosshairs", "위치", "광선 교차 삼각측량 + 오차반경"],
    ["FaCubes", "부피·무게", "SfM 3D 부피 × 겉보기밀도"],
    ["FaRulerCombined", "예측구간", "하한~상한, conformal 보정"],
    ["FaTruck", "수거계획", "재방문 판단 → 마대·트럭·인원"],
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
  // 위성 입력 표시
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 4.75, w: 3.4, h: 0.55, fill: { color: H.accent6 }, line: { color: H.accent6 }, rectRadius: 0.1, objectName: "satellite input" });
  s.addImage({ data: ICON.FaSatellite_n, x: 0.78, y: 4.88, w: 0.3, h: 0.3, objectName: "icon satellite" });
  tb(s, "3DLabs 위성 ARD가 들어가는 자리: 집적 패치·변화 → 우선순위", { x: 1.18, y: 4.75, w: 2.8, h: 0.55, fontSize: 9.5, bold: true, color: C.text2, valign: "middle" });
  card(s, 0.6, 5.5, 6.0, 1.05, { head: "입력", body: "비행 영상(MP4) + 자막 로그(SRT: 시각·GPS·고도). 1차 비행 1회.", headSize: 12, bodySize: 11 });
  card(s, 6.73, 5.5, 6.0, 1.05, { head: "출력", body: "구간 우선순위 지도(GeoJSON) · 물체 목록(위치·오차반경·무게 구간 CSV) · 마대·트럭·인원 산출표 · 2차 비행 경로(KMZ)", headSize: 12, bodySize: 11 });
  s.addNotes("7단계 파이프라인. 우리 기여는 6→7의 재방문 규칙: 수거계획을 바꾸는 불확실성만 줄인다.");

  // 핫스팟 경로
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "02 솔루션" });
  s.addText("어디부터 날릴까: 조류가 모으는 해안을 먼저", { placeholder: "title" });
  sub(s, "조류·바람·하천 유입을 넣은 라그랑주 입자추적으로 좌초 밀도가 높은 해안을 순위화하고, 바다·산 등 비행 불가 구역은 자동 마스킹합니다.");
  s.addImage({ path: img("hotspot_map_gyodong.jpg"), x: 0.6, y: 1.95, w: 5.6, h: 4.41, objectName: "교동도 집적 예상 지도" });
  tb(s, "교동도 집적 예상 구간 (빨간 라인). 100 m 격자 · 200,000 입자 · 30일 여름 장마 시나리오", { x: 0.6, y: 6.38, w: 5.6, h: 0.3, fontSize: 9, color: C.accent4 });
  s.addShape(pres.ShapeType.roundRect, { x: 6.5, y: 1.95, w: 6.23, h: 2.75, fill: { color: H.lt2 }, line: { color: H.lt2 }, rectRadius: 0.12, objectName: "chart card" });
  tb(s, "인천·강화 집적 예상 해안 상위 5구간 (좌초 밀도 점수)", { x: 6.75, y: 2.05, w: 5.8, h: 0.3, fontSize: 11.5, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "점수", labels: ["김포 서안(한강하구)", "강화 북안(조강 연안)", "소래·시흥 연안", "강화 동안(염하수로)", "인천 북항·연안부두"], values: [162.7, 150.4, 118.6, 115.8, 107.3] }],
    chartBase({ x: 6.6, y: 2.35, w: 6.0, h: 2.3, barDir: "bar", valAxisMinVal: 0, valAxisMaxVal: 200, dataLabelFormatCode: "0", catAxisLabelFontSize: 9.5, catAxisOrientation: "maxMin", valAxisHidden: true, valGridLine: { style: "none" }, plotArea: { fill: { color: H.lt2 } } }));
  bullets(s, [
    "모델: 조석 연속방정식(M2+S2) 조류 + 풍압 1.5% + 확산 10 m²/s, 좌초·재부유 확률. 200 m 격자, 15,000 입자, 30일.",
    "출력: 구간별 순위(JSON)·GIS 라인(GeoJSON)·추천 촬영 경로. 섬 단위(교동도·서검도)는 8방위 구간으로 이름 붙임.",
    "실측 해류(국립해양조사원·KOOS·Copernicus)로 교체 가능한 인터페이스. 현재는 모식 조류라 실측 검증 전.",
  ], { x: 6.5, y: 4.85, w: 6.23, h: 1.5, fontSize: 11 });
  refs(s, "근거: Dagestad et al. (2018) OpenDrift, Geosci. Model Dev. 11:1405–1420 · Onink et al. (2021) 좌초·재부유 매개변수화, Environ. Res. Lett. 16:064053", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("핫스팟 경로: '어디부터'를 정하는 단계. 3DLabs 위성 데이터가 결합되면 모델 순위를 실제 패치로 보정할 수 있다.");

  // 촬영 조건·시뮬레이터
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "02 솔루션" });
  s.addText("어떻게 날릴까: 시뮬레이터로 정한 비행 조건", { placeholder: "title" });
  sub(s, "비행시간·발열·바닷바람의 제약과 탐지량의 트레이드오프를 실제 지형 위 시뮬레이션과 정사영상 시뮬레이터로 조정했습니다.");
  s.addImage({ path: img("wolmido_map.jpg"), x: 0.6, y: 1.95, w: 3.6, h: 4.4, objectName: "월미도 비행 시뮬레이션 지도" });
  tb(s, "월미도 DEM 위 선회 비행 시뮬레이션 (PyBullet)", { x: 0.6, y: 6.38, w: 3.6, h: 0.3, fontSize: 9, color: C.accent4 });
  s.addShape(pres.ShapeType.roundRect, { x: 4.5, y: 1.95, w: 4.0, h: 2.6, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "재방문 효과: 탐지 재현율 (sim_ortho)", { x: 4.75, y: 2.05, w: 3.6, h: 0.3, fontSize: 11.5, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "재현율", labels: ["커버리지만", "커버리지 + 재방문"], values: [0.71, 0.86] }],
    chartBase({ x: 4.6, y: 2.4, w: 3.8, h: 2.05, barDir: "col", valAxisMinVal: 0, valAxisMaxVal: 1, dataLabelFormatCode: "0.00", catAxisLabelFontSize: 10, valAxisLabelFormatCode: "0.0" }));
  stat(s, 8.73, 1.95, 4.0, 2.6, { value: "+697", unit: "m", label: "재방문으로 늘어난 비행거리", note: "재현율 15%p를 사는 값. 불확실한 물체만 다시 가므로 전체 재비행보다 짧다.", color: C.accent2 });
  card(s, 4.5, 4.75, 8.23, 1.6, { head: "비행 조건 (실험으로 고정)", body: "선회 패턴 기본(경사 통과는 탐지 전용) · 고도 20~40 m · 짐벌 −90° · 1초 간격 프레임 · 시차 확보: 고도 10 m 약 53°, 20 m 약 28°, 40 m 약 14°(5프레임 이상 권장) · 경로 추종 오차 최대 2.8 m(월미도), 2.4 m(강화)", headSize: 12.5, bodySize: 11 });
  refs(s, "근거: Galceran & Carreras (2013) 커버리지 경로계획 서베이, Robot. Auton. Syst. 61(12):1258–1276 · Popović et al. (2020) 정보 경로계획(IPP), Auton. Robots 44:889–911", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("IPP는 지도 전체의 불확실성을 줄이지만 우리는 수거계획이 바뀌는 불확실성만 줄인다. 2 kg짜리가 1인지 3인지는 안 가고, 20 kg짜리가 23 kg을 넘는지는 간다.");

  // 탐지·위치
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "02 솔루션" });
  s.addText("무엇이 어디에: 탐지와 광선 교차 삼각측량", { placeholder: "title" });
  sub(s, "같은 물체를 본 여러 프레임의 카메라 광선을 서로 교차시켜 위치를 풉니다. 카메라 높이·평지 가정이 빠져 고도 입력 오류에 둔감합니다.");
  card(s, 0.6, 1.95, 5.3, 2.1, { icon: "FaSearchLocation", head: "탐지: AI-Hub 해안쓰레기 학습 YOLO", body: "11개 레이블 추가 학습. 1초 간격 프레임마다 박스·종류·신뢰도를 내고, 신뢰도는 위치 계산의 가중치로 넘어갑니다.", headSize: 13.5, bodySize: 11.5 });
  card(s, 0.6, 4.25, 5.3, 2.1, { icon: "FaCrosshairs", head: "위치: 3×3 최소제곱 + Huber 가중", body: "시차 5° 미만(호버링)이면 평면 교차로 자동 복귀. 쌍별 높이 투표로 지면 높이를 역산해 SRT 고도를 검증하고, GPS 편향을 공통 오차로 넣은 몬테카를로 오차반경(r95)을 물체마다 기록합니다.", headSize: 13.5, bodySize: 11.5 });
  s.addShape(pres.ShapeType.roundRect, { x: 6.2, y: 1.95, w: 6.53, h: 3.0, fill: { color: H.lt2 }, line: { color: H.lt2 }, rectRadius: 0.12, objectName: "table card" });
  tb(s, "합성 시나리오 검증 (정답 위치 대비 최대 오차)", { x: 6.45, y: 2.05, w: 6.0, h: 0.3, fontSize: 11.5, bold: true });
  const hdr = (t) => ({ text: t, options: { bold: true, color: H.dk2, fill: { color: "DCE6EC" }, fontSize: 10 } });
  s.addTable([
    [hdr("시나리오"), hdr("삼각측량"), hdr("기존 평면 교차")],
    ["직진, 입력 높이 3.7 m / 실제 20 m", "0.02 m", "묶기 실패 (0개)"],
    ["일렬 물체 3개, 입력 8 m / 실제 20 m", "0.01~0.02 m", "—"],
    ["이상치 광선 1개 포함", "0.11 m", "—"],
    ["짐벌 −60° 선회 (반경 6 m)", "0.01 m", "—"],
    ["몬테카를로 r95 (GPS 1σ 2.5 m)", "5.2 m", "—"],
  ], { x: 6.45, y: 2.4, w: 6.03, colW: [3.03, 1.4, 1.6], fontSize: 10, color: H.dk1, border: { type: "solid", color: "C9D6DE", pt: 0.5 }, fill: { color: H.lt1 }, rowH: 0.36, margin: 0.05, objectName: "synthetic results" });
  stat(s, 6.2, 5.15, 3.15, 1.2, { value: "1.16", unit: "m", label: "ㅁ자 건물 실기체: 3D ↔ GPS 잔차" });
  stat(s, 9.58, 5.15, 3.15, 1.2, { value: "5.2", unit: "m", label: "r95 오차반경 (GPS 1σ 2.5 m)", color: C.accent2 });
  refs(s, "근거: Martin et al. (2018) MPB 131:662–673 · Fallati et al. (2019) STOTEN 693:133581 · Hartley & Sturm (1997) CVIU 68(2):146–157 · 절대 위치의 바닥은 GPS(1 m 이하는 RTK·기준표식)", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("1장의 50 m 오차는 고도·평지 가정에서 왔다. 그 가정을 빼면 오차는 GPS 자체 수준(수 m)으로 내려온다.");

  // 부피·무게
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "02 솔루션" });
  s.addText("얼마나 무거운가: 3D 부피 × 겉보기밀도, 그리고 구간", { placeholder: "title" });
  sub(s, "선회 비행 사진으로 물체 3D를 복원해 부피를 재고, 종류별 겉보기밀도를 곱합니다. 무게는 점이 아니라 하한~상한 구간으로 넘깁니다.");
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.95, w: 5.4, h: 4.4, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "SfM 부피 오차, 실측 대비 (선회 비행 0007)", { x: 0.85, y: 2.05, w: 5, h: 0.3, fontSize: 11.5, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "부피 오차(%)", labels: ["물체 1", "물체 2"], values: [-3, 19] }],
    chartBase({ x: 0.7, y: 2.4, w: 5.2, h: 2.6, barDir: "col", valAxisMinVal: -30, valAxisMaxVal: 30, dataLabelFormatCode: "+0;-0", catAxisLabelFontSize: 10.5, valAxisLabelFormatCode: "0" }));
  tag(s, "경사 통과 0015: 3D 복원 실패", 0.85, 5.15, true, 2.6);
  tb(s, "한 방향으로 지나가는 비행은 물체의 면이 한쪽만 보여 3D가 서지 않습니다. 선회를 기본 패턴으로 고정한 이유입니다.", { x: 0.85, y: 5.55, w: 4.9, h: 0.7, fontSize: 10.5, color: C.accent4, valign: "top" });
  card(s, 6.3, 1.95, 6.43, 2.1, { icon: "FaRulerCombined", head: "예측구간: 분포 가정 없는 conformal prediction", body: "문갑도 42개의 부피·실측 무게 쌍으로 종류별 겉보기밀도 분포와 보정 집합을 만들고, 포함확률 90%의 하한~상한을 물체마다 붙입니다. 어떤 모델에도 사후 적용 가능합니다.", headSize: 13.5, bodySize: 11.5 });
  card(s, 6.3, 4.25, 6.43, 2.1, { icon: "FaBullseye", head: "재방문 규칙: 계획을 바꾸는 불확실성만", body: "구간이 1인 운반 한계(23 kg), 마대, 트럭 적재 경계를 가로지르는 물체만 2차 비행 후보. 그 외는 구간이 넓어도 다시 가지 않습니다. 보정 데이터 확보 중.", headSize: 13.5, bodySize: 11.5 });
  refs(s, "근거: Westoby et al. (2012) SfM, Geomorphology 179:300–314 · Kako, Morita & Taneda (2020) 드론+SfM+딥러닝 해변 플라스틱 부피, MPB 155:111127 · Angelopoulos & Bates (2023) Conformal Prediction, Found. Trends ML 16(4):494–591", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("부피→무게→구간. 구간이 있어야 '어디를 다시 갈지'가 정의된다.");

  // 수거계획 대시보드
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "02 솔루션" });
  s.addText("수거계획: 마대·트럭·인원이 숫자로 나온다", { placeholder: "title" });
  sub(s, "대시보드 화면 구성. 아래 수치는 예시 데이터이며, 문갑도 42개 라벨을 넣으면 같은 화면이 실제 값으로 바뀝니다.", 10.4);
  tag(s, "예시 데이터", 11.18, 1.4, true);
  const kp = [["탐지 물체", "12", "개", "4개 구간"], ["총 무게 예측구간", "71–175", "kg", "폭 104 kg"], ["2차 비행 후보", "4", "개", "33%만 재방문"], ["2차 비행 후 확정", "마대 4→9 · 트럭 1 · 인원 1→2", "", "하한·상한 두 번 계산"]];
  kp.forEach((k, i) => {
    const x = 0.6 + i * 3.075;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.95, w: 2.9, h: 1.35, fill: { color: H.lt2 }, line: { color: H.lt2 }, rectRadius: 0.1, objectName: "kpi " + k[0] });
    tb(s, k[0], { x: x + 0.22, y: 2.05, w: 2.5, h: 0.3, fontSize: 10, color: C.accent4 });
    s.addText([{ text: k[1], options: { fontSize: i === 3 ? 13 : 24, bold: true, color: i === 2 ? C.accent2 : C.text2 } }, { text: k[2] ? " " + k[2] : "", options: { fontSize: 11, bold: true, color: C.accent4 } }], { x: x + 0.22, y: 2.35, w: 2.5, h: 0.6, isTextBox: true, margin: 0, valign: "middle" });
    tb(s, k[3], { x: x + 0.22, y: 2.95, w: 2.5, h: 0.3, fontSize: 9.5, color: C.accent4 });
  });
  // 구간 우선순위 띠
  tb(s, "구간 우선순위 (집적 예측 × 1차 비행 탐지량)", { x: 0.6, y: 3.5, w: 6, h: 0.3, fontSize: 11.5, bold: true });
  const segs = [["A", "12–36 kg", 3], ["B", "23–66 kg", 3], ["C", "22–38 kg", 2], ["D", "14–35 kg", 2], ["E", "미탐지", 1], ["F", "미탐지", 1]];
  const segCol = { 3: H.dk2, 2: "7FA6B8", 1: "D5DEE4" };
  segs.forEach((g, i) => {
    const x = 0.6 + i * 1.0;
    s.addShape(pres.ShapeType.rect, { x, y: 3.85, w: 0.95, h: 0.9, fill: { color: segCol[g[2]] }, line: { color: H.lt1, width: 1 }, objectName: "segment " + g[0] });
    tb(s, g[0], { x: x + 0.1, y: 3.9, w: 0.8, h: 0.3, fontSize: 12, bold: true, color: g[2] >= 2 ? C.background1 : C.text1 });
    tb(s, g[1], { x: x + 0.1, y: 4.4, w: 0.85, h: 0.3, fontSize: 8.5, color: g[2] >= 2 ? C.background1 : C.accent4 });
  });
  tb(s, "A→F는 해안을 따라 서→동. 색이 진할수록 먼저 수거. 실제 지도는 라벨 좌표로 그립니다.", { x: 0.6, y: 4.85, w: 6, h: 0.5, fontSize: 9.5, color: C.accent4, valign: "top" });
  // 산출
  const outs = [["마대", "4–9 장", "⌈71~175 ÷ 20⌉ · 2차 비행으로 확정"], ["트럭", "1 대", "⌈71~175 ÷ 1,000⌉ · 확정"], ["인원 (1일)", "1–2 명", "⌈마대 ÷ 8⌉ · 2차 비행으로 확정"]];
  outs.forEach((o, i) => {
    const x = 0.6 + i * 2.05;
    s.addShape(pres.ShapeType.roundRect, { x, y: 5.4, w: 1.95, h: 1.05, fill: { color: H.lt2 }, line: { color: H.lt2 }, rectRadius: 0.1, objectName: "output " + o[0] });
    tb(s, o[0], { x: x + 0.15, y: 5.47, w: 1.7, h: 0.25, fontSize: 9.5, color: C.accent4 });
    tb(s, o[1], { x: x + 0.15, y: 5.7, w: 1.7, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
    tb(s, o[2], { x: x + 0.15, y: 6.1, w: 1.75, h: 0.3, fontSize: 7.5, color: C.accent4 });
  });
  // 후보 표
  tb(s, "2차 비행 후보 (구간이 경계에 걸린 물체만)", { x: 7.0, y: 3.5, w: 5.7, h: 0.3, fontSize: 11.5, bold: true });
  s.addTable([
    [hdr("ID · 구간"), hdr("종류"), hdr("무게 구간"), hdr("이유")],
    ["D-06 · B", "폐어망(젖음)", "18–52 kg", "23 kg 가로지름 · 마대 2→4장"],
    ["D-02 · A", "폐어망 뭉치", "9.5–31 kg", "23 kg 가로지름 · 마대 1→2장"],
    ["D-12 · D", "혼합 뭉치", "6–20 kg", "마대 1→2장, 폭이 큰 물체"],
    ["D-08 · C", "폐목재", "14–27 kg", "23 kg 가로지름"],
  ], { x: 7.0, y: 3.85, w: 5.73, colW: [1.1, 1.25, 1.1, 2.28], fontSize: 9.5, color: H.dk1, border: { type: "solid", color: "C9D6DE", pt: 0.5 }, fill: { color: H.lt1 }, rowH: 0.34, margin: 0.04, objectName: "revisit candidates" });
  tb(s, "규칙: 무게 구간이 1인 운반 한계를 가로지르거나, 구간 합계의 마대 수가 하한·상한에서 달라지는 물체. 산출은 하한과 상한으로 두 번 계산해 '확정'인지 '2차 비행 필요'인지 보여줍니다.", { x: 7.0, y: 5.65, w: 5.73, h: 0.85, fontSize: 9.5, color: C.accent4, valign: "top" });
  s.addNotes("제품 화면의 뼈대. 데모 때는 웹 대시보드(설정값 바꾸면 재계산)로 직접 보여준다.");

  // 수거 동선
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "02 솔루션" });
  s.addText("수거 경로: 사람이 갈 수 있는 길로, 지자체 조건에 맞춰", { placeholder: "title" });
  sub(s, "수거 인력을 위한 접근·수거 동선. 드론 비행 때는 바다·산을, 수거 때는 사람·차량이 못 가는 곳을 마스킹합니다.", 10.4);
  tag(s, "설계 중", 11.18, 1.4, true);
  const rt = [
    ["FaCity", "지자체 조건 입력", "인원·차량(트럭 적재량)·작업 시간·마대 규격. 지자체마다 다르므로 설정값으로 둡니다."],
    ["FaWalking", "통행 가능 구역 마스킹", "해안 접근로·로드뷰 기반 진입 지점. 해변은 차량 진입이 제한되므로 하역 지점을 따로 둡니다."],
    ["FaRoute", "최단 수거 경로", "물체 위치·무게 구간·하역 지점을 넣어 인원별 동선과 왕복 횟수를 계산합니다."],
    ["FaClipboardList", "앱·대시보드 제공", "현장에서는 '못 찾음'·'수거 완료' 체크로 되돌려 받아 다음 비행의 재현율 보정에 씁니다."],
  ];
  rt.forEach((r, i) => card(s, 0.6 + i * 3.075, 1.95, 2.9, 3.3, { icon: r[0], head: r[1], body: r[2], headSize: 13.5, bodySize: 11.5 }));
  card(s, 0.6, 5.45, 12.13, 1.0, { head: "왜 드론 단계와 분리하는가", body: "드론은 공중에서 '어디에 얼마나'를 재고, 수거 동선은 지상의 제약(접근로·적재·인원)을 받습니다. 두 마스킹이 다르므로 같은 지도 위에서 계층을 나눠 둡니다.", headSize: 12.5, bodySize: 11 });
  s.addNotes("원본 기획의 '수거자 최단경로'를 설계 단계로 정직하게 표시.");

  // ═════════ 03 검증 ═════════
  pres.addSection({ title: "03 검증" });
  s = pres.addSlide({ masterName: "SECTION", sectionTitle: "03 검증" });
  tb(s, "03", { x: 0.8, y: 1.9, w: 3, h: 1.0, fontSize: 60, bold: true, color: C.accent2 });
  s.addText("검증", { placeholder: "title" });
  s.addText("세 실험은 각각 파이프라인의 한 가정을 깹니다. 결과가 없는 항목은 '진행 중', 가정은 '가정'이라고 썼습니다.", { placeholder: "body" });

  // 검증 요약표
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "03 검증" });
  s.addText("검증 요약: 가설 · 설계 · 결과", { placeholder: "title" });
  sub(s, "완료 5건, 진행 중 2건, 가정 1건. 수치는 모두 재현 가능한 로그·스크립트에서 나왔습니다.");
  const okc = { text: "완료", options: { bold: true, color: "0A7A2F", fontSize: 9.5, align: "center" } };
  const runc = { text: "진행 중", options: { bold: true, color: "B35A00", fontSize: 9.5, align: "center" } };
  const asc = { text: "가정", options: { bold: true, color: H.accent4, fontSize: 9.5, align: "center" } };
  s.addTable([
    [hdr("실험"), hdr("가설"), hdr("설계"), hdr("결과"), hdr("상태")],
    ["EXP-A 비행 패턴", "선회 비행은 SfM 부피를 복원하고, 경사 통과는 실패한다", "같은 물체군을 선회(0007)·경사 통과(0015)로 촬영, 부피를 실측과 비교", "선회 −3% / +19%, 경사 통과 복원 실패", okc],
    ["EXP-B 위치 정합", "SfM 자세를 GPS에 정합하면 잔차 수 m 이내, 고도 입력 오류에 둔감", "ㅁ자 건물 실기체 비행 + 합성 7개 시나리오", "실기체 잔차 1.16 m · 합성 0.02 m(기존 방식 0개) · r95 5.2 m", okc],
    ["EXP-C 재방문", "불확실한 물체만 재방문하면 짧은 추가 비행으로 재현율이 크게 오른다", "정사영상 시뮬레이터(sim_ortho)에서 커버리지만 vs +재방문", "재현율 0.71 → 0.86, 비행거리 +697 m", okc],
    ["SUP-D 지형 비행", "실제 DEM 위에서 경로·고도 유지가 가능하다", "월미도(3.8 m/px)·강화(30 m/px) PyBullet 시뮬레이션", "경로 추종 오차 최대 2.8 / 2.4 m, 지형 오차 0.00 m", okc],
    ["SUP-E 집적 예측", "조류 입자추적으로 집적 해안을 순위화할 수 있다", "인천·강화 200 m 격자 15,000 입자 30일, 섬 단위 100 m 격자", "상위 구간 산출(김포 서안·강화 북안…), 실측 검증 전", okc],
    ["재방문 규칙 비교", "경계 기반 규칙이 고정 임계 규칙보다 수거계획 오차를 더 줄인다", "같은 비행거리에서 두 규칙 비교", "결과 없음", runc],
    ["예측구간 보정", "종류별 겉보기밀도 분포로 포함확률 90% 구간을 만들 수 있다", "문갑도 42개 부피·실측 무게 쌍", "보정 데이터 확보 중", runc],
    ["위성 우선순위 곡선", "위성·집적 순위가 실제 드론 탐지량과 상관된다", "구간 순위 vs 탐지량 상관", "곡선 없음, 1차는 집적 순위 사용", asc],
  ], { x: 0.6, y: 1.95, w: 12.13, colW: [1.7, 3.3, 3.2, 3.0, 0.93], fontSize: 9.5, color: H.dk1, border: { type: "solid", color: "C9D6DE", pt: 0.5 }, fill: { color: H.lt1 }, rowH: 0.47, margin: 0.05, valign: "middle", objectName: "validation summary" });
  source(s, "저장소: island_drone_sim(지형 비행) · 삼각측량 패치 docs/삼각측량_위치보정.md · incheon_debris_sim(집적 예측) · 결과자료 폴더(0007/0015, ㅁ자 건물, sim_ortho)");
  s.addNotes("한 표로 신뢰성. 결과 없는 항목을 숨기지 않는 것이 이 장의 메시지.");

  // 한계와 대응
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "03 검증" });
  s.addText("정직한 한계와 대응", { placeholder: "title" });
  sub(s, "시연에서 드러난 문제와 모델의 가정. 각각 어떻게 줄이는지까지 적었습니다.");
  const lim = [
    ["FaMapMarkerAlt", "절대 위치의 바닥은 GPS", "드론 GPS가 2 m 밀리면 모든 광선이 같이 밀립니다(r95 ≈ 5 m). 1 m 아래로 가려면 RTK, 좌표를 아는 기준 표식, 또는 정사영상 정합이 필요합니다."],
    ["FaSun", "해수면 빛반사", "낮·저녁 두 번 시연했을 때 반사 조건이 달랐습니다. 촬영 시간대 규칙, 편광 필터·노출 보정, 반사 영역 마스킹으로 대응합니다."],
    ["FaBoxOpen", "구석 고정 사물 오인식", "구조물 옆 상자를 고정 사물과 같은 물체로 묶을 수 있습니다. 다중 프레임 추적(ByteTrack)과 정적 배경 제외로 묶기를 단단히 합니다."],
    ["FaWater", "모식 조류 모델", "조류는 실측이 아니라 조석 연속방정식 모델입니다. 국립해양조사원 관측·KOOS·Copernicus 해류로 교체하고 KOEM 모니터링으로 좌초 확률을 보정합니다."],
  ];
  lim.forEach((l, i) => card(s, 0.6 + i * 3.075, 1.95, 2.9, 4.0, { icon: l[0], head: l[1], body: l[2], headSize: 14, bodySize: 12.5 }));
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
    ["FaSatellite", "3DLabs · 위성 계층", ["위성 지상국 운영, 1:5,000 도엽 정사영상·ARD(Analysis Ready Data) 생산", "광역 집적 패치 탐지와 시계열 변화 → 구간 우선순위 입력", "B2G 공급 채널(공공 활용 플랫폼)"], H.dk2, true],
    ["FaPlane", "붕붕이 · 드론 계층", ["구간별 커버리지 비행, 탐지·삼각측량·SfM 부피", "무게 예측구간과 재방문 규칙, 2차 비행 경로", "수거계획 산출(마대·트럭·인원), 대시보드"], "124A6E", true],
    ["FaUsers", "고객 · 지자체 계층", ["시군 해양수산 부서: 예산·배차", "수거 용역업체: 동선·인원", "해양환경공단: 반복 모니터링 데이터"], H.lt2, false],
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
  source(s, "3DLabs 소개: 인하대 공간정보공학 스핀오프(2011), 위성 지상국·전처리·ARD·드론 영상처리(위키백과·회사 소개) · 전남도 441억(뉴스핌 2026.03.22) · KOEM 드론·KOEM-ARK(이투데이, 뉴스핌 2026.07.07)");
  s.addNotes("상대의 강점(위성·ARD·B2G 채널)을 앞에 두고 우리를 계층으로 끼운다. 시장 신호 세 개는 모두 2026년.");

  // 로드맵
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "04 제안" });
  s.addText("공동 실증 로드맵 (제안)", { placeholder: "title" });
  sub(s, "세 단계, 각 단계의 끝에 숫자로 확인할 수 있는 결과를 두었습니다.");
  const ph = [
    ["1", "2026 4분기", "데이터 보정", ["문갑도 42개 부피·실측 무게 쌍으로 예측구간 보정(포함확률 90%)", "재방문 규칙 비교 실험(고정 임계 vs 경계 기반)", "위성 ARD 샘플 2~3개 해안으로 집적 순위 vs 패치 비교"], "산출: 보정 집합, 규칙 비교 보고"],
    ["2", "2027 상반기", "지자체 시범", ["시군 1곳(인천 옹진 또는 전남 도서) 해안 3구간 선정", "실측 해류(KHOA·KOOS) 교체, RTK 또는 기준 표식 도입", "비행 1회 → 수거계획서 → 실제 수거량과 대조"], "산출: 추정 vs 실제 수거량 오차, 마대·트럭 적중률"],
    ["3", "2027 하반기", "위성 결합 · 상용", ["위성 변화 탐지로 비행 시점·구간 자동 추천", "KOEM 2개월 모니터링과 연동한 반복 조사 상품", "B2G 플랫폼 활용 분야에 '해안쓰레기' 추가"], "산출: 구독형 수거계획 서비스, 레퍼런스 1곳"],
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
    ["FaDatabase", "위성 ARD 샘플", "대상 해안 2~3곳(인천·강화 도서 또는 전남 도서)의 정사영상·시계열. 집적 모델 순위와 실제 패치를 대조합니다."],
    ["FaHandshake", "시범 지자체 소개", "B2G 채널로 연결된 시군 1곳. 비행 1회로 수거계획서를 내고 실제 수거량과 대조합니다."],
    ["FaLayerGroup", "데이터 연동 규격 협의", "ARD → 우선순위 입력, 드론 결과(GeoJSON·CSV) → 플랫폼 활용 분야 등록. 양방향 포맷을 먼저 맞춥니다."],
  ];
  asks.forEach((a, i) => card(s, 0.6 + i * 4.1, 1.95, 3.9, 3.0, { icon: a[0], head: a[1], body: a[2], dark: true, headSize: 15, bodySize: 12 }));
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.2, w: 12.13, h: 1.25, fill: { color: H.accent2 }, line: { color: H.accent2 }, rectRadius: 0.12, objectName: "closing" });
  tb(s, "추정이 틀리면 배차가 틀린다.  위성이 넓게 보고, 드론이 자세히 재면, 지자체는 맞게 배차할 수 있습니다.", { x: 0.95, y: 5.2, w: 11.4, h: 0.8, fontSize: 17, bold: true, color: C.background1, valign: "middle" });
  tb(s, "드론대장 붕붕이 · 저장소 HSR2M/hsr1m · 발표 사이트: 한 페이지 스크롤 버전 별도 제공", { x: 0.95, y: 5.95, w: 11.4, h: 0.4, fontSize: 10.5, color: C.background1 });
  s.addNotes("요청 3개를 명확히. 마지막 문장은 표지 문장의 반복.");

  const out = path.join(__dirname, "붕붕이_3DLabs_제안.pptx");
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("written", out);
})().catch((e) => { console.error(e); process.exit(1); });
