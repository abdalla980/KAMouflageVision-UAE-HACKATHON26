"""③ Review queue: an expert confirms or corrects only the bursts the AI was unsure about."""

import pandas as pd
import streamlit as st

from suggestions import review_hints
from lib import (badge, display_species, image_bytes, load_reviews, require_predictions, save_review,
                 setup_page, uae_mode)

setup_page("Review Queue", "Only the bursts the AI is unsure about. One click turns an AI suggestion into a "
                           "scientifically validated observation.")
df = require_predictions()


queue = (df[df["effective_status"] == "needs_review"]
         .sort_values(["seq_conf", "datetime"]).groupby("seq_id", sort=False).first().reset_index())
reviews = load_reviews()
done_today = len(reviews)
total_review = df[df["status"] == "needs_review"]["seq_id"].nunique()

m1, m2, m3 = st.columns(3)
m1.metric("Waiting for review", len(queue))
m2.metric("Validated by experts", int((reviews["decision"].isin(["confirm", "correct"])).sum()))
m3.metric("Rejected (not an animal)", int((reviews["decision"] == "not_animal").sum()))
st.progress(1 - len(queue) / max(total_review, 1), text=f"{total_review - len(queue)} of {total_review} reviewed")

if queue.empty:
    st.success("Queue is empty: every observation is validated. 🎉")
    st.page_link("views/dashboard.py", label="Go to the insights dashboard", icon=":material/monitoring:")
    st.stop()

order = st.sidebar.radio("Queue order", ["Least confident first", "Oldest first"], index=0)
if order == "Oldest first":
    queue = queue.sort_values("datetime")
# Skipped bursts stay in the queue but move to the back.
skipped = set(reviews.loc[reviews["decision"] == "skipped", "seq_id"])
queue = pd.concat([queue[~queue["seq_id"].isin(skipped)], queue[queue["seq_id"].isin(skipped)]])
item = queue.iloc[0]
burst = df[df["seq_id"] == item["seq_id"]].sort_values("frame_num").reset_index(drop=True)

left, right = st.columns([3, 2], gap="large")
with left:
    frame_idx = 0
    if len(burst) > 1:
        frame_idx = st.select_slider("Frame in burst", options=list(range(len(burst))),
                                     format_func=lambda i: f"{i + 1} of {len(burst)} · {burst.loc[i, 'detection']}",
                                     value=int(burst["det_conf"].idxmax()))
    frame = burst.loc[frame_idx]
    enhanced = st.toggle("Enhance (AI view)", value=bool(frame["is_night"]))
    st.image(image_bytes(frame["abs_path"], 1200, enhanced, frame["bbox"]), width="stretch")
    st.caption(f"{frame['camera_id']} · {frame['reserve']}, {frame['emirate']} · "
               f"{frame['datetime']:%d %b %Y, %H:%M}{' · 🌙 night' if frame['is_night'] else ''}")

with right:
    st.markdown(f"{badge('needs_review')} &nbsp; burst confidence **{item['seq_conf']:.0%}**", unsafe_allow_html=True)
    st.markdown("#### AI suggestion")
    def shown(s):
        """UAE name, plus the demo photo's own species when it differs (e.g. 'Arabian Oryx · Gemsbok')."""
        d = display_species(s, uae_mode())
        return d if d == s else f"{d} · {s}"

    cands = [c.split(":") for c in item["top3"].split("|") if c] if item["top3"] else []
    for name, p in cands:
        st.progress(float(p), text=f"{shown(name)} · {float(p):.0%}")

    hints = review_hints(item, burst, uae_mode())
    if hints:
        with st.container(border=True):
            st.markdown(":material/auto_awesome: **AI hint: why this one is uncertain**")
            for title, text in hints:
                st.markdown(f"- **{title}.** {text}")

    names = [n for n, _ in cands]
    all_species = sorted({s for s in df["species"].unique() if s} | set(names), key=shown)
    choice = st.selectbox("Species", all_species, index=all_species.index(names[0]) if names else 0,
                          format_func=shown)

    c1, c2 = st.columns(2)
    if c1.button("Confirm", type="primary", icon=":material/check_circle:", width="stretch"):
        decision = "confirm" if names and choice == names[0] else "correct"
        save_review(item["seq_id"], decision, choice, "Expert")
        st.toast(f"Validated: {display_species(choice, uae_mode())}", icon="✅")
        st.rerun()
    if c2.button("No animal", icon=":material/block:", width="stretch"):
        save_review(item["seq_id"], "not_animal", "", "Expert")
        st.toast("Marked as false trigger", icon="🚫")
        st.rerun()
    if st.button("Skip for now", icon=":material/skip_next:", width="stretch"):
        save_review(item["seq_id"], "skipped", "", "Expert")
        st.rerun()
    st.caption("Picking a different species than the AI's first choice records a **correction**, which is "
               "used to retrain the model later.")

    with st.expander("Demo ground truth"):
        st.write(f"Burst label: `{item['ground_truth']}`")
        if item["uae_counterpart"] == item["uae_counterpart"]:
            st.write(f"UAE counterpart: {item['uae_counterpart']} ({item['uae_match']})")

if not reviews.empty:
    with st.expander(f"Review history ({done_today})"):
        st.dataframe(reviews.sort_values("timestamp", ascending=False), width="stretch", hide_index=True)
