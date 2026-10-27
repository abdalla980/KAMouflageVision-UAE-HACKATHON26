# AI pipeline → app contract

The AI pipeline writes `data/results/predictions.csv`, one row per image. The app reads only this file, so
either side can change its internals freely. `code/app/mock_predictions.py` writes the same format with demo values.

| Column | Example | Notes |
|---|---|---|
| `image_id` | `KAR_S1/B03/B03_R1/KAR_S1_B03_R1_IMAG0949` | same as `data/processed/images.csv` |
| `seq_id` | `KAR_S1#B03#1#12` | burst ID |
| `detection` | `animal` | `animal`, `person`, `vehicle` or `empty` (top detection in this frame) |
| `det_conf` | `0.93` | detector confidence, 0–1 |
| `bbox` | `0.41,0.52,0.12,0.09` | x, y, w, h as fractions of the image; empty if none |
| `species` | `Caracal` | classifier output for this frame |
| `species_conf` | `0.88` | 0–1 |
| `top3` | `Caracal:0.61\|Cape Fox:0.24\|Hare:0.08` | best first |
| `seq_species` | `Caracal` | decision for the whole burst |
| `seq_conf` | `0.88` | 0–1 |
| `status` | `needs_review` | `empty`, `auto_accepted` (seq_conf ≥ 0.90), `needs_review` or `blurred_person` |
| `enhanced_path` | | optional; the app enhances on the fly if empty |
| `model_version` | `MDV6-mit-yolov9-c + speciesnet-4.0.1a` | written into the audit trail |

The app writes expert decisions to `data/results/reviews.csv`:
`seq_id, decision (confirm | correct | not_animal | skipped), final_species, reviewer, timestamp`.

For live uploads the app calls `code/ai_pipeline/pipeline.py: run(paths, camera_id) -> DataFrame` with the
columns above, if that function exists.
