# Soil screening assessment

`soil-observations-v1` is an AgroBot questionnaire screening rubric, not a
scientifically calibrated soil-health index, laboratory assessment, crop yield
prediction or measurement of overall farm performance. The dashboard farm score
and soil status summarise the same soil screening assessment. The UI explicitly
labels it estimated and exposes its component scores.

All six answers are required. Missing, unknown or malformed answers produce no
score and a list of missing fields. Boolean `false` is a valid answer. The score
is the equally weighted mean of the following points, rounded to one decimal:

| Indicator | Answer → points out of 10 |
| --- | --- |
| Soil top layer | Dark/crumbly → 10; mixed → 5; hard/compact → 0 |
| Water retention | Moderate → 10; retains long or drains quickly → 5 |
| Yellowing or slow growth | No → 10; yes → 0 |
| Organic matter use | Yes → 10; no → 0 |
| Crop residue management | Leave or compost → 10; remove → 5; burn → 0 |
| Earthworms observed | Yes → 10; no → 0 |

These are product screening weights, not agronomic thresholds. Observations can
depend on season, soil type and crop; absence of earthworms or yellowing alone
does not diagnose soil health. Scores at least 7.5 show favourable indicators,
6–7.4 need attention, and lower scores need review. Laboratory NPK/pH and inferred
nutrient defaults are excluded from this rubric: a general nutrient-health score
would require verified sampling methods, units and crop-specific reference
ranges. Those inputs remain available to the crop recommendation pipeline.

The authorised farm assessment endpoint calculates directly from saved answers,
so existing questionnaires work immediately, even if crop generation or weather
is unavailable. Analytics uses the same current assessment. New recommendations
store the score and versioned component snapshot for historical trends. Old
NULL scores are not backdated using today's answers. No database migration or
external model/API is needed for assessment.
