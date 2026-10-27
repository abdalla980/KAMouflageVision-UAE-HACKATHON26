# Things to double-check

Open questions and risks collected while building. Tick them off as you go.

## Before the deadline (Wed 28 Oct, 12:00)

- [ ] **Submission format.** What exactly do we hand in at 12:00 (slides only? link? video?) and where?
- [ ] **Pitch length.** The Playbook says 5 min + 3 Q&A, the Q&A sheet says 3 + 2. Ask an organizer; rehearse the shorter one.
- [ ] **Say the AI results are simulated** if the real pipeline isn't connected by then. The app reads
      `data/results/predictions.csv`; right now that comes from `mock_predictions.py` (`model_version = DEMO-mock-0.1`).
- [ ] **Reset the review queue before the demo:** delete `data/results/reviews.csv` so it starts at 105.
- [ ] **Venue WiFi.** The dashboard map tiles (CARTO) and fonts load from the internet. Test the app offline,
      and keep screenshots of every screen in the deck as a fallback.
- [ ] **Projector test.** Run the app at 1280×720 and check that nothing is cut off.
- [ ] **Laptop:** charger, app already running, browser tab open on the Upload screen.
- [ ] **Slides still missing:** Business Model Canvas, 90-day plan, team. The diagrams are in `docs/diagrams/*.png`.
- [ ] **MOCCAE logo on the title slide** only with the organizers' OK ("Challenge by MOCCAE"), never as our app's logo.

## AI pipeline (`code/ai_pipeline/`)

- [ ] **Python version.** The venv is Python 3.14. PyTorch / MegaDetector / SpeciesNet may not support it yet;
      a separate Python 3.11 or 3.12 venv for the AI part is probably needed.
- [ ] **SpeciesNet weights license** on the Kaggle model page (the code is Apache-2.0; the weights weren't confirmed).
- [ ] **SpeciesNet with our own detections.** By default it runs MegaDetector v5 (AGPL). Confirm we can pass
      MDV6-MIT boxes and run only the classifier.
- [ ] **UAE species coverage:** does SpeciesNet know Arabian oryx, sand/Arabian gazelle, Arabian tahr, sand cat?
      If not, use BioCLIP 2 with the list in `data/processed/species_reference.csv`.
- [ ] **CPU speed** on our laptops: 600 images must finish well before the pitch; cache the results.
- [ ] Output must match [`code/CONTRACT.md`](../code/CONTRACT.md) exactly, otherwise the app breaks.
- [ ] Compute **accuracy against `ground_truth`** for one honest number in the pitch.

## Claims we make in the pitch: verify or soften

- [ ] **"Saves ≈X hours per 100k images"** uses an assumed 8 s per image of manual review. Call it an estimate,
      or find a published figure.
- [ ] **UAE law points** (PDPL, cloud policy) come from law-firm summaries, not the statute texts. Say "designed for compliance".
- [ ] **Bayanat terms of use**: check the license on the portal before saying "open data".
- [ ] **Credit the sources** on a slide: LILA BC (CDLA-Permissive), GBIF.org, MOCCAE via Bayanat.
- [ ] **People blurring** can't be shown with our data (LILA removed human photos). Test with our own photo, or don't demo it.

## Data quirks we know about

- Labels apply to the whole burst, so some frames tagged "caracal" don't show it.
- The date printed on the photos is 2017/18; our tables shift years to 2023–25. Don't zoom in on it.
- Some camera clocks are wrong (a daylight photo stamped 8:32 PM).
- Timestamps are local South African time but exported with `+04:00` (UAE). Fine for the demo; fix for real data.
- MOCCAE's coordinates file has 45 rows; one has no usable coordinates, so 44 reserves are loaded.
- Bayanat's "Long-Range Nature Reserves" dataset contains the same files as "Protected Lands Coordinates". Cite only one.
- GBIF includes pets, livestock and zoo animals; they're flagged in `domestic_or_captive`.

## Repo / teamwork

- [ ] Add your friend as a **collaborator** on GitHub (Settings → Collaborators).
- [ ] The repo was renamed on GitHub. Update the remote:
      `git remote set-url origin https://github.com/abdalla980/KAMouflageVision-UAE-HACKATHON26.git`
- [ ] **Pin package versions** in `requirements.txt` once everything works (currently `>=`), so a fresh install
      on the demo laptop can't break. Known-good: streamlit 1.66.1, pandas 3.1.0, plotly 7.1.0, pydeck 0.9.3.
- [ ] The repo is ~290 MB because of the photos; the first clone takes a while.
- [ ] `fetch_bayanat.py` copies the website's own requests; if Bayanat changes its site, it may break.
