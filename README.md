# stock-dashboard-skill

> 一个 WorkBuddy / CodeBuddy Skill：把自选标的、持仓、财报与价格整理成**本地静态看板**。
>
> *A local, static, reproducible portfolio dashboard skill. No investment advice, no trading, no public hosting.*

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

## 它能做什么

- 录入关注标的与持仓（截图可选、可跳过），或从**完全虚构的演示数据**一键看到完整样式
- 生成单文件自包含的 `dashboard/index.html`：账户概览、持仓卡、可接受价格带、估值偏贵程度、财报日历、分红、事件记录
- 为每只标的生成 `dashboard/stocks/<主代码>.html`：近 8 季财报柱状图（真实金额纵轴 + 柱端数值常显）、报告期切换、同业横比、股价反应校验、公告溯源
- 看板上的「+ 添加标的」「更新持仓」入口生成可复制指令，粘贴回对话由 Agent 执行完整链路
- 附一套**踩坑清单与方法论**：数据源降级、双重币种口径、A/H 报告期对齐、调度时区陷阱、禁止口径伪装等 28 条实测规则

## 它不做什么

- ❌ 不提供投资建议、不执行交易、不代下单
- ❌ 不发布公网、不默认创建定时任务、不默认写平台原生提醒
- ❌ 不捆绑任何真实行情、财报或持仓数据

## 30 秒体验（零依赖、零网络）

```bash
git clone https://github.com/ginadochen/stock-dashboard-skill.git
cd stock-dashboard-skill
python scripts/instance.py --root ../demo-instance --mode demo
python scripts/build_dashboard.py    --root ../demo-instance
python scripts/build_stock_pages.py --root ../demo-instance
```

实例目录必须在 skill 包**之外**（脚本会拒绝写入能力包内部；仓库内的 `.sandbox/` 是 gitignore 的本地回归专用区）。

打开 `../demo-instance/dashboard/index.html`。或者**直接双击 `example/index.html`**，那是已经生成好的演示成品。

> 演示数据全部虚构，标的仅借用公开的证券代码，价格、财报、持仓金额均为编造，与真实行情无关。

## 作为 Skill 使用

把本目录安装到 WorkBuddy / CodeBuddy 的 skills 目录后，对 Agent 说：

> 帮我做一个股票看板

Agent 会按 `SKILL.md` 的 8 步流程走：确定实例根目录 → 录入（可跳过）→ 选模式 → 取数 → 构建 → 变更 → 自动化（需授权）→ 自检。

**关键约定**：

| 项 | 说明 |
|---|---|
| 实例根目录 | 由用户指定，`--root` 显式传入；skill 目录只读 |
| `demo` | 内置虚构快照，零连接器可跑，页面常驻「演示数据」横幅 |
| `live` | 需自备行情/公告连接器与合规授权；切换时强制清空演示数据 |
| 产物 | 只落在实例目录，见 `assets/templates/agent.md` 的目录纪律 |
| 敏感信息 | 持仓/成本只写 `config/`，不进日志、不进通知、不进仓库 |

## 目录结构

```
stock-dashboard-skill/
├─ SKILL.md                 工作流与授权纪律
├─ scripts/                 参数化脚本（--root，不直连 MCP）
│   ├─ instance.py          从模板实例化 demo / live 实例
│   ├─ build_dashboard.py   构建首页
│   ├─ build_stock_pages.py 构建个股财报详情页
│   ├─ check_sources.py     数据源健康自检
│   ├─ record_nav.py        每日净值埋点
│   ├─ privacy_check.py     仓库隐私扫描
│   └─ layout_check.py      产物目录合规检查
├─ references/              口径 / 方法论 / 调度 / 踩坑 / 免责
├─ assets/templates/        agent.md 模板 + *.yaml.example
├─ assets/demo/             虚构行情财报快照
├─ example/                 demo-offline 生成的成品看板
├─ docs/PRIVACY-AUDIT.md    发布前隐私验收
└─ .github/workflows/       CI：隐私扫描 + 离线回归
```

## 隐私设计

- `.gitignore` 采用**默认拒绝**（`*` + `!` 白名单），新文件不会意外进入仓库
- `privacy_check.py` 扫描金额、姓名、聊天 ID、绝对路径、token、自动化 ID、邮箱/手机/IP
- CI 与 pre-commit 双跑；发布前需独立 clone 复扫
- 详见 [PRIVACY.md](PRIVACY.md) 与 [SECURITY.md](SECURITY.md)

## 数据来源与合规

`live` 模式需要用户自备数据连接器。本项目**不打包、不二次分发任何供应商数据**。部分数据供应商的许可条款禁止第三方工具提取或对外展示，请在启用 live 模式前自行确认合规义务；`demo` 模式不涉及此问题。

## 免责声明

本项目是个人持仓整理与信息可视化工具，**不提供投资顾问服务**。所有价位、区间、分位与结论均为基于公开数据的量化参考，不构成投资建议。市场有风险，投资需谨慎。完整文本见 `references/disclaimer.md`。

## License

Apache-2.0 © 2026 ginadochen — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
