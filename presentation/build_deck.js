// Builds KAMouflage_Vision_Pitch.pptx. Run: node build_deck.js
// Drop optional files into assets/ and re-run:
//   demo.mp4 (+ demo_cover.png)  -> embedded on the demo slide
//   team_khaled.jpg, team_abdulla.jpg -> round photos on the team slide
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const { FaGithub, FaLinkedin } = require("react-icons/fa");

const A = (f) => path.join(__dirname, "assets", f);
const has = (f) => fs.existsSync(A(f));

// ------------------------------------------------------------------ content to fill in
const TEAM = [
  { id: "khaled", name: "Khaled Sandoqa", role: "Computer vision & AI",
    github: "https://github.com/khaledSandoqa", linkedin: "https://www.linkedin.com/in/khaled-sandoqa-9a649132b/" },
  { id: "abdalla", name: "Abdalla Izzeldin", role: "Full-stack software engineering",
    github: "https://github.com/abdalla980", linkedin: "https://www.linkedin.com/in/abdallaizzeldin" },
];
const REPO = "https://github.com/abdalla980/KAMouflageVision-UAE-HACKATHON26";

// ------------------------------------------------------------------ design tokens (from the original deck)
const DARK = "14271F", CREAM = "F7F3EA", GREEN = "1F5C45", GOLD = "D8B66A", GOLD_DK = "B68A35";
const TEXT = "1B2A23", MUTED = "56655C", WHITE = "FFFFFF", TINT = "EAEFEA", RULE = "D3DCD6", ON_DARK = "C9D3CC";
const THEME = {
  name: "KAMouflage Vision", headFontFace: "Arial", bodyFontFace: "Arial",
  colors: { dk1: TEXT, lt1: WHITE, dk2: DARK, lt2: CREAM, accent1: GREEN, accent2: GOLD, accent3: GOLD_DK,
            accent4: MUTED, accent5: "E9DFC8", accent6: "B23A3A", hlink: GREEN, folHlink: GREEN },
};
const W = 13.333, X = 0.6, CW = W - 2 * X;

