"""④ Insights dashboard: where and when species are active, camera coverage, export."""

import math

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

from lib import (COLORS, SECONDS_PER_IMAGE, SPECIES_PALETTE, display_species, iucn_for, load_cameras,
                 load_gbif_occurrences, load_protected_areas, model_label, observations, require_predictions,
                 setup_page, uae_counterparts, uae_mode, uae_only)

setup_page("Insights Dashboard", "Validated observations across monitored habitats: where each species is, "
                                 "when it is active, and where cameras are missing.")
df = require_predictions()

obs = observations(df)
obs["shown"] = obs["final_species"].map(lambda s: display_species(s, uae_mode()))
if uae_only():
    obs = obs[obs["final_species"].isin(uae_counterparts().keys())]
obs["hour"] = obs["datetime"].dt.hour

# ---------------------------------------------------------------- KPIs
n_img = len(df)
human_imgs = df[df["status"] == "needs_review"].shape[0]
empty_imgs = (df["detection"] == "empty").sum()
pending = df[df["effective_status"] == "needs_review"]["seq_id"].nunique()
saved_share = 1 - human_imgs / max(n_img, 1)
k = st.columns(5)
k[0].metric("Images processed", f"{n_img:,}")
k[1].metric("Empty frames filtered", f"{empty_imgs / n_img:.0%}")
k[2].metric("Validated observations", f"{len(obs):,}", help="Bursts auto-accepted (≥90%) or confirmed by an expert")
k[3].metric("Species recorded", obs["shown"].nunique())
k[4].metric("Awaiting review", pending)
st.caption(f"Experts look at **{1 - saved_share:.0%}** of images instead of all of them: an estimated "
           f"**{saved_share * 100_000 * SECONDS_PER_IMAGE / 3600:,.0f} hours saved per 100,000 images**.")

species_order = obs["shown"].value_counts().index.tolist()
color_map = {s: SPECIES_PALETTE[i % len(SPECIES_PALETTE)] for i, s in enumerate(species_order)}

# ---------------------------------------------------------------- map
st.subheader("Where: cameras, reserves and coverage gaps")
cams = load_cameras()
areas = load_protected_areas()
land = areas[areas["type"].str.lower().str.startswith("terrestrial")].copy()
covered = set(cams["reserve"])
land["covered"] = land["name"].isin(covered)
land["radius"] = land["area_km2"].clip(lower=1).map(lambda a: math.sqrt(a / math.pi) * 1000)
land["fill"] = land["covered"].map(lambda c: [182, 138, 53, 70] if c else [150, 150, 150, 60])
land["label"] = land.apply(lambda r: f"{r['name']} ({r['emirate']}) · {r['area_km2']:.0f} km² · "
                                     + ("camera coverage" if r["covered"] else "NO cameras"), axis=1)

per_cam = obs.groupby("camera_id").agg(n=("seq_id", "size"),
                                       species=("shown", lambda s: ", ".join(s.value_counts().index[:3])))
cams = cams.merge(per_cam, on="camera_id", how="left").fillna({"n": 0, "species": "–"})
cams["size"] = 900 + cams["n"] * 250
cams["label"] = cams.apply(lambda r: f"{r['camera_id']} · {r['reserve']} · {int(r['n'])} observations · {r['species']}",
                           axis=1)

show_gbif = st.toggle("Overlay known UAE sightings (GBIF)", value=False,
                      help="Where mammals were recorded in the UAE: areas with sightings but no cameras are candidates "
                           "for new camera placements.")
layers = [
    pdk.Layer("ScatterplotLayer", land, get_position=["longitude", "latitude"], get_radius="radius",
              get_fill_color="fill", get_line_color=[20, 39, 31, 160], line_width_min_pixels=1, stroked=True,
              pickable=True),
    pdk.Layer("ScatterplotLayer", cams, get_position=["longitude", "latitude"], get_radius="size",
              get_fill_color=[31, 92, 69, 230], get_line_color=[247, 243, 234], line_width_min_pixels=2, radius_min_pixels=6,
              stroked=True, pickable=True),
]
if show_gbif:
    occ = load_gbif_occurrences()
    if not occ.empty:
        layers.insert(1, pdk.Layer("HeatmapLayer", occ, get_position=["longitude", "latitude"], opacity=0.5,
                                   color_range=[[233, 223, 200], [216, 182, 106], [182, 138, 53], [140, 90, 43]]))
