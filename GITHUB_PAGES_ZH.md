# GitHub Pages 发布

仓库已经包含 `.github/workflows/pages.yml`。推送本次验收版本后：

1. 打开仓库的 **Settings > Pages**。
2. 在 **Build and deployment** 中选择 **GitHub Actions**。
3. 运行 `Deploy bilingual interactive model to Pages`，或推送到默认分支触发部署。
4. 使用部署任务给出的公开网址。

`index.html` 是英文参数探索器，`index_zh.html` 是中文参数探索器。论文采用的质量门控结果位于 `accepted_runs.html?lang=en` 和 `accepted_runs.html?lang=zh`。验收结果页会读取 `data/accepted-v2/` 中的静态数组和清单，不需要服务器端程序。

公开前必须确认：

- 验收结果页只加载 `low_f64_v2` 和 `medium_f64_v2`；
- 最大水深、终态水深、到达年份和湿润时长四个图层均可切换；
- 历史未完成中情景仍保存在 `data/excluded/`，且不会被验收结果页加载；
- 旧高情景仅标为旧版探索结果，不与 v2 低、中情景并列；
- 参数探索器明确标为体积映射展示层，而不是精确模拟结果页。

归档发布前，还需核对 `CITATION.cff` 的作者信息，补入仓库网址和 DOI，并根据第三方行星数据产品的许可条款选择明确的软件与数据许可证。
