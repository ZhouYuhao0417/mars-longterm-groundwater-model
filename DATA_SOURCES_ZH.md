# 数据来源与溯源

[English data provenance](DATA_SOURCES.md)

## 发布原则

仓库上传复现模型所需的紧凑派生输入、完成运行数组和图件，不重复分发完整的第三方行星数据档案。原始产品应从官方来源下载，并继续遵守各自的署名和使用条款。

## 地形输入

数值模型的标准输入是 `data/conservative-model.npz`。现存预处理代码和工作区记录表明，100 m 融合地形来自：

1. HRSC HMC-13E 区域产品中的 50 m、相对火星 areoid 的 DTM 子区；
2. USGS 的 `M20_JezeroCrater_CTXDEM_20m.tif`，在重叠区校正垂直偏差并以四个网格渐变融合。

100 m 地形按每个 4 × 4 窗口的第 35 百分位数生成 400 m 水动力网格，另保留 200 m 展示网格。官方入口：

- DLR HRSC HMC-30：<https://hrscteam.dlr.de/public/data/regionaldtms.php>
- DLR HRSC MC13E：<https://hrscteam.dlr.de/public/data/HMC30/quads.php?quad=mc13e>
- NASA PDS HRSC：<https://pds-geosciences.wustl.edu/missions/mars_express/hrsc.htm>
- USGS Mars 2020 CTX DEM：<https://astrogeology.usgs.gov/search/map/mars_2020_science_investigation_ctx_dem_mosaic>

现存 HTTP 分段文件没有保留具体 HRSC 源瓦片文件名，这是上游溯源缺口。在补齐以前，不能宣称从原始产品到模型输入的逐位复现；从仓库内 `conservative-model.npz` 开始的模型复现是完整的，并由 SHA-256 和原二维网格回归测试约束。

## 影像底图

`data/derived/ctx-hrsc-extended-basemap.jpg` 只是可视化层：Global CTX Mosaic V01 子区与融合 DEM 阴影组合。水动力方程不读取该 JPG。

- Global CTX Mosaic V01：<https://murray-lab.caltech.edu/CTX/V01/SceneView/intro_c.html>
- Dickson et al. (2024)：<https://doi.org/10.1029/2024EA003555>

## CRISM 点位

`data/crism_selected_sites.csv` 的 C1、P1、A1 来自 HRL0001FC92 的 MTRDR 产品 `HRL0001FC92_07_IF182J_MTR3` 和 `HRL0001FC92_07_SR182J_MTR3`。选择流程另存于 <https://github.com/ZhouYuhao0417/CRISM-HRL0001FC92-reproducible>。

- NASA PDS CRISM：<https://pds-geosciences.wustl.edu/missions/mro/crism.htm>
- MTRDR DOI：<https://doi.org/10.17189/1519470>
- MICA：<https://crismtypespectra.rsl.wustl.edu/>

所有发布数据的大小、SHA-256、用途和论文状态见 `data/data_manifest.csv`，可用 `python scripts/build_manifest.py` 重建。
