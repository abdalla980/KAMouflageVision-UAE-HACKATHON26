"""Draw the architecture diagrams as SVG (for GitHub) and PNG (for slides).

    python code/diagrams/make_diagrams.py

Writes docs/diagrams/*.svg and, if Microsoft Edge is installed, *.png.
"""

import shutil
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "diagrams"
FONT = "Segoe UI, Helvetica Neue, Arial, sans-serif"

C = {"dark": "#14271F", "green": "#1F5C45", "sand": "#E9DFC8", "paper": "#F7F3EA", "gold": "#B68A35",
     "text": "#1B2A23", "muted": "#5E6963", "line": "#3B4A42"}
STYLES = {
    "default": ("white", C["green"], C["text"], C["muted"]),
    "core": (C["dark"], C["gold"], C["paper"], "#D8C9A3"),
    "good": ("#DCEBE2", C["green"], C["text"], C["muted"]),
    "review": ("#F6E7C8", C["gold"], C["text"], C["muted"]),
    "out": ("#ECEBE7", "#9AA19D", C["text"], C["muted"]),
    "source": (C["sand"], C["gold"], C["text"], C["muted"]),
}
TITLE_PX, LINE_PX = 21, 17


class Diagram:
    def __init__(self, w, h):
        self.w, self.h, self.parts = w, h, []

    def box(self, x, y, w, h, title, lines=(), style="default"):
        fill, stroke, tcol, lcol = STYLES[style]
        for text, px in [(title, TITLE_PX)] + [(l, LINE_PX) for l in lines]:
            if len(text) * px * 0.55 > w - 24:  # rough width check so nothing overflows
                print(f"  warning: '{text}' may be too wide for a {w}px box")
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" '
                          f'stroke="{stroke}" stroke-width="2.5"/>')
        total = TITLE_PX + len(lines) * (LINE_PX + 9) + (8 if lines else 0)
        ty = y + (h - total) / 2 + TITLE_PX - 3
        self.parts.append(f'<text x="{x + w / 2}" y="{ty}" text-anchor="middle" font-size="{TITLE_PX}" '
                          f'font-weight="700" fill="{tcol}">{escape(title)}</text>')
        for i, line in enumerate(lines):
            ly = ty + 10 + (i + 1) * (LINE_PX + 9)
            self.parts.append(f'<text x="{x + w / 2}" y="{ly}" text-anchor="middle" font-size="{LINE_PX}" '
                              f'fill="{lcol}">{escape(line)}</text>')

    def left_box(self, x, y, w, h, title, lines, style="core"):
        """Box with left-aligned lines (for step lists)."""
        fill, stroke, tcol, lcol = STYLES[style]
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" '
                          f'stroke="{stroke}" stroke-width="2.5"/>')
        self.parts.append(f'<text x="{x + 22}" y="{y + 38}" font-size="{TITLE_PX}" font-weight="700" '
                          f'fill="{tcol}">{escape(title)}</text>')
        for i, line in enumerate(lines):
            self.parts.append(f'<text x="{x + 22}" y="{y + 76 + i * 28}" font-size="{LINE_PX}" '
                              f'fill="{lcol}">{escape(line)}</text>')

    def arrow(self, points, label=None, at=None, dashed=False):
        d = "M" + " L".join(f"{x},{y}" for x, y in points)
        dash = ' stroke-dasharray="8 6"' if dashed else ""
        self.parts.append(f'<path d="{d}" fill="none" stroke="{C["line"]}" stroke-width="2.5"{dash} '
                          f'marker-end="url(#head)"/>')
        if label:
            lx, ly = at
            pad = len(label) * 15 * 0.55 / 2 + 8
            self.parts.append(f'<rect x="{lx - pad}" y="{ly - 16}" width="{2 * pad}" height="24" rx="6" '
                              f'fill="{C["paper"]}"/>')
            self.parts.append(f'<text x="{lx}" y="{ly + 1}" text-anchor="middle" font-size="15" '
                              f'font-weight="600" fill="{C["green"]}">{escape(label)}</text>')

    def frame(self, x, y, w, h, caption):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="none" '
                          f'stroke="{C["gold"]}" stroke-width="2" stroke-dasharray="10 7"/>')
        self.parts.append(f'<text x="{x + 20}" y="{y + h - 16}" font-size="16" font-style="italic" '
                          f'fill="{C["gold"]}">{escape(caption)}</text>')

    def title(self, text):
        self.parts.append(f'<text x="40" y="44" font-size="26" font-weight="700" fill="{C["dark"]}">'
                          f'{escape(text)}</text>')

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" font-family="{FONT}">'
                f'<defs><marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
                f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{C["line"]}"/></marker></defs>'
                f'<rect width="100%" height="100%" fill="{C["paper"]}"/>' + "".join(self.parts) + "</svg>")


