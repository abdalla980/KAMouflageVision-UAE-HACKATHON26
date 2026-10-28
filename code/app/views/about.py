"""System: database, models, data lineage and workspace settings."""

import streamlit as st

from lib import PIPELINE_MODELS, SECONDS_PER_IMAGE, setup_page
from store import db_summary, list_runs

setup_page("System", "Observation database, local models, and the lineage of the pilot batch.")

summary = db_summary()
counts = summary["counts"]
k = st.columns(5)
labels = [
    ("Deployments", "deployments"),
    ("Frames", "frames"),
    ("Classifications", "classifications"),
    ("Expert reviews", "reviews"),
    ("Pipeline runs", "pipeline_runs"),
]
for col, (label, key) in zip(k, labels):
    col.metric(label, f"{counts.get(key, 0):,}")

c1, c2 = st.columns([1.2, 1], gap="large")
with c1:
    st.subheader("Observation database")
    st.markdown(f"""
- **Engine:** SQLite, file `{summary['path']}`
- **Status:** online, read and written by this workspace
- **Contents:** camera deployments, frames, classifications, expert decisions, pipeline runs
- **Models on each classification:** {PIPELINE_MODELS}
""")
    st.subheader("Local models")
    st.markdown("""
| Step | Model | Where it runs |
|---|---|---|
| Detect animal, person, vehicle, empty | MegaDetector V6 `MDV6-mit-yolov9-c` (MIT) | This server |
| Species, geofenced to the UAE | SpeciesNet (Apache-2.0) | This server |
| Rare species fallback | BioCLIP 2 (MIT) | This server |

Images stay in this workspace. Person and vehicle frames are blurred and kept out of the analytics export.
""")
with c2:
    st.subheader("Recent pipeline runs")
    runs = list_runs(6)
    if runs.empty:
        st.info("No pipeline runs yet. Import a camera to write one.")
    else:
        show = runs.rename(columns={
            "id": "Run", "camera_id": "Camera", "reserve": "Reserve",
            "finished_at": "Finished", "n_images": "Images",
            "n_auto": "Auto", "n_review": "Review",
        })
        st.dataframe(show[["Run", "Camera", "Reserve", "Images", "Auto", "Review", "Finished"]],
                     hide_index=True, width="stretch")

st.subheader("Data lineage")
st.markdown("""
- **Reserves:** MOCCAE protected areas and coordinates from [Bayanat](https://bayanat.ae).
- **Species reference:** UAE mammals and reptiles with IUCN status from [GBIF](https://www.gbif.org/country/AE/summary),
  plus MOCCAE's list of local birds on Bayanat.
- **Pilot frames:** 600 camera-trap photos from arid habitat
  ([LILA BC](https://lila.science), Snapshot Kgalagadi and Snapshot Karoo, CDLA-Permissive).
  The MOCCAE camera archive is not public, so this batch stands in for it and each animal is shown
  under its UAE counterpart.
""")

st.subheader("How the numbers are calculated")
st.markdown(f"""
- **Time saved** assumes an expert needs about **{SECONDS_PER_IMAGE} seconds** to look at one photo by hand.
  Frames the pipeline filters or accepts at 90% confidence or more skip that look.
- **Validated observation** = a burst the model accepted at 90% or more, or a burst an expert confirmed.
  Both are stored in the observation database and included in the Camtrap DP export.
""")

st.subheader("Workspace")


def persist(key):
    st.session_state[key] = st.session_state[f"_{key}"]


st.toggle("Show UAE species names", value=st.session_state.get("uae_mode", True), key="_uae_mode",
          on_change=persist, args=("uae_mode",),
          help="Off: show the species name printed by the classifier.")
st.toggle("Dashboard: UAE species only", value=st.session_state.get("uae_only", True), key="_uae_only",
          on_change=persist, args=("uae_only",),
          help="Hide species with no UAE counterpart, such as zebra or kudu.")

st.subheader("Privacy and sovereignty")
st.markdown("""
The database and the models run on this machine. A MOCCAE deployment uses a ministry server or a UAE sovereign
cloud, with the same tables: deployments, frames, classifications, reviews and pipeline runs. Exact locations of
threatened species stay inside the authorised workspace.
""")
