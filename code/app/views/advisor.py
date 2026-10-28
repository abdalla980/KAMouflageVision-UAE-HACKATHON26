"""AI Advisor: suggestions that help researchers decide what to do next."""

import streamlit as st

from suggestions import answer_question, build_suggestions
from lib import COLORS, require_predictions, setup_page, uae_mode

setup_page("AI Advisor", "Suggestions on what to review first, where cameras are missing and which records "
                         "matter most for conservation decisions.")
df = require_predictions()

PRIORITY = {"High": "#B23A3A", "Medium": "#C98A1B", "Info": COLORS["green"]}
state = st.session_state.setdefault("advisor_state", {})

st.markdown(
    "<div class='kv-note' style='margin-bottom:14px'><b>Grounded in the observation database.</b> "
    "Every suggestion cites the records it used. The assistant answers from those same records, "
    "on this workspace, with no image sent to an external service.</div>",
    unsafe_allow_html=True)

with st.spinner("Analysing observations ..."):
    suggestions = build_suggestions(df, uae_mode())
open_items = [s for s in suggestions if s["id"] not in state]
handled = [s for s in suggestions if s["id"] in state]

tab_s, tab_chat = st.tabs([f":material/lightbulb: Suggestions ({len(open_items)})",
                           ":material/forum: Ask the assistant"])

# ---------------------------------------------------------------- suggestions
with tab_s:
    counts = {p: sum(s["priority"] == p for s in open_items) for p in PRIORITY}
    m = st.columns(3)
    for col, (p, n) in zip(m, counts.items()):
        col.metric(f"{p} priority", n)

    if not open_items:
        st.success("All suggestions handled.")
    for s in open_items:
        with st.container(border=True):
            color = PRIORITY[s["priority"]]
            st.markdown(
                f"<span style='background:{color};color:white;padding:2px 10px;border-radius:999px;"
                f"font-size:.75rem;font-weight:700'>{s['priority']}</span> "
                f"<span class='kv-species' style='font-size:1.05rem'>&nbsp;{s['title']}</span>",
                unsafe_allow_html=True)
            st.markdown(f"**Why:** {s['evidence']}")
            st.markdown(f"**Suggested action:** {s['action']}")
            c1, c2, c3 = st.columns([2, 1, 1], vertical_alignment="center")
            if s["link"]:
                c1.page_link(s["link"], label=s["link_label"], icon=":material/arrow_forward:")
            if c2.button("Mark as done", key=f"done_{s['id']}", icon=":material/check:", width="stretch"):
                state[s["id"]] = "done"
                st.rerun()
            if c3.button("Dismiss", key=f"dis_{s['id']}", icon=":material/close:", width="stretch"):
                state[s["id"]] = "dismissed"
                st.rerun()

    if handled:
        with st.expander(f"Handled ({len(handled)})"):
            for s in handled:
                c1, c2 = st.columns([5, 1], vertical_alignment="center")
                c1.markdown(f"~~{s['title']}~~ · {state[s['id']]}")
                if c2.button("Undo", key=f"undo_{s['id']}"):
                    state.pop(s["id"])
                    st.rerun()

# ---------------------------------------------------------------- assistant
PROMPTS = ["What should I review first?", "Where should we add cameras?", "Which threatened species did we record?",
           "Are any cameras misconfigured?"]

with tab_chat:
    if "advisor_chat" not in st.session_state:
        pending = int(df[df["effective_status"] == "needs_review"]["seq_id"].nunique())
        st.session_state["advisor_chat"] = [{
            "role": "assistant",
            "content": (f"Observation database is online. **{pending}** bursts are waiting in review. "
                        "Ask what to review first, where cameras are missing, or which threatened species were recorded."),
        }]
    chat = st.session_state["advisor_chat"]
    st.caption("Answers use this workspace only: classifications, reviews, reserves and camera deployments.")
    picked = st.pills("Try asking", PROMPTS, selection_mode="single", key="advisor_prompt")

    for msg in chat:
        with st.chat_message(msg["role"], avatar=":material/person:" if msg["role"] == "user" else ":material/eco:"):
            st.markdown(msg["content"])

    question = st.chat_input("Ask about species, cameras or the review queue")
    question = question or (picked if picked and st.session_state.get("_last_pick") != picked else None)
    if picked:
        st.session_state["_last_pick"] = picked
    if question:
        answer = answer_question(question, df, suggestions, uae_mode())
        chat += [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
        st.rerun()

    if len(chat) > 1 and st.button("Clear conversation", icon=":material/delete:"):
        del st.session_state["advisor_chat"]
        st.rerun()
