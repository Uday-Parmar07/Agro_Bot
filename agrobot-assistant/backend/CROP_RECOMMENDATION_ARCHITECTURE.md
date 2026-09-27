# Safe hybrid crop recommendations

The recommendation pipeline has two candidate lanes. The XGBoost lane derives
its crop slugs from the serialized `LabelEncoder.classes_`; the catalogue lane
returns only active profiles marked `knowledge_profile_complete` with a named
source and at least one verified agronomic constraint. Both lanes are merged by
canonical slug and pass deterministic validation before ranking.

The checked-in model currently contains 22 crop classes. The versioned
catalogue intentionally contains no knowledge-only crops because this repository
does not include a verified agronomic profile source for additional crops. Its
model entries are deliberately marked incomplete. Import sourced profiles before
enabling knowledge-only recommendations.

## Ranking heuristic

`crop-ranking-v2` is a product heuristic, not a scientifically validated score:

| Component | Weight |
| --- | ---: |
| Agronomic/model signal | 0.45 |
| Season | 0.10 |
| Region | 0.10 |
| Soil | 0.10 |
| Water | 0.10 |
| Climate | 0.10 |
| Farmer preferences | 0.05 |

Only applicable, verified components are included in the denominator. Input
quality reduces the score (`high=1.0`, `medium=0.85`, `low=0.70`), each warning
applies a small capped product penalty, and out-of-distribution model input has
an additional factor. These values should be evaluated with agronomists and
field outcomes before being treated as more than ordering heuristics.

The model low-confidence threshold defaults to `0.15` and is configurable with
`CROP_MODEL_LOW_CONFIDENCE_THRESHOLD`. It is provisional; XGBoost probabilities
have not been calibrated as real-world success probabilities.

Final inclusion is applied after validation and scoring. Scores below
`MIN_PRELIMINARY_SCORE` (default `25`) are rejected; scores from that threshold
up to `MIN_RECOMMENDATION_SCORE` (default `50`) are preliminary. A normal
recommendation also requires non-low input quality and at least
`MIN_VERIFIED_CHECKS_FOR_RECOMMENDATION` (default `4`) verified catalogue checks.
These are provisional product-safety thresholds, not agronomic findings. The API
returns fewer than three crops rather than padding the result.

## Catalogue import safety

Run this check after replacing or retraining the model:

```bash
python scripts/sync_crop_catalog_model_classes.py
```

An explicit `--write` synchronizes model-coverage flags and missing model entries
without generating agronomic constraints. Verified knowledge profiles must be
added separately with provenance.

## Weather and climate

Mock weather is disabled by default. `ENABLE_MOCK_WEATHER=true` enables it for
development and labels it `mock_fallback`; it always lowers data quality. Current
weather supplies current temperature/humidity only. Farmer-provided rainfall is
stored explicitly as annual millimetres and kept separate because the checked-in
training dataset documents neither a rainfall unit nor a time period. It is never
converted, passed into XGBoost, or compared with the model rainfall range. With
`ENABLE_PRELIMINARY_MODEL_WITH_MISSING_RAINFALL=true`, XGBoost's native missing-
value path can generate explicitly preliminary matches from the other six
features. No rainfall default is inserted, and this mode can never produce a
normal recommendation. When disabled, the model lane returns
`insufficient_compatible_input`.

## Explanation boundary

Groq receives only the final validated crop slugs, their sources, matched
conditions, warnings, data quality, and catalogue facts. It cannot change the
ranking. Unauthorized or duplicate slugs and malformed JSON cause deterministic
template fallback while preserving the ranked crops. Harmless output ordering is
ignored, missing allowed explanations are filled individually, and unsafe numeric
fields are replaced individually before the server restores deterministic crop
order.
