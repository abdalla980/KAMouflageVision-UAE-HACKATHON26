"""Shared data loading, styling and image helpers for the KAMouflage Vision app."""

import io
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageOps

APP_DIR = Path(__file__).resolve().parent
REPO_DIR = APP_DIR.parents[1]
DATA_DIR = REPO_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = DATA_DIR / "results"
PREDICTIONS_CSV = RESULTS_DIR / "predictions.csv"
REVIEWS_CSV = RESULTS_DIR / "reviews.csv"
UPLOADS_DIR = DATA_DIR / "uploads"
LOGO = APP_DIR / "assets" / "logo.png"

# Palette taken from the KAMouflage Vision logo: desert green, sand and gold.
COLORS = {
    "green_dark": "#14271F",
    "green": "#1F5C45",
    "green_light": "#4E8A6B",
    "sand": "#E9DFC8",
    "sand_light": "#F7F3EA",
    "gold": "#B68A35",
    "gold_light": "#D8B66A",
    "text": "#1B2A23",
    "muted": "#6B746F",
}
STATUS = {
    "auto_accepted": ("Auto-identified", "#2E7D4F"),
    "needs_review": ("Needs review", "#C98A1B"),
    "empty": ("Empty", "#8A8F8C"),
    "blurred_person": ("Person blurred", "#B23A3A"),
    "validated": ("Expert validated", "#1F5C45"),
    "rejected": ("Not an animal", "#8A8F8C"),
}
SPECIES_PALETTE = ["#1F5C45", "#B68A35", "#4E8A6B", "#8C5A2B", "#6F9C86", "#D8B66A",
                   "#2F4858", "#A3684A", "#8DA47E", "#C9A66B", "#5B6B4E", "#9C7A3C"]

# Readable names for the LILA Snapshot Safari labels (what a species classifier would output).
LABEL_NAMES = {
    "gemsbokoryx": "Gemsbok", "caracal": "Caracal", "catafricanwild": "African Wildcat",
    "honeybadger": "Honey Badger", "harecape": "Cape Hare", "hare": "Hare", "foxcape": "Cape Fox",
    "foxbateared": "Bat-eared Fox", "hyenabrown": "Brown Hyena", "hyenaspotted": "Spotted Hyena",
    "steenbok": "Steenbok", "springbok": "Springbok", "duiker": "Common Duiker",
    "duikercommongrey": "Common Duiker", "klipspringer": "Klipspringer", "bustardkori": "Kori Bustard",
    "bustardludwigs": "Ludwig's Bustard", "mongoosesmallcapegrey": "Cape Grey Mongoose",
    "mongooseyellow": "Yellow Mongoose", "porcupine": "Cape Porcupine", "rodent": "Rodent",
    "reptilesamphibians": "Reptile", "tortoise": "Tortoise", "birdofprey": "Bird of Prey",
    "birdsofprey": "Bird of Prey", "birdother": "Bird", "ostrich": "Ostrich", "eland": "Eland",
    "kudu": "Kudu", "jackalblackbacked": "Black-backed Jackal", "hartebeestred": "Red Hartebeest",
    "baboon": "Chacma Baboon", "zebramountain": "Mountain Zebra", "zebraburchells": "Plains Zebra",
    "wildebeestblue": "Blue Wildebeest", "leopard": "Leopard", "lionfemale": "Lion", "lionmale": "Lion",
    "secretarybird": "Secretarybird", "reedbuckmountain": "Mountain Reedbuck", "rhebokgrey": "Grey Rhebok",
    "rabbitriverine": "Riverine Rabbit", "aardvarkantbear": "Aardvark", "meerkatsuricate": "Meerkat",
    "cheetah": "Cheetah", "monkeyvervet": "Vervet Monkey", "rhinocerosblack": "Black Rhino",
}
NON_ANIMAL = {"", "empty", "none", "nan"}


def label_name(label):
    return LABEL_NAMES.get(label, label.replace("_", " ").title())


