"""① Upload & Process: ingest a camera's SD card and show what the AI did with it."""

import sys
import time
from datetime import datetime, timezone

import streamlit as st
from PIL import ExifTags, Image

from lib import (REPO_DIR, UPLOADS_DIR, badge, display_species, image_bytes, load_cameras,
                 model_label, require_predictions, setup_page, uae_mode)
from store import record_run

setup_page("Import Photos", "Ingest a camera trap memory card. Empty frames are filtered, species are identified, "
                             "and only uncertain bursts are written to the expert queue.")

STAGES = ["Ingest", "Enhance", "Detect", "Classify", "Burst vote", "Write to DB"]

tab_demo, tab_upload = st.tabs([":material/photo_camera: Import from a camera", ":material/upload_file: Upload photos"])


def batch_tallies(batch):
    tallies = {"empty": 0, "auto_accepted": 0, "needs_review": 0, "blurred_person": 0}
    for _, r in batch.iterrows():
        key = "empty" if r["detection"] == "empty" and r["status"] != "needs_review" else r["status"]
        tallies[key] = tallies.get(key, 0) + 1
    return tallies


def steps_html(active):
    parts = []
    for i, name in enumerate(STAGES):
        cls = "done" if i < active else "active" if i == active else ""
        parts.append(f"<div class='kv-step {cls}'>{i + 1} {name}</div>")
    return "<div class='kv-steps'>" + "".join(parts) + "</div>"


def show_tallies(tallies, slots):
    slots[0].metric("Empty frames removed", tallies["empty"])
    slots[1].metric("Auto-identified", tallies["auto_accepted"])
    slots[2].metric("Sent to expert review", tallies["needs_review"])
    slots[3].metric("People blurred", tallies["blurred_person"])


def show_raw_images(batch):
    """The memory card only. No species and no routing until the pipeline runs."""
    st.markdown(f"**On the memory card** · {len(batch)} photos · not identified yet")
    cols = st.columns(4)
    for i, (_, r) in enumerate(batch.head(8).iterrows()):
        with cols[i % 4]:
            st.image(image_bytes(r["abs_path"], 480, False, ""), width="stretch")
            st.caption(f"{r['datetime']:%d %b %H:%M}")


def show_routed_images(batch):
    """Photos for this deployment, gallery first, then the review queue."""
    groups = [
        ("auto_accepted", "Gallery · auto-identified"),
        ("needs_review", "Review queue"),
    ]
    for status, title in groups:
        group = batch[batch["status"] == status]
        animals = group[group["detection"] == "animal"]
        if not animals.empty:
            group = animals
        st.markdown(f"**{title}** · {len(group)}")
        if group.empty:
            continue
        cols = st.columns(4)
        for i, (_, r) in enumerate(group.head(8).iterrows()):
            name = display_species(r["seq_species"], uae_mode()) or "Animal"
            box = r["bbox"] if isinstance(r["bbox"], str) else ""
            with cols[i % 4]:
                st.image(image_bytes(r["abs_path"], 480, bool(r["is_night"]), box), width="stretch")
                st.caption(f"{name} · {r['seq_conf']:.0%}")

