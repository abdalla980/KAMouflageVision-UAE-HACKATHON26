"""About & Data: what this prototype is, where the data comes from, and demo settings."""

import streamlit as st

from lib import SECONDS_PER_IMAGE, setup_page

setup_page("About & Data", "What this prototype is, where the data comes from, and how the numbers are calculated.")

st.markdown("""
**KAMouflage Vision** is a prototype built for the MOCCAE camera-trap challenge at UAE Hackathon 2026.
It is not an official MOCCAE product.
""")

st.subheader("Demo data")
st.markdown("""
- **Photos:** 600 real camera-trap images from arid southern Africa
  ([LILA BC](https://lila.science), Snapshot Kgalagadi and Snapshot Karoo, CDLA-Permissive license).
  Real UAE camera-trap archives are not public, so these stand in for them.
- **Species names:** each southern-African animal is shown as the UAE species it stands in for
  (gemsbok → Arabian oryx, caracal → caracal, …). The original species is shown in the photo details.
- **Reserves:** real MOCCAE protected areas and coordinates from [Bayanat](https://bayanat.ae).
- **Cameras:** positions inside those reserves are **simulated**.
- **Species reference:** UAE mammals and reptiles with IUCN status from [GBIF](https://www.gbif.org/country/AE/summary),
  and MOCCAE's list of local birds (Bayanat).
- **AI results:** until the AI pipeline is connected, the results are simulated from the photos' known labels.
""")

st.subheader("How the estimates are calculated")
st.markdown(f"""
- **Time saved** assumes an expert needs about **{SECONDS_PER_IMAGE} seconds** to look at one photo by hand.
  Photos the AI filters out or identifies with high confidence don't need that look.
- **Validated observation** = a burst the AI identified with 90% confidence or more, or one an expert confirmed.
""")

st.subheader("Demo settings")


def persist(key):
    st.session_state[key] = st.session_state[f"_{key}"]


st.toggle("Show UAE counterpart names", value=st.session_state.get("uae_mode", True), key="_uae_mode",
          on_change=persist, args=("uae_mode",),
          help="Off: show the original southern-African species names.")
st.toggle("Dashboard: UAE-relevant species only", value=st.session_state.get("uae_only", True), key="_uae_only",
          on_change=persist, args=("uae_only",),
          help="Hide demo species that have no UAE counterpart, such as zebra or kudu.")

st.subheader("Privacy and data sovereignty")
st.markdown("""
Photos stay on this machine; nothing is sent to an external service. In a real deployment the system runs on a
MOCCAE server or a UAE sovereign cloud, people and vehicles are blurred automatically, and exact locations of
endangered species are only visible to authorised staff.
""")