def system_architecture():
    d = Diagram(1440, 860)
    d.title("System architecture (MOCCAE pilot)")
    d.frame(290, 80, 1120, 750, "Runs inside the UAE: MOCCAE server or UAE sovereign cloud. All models run locally.")
    d.box(40, 200, 210, 170, "Camera traps", ["motion / heat trigger", "bursts of 3–10 frames", "GPS per camera"],
          "source")
    d.box(320, 200, 230, 170, "Ingest", ["SD card upload or LTE", "read EXIF timestamp", "link to camera"])
    d.left_box(600, 130, 400, 270, "AI pipeline (GPU workers)", [
        "1  Enhance night / IR frames",
        "2  Detect: MegaDetector V6 (MIT)",
        "3  Blur people and vehicles",
        "4  Classify: SpeciesNet, UAE species",
        "5  Combine all frames of a burst",
        "6  Route by confidence",
    ])
    d.box(1080, 200, 300, 170, "Expert review queue", ["only bursts under 90%", "confirm / correct / reject"],
          "review")
    d.box(600, 540, 400, 170, "Observation database", ["PostgreSQL + PostGIS, image store",
                                                      "audit trail: model, reviewer, time"])
    d.box(1080, 540, 300, 170, "Insights dashboard", ["species map, activity by hour", "trends, coverage gaps"],
          "good")
    d.box(1080, 735, 300, 70, "Export: Camtrap DP", [], "out")
    d.arrow([(250, 285), (316, 285)])
    d.arrow([(550, 285), (596, 285)])
    d.arrow([(1000, 285), (1076, 285)], "< 90%", (1040, 268))
    d.arrow([(720, 400), (720, 536)], "≥ 90%: auto-accepted", (720, 470))
    d.arrow([(1230, 370), (1230, 470), (940, 470), (940, 536)], "validated", (1100, 470))
    d.arrow([(1000, 625), (1076, 625)])
    d.arrow([(1230, 710), (1230, 731)])
    d.arrow([(1230, 200), (1230, 108), (800, 108), (800, 126)], "corrections retrain the model", (1015, 108),
            dashed=True)
    return d


def ai_pipeline():
    d = Diagram(1480, 640)
    d.title("What happens to one burst of photos")
    y, h, w = 260, 120, 200
    xs = [40, 280, 520, 760, 1000, 1240]
    d.box(xs[0], y, w, h, "Burst", ["3–10 frames", "one trigger"], "source")
    d.box(xs[1], y, w, h, "Enhance", ["brighten night/IR", "stretch contrast"])
    d.box(xs[2], y, w, h, "Detect", ["MegaDetector V6", "MIT license"], "core")
    d.box(xs[3], y, w, h, "Classify", ["SpeciesNet", "UAE species only"], "core")
    d.box(xs[4], y, w, h, "Burst vote", ["combine frames,", "best frame wins"])
    d.box(xs[5], y, w, h, "Confidence", ["burst score", "0 – 100%"])
    for a, b in zip(xs, xs[1:]):
        d.arrow([(a + w, y + h / 2), (b - 4, y + h / 2)])
    d.box(500, 80, 240, 90, "Empty: filtered out", [], "out")
    d.box(500, 480, 240, 90, "Person: blurred", [], "out")
    d.arrow([(620, y), (620, 174)], "no animal", (620, 218))
    d.arrow([(620, y + h), (620, 476)], "person / vehicle", (620, 430))
    d.box(1220, 80, 240, 90, "Auto-accepted", ["90% or more"], "good")
    d.box(1220, 480, 240, 90, "Expert review", ["under 90%"], "review")
    d.arrow([(1340, y), (1340, 174)])
    d.arrow([(1340, y + h), (1340, 476)])
    return d


def prototype():
    d = Diagram(1440, 600)
    d.title("Hackathon prototype: what is in this repo")
    d.box(40, 90, 250, 110, "Bayanat (MOCCAE)", ["reserves, local species"], "source")
    d.box(40, 230, 250, 110, "GBIF", ["UAE species, IUCN status"], "source")
    d.box(40, 370, 250, 110, "LILA BC", ["600 camera-trap photos"], "source")
    d.box(350, 210, 250, 150, "data_pipeline", ["code/data_pipeline/", "fetch and clean"])
    d.box(660, 210, 250, 150, "data/processed", ["images, cameras,", "species, reserves"], "source")
    d.box(970, 80, 200, 130, "ai_pipeline", ["code/ai_pipeline/", "(in progress)"], "core")
    d.box(1210, 80, 200, 130, "predictions.csv", ["demo version from", "mock_predictions.py"], "review")
    d.left_box(970, 320, 440, 200, "Streamlit app (code/app/)", [
        "Upload & Process",
        "Gallery with before/after enhancement",
        "Review Queue: writes reviews.csv",
        "Insights Dashboard: map, hours, export",
    ])
    for yy in (145, 285, 425):
        d.arrow([(290, yy), (320, yy), (320, 285), (346, 285)])
    d.arrow([(600, 285), (656, 285)])
    d.arrow([(910, 285), (940, 285), (940, 145), (966, 145)])
    d.arrow([(910, 285), (940, 285), (940, 420), (966, 420)])
    d.arrow([(1170, 145), (1206, 145)])
    d.arrow([(1310, 210), (1310, 316)])
    return d


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    edge = next((p for p in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                             r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                             shutil.which("msedge") or ""] if p and Path(p).exists()), None)
    for name, fn in [("system-architecture", system_architecture), ("ai-pipeline", ai_pipeline),
                     ("prototype", prototype)]:
        print(name)
        d = fn()
        svg = OUT / f"{name}.svg"
        svg.write_text(d.svg(), encoding="utf-8")
        if edge:
            subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            f"--window-size={d.w},{d.h}", "--force-device-scale-factor=2",
                            f"--screenshot={OUT / f'{name}.png'}", svg.as_uri()],
                           capture_output=True, timeout=120)
    print(f"Diagrams written to {OUT}")


if __name__ == "__main__":
    main()
