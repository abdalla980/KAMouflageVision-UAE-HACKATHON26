# KAMouflage Vision – Project Notes (Session 27 Oct 2026)

This is the full record of the planning session for our UAE Hackathon 2026 entry, written for teammates joining
the project. It follows the conversation in order: each section is a question we worked through, and what we
decided. The short version is in [`README.md`](README.md); this file has the reasoning behind it.

**Key dates:** Abu Dhabi hackathon 26–28 Oct 2026 · **Submission hard close Wed 28 Oct, 12:00** · Judging the same day.

---

## Contents

1. [What's in the material folder](#1-whats-in-the-material-folder)
2. [The problem: first understanding](#2-the-problem-first-understanding)
3. [The official challenge and what it adds](#3-the-official-challenge-and-what-it-adds)
4. [Software architecture](#4-software-architecture)
5. [The 90-day plan](#5-the-90-day-plan)
6. [Legal check: model licenses and UAE rules](#6-legal-check-model-licenses-and-uae-rules)
7. [What the finished product looks like](#7-what-the-finished-product-looks-like)
8. [Where the data comes from](#8-where-the-data-comes-from)
9. [What we built: the data pipeline](#9-what-we-built-the-data-pipeline)
10. [Decisions log](#10-decisions-log)
11. [Next steps and how to split the work](#11-next-steps-and-how-to-split-the-work)
12. [Sources](#12-sources)

---

## 1. What's in the material folder

`material/` holds the official hackathon documents: the HackArena Playbook (Track 2), orientation slides, the Q&A
sheet, the Challenge Profiles overview, registration journey and the Abu Dhabi agenda. These are **general hackathon
documents**. The specific challenge profile was shared separately (we got the official challenge statement later,
see section 3).

Useful facts from them:

- **Pitch:** the Playbook says 5 min + 3 min questions; the Q&A sheet says 3 min + 2 min. **Prepare for the shorter one.**
  All team members take part, slides in Arabic or English, **one slide must be a Business Model Canvas**.
- **AI tools are allowed** and encouraged this year.
- **No working prototype required**, but "any development you add makes it stronger".
- **Judging criteria, Rising Stars (school students):**

  | Criterion | Weight |
  |---|---|
  | Alignment with challenge & impact | 25% |
  | Effective use of (open government) data | 20% |
  | Innovative use of AI & emerging tech | 20% |
  | Presentation, clarity & creativity | 20% |
  | Feasibility & planning, incl. **a 90-day execution plan** | 15% |

  **Pioneers (university, 17–25):** Alignment 15 · Data 15 · AI 20 · Feasibility 15 · **Market potential 15** · Pitch 20.
- The Playbook lists UAE open data portals (Bayanat, Abu Dhabi, Dubai, Sharjah, Ajman, RAK, Fujairah). Citing the
  exact dataset and portal "directly strengthens the Data Readiness and Problem Clarity" scores.

`Images & Videos/` has our logo (**KAMouflage Vision / رؤية كاموفلاج**, with an Arabian oryx, a camera shutter in
camouflage pattern and AI graphics) and a concept image of a researcher mounting a camera trap on a ghaf tree in
the desert, with a grainy night-vision animal shot on a laptop.

## 2. The problem: first understanding

Our starting understanding: *someone's job is to check a huge number of photos by hand, and they have to guess on
unclear images whether there's an animal in them or not.*

That's correct. Expanded:

- Rangers and researchers mount **camera traps** that shoot automatically on motion or heat.
- **Most photos are empty** (wind, heat shimmer, moving plants).
- Many others are hard to read: **night/IR shots, motion blur, animals camouflaged against sand and scrub**, or
  only part of an animal in frame. The person has to **guess** whether it's an animal and which species.
- This is **slow, tiring and inconsistent**. Data reaches conservation decisions late, and rare species can be
  missed or miscounted.

## 3. The official challenge and what it adds

> How might we enable **MOCCAE environmental monitoring teams, conservation authorities, and researchers** to
> **identify local wildlife species** and **analyze patterns of their observed presence and spatial-temporal
> activity** across monitored habitats, to **reduce manual camera-trap image processing, accelerate validated
> observations, and improve the timeliness of conservation insights** under **image-quality,
> species-identification, spatial-coverage, and scientific-verification constraints**, using camera-trap imagery,
> species reference records, observation timestamps, location metadata, and computer vision and artificial
> intelligence while aligning with the UAE's biodiversity conservation and sustainability objectives?

(MOCCAE = Ministry of Climate Change and Environment.)

**Breakdown:**

| Part | What it says | What it means for us |
|---|---|---|
| Who | MOCCAE monitoring teams, conservation authorities, researchers | Users are government field teams and scientists |
| Outcome 1 | Identify local wildlife **species** | Not just "animal / no animal": *which* UAE species |
| Outcome 2 | Presence patterns, **spatial-temporal activity** | **Where and when**: maps, activity by hour, trends |
| Impact | Less manual work, faster **validated** observations, timely insights | Measure hours saved and days from photo to insight |
| Constraint: image quality | Night/IR, blur, camouflage | Our "KAMouflage" angle, the strongest differentiator |
| Constraint: species ID | Similar-looking species, partial animals | Confidence score + top 3 candidates |
| Constraint: spatial coverage | Limited cameras, gaps | Show coverage and where cameras are missing |
| Constraint: scientific verification | Results must be trustworthy | **Human in the loop**: AI suggests, an expert confirms |
| Data | Images, species reference records, timestamps, location metadata | We need all four |
| Alignment | UAE biodiversity & sustainability goals | Mention national biodiversity strategy, oryx protection |

**Problem statement (in the Playbook's formula):**

> MOCCAE monitoring teams and researchers manually review thousands of camera-trap images, many of them empty,
> dark, blurred, or showing camouflaged animals. Because of the lack of automated, trustworthy species
> identification, they guess on unclear images and spend weeks before observations are validated. This happens
> with every camera retrieval cycle across all monitored habitats. As a result, conservation insights about where
> and when species are active arrive late. The goal is fast, scientifically verified species observations with
> clear spatial-temporal patterns.

**What the official wording adds to our first idea:** our first idea covered filtering, detecting and identifying.
The official version also needs **(5) a verification step** and **(6) spatial-temporal analysis**. Judges will
look for both.

## 4. Software architecture

### Core idea: assemble existing models, don't train from scratch

Training a species model by the deadline is not realistic, and open-source wildlife models already exist:

| Job | Model | Why |
|---|---|---|
| Animal / person / vehicle / empty | **MegaDetector** (Microsoft) | The standard camera-trap detector; robust on night/IR and partly hidden animals; filters most empty frames |
| Species ID | **SpeciesNet** (Google) | Trained on millions of camera-trap images; supports **geofencing by country** (`ARE`) |
| Fallback for rare local species | **BioCLIP 2** (zero-shot) | Matches against a text list of UAE species a generic model may lack |

**Open check:** run test images to see how well SpeciesNet labels UAE species. If coverage is weak, BioCLIP plus
our UAE species list is the backup.

### Full system (what we pitch for the pilot)

```
 FIELD                    INGEST                  AI PIPELINE (async workers)                 PEOPLE
┌──────────┐   SD card  ┌────────────┐  queue  ┌──────────────────────────────────────┐   ┌──────────────┐
│Camera    │──────────▶│Upload +     │───────▶│1 Enhance  (CLAHE for night/IR, dehaze)│   │Expert review │
│traps     │  or LTE    │EXIF parse   │        │2 Detect   MegaDetector + tiling for   │   │queue (verify │
│(GPS per  │            │time, cam ID │        │           small/camouflaged animals   │──▶│/ correct)    │
│deployment│            │→ deployment │        │3 Group    burst/sequence (same event) │   └──────┬───────┘
└──────────┘            └────────────┘        │4 Classify SpeciesNet + UAE geofence   │          │ verified
                                               │           + GBIF UAE species prior    │          ▼
                                               │5 Route    conf ≥ 0.9 → auto-accept    │   ┌──────────────┐
                                               │           conf < 0.9 → human queue    │   │PostgreSQL +  │
                                               └──────────────────────────────────────┘   │PostGIS       │
                                                         ▲  retrain on verified crops       └──────┬───────┘
                                                         └──────── active learning ◀──────────────┤
                                                                                                    ▼
                                    ┌───────────────────────────────────────────────────────────────────┐
                                    │ ANALYTICS: species map · activity by hour · detections over time  │
                                    │ RAI (relative abundance) · coverage gaps (hex grid) · alerts       │
                                    │ EXPORT: Camtrap DP standard → GBIF / MOCCAE reporting               │
                                    └───────────────────────────────────────────────────────────────────┘
```

### How each design choice answers a challenge constraint

| Constraint | Design answer |
|---|---|
| **Image quality** | Contrast enhancement (CLAHE) before detection; tiled inference for small, distant animals; **burst grouping**: one trigger gives 3–10 frames, so if one frame is clear the whole burst is labelled |
| **Species identification** | UAE geofence + species list from GBIF UAE records (the "species reference records"); top 3 with confidence |
| **Scientific verification** | Confidence routing; only human-confirmed or high-confidence records count as *validated*; audit trail per record (model version, reviewer, time) |
| **Spatial coverage** | Each camera deployment stored with GPS and active dates; hex-grid map with "no camera here" gaps; later: suggest new placements |
| **Timeliness** | Asynchronous pipeline turns weeks into hours. Phase 2: **edge AI** on the camera (Jetson / Raspberry Pi + LTE), so only detections are sent |
| **Sovereignty** | On-prem at MOCCAE or a UAE sovereign cloud; all models run locally, no images sent to foreign APIs |

**Pilot stack:** Python, FastAPI, Celery + Redis workers, PostgreSQL + PostGIS, S3-compatible storage (MinIO),
React dashboard, Docker on one GPU server.

**Competitors if judges ask:** Wildlife Insights, Addax AI (formerly EcoAssist), Timelapse. Our edge: a
UAE-specific species prior, burst-based handling of camouflage, a MOCCAE verification workflow, and spatial-temporal
insights built in, not just tagging.

### Hackathon build (by the deadline)

- **One Python app in Streamlit** with the screens Upload, Gallery, Review queue, Insights.
- MegaDetector and SpeciesNet on CPU (about 1–3 s per image, fine for a demo batch).
- **SQLite** instead of Postgres; Plotly / pydeck for map and charts.
- **Pre-compute all results** on the demo set and cache them; do one small live upload in the pitch, with the
  cached results ready in case of WiFi problems.
- Rough time plan: ~3 h pipeline, ~2 h review queue, ~3 h dashboard, the rest for pitch, 90-day plan and
  Business Model Canvas.
- Fallback if coding stalls: a clickable mock-up driven by the same cached AI results.

## 5. The 90-day plan

**What it is:** from the judging criteria: *"ease of implementation in the actual work environment of the government
entity, including a clear 90-day execution plan to test the product, with defined milestones and a realistic
timeline"* (15%). It's not about the hackathon. It's one slide answering: *"If MOCCAE said yes tomorrow, what
would we do in the next 3 months to test this with them?"*

| Phase | Weeks | Milestones | Success measure |
|---|---|---|---|
| 1. Setup & baseline | 1–4 | Data-sharing agreement with MOCCAE; 1 protected area (e.g. Arabian Oryx PA), ~10 cameras, ~20k archive images; measure today's manual review time; deploy on MOCCAE server or UAE cloud | Baseline: hours per 1,000 images |
| 2. Calibrate | 5–8 | Run AI on the archive; experts verify a sample; tune thresholds and UAE species list; fine-tune on verified local photos (oryx, gazelles, foxes, sand cat) | ≥ 90% of empty frames removed; accuracy per species |
| 3. Live pilot | 9–12 | Rangers use it on new camera retrievals; review queue and dashboard in daily use; feedback sessions; go/no-go report on scaling | ≥ 70% less review time; insights in days, not weeks |

## 6. Legal check: model licenses and UAE rules

Feasibility is graded, so we checked that a government entity can actually use this.

### Model licenses

| Component | License | OK for government use? |
|---|---|---|
| MegaDetector **v5** | **AGPL-3.0** (built with Ultralytics) | ⚠️ **Avoid.** AGPL obliges sharing the source of network-served systems; Ultralytics sells commercial licenses for this case. A red flag in procurement |
| MegaDetector V6 **`MDV6-mit-yolov9-c`** | **MIT** | ✅ **Use this** |
| MegaDetector V6 **`MDV6-apa-rtdetr-e`** | **Apache-2.0** | ✅ More accurate alternative |
| MegaDetector V6 `yolov10-e` / `yolov10-c` | AGPL-3.0 | ⚠️ Avoid |
| SpeciesNet code (Google) | Apache-2.0 | ✅ |
| SpeciesNet weights (Kaggle) | Not stated on the pages checked | ❓ **Check the Kaggle model page before the pitch** |
| BioCLIP 2 | MIT | ✅ |
| PytorchWildlife library | MIT, but **no longer maintained** (v1.3.1 final) | ⚠️ Use the `microsoft/MegaDetector` package instead |

**Catch:** by default SpeciesNet runs MegaDetector **v5 (AGPL)** internally. So our pipeline runs the MIT/Apache
MegaDetector V6 itself, crops the animals and passes the crops to SpeciesNet's classifier only. (Still to confirm in
code that SpeciesNet accepts outside detections.)

**Pitch line:** *"Every model component is MIT or Apache-2.0 licensed: no license fees, no vendor lock-in,
MOCCAE owns the deployment."*

### UAE rules

| Topic | What applies | How we handle it |
|---|---|---|
| Personal data | The **PDPL** (Federal Decree-Law 45/2021) excludes government entities and government data, so MOCCAE itself isn't bound by it. But camera traps catch rangers, visitors, poachers | MegaDetector detects "person"/"vehicle" → **auto-blur**, never shown in analytics; originals only for authorized staff (anti-poaching). Privacy by design |
| Cloud & sovereignty | UAE Cloud Policy covers federal ministries: encryption keys generated and kept **in the UAE**, foreign access denied by default for sovereign tiers | Deploy on MOCCAE servers or a certified UAE sovereign cloud; all models local |
| Sensitive species locations | Exact GPS of endangered species can help poachers | Role-based access; coarsened locations in public exports (GBIF sensitive-data practice) |
| Responsible AI | UAE AI charter principles: human oversight, transparency | Human verification queue, confidence scores, audit trail |

**Caveats:** the legal points come from law-firm and secondary summaries, not statute texts; the PDPL's executive
regulations have a disputed status; MOCCAE decides which cloud tier applies. Pitch these as "designed for
compliance", not legal advice.

## 7. What the finished product looks like

A **web app in the browser**. One person runs `streamlit run app.py`, it opens at `http://localhost:8501`, and it
can be shown on the projector. Optionally it goes online (e.g. Hugging Face Spaces) with demo data only, so judges
can scan a QR code.

**① Upload**: the ranger drops in photos from a camera's SD card.
```
┌─ KAMouflage Vision ──────────────────────────────────────────────┐
│ Camera: [CAM-07 · Arabian Oryx PA ▼]   Drop images here 📂       │
│ Processing 1,240 images  ███████████████░░░░  78%                 │
│  ✓ 812 empty (removed)   ✓ 301 auto-identified   ⚠ 97 need review│
│  🔒 30 people/vehicles detected → blurred                         │
└───────────────────────────────────────────────────────────────────┘
```

**② Gallery**: every photo with what the AI found, filters, and a **before/after toggle** (dark original vs.
enhanced with box). This is the "camouflage" moment for the judges.
```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ [night photo]│ [blurry]     │ [day photo]  │ [person ▓▓]  │
│ Arabian Oryx │ Sand Cat?    │ Arabian      │ Person       │
│ 96% ✓ auto   │ 61% ⚠ review │ Gazelle 93% ✓│ blurred 🔒   │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

**③ Review queue**: the expert confirms only uncertain cases (keyboard shortcuts); one click makes a record
**validated**; corrections are saved for retraining.
```
┌──────────────────────────────────────┬───────────────────────────┐
│   [large photo, enhanced, with box]  │ AI suggestion:            │
│   ◀ frame 2 of 5 in this burst ▶     │  1. Sand Cat      61%     │
│                                      │  2. Arabian Red Fox 24%   │
│                                      │ [✓ Confirm] [✎ Correct ▼] │
└──────────────────────────────────────┴───────────────────────────┘
```

**④ Insights dashboard**: KPIs (images, species, validated observations, hours saved), map with cameras and
coverage gaps, activity by hour per species, sightings over time, species breakdown, **export** (Camtrap DP / CSV).

**Demo flow in the pitch (~60 s):** upload a small batch ("812 of 1,240 were empty") → gallery night photo ("a
human guesses here; we find the camouflaged animal") → confirm 2 in the review queue ("the expert stays in
control") → dashboard ("sand cats only active at night; here's a habitat with no cameras"). The cached results
are the fallback.

**Be honest about:** no real MOCCAE data (public photos, simulated UAE locations) and no UAE-trained model yet;
both are part of the 90-day plan.

## 8. Where the data comes from

The challenge names four data types. Real MOCCAE camera-trap images aren't public, so we combine real camera-trap
photos from similar desert habitats with real UAE species and location data.

| Data type | Source | Real or simulated |
|---|---|---|
| Camera-trap images | **LILA BC** Snapshot Kgalagadi (Kalahari) + Snapshot Karoo (semi-arid), CDLA-Permissive-1.0 | Real camera-trap photos, **not from the UAE** |
| Species reference records | **GBIF** UAE occurrences (mammals, reptiles, with IUCN status) + **MOCCAE** local bird list (Bayanat) | Real UAE data |
| Location metadata | **MOCCAE** "Protected Lands Coordinates in UAE" (Bayanat) | Real reserves; **camera positions simulated** inside them |
| Timestamps | Camera-trap metadata | Real time of day and season; years shifted |

Other sources considered:
- **iNaturalist / GBIF photos** (CC0 / CC-BY only) are useful for testing species ID on real UAE animals, but they
  aren't camera-trap shots.
- **Abu Dhabi ADSDI** protected-areas layer (EAD) is licensed "government entities only", so we don't use it in the
  demo; in the pilot it would connect.
- **Protected Planet (WDPA)** is an open alternative for reserve boundaries.
- **GBIF West Asia EIA Data Repository** (AGEDI, Abu Dhabi) holds biodiversity survey records.
- **Don't use photos from news articles or press releases** (copyrighted).

### What we found on Bayanat (bayanat.ae)

Bayanat has **no wildlife sightings or camera-trap data**: searches for "wildlife", "biodiversity", "mammal" and
"endangered" return nothing. It does have MOCCAE / FCSC datasets we use:

- Protected Lands Coordinates in UAE (**45 reserves with GPS**, the basis of our map)
- Protected Lands in UAE · Protected Lands by Area, Emirate and Zone
- Designated Protected Areas by Types and Emirates
- Natural Reserves in UAE by Emirate, Type and Establishment Year
- Long-Range Nature Reserves in the UAE · Areas of Nature Reserves According to the Type and Emirate
- **List of local Aves (Birds) in the UAE – 2023** (381 species) · Local Birds List

**Pitch line:** *"We used MOCCAE's own open data for reserves and species. The camera-trap archive is MOCCAE-internal,
which is why the 90-day pilot starts with it."*

Technical note: Bayanat has no proper public API, so our script uses the same requests the website makes (search →
dataset page → download). If the site changes, the script may need a fix. The server sometimes drops connections,
so the script retries.

## 9. What we built: the data pipeline

All code is in [`code/`](code/). The data pipeline is in [`code/data_pipeline/`](code/data_pipeline/) and the data
in [`data/`](data/) (details: [`data/README.md`](data/README.md)).

```bash
python -m venv .venv
.venv\Scripts\activate                       # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python code/data_pipeline/fetch_all.py       # already done; data is in the repo
```

| Script | What it does |
|---|---|
| `fetch_bayanat.py` | Downloads the 9 Bayanat datasets (xlsx + csv) and a manifest |
| `fetch_species_reference.py` | GBIF: 149 UAE species (72 mammals, 77 reptiles) with names, family, IUCN status + 6,017 UAE sighting points |
| `fetch_camera_traps.py` | Picks a balanced 600-image subset from LILA (whole bursts only) and downloads them resized |
| `build_demo_dataset.py` | Places 35 simulated cameras in 8 real reserves, shifts years, and writes the clean tables |
| `fetch_all.py` | Runs all four in order; a failing source doesn't stop the rest |

**Result:**

- **600 photos in 276 bursts:** 210 empty, 170 at night. Images:
  [`data/raw/camera_traps/kar/images/`](data/raw/camera_traps/kar/images/) and
  [`data/raw/camera_traps/kga/images/`](data/raw/camera_traps/kga/images/)
- **Reserves:** Arabian Oryx, Al Houbara, Al Marzoum, Qasr Al Sarab, Al Wathba, Dubai Desert Conservation Reserve,
  Wadi Wurayah, Jebel Hafeet
- **Tables** in [`data/processed/`](data/processed/): `images.csv`, `cameras.csv`, `species_reference.csv`
  (530 species incl. birds), `protected_areas.csv`, `data_sources.json`

**UAE counterparts.** The photos show southern-African species. Each is mapped to a UAE counterpart with a match level:

| Match | Examples |
|---|---|
| same species | caracal, African/Arabian wildcat (*Felis lybica*), cape hare |
| same genus | gemsbok → Arabian oryx; cape fox → Arabian red / Blanford's fox; porcupine |
| same family | kori bustard → Asian houbara |
| not mapped | brown hyena (striped hyena is extinct in the wild in the UAE), honey badger (no UAE records in GBIF) |
| analogue only | steenbok / springbok / duiker → gazelles; klipspringer → Arabian tahr |

Present these as stand-ins in the pitch, not as UAE data.

**Data quirks we found (good pitch material):**
1. **Labels apply to the whole burst**, so some frames labelled "caracal" don't show the caracal. That's exactly
   why our app judges a burst as a whole.
2. **Camera clocks are sometimes wrong**: a daylight photo is stamped "8:32 PM". The tool could flag this.
3. The date printed on each photo shows the original year (2017–18); in our tables years are shifted to 2023–25.
   Don't zoom in on the printed date during the demo.
4. LILA removed images of people for privacy; those bursts are skipped.
5. GBIF also lists pets, livestock and zoo animals (domestic cat, camel, Patagonian mara), flagged as
   `domestic_or_captive` in the species table.

## 10. Decisions log

| # | Decision | Why |
|---|---|---|
| 1 | Use existing open models, not training from scratch | Not realistic before the deadline; mature wildlife models exist |
| 2 | MegaDetector **V6 MIT/Apache variants only**; SpeciesNet classifier fed with our detections | Avoid AGPL; feasibility is graded |
| 3 | Human-in-the-loop verification + spatial-temporal dashboard are must-haves | Explicitly in the official challenge |
| 4 | Burst/sequence grouping as a core feature | Handles camouflage and blur; real labels are burst-level anyway |
| 5 | Streamlit + SQLite for the prototype; FastAPI/Postgres/PostGIS for the pilot | Speed now, credible architecture later |
| 6 | Pre-compute results; live upload only for a few images | Demo safety |
| 7 | LILA Kgalagadi + Karoo photos, GBIF + Bayanat for UAE data, simulated cameras in real reserves | Best available public data; honest labelling |
| 8 | Commit images to the repo (~290 MB) | Teammates can see the data on GitHub without running scripts |
| 9 | All code in `code/` | Team preference |

## 11. Next steps and how to split the work

- [x] Problem and solution defined, license and legal check
- [x] Data pipeline and demo dataset
- [ ] **AI pipeline** (`code/`): MegaDetector V6 (MIT) → enhance (CLAHE) → crop → SpeciesNet (geofence `ARE`) →
      burst grouping → confidence routing → results cached to SQLite/CSV. Measure accuracy against `ground_truth`.
- [ ] Check the SpeciesNet weights license on Kaggle and its UAE species coverage
- [ ] **Streamlit app**: Upload · Gallery (before/after toggle) · Review queue · Insights dashboard (map with
      reserves and cameras, activity by hour, trends, coverage gaps, export)
- [ ] **Pitch deck:** problem → demo → data used (cite Bayanat datasets by name) → architecture → legal/compliance
      → 90-day plan → Business Model Canvas → team
- [ ] Rehearse the 60-second demo flow, with cached fallback

**Suggested split:** one person on the AI pipeline, one on the Streamlit screens (they can start with
`data/processed/images.csv` and fake predictions until the pipeline is ready), one on the pitch deck and Business
Model Canvas.

**Working together:** `git pull` before you start, commit small and often, and say in the group chat which file
you're editing.

## 12. Sources

Models and licenses
- [microsoft/MegaDetector (per-variant licenses)](https://github.com/microsoft/MegaDetector)
- [Microsoft Biodiversity license page (MDv5 AGPL)](https://microsoft.github.io/Biodiversity/license/)
- [microsoft/Pytorch-Wildlife](https://github.com/microsoft/Pytorch-Wildlife)
- [google/cameratrapai (SpeciesNet)](https://github.com/google/cameratrapai)
- [BioCLIP 2](https://huggingface.co/imageomics/bioclip-2)
- [Ultralytics licensing](https://www.ultralytics.com/license)

UAE rules
- [Al Tamimi: UAE data sovereignty / Cloud Policy](https://www.tamimi.com/law-update/the-technology-issue-2026/articles/new-data-sovereignty-rules-for-cloud-consumers-and-providers-in-the-uae/)
- [Simmons & Simmons: UAE PDPL FAQs](https://www.simmons-simmons.com/en/publications/ckwugz8lu16rs0a44qvbqcbz9/uae-personal-data-protection-law-faqs)
- [Modulos: PDPL scope](https://docs.modulos.ai/frameworks/uae-pdpl/scope-enforcement-and-the-executive-regulation)
- [Baker McKenzie: UAE data & cyber laws](https://resourcehub.bakermckenzie.com/en/resources/global-data-and-cyber-handbook/emea/uae/topics/key-data-and-cybersecurity-laws)

Data
- [LILA BC datasets](https://lila.science/datasets) · [Snapshot Kgalagadi](https://lila.science/datasets/snapshot-kgalagadi)
- [Bayanat (UAE federal open data)](https://bayanat.ae)
- [GBIF UAE country page](https://www.gbif.org/country/AE/summary) · [GBIF Country Report UAE](https://analytics-files.gbif.org/country/AE/GBIF_CountryReport_AE.pdf)
- [GBIF West Asia EIA Data Repository](https://www.gbif.org/installation/e42db8b1-d5c5-46fa-ab1e-b81b0fc1e464)
- [Protected Planet: UAE](https://www.protectedplanet.net/country/ARE)
- [ADSDI protected areas layer (EAD)](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/OpenData/ADSDI_OpenData/MapServer/127/iteminfo)
