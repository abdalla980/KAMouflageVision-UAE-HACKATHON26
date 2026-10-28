"""Decision-support suggestions for researchers.

Each suggestion is derived from the data with transparent rules, so every claim can be traced back to numbers.
A language model can later rewrite or extend these, but the evidence always comes from here.
"""

import math

import pandas as pd
import streamlit as st
from PIL import Image, ImageStat

from lib import (display_species, iucn_for, load_cameras, load_gbif_occurrences, load_protected_areas,
                 load_species_reference, observations, uae_counterparts)

THREATENED = {"Vulnerable", "Endangered", "Critically Endangered"}


@st.cache_data
def looks_like_daylight(path):
    """Daylight photos are bright AND colourful; infrared night shots are bright but grey."""
    im = Image.open(path).convert("RGB")
    im.thumbnail((96, 96))
    hsv = im.convert("HSV")
    saturation = ImageStat.Stat(hsv).mean[1]
    return ImageStat.Stat(im.convert("L")).mean[0] > 90 and saturation > 45


def km(lat1, lon1, lat2, lon2):
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def suggestion(sid, priority, title, evidence, action, link=None, link_label=None):
    return {"id": sid, "priority": priority, "title": title, "evidence": evidence, "action": action,
            "link": link, "link_label": link_label}