def primary_label(ground_truth):
    """Pick one label for a burst: prefer an animal with a UAE counterpart, never 'empty' when an animal is present."""
    labels = [l for l in str(ground_truth).split("|") if l and l != "empty"]
    return labels[0] if labels else "empty"


# ---------------------------------------------------------------- data loading

@st.cache_data
def load_images():
    df = pd.read_csv(PROCESSED_DIR / "images.csv", dtype={"frame_num": "Int64"})
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["abs_path"] = df["file_path"].map(lambda p: str(DATA_DIR / p))
    df["is_night"] = df["is_night"].astype(str) == "True"
    return df


@st.cache_data
def load_cameras():
    return pd.read_csv(PROCESSED_DIR / "cameras.csv")


@st.cache_data
def load_protected_areas():
    return pd.read_csv(PROCESSED_DIR / "protected_areas.csv")


@st.cache_data
def load_species_reference():
    return pd.read_csv(PROCESSED_DIR / "species_reference.csv", dtype=str).fillna("")


@st.cache_data
def load_gbif_occurrences():
    path = DATA_DIR / "raw" / "gbif" / "uae_occurrences.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


@st.cache_data
def uae_counterparts():
    """Classifier species name -> (UAE counterpart, match level), derived from the dataset table."""
    df = load_images().dropna(subset=["uae_counterpart"])
    single = df[~df["ground_truth"].str.contains("|", regex=False)]
    return {label_name(r["ground_truth"]): (r["uae_counterpart"], r["uae_match"])
            for _, r in single.drop_duplicates("ground_truth").iterrows()}


def display_species(species, uae_mode=True):
    """Name shown in the UI. In UAE demo mode, stand-in species are shown as their UAE counterpart."""
    if not isinstance(species, str) or species.lower() in NON_ANIMAL:
        return ""
    if uae_mode:
        cp = uae_counterparts().get(species)
        if cp:
            return re.sub(r"\s*\(.*\)$", "", cp[0])
    return species


