# GitHub Pages deployment

The repository contains a Pages workflow at `.github/workflows/pages.yml`. After pushing the accepted release:

1. Open the repository's **Settings > Pages**.
2. Under **Build and deployment**, choose **GitHub Actions**.
3. Run `Deploy bilingual interactive model to Pages`, or push to the default branch.
4. Use the URL reported by the deployment job.

`index.html` is the English parameter explorer and `index_zh.html` is the Chinese parameter explorer. The quality-gated manuscript results are available at `accepted_runs.html?lang=en` and `accepted_runs.html?lang=zh`. The accepted-runs viewer requests static files from `data/accepted-v2/`; no server-side code is required.

Before publication, verify that:

- the accepted viewer loads only `low_f64_v2` and `medium_f64_v2`;
- maximum depth, final depth, arrival year, and wet duration can all be selected;
- the historical incomplete medium run remains under `data/excluded/` and is never loaded by the accepted page;
- the old high run is labeled legacy exploratory and is not presented as an accepted v2 result;
- the parameter explorer is described as a volume-mapped communication layer rather than an exact simulation viewer.

Before an archival release, replace any provisional author entry in `CITATION.cff`, add the repository URL and DOI, and select an explicit licence after checking the terms of third-party planetary products.
