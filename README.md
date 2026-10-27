# KAMouflage Vision · رؤية كاموفلاج

> AI that finds and identifies UAE wildlife in camera-trap photos, including camouflaged, blurry and night shots,
> so MOCCAE rangers verify a short list instead of sorting thousands of images by hand.

**UAE Hackathon 2026 · Track 2 (Youth) · Abu Dhabi, 26–28 Oct 2026**
**Submission hard close: Wed 28 Oct, 12:00** · Pitch: 3–5 min + Q&A · Business Model Canvas slide required

---

## 1. The challenge (official, MOCCAE)

> How might we enable **MOCCAE environmental monitoring teams, conservation authorities, and researchers** to
> **identify local wildlife species** and **analyze patterns of their observed presence and spatial-temporal
> activity** across monitored habitats, to **reduce manual camera-trap image processing, accelerate validated
> observations, and improve the timeliness of conservation insights** under **image-quality,
> species-identification, spatial-coverage, and scientific-verification constraints**, using camera-trap imagery,
> species reference records, observation timestamps, location metadata, and computer vision and AI, while
> aligning with the UAE's biodiversity conservation and sustainability objectives?

**In plain words:** rangers set camera traps in the desert. These produce thousands of photos, most of them empty
(set off by wind or heat), and many dark, blurry, or showing an animal hidden against sand. Today a person checks
them all by hand and has to *guess* on the unclear ones. Insights arrive weeks late.

## 2. Our solution

| Step | What happens | Challenge constraint it answers |
|---|---|---|
| 1. Upload | Photos from the SD card plus metadata (time, camera, GPS) | – |
| 2. Filter | AI removes empty frames automatically | Reduces manual processing |
| 3. Enhance + detect | Brightens night/IR shots, finds animals even when camouflaged; uses the whole **burst** of 3–10 frames | Image quality |
| 4. Identify | Species + confidence + top 3 candidates, limited to species that live in the UAE | Species identification |
| 5. Verify | Only uncertain images go to an expert review queue; one click confirms or corrects | Scientific verification |
| 6. Insights | Map, activity by hour, trends, camera coverage gaps, export | Spatial coverage, timeliness |

**App screens (Streamlit):** ① Upload → ② Gallery → ③ Review queue → ④ Insights dashboard

### Tech stack and why it's legally safe

| Part | Choice | License |
|---|---|---|
| Animal detector | **MegaDetector V6** `MDV6-mit-yolov9-c` or `MDV6-apa-rtdetr-e` (Microsoft) | MIT / Apache-2.0 ✅ |
| Species classifier | **SpeciesNet** (Google), fed with our own detections, UAE geofence | Apache-2.0 ✅ (check the Kaggle weights license) |
| Fallback for rare UAE species | **BioCLIP 2** (zero-shot) | MIT ✅ |
| App / data | Python, Streamlit, SQLite (pilot: FastAPI + PostgreSQL/PostGIS) | open source |

⚠️ **Do NOT use MegaDetector v5 or the V6 `yolov10` variants.** They are **AGPL-3.0** (Ultralytics), which is a
problem for government procurement. SpeciesNet uses MDv5 by default, so we run the detector ourselves.
`PytorchWildlife` is unmaintained, so use the `microsoft/MegaDetector` package.

**Compliance talking points:** everything runs locally or on a UAE sovereign cloud (no images sent to foreign APIs);
people and vehicles are auto-blurred; exact locations of endangered species are coarsened when shared; humans
verify AI results and every record has an audit trail.

### Judging criteria (Rising Stars)
Alignment & impact 25% · Use of open government data 20% · Innovative AI 20% · Pitch 20% · Feasibility & **90-day pilot plan** 15%
(Pioneers: 15/15/20/15 + Market potential 15 + Pitch 20)

### 90-day pilot plan (draft)
| Weeks | Milestones | Success measure |
|---|---|---|
| 1–4 Setup & baseline | Data agreement with MOCCAE, 1 reserve (~10 cameras, ~20k archive images), measure today's manual time, deploy on MOCCAE/UAE server | Baseline hours per 1,000 images |
| 5–8 Calibrate | Run on archive, experts verify a sample, tune thresholds, fine-tune on local species | ≥ 90% of empty frames removed; accuracy per species |
| 9–12 Live pilot | Rangers use it on new retrievals; feedback; go/no-go report for scaling | ≥ 70% less review time; insights in days, not weeks |

---

## 3. The data

All demo data is in **[`data/`](data/)**. Full source and license details: **[`data/README.md`](data/README.md)**.

### 📷 Camera-trap photos (600 images, 276 bursts)

- **[`data/raw/camera_traps/kar/images/`](data/raw/camera_traps/kar/images/)**: 300 photos, Snapshot Karoo (semi-arid South Africa)
- **[`data/raw/camera_traps/kga/images/`](data/raw/camera_traps/kga/images/)**: 300 photos, Snapshot Kgalagadi (Kalahari desert)

Mix: 210 empty · 170 at night · bursts of 1–10 frames · real timestamps · real species labels (ground truth).

**Example photos per species** (the "UAE counterpart" is the animal it stands in for in our demo):

