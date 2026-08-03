# 火星长期地下水出流模拟

[English README](README.md) · [英文交互页](index.html) · [中文交互页](index_zh.html) · [方法](METHODS_ZH.md) · [数据来源](DATA_SOURCES_ZH.md) · [数据字典](DATA_DICTIONARY.md)

这是原二维有限体积扩散波水文模型的长期地下水出流扩展和双语科研发布包。二维空间求解器没有替换；DEM 控制蓄水、最低天然鞍部溢流、下游传播和开放边界外排。升级仅涉及长期过程线、解析水量积分和经过验证的多年计算加速。

模型不推测、不标绘两条沟槽。研究者指定的原始点位 `75.937180°E, 18.136689°N` 作为两条概念沟槽合计出流的等效源。任一时刻的总流量 `Q(t)` 只施加一次，不按源网格数量重复。

## 双语交互前端

- [index.html](index.html)：英文默认页，供英文期刊和 GitHub Pages 使用；
- [index_zh.html](index_zh.html)：中文完整交互页；
- 两个页面都可一键切换语言；
- 页面完全自包含，不请求外部字体、地图服务或脚本；
- 支持论文截图模式、PNG 导出和参数 JSON 下载。

交互页用于方案展示和选参，不能代替 `data/completed-runs/` 中的精确二维结果数组。

## 一键验证

参考环境为 Python 3.12：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts\validate_repository.py
```

运行低情景：

```powershell
python model\run_exact_longterm.py --scenario low --fresh
```

高情景计算量较大，因此仓库已经包含完成的低/高情景摘要、地图、逐网格到达时间、当前/最大水深、持续淹没时长和数值审计。

## 情景状态

| 情景 | 过程线 | 参数 | T | C | 论文状态 |
|---|---|---|---:|---:|---|
| 低 | 恒定基流 | `Qb=100 m³/s` | 10 年 | 0.4 | 完成，可用 |
| 中 | 指数衰减 | `Qb=300`、`Q0=3000 m³/s`、`tau=3 年` | 20 年 | 0.7 | 未完成，禁止空间定量引用 |
| 高 | 分阶段脉冲 | `Qb=500`、`Q0=5000 m³/s` | 30 年 | 1.0 | 完成，可用 |

只有 `complete=true` 且 `paper_usable=true` 的结果进入论文定量图。详见 [EXCLUSIONS.md](EXCLUSIONS.md)。

## 使用边界

本模型检验给定边界条件下的水文可行性，不包含侵蚀、泥沙输运、冻融、三维含水层压力扩散和沟槽几何反演。`C` 是沿程有效保留系数，不是降雨—径流系数。

引用格式见 [CITATION.cff](CITATION.cff)。源代码 © 2026 Zhou Yuhao，采用 [MIT 许可证](LICENSE)；作者拥有权利的原创文档、图注、界面设计和图件编排采用 [CC BY 4.0](LICENSES/CC-BY-4.0.txt)。HRSC、CTX、CRISM 等第三方行星数据仍遵守原始来源条款，见 [DATA_SOURCES_ZH.md](DATA_SOURCES_ZH.md)。