st.pydeck_chart(pdk.Deck(layers=layers, map_style="light",
                         initial_view_state=pdk.ViewState(latitude=24.0, longitude=54.6, zoom=6.3),
                         tooltip={"text": "{label}"}), height=480)
m1, m2 = st.columns([3, 2])
m1.caption("Green cameras (size = observations) · gold reserves with coverage · grey reserves with no cameras. "
           "Reserve boundaries are MOCCAE protected areas from Bayanat.")
gaps = land[~land["covered"]].sort_values("area_km2", ascending=False)
with m2.expander(f"{len(gaps)} terrestrial reserves without cameras"):
    st.dataframe(gaps[["name", "emirate", "area_km2"]].rename(columns={"area_km2": "km²"}),
                 hide_index=True, width="stretch")

# ---------------------------------------------------------------- when
st.subheader("When: activity by hour")
if obs.empty:
    st.info("No validated observations yet.")
    st.stop()
top = species_order[:10]
heat = (obs[obs["shown"].isin(top)].groupby(["shown", "hour"]).size().unstack(fill_value=0)
        .reindex(columns=range(24), fill_value=0).reindex(top))
heat_share = heat.div(heat.sum(axis=1), axis=0)
fig = px.imshow(heat_share, aspect="auto", color_continuous_scale=[COLORS["sand_light"], COLORS["gold_light"],
                                                                  COLORS["green"], COLORS["green_dark"]],
                labels={"x": "Hour of day", "y": "", "color": "Share of sightings"})
fig.update_xaxes(tickmode="linear", dtick=2)
fig.update_layout(height=60 + 34 * len(top), margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False,
                  paper_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
st.plotly_chart(fig, width="stretch")
night_share = obs.assign(n=obs["is_night"]).groupby("shown")["n"].mean().reindex(top)
nocturnal = night_share[night_share >= 0.6].index.tolist()
if nocturnal:
    st.caption("Mostly nocturnal in this data: **" + ", ".join(nocturnal) + "**: exactly the frames humans "
               "struggle with most.")

# ---------------------------------------------------------------- trend + species table
c1, c2 = st.columns([3, 2], gap="large")
with c1:
    st.subheader("Observations over time")
    trend = (obs[obs["shown"].isin(species_order[:6])]
             .assign(month=lambda d: d["datetime"].dt.to_period("M").dt.to_timestamp())
             .groupby(["month", "shown"]).size().reset_index(name="observations"))
    fig2 = px.bar(trend, x="month", y="observations", color="shown", color_discrete_map=color_map,
                  labels={"month": "", "shown": "Species"})
    fig2.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.2),
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=13))
    st.plotly_chart(fig2, width="stretch")

with c2:
    st.subheader("Species")
    cps = uae_counterparts()
    table =(obs.groupby("shown").agg(observations=("seq_id", "size"), cameras=("camera_id", "nunique"),
                                      species=("final_species", "first"), expert=("method", lambda m: (m == "Expert").sum()))
             .sort_values("observations", ascending=False).reset_index())
    table["IUCN"] = table["species"].map(iucn_for)
    table["match"] = table["species"].map(lambda s: cps.get(s, ("", "–"))[1])
    st.dataframe(table.drop(columns="species").rename(columns={"shown": "Species", "expert": "expert-validated"}),
                 hide_index=True, width="stretch", height=360)

# ---------------------------------------------------------------- export
st.subheader("Export")
export = pd.DataFrame({
    "observationID": obs["seq_id"],
    "deploymentID": obs["camera_id"],
    "locationName": obs["reserve"],
    "latitude": obs["latitude"],
    "longitude": obs["longitude"],
    "eventStart": obs["datetime"].dt.strftime("%Y-%m-%dT%H:%M:%S+04:00"),
    "scientificName": obs["final_species"].map(lambda s: cps.get(s, (s, ""))[0]),
    "sourceSpecies": obs["final_species"],
    "classificationMethod": obs["method"].map({"AI (auto)": "machine", "Expert": "human"}),
    "classificationProbability": obs["seq_conf"].round(3),
    "classifiedBy": obs["review_by"].where(obs["method"] == "Expert", obs["model_version"].map(model_label)),
})
st.download_button("Download validated observations (CSV, Camtrap DP-style)", export.to_csv(index=False),
                   file_name="kamouflage_validated_observations.csv", mime="text/csv", type="primary",
                   icon=":material/download:")
st.caption("Columns follow the Camtrap DP observation standard, so the export can feed GBIF or MOCCAE reporting.")