| Photo | Label | UAE counterpart | Match | Night |
|---|---|---|---|---|
| [oryx](data/raw/camera_traps/kar/images/KAR_S1/A01/A01_R1/KAR_S1_A01_R1_IMAG00142.JPG) | gemsbok | Arabian Oryx | same genus | |
| [caracal](data/raw/camera_traps/kar/images/KAR_S1/B03/B03_R1/KAR_S1_B03_R1_IMAG0949.JPG) | caracal | Caracal | same species | 🌙 |
| [wildcat](data/raw/camera_traps/kga/images/KGA_S1/B09/B09_R1/KGA_S1_B09_R1_IMAG0635.JPG) | African wildcat | Arabian Wildcat (*Felis lybica*) | same species | 🌙 |
| [honey badger](data/raw/camera_traps/kga/images/KGA_S1/A01/A01_R1/KGA_S1_A01_R1_IMAG0890.JPG) | honey badger | Honey Badger | same species | 🌙 |
| [fox](data/raw/camera_traps/kar/images/KAR_S1/B02/B02_R1/KAR_S1_B02_R1_IMAG0196.JPG) | cape fox | Arabian Red Fox / Blanford's Fox | same genus | 🌙 |
| [hare](data/raw/camera_traps/kar/images/KAR_S1/B01/B01_R1/KAR_S1_B01_R1_IMAG6643.JPG) | hare | Cape Hare | same genus | |
| [hyena](data/raw/camera_traps/kar/images/KAR_S1/E03/E03_R1/KAR_S1_E03_R1_IMAG0098.JPG) | brown hyena | Striped Hyena | same family | 🌙 |
| [porcupine](data/raw/camera_traps/kar/images/KAR_S1/C02/C02_R1/KAR_S1_C02_R1_IMAG0050.JPG) | porcupine | Indian Crested Porcupine | same genus | 🌙 |
| [bustard](data/raw/camera_traps/kar/images/KAR_S1/D03/D03_R1/KAR_S1_D03_R1_IMAG0128.JPG) | kori bustard | Houbara Bustard | same family | |
| [steenbok](data/raw/camera_traps/kar/images/KAR_S1/D01/D01_R1/KAR_S1_D01_R1_IMAG0101.JPG) | steenbok | Arabian / Sand Gazelle | analogue | 🌙 |
| [empty night](data/raw/camera_traps/kar/images/KAR_S1/F02/F02_R1/KAR_S1_F02_R1_IMAG1014.JPG) | empty | – | – | 🌙 |

To find more: open [`data/processed/images.csv`](data/processed/images.csv), filter `ground_truth`, and open the
`file_path` (relative to `data/`).

### 📊 Tables the app reads: [`data/processed/`](data/processed/)

| File | Contents |
|---|---|
| [`images.csv`](data/processed/images.csv) | 1 row per photo: camera, reserve, GPS, timestamp, burst (`seq_id`), ground truth, night flag, UAE counterpart |
| [`cameras.csv`](data/processed/cameras.csv) | 35 **simulated** cameras inside 8 real UAE reserves |
| [`species_reference.csv`](data/processed/species_reference.csv) | UAE species: 72 mammals + 77 reptiles (GBIF, with IUCN status) + 381 birds (MOCCAE) |
| [`protected_areas.csv`](data/processed/protected_areas.csv) | MOCCAE's 44 protected areas with coordinates |
| [`data_sources.json`](data/processed/data_sources.json) | Provenance and licenses |

### 🏛️ Original source files: [`data/raw/`](data/raw/)

- **[`bayanat/`](data/raw/bayanat/)**: 9 datasets from **bayanat.ae** (MOCCAE / Federal Competitiveness and Statistics Centre):
  protected lands with coordinates, natural reserves by emirate and type, designated protected areas, and the
  **List of local Aves (Birds) in the UAE – 2023**. Bayanat has **no wildlife sightings or camera-trap data**.
- **[`gbif/`](data/raw/gbif/)**: UAE species list + 6,017 real UAE sighting coordinates from GBIF.org

### ✅ What's real vs. simulated (say this in the pitch)

| | Status |
|---|---|
| Photos | Real camera-trap photos from comparable arid habitats in southern Africa, **not the UAE** |
| Reserves, species list, IUCN status | Real UAE data (MOCCAE via Bayanat, GBIF) |
| Camera positions | **Simulated** inside real reserves |
| Timestamps | Real time of day and season; years shifted to 2023–2025 (the date printed on the photo still shows 2017/18) |

Known data quirks (good pitch material): labels apply to the whole burst, so some frames labelled "caracal" don't
show the caracal; some camera clocks are wrong (a daylight photo stamped "8:32 PM").

---

## 4. Getting started

```bash
git clone https://github.com/abdalla980/KAMouflage-Vision---UAE-HACKATHON26.git
cd KAMouflage-Vision---UAE-HACKATHON26
python -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

The data is already in the repo. To re-download or change the size: `python data/scripts/fetch_all.py --n-images 600`

## 5. Repo layout

```
├── README.md              ← you are here
├── data/                  demo data + scripts (see data/README.md)
├── material/              hackathon PDFs (playbook, agenda, Q&A, challenge profiles)
├── Images & Videos/       logo and concept images
└── requirements.txt
```

## 6. Status / next steps

- [x] Problem and solution defined, license and legal check
- [x] Data pipeline: Bayanat + GBIF + LILA camera traps → `data/processed/`
- [ ] AI pipeline: MegaDetector V6 (MIT) → enhance → SpeciesNet → burst grouping → confidence routing
- [ ] Streamlit app: Upload · Gallery · Review queue · Insights dashboard
- [ ] Pre-computed results as a demo fallback
- [ ] Pitch deck: problem, demo, data, 90-day plan, Business Model Canvas

**Working together:** pull before you start (`git pull`), commit small and often, and say in the group chat which
part you're on so you don't edit the same file.