def load_predictions():
    if not PREDICTIONS_CSV.exists():
        return None
    df = pd.read_csv(PREDICTIONS_CSV, dtype=str).fillna("")
    for col in ("det_conf", "species_conf", "seq_conf"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def load_reviews():
    cols = ["seq_id", "decision", "final_species", "reviewer", "timestamp"]
    if not REVIEWS_CSV.exists():
        return pd.DataFrame(columns=cols)
    return pd.read_csv(REVIEWS_CSV, dtype=str).fillna("")


def save_review(seq_id, decision, final_species, reviewer):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    reviews = load_reviews()
    reviews = reviews[reviews["seq_id"] != seq_id]
    row = {"seq_id": seq_id, "decision": decision, "final_species": final_species,
           "reviewer": reviewer or "expert", "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    pd.concat([reviews, pd.DataFrame([row])], ignore_index=True).to_csv(REVIEWS_CSV, index=False)


def merged():
    """Images joined with predictions and expert reviews. Returns None if there are no predictions yet."""
    preds = load_predictions()
    if preds is None:
        return None
    df = load_images().merge(preds.drop(columns=["seq_id"], errors="ignore"), on="image_id", how="inner")
    reviews = load_reviews().set_index("seq_id")
    df["review_decision"] = df["seq_id"].map(reviews["decision"]).fillna("")
    df["review_species"] = df["seq_id"].map(reviews["final_species"]).fillna("")
    df["review_by"] = df["seq_id"].map(reviews["reviewer"]).fillna("")

    def effective_status(r):
        if r["review_decision"] in ("confirm", "correct"):
            return "validated"
        if r["review_decision"] == "not_animal":
            return "rejected"
        return r["status"]

    df["effective_status"] = df.apply(effective_status, axis=1)
    df["final_species"] = df.apply(
        lambda r: r["review_species"] if r["review_decision"] in ("confirm", "correct") else r["seq_species"], axis=1)
    return df


def observations(df):
    """One row per burst that counts as a validated observation (AI >= threshold or expert-confirmed)."""
    seq = df.sort_values("frame_num").groupby("seq_id", as_index=False).first()
    obs = seq[seq["effective_status"].isin(["auto_accepted", "validated"]) & (seq["final_species"] != "")].copy()
    obs["method"] = obs["effective_status"].map({"auto_accepted": "AI (auto)", "validated": "Expert"})
    return obs


def require_predictions():
    df = merged()
    if df is None:
        st.warning("No AI results yet. Generate demo results with "
                   "`python code/app/mock_predictions.py`, or run the AI pipeline.")
        st.stop()
    return df


# ---------------------------------------------------------------- images

def enhance(im):
    """Brighten dark / IR frames and stretch contrast (a light-weight stand-in for CLAHE)."""
    gray = ImageOps.grayscale(im)
    mean = sum(i * c for i, c in enumerate(gray.histogram())) / max(gray.width * gray.height, 1)
    if mean < 70:  # dark night / IR frame
        eq = ImageOps.equalize(im)
        return Image.blend(im, eq, 0.75)
    return ImageOps.autocontrast(im, cutoff=1)


def draw_bbox(im, bbox, color=COLORS["gold_light"]):
    try:
        x, y, w, h = (float(v) for v in str(bbox).split(","))
    except ValueError:
        return im
    W, H = im.size
    im = im.copy()
    d = ImageDraw.Draw(im)
    width = max(3, W // 200)
    d.rectangle([x * W, y * H, (x + w) * W, (y + h) * H], outline=color, width=width)
    return im


@st.cache_data(max_entries=400)
def image_bytes(path, max_side=640, enhanced=False, bbox=""):
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_side, max_side))
    if enhanced:
        im = enhance(im)
    if bbox:
        im = draw_bbox(im, bbox)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return buf.getvalue()


# ---------------------------------------------------------------- UI helpers

def badge(status):
    label, color = STATUS.get(status, (status, COLORS["muted"]))
    return (f'<span style="background:{color};color:white;padding:2px 9px;border-radius:999px;'
            f'font-size:0.75rem;font-weight:600;white-space:nowrap">{label}</span>')


def setup_page(title, subtitle=""):
    st.logo(str(LOGO), size="large")
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="kv-header"><div class="kv-title">{title}</div>'
        f'<div class="kv-sub">{subtitle}</div></div>', unsafe_allow_html=True)


SECONDS_PER_IMAGE = 8  # assumed manual review time; explained on the About page


def uae_mode():
    """Demo setting (About page): show stand-in species under their UAE counterpart name."""
    return st.session_state.get("uae_mode", True)


def uae_only():
    """Demo setting (About page): hide demo species that have no UAE counterpart."""
    return st.session_state.get("uae_only", True)


CSS = f"""
<style>
.kv-header {{
  background: linear-gradient(120deg, {COLORS['green_dark']} 0%, {COLORS['green']} 70%, {COLORS['green_light']} 100%);
  border-bottom: 4px solid {COLORS['gold']};
  border-radius: 14px; padding: 18px 24px; margin-bottom: 18px;
}}
.kv-title {{ color: {COLORS['sand_light']}; font-size: 1.7rem; font-weight: 700; letter-spacing: .2px; }}
.kv-sub {{ color: {COLORS['gold_light']}; font-size: .95rem; margin-top: 2px; }}
.kv-note {{
  background: {COLORS['sand']}; border-left: 4px solid {COLORS['gold']}; border-radius: 8px;
  padding: 10px 12px; font-size: .8rem; color: {COLORS['text']}; margin-top: 8px;
}}
.kv-card-meta {{ color: {COLORS['muted']}; font-size: .78rem; line-height: 1.35; }}
.kv-species {{ font-weight: 700; color: {COLORS['text']}; font-size: .95rem; }}
div[data-testid="stMetric"] {{
  background: white; border: 1px solid {COLORS['sand']}; border-top: 4px solid {COLORS['gold']};
  border-radius: 12px; padding: 12px 16px;
}}
div[data-testid="stMetricValue"] {{ color: {COLORS['green']}; }}
section[data-testid="stSidebar"] {{ border-right: 3px solid {COLORS['gold']}; }}
[data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none; }}
</style>
"""
