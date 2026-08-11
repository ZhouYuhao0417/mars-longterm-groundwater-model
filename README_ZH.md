# 火星长期地下水出流模拟

[English README](README.md) · [已验收低/中情景](accepted_runs.html?lang=zh) · [Accepted low/medium viewer](accepted_runs.html) · [参数探索器](index_zh.html) · [英文参数探索器](index.html) · [方法](METHODS_ZH.md) · [数据来源](DATA_SOURCES_ZH.md) · [数据字典](DATA_DICTIONARY.md)

这是原二维有限体积扩散波水文模型的长期地下水出流扩展和双语科研发布包。二维空间求解器没有替换；DEM 控制蓄水、最低天然鞍部溢流、下游传播和开放边界外排。升级仅涉及长期过程线、解析水量积分和经过验证的多年计算加速。

规定点位 `75.937180°E, 18.136689°N` 是源坑蓄满后在候选低坑缘出口施加的一次坑侧等效输入。任一时刻的总流量 `Q(t)` 只施加一次，不按源网格数量重复。它不代表沿东北—西南向 Nili Fossae 沟槽的地表输水，也不预设水能沿该沟槽到达 Jezero 西三角洲流域上游。

## 双语交互前端

- [accepted_runs.html?lang=zh](accepted_runs.html?lang=zh)：论文使用的门控通过低情景和中等情景精确数组；
- [accepted_runs.html](accepted_runs.html)：同一结果的英文入口；
- [index_zh.html](index_zh.html) 与 [index.html](index.html)：可调参数的体积映射探索器；
- 已验收页面可切换最大水深、终态水深、到达年份和湿润时长，显示闭合水账、HW1–HW3、阈值与 PNG 导出；
- 参数探索器保留方案沟通用途，其中高情景明确标为旧版探索。

已验收页面读取 `data/accepted-v2/` 中带哈希的浏览器显示副本，权威定量记录仍是归档 `.npy` 数组和摘要。可调参数探索器不能替代这些精确结果。

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

仓库已经包含已验收低情景和中等情景的浏览器资产，因此无需重跑也能检查论文状态。旧高情景不是同版本、全显式 v2 结果，只保留为探索性敏感性材料。

## 情景状态

| 情景 | 过程线 | 参数 | T | C | 论文状态 |
|---|---|---|---:|---:|---|
| 低 | 恒定基流 | `Qb=100 m³/s` | 10 年 | 0.4 | v2 已验收；解析蓄水、未溢流 |
| 中 | 指数衰减 | `Qb=300`、`Q0=3000 m³/s`、`tau=3 年` | 20 年 | 0.7 | v2 已验收；2.660227 年预填充＋17.339773 年显式路由 |
| 高 | 分阶段脉冲 | `Qb=500`、`Q0=5000 m³/s` | 30 年 | 1.0 | 仅旧版探索；不是 v2 论文结果 |

只有当前 v2 低情景和中情景同时满足 `complete=true`、`paper_usable=true`、全部论文门控、水账闭合且无下游跳时，才进入已验收页面。详见 [EXCLUSIONS.md](EXCLUSIONS.md)。

## 使用边界

本模型检验给定边界条件下的水文可行性，不包含侵蚀、泥沙输运、冻融、三维含水层压力扩散和沟槽几何反演。`C` 是沿程有效保留系数，不是降雨—径流系数。

引用格式见 [CITATION.cff](CITATION.cff)。源代码 © 2026 Zhou Yuhao，采用 [MIT 许可证](LICENSE)；作者拥有权利的原创文档、图注、界面设计和图件编排采用 [CC BY 4.0](LICENSES/CC-BY-4.0.txt)。HRSC、CTX、CRISM 等第三方行星数据仍遵守原始来源条款，见 [DATA_SOURCES_ZH.md](DATA_SOURCES_ZH.md)。
