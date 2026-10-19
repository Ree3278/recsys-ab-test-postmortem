# PLAN

## Phase 1 — 数据与统计内核 (Week 1)
- [x] uv 项目骨架、依赖、pytest/ruff
- [x] `simulate.py`：用户、每日 GMV、SKU 曝光；新鲜感衰减、分群效应、SRM 注入
- [x] `stats.py`：SRM、Welch、CUPED、样本量/MDE、Gini/Lorenz、多重比较校正
- [x] `analysis.py`：整体 / 分群(BH 校正) / 逐日累积 / 单日 / 早晚窗口 / SRM / 基尼 / 样本量 → `reports/results.json`
- [x] 验证 `validate.py`：1000 次模拟，A/A 假阳性 ≈5.5%，SRM 误报 0.2%，CI 覆盖率 94–95%，CUPED 使 CI 缩短约 15–19%
- [ ] 逐日累积分析：固定 14 天决策 + 说明 peeking；可选 alpha spending

## Phase 2 — 4 张图 (Week 2)
- [x] 1. 累积 Lift + 逐日 Lift（含 95% CI，早/晚窗口标注）→ `site/charts/novelty.html`
- [x] 2. 森林图（分群 lift，BH 校正后区分显著性）→ `heterogeneity.html`
- [x] 3. Lorenz 曲线 + Gini 对比 → `long_tail.html`
- [x] 4. SRM 诊断（正常 vs 注入，按设备定位，含容许区间）→ `srm.html`
- [x] Plotly 本地打包（无 CDN 依赖）、明暗主题、数据表视图、"SIMULATED DATA" 标签
- [ ] SRM 漏斗定位（入口分流 / 埋点丢失）：需要在生成器里加漏斗阶段，暂缺

## Phase 3 — 网站与文档 (Week 3)
- [x] `site/index.html`：4 图 + 结论 + 方法 + 验证表 + 局限性（`uv run python -m ab_rec_eval.site` 生成）
- [x] 明暗主题切换、手机宽度适配（iframe 自动高度）
- [x] GitHub Actions：CI（ruff + pytest）与 Pages 部署（`.github/workflows/`）
- [x] README：模拟数据声明、方法、局限性
- [ ] 在 GitHub 建仓库、推送、开启 Pages（Settings → Pages → Source: GitHub Actions），把仓库地址填进 `site.py` 的 `REPO_URL` 后重新生成
- [ ] （可选）SRM 区域加滑块：预计算多组丢失比例，演示告警阈值
- 可选：Tableau Public 复刻 1–2 张图

## 约定
- 所有输出标注 "simulated"
- 简历不写业务提升百分比
