# Data sources and provenance

[中文数据来源](DATA_SOURCES_ZH.md)

## Distribution policy

This repository includes compact derived inputs needed to rerun the model and the numerical outputs used in the supplied figures. It does not republish complete third-party planetary archives. Original products should be obtained from the authoritative providers below and remain subject to their terms and attribution requirements.

## Topography

The canonical computational input is `data/conservative-model.npz`. Surviving preprocessing code and workspace records describe a 100 m fused terrain surface derived from:

1. an areoid-referenced 50 m HRSC HMC-13E regional DTM subset; and
2. the USGS `M20_JezeroCrater_CTXDEM_20m.tif` local CTX DEM, vertically bias-corrected in the overlap and feathered across a four-cell seam.

The fused 100 m surface was reduced to the 400 m hydrodynamic grid using the 35th percentile in each 4 × 4 block. A 200 m display grid was retained separately. Authoritative discovery pages:

- DLR HRSC HMC-30 regional products: <https://hrscteam.dlr.de/public/data/regionaldtms.php>
- DLR HRSC MC13E product listing: <https://hrscteam.dlr.de/public/data/HMC30/quads.php?quad=mc13e>
- NASA PDS HRSC holdings: <https://pds-geosciences.wustl.edu/missions/mars_express/hrsc.htm>
- USGS Mars 2020 Science Investigation CTX DEM Mosaic: <https://astrogeology.usgs.gov/search/map/mars_2020_science_investigation_ctx_dem_mosaic>

The exact HRSC source tile filename was not retained with the surviving HTTP range fragments. This is an upstream provenance gap and must be resolved before claiming raw-product-to-model bitwise reproduction. Reproduction from the archived derived input `conservative-model.npz` is complete and is guarded by its SHA-256 checksum and original-grid regression tests.

## Image basemap

`data/derived/ctx-hrsc-extended-basemap.jpg` is a non-quantitative visualization layer: a Global CTX Mosaic V01 subset is combined with hillshade derived from the fused elevation surface. It is not sampled by the hydrodynamic equations.

- Global CTX Mosaic V01 viewer: <https://murray-lab.caltech.edu/CTX/V01/SceneView/intro_c.html>
- Global CTX Mosaic V01 files: <https://murray-lab.caltech.edu/CTX/V01/tiles/>
- Dickson et al. (2024), *Earth and Space Science*: <https://doi.org/10.1029/2024EA003555>

## CRISM sites

`data/crism_selected_sites.csv` contains three investigator-selected sites from CRISM observation HRL0001FC92:

- `HRL0001FC92_07_IF182J_MTR3`
- `HRL0001FC92_07_SR182J_MTR3`

The products belong to the NASA PDS CRISM Map-Projected Targeted Reduced Data Record bundle `mrocr_4001`. Mineral reference spectra use the CRISM MICA library (`mrocr_8001`). The selection workflow is archived separately at <https://github.com/ZhouYuhao0417/CRISM-HRL0001FC92-reproducible>.

- NASA PDS CRISM data: <https://pds-geosciences.wustl.edu/missions/mro/crism.htm>
- CRISM MTRDR DOI: <https://doi.org/10.17189/1519470>
- MICA library: <https://crismtypespectra.rsl.wustl.edu/>
- Summary-parameter reference: <https://doi.org/10.1002/2014JE004627>

## Repository artifacts

`data/data_manifest.csv` records byte sizes, SHA-256 checksums, roles and publication status for every distributed data file. Regenerate it with:

```bash
python scripts/build_manifest.py
```

The preprocessing history above is evidence-based but does not justify redistributing the full HRSC, CTX or CRISM archives. Cite the original data providers and the associated journal papers in the manuscript.