def build_suggestions(df, uae_mode=True):
    out = []
    obs = observations(df)
    obs["shown"] = obs["final_species"].map(lambda s: display_species(s, uae_mode))
    obs["iucn"] = obs["final_species"].map(iucn_for)

    # 1. Threatened species recorded
    thr = obs[obs["iucn"].isin(THREATENED)]
    for name, g in thr.groupby("shown"):
        cams = g["camera_id"].nunique()
        reserves = ", ".join(sorted(g["reserve"].unique()))
        out.append(suggestion(
            f"threat-{name}", "High", f"{name} ({g['iucn'].iloc[0]}) recorded {len(g)} times",
            f"Validated at {cams} camera(s) in {reserves}. Last seen {g['datetime'].max():%d %b %Y}.",
            "Keep these cameras on a short retrieval cycle and include the records in the next Red List update.",
            "views/dashboard.py", "See on the map"))

    # 2. Large reserves without cameras, ranked by known sightings nearby
    areas = load_protected_areas()
    land = areas[areas["type"].str.lower().str.startswith("terrestrial")]
    covered = set(load_cameras()["reserve"])
    occ = load_gbif_occurrences()
    gaps = []
    for _, a in land[~land["name"].isin(covered) & (land["area_km2"] >= 50)].iterrows():
        radius = max(math.sqrt(max(a["area_km2"], 1) / math.pi), 5)
        near = 0
        if not occ.empty:
            near = sum(km(a["latitude"], a["longitude"], o.latitude, o.longitude) <= radius
                       for o in occ.itertuples())
        gaps.append((near, a))
    gaps.sort(key=lambda t: (-t[0], -t[1]["area_km2"]))
    for near, a in gaps[:2]:
        n_cams = max(2, min(6, round(a["area_km2"] / 250)))
        out.append(suggestion(
            f"gap-{a['name']}", "Medium", f"No cameras in {a['name']} ({a['emirate']})",
            f"{a['area_km2']:,.0f} km² protected area with {near} known wildlife records (GBIF) inside it, "
            f"but no camera coverage.",
            f"Consider deploying about {n_cams} cameras along water points and animal trails.",
            "views/dashboard.py", "Open coverage map"))

    # 3. Cameras where the AI is often unsure
    seq = df.sort_values("frame_num").groupby("seq_id").first()
    animal = seq[seq["status"] != "empty"]
    per_cam = animal.groupby("camera_id")["status"].agg(n="size", review=lambda s: (s == "needs_review").mean())
    for cam, r in per_cam[(per_cam["n"] >= 4) & (per_cam["review"] >= 0.6)].sort_values("review").tail(2).iterrows():
        reserve = seq[seq["camera_id"] == cam]["reserve"].iloc[0]
        out.append(suggestion(
            f"cam-{cam}", "Medium", f"{cam} produces many uncertain photos",
            f"{r['review']:.0%} of its {int(r['n'])} animal bursts at {reserve} needed expert review "
            f"(average elsewhere: {per_cam['review'].mean():.0%}).",
            "On the next visit, check the camera angle, distance to the trail, vegetation in front of the lens "
            "and IR flash.",
            "views/gallery.py", "View its photos"))

    # 4. Possible clock errors: daylight-looking photos stamped at night
    night = df[df["is_night"]].copy()
    if not night.empty:
        night["daylight"] = night["abs_path"].map(looks_like_daylight)
        share = night.groupby("camera_id")["daylight"].agg(["sum", "mean"])
        suspects = share[(share["sum"] >= 3) & (share["mean"] >= 0.5)].sort_values("sum", ascending=False).head(2)
        for cam in suspects.index:
            g = night[(night["camera_id"] == cam) & night["daylight"]]
            out.append(suggestion(
                f"clock-{cam}", "Medium", f"{cam} may have a wrong clock",
                f"{len(g)} photos look like daylight but are time-stamped between "
                f"{g['datetime'].dt.strftime('%H:%M').min()} and {g['datetime'].dt.strftime('%H:%M').max()}.",
                "Check the camera's date and time on the next visit; activity-by-hour charts for this camera "
                "may be shifted.",
                "views/gallery.py", "View its photos"))

    # 5. Review backlog: which bursts to do first
    pending = df[df["effective_status"] == "needs_review"].groupby("seq_id").first()
    if not pending.empty:
        cand = pending["top3"].fillna("").map(lambda t: [c.split(":")[0] for c in t.split("|") if c])
        threatened_pending = cand.map(lambda names: any(iucn_for(n) in THREATENED for n in names)).sum()
        night_pending = int(pending["is_night"].sum())
        out.append(suggestion(
            "backlog", "High" if threatened_pending else "Info",
            f"{len(pending)} bursts waiting for review",
            f"{threatened_pending} may show a threatened species; {night_pending} are night shots.",
            "Review the possible threatened-species bursts first, with enhancement switched on.",
            "views/review.py", "Open review queue"))

    # 6. Native mammals never recorded by any camera
    ref = load_species_reference()
    wild = ref[(ref["class"] == "Mammalia") & (ref["domestic_or_captive"] != "True")
               & ref["iucn_category"].isin(["VULNERABLE", "ENDANGERED", "CRITICALLY_ENDANGERED"])]
    # Names in brackets are either "Genus species" or just "Genus" for analogue matches.
    recorded = {cp.split(" (")[1].rstrip(")") for cp, _ in
                (uae_counterparts().get(s, ("", "")) for s in obs["final_species"].unique()) if "(" in cp}
    genera = {r.split()[0] for r in recorded}
    missing = wild[~wild["scientific_name"].isin(recorded) & ~wild["genus"].isin(genera)]
    land_missing = missing[~missing["order"].isin(["Cetacea", "Sirenia"])]
    if not land_missing.empty:
        names = ", ".join(f"{r.common_name or r.scientific_name}" for r in land_missing.head(4).itertuples())
        out.append(suggestion(
            "missing", "Info", f"{len(land_missing)} threatened land mammals not detected yet",
            f"Recorded in the UAE (GBIF) but not by our cameras: {names}.",
            "Check whether current camera sites cover their habitat (mountains, gravel plains, dunes).",
            "views/dashboard.py", "Open dashboard"))

    order = {"High": 0, "Medium": 1, "Info": 2}
    return sorted(out, key=lambda s: order[s["priority"]])


