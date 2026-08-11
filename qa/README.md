# Accepted-viewer browser QA

`accepted_viewer_local.png` is the full-page Microsoft Edge headless capture from the local static server after loading the accepted medium maximum-depth array and switching to Chinese.

Browser checks completed on 2026-08-11:

- the manifest and all requested static arrays returned HTTP 200;
- no console errors, page errors, or failed HTTP responses occurred;
- medium showed 20 yr, 2.660227 yr source fill, float64 / 600 s / no skip, and exact HW1-HW3 cell depths of 51.720, 3.182, and 0.132 m;
- maximum, final, arrival, and duration layers all loaded;
- low showed analytical no-spill status and zero HW1-HW3 depth;
- Chinese/English switching updated text, URL state, and source-boundary wording;
- the parameter explorer exposed a direct link to the accepted low/medium viewer.

The screenshot is interface QA, not a quantitative source. Quantitative values remain bound to the v2 summaries and arrays through `data/accepted-v2/accepted_v2_manifest.json`.
