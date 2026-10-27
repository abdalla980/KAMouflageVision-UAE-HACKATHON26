"""① Upload & Process: ingest a camera's SD card and show what the AI did with it."""

import sys
import time
from datetime import datetime

import streamlit as st
from PIL import ExifTags, Image

from lib import (REPO_DIR, UPLOADS_DIR, badge, demo_notice, load_cameras, merged, require_predictions,
                 setup_page)

setup_page("Upload & Process", "Drop in a camera's SD card. The AI removes empty frames, identifies species "
                                "and sends only uncertain bursts to an expert.")
demo_notice()

tab_demo, tab_upload = st.tabs([":material/sd_card: Process a camera (demo)", ":material/upload_file: Upload photos"])

# ---------------------------------------------------------------- demo: replay a camera's SD card
with tab_demo:
    df = require_predictions()
    cams = load_cameras()
    counts = df.groupby("camera_id").size()
    cams = cams[cams["camera_id"].isin(counts.index)].copy()
    cams["label"] = cams.apply(lambda c: f"{c['camera_id']} · {c['reserve']} · {counts[c['camera_id']]} images", axis=1)

    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    choice = c1.selectbox("Camera / SD card", cams["label"].tolist(), index=0)
    run = c2.button("Process SD card", type="primary", icon=":material/play_arrow:", width="stretch")
    cam_id = choice.split(" · ")[0]
    batch = df[df["camera_id"] == cam_id].sort_values("datetime")

    if run:
        bar = st.progress(0.0, text="Starting AI pipeline ...")
        m = st.columns(4)
        slots = [col.empty() for col in m]
        tallies = {"empty": 0, "auto_accepted": 0, "needs_review": 0, "blurred_person": 0}
        for i, (_, r) in enumerate(batch.iterrows(), 1):
            key = "empty" if r["detection"] == "empty" and r["status"] != "needs_review" else r["status"]
            tallies[key] = tallies.get(key, 0) + 1
            bar.progress(i / len(batch), text=f"Image {i}/{len(batch)} · {r['datetime']:%d %b %Y %H:%M}")
            slots[0].metric("Empty frames removed", tallies["empty"])
            slots[1].metric("Auto-identified", tallies["auto_accepted"])
            slots[2].metric("Sent to expert review", tallies["needs_review"])
            slots[3].metric("People blurred", tallies["blurred_person"])
            time.sleep(min(0.04, 2.5 / len(batch)))
        bar.progress(1.0, text="Done")
        share = 1 - tallies["needs_review"] / max(len(batch), 1)
        st.success(f"**{len(batch)} images processed.** A human only needs to look at "
                   f"**{tallies['needs_review']}** of them ({1 - share:.0%}); the AI handled **{share:.0%}**.")
        b1, b2 = st.columns(2)
        b1.page_link("views/review.py", label="Open the review queue", icon=":material/fact_check:")
        b2.page_link("views/gallery.py", label="See all photos in the gallery", icon=":material/photo_library:")
    else:
        seqs = batch.groupby("seq_id").first()
        st.markdown(f"**{cam_id}** in **{batch['reserve'].iloc[0]}**, {batch['emirate'].iloc[0]} · "
                    f"{len(batch)} images in {len(seqs)} bursts · "
                    f"{batch['datetime'].min():%d %b %Y} – {batch['datetime'].max():%d %b %Y}")
        st.caption("Press **Process SD card** to replay how the pipeline handles this card.")

# ---------------------------------------------------------------- upload your own photos
with tab_upload:
    st.markdown("Upload camera-trap photos (JPG). They are stored locally, never sent to an external service.")
    cams = load_cameras()
    cam = st.selectbox("Which camera are these from?", cams["camera_id"] + " · " + cams["reserve"], key="up_cam")
    files = st.file_uploader("Camera-trap photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

    if files and st.button("Save & process", type="primary", icon=":material/rocket_launch:"):
        folder = UPLOADS_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
        folder.mkdir(parents=True, exist_ok=True)
        saved = []
        for f in files:
            path = folder / f.name
            path.write_bytes(f.getbuffer())
            saved.append(path)

        sys.path.insert(0, str(REPO_DIR / "code"))
        try:
            from ai_pipeline.pipeline import run as run_pipeline  # provided by the AI track
        except ImportError:
            run_pipeline = None

        if run_pipeline:
            with st.spinner("Running AI pipeline ..."):
                result = run_pipeline([str(p) for p in saved], camera_id=cam.split(" · ")[0])
            st.success(f"Processed {len(saved)} photos.")
            st.dataframe(result, width="stretch")
        else:
            st.info(f"Saved {len(saved)} photos to `{folder.relative_to(REPO_DIR)}`. The AI pipeline "
                    "(`code/ai_pipeline/pipeline.py`) is not connected yet, so here is what we read from "
                    "the files themselves:")
            tag = {v: k for k, v in ExifTags.TAGS.items()}
            cols = st.columns(4)
            for i, p in enumerate(saved):
                im = Image.open(p)
                exif = im.getexif()
                taken = exif.get(tag["DateTime"], "no timestamp in EXIF")
                with cols[i % 4]:
                    st.image(str(p), width="stretch")
                    st.caption(f"{p.name}  \n📅 {taken}  \n📐 {im.width}×{im.height}")

    st.markdown(badge("empty") + " " + badge("auto_accepted") + " " + badge("needs_review") + " "
                + badge("blurred_person"), unsafe_allow_html=True)
    st.caption("Every photo ends up in one of these four states.")