async function icon(Comp, color, px = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: px }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = "KAMouflage Vision";
  pres.author = "Khaled Sandoqa and Abdalla Izzeldin";
  pres.theme = { headFontFace: "Arial", bodyFontFace: "Arial" };

  const footer = (label, color) => [
    { text: { text: label, options: { x: X, y: 6.92, w: 6, h: 0.3, fontSize: 10, color, margin: 0 } } },
  ];
  const title = (color) => ({ placeholder: { options: { name: "title", type: "title", x: X, y: 0.42, w: CW, h: 0.9,
    fontSize: 36, bold: true, color, align: "left", valign: "middle", margin: 0 }, text: "" } });
  const num = (color) => ({ x: 12.23, y: 6.92, w: 0.5, h: 0.3, fontSize: 10, color, align: "right" });

  pres.defineSlideMaster({ title: "COVER", background: { color: DARK }, objects: [] });
  pres.defineSlideMaster({ title: "LIGHT", background: { color: CREAM },
    objects: [...footer("KAMOUFLAGE VISION", TEXT), title(TEXT)], slideNumber: num(TEXT) });
  pres.defineSlideMaster({ title: "DARK", background: { color: DARK },
    objects: [...footer("KAMOUFLAGE VISION", ON_DARK), title(CREAM)], slideNumber: num(ON_DARK) });
  pres.defineSlideMaster({ title: "BACKUP", background: { color: CREAM },
    objects: [...footer("KAMOUFLAGE VISION  /  BACKUP", GREEN), title(TEXT)], slideNumber: num(GREEN) });

  const T = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, fontFace: "Arial", color: TEXT, ...o });
  const note = (s, text, o = {}) => T(s, text, { x: X, y: 6.42, w: CW, h: 0.4, fontSize: 11, color: MUTED,
                                                  valign: "bottom", ...o });
  const hdr = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: GREEN } } });
  const tableOpts = (o) => ({ x: X, w: CW, fontFace: "Arial", fontSize: 15, color: TEXT, valign: "middle",
    border: { type: "solid", pt: 0.75, color: RULE }, margin: [0.08, 0.14, 0.08, 0.14], ...o });
  const zebra = (rows) => rows.map((r, i) => r.map((c) => (typeof c === "string"
    ? { text: c, options: { fill: { color: i % 2 ? TINT : WHITE } } }
    : { ...c, options: { fill: { color: i % 2 ? TINT : WHITE }, ...c.options } })));

  // ================================================================ MAIN PITCH
  pres.addSection({ title: "Pitch" });

  // 1 - Brand
  let s = pres.addSlide({ masterName: "COVER", sectionTitle: "Pitch" });
  s.addImage({ path: A("logo_round.png"), x: 0.9, y: 1.25, w: 4.9, h: 4.9, objectName: "Logo" });
  T(s, "UAE HACKATHON 2026  ·  PIONEERS", { x: 6.4, y: 1.4, w: 6.3, h: 0.35, fontSize: 14, bold: true,
                                          color: GOLD, charSpacing: 2 });
  T(s, "KAMouflage Vision", { x: 6.4, y: 1.9, w: 6.9, h: 1.0, fontSize: 50, bold: true, color: CREAM });
  T(s, "AI that finds UAE wildlife in camera-trap photos, so experts only check what matters.",
    { x: 6.4, y: 3.1, w: 6.1, h: 1.2, fontSize: 22, color: CREAM, valign: "top" });
  T(s, "Khaled Sandoqa  ·  Abdalla Izzeldin", { x: 6.4, y: 4.85, w: 6.3, h: 0.4, fontSize: 16, bold: true, color: CREAM });
  T(s, "MOCCAE wildlife monitoring challenge", { x: 6.4, y: 5.3, w: 6.3, h: 0.35, fontSize: 13, color: ON_DARK });
  s.addNotes("Hi, we are KAMouflage Vision. (5 s)");

  // 2 - Team
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Pitch" });
  s.addText("Our team", { placeholder: "title" });
  const gh = await icon(FaGithub, TEXT), li = await icon(FaLinkedin, "0A66C2");
  const cardW = 5.8, cardH = 3.9, cardY = 1.75;
  TEAM.forEach((m, i) => {
    const cx = X + i * (cardW + CW - 2 * cardW);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx, y: cardY, w: cardW, h: cardH, rectRadius: 0.12,
      fill: { color: WHITE }, line: { color: RULE, width: 0.75 }, objectName: `Card ${m.name}` });
    const px = cx + 0.45, py = cardY + 0.45, d = 1.6;
    if (has(`team_${m.id}.jpg`)) {
      s.addImage({ path: A(`team_${m.id}.jpg`), x: px, y: py, w: d, h: d, rounding: true,
                   sizing: { type: "cover", w: d, h: d }, objectName: `Photo ${m.name}` });
    } else {
      s.addShape(pres.shapes.OVAL, { x: px, y: py, w: d, h: d, fill: { color: TINT }, line: { color: GREEN, width: 1 } });
      T(s, m.name.split(" ").map((w) => w[0]).join(""), { x: px, y: py, w: d, h: d, align: "center",
        valign: "middle", fontSize: 40, bold: true, color: GREEN });
    }
    const tx = px + d + 0.35, tw = cardW - (tx - cx) - 0.2;
    T(s, m.name, { x: tx, y: py + 0.25, w: tw, h: 0.5, fontSize: 22, bold: true });
    T(s, m.role, { x: tx, y: py + 0.8, w: tw, h: 0.7, fontSize: 16, color: GREEN, valign: "top" });
    const links = [[gh, m.github, "GitHub link to add"], [li, m.linkedin, "LinkedIn link to add"]];
    links.forEach(([img, url, missing], k) => {
      const ly = cardY + 2.5 + k * 0.6;
      s.addImage({ data: img, x: px, y: ly, w: 0.36, h: 0.36 });
      T(s, url ? [{ text: url.replace(/^https:\/\/(www\.)?/, "").replace(/\/$/, ""), options: { hyperlink: { url } } }] : missing,
        { x: px + 0.55, y: ly - 0.02, w: cardW - 1.3, h: 0.4, fontSize: 15, valign: "middle",
          color: url ? GREEN : "B23A3A" });
    });
  });
  s.addNotes("We are Khaled and Abdulla. (5 s)");

  // 3 - Challenge
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Pitch" });
  s.addText("The problem", { placeholder: "title" });
  s.addImage({ path: A("logo_round.png"), x: 11.55, y: 0.35, w: 1.18, h: 1.18 });
  T(s, "MOCCAE wildlife monitoring challenge", { x: X, y: 1.3, w: 6, h: 0.35, fontSize: 15, color: GOLD });
  T(s, "Camera traps across UAE reserves take thousands of photos. Experts check every one by hand, so verified " +
    "wildlife records arrive too late to guide conservation decisions.",
    { x: X, y: 1.9, w: CW, h: 1.5, fontSize: 26, bold: true, color: CREAM, valign: "top" });
  [["Too many photos", "Most frames are empty, triggered by wind or heat, yet someone still opens each one."],
   ["Hard to read", "Night and infrared shots, partial animals and look-alike species slow experts down."],
   ["Insights come late", "Records reach the map long after the photos were taken, and coverage gaps stay hidden."]]
    .forEach(([h, b], i) => {
      const x = X + i * 4.15, cw = 3.85;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 3.85, w: cw, h: 2.35, rectRadius: 0.1,
        fill: { color: GREEN }, line: { color: GREEN }, objectName: `Pain ${h}` });
      T(s, String(i + 1).padStart(2, "0"), { x: x + 0.3, y: 4.05, w: 1, h: 0.45, fontSize: 20, bold: true, color: GOLD });
      T(s, h, { x: x + 0.3, y: 4.55, w: cw - 0.6, h: 0.45, fontSize: 21, bold: true, color: CREAM });
      T(s, b, { x: x + 0.3, y: 5.05, w: cw - 0.6, h: 1.05, fontSize: 15, color: CREAM, valign: "top" });
    });
  s.addNotes("Camera traps take thousands of photos. Most are empty, night shots are hard to read, and experts " +
             "check every one by hand, so insights come late. " +
             "BRIDGE: So we asked: what if experts only looked at the photos that actually need them? (20 s)");

  // 4 - Solution
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Pitch" });
  s.addText("Our solution: KAMouflage Vision", { placeholder: "title" });
  s.addImage({ path: A("p2_0.jpeg"), x: 0.95, y: 1.6, w: 5.75, h: 5.75 * 1235 / 1600, objectName: "Gemsbok detection" });
  [["Detect", "Find animals in a batch of camera-trap images."],
   ["Suggest", "Identify a species and combine burst evidence."],
   ["Verify", "A reviewer confirms or corrects the event."],
   ["Understand", "Confirmed events feed the map and activity chart."]].forEach(([h, b], i) => {
    const y = 1.6 + i * 1.15;
    T(s, h, { x: 7.55, y, w: 5.2, h: 0.45, fontSize: 24, bold: true, color: GREEN });
    T(s, b, { x: 7.55, y: y + 0.48, w: 5.2, h: 0.55, fontSize: 17, valign: "top" });
  });
  note(s, "Real inference example: gemsbok, public southern-African proxy image.");
  s.addNotes("Our app does four things: detect, suggest, verify, understand. (15 s)");

  // 5 - Architecture
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Pitch" });
  s.addText("How it works", { placeholder: "title" });
  T(s, "SYSTEM", { x: X, y: 1.42, w: 4, h: 0.3, fontSize: 12, bold: true, color: GOLD_DK, charSpacing: 2 });
  s.addImage({ path: A("architecture.png"), x: X, y: 1.78, w: CW, h: CW * 363 / 2938, objectName: "System architecture" });
  T(s, "ONE BURST OF PHOTOS", { x: X, y: 3.55, w: 4, h: 0.3, fontSize: 12, bold: true, color: GOLD_DK, charSpacing: 2 });
  const bw = 11.0;
  s.addImage({ path: A("burst.png"), x: X + (CW - bw) / 2, y: 3.9, w: bw, h: bw * 629 / 2928, objectName: "Burst flow" });
  note(s, "All models run locally and are MIT / Apache-2.0 licensed. No images leave the UAE.", { color: GREEN, fontSize: 13, bold: true });
  s.addNotes("Photos come in, AI filters empties and suggests a species. Above 90% is accepted, the rest goes " +
             "to an expert. Everything runs inside the UAE. (20 s)");

  // 6 - Demo
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Pitch" });
  s.addText("Live demo", { placeholder: "title" });
  const vw = 9.0, vh = vw * 9 / 16, vx = (W - vw) / 2, vy = 1.45;
  if (has("demo.mp4")) {
    s.addMedia({ type: "video", path: A("demo.mp4"), x: vx, y: vy, w: vw, h: vh,
                 ...(has("demo_cover.png") ? { cover: A("demo_cover.png") } : {}) });
  } else {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: vx, y: vy, w: vw, h: vh, rectRadius: 0.1,
      fill: { color: GREEN }, line: { color: GOLD, width: 1.5, dashType: "dash" }, objectName: "Video placeholder" });
    s.addShape(pres.shapes.OVAL, { x: W / 2 - 0.6, y: vy + vh / 2 - 0.95, w: 1.2, h: 1.2, fill: { color: GOLD } });
    s.addShape(pres.shapes.ISOSCELES_TRIANGLE, { x: W / 2 - 0.2, y: vy + vh / 2 - 0.62, w: 0.55, h: 0.5,
      rotate: 90, fill: { color: DARK }, line: { color: DARK } });
    T(s, "Demo video goes here", { x: vx, y: vy + vh / 2 + 0.45, w: vw, h: 0.5, align: "center",
      fontSize: 20, bold: true, color: CREAM });
  }
  s.addNotes("Play the demo video. (about 60 s)");

  // 7 - Evidence
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Pitch" });
  s.addText("Tested on 600 camera-trap photos", { placeholder: "title" });
  T(s, "276 bursts with known labels, run through our detector and classifier", { x: X, y: 1.3, w: CW, h: 0.4,
    fontSize: 17, color: MUTED });
  [["86.8%", "Animal bursts kept", "165 / 190"], ["67.4%", "Empty bursts filtered", "58 / 86"],
   ["48.9%", "Species named exactly", "93 / 190"]].forEach(([n, l, f], i) => {
    const x = X + i * 4.25;
    T(s, n, { x, y: 2.05, w: 3.9, h: 1.15, fontSize: 66, bold: true, color: GREEN });
    T(s, l, { x, y: 3.25, w: 3.9, h: 0.45, fontSize: 20 });
    T(s, f, { x, y: 3.72, w: 3.9, h: 0.35, fontSize: 15, color: MUTED });
  });
  T(s, "Empty photos never reach an expert. Unsure species go to review, not into the records.",
    { x: X, y: 4.55, w: CW, h: 0.9, fontSize: 24, bold: true });
  T(s, "UAE context: 44 MOCCAE reserves and 381 bird species via Bayanat, plus GBIF species records.",
    { x: X, y: 5.5, w: CW, h: 0.45, fontSize: 16 });
  note(s, "Public southern-African proxy photos (LILA BC); UAE camera sites simulated. UAE field accuracy needs permitted local data.");
  s.addNotes("We tested on 600 real camera-trap photos: 87% of animal bursts kept, two-thirds of empty bursts " +
             "removed automatically. (15 s)");

  // 8 - How we're different
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Pitch" });
  s.addText("Building on what exists", { placeholder: "title" });
  s.addTable([
    [hdr("Wildlife Insights"), hdr("AddaxAI"), { text: "KAMouflage Vision", options: { bold: true, color: DARK, fill: { color: GOLD } } }],
    [{ text: "Cloud platform for camera-trap management, AI identification and human validation." },
     { text: "Open-source desktop tool. Models run locally, offline after setup." },
     { text: "Built for MOCCAE: UAE government data, expert review queue, AI Advisor, Camtrap DP export. Runs inside the UAE." }]
      .map((c) => ({ ...c, options: { fill: { color: WHITE }, valign: "top" } })),
  ], tableOpts({ y: 1.6, colW: [CW / 3, CW / 3, CW / 3], rowH: [0.6, 1.75], fontSize: 17 }));
  T(s, "Our advantage", { x: X, y: 4.35, w: CW, h: 0.45, fontSize: 22, bold: true, color: GREEN });
  T(s, "A workflow tailored to MOCCAE, with government data integration and a path to authority-hosted deployment.",
    { x: X, y: 4.85, w: CW, h: 1.0, fontSize: 24 });
  note(s, "Sources: wildlifeinsights.org; docs.addaxai.com", { fontSize: 10 });
  s.addNotes("Good tools exist. We build on the same open models, shaped around MOCCAE's own workflow and data. (10 s)");

  // 9 - Business Model Canvas
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Pitch" });
  s.addText("Business Model Canvas", { placeholder: "title" });
  const bmc = (h, b) => ({ text: [{ text: h, options: { bold: true, breakLine: true } }, { text: b }] });
  s.addTable([
    [hdr("How we deliver"), hdr("The value"), hdr("How adoption works")],
    ...zebra([
      [bmc("Partners", "Authority sponsor, reserve team and ecologists."), bmc("Value", "Less repetitive review and traceable observations."),
       bmc("Customers", "Monitoring staff use it. Conservation authorities sponsor it.")],
      [bmc("Activities", "Inference, verification, evaluation and reporting."), bmc("Relationships", "Reviewer onboarding, support and quality reviews."),
       bmc("Channels", "A challenge-owner pilot and government integration.")],
      [bmc("Resources", "Permitted images, expert labels, software and hosting."), bmc("Costs", "Engineering, review labor, compute, storage and security."),
       bmc("Funding", "Sponsored pilot, then support or integration contracts.")],
    ]),
  ], tableOpts({ y: 1.55, colW: [CW / 3, CW / 3, CW / 3], rowH: [0.6, 1.4, 1.4, 1.4], fontSize: 17, valign: "top" }));
  s.addNotes("Authorities sponsor a pilot; staff use it daily; we earn through support and integration. (10 s)");

  // 10 - 90 days
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Pitch" });
  s.addText("The next 90 days", { placeholder: "title" });
  [["01-30", "Establish the baseline", "Prepare local GPU, database and storage. Agree access controls and a local test set."],
   ["31-60", "Improve local quality", "Fine-tune SpeciesNet on verified UAE crops. Calibrate and test held-out sites."],
   ["61-90", "Test real operations", "Review new retrievals. Audit errors and compare human time. Make a scale decision."]]
    .forEach(([d, h, b], i) => {
      const x = X + i * 4.25;
      T(s, d, { x, y: 1.55, w: 3.9, h: 0.8, fontSize: 44, bold: true, color: GOLD });
      T(s, h, { x, y: 2.45, w: 3.9, h: 0.45, fontSize: 21, bold: true, color: CREAM });
      T(s, b, { x, y: 3.0, w: 3.9, h: 1.15, fontSize: 17, color: CREAM, valign: "top" });
    });
  T(s, "The ask: one site, permitted images and expert reviewers.", { x: X, y: 4.65, w: CW, h: 0.55, fontSize: 26,
    bold: true, color: CREAM });
  T(s, "Targets: 99% animal retention, 95% accepted precision, 50% less review time.", { x: X, y: 5.3, w: CW, h: 0.45,
    fontSize: 18, color: CREAM });
  T(s, "Runs on existing authority hardware; budget scoped with the authority's IT team. All images and models stay on authority-controlled infrastructure.",
    { x: X, y: 6.3, w: CW, h: 0.45, fontSize: 12, color: ON_DARK, valign: "bottom" });
  s.addNotes("In 90 days: set up, adapt to UAE species, then measure real time saved at one site. (15 s)");

  // ================================================================ BACKUP
  pres.addSection({ title: "Backup" });

  // B0 - Quick facts: how the AI names an animal
  s = pres.addSlide({ masterName: "BACKUP", sectionTitle: "Backup" });
  s.addText("Quick facts: how the AI names an animal", { placeholder: "title" });
  [["MegaDetector V6", "Is anything there?",
    "Draws a box around an animal, person or vehicle. It does not name the species.", "Microsoft  ·  MIT"],
   ["SpeciesNet", "Which animal is it?",
    "Names the animal in the box, e.g. \"Arabian oryx, 94%\". Trained on about 65 million camera-trap photos and knows about 2,000 labels.",
    "Google  ·  Apache-2.0"],
   ["UAE geofence", "Could it live here?",
    "We tell SpeciesNet the photos come from the UAE, so it never suggests animals that don't live here.", "Country filter"]]
    .forEach(([h, q, b, tag], i) => {
      const cw = 3.85, x = X + i * 4.14, y = 1.45, ch = 3.0;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: cw, h: ch, rectRadius: 0.1, fill: { color: WHITE },
        line: { color: RULE, width: 0.75 }, objectName: `Fact ${h}` });
      T(s, h, { x: x + 0.3, y: y + 0.25, w: cw - 0.6, h: 0.45, fontSize: 22, bold: true, color: GREEN });
      T(s, q, { x: x + 0.3, y: y + 0.72, w: cw - 0.6, h: 0.4, fontSize: 16, bold: true });
      T(s, b, { x: x + 0.3, y: y + 1.18, w: cw - 0.6, h: 1.25, fontSize: 15, valign: "top" });
      T(s, tag, { x: x + 0.3, y: y + ch - 0.48, w: cw - 0.6, h: 0.3, fontSize: 12, bold: true, color: GOLD_DK });
    });
  T(s, "HOW A DECISION IS MADE", { x: X, y: 4.75, w: 6, h: 0.3, fontSize: 12, bold: true, color: GOLD_DK, charSpacing: 2 });
  [["Burst vote", "3–10 frames per trigger are combined"], ["90% or more", "Accepted automatically"],
   ["Below 90%", "An expert confirms or corrects"], ["Empty photos", "Filtered out before anyone sees them"],
   ["Night and people", "Night shots enhanced, people blurred"]].forEach(([h, b], i) => {
    const cw = 2.25, x = X + i * (cw + (CW - 5 * cw) / 4), y = 5.15;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: cw, h: 1.15, rectRadius: 0.08, fill: { color: GREEN },
      line: { color: GREEN }, objectName: `Step ${h}` });
    T(s, h, { x: x + 0.18, y: y + 0.14, w: cw - 0.36, h: 0.35, fontSize: 15, bold: true, color: CREAM });
    T(s, b, { x: x + 0.18, y: y + 0.5, w: cw - 0.36, h: 0.55, fontSize: 12, color: CREAM, valign: "top" });
  });

  // B0b - Quick facts: data and product
  s = pres.addSlide({ masterName: "BACKUP", sectionTitle: "Backup" });
  s.addText("Quick facts: data and product", { placeholder: "title" });
  const bullets = (items) => items.map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < items.length - 1 } }));
  [["Data", ["600 test photos (276 bursts) from LILA BC, a public camera-trap library",
             "UAE protected areas and bird list from MOCCAE via Bayanat",
             "Species records and IUCN Red List status from GBIF",
             "UAE camera positions simulated until real photos are shared"]],
   ["Product", ["Python + Streamlit app",
                "Import, gallery and review queue",
                "Dashboard: map, activity by hour, coverage gaps",
                "AI Advisor: missing cameras, clock errors, threatened species",
                "Camtrap DP export, the format GBIF uses"]],
   ["Why these models", ["Free and permitted for government use (MIT / Apache-2.0)",
                         "Avoided MegaDetector v5: its AGPL license would force everything built on it to be open-sourced",
                         "Everything runs locally: no photos go to a cloud service"]]]
    .forEach(([h, items], i) => {
      const cw = 3.85, x = X + i * 4.14, y = 1.45, ch = 4.3;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: cw, h: ch, rectRadius: 0.1, fill: { color: WHITE },
        line: { color: RULE, width: 0.75 }, objectName: `Facts ${h}` });
      T(s, h, { x: x + 0.3, y: y + 0.25, w: cw - 0.6, h: 0.45, fontSize: 22, bold: true, color: GREEN });
      T(s, bullets(items), { x: x + 0.3, y: y + 0.85, w: cw - 0.5, h: ch - 1.1, fontSize: 15, valign: "top",
                             paraSpaceAfter: 9 });
    });

  // B1 - How we built it
  s = pres.addSlide({ masterName: "BACKUP", sectionTitle: "Backup" });
  s.addText("How we built it", { placeholder: "title" });
  const bold = (t) => ({ text: t, options: { bold: true } });
  s.addTable([
    [hdr("Area"), hdr("What we did")],
    ...zebra([
      [bold("Challenge fit"), "Built around MOCCAE's workflow: detect, suggest, expert verify, insights."],
      [bold("Data"), "MOCCAE reserves and bird list (Bayanat), GBIF species and IUCN status, 600 LILA BC camera-trap photos."],
      [bold("AI"), "MegaDetector V6 (MIT) and SpeciesNet (Apache-2.0), burst voting, confidence routing, AI Advisor."],
      [bold("Product"), "Working app: import, gallery, review queue, insights dashboard, AI Advisor, Camtrap DP export."],
      [bold("Feasibility"), "Runs locally; 90-day pilot plan; data stays on authority infrastructure."],
      [bold("Market"), "Clear buyer (conservation authorities), pilot-first adoption, support and integration contracts."],
    ]),
  ], tableOpts({ y: 1.5, colW: [2.6, CW - 2.6], rowH: 0.62 }));
  note(s, "Sources: MOCCAE/FCSC via Bayanat; GBIF.org; LILA BC Snapshot Karoo/Kgalagadi (CDLA-Permissive); microsoft/MegaDetector; google/cameratrapai; camtrap-dp.tdwg.org",
       { fontSize: 10, y: 6.25, h: 0.55 });

  // B2 - Technical evidence
  s = pres.addSlide({ masterName: "BACKUP", sectionTitle: "Backup" });
  s.addText("What works today, what the pilot adds", { placeholder: "title" });
  s.addTable([
    [hdr("Implemented MVP"), hdr("Funded pilot work")],
    ...zebra([
      ["MIT detector and Apache SpeciesNet classifier. Species names, documented footer exclusion for proxy images, resumable caches.",
       "Local taxonomy coverage, calibrated thresholds and independent tests on unseen UAE sites."],
      ["Review decisions saved, reviewer-confirmed analytics, CSV export in Camtrap DP format.",
       "Authenticated access, protected-location policies, monitoring, backup and validated Camtrap DP packages."],
      ["Local processing and cached demo. No cloud inference API required.",
       "Authority-approved UAE deployment, security review, operational ownership and support agreements."],
    ]),
  ], tableOpts({ y: 1.5, colW: [CW / 2, CW / 2], rowH: [0.6, 1.25, 1.25, 1.25], fontSize: 16, valign: "top" }));
  note(s, "Production hosting and data reuse require authority approval.", { fontSize: 10 });

  // B3 - Evaluation protocol
  s = pres.addSlide({ masterName: "BACKUP", sectionTitle: "Backup" });
  s.addText("Evaluation protocol and limitations", { placeholder: "title" });
  [["Unit of evaluation", "276 complete source bursts. Labels are per burst, so no frame-level or animal-count claim."],
   ["Exact species scoring", "Case-insensitive name aliases. Any label can match in a multi-label burst. Genus-level answers count as wrong."],
   ["Data limitations", "Curated class balance, few rare-class samples, unknown overlap with pretrained training data. No UAE generalization claim."],
   ["Risk control", "Bursts below 90% confidence go to an expert. Corrections become training labels only after quality checks."],
   ["Next experiment", "A site-separated UAE test set and an assisted-vs-manual time study with monitoring staff."]]
    .forEach(([h, b], i) => {
      const y = 1.55 + i * 1.02;
      T(s, h, { x: X, y, w: 3.4, h: 0.85, fontSize: 19, bold: true, valign: "top" });
      T(s, b, { x: 4.25, y, w: W - X - 4.25, h: 0.85, fontSize: 17, valign: "top" });
    });

  // End - Thank you
  pres.addSection({ title: "End" });
  s = pres.addSlide({ masterName: "COVER", sectionTitle: "End" });
  s.addImage({ path: A("logo_round.png"), x: (W - 2.6) / 2, y: 0.7, w: 2.6, h: 2.6 });
  T(s, "Thank you", { x: X, y: 3.55, w: CW, h: 1.0, fontSize: 54, bold: true, color: CREAM, align: "center" });
  T(s, "Questions?", { x: X, y: 4.55, w: CW, h: 0.55, fontSize: 26, color: GOLD, align: "center" });
  T(s, [{ text: REPO.replace("https://", ""), options: { hyperlink: { url: REPO } } }],
    { x: X, y: 5.45, w: CW, h: 0.4, fontSize: 15, color: CREAM, align: "center" });
  T(s, "Khaled Sandoqa  ·  Abdalla Izzeldin", { x: X, y: 5.95, w: CW, h: 0.4, fontSize: 15, color: ON_DARK, align: "center" });
  s.addNotes("Thank you. We're happy to take questions. (5 s)");

  const out = path.join(__dirname, "KAMouflage_Vision_Pitch.pptx");
  await pres.writeFile({ fileName: out });
  const skill = process.env.PPTX_SKILL;
  if (skill) await require(path.join(skill, "scripts", "apply_theme.js")).applyTheme(out, THEME);
  console.log("wrote", out);
}

main().catch((e) => { console.error(e); process.exit(1); });
