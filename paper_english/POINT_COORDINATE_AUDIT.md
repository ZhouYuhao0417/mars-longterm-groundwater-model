# Point-coordinate audit

The earlier static figure used 200 m display-grid coordinates directly on a 1368×1100 image and therefore placed every marker at approximately half of its correct image coordinate. The corrected figures project the 400 m model-grid centres to the 4× exact-run preview:

\[
x_{\mathrm{preview}}=4\,\mathrm{col}_{400}+2,\qquad
y_{\mathrm{preview}}=4\,\mathrm{row}_{400}+2.
\]

| Marker | Longitude | Latitude | 400 m row | 400 m column | Preview x | Preview y | Source |
|---|---:|---:|---:|---:|---:|---:|---|
| Equivalent source | 75.937180°E | 18.136689°N | 105 | 64 | 258 | 422 | source-coordinate transform |
| Natural spillway | — | — | 103 | 84 | 338 | 414 | `conservative-model.npz` |
| C1 Mg-carbonate | 76.632167°E | 17.842999°N | 149 | 167 | 670 | 598 | completed-run summary |
| P1 Fe/Mg phyllosilicate | 76.636570°E | 17.807759°N | 154 | 168 | 674 | 618 | completed-run summary |
| A1 tentative Al-OH | 76.545992°E | 17.889783°N | 142 | 155 | 622 | 570 | completed-run summary |

The northeast–southwest trough remains unmarked as a source path because the model does not resolve surface transport along it; the plotted source is a separate equivalent crater-side boundary at the candidate low-rim outlet.
