"""Generate DEMO AI results so the app can be built before the real AI pipeline is ready.

Writes data/results/predictions.csv in the format defined in code/CONTRACT.md. Values are derived from the
ground-truth labels with realistic noise: confidence is lower at night, ~12-25% of bursts are misclassified
and go to review, some frames inside an animal burst are empty (labels are burst-level), and a few empty
bursts are false triggers. No bounding boxes are produced: drawing invented boxes would be misleading.
The real pipeline (code/ai_pipeline/) overwrites this file with genuine model output.

    python code/app/mock_predictions.py
"""

import random
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import PREDICTIONS_CSV, PROCESSED_DIR, label_name, primary_label  # noqa: E402

AUTO_ACCEPT = 0.90


def main(seed=7):
    rng = random.Random(seed)
    images = pd.read_csv(PROCESSED_DIR / "images.csv")
    animal_names = sorted({label_name(primary_label(g)) for g in images["ground_truth"]} - {"empty"})

    rows = []
    for seq_id, burst in images.sort_values("frame_num").groupby("seq_id", sort=False):
        first = burst.iloc[0]
        truth = primary_label(first["ground_truth"])
        night = str(first["is_night"]) == "True"

        if truth == "empty":
            false_trigger = rng.random() < 0.08
            species, seq_conf = (rng.choice(animal_names), rng.uniform(0.30, 0.55)) if false_trigger else ("", 0.0)
            status = "needs_review" if false_trigger else "empty"
            correct_name = None
        else:
            correct_name = label_name(truth)
            p_correct = 0.75 if night else 0.88
            seq_conf = min(rng.gauss(0.88 if night else 0.95, 0.06), 0.985)
            if rng.random() < p_correct:
                species = correct_name
            else:
                species = rng.choice([n for n in animal_names if n != correct_name])
                seq_conf = min(seq_conf, rng.uniform(0.45, 0.85))
            status = "auto_accepted" if seq_conf >= AUTO_ACCEPT else "needs_review"

        others = [n for n in animal_names if n not in (species, correct_name)]
        cands = [species] + ([correct_name] if correct_name and correct_name != species else []) + rng.sample(others, 2)
        cands = list(dict.fromkeys(c for c in cands if c))[:3]
        # The AI's pick is always the top candidate; the others share what is left, below the top score.
        rest = 1 - seq_conf
        cand_confs = [seq_conf] + [min(rest * 0.6, seq_conf * 0.8), min(rest * 0.25, seq_conf * 0.4)][: len(cands) - 1]
        top3 = "|".join(f"{c}:{p:.2f}" for c, p in zip(cands, cand_confs))

        has_animal = [truth != "empty" and rng.random() < 0.75 for _ in range(len(burst))]
        if truth != "empty" and not any(has_animal):
            has_animal[rng.randrange(len(burst))] = True

        for (_, img), animal in zip(burst.iterrows(), has_animal):
            frame_conf = max(min(seq_conf + rng.uniform(-0.12, 0.05), 0.99), 0.2) if animal else 0.0
            rows.append({
                "image_id": img["image_id"],
                "seq_id": seq_id,
                "detection": "animal" if animal or (status == "needs_review" and truth == "empty") else "empty",
                "det_conf": round(frame_conf if animal else rng.uniform(0.01, 0.15), 3),
                "bbox": "",
                "species": species if animal or truth == "empty" else "",
                "species_conf": round(frame_conf, 3),
                "top3": top3 if species else "",
                "seq_species": species,
                "seq_conf": round(seq_conf, 3),
                "status": status,
                "enhanced_path": "",
                "model_version": "DEMO-mock-0.1",
            })

    PREDICTIONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame(rows)
    out.to_csv(PREDICTIONS_CSV, index=False)
    seqs = out.groupby("seq_id").first()
    print(f"Wrote {len(out)} DEMO predictions -> {PREDICTIONS_CSV}")
    print(seqs["status"].value_counts().to_string())


if __name__ == "__main__":
    main()
