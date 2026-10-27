"""② Gallery: every photo with what the AI found, filters, and a before/after enhancement toggle."""

import streamlit as st

from lib import STATUS, badge, display_species, image_bytes, require_predictions, setup_page, uae_mode

setup_page("Gallery", "Every photo with the AI's result. Switch on enhancement to see camouflaged and "
                      "night-time animals the way the AI sees them.")
df = require_predictions()

df["shown_species"] = df["final_species"].map(lambda s: display_species(s, uae_mode()))

# ---------------------------------------------------------------- filters
f1, f2, f3, f4 = st.columns([2, 2, 4, 1.6])
reserves = f1.multiselect("Reserve", sorted(df["reserve"].unique()))
species = f2.multiselect("Species", sorted(s for s in df["shown_species"].unique() if s))
status_keys = ["auto_accepted", "needs_review", "validated", "empty", "rejected"]
statuses = f3.pills("Status", status_keys, format_func=lambda k: STATUS[k][0], selection_mode="multi",
                    default=["auto_accepted", "needs_review", "validated"])
with f4:
    night_only = st.toggle("Night only", value=False)
    enhanced = st.toggle("Enhance (AI view)", value=False, help="Brightens dark/IR frames and stretches contrast.")

view = df
if reserves:
    view = view[view["reserve"].isin(reserves)]
if species:
    view = view[view["shown_species"].isin(species)]
if statuses:
    view = view[view["effective_status"].isin(statuses)]
if night_only:
    view = view[view["is_night"]]
view = view.sort_values(["datetime", "frame_num"])

# ---------------------------------------------------------------- detail dialog


@st.dialog("Photo detail", width="large")
def detail(row):
    burst = df[df["seq_id"] == row["seq_id"]].sort_values("frame_num")
    a, b = st.columns(2)
    a.image(image_bytes(row["abs_path"], 1100, False, row["bbox"]), caption="Original", width="stretch")
    b.image(image_bytes(row["abs_path"], 1100, True, row["bbox"]), caption="Enhanced (AI view)",
            width="stretch")
    st.markdown(f"<span class='kv-species'>{row['shown_species'] or 'No animal'}</span> &nbsp; "
                f"{badge(row['effective_status'])}", unsafe_allow_html=True)
    st.markdown(f"Burst confidence **{row['seq_conf']:.0%}** · frame detection **{row['detection']}** "
                f"({row['det_conf']:.0%}) · {row['camera_id']} · {row['reserve']} · "
                f"{row['datetime']:%d %b %Y, %H:%M}")
    if row["top3"]:
        st.caption("Top candidates: " + " · ".join(
            f"{display_species(c.split(':')[0], uae_mode())} {float(c.split(':')[1]):.0%}" for c in row["top3"].split("|")))
    st.caption(f"Source: {row['dataset'].upper()} {row['image_id']} · ground truth (burst): {row['ground_truth']}"
               + (f" · UAE counterpart: {row['uae_counterpart']} ({row['uae_match']})" if row['uae_counterpart'] == row['uae_counterpart'] else ""))
    if len(burst) > 1:
        st.markdown(f"**All {len(burst)} frames in this burst**")
        cols = st.columns(len(burst))
        for col, (_, f) in zip(cols, burst.iterrows()):
            col.image(image_bytes(f["abs_path"], 300, True, f["bbox"]), width="stretch",
                      caption=f"#{f['frame_num']} · {f['detection']}")


# ---------------------------------------------------------------- grid
PER_PAGE = 20
pages = max(1, -(-len(view) // PER_PAGE))
# Go back to page 1 whenever the filters change.
filter_key = (tuple(reserves), tuple(species), tuple(statuses or ()), night_only)
if st.session_state.get("gallery_filters") != filter_key:
    st.session_state["gallery_filters"] = filter_key
    st.session_state["gallery_page"] = 1
page = min(st.session_state.get("gallery_page", 1), pages)


def pager(where):
    if pages <= 1:
        return
    left, mid, right = st.columns([1, 2, 1], vertical_alignment="center")
    if left.button("Previous", key=f"prev_{where}", icon=":material/chevron_left:", disabled=page == 1,
                   width="stretch"):
        st.session_state["gallery_page"] = page - 1
        st.rerun()
    mid.markdown(f"<div style='text-align:center'>Page <b>{page}</b> of {pages}</div>", unsafe_allow_html=True)
    if right.button("Next", key=f"next_{where}", icon=":material/chevron_right:", disabled=page == pages,
                    width="stretch"):
        st.session_state["gallery_page"] = page + 1
        st.rerun()


st.markdown(f"**{len(view)}** photos · {view['seq_id'].nunique()} bursts")
pager("top")

chunk = view.iloc[(page - 1) * PER_PAGE: page * PER_PAGE]
cols = st.columns(4)
for i, (_, r) in enumerate(chunk.iterrows()):
    with cols[i % 4], st.container(border=True):
        st.image(image_bytes(r["abs_path"], 520, enhanced, r["bbox"]), width="stretch")
        name = r["shown_species"] or "No animal"
        conf = f" · {r['seq_conf']:.0%}" if r["shown_species"] else ""
        moon = " 🌙" if r["is_night"] else ""
        st.markdown(f"<div class='kv-species'>{name}{conf}{moon}</div>{badge(r['effective_status'])}"
                    f"<div class='kv-card-meta'>{r['camera_id']} · {r['reserve']}<br>"
                    f"{r['datetime']:%d %b %Y, %H:%M} · frame {r['frame_num']}/{r['seq_num_frames']}</div>",
                    unsafe_allow_html=True)
        if st.button("Details", key=f"d_{r['image_id']}", icon=":material/zoom_in:", width="stretch"):
            detail(r)

if view.empty:
    st.info("No photos match these filters.")
else:
    pager("bottom")
