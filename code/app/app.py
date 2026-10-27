"""KAMouflage Vision – camera-trap wildlife monitoring for MOCCAE.

Run from the repo root:
    streamlit run code/app/app.py
"""

import streamlit as st

from lib import LOGO

st.set_page_config(page_title="KAMouflage Vision", page_icon=str(LOGO), layout="wide",
                   initial_sidebar_state="expanded")

pages = st.navigation({
    "Workflow": [
        st.Page("views/upload.py", title="Import Photos", url_path="upload", icon=":material/upload:", default=True),
        st.Page("views/gallery.py", title="Gallery", url_path="gallery", icon=":material/photo_library:"),
        st.Page("views/review.py", title="Review Queue", url_path="review", icon=":material/fact_check:"),
    ],
    "Insights": [
        st.Page("views/dashboard.py", title="Insights Dashboard", url_path="dashboard", icon=":material/monitoring:"),
        st.Page("views/advisor.py", title="AI Advisor", url_path="advisor", icon=":material/auto_awesome:"),
    ],
    "Info": [
        st.Page("views/about.py", title="About & Data", url_path="about", icon=":material/info:"),
    ],
})
pages.run()
