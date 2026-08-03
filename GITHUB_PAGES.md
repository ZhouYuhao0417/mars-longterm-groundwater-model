# GitHub Pages deployment

The repository contains a Pages workflow at `.github/workflows/pages.yml`. After the first push:

1. open the repository's **Settings → Pages**;
2. under **Build and deployment**, choose **GitHub Actions**;
3. run the `Deploy bilingual interactive model to Pages` workflow, or push to the default branch;
4. use the URL reported by the deployment job.

`index.html` is the English default page and `index_zh.html` is the Chinese page. Both are self-contained and require no build step or server-side code.

Before an archival release, replace the provisional author entry in `CITATION.cff`, add the repository URL and DOI, and select an explicit licence after checking the terms of third-party planetary products.