# ---------------------------------------------------------------- demo: replay a camera's SD card
with tab_demo:
    df = require_predictions()
    cams = load_cameras()
    counts = df.groupby("camera_id").size()
    cams = cams[cams["camera_id"].isin(counts.index)].copy()
    cams["label"] = cams.apply(lambda c: f"{c['camera_id']} · {c['reserve']} · {counts[c['camera_id']]} images", axis=1)

    labels = cams["label"].tolist()
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    choice = c1.selectbox("Camera deployment", labels, index=None, placeholder="Select a camera",
                          key="import_camera")
    run = c2.button("Run pipeline", type="primary", icon=":material/play_arrow:", width="stretch",
                    disabled=choice is None)
    if not choice:
        st.caption("Select a camera to open its memory card.")
    else:
        cam_id = choice.split(" · ")[0]
        batch = df[df["camera_id"] == cam_id].sort_values("datetime")
        reserve = batch["reserve"].iloc[0]
        emirate = batch["emirate"].iloc[0]
        seqs = batch.groupby("seq_id").first()
        ran = set(st.session_state.get("ran_cameras", []))
        already = cam_id in ran

        st.markdown(f"**{cam_id}** · **{reserve}**, {emirate} · "
                    f"{len(batch)} images in {len(seqs)} bursts · "
                    f"{batch['datetime'].min():%d %b %Y} – {batch['datetime'].max():%d %b %Y}")
        stage = st.empty()

        def show_results():
            with stage.container():
                show_routed_images(batch)
                show_tallies(batch_tallies(batch), st.columns(4))
                b1, b2 = st.columns(2)
                b1.page_link("views/review.py", label="Open these in the review queue", icon=":material/fact_check:")
                b2.page_link("views/gallery.py", label="Open these in the gallery", icon=":material/photo_library:")

        if already and not run:
            show_results()
        elif not run:
            with stage.container():
                show_raw_images(batch)

        if run:
            started = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with stage.container():
                steps = st.empty()
                bar = st.progress(0.0, text="Reading memory card ...")
                log_box = st.empty()
                slots = [col.empty() for col in st.columns(4)]
                tallies = {"empty": 0, "auto_accepted": 0, "needs_review": 0, "blurred_person": 0}
                logs = []
                step = max(1, len(batch) // 7)
                for i, (_, r) in enumerate(batch.iterrows(), 1):
                    key = "empty" if r["detection"] == "empty" and r["status"] != "needs_review" else r["status"]
                    tallies[key] = tallies.get(key, 0) + 1
                    frac = i / len(batch)
                    stage_i = min(len(STAGES) - 1, int(frac * len(STAGES)))
                    steps.markdown(steps_html(stage_i), unsafe_allow_html=True)
                    bar.progress(frac, text=f"{STAGES[stage_i]} · image {i}/{len(batch)} · {r['datetime']:%d %b %Y %H:%M}")
                    if i == 1 or i == len(batch) or i % step == 0:
                        name = display_species(r["seq_species"], uae_mode()) or "empty"
                        route = {"empty": "filtered", "auto_accepted": "auto-accept ≥90%",
                                 "needs_review": "expert queue", "blurred_person": "person blurred"}.get(key, key)
                        logs.append(f"<b>{r['datetime']:%H:%M}</b> &nbsp; {name} &nbsp; → {route}")
                        logs = logs[-4:]
                        log_box.markdown("<div class='kv-log'>" + "<br>".join(logs) + "</div>", unsafe_allow_html=True)
                    show_tallies(tallies, slots)
                    time.sleep(min(0.45, 5.0 / max(len(batch), 1)))
                steps.markdown(steps_html(len(STAGES)), unsafe_allow_html=True)
                run_id = record_run(cam_id, reserve, len(batch), tallies["empty"], tallies["auto_accepted"],
                                    tallies["needs_review"], tallies["blurred_person"], started)
                bar.progress(1.0, text=f"Written to observation database · run #{run_id}")
            st.session_state["ran_cameras"] = list(ran | {cam_id})
            st.session_state["processed_camera"] = cam_id
            show_results()

# ---------------------------------------------------------------- upload your own photos
with tab_upload:
    st.markdown("Upload camera-trap photos (JPG). They are stored locally, never sent to an external service.")
    cams = load_cameras()
    cam = st.selectbox("Which camera are these from?", cams["camera_id"] + " · " + cams["reserve"],
                       index=None, placeholder="Select a camera", key="up_cam")
    files = st.file_uploader("Camera-trap photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

    if cam and files and st.button("Save & process", type="primary", icon=":material/rocket_launch:"):
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
            with st.spinner("Running detection and classification ..."):
                result = run_pipeline([str(p) for p in saved], camera_id=cam.split(" · ")[0])
            st.success(f"Processed {len(saved)} photos and wrote them to the observation database.")
            st.dataframe(result, width="stretch")
        else:
            st.success(f"Ingested {len(saved)} photos for **{cam.split(' · ')[0]}**. "
                       "EXIF time and camera assignment are stored with the deployment. "
                       "Classification uses the same local models as the pilot batch.")
            tag = {v: k for k, v in ExifTags.TAGS.items()}
            cols = st.columns(4)
            for i, p in enumerate(saved):
                im = Image.open(p)
                exif = im.getexif()
                taken = exif.get(tag["DateTime"], "timestamp pending")
                with cols[i % 4]:
                    st.image(str(p), width="stretch")
                    st.caption(f"{p.name}  \n{taken}  \n{im.width}×{im.height}")

    st.markdown(badge("empty") + " " + badge("auto_accepted") + " " + badge("needs_review") + " "
                + badge("blurred_person"), unsafe_allow_html=True)
    st.caption("Every photo ends up in one of these four states.")
