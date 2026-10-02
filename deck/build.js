// DroneSweep × 3DLabs 제안 덱 v4 — 구조 개편 (문제 → 과제·과정 → 기술 → 검증 → 기대효과 → 요약)
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
const H = THEME.colors;
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
  pres.layout = "LAYOUT_WIDE";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.author = "드론대장 붕붕이";
  pres.title = "DroneSweep — 드론 영상 하나로 끝내는 해안쓰레기 측정·수거계획";
  const C = pres.SchemeColor;
  const ICON = {};
  for (const n of ["FaExclamationTriangle", "FaSatellite", "FaSearchLocation", "FaCubes", "FaRoute", "FaTruck", "FaWater", "FaMapMarkedAlt",
    "FaBalanceScale", "FaUsers", "FaCheckCircle", "FaFlask", "FaHandshake", "FaEye", "FaCamera", "FaCoins", "FaClipboardList", "FaPlane",
    "FaLayerGroup", "FaRulerCombined", "FaCrosshairs", "FaWalking", "FaBoxOpen", "FaDatabase", "FaMapMarkerAlt", "FaBullseye", "FaCity",
    "FaWeightHanging", "FaVideo", "FaTimesCircle", "FaRedo", "FaCalculator", "FaListOl", "FaComments", "FaCogs", "FaSync", "FaCheck"]) {
    ICON[n + "_w"] = await icon(n, "FFFFFF");
    ICON[n + "_n"] = await icon(n, H.dk2);
    ICON[n + "_o"] = await icon(n, H.accent2);
  }

  // ───────── 레이아웃 ─────────
  const footer = () => [
    { text: "DroneSweep · 드론대장 붕붕이 · 3DLabs 제안 · 2026.10", options: { x: 0.6, y: 7.02, w: 6, h: 0.3, fontSize: 9, color: C.accent4, margin: 0, isTextBox: true } },
  ];
  const titlePh = (dark) => ({ placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.42, w: 12.1, h: 0.95, fontSize: 28, bold: true, color: dark ? C.background1 : C.text1, valign: "middle", margin: 0, align: "left" } } });
  pres.defineSlideMaster({
    title: "DARK_TITLE", background: { color: H.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 1.95, w: 7.3, h: 2.1, fontSize: 36, bold: true, color: C.background1, valign: "bottom", margin: 0, align: "left" } } },
      { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 4.2, w: 7.1, h: 1.5, fontSize: 15, color: C.accent5, valign: "top", margin: 0, align: "left" } } },
    ],
  });
  pres.defineSlideMaster({
    title: "SECTION", background: { color: H.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 3.0, w: 11.5, h: 1.3, fontSize: 40, bold: true, color: C.background1, valign: "bottom", margin: 0, align: "left" } } },
      { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.4, w: 11.0, h: 1.2, fontSize: 16, color: C.accent5, valign: "top", margin: 0, align: "left" } } },
      ...footer(),
    ],
  });
  pres.defineSlideMaster({ title: "CONTENT", background: { color: H.lt1 }, objects: [titlePh(false), ...footer()], slideNumber: { x: 12.3, y: 7.02, w: 0.5, h: 0.3, fontSize: 9, color: C.accent4, align: "right" } });
  pres.defineSlideMaster({ title: "CONTENT_LT2", background: { color: H.lt2 }, objects: [titlePh(false), ...footer()], slideNumber: { x: 12.3, y: 7.02, w: 0.5, h: 0.3, fontSize: 9, color: C.accent4, align: "right" } });
  pres.defineSlideMaster({ title: "DARK_CONTENT", background: { color: H.dk2 }, objects: [titlePh(true), ...footer()], slideNumber: { x: 12.3, y: 7.02, w: 0.5, h: 0.3, fontSize: 9, color: C.accent5, align: "right" } });

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
  function card(slide, x, y, w, h, { icon, head, body, dark, fill, headSize, bodySize, iconColor, inline }) {
    slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill || (dark ? "124A6E" : H.lt1) }, line: { color: fill || (dark ? "124A6E" : H.lt1) }, rectRadius: 0.12, shadow: dark ? undefined : shadow(), objectName: "card " + head });
    let ty = y + 0.28;
    const ic = iconColor || (dark ? H.accent2 : H.dk2);
    if (icon && inline) {
      // 아이콘을 제목 왼쪽에 두는 압축형: 높이 1.3~1.6 카드용
      slide.addShape(pres.ShapeType.ellipse, { x: x + 0.25, y: y + 0.2, w: 0.46, h: 0.46, fill: { color: ic }, line: { color: ic }, objectName: "icon circle" });
      slide.addImage({ data: ICON[icon + "_w"], x: x + 0.36, y: y + 0.31, w: 0.24, h: 0.24, objectName: "icon " + icon });
      tb(slide, head, { x: x + 0.85, y: y + 0.18, w: w - 1.1, h: 0.5, fontSize: headSize || 13, bold: true, color: dark ? C.background1 : C.text1, valign: "middle" });
      tb(slide, body, { x: x + 0.3, y: y + 0.74, w: w - 0.6, h: h - 0.74 - 0.14, fontSize: bodySize || 10.5, color: dark ? C.accent5 : C.accent4, valign: "top", paraSpaceAfter: 4 });
      return;
    }
    if (icon) {
      slide.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: y + 0.28, w: 0.62, h: 0.62, fill: { color: ic }, line: { color: ic }, objectName: "icon circle" });
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
  function pic(slide, file, x, y, w, h, name) { slide.addImage({ path: img(file), x, y, w, h, sizing: { type: "contain", w, h }, objectName: name || file }); }
  function cap(slide, text, x, y, w, h) { tb(slide, text, { x, y, w, h: h || 0.3, fontSize: 9, color: C.accent4, valign: "top" }); }
  const hdr = (t) => ({ text: t, options: { bold: true, color: H.dk2, fill: { color: "DCE6EC" }, fontSize: 10 } });
  const chartBase = (extra) => Object.assign({
    chartColors: [H.accent1], showLegend: false, showTitle: false,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelFontFace: "+mn-lt", dataLabelColor: H.dk1,
    catAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: 10, catAxisLabelColor: H.accent4,
    valAxisLabelFontFace: "+mn-lt", valAxisLabelFontSize: 9, valAxisLabelColor: H.accent4,
    valGridLine: { color: "DDE3E8", size: 0.5 }, catGridLine: { style: "none" }, barGapWidthPct: 60,
    plotArea: { fill: { color: H.lt1 } },
  }, extra);
  function divider(num, title, body, section) {
    const s = pres.addSlide({ masterName: "SECTION", sectionTitle: section });
    tb(s, num, { x: 0.8, y: 1.9, w: 3, h: 1.0, fontSize: 60, bold: true, color: C.accent2 });
    s.addText(title, { placeholder: "title" });
    s.addText(body, { placeholder: "body" });
    return s;
  }
  // 단계 띠 (기술 맵·검증 맵 공용)
  function stepRow(slide, steps, y, h, opts) {
    const n = steps.length, gap = 0.075, w = (12.13 - gap * (n - 1)) / n;
    steps.forEach((st, i) => {
      const x = 0.6 + i * (w + gap), last = st.hl;
      slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: last ? H.dk2 : H.lt2 }, line: { color: last ? H.dk2 : H.lt2 }, rectRadius: 0.1, objectName: "step " + st.name });
      const ic = st.ok === false ? H.accent4 : (last ? H.accent2 : H.dk2);
      slide.addShape(pres.ShapeType.ellipse, { x: x + w / 2 - 0.3, y: y + 0.2, w: 0.6, h: 0.6, fill: { color: ic }, line: { color: ic }, objectName: "icon circle" });
      slide.addImage({ data: ICON[st.icon + "_w"], x: x + w / 2 - 0.15, y: y + 0.35, w: 0.3, h: 0.3, objectName: "icon " + st.icon });
      tb(slide, (i + 1) + ". " + st.name, { x: x + 0.08, y: y + 0.9, w: w - 0.16, h: 0.35, fontSize: 11.5, bold: true, color: last ? C.background1 : C.text1, align: "center" });
      tb(slide, st.desc, { x: x + 0.1, y: y + 1.26, w: w - 0.2, h: h - 1.36, fontSize: opts && opts.descSize || 9.5, color: last ? C.accent5 : C.accent4, align: "center", valign: "top" });
    });
  }

  // ═════════ 표지 ═════════
  pres.addSection({ title: "표지" });
  let s = pres.addSlide({ masterName: "DARK_TITLE", sectionTitle: "표지" });
  s.addImage({ path: img("fig_26_문갑도_우선구간_비행경로.jpg"), x: 8.1, y: 0, w: 5.233, h: 7.5, sizing: { type: "cover", w: 5.233, h: 7.5 }, objectName: "문갑도 우선 구간 비행경로" });
  s.addShape(pres.ShapeType.rect, { x: 8.1, y: 0, w: 5.233, h: 7.5, fill: { color: H.dk2, transparency: 30 }, line: { color: H.dk2, transparency: 100 }, objectName: "image tint" });
  tb(s, "DroneSweep  ·  드론대장 붕붕이  ·  3DLabs 제안", { x: 0.7, y: 1.2, w: 7.3, h: 0.4, fontSize: 13, bold: true, color: C.accent2, charSpacing: 1 });
  s.addText("드론 영상 하나로 끝내는\n해안쓰레기 측정·수거계획", { placeholder: "title" });
  s.addText([
    { text: "추정이 틀리면 배차가 틀린다.", options: { bold: true, color: C.background1, breakLine: true } },
    { text: "위성·해류로 어디를 날지 고르고, 드론 영상 하나로 3D 부피와 무게 구간을 내고,\n수거계획을 바꾸는 물체만 다시 날아 마대·트럭·인원을 확정합니다." },
  ], { placeholder: "body" });
  tb(s, "2026. 10  ·  문갑도 · 송도 · 인천 · 니하우 실증 데이터", { x: 0.7, y: 6.5, w: 7.3, h: 0.4, fontSize: 11, color: C.accent5 });
  s.addNotes("표지. 제목은 '무엇을 하는 것'이고, '추정이 틀리면 배차가 틀린다'는 부제. 오른쪽 그림은 문갑도 위성 형상 점수 상위 구간과 실제 비행 경로.");

  // ═════════ 핵심 기술 맵 ═════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "표지" });
  s.addText("한눈에: 이 기술 → 이 기술 → 이 결과", { placeholder: "title" });
  sub(s, "드론 영상과 비행기록을 넣으면 수거계획서가 나옵니다. 그 사이에 기술 세 덩어리가 있습니다.");
  const techs = [
    ["FaSatellite", "어디를 날지", "위성 해안 형상 점수 + 해류·조석 방향", "쌓이는 자리를 골라 상위 30% 구간만 비행", "비행시간 −63%", "니하우: 41.3 h → 15.4 h로 쓰레기 67% 포착 · 문갑도 라벨 62%"],
    ["FaCubes", "무엇이 어디에 얼마나", "드론 영상 하나 → 탐지 → 3D 위치 → 부피·무게 구간", "정사영상·DSM 없이 영상+SRT만으로", "1.3 kg → 101 kg", "업체 기록 vs 3D 측정 · 위치 1 m대 · 부피 오차 ±20% 안"],
    ["FaTruck", "그래서 몇 대", "정거장·마대·트럭·인력·경로 작업카드", "23 kg 경계에 걸린 물체만 2차 선회", "비행 1회 = 계획서 1부", "니하우 5,476개 → 마대 1,082 · 트럭 37 · 경로 71.9 km"],
  ];
  techs.forEach((t, i) => {
    const x = 0.6 + i * 4.1;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.95, w: 3.9, h: 4.1, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.14, shadow: shadow(), objectName: "tech " + t[1] });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: 2.25, w: 0.7, h: 0.7, fill: { color: H.dk2 }, line: { color: H.dk2 }, objectName: "icon circle" });
    s.addImage({ data: ICON[t[0] + "_w"], x: x + 0.47, y: 2.42, w: 0.36, h: 0.36, objectName: "icon " + t[0] });
    tb(s, "기술 " + (i + 1), { x: x + 1.15, y: 2.28, w: 2.5, h: 0.3, fontSize: 10, color: C.accent4 });
    tb(s, t[1], { x: x + 1.15, y: 2.52, w: 2.6, h: 0.45, fontSize: 17, bold: true });
    tb(s, t[2], { x: x + 0.3, y: 3.12, w: 3.3, h: 0.5, fontSize: 11.5, bold: true, color: C.text2, valign: "top" });
    tb(s, t[3], { x: x + 0.3, y: 3.62, w: 3.3, h: 0.5, fontSize: 10.5, color: C.accent4, valign: "top" });
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.3, y: 4.3, w: 3.3, h: 1.5, fill: { color: H.lt2 }, line: { color: H.lt2 }, rectRadius: 0.1, objectName: "result" });
    tb(s, "결과", { x: x + 0.48, y: 4.36, w: 2.5, h: 0.25, fontSize: 9.5, color: C.accent4 });
    tb(s, t[4], { x: x + 0.48, y: 4.6, w: 3.0, h: 0.5, fontSize: 20, bold: true, color: C.accent2 });
    tb(s, t[5], { x: x + 0.48, y: 5.12, w: 3.0, h: 0.62, fontSize: 9.5, color: C.accent4, valign: "top" });
    if (i < 2) s.addShape(pres.ShapeType.rightArrow, { x: x + 3.92, y: 3.8, w: 0.17, h: 0.4, fill: { color: H.accent2 }, line: { color: H.accent2 }, objectName: "arrow" });
  });
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 6.2, w: 12.13, h: 0.42, fill: { color: H.accent6 }, line: { color: H.accent6 }, rectRadius: 0.1, objectName: "io" });
  tb(s, "입력: 드론 영상(MP4) + 비행기록(SRT)     →     출력: 지도 핀(위치·오차반경) · 물체 목록(부피·무게 구간) · 정거장별 작업카드 · 비행 경로 KML", { x: 0.8, y: 6.2, w: 11.8, h: 0.42, fontSize: 10.5, bold: true, color: C.text2, valign: "middle" });
  s.addNotes("2장. 교수님이 '뭘 많이 했는데 뭔지 모르겠다'고 하셨던 자리. 세 덩어리와 결과 숫자만.");

  // ═════════ 목차 ═════════
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "표지" });
  s.addText("목차", { placeholder: "title" });
  const toc = [
    ["01", "기업이 겪는 문제", "지금 일하는 방식 · 업체 데이터의 오류 · 왜 공공이 돈을 쓰는 일인가 · 비용 구조 · 폭우 사례"],
    ["02", "우리가 받은 과제와 과정", "처음 과제와 바뀐 주제 · 이틀의 과정과 접은 것 · 실제 촬영"],
    ["03", "솔루션: 기술 소개", "한 문장 · 어디를 날지(위성 형상·해류) · 촬영 거리 · 탐지와 3D 위치 · 부피와 무게 · 수거계획과 운용"],
    ["04", "검증", "검증 맵 · 어디를 날지 · 탐지·위치 · 부피·무게 · 재방문·수거계획 · 요약표"],
    ["05", "기대효과와 제안", "기업이 아끼는 것 · 포인트 기술의 의의 · 3DLabs 결합 · 로드맵 · 요청"],
    ["+", "한 장 요약", ""],
  ];
  toc.forEach((t, i) => {
    const y = 1.6 + i * 0.82;
    s.addShape(pres.ShapeType.roundRect, { x: 0.6, y, w: 12.13, h: 0.7, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.1, shadow: shadow(), objectName: "toc " + t[1] });
    tb(s, t[0], { x: 0.85, y, w: 0.8, h: 0.7, fontSize: 20, bold: true, color: C.accent2, valign: "middle" });
    tb(s, t[1], { x: 1.75, y, w: 3.4, h: 0.7, fontSize: 16, bold: true, valign: "middle" });
    tb(s, t[2], { x: 5.2, y, w: 7.3, h: 0.7, fontSize: 11, color: C.accent4, valign: "middle" });
  });
  s.addNotes("목차.");

  // ═════════ 01 기업이 겪는 문제 ═════════
  pres.addSection({ title: "01 기업이 겪는 문제" });
  divider("01", "기업이 겪는 문제", "수거 업체는 세 번 헤맵니다. 어디 있는지, 얼마나 무거운지, 그래서 트럭이 몇 대인지.", "01 기업이 겪는 문제");

  // 지금 일하는 방식
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "01 기업이 겪는 문제" });
  s.addText("지금 일하는 방식: 눈으로 찾고, 면적에 계수를 곱하고, 경험으로 배차한다", { placeholder: "title" });
  sub(s, "문갑도 수거 업체의 현재 작업 흐름. 세 단계 모두 사람이 하고, 숫자는 곱셈 하나입니다.");
  const now = [
    ["FaEye", "찾기: 드론 사진의 드론 GPS가 곧 쓰레기 위치", "화면 가장자리 쓰레기도 드론 좌표로 기록되고 비스듬히 찍은 사진은 수십 m 앞을 가리킵니다. 현장에서 50 m씩 어긋나 수거자가 헤맵니다.", "50 m 오차"],
    ["FaCalculator", "무게: 라벨 면적 × 재질 계수", "스티로폼 0.012, 로프·어망 0.024, 플라스틱 0.020 kg/m². 높이(두께)가 없으니 1.54 m² 스티로폼 더미가 18 g으로 기록됩니다.", "42개 합계 1.3 kg"],
    ["FaTruck", "배차: 경험으로 트럭·마대·인원", "많으면 트럭을 다시 부르고, 적으면 장비가 놀고, 못 찾으면 다시 옵니다. 폭우 뒤에는 추정 그대로 굴삭기·차량을 투입합니다.", "재방문 · 재배차"],
  ];
  now.forEach((e, i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.95, 3.9, 3.75, { icon: e[0], head: e[1], body: e[2], headSize: 14, bodySize: 12 });
    tag(s, e[3], x + 0.3, 5.25, true, 2.2);
  });
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.9, w: 12.13, h: 0.65, fill: { color: H.accent6 }, line: { color: H.accent6 }, rectRadius: 0.1, objectName: "callout" });
  tb(s, "세 단계 모두 '어디에 얼마나'라는 같은 숫자를 쓰는데, 그 숫자가 눈과 곱셈에서 나옵니다. 그래서 위치가 틀리면 동선이, 무게가 틀리면 트럭이 틀립니다.", { x: 0.85, y: 5.9, w: 11.6, h: 0.65, fontSize: 12, bold: true, color: C.text2, valign: "middle" });
  source(s, "출처: 업체 제보(방향정리 문서 0절, 2026-09-30) · 업체 라벨 자료(문갑도 MGD, 42개) · 경남도 2026년 8월 집중호우 대응 보도");
  s.addNotes("제목 후보: ① 지금 일하는 방식: 눈으로 찾고, 면적에 계수를 곱하고, 경험으로 배차한다 ② 수거 업체의 하루: 헤매고, 세고, 다시 부른다 ③ 세 번 틀리는 숫자: 위치·무게·트럭. 1안 채택.");

  // 업체 데이터 오류 (강조)
  s = pres.addSlide({ masterName: "DARK_CONTENT", sectionTitle: "01 기업이 겪는 문제" });
  s.addText("업체 데이터의 오류: 같은 42개가 기록으로는 1.3 kg, 3D로 재면 101 kg", { placeholder: "title" });
  tb(s, "문갑도 업체 라벨의 weight_kg는 실측이 아니라 '면적 × 계수'입니다. 같은 물체를 3D 부피 × 겉보기밀도로 계산하면 78배 커지고, 현실적 두께 범위로는 115~1,355 kg입니다.", { x: 0.6, y: 1.32, w: 12.1, h: 0.5, fontSize: 14, color: C.accent5 });
  pic(s, "fig_12_업체라벨_기록무게_vs_현실범위.jpg", 0.6, 1.95, 7.4, 2.86, "업체 라벨 기록 무게 vs 현실 범위");
  tb(s, "왼쪽: 라벨 42개의 기록 무게 분포(합계 1.32 kg, 최대 0.25 kg). 오른쪽: 같은 면적의 현실적 범위(두께 2~35 cm × 재질 밀도, 로그 눈금).", { x: 0.6, y: 4.85, w: 7.4, h: 0.45, fontSize: 9.5, color: C.accent5, valign: "top" });
  stat(s, 8.3, 1.95, 2.1, 1.65, { value: "1.3", unit: "kg", label: "업체 기록 합계", note: "면적 × 계수", dark: true, valueSize: 30 });
  stat(s, 10.63, 1.95, 2.1, 1.65, { value: "101", unit: "kg", label: "3D 부피 × 밀도", note: "범위 15~1,328 kg", dark: true, color: C.accent2, valueSize: 30 });
  stat(s, 8.3, 3.75, 2.1, 1.55, { value: "78", unit: "배", label: "차이", note: "1.54 m² 더미: 18 g vs 0.3~17 kg", dark: true, valueSize: 30 });
  stat(s, 10.63, 3.75, 2.1, 1.55, { value: "1 → 6", unit: "장", label: "마대 계획 (20 kg 기준)", note: "트럭·인원 계획이 통째로 틀어짐", dark: true, valueSize: 26 });
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.45, w: 12.13, h: 1.1, fill: { color: "124A6E" }, line: { color: "124A6E" }, rectRadius: 0.12, objectName: "money card" });
  s.addImage({ data: ICON.FaCoins_o, x: 0.95, y: 5.75, w: 0.5, h: 0.5, objectName: "icon coins" });
  tb(s, "돈으로 환산하면", { x: 1.7, y: 5.52, w: 10.8, h: 0.35, fontSize: 13, bold: true, color: C.background1 });
  tb(s, "해양쓰레기 처리 단가는 톤당 약 50만 원(전남). 무게를 100 t 잘못 잡으면 5천만 원, 트럭 한 대를 더 부르면 하루 인력·장비가 추가됩니다. 지금 기록 방식으로는 이 오차가 수십~수백 배 단위로 들어 있습니다.", { x: 1.7, y: 5.87, w: 10.8, h: 0.65, fontSize: 11, color: C.accent5, valign: "top" });
  source(s, "출처: 업체 라벨 자료(문갑도 MGD 42개)와 팀 분석 · 서비스 수거계획 산출(demo-mungap, 가정 밀도) · 처리 단가 한국일보(2018·2019, 전남 톤당 50만 원)", true);
  s.addNotes("강조 장. 제목 후보: ① 업체 데이터의 오류: 같은 42개가 1.3 kg vs 101 kg ② 높이가 없으면 무게가 없다 ③ 78배: 기록과 실제의 거리. 101 kg도 가정 밀도 계산값이라 질문이 오면 '저울 실측이 1단계'라고 답한다.");

  // 왜 공공이 돈을 쓰는 일인가
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "01 기업이 겪는 문제" });
  s.addText("왜 공공이 돈을 쓰는 일인가: 수거량은 5년간 19.8% 늘었다", { placeholder: "title" });
  sub(s, "해양쓰레기 수거는 지자체와 공단이 발주하는 공공 사업입니다. 2025년 14.5만 톤 수거는 연간 발생량 추정치와 같아, 치워도 현존량이 줄지 않습니다.");
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.95, w: 7.6, h: 4.5, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "연도별 해양폐기물 수거량 (톤)", { x: 0.9, y: 2.1, w: 7, h: 0.35, fontSize: 12, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "수거량(t)", labels: ["2021", "2022", "2023", "2024", "2025"], values: [120736, 126035, 131931, 132686, 144615] }],
    chartBase({ x: 0.8, y: 2.5, w: 7.2, h: 3.85, barDir: "col", valAxisMinVal: 0, valAxisMaxVal: 160000, valAxisLabelFormatCode: "#,##0", dataLabelFormatCode: "#,##0", catAxisLabelFontSize: 11 }));
  stat(s, 8.5, 1.95, 4.23, 1.4, { value: "14.5만", unit: "t / 년", label: "연간 해양쓰레기 발생량 추정", note: "육상 기인 65.3% · 해상 기인 34.7%" });
  stat(s, 8.5, 3.5, 4.23, 1.4, { value: "15.2만", unit: "t", label: "해양에 남아 있는 현존량", note: "침적 13.8만 · 해변 1.2만 · 부유 0.2만 t" });
  stat(s, 8.5, 5.05, 4.23, 1.4, { value: "1,114", unit: "억 원", label: "2026년 해양폐기물 처리 예산", note: "해안쓰레기가 수거량의 76%", color: C.accent2 });
  source(s, "출처: 해양수산부 자료(김선교 의원실, 2026.09) 연도별 수거량 · 해양수산부 「해양폐기물 저감 대책」 발생량·현존량 추정 · 2026년 처리 예산 1,114억 원(해양수산부, 2026.09)");
  s.addNotes("B2G 근거. 제목 후보: ① 왜 공공이 돈을 쓰는 일인가 ② 치워도 줄지 않는 15만 톤 ③ 매년 늘어나는 공공 발주. 1안 채택.");

  // 비용 구조
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "01 기업이 겪는 문제" });
  s.addText("수거 비용은 지자체 몫이고, 추정이 곧 예산이다", { placeholder: "title" });
  sub(s, "그 수거의 90%를 지자체가 수행하고 업체에 발주합니다. 톤 단위 추정 오차가 곧 수천만 원이라, 발주처도 업체도 '미리 재는 것'이 예산 그 자체입니다.");
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.95, w: 6.2, h: 4.5, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "유형별 수거량, 2021~2025 누계 (톤)", { x: 0.9, y: 2.1, w: 5.8, h: 0.35, fontSize: 12, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "수거량(t)", labels: ["해안쓰레기", "침적쓰레기", "부유쓰레기"], values: [499934, 119521, 36548] }],
    chartBase({ x: 0.8, y: 2.5, w: 5.8, h: 3.8, barDir: "bar", valAxisMinVal: 0, valAxisMaxVal: 600000, valAxisLabelFormatCode: "#,##0", dataLabelFormatCode: "#,##0", catAxisLabelFontSize: 11, catAxisOrientation: "maxMin" }));
  stat(s, 7.1, 1.95, 2.7, 2.15, { value: "3,654", unit: "억 원", label: "지자체 수거예산 2017~2022 누계", note: "같은 기간 3.5배 증가" });
  stat(s, 10.03, 1.95, 2.7, 2.15, { value: "50 : 50", unit: "", label: "수거비 국비 : 지방비", note: "지방비는 다시 도비·시군비로 나뉨" });
  stat(s, 7.1, 4.3, 2.7, 2.15, { value: "90", unit: "%", label: "지자체가 처리하는 수거량 비중", note: "공공기관 처리는 10%", color: C.accent2 });
  stat(s, 10.03, 4.3, 2.7, 2.15, { value: "50만", unit: "원/t", label: "처리 단가 (전남, 약)", note: "100 t 오차 = 5천만 원", valueSize: 30 });
  source(s, "출처: 유형별 수거량 해양수산부(2026.09) · 지자체 수거예산·국비 분담·처리 비중 에너지데일리(국회 자료, 2017~2022) · 처리 단가 한국일보(2018·2019, 전남 톤당 50만 원)");
  s.addNotes("제목 후보: ① 수거 비용은 지자체 몫이고, 추정이 곧 예산이다 ② 톤 단위 오차가 수천만 원이 되는 구조 ③ 발주처의 숫자는 어디서 오나. 1안 채택.");

  // 경남 2026 사례
  s = pres.addSlide({ masterName: "DARK_CONTENT", sectionTitle: "01 기업이 겪는 문제" });
  s.addText("한 번의 폭우가 1,180 t을 보낸다: 경남, 2026년 8월", { placeholder: "title" });
  tb(s, "광복절 연휴 폭우로 경남 연안에 1,180 t이 유입됐고 거제·통영이 80%를 차지했습니다. 유입량 추정은 육안과 경험에 기대고, 그 추정이 장비·인력·마대를 정합니다.", { x: 0.6, y: 1.32, w: 12.1, h: 0.45, fontSize: 14, color: C.accent5 });
  stat(s, 0.6, 2.0, 2.9, 2.0, { value: "1,180", unit: "t", label: "유입량 추정 (경남 연안)", note: "육안·경험 기반 집계", dark: true });
  stat(s, 3.7, 2.0, 2.9, 2.0, { value: "757", unit: "t", label: "거제 (통영 190 t)", note: "두 시군이 전체의 80%", dark: true, color: C.accent2 });
  stat(s, 6.8, 2.0, 2.9, 2.0, { value: "3주", unit: "", label: "96% 수거까지 걸린 시간", note: "장비·인력 상시 투입", dark: true });
  stat(s, 9.9, 2.0, 2.83, 2.0, { value: "$29~37M", unit: "", label: "2011년 거제 관광수입 손실", note: "낙동강 유입 쓰레기, Jang et al. 2014", dark: true, valueSize: 28 });
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 4.25, w: 12.13, h: 2.1, fill: { color: "124A6E" }, line: { color: "124A6E" }, rectRadius: 0.12, objectName: "insight card" });
  s.addShape(pres.ShapeType.ellipse, { x: 0.95, y: 4.6, w: 0.7, h: 0.7, fill: { color: H.accent2 }, line: { color: H.accent2 }, objectName: "icon circle" });
  s.addImage({ data: ICON.FaTruck_w, x: 1.12, y: 4.77, w: 0.36, h: 0.36, objectName: "icon truck" });
  tb(s, "남는 트럭과 모자라는 트럭이 동시에 생긴다", { x: 1.95, y: 4.55, w: 10.5, h: 0.45, fontSize: 16, bold: true, color: C.background1 });
  tb(s, "무게가 틀리면 마대·트럭 수가 틀리고, 위치가 틀리면 동선·인원이 틀립니다. 유입 직후 며칠 안에 '어디에 얼마나'를 재서 배차하면 장비 대기 일수와 처리비가 줄어듭니다. 거제는 2011년에도 같은 일을 겪었고, 작은 지자체일수록 수거 전에 재는 것이 예산 그 자체입니다.",
    { x: 1.95, y: 5.05, w: 10.5, h: 1.2, fontSize: 12.5, color: C.accent5, valign: "top" });
  source(s, "출처: 서울신문 2026.09.09 「광복절 연휴 폭우 해양쓰레기, 경남 연안 96% 수거」(1,180 t 유입, 거제 757 t·통영 190 t) · Jang, Hong, Lee, Lee & Shim (2014) Marine Pollution Bulletin 81:49–54", true);
  s.addNotes("제목 후보: ① 한 번의 폭우가 1,180 t을 보낸다 ② 폭우 다음 날, 트럭은 몇 대를 불러야 하나 ③ 거제는 두 번 겪었다. 1안 채택.");

  // ═════════ 02 과제와 과정 ═════════
  pres.addSection({ title: "02 과제와 과정" });
  divider("02", "우리가 받은 과제와 과정", "위성-드론 정합이라는 과제로 시작해, 업체의 두 마디로 주제가 바뀌었고, 이틀 동안 세 번 날렸습니다.", "02 과제와 과정");

  // 받은 과제와 바뀐 주제
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "02 과제와 과정" });
  s.addText("받은 과제와 바뀐 주제", { placeholder: "title" });
  sub(s, "처음 과제는 위성·드론 영상 정합과 변화탐지였습니다. 업체가 현장에서 겪는 문제 두 가지를 듣고, 정합을 '위치 엔진'으로 재활용하는 쪽으로 주제를 바꿨습니다.");
  const stage = [
    ["FaSatellite", "처음 받은 과제", "위성-드론 영상 정합과 변화탐지", ["LoFTR·LightGlue 정합, Sentinel-2·SkySat", "SkySat↔Sentinel-2 정합 인라이어 85%, 어긋남 5~8 m", "변화탐지 파이프라인(07_change_detection)"]],
    ["FaComments", "업체가 말한 문제", "\"위치가 50 m씩 어긋나고, 2D만 보고 가니 생각보다 크고 무겁다\"", ["탐지 위치와 실제 위치가 50 m 차이", "크기·무게를 몰라 트럭·마대가 틀림", "업체 무게 기록은 면적 × 계수(실측 아님)"]],
    ["FaCubes", "바뀐 주제", "드론 영상 기반 위치·부피·무게 추정 → 수거계획", ["정합 기술은 3D 위치 정렬·위성 해안선 갱신에 재활용", "위성은 '어디를 날지' 고르는 역할로", "결과를 좌표 목록이 아니라 작업카드로"]],
  ];
  stage.forEach((t, i) => {
    const x = 0.6 + i * 4.1;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.95, w: 3.9, h: 4.45, fill: { color: i === 2 ? H.dk2 : H.lt1 }, line: { color: i === 2 ? H.dk2 : H.lt1 }, rectRadius: 0.12, shadow: i === 2 ? undefined : shadow(), objectName: "stage " + t[1] });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: 2.25, w: 0.62, h: 0.62, fill: { color: i === 2 ? H.accent2 : H.dk2 }, line: { color: i === 2 ? H.accent2 : H.dk2 }, objectName: "icon circle" });
    s.addImage({ data: ICON[t[0] + "_w"], x: x + 0.45, y: 2.4, w: 0.32, h: 0.32, objectName: "icon " + t[0] });
    tb(s, t[1], { x: x + 1.05, y: 2.3, w: 2.6, h: 0.5, fontSize: 11, color: i === 2 ? C.accent5 : C.accent4, valign: "middle" });
    tb(s, t[2], { x: x + 0.3, y: 3.05, w: 3.3, h: 0.9, fontSize: 14, bold: true, color: i === 2 ? C.background1 : C.text1, valign: "top" });
    bullets(s, t[3], { x: x + 0.3, y: 4.05, w: 3.3, h: 2.2, fontSize: 11, color: i === 2 ? C.accent5 : C.text1 });
    if (i < 2) s.addShape(pres.ShapeType.rightArrow, { x: x + 3.92, y: 3.95, w: 0.17, h: 0.4, fill: { color: H.accent2 }, line: { color: H.accent2 }, objectName: "arrow" });
  });
  source(s, "출처: 해안쓰레기_수거계획_방향정리.md(2026-09-30) 0~2절, 기술정리_전체.md 4절 · 업체 제보 2건");
  s.addNotes("과제 소개. 정합을 버린 게 아니라 위치 엔진으로 재활용했음을 강조.");

  // 과정과 노력
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "02 과제와 과정" });
  s.addText("이틀의 과정: 날리고, 재고, 고치고, 접은 것", { placeholder: "title" });
  sub(s, "줌 회의로 방향을 정하고 역할을 나눴습니다. 결과가 안 나온 것도 적었습니다.", 10.4);
  const tl = [
    ["9/30", "방향 전환", "업체 문제 정리, 위치 오차 원인표, 무게 선행연구 빈칸 확인, 업체 확인 체크리스트"],
    ["10/1 낮", "송도 촬영 · 학습셋", "선회 0007(7 m)·골목 왕복 0010(2 m) 촬영, AI Hub 1.2만 장을 2~4 cm/px로 축소한 학습셋"],
    ["10/1 밤", "야간 촬영 · 3D v2", "야간 0015(10분) 촬영, SAM 2 마스크 투표 + 지역 바닥 평면, 조밀 복원 45분 → 3분 24초"],
    ["10/2", "위성·해류 · 서비스", "위성 형상 점수와 전략 비교(니하우), OpenDrift 문갑도, 인천 조석 결합, 마스킹·KML 내보내기"],
  ];
  tl.forEach((t, i) => {
    const x = 0.6 + i * 3.075;
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.1, y: 2.05, w: 0.5, h: 0.5, fill: { color: i === 3 ? H.accent2 : H.dk2 }, line: { color: i === 3 ? H.accent2 : H.dk2 }, objectName: "dot" });
    if (i < 3) s.addShape(pres.ShapeType.line, { x: x + 0.6, y: 2.3, w: 2.5, h: 0, line: { color: H.accent5, width: 2 }, objectName: "line" });
    tb(s, t[0], { x: x + 0.75, y: 2.05, w: 2.3, h: 0.5, fontSize: 13, bold: true, color: C.text2, valign: "middle" });
    s.addShape(pres.ShapeType.roundRect, { x, y: 2.7, w: 2.9, h: 1.75, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.1, shadow: shadow(), objectName: "tl " + t[1] });
    tb(s, t[1], { x: x + 0.2, y: 2.8, w: 2.5, h: 0.35, fontSize: 12.5, bold: true });
    tb(s, t[2], { x: x + 0.2, y: 3.15, w: 2.5, h: 1.25, fontSize: 10.5, color: C.accent4, valign: "top" });
  });
  card(s, 0.6, 4.65, 6.0, 1.85, { icon: "FaTimesCircle", head: "만들었다가 접은 것", body: "실시간 미러링 탐지(live.py, 기체 SDK 없음) · VGGT·MASt3R·단안 깊이·3DGS(축척 불안정) · Isaac Sim(VRAM 16 GB) · 합성 해변 데이터(초기 검증용) · YOLO-World 범용 탐지(항공 작은 물체 0.01) · 정합·변화탐지 파이프라인(보류 → 위치 엔진으로)", headSize: 13, bodySize: 10.5, iconColor: H.accent4, inline: true });
  card(s, 6.73, 4.65, 6.0, 1.85, { icon: "FaSync", head: "고친 것", body: "작은 상자 −3%는 바닥 잡음이 상쇄한 우연(v1) → v2 +19%로 정직하게 수정 · SRT 고도가 틀린 영상 2편(0010·0015)은 GPS 경로로 축척 자동 선택 · 탐지 모델은 현장별 엇갈림을 확인하고 단일 통합 모델 노선으로", headSize: 13, bodySize: 10.5, inline: true });
  source(s, "출처: 기술정리_전체.md 4·5절, 파이프라인_결과정리.md, 미해결_과제.md(10-02). 줌 회의 일정·횟수는 팀이 기입.");
  s.addNotes("노력 장. 줌 회의 횟수·날짜는 팀이 채운다.");

  // 실제 촬영
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "02 과제와 과정" });
  s.addText("실제로 날려서 찍었다: 송도 선회 7 m · 골목 왕복 2 m · 야간 10분", { placeholder: "title" });
  sub(s, "시뮬레이션만이 아닙니다. DJI 기본 기체로 2026년 10월 1일 세 번 비행했고, 아래 프레임이 그 영상에서 탐지·복원된 결과입니다.");
  pic(s, "fig_02_탐지결과_모음.jpg", 0.6, 1.95, 6.3, 3.54, "0007 탐지 결과 프레임");
  cap(s, "0007 송도 선회(고도 7 m, 100프레임): 상자 2개와 사람·오토바이·자전거까지 탐지. 지도 핀이 상자 위치와 일치.", 0.6, 5.52, 6.3, 0.45);
  pic(s, "fig_13_0007_조밀_큰상자_마스크.jpg", 7.15, 1.95, 5.58, 1.4, "0007 큰 상자 SAM 마스크");
  cap(s, "0007 큰 상자(60×45×12 cm): 24프레임 SAM 2 마스크 투표로 점구름에서 상자 점만 분리 → 3D 62×49×13.5 cm", 7.15, 3.37, 5.58, 0.4);
  pic(s, "fig_15_0010_키큰상자_마스크_v2.jpg", 7.15, 3.85, 5.58, 1.4, "0010 키 큰 상자 마스크");
  cap(s, "0010 골목 왕복(고도 2 m): 키 큰 상자 42×32×39 cm → 3D 49×37×38 cm, 부피 −10%", 7.15, 5.27, 5.58, 0.4);
  s.addShape(pres.ShapeType.roundRect, { x: 7.15, y: 5.75, w: 5.58, h: 0.8, fill: { color: H.lt2 }, line: { color: H.lt2 }, rectRadius: 0.1, objectName: "night" });
  tb(s, "0015 야간 10분(4K 60 fps, 531 m): 종이상자 30개를 자동 지도화, 25구간 모두 3D 뼈대 성공. 밤에도 탐지·위치는 된다.", { x: 7.35, y: 5.75, w: 5.2, h: 0.8, fontSize: 10.5, bold: true, color: C.text2, valign: "middle" });
  source(s, "촬영: 2026-10-01 송도(37.3843, 126.6571) DJI Mini 5 Pro, SRT 비행기록 포함 · 그림: docs/figures/02·13·15, 0015_objects.csv");
  s.addNotes("현실성 장. '진짜 날려서 찍은 것'을 먼저 보여 준다.");

  // ═════════ 03 솔루션: 기술 소개 ═════════
  pres.addSection({ title: "03 솔루션" });
  divider("03", "솔루션: 기술 소개", "두 가지 기술입니다. 위성·해류로 어디를 날지 고르는 선별, 드론 영상 하나로 재는 3D 측정. 그 끝에 수거계획이 나옵니다.", "03 솔루션");

  // 한 문장 + 파이프라인
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "03 솔루션" });
  s.addText("한 문장으로: 위성이 고르고, 드론이 재고, 소프트웨어가 배차한다", { placeholder: "title" });
  sub(s, "DroneSweep은 드론 영상(MP4)과 비행기록(SRT)을 받아 수거계획서를 내는 소프트웨어입니다. 비행은 조종자가 하고, 나머지 7단계는 노트북 한 대가 합니다.");
  card(s, 0.6, 1.95, 6.0, 1.55, { icon: "FaSatellite", head: "기술 A · 선별: 어디를 날지 고른다", body: "위성 해안 형상(만입도·풍향 노출·띠 폭)과 해류·조석 방향으로 200 m 구간마다 점수를 매겨, 쌓이는 자리 상위 30%만 비행 경로(KML)로 만듭니다.", headSize: 13.5, bodySize: 10.5, inline: true });
  card(s, 6.73, 1.95, 6.0, 1.55, { icon: "FaCubes", head: "기술 B · 측정: 무엇이 어디에 얼마나 있는지 잰다", body: "영상에서 쓰레기를 탐지하고, 3D 카메라 자세로 위치를 정렬하고, SfM 점구름에서 부피를 재서 무게 구간을 냅니다. 정사영상·DSM 없이 영상 하나로.", headSize: 13.5, bodySize: 10.5, inline: true });
  stepRow(s, [
    { icon: "FaSatellite", name: "어디를 날지", desc: "위성 형상 점수 + 해류·조석 방향" },
    { icon: "FaPlane", name: "조종자 비행", desc: "KML 경로, 고도 20 m, 애매한 곳 8 m" },
    { icon: "FaSearchLocation", name: "탐지", desc: "YOLO11-s 타일 추론, 통합 학습셋" },
    { icon: "FaCrosshairs", name: "위치", desc: "3D 카메라 자세 광선 교차 → GPS" },
    { icon: "FaCubes", name: "부피", desc: "SfM+MVS, SAM 2 투표, 높이지도" },
    { icon: "FaRulerCombined", name: "무게 구간", desc: "겉보기밀도 × 젖음·압축 계수" },
    { icon: "FaTruck", name: "수거계획", desc: "정거장·마대·트럭·인력·경로 작업카드", hl: true },
  ], 3.65, 2.1);
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.87, w: 12.13, h: 0.68, fill: { color: H.accent6 }, line: { color: H.accent6 }, rectRadius: 0.1, objectName: "io" });
  tb(s, "입력: 드론 영상 + 비행기록(SRT)  ·  출력: 지도 핀(위치·오차반경) · 물체 목록(부피·무게 구간 CSV/GeoJSON) · 정거장별 작업카드(인력·마대·트럭·경로) · 비행 경로 KML. 3DLabs 위성 ARD는 1단계(해안선 갱신·형상 점수)에 들어갑니다.", { x: 0.85, y: 5.87, w: 11.6, h: 0.68, fontSize: 10.5, bold: true, color: C.text2, valign: "middle" });
  s.addNotes("솔루션 개괄. 기술 두 덩어리를 한 줄씩 먼저 말하고, 7단계는 그 다음.");

  // 기술 A-1 위성 형상 점수
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "03 솔루션" });
  s.addText("기술 A · 어디를 날지: 위성 해안 형상 점수", { placeholder: "title" });
  sub(s, "위성 10 m 픽셀로는 쓰레기가 안 보입니다. 대신 해안선의 '모양'을 재서 쌓이기 쉬운 구간을 점수화하고, 드론 정밀 촬영은 점수 상위 구간에만 씁니다.");
  pic(s, "fig_26_문갑도_우선구간_비행경로.jpg", 0.6, 1.95, 4.0, 4.42, "문갑도 우선 구간 비행경로");
  cap(s, "문갑도: 점수 상위 30%(주황)와 소티별 코리더 경로, 집결지·이륙점.", 0.6, 6.38, 4.0, 0.3);
  const fs_ = [
    ["Sentinel-2 L2A", "맑은 장면 3개를 NDWI 최댓값으로 합성해 육지·물을 가르고 해안선을 10 m 표본점으로 뽑습니다."],
    ["세 가지 형상 특징", "만입도 = 1 − 반경 150 m 안 물 비율(오목할수록 큼) · 노출 = cos(법선 방위 − 풍향) · 띠 폭 = 물도 식생도 아닌 안쪽 길이(NDVI)"],
    ["점수와 구간", "점수 = z(만입도) + 0.5 z(노출) + 0.5 z(log 띠 폭), 해안선 방향 100 m 이동평균 → 200 m 구간 → 점수 순으로 길이 예산(30%)을 채움"],
    ["경로와 소티", "선택 구간마다 해안선을 안쪽으로 밀어 코리더 웨이포인트 → 최근접 이웃 + 2-opt → 소티당 비행거리 예산(기본 5 km)으로 자름 → KML"],
  ];
  fs_.forEach((f, i) => {
    const y = 1.95 + i * 1.12;
    s.addShape(pres.ShapeType.roundRect, { x: 4.85, y, w: 7.88, h: 1.0, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.1, shadow: shadow(), objectName: "fs " + f[0] });
    tb(s, String(i + 1), { x: 5.05, y, w: 0.5, h: 1.0, fontSize: 22, bold: true, color: C.accent2, valign: "middle" });
    tb(s, f[0], { x: 5.6, y: y + 0.12, w: 7.0, h: 0.3, fontSize: 12.5, bold: true });
    tb(s, f[1], { x: 5.6, y: y + 0.42, w: 7.0, h: 0.55, fontSize: 10.5, color: C.accent4, valign: "top" });
  });
  refs(s, "코드: route_optimization/litter3d/priority.py · 입력은 Sentinel-2 공개 자료(AWS COG)라 비용 0, 상용 고해상 위성(3DLabs ARD)은 띠 폭·해안선 정확도를 올리는 상위 입력", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("기술 소개만. 검증 수치(62~67%)는 4장에서.");

  // 기술 A-2 해류·조석 분석
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "03 솔루션" });
  s.addText("기술 A · 해류·조석 분석: 어느 면에 쌓이는가", { placeholder: "title" });
  sub(s, "형상 점수는 '어느 200 m'를 고르고, 해류·조석은 '어느 섬·어느 면'을 고릅니다. 두 층을 겹쳐 씁니다.");
  // 왼쪽 열: 우리 조석 모델 두 프레임 (16:9, 3.5×1.97) / 가운데: OpenDrift 경기만 / 오른쪽: 문갑도
  pic(s, "fig_frame_00390.jpg", 0.6, 1.95, 3.5, 1.97, "인천·강화 조류 흐름");
  cap(s, "① 우리 조석 모델(M2+S2 연속방정식): 인천·강화 200 m 격자의 조류 흐름장, 입자 15,000개·30일.", 0.6, 3.94, 3.5, 0.36);
  pic(s, "fig_frame_01811.jpg", 0.6, 4.32, 3.5, 1.97, "집적 예상 해안");
  cap(s, "① 30일 뒤 좌초 분포 → 집적 해안 상위 구간(붉은색).", 0.6, 6.31, 3.5, 0.28);
  pic(s, "fig_40_stranding_density_map.jpg", 4.3, 1.95, 4.2, 2.66, "경기만 OpenDrift 좌초 밀도");
  cap(s, "② OpenDrift(Open-Meteo·Copernicus SMOC 1/12°, 조석 포함): 90일 표류·좌초, 해안 200 m 구간 밀도 → 집적 해안 상위 15%.", 4.3, 4.63, 4.2, 0.48);
  card(s, 4.3, 5.15, 4.2, 1.4, { head: "쓰임: 두 층 규칙", body: "광역 층(조석 모델·해류 통계)이 어느 섬·어느 면인지를, 국지 층(위성 형상)이 그 면 안의 어느 200 m인지를 정합니다. 해류에서 뽑은 풍향·잔차류 방향은 형상 점수의 '노출' 입력이 됩니다.", headSize: 12.5, bodySize: 10 });
  pic(s, "fig_50_mungap_stranding_vs_labels_map.jpg", 8.7, 1.95, 4.03, 3.87, "문갑도 OpenDrift 좌초 vs 라벨");
  cap(s, "③ 문갑도: 조사일 전 8주 입자 16,000개 좌초(주황)와 업체 라벨 42개(별). KHOA 조류예보로 위상·회전·유속 보정.", 8.7, 5.85, 4.03, 0.6);
  source(s, "모델: incheon_debris_sim(조석 연속방정식) · OpenDrift 1.14(RK4 20분, 풍압 2%, 확산 10 m²/s) · 자료: Open-Meteo Marine(SMOC), ERA5 바람, KHOA 조류예보, Sentinel-2 해안선");
  s.addNotes("해류 분석 장. 그림 ①은 우리 조석 모델, ②③은 OpenDrift. 수치 평가는 4장.");

  // 기술 B-1 촬영 거리
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "03 솔루션" });
  s.addText("기술 B · 촬영 거리는 물체 크기에서 역산했다", { placeholder: "title" });
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
  tb(s, "선회 촬영 가이드", { x: 1.7, y: 5.42, w: 10.5, h: 0.35, fontSize: 13, bold: true, color: C.background1 });
  tb(s, "고도 3~4 m · 반경 3 m · 짐벌 45° 한 바퀴 + 수직 1장 · SRT 켜기 · 기준 물체 1개. 1차 커버리지는 20 m 통과 비행으로 충분하고(야간 10분 비행에서 상자 30개 탐지·지도화), 부피가 필요한 물체만 선회합니다. 3·5·7 m 선회 통제 실험으로 고도별 편향을 확정할 예정.", { x: 1.7, y: 5.78, w: 10.8, h: 0.7, fontSize: 10.5, color: C.accent5, valign: "top" });
  refs(s, "근거: Andriolo, Topouzelis, van Emmerik et al. (2023) Marine Pollution Bulletin 195:115521 · Andriolo & Gonçalves (2022) Environmental Pollution 315:120370 · Kako, Morita & Taneda (2020) MPB 155:111127", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("'왜 그 거리에서 찍나'. 숫자는 4K 24 mm 기준 계산값이며 실제 기체 스펙으로 확정 예정.");

  // 기술 B-2 탐지와 3D 위치
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "03 솔루션" });
  s.addText("기술 B · 탐지와 3D 위치: 영상 한 편에서 핀을 찍는다", { placeholder: "title" });
  sub(s, "프레임마다 쓰레기를 찾고, 영상 전체로 3D 카메라 자세를 복원한 뒤, 탐지 박스에서 광선을 쏴 지면과 만나는 점을 GPS에 정렬합니다.");
  pic(s, "fig_04_물체위치_개요.jpg", 0.6, 1.95, 4.0, 4.0, "탐지 물체 위치 3D 기준");
  cap(s, "0007: 3D로 복원한 드론 경로(선)와 탐지 물체 위치(점). 상자 2개가 지도 핀과 일치.", 0.6, 5.97, 4.0, 0.45);
  const det = [
    ["FaSearchLocation", "탐지: YOLO11-s 타일 추론", "4K 프레임을 1024 타일(겹침 0.2)로 나눠 추론 후 병합. 학습셋은 AI Hub 2,375 + 하와이 1,109 + 튀니지 1,900 + 문갑도 21 = 5,405장·13클래스 통합(운용 고도 해상도 2~4 cm/px로 축소). 현장 신종은 개방형 탐지로 이름만 추가."],
    ["FaCrosshairs", "3D 위치: 카메라 자세 → 광선 → 지면", "pycolmap SfM으로 100프레임 카메라 자세 복원 → 탐지 박스 중심 광선을 지면과 교차 → GPS 경로에 정렬. 축척은 SRT 고도·GPS 경로 중 자동 선택, 호버링(시차 5° 미만)은 평면 교차로 복귀, 물체마다 오차반경(r95) 기록."],
    ["FaMapMarkerAlt", "출력: 지도 핀 + 사진 카드", "Leaflet 위성지도에 핀·썸네일, objects.csv/geojson. 수거자가 도착해서 눈으로 찾도록 주변 표지물이 보이는 사진을 함께 냅니다."],
  ];
  det.forEach((d, i) => card(s, 4.85, 1.95 + i * 1.57, 7.88, 1.5, { icon: d[0], head: d[1], body: d[2], headSize: 12.5, bodySize: 10, inline: true }));
  refs(s, "코드: litter/seg.py, orbit3d.py(pycolmap), orbit_map.py, triangulate.py · 근거: Martin et al. 2018 MPB 131 · Fallati et al. 2019 STOTEN 693 · Hartley & Sturm 1997 CVIU 68", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("기술 소개. 재현율·잔차 수치는 4장.");

  // 기술 B-3 부피와 무게
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "03 솔루션" });
  s.addText("기술 B · 부피와 무게: 점구름에서 물체 점만 남겨 높이를 잰다", { placeholder: "title" });
  sub(s, "핵심 차별점. 정사영상·DSM을 따로 만들지 않고 영상 하나로 3D 부피까지 갑니다. 무게는 점이 아니라 구간으로 냅니다.");
  pic(s, "fig_13_0007_조밀_큰상자_마스크.jpg", 0.6, 1.95, 7.3, 1.82, "SAM 2 마스크 투표");
  cap(s, "같은 상자를 24프레임에서 SAM 2로 마스킹하고, 각 3D 점이 마스크 안에 든 비율로 투표(70% 이상)해 상자 점만 남깁니다.", 0.6, 3.8, 7.3, 0.4);
  const vol = [
    ["1", "조밀 점구름", "COLMAP PatchMatch(GPU) 243만 점. 빠른 설정으로 45분 → 3분 24초, RAM 16 GB 노트북에서 안정"],
    ["2", "마스크 투표", "SAM 2.1 점 프롬프트 24프레임 → 마스크 일치율 70% 이상인 점만 물체"],
    ["3", "지역 바닥 평면", "링 점 RANSAC 평면 기준 높이, 바닥점(<3 cm) 제거, 뒤집힌 카메라 포즈 자동 제외"],
    ["4", "높이지도 부피", "격자별 높이 합. 윗면 높이는 히스토그램 상단 봉우리(볼록껍질은 +60% 과대라 폐기)"],
  ];
  vol.forEach((v, i) => {
    const y = 4.3 + i * 0.56;
    tb(s, v[0], { x: 0.6, y, w: 0.4, h: 0.5, fontSize: 16, bold: true, color: C.accent2, valign: "middle" });
    tb(s, v[1], { x: 1.05, y, w: 1.6, h: 0.5, fontSize: 11, bold: true, valign: "middle" });
    tb(s, v[2], { x: 2.7, y, w: 5.2, h: 0.5, fontSize: 9.5, color: C.accent4, valign: "middle" });
  });
  card(s, 8.2, 1.95, 4.53, 2.15, { icon: "FaRulerCombined", head: "무게 = 부피 × 겉보기밀도 → 구간", body: "스티로폼 20~25, 플라스틱 60, 어망·로프 100~400 kg/m³에 젖음 계수(어망 2.0)·마대 압축비. 실측 30개가 모이면 conformal 예측구간(포함확률 90%)으로 교체(코드 완료).", headSize: 12.5, bodySize: 10 });
  card(s, 8.2, 4.25, 4.53, 2.25, { icon: "FaBullseye", head: "구간이 있어야 '다시 갈 곳'이 정해진다", body: "구간 상한이 1인 운반 한계 23 kg(NIOSH)·마대·트럭 적재 경계를 넘나드는 물체만 2차 선회. 면적은 넓은데 높이가 없으면 '묻힘 의심' 태그. 2 kg짜리가 1인지 3인지는 안 가고, 20 kg짜리가 23을 넘는지는 갑니다.", headSize: 12.5, bodySize: 10 });
  refs(s, "코드: litter/objvol.py v2, volume.py, weight.py · 근거: Westoby et al. 2012 Geomorphology 179 · Kako et al. 2020 MPB 155 · Angelopoulos & Bates 2023 Found. Trends ML 16", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("기술 소개. 상자 오차 수치는 4장.");

  // 기술 C 수거계획과 운용
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "03 솔루션" });
  s.addText("기술 C · 수거계획과 운용: 비행은 조종자, 나머지는 소프트웨어", { placeholder: "title" });
  sub(s, "물체 목록이 작업카드가 되기까지. 자동비행은 제품 전제에서 뺐고, 비행 구역은 위성 타일로 자동 마스킹합니다.");
  pic(s, "fig_18_하와이_niihau_지도_수거계획.jpg", 0.6, 1.95, 6.3, 2.78, "니하우 수거계획 출력 예시");
  cap(s, "출력 예시(니하우): 섬 해안 물체와 수거 경로(왼쪽), 가장 밀집한 120×120 m 구간의 재질별 점(오른쪽).", 0.6, 4.75, 6.3, 0.4);
  card(s, 0.6, 5.2, 6.3, 1.3, { head: "작업카드 (plan.py · report.py)", body: "반경 기반 클러스터 → 정거장 → 정거장별 인력(1인/2인/장비)·마대(압축 후 부피·무게)·1톤 트럭 → 집하장 출발 최근접 이웃 + 2-opt 순회 경로 → HTML 카드(썸네일·위경도·추정/최대 kg·휴대폰 길찾기)", headSize: 12, bodySize: 10 });
  card(s, 7.15, 1.95, 5.58, 1.45, { icon: "FaPlane", inline: true, head: "조종자 비행 + KML 내보내기", body: "핫스팟 경로를 KML로 내보내 Google Earth·Litchi에서 열고 조종자가 비행. DJI Fly용 KMZ 변환은 확인 전. 배터리는 소티당 비행거리 예산 한 변수.", headSize: 12, bodySize: 10 });
  card(s, 7.15, 3.52, 5.58, 1.45, { icon: "FaLayerGroup", inline: true, head: "비행 구역 자동 마스킹 (구현)", body: "위성 타일(약 1 m/px) 지형분류로 바다·갯벌·숲을 빼고 물에 닿은 땅의 외곽선만 해안선(100 m 구간)으로. 해안 띠 밖 사진은 쓸모없고 배터리를 낭비하며 바다 추락은 기체 손실이라서.", headSize: 12, bodySize: 10 });
  card(s, 7.15, 5.09, 5.58, 1.41, { icon: "FaRedo", inline: true, head: "능동 재방문 + 노트북 한 대", body: "애매한 후보(신뢰도 0.25~0.5)는 8 m로 내려가 3장 재촬영 후 확정·기각. 탐지·3D·작업카드는 RTX 4060 8 GB·RAM 16 GB 노트북에서 돌아갑니다.", headSize: 12, bodySize: 10 });
  refs(s, "코드: litter/plan.py, report.py, fromvideo.py, sim_ortho.py · 서비스 app/region.py(마스킹), route.kml 내보내기", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("기술 C. 수거 접근로·로드뷰는 미구현이라 말하지 않는다(질문 오면 로드맵).");

  // ═════════ 04 검증 ═════════
  pres.addSection({ title: "04 검증" });
  divider("04", "검증", "7단계 중 6단계를 실제 데이터로 확인했습니다. 상자 3개, 영상 3편, 해안 3곳.", "04 검증");

  // 검증 맵
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "04 검증" });
  s.addText("검증 맵: 파이프라인의 어디를 무엇으로 확인했나", { placeholder: "title" });
  sub(s, "초록 = 실제 데이터로 확인. 회색 = 실측 데이터를 기다리는 중.");
  stepRow(s, [
    { icon: "FaSatellite", name: "어디를 날지", desc: "니하우 상위 30% 길이에 67%\n문갑도 라벨 62%\n인천 하구 조석 모델 99%" },
    { icon: "FaPlane", name: "비행", desc: "야간 10분 통과 비행으로\n상자 30개 지도화\n3D 뼈대 25/25 구간" },
    { icon: "FaSearchLocation", name: "탐지", desc: "문갑도 재현율 0.72\n(공개 모델 0.28)\n하와이 미세조정 0.69" },
    { icon: "FaCrosshairs", name: "위치", desc: "3D↔GPS 잔차 1.16 m\n축척 자동 8.07→0.51 m\n합성 7개 0.01~0.11 m" },
    { icon: "FaCubes", name: "부피", desc: "상자 3개 ±20% 안\n+19 / +20 / −10%\n업체 방식 1/112·1/180" },
    { icon: "FaRulerCombined", name: "무게 구간", desc: "가정 밀도로 산출\n저울 실측 30개\n확보 예정", ok: false },
    { icon: "FaTruck", name: "수거계획", desc: "니하우 5,476개 →\n마대 1,082 · 트럭 37\n경로 71.9 km", hl: true },
  ], 1.95, 2.75, { descSize: 9.5 });
  // 체크 표시
  for (let i = 0; i < 7; i++) {
    const w = (12.13 - 0.075 * 6) / 7, x = 0.6 + i * (w + 0.075);
    const ok = i !== 5;
    s.addShape(pres.ShapeType.ellipse, { x: x + w - 0.42, y: 2.05, w: 0.3, h: 0.3, fill: { color: ok ? "0A7A2F" : H.accent4 }, line: { color: ok ? "0A7A2F" : H.accent4 }, objectName: "check" });
    s.addImage({ data: ICON.FaCheck_w, x: x + w - 0.35, y: 2.12, w: 0.16, h: 0.16, objectName: "check icon" });
  }
  stat2(s, 0.6, 4.95, 2.9, 1.5, { value: "6 / 7", unit: "단계", label: "실제 데이터로 확인한 단계", note: "무게 구간만 실측 대기" });
  stat2(s, 3.68, 4.95, 2.9, 1.5, { value: "3 · 3 · 3", unit: "", label: "상자 · 영상 · 해안", note: "상자 3개, 영상 0007·0010·0015, 니하우·문갑도·인천" });
  stat2(s, 6.75, 4.95, 2.9, 1.5, { value: "9", unit: "건", label: "완료한 검증 실험", note: "요약표는 이 장 끝에" });
  stat2(s, 9.83, 4.95, 2.9, 1.5, { value: "2배", unit: "", label: "같은 자원으로 찾는 양", note: "핫스팟 30% 67% vs 무작위 29%", color: C.accent2 });
  s.addNotes("검증 맵. 긍정 프레임: 6/7 확인. 무게 실측은 '예정'으로만.");

  // 검증 ① 어디를 날지
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "04 검증" });
  s.addText("검증 ① 어디를 날지: 상위 30% 구간에 쓰레기의 62~67%가 있었다", { placeholder: "title" });
  sub(s, "같은 카메라·같은 띠 폭·같은 배터리로 비교했습니다. 위성 형상 점수 상위 30%만 날면 전체 지그재그의 37% 시간으로 탐지 무게의 67%를 잡습니다(니하우).");
  pic(s, "fig_22_시간대비포착_핫스팟_vs_지그재그.jpg", 0.6, 1.95, 6.1, 3.97, "니하우 시간 대비 포착");
  cap(s, "니하우 해안 98.8 km, 고도 20 m·GSD 2.9 cm·8패스. 파란 선이 핫스팟, 주황이 지리 순서, 점선이 무작위.", 0.6, 5.95, 6.1, 0.5);
  stat2(s, 6.95, 1.95, 2.8, 1.45, { value: "67", unit: "%", label: "니하우: 상위 30% 길이가 잡는 무게", note: "15.4 h vs 전체 41.3 h. 같은 시간 무작위 29%", color: C.accent2 });
  stat2(s, 9.93, 1.95, 2.8, 1.45, { value: "62", unit: "%", label: "문갑도: 라벨 42개 중 상위 30% 안", note: "만입도만 62%, 잔차류·풍향 더하면 67%" });
  stat2(s, 6.95, 3.52, 2.8, 1.45, { value: "99", unit: "%", label: "인천 하구: 조석 모델 집적 해안", note: "13% 길이로 448 h → 57 h" });
  stat2(s, 9.93, 3.52, 2.8, 1.45, { value: "0.88", unit: "", label: "다시 쌓인다: 앞/뒤 기간 순위상관", note: "NOAA MDMAP 134곳 반복조사, 상위 20% 유지 74%" });
  card(s, 6.95, 5.1, 5.78, 1.4, { head: "읽는 법", body: "외해 섬(니하우·문갑도)은 위성 형상이, 하구·항만(인천)은 조석 모델이 맞혔습니다. 공간 군집은 자료로 확인했고(니하우 만 244 vs 곶 40 kg/km), 시간 반복은 미국 반복조사로 뒷받침됩니다.", headSize: 12.5, bodySize: 10.5 });
  refs(s, "자료: Sentinel-2 10 m 해안선 · 하와이 탐지 격자 5,476개(Zenodo 8381113) · 업체 라벨 42개(2026-07-29) · NOAA MDMAP · route_optimization/docs, hotspot/", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("긍정 프레임. '선택 안 된 70%는 관측 없음'은 질문 때 답한다: 핫스팟 정기 + N회에 1번 전수 + 20% 무작위 표본.");

  // 검증 ② 탐지·위치
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "04 검증" });
  s.addText("검증 ② 탐지와 위치: 재현율 0.72, 위치 잔차 1 m대", { placeholder: "title" });
  sub(s, "운용 고도 해상도로 학습한 모델이 업체 정사영상에서 쓰레기 10개 중 7개를 찾고, 3D 위치는 GPS와 1.16 m 안에서 맞습니다. 낯선 해안에서도 10분 미세조정으로 0.69까지.");
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.95, w: 5.6, h: 2.75, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "탐지 재현율, 현장별 (클래스 무시, IoU 0.3)", { x: 0.85, y: 2.05, w: 5.2, h: 0.3, fontSize: 11.5, bold: true });
  s.addChart(pres.ChartType.bar, [
      { name: "공개 모델 그대로", labels: ["문갑도 칩 48", "하와이 420칩", "튀니지 179장"], values: [0.28, 0.24, 0.14] },
      { name: "DroneSweep 학습·미세조정", labels: ["문갑도 칩 48", "하와이 420칩", "튀니지 179장"], values: [0.72, 0.69, 0.52] },
    ],
    chartBase({ x: 0.7, y: 2.4, w: 5.4, h: 2.25, barDir: "col", valAxisMinVal: 0, valAxisMaxVal: 1, dataLabelFormatCode: "0.00", catAxisLabelFontSize: 10, valAxisLabelFormatCode: "0.0", chartColors: [H.accent4, H.accent1], showLegend: true, legendPos: "b", legendFontSize: 9, legendFontFace: "+mn-lt", legendColor: H.accent4, barGapWidthPct: 80 }));
  card(s, 0.6, 4.85, 5.6, 1.65, { head: "무엇이 올렸나", body: "문갑도: 공개 UAVVaste 0.28 → AI Hub 거리별 학습 0.72(스티로폼 0.81). 하와이: 재학습 없이 0.24 → 현지 사진 10분 미세조정 0.58 → 8클래스·1024 px 0.69(AP50 0.62). 튀니지: 통합 학습 0.14 → 0.52. 야간 종이상자 30개는 개방형 탐지에 이름만 추가해 잡았습니다.", headSize: 12.5, bodySize: 10 });
  pic(s, "fig_16_0015_야간_상자30개_지도.jpg", 6.5, 1.95, 2.55, 2.9, "0015 야간 상자 30개 지도");
  cap(s, "야간 10분 통과 비행(0015): 상자 30개 자동 지도화, 3D 뼈대 25/25", 6.5, 4.9, 2.55, 0.45);
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
  card(s, 6.5, 5.4, 6.23, 1.1, { head: "50 m 오차가 1 m대로", body: "드론 GPS 대신 3D 카메라 자세로 광선을 쏴 지면과 교차. 절대 위치의 바닥은 GPS(r95 ≈ 5 m)라 RTK·기준 표식·위성 정합으로 더 내릴 수 있습니다.", headSize: 12, bodySize: 10 });
  refs(s, "자료: 업체 칩 48장(정답 47) · 하와이 420칩(정답 3,195) · 튀니지 TUN-MarineLitter 179장 · figures/cross_eval*.json, 0007_plan_summary.json, 삼각측량 패치 tests", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("긍정 프레임. 통합 모델이 문갑도에서 0.53으로 떨어지는 것은 질문 때: 서비스 기본 가중치는 AI Hub 11종, 30 에폭 결과로 재비교.");

  // 검증 ③ 부피·무게
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "04 검증" });
  s.addText("검증 ③ 부피와 무게: 크기 아는 상자 3개가 ±20% 안에 들었다", { placeholder: "title" });
  sub(s, "정답 부피를 아는 상자를 두 고도에서 찍어 3D 부피와 비교했습니다. 같은 상자를 업체 방식(면적 × 계수)으로 계산하면 기준의 1/112·1/180입니다.");
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.95, w: 5.4, h: 4.55, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "크기 아는 상자 3개의 부피 오차 (실측 대비)", { x: 0.85, y: 2.05, w: 5, h: 0.3, fontSize: 11.5, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "부피 오차(%)", labels: ["0007 작은 상자 (7 m 선회)", "0007 큰 상자 (7 m 선회)", "0010 키 큰 상자 (2 m 왕복)"], values: [19, 20, -10] }],
    chartBase({ x: 0.7, y: 2.4, w: 5.2, h: 2.6, barDir: "col", valAxisMinVal: -30, valAxisMaxVal: 30, dataLabelFormatCode: "+0;-0", catAxisLabelFontSize: 9, valAxisLabelFormatCode: "0" }));
  s.addTable([
    [hdr("상자"), hdr("정답"), hdr("3D 측정"), hdr("부피")],
    ["0007 작은", "23×17×8 cm · 3.1 L", "27×19×11.5 cm", "3.7 L (+19%)"],
    ["0007 큰", "60×45×12 cm · 32.4 L", "62×49×13.5 cm", "38.8 L (+20%)"],
    ["0010 키 큰", "32×42×39 cm · 52.4 L", "49×37×38 cm", "47.2 L (−10%)"],
  ], { x: 0.85, y: 5.05, w: 4.9, colW: [0.95, 1.6, 1.3, 1.05], fontSize: 9, color: H.dk1, border: { type: "solid", color: "C9D6DE", pt: 0.5 }, fill: { color: H.lt1 }, rowH: 0.3, margin: 0.03, objectName: "box table" });
  pic(s, "fig_11_업체방식_vs_3D_상자무게.jpg", 6.3, 1.95, 6.43, 2.57, "업체 방식 vs 3D 상자 무게");
  cap(s, "같은 상자 2개의 무게: 업체 방식(주황) vs 3D 부피 × 겉보기밀도(파랑) vs 기준값(초록). 업체 방식은 기준의 1/112·1/180.", 6.3, 4.54, 6.43, 0.4);
  stat2(s, 6.3, 5.0, 3.1, 1.5, { value: "±20", unit: "% 안", label: "상자 3개 부피 오차", note: "7 m 선회 2개, 2 m 왕복 1개" });
  stat2(s, 9.63, 5.0, 3.1, 1.5, { value: "1/112", unit: "· 1/180", label: "업체 방식의 무게 (기준 대비)", note: "같은 상자를 면적 × 계수로", color: C.accent2 });
  refs(s, "자료: figures/0007_objvol_v2.json, 0010 v2, compare_summary.json · 기준값은 정답 부피 × 같은 겉보기밀도(저울 실측으로 교체 예정)", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("긍정 프레임. 7 m 윗면 편향(+1.5~3.5 cm)과 저울 실측 부재는 질문 때 답한다.");

  // 검증 ④ 재방문·수거계획
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "04 검증" });
  s.addText("검증 ④ 재방문과 수거계획: 재현율 0.86, 섬 하나의 작업카드", { placeholder: "title" });
  sub(s, "업체 정사영상 위 가상비행에서 애매한 후보만 재방문해 재현율을 0.71 → 0.86으로 올렸고, 니하우 섬 전체에 파이프라인을 돌려 작업카드까지 냈습니다.");
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.95, w: 4.0, h: 2.6, fill: { color: H.lt1 }, line: { color: H.lt1 }, rectRadius: 0.12, shadow: shadow(), objectName: "chart card" });
  tb(s, "능동 재방문 효과 (문갑도 100×100 m, 라벨 7개)", { x: 0.85, y: 2.05, w: 3.6, h: 0.3, fontSize: 11, bold: true });
  s.addChart(pres.ChartType.bar, [{ name: "재현율", labels: ["커버리지만", "+ 재방문"], values: [0.71, 0.86] }],
    chartBase({ x: 0.7, y: 2.4, w: 3.8, h: 2.05, barDir: "col", valAxisMinVal: 0, valAxisMaxVal: 1, dataLabelFormatCode: "0.00", catAxisLabelFontSize: 10, valAxisLabelFormatCode: "0.0" }));
  card(s, 0.6, 4.7, 4.0, 1.8, { head: "재방문 25회 중 22회 기각", body: "한 프레임에서만 우연히 잡힌 탐지를 8 m 재촬영으로 걸러내고 3개를 확정. 추가 비행거리 697 m(679 → 1,718 m).", headSize: 12, bodySize: 10 });
  pic(s, "fig_18_하와이_niihau_지도_수거계획.jpg", 4.85, 1.95, 7.88, 3.47, "니하우 수거계획");
  const kp = [["탐지 물체", "5,476개", "플라스틱 3,966 · 부표 477 · 페트병 439 · 어망 214"], ["무게 구간", "7.9~33.6 t", "추정 13.7 t (업체 방식이면 69 kg)"], ["마대 · 트럭", "1,082장 · 37대", "정거장 331 · 경로 71.9 km"], ["인력 구분", "1인 5,294 · 2인 138 · 장비 44", "23 kg 규칙 · 묻힘 의심"]];
  kp.forEach((k, i) => {
    const x = 4.85 + i * 2.0;
    s.addShape(pres.ShapeType.roundRect, { x, y: 5.5, w: 1.9, h: 1.0, fill: { color: H.lt2 }, line: { color: H.lt2 }, rectRadius: 0.1, objectName: "kpi " + k[0] });
    tb(s, k[0], { x: x + 0.15, y: 5.55, w: 1.65, h: 0.25, fontSize: 9, color: C.accent4 });
    tb(s, k[1], { x: x + 0.15, y: 5.78, w: 1.7, h: 0.4, fontSize: i === 3 ? 9.5 : 14, bold: true, color: i === 1 ? C.accent2 : C.text2, valign: "middle" });
    tb(s, k[2], { x: x + 0.15, y: 6.17, w: 1.7, h: 0.3, fontSize: 7.5, color: C.accent4, valign: "top" });
  });
  refs(s, "자료: figures/sim_aihub_*_summary.json · hawaii_niihau_ft_summary.json(칩 553장, 2 cm/px) · 송도 0007 작업카드: 정거장 1, 0.83 kg(상한 1.67), 마대 1, 트럭 1, 경로 20 m", 0.6, 6.62, 12.1, 0.36);
  s.addNotes("긍정 프레임. 니하우는 2D라 무게 구간이 넓다 → '그래서 3D가 필요하다'로 연결.");

  // 검증 요약표
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "04 검증" });
  s.addText("검증 요약: 가설 · 설계 · 결과", { placeholder: "title" });
  sub(s, "완료 9건. 수치는 모두 저장소의 로그·JSON에서 재현됩니다.");
  const okc = { text: "완료", options: { bold: true, color: "0A7A2F", fontSize: 9, align: "center" } };
  s.addTable([
    [hdr("실험"), hdr("가설"), hdr("설계"), hdr("결과"), hdr("상태")],
    ["A 부피", "영상 3D로 잰 부피가 실측과 ±20% 안에 든다", "크기 아는 상자 3개, 7 m 선회(0007)·2 m 왕복(0010)", "+19% / +20% / −10%. 업체 방식은 1/112·1/180", okc],
    ["B 위치", "3D 자세로 계산한 위치가 GPS와 수 m 안", "0007·0010 실기체 + 합성 7개 시나리오", "1.16 m · 8.07→0.51 m(축척 자동) · 합성 0.01~0.11 m", okc],
    ["C 탐지", "운용 고도 GSD로 학습하면 현장 재현율이 오른다", "문갑도 칩 48·하와이 420칩·튀니지 179장 교차평가", "문갑도 0.28→0.72 · 하와이 0.24→0.69 · 튀니지 0.14→0.52", okc],
    ["D 재방문", "애매한 후보만 재방문하면 짧은 추가 비행으로 재현율↑", "문갑도 정사영상 가상비행 100×100 m, 라벨 7개", "0.71→0.86, +697 m (25회 중 22회 기각)", okc],
    ["E 야간 통과", "통과 비행만으로 탐지·지도·3D 뼈대가 된다", "0015 야간 10분, 4K 60 fps, 상자 ~28개", "탐지 30개 · 3D 뼈대 25/25 · 부피는 선회로", okc],
    ["F 반복성(미국)", "몰리고, 다시 쌓이고, 과거로 짠 경로가 통한다", "하와이 2015 항공조사 · NOAA MDMAP 134곳 · 텍사스 33곳", "상위 10% 칸 75% · 순위상관 0.88 · 61% vs 36%", okc],
    ["G 위성 형상 선별", "형상 점수 상위 30% 길이에 무게의 절반 이상", "니하우 탐지 격자 · 문갑도 라벨 42 · 인천 조석 지도", "니하우 65~67% · 문갑도 62~67% · 인천 조석 모델 99%", okc],
    ["H 전략 비교", "핫스팟 30%가 같은 자원으로 전체 지그재그의 2배", "같은 카메라·띠 폭·배터리 모델, 지리 순서·무작위 대조", "15.4 h vs 41.3 h · 67% vs 25~29%", okc],
    ["I 해안 적용", "같은 파이프라인이 다른 해안에서 수거계획을 낸다", "니하우 섬 칩 553장, 10분 미세조정", "5,476개 · 7.9~33.6 t · 마대 1,082 · 트럭 37", okc],
  ], { x: 0.6, y: 1.95, w: 12.13, colW: [1.3, 3.25, 3.2, 3.45, 0.93], fontSize: 9, color: H.dk1, border: { type: "solid", color: "C9D6DE", pt: 0.5 }, fill: { color: H.lt1 }, rowH: 0.4, margin: 0.035, valign: "middle", objectName: "validation summary" });
  source(s, "저장소: dohun415/aerodrone_hackathon (docs/파이프라인_결과정리.md, figures/*.json, hotspot/, route_optimization/) · HSR2M/hsr1m (island_drone_sim, 삼각측량 패치, incheon_debris_sim). 다음 검증(저울 실측, 3·5·7 m 선회, 국내 정점 시계열)은 로드맵에.");
  s.addNotes("완료 실험만. 예정 실험은 로드맵 1단계.");

  // ═════════ 05 기대효과와 제안 ═════════
  pres.addSection({ title: "05 기대효과와 제안" });
  divider("05", "기대효과와 제안", "기업이 아끼는 것, 이 기술의 의의, 그리고 3DLabs와 함께 검증하고 싶은 것.", "05 기대효과와 제안");

  // 기업이 아끼는 것
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "05 기대효과와 제안" });
  s.addText("기업이 아끼는 것: 비행시간 63%, 재방문·재배차, 현장에서 헤매는 시간", { placeholder: "title" });
  sub(s, "같은 장비·같은 인원으로 어디가 달라지는지. 수치는 니하우·인천·문갑도 비교 모델과 업체 라벨 분석에서 나왔습니다.");
  const hdr2 = (t) => ({ text: t, options: { bold: true, color: H.dk2, fill: { color: "DCE6EC" }, fontSize: 10.5 } });
  s.addTable([
    [hdr2("항목"), hdr2("지금"), hdr2("DroneSweep"), hdr2("근거")],
    ["비행·조사 시간", "해안 전체 지그재그", "상위 30% 구간만 → −63% (니하우 41.3 → 15.4 h)", "인천 448 → 57 h, 문갑도 5.0 → 2.2 h. 배터리·인력·일수가 같은 비율로"],
    ["탐지·3D 연산", "프레임 147,266장", "51,640장 → −65% (CPU 9.0 → 3.2 h, 58 → 20 GB)", "노트북 한 대 처리가 100 km 해안에서도 유지"],
    ["현장에서 찾기", "50 m 어긋난 핀을 보고 헤맴", "1 m대 핀 + 주변 표지물 사진 카드", "3D↔GPS 잔차 1.16 m, 수거자가 도착 즉시 확인"],
    ["무게·배차", "면적 × 계수 1.3 kg → 마대 1장", "3D 101 kg → 마대 6장·트럭·2인 작업을 사전 확정", "같은 42개 물체, 78배 차이. 추가 호출·장비 대기 방지"],
    ["방문 횟수", "찾고, 재고, 다시 오고", "비행 1회 = 작업카드 1부, 경계 물체만 2차 선회", "재방문 후보 25개 중 22개는 영상으로 기각"],
  ], { x: 0.6, y: 1.95, w: 12.13, colW: [1.7, 2.6, 4.0, 3.83], fontSize: 10, color: H.dk1, border: { type: "solid", color: "C9D6DE", pt: 0.5 }, fill: { color: H.lt1 }, rowH: 0.62, margin: 0.06, valign: "middle", objectName: "savings table" });
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.75, w: 12.13, h: 0.8, fill: { color: H.accent6 }, line: { color: H.accent6 }, rectRadius: 0.1, objectName: "money" });
  s.addImage({ data: ICON.FaCoins_n, x: 0.9, y: 5.95, w: 0.4, h: 0.4, objectName: "icon coins" });
  tb(s, "돈으로: 처리 단가 톤당 약 50만 원이면 100 t 추정 오차가 5천만 원이고, 비행·연산 시간 63~65% 절감은 소티·배터리·인건비에 그대로 비례합니다. 발주처(지자체)에는 추정 오차가, 업체에는 재방문과 재배차가 줄어듭니다.", { x: 1.45, y: 5.75, w: 11.1, h: 0.8, fontSize: 11, bold: true, color: C.text2, valign: "middle" });
  source(s, "자료: route_optimization/docs/전략비교(니하우), incheon/비교표, mungap_opendrift · 업체 라벨 42개 분석 · 처리 단가 한국일보(전남). 금액은 단가 × 오차의 산술 환산이며 계약 조건에 따라 달라집니다.");
  s.addNotes("기대효과. 금액은 환산 예시임을 분명히.");

  // 포인트 기술의 의의
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "05 기대효과와 제안" });
  s.addText("포인트 기술의 의의: 정합이 '위치 엔진'이 되고, 3D가 '무게'를 만든다", { placeholder: "title" });
  sub(s, "처음 과제였던 정합 기술을 버리지 않고 두 곳에 꽂았습니다. 그리고 업체 데이터에서 가장 큰 구멍이었던 '높이'를 영상 하나로 채웠습니다.");
  card(s, 0.6, 1.95, 3.9, 4.55, { icon: "FaCrosshairs", head: "정합 → 위치 엔진: 50 m가 1 m대로", body: "SfM 카메라 자세를 GPS 경로에 정렬하고(잔차 1.16 m), 정사영상은 위성(SkySat↔Sentinel-2 인라이어 85%, 5~8 m)에 정합합니다. 수거자가 핀을 보고 바로 찾습니다.\n\n사람이 아끼는 것: 헤매는 시간, 못 찾고 돌아오는 날." , headSize: 13.5, bodySize: 11 });
  card(s, 4.72, 1.95, 3.9, 4.55, { icon: "FaCubes", head: "3D 부피 → 무게: 1.3 kg이 101 kg으로", body: "업체 기록은 면적 × 계수라 높이가 없습니다. 영상 하나로 점구름을 만들고 SAM 2 투표로 물체 점만 남겨 높이를 잽니다. 상자 3개에서 ±20% 안.\n\n기업이 아끼는 것: 마대·트럭·인원을 한 번에 맞게, 재배차 없이.", headSize: 13.5, bodySize: 11 });
  card(s, 8.83, 1.95, 3.9, 4.55, { icon: "FaSatellite", head: "위성 → 선별: 해안의 30%만 날아 67%", body: "위성이 쓰레기를 보는 게 아니라 해안의 모양을 봅니다. 만입도·풍향 노출·띠 폭으로 쌓이는 자리를 고르고, 하구는 조석 모델이 맡습니다.\n\n아끼는 것: 비행시간 63%, 배터리와 하루.", headSize: 13.5, bodySize: 11 });
  s.addNotes("의의 장. 업체 데이터 오류(1.3 vs 101 kg)를 다시 한 번 강조.");

  // 3DLabs 결합
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "05 기대효과와 제안" });
  s.addText("위성이 넓게 보고, 드론이 자세히 재고, 지자체가 배차한다", { placeholder: "title" });
  sub(s, "3DLabs의 위성 지상국·ARD 플랫폼 위에 드론 측정 계층을 얹어, 활용 분야(도시·산림·항만·수체변화)에 '해안쓰레기 수거계획'을 추가합니다.");
  const roles = [
    ["FaSatellite", "3DLabs · 위성 계층", ["위성의 역할은 탐지가 아니라 해안선 갱신(송도·소래 매립)·형상 점수·선별", "Sentinel-2 공개자료로 시작, 상용 고해상 위성은 띠 폭·해안선 정확도를 올리는 상위 상품", "하구에서는 조석·수리 모델 결합이 필요 → 제휴 포인트"], H.dk2, true],
    ["FaPlane", "DroneSweep · 드론 계층", ["핫스팟 경로 KML, 조종자 비행, 탐지·3D 위치·SfM 부피", "무게 구간과 23 kg·마대·트럭 경계 2차 선회", "정거장별 작업카드(인력·마대·트럭·경로), 대시보드"], "124A6E", true],
    ["FaUsers", "고객 · 지자체 계층", ["시군 해양수산 부서: 예산·배차", "수거 용역업체: 동선·인원", "해양환경공단: 반복 모니터링 데이터(핫스팟 이력)"], H.lt2, false],
  ];
  roles.forEach((r, i) => {
    const x = 0.6 + i * 4.1;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.95, w: 3.9, h: 3.35, fill: { color: r[3] }, line: { color: r[3] }, rectRadius: 0.12, shadow: r[4] ? undefined : shadow(), objectName: "role " + r[1] });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: 2.25, w: 0.62, h: 0.62, fill: { color: r[4] ? H.accent2 : H.dk2 }, line: { color: r[4] ? H.accent2 : H.dk2 }, objectName: "icon circle" });
    s.addImage({ data: ICON[r[0] + "_w"], x: x + 0.45, y: 2.4, w: 0.32, h: 0.32, objectName: "icon " + r[0] });
    tb(s, r[1], { x: x + 0.3, y: 3.05, w: 3.3, h: 0.4, fontSize: 14.5, bold: true, color: r[4] ? C.background1 : C.text1 });
    bullets(s, r[2], { x: x + 0.3, y: 3.5, w: 3.3, h: 1.7, fontSize: 11, color: r[4] ? C.accent5 : C.text1 });
    if (i < 2) s.addShape(pres.ShapeType.rightArrow, { x: x + 3.92, y: 3.35, w: 0.17, h: 0.4, fill: { color: H.accent2 }, line: { color: H.accent2 }, objectName: "arrow" });
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
  s.addNotes("상대의 강점(위성·ARD·B2G 채널)을 앞에 두고 우리를 계층으로 끼운다.");

  // 로드맵
  s = pres.addSlide({ masterName: "CONTENT_LT2", sectionTitle: "05 기대효과와 제안" });
  s.addText("공동 실증 로드맵 (제안)", { placeholder: "title" });
  sub(s, "세 단계, 각 단계의 끝에 숫자로 확인할 수 있는 결과를 두었습니다.");
  const ph = [
    ["1", "2026 4분기", "데이터 보정", ["상자 3개 저울 실측 + 3·5·7 m 선회 통제 실험 → 밀도·편향 보정", "문갑도 핫스팟 30% vs 전체를 같은 날 비행해 라벨로 비교, 국가 모니터링 정점 시계열로 반복성 검증", "통합 모델 30 에폭 재비교, 위성 ARD 샘플 2~3개 해안으로 형상 점수 vs 실제 패치"], "산출: 실측 기반 무게 구간, 한국 핫스팟 검증 보고"],
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

  // 요청사항
  s = pres.addSlide({ masterName: "DARK_CONTENT", sectionTitle: "05 기대효과와 제안" });
  s.addText("함께 검증하고 싶은 것", { placeholder: "title" });
  tb(s, "세 가지를 요청드립니다. 모두 1단계(2026 4분기) 안에 결과를 숫자로 돌려드릴 수 있는 범위입니다.", { x: 0.6, y: 1.32, w: 12.1, h: 0.45, fontSize: 14, color: C.accent5 });
  const asks = [
    ["FaDatabase", "위성 ARD 샘플", "대상 해안 2~3곳(인천·강화 도서 또는 전남 도서)의 정사영상·시계열. 해안선 갱신과 형상 점수의 입력으로 쓰고 실제 패치와 대조합니다."],
    ["FaHandshake", "시범 지자체 소개", "B2G 채널로 연결된 시군 1곳. 비행 1회로 작업카드를 내고 실제 수거량·마대·트럭과 대조합니다."],
    ["FaLayerGroup", "데이터 연동 규격 협의", "ARD → 핫스팟 사전값 입력, 드론 결과(GeoJSON·CSV·작업카드) → 플랫폼 활용 분야 등록. 양방향 포맷을 먼저 맞춥니다."],
  ];
  asks.forEach((a, i) => card(s, 0.6 + i * 4.1, 1.95, 3.9, 3.0, { icon: a[0], head: a[1], body: a[2], dark: true, headSize: 15, bodySize: 12 }));
  s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.2, w: 12.13, h: 1.25, fill: { color: H.accent2 }, line: { color: H.accent2 }, rectRadius: 0.12, objectName: "closing" });
  tb(s, "추정이 틀리면 배차가 틀린다.  위성이 넓게 보고, 드론이 자세히 재면, 지자체는 맞게 배차할 수 있습니다.", { x: 0.95, y: 5.2, w: 11.4, h: 0.8, fontSize: 17, bold: true, color: C.background1, valign: "middle" });
  tb(s, "DroneSweep · 드론대장 붕붕이 · 저장소 dohun415/aerodrone_hackathon, HSR2M/hsr1m", { x: 0.95, y: 5.95, w: 11.4, h: 0.4, fontSize: 10.5, color: C.background1 });
  s.addNotes("요청 3개를 명확히. 마지막 문장은 부제의 반복.");

  // ═════════ 한 장 요약 ═════════
  pres.addSection({ title: "요약" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "요약" });
  s.addText("다시 한 장으로", { placeholder: "title" });
  sub(s, "문제 → 해법 → 검증 → 제안. 새로 발명한 알고리즘은 없고, 검증된 방법을 수거계획 하나로 이었습니다.");
  const sum = [
    ["FaExclamationTriangle", "문제: 추정이 곧 예산이다", "수거 업체는 눈으로 찾고(50 m 오차), 면적에 계수를 곱해 무게를 내고(42개 합계 1.3 kg, 3D로는 101 kg), 경험으로 배차합니다. 수거량은 5년간 19.8% 늘었고 90%를 지자체가 발주합니다."],
    ["FaRoute", "해법: 비행 한 번 = 수거계획서 한 부", "위성 형상 점수·조석 모델로 어디를 날지 고르고(상위 30% 구간에 쓰레기 절반 이상) → 조종자 비행(KML) → 탐지 → 3D 위치 → SfM 부피 × 겉보기밀도 → 무게 구간 → 마대·트럭·인원·경로 작업카드."],
    ["FaFlask", "검증: 상자 3개, 영상 3편, 해안 3곳", "부피 오차 ±20% 안(업체 방식은 1/112·1/180). 3D↔GPS 1.16 m. 재현율 0.72, 재방문 0.86. 니하우: 핫스팟 30%가 37% 시간으로 67% 포착. 문갑도 라벨: 상위 30% 길이에 62%."],
    ["FaHandshake", "제안: 위성이 넓게, 드론이 자세히", "위성의 역할은 탐지가 아니라 해안선 갱신·형상 점수·선별입니다. 3DLabs의 ARD 위에 드론 측정 계층을 얹어 지자체 수거계획으로 연결하는 B2G 공동 실증."],
  ];
  sum.forEach((c, i) => card(s, 0.6 + i * 3.075, 1.95, 2.9, 4.3, { icon: c[0], head: c[1], body: c[2], headSize: 14.5, bodySize: 12 }));
  s.addNotes("맨 뒤 요약. 질의응답 때 띄워 둔다.");

  const out = path.join(__dirname, "붕붕이_3DLabs_제안.pptx");
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("written", out);
})().catch((e) => { console.error(e); process.exit(1); });