def review_hints(item, burst, uae_mode=True):
    """Plain-language reasons why the AI is unsure about one burst, and what to check."""
    hints = []
    cands = [c.split(":") for c in str(item["top3"]).split("|") if ":" in c]
    if item["is_night"]:
        hints.append(("Night / IR frame", "Colours are missing at night, so similar species are harder to tell apart. "
                      "Switch on enhancement."))
    if len(cands) >= 2:
        margin = float(cands[0][1]) - float(cands[1][1])
        if margin < 0.25:
            a, b = (display_species(c[0], uae_mode) for c in cands[:2])
            hints.append(("Two close candidates", f"{a} and {b} are only {margin:.0%} apart. "
                          "Look at body size, tail and ear shape."))
    with_animal = (burst["detection"] == "animal").sum()
    if len(burst) > 1 and with_animal < len(burst):
        best = int(burst["det_conf"].idxmax()) + 1
        hints.append(("Animal not in every frame", f"Detected in {with_animal} of {len(burst)} frames. "
                      f"Frame {best} is the clearest."))
    if item["seq_conf"] < 0.5:
        hints.append(("Low overall confidence", "This may be a false trigger (wind, shadow). "
                      "Use 'No animal' if nothing is there."))
    top_iucn = iucn_for(cands[0][0]) if cands else ""
    if top_iucn in THREATENED:
        hints.append(("Possible threatened species", f"If confirmed, this is a {top_iucn} species record. "
                      "Double-check before validating."))
    return hints


def answer_question(question, df, suggestions, uae_mode=True):
    """Grounded reply for the advisor. Every number comes from the observation tables."""
    q = question.lower()
    obs = observations(df)
    if not obs.empty:
        obs["shown"] = obs["final_species"].map(lambda s: display_species(s, uae_mode))
    pending = int(df[df["effective_status"] == "needs_review"]["seq_id"].nunique())
    n_img = len(df)
    empty_share = (df["detection"] == "empty").mean() if n_img else 0

    def related(prefixes):
        return [s for s in suggestions if any(str(s["id"]).startswith(p) for p in prefixes)]

    def bullets(items):
        return "\n".join(f"- **{s['title']}.** {s['evidence']} {s['action']}" for s in items)

    if any(w in q for w in ("review", "first", "queue", "backlog", "uncertain", "next")):
        items = related(["backlog"])
        lead = f"The review queue has **{pending}** bursts, already ordered least-confident first."
        return lead + ("\n\n" + bullets(items) if items else "\n\nOpen the review queue and confirm or correct each burst. Decisions are stored with the reviewer and time.")

    if any(w in q for w in ("clock", "misconfig", "time stamp", "timestamp", "wrong time")):
        items = related(["clock-", "cam-"])
        if not items:
            return "No camera in this batch has a daylight photo stamped at night, and uncertain-photo rates are within the normal range."
        return "These deployments need a field check:\n\n" + bullets(items)

    if any(w in q for w in ("camera", "place", "coverage", "where", "gap", "deploy")):
        items = related(["gap-", "cam-"])
        if not items:
            return "Every large terrestrial reserve in this workspace already has at least one camera."
        return "Coverage from the observation database:\n\n" + bullets(items[:3])

    if any(w in q for w in ("threat", "endanger", "iucn", "oryx", "gazelle", "red list", "vulnerable")):
        items = related(["threat-", "missing"])
        if not items:
            return "No threatened species are in the validated set yet. Finish the review queue before the next Red List extract."
        return "Threatened species in the observation database:\n\n" + bullets(items[:4])

    if any(w in q for w in ("night", "nocturnal", "hour", "when", "active")):
        if obs.empty:
            return "No validated observations yet, so activity-by-hour is empty. Confirm the review queue first."
        night = obs.groupby("shown")["is_night"].mean().sort_values(ascending=False)
        top = ", ".join(f"{name} ({share:.0%} at night)" for name, share in night.head(4).items())
        return (f"Activity is computed from **{len(obs)}** validated observations. "
                f"The most nocturnal species in this batch: {top}. "
                f"Empty frames are **{empty_share:.0%}** of the archive, so those hours are not inflated by blank triggers.")

    words = [w for w in q.split() if len(w) > 3]
    hits = [s for s in suggestions if any(w in s["title"].lower() or w in s["evidence"].lower() for w in words)]
    if hits:
        return "From the observation database:\n\n" + bullets(hits[:3])

    species = obs["shown"].value_counts().head(5) if not obs.empty else None
    species_line = ""
    if species is not None and len(species):
        species_line = " Top species: " + ", ".join(f"{n} ({c})" for n, c in species.items()) + "."
    return (f"The observation database holds **{n_img}** frames and **{len(obs)}** validated observations. "
            f"**{pending}** bursts are still in review. Empty frames filtered: **{empty_share:.0%}**."
            f"{species_line} Ask what to review first, where to add cameras, or which threatened species were recorded.")
