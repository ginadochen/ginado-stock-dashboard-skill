# Changelog

All notable changes to this project are documented here. Dates use `YYYY-MM-DD`.

## [0.4.0] - 2026-11-13

把「我当时的判断」变成可对账的资产。这是第三个可选模块，与宏观、新闻同级。

### 新增

- **可选模块：深度研究对账**。`reports/YYYY-MM/YYYY-MM-DD-research-<主代码>.md` 出现的标的，
  详情页长出顶栏入口按钮、首屏入口条、页内「研究结论对账」卡片三处；没有报告的标的显示「未覆盖」
  并说明原因。删掉报告文件，整块自动消失，不需要改代码。
- `references/research-contract.md`：报告格式契约（`## 待验证命题` 四列表格是解析契约）、
  状态文件语义、调研来源的实测质量对比（哪个话题类型找得到东西、哪个找不到）。
- `state/research-checks.json`：命题核对状态，由 `instance.py` 初始化。
  **只存状态不存正文**，正文永远从报告 Markdown 现读，避免两份真相。
- `scripts/build_stock_pages.py` 新增 `latest_research` / `parse_props` / `load_checks` /
  `research_card` / `research_strip`。缺报告、缺小节都返回空而不抛错——一份格式错误的报告
  不能炸掉全部详情页。
- `assets/demo/research/`：一份完全虚构的示例报告 + 对应状态，`--mode demo` 时自动落到
  `reports/`，让新用户 clone 下来就能看到这个模块长什么样。
- `docs/screenshots/07-research-entry.png`、`08-research-card.png`。
- `references/pitfalls.md` 新增 36–39：报告不可变、状态文件不存正文、未覆盖不许静默留空、
  内容入口不要复用导航按钮的样式类。

### 变更

- **`example/` 改成镜像「实例根」结构**：`example/dashboard/` + `example/reports/`，
  原来平铺的 `example/index.html`、`example/stocks/` 已删除。理由：研究报告在 `<实例根>/reports/`，
  详情页链接是 `../../reports/…`，平铺结构下这个链接会跑到仓库外面，点不通。
- README 的「先看效果」入口改为 `example/dashboard/index.html`。

### 修复

- 首页「分红日历」与「收益曲线」改为常驻展开，不再折叠。折叠面板对两块常看的内容没有意义，
  反而多一次点击。

### 设计取舍

- **只开源「对账」，不开源「怎么产报告」**。产报告要接外部检索服务、要账号凭证，
  陌生 clone 下来第一步就卡死；把一个装好也用不了的东西写进包里，等于给用户一个假承诺。
  这个包负责把研究变成可对账的资产，不负责替你写研究。
- **入口显示的来源名从 `source_label` 读，不写死在代码里**。不同人的研究来源不同，
  在 UI 里硬编码一个供应商名字，等于替所有用户声明了来源。
- **对账卡不放进首屏**。详情页主线是「结论 → 数据验证 → 预期差」，研究是另一条线，
  硬插中间会切碎数据流；用首屏入口条解决可见性，比移动整卡划算。

## [0.3.0] - 2026-11-13

修三个「数据看起来是新的、其实不是」的问题。都不影响首次安装，但长期运行后会咬人。

### 新增

- `scripts/macro_release_due.py`：判断今天或昨天有没有白名单内的宏观发布，输出该重取哪几项。
  只读本地文件、不调 MCP，判定失败返回空而不是抛错。
- `config/macro.yaml` 模板新增 `release_refresh`（关键词表、`window_days`、讲话/纪要排除词）
- `references/automation-prompts.md` 新增模板 C「盘前集合竞价检查」，并给模板 A 加公布日重取判定
- `config/alert-rules.yaml` 模板新增 `preopen_hour` 占位符

### 修复

- **宏观滞后最多 5 个交易日**：原来「周二至周五只查日历」没有配套的重取机制，周三公布的 CPI
  要等到下周一才进看板。现在自动化每天跑一次判定脚本，命中就只重取受影响指标并写 `forced_refresh`。
- **快照过期不报警**：看板按「含该文件的最新目录」读快照，某天任务挂了不会报错，只是继续显示上一天的数据。
  现在环境条带 `data-asof`，由内联 JS 按**打开页面的时间**算「N 小时前更新 / 已 N 天未更新」，
  新闻超 24h、宏观日历超 48h 标橙。演示模式不显示该标记（虚构数据日期是固定的，会永远显示过期）。
- **「已收盘」是写死的**：状态标签原来固定输出 `已收盘 · as_of`，盘中打开也在说收盘。
  现在分三态：收盘 / 盘中 / 盘前参考价。**判收盘档不能只查「收盘」两字**——盘中快照的
  `as_of` 常写「非收盘价」，会被误判成收盘档，把没确认的价说成已确认。
- 新闻取数全部失败时，不再用空列表覆盖当天快照（否则看板显示「刚更新、0 条」，掩盖了失败）。

### 文档

- `references/pitfalls.md` 新增 34–35：子串判断把盘中当收盘、盘前竞价价不是成交价且去重要独立字段
- `references/data-contract.md`：`quotes.json` 的 `as_of` 三态与 `price_type`、`macro.json` 的 `forced_refresh`

## [0.2.0] - 2026-11-12

新增两个**可选**模块：宏观环境与行业新闻。两者默认关闭，有快照才渲染，删掉快照即消失。

### 新增

- `config/macro.yaml` 模板 + `assets/demo/macro.json`：中美 6–8 项指标定义、取数路径、未来日历白名单、提醒规则
- `config/industry-topics.yaml` 模板 + `assets/demo/news.json`：细分行业词表、A/B/C 分层、过滤与合规规则
- 首页新增顶部常露的「环境条」（下一个数据倒计时 + 覆盖概览）与可折叠的宏观指标面板
- 首页新增行业新闻列表：A/B 类直列、C 类折叠、被过滤项可展开看理由
- `references/pitfalls.md` 新增 5 条（29–33）：语义检索不是字面匹配、宏观接口 `start/end` 陷阱、乱序混装表、一篮子字段的行类型、日历无指标代码
- `references/data-contract.md` 新增 `macro.json` 与 `news.json` 两个 schema

### 变更

- 分红日历与收益曲线改为默认折叠，给新模块腾出首屏空间
- `build_dashboard.py` 的宏观/新闻快照按「含该文件的最新目录」独立读取，不与 `quotes.json` 绑定
- `example/index.html` 重建，包含两个新模块的演示形态
- 仓库更名为 `ginado-stock-dashboard-skill`（GitHub 对旧地址保留重定向，已 clone 的本地副本只需 `git remote set-url`）
- README 重写：按六项主要功能逐条展开，新增「需要添加的连接器」一节（腾讯自选股主源 / Wind 校准源 / 企业微信推送通道），删掉原有的问题对照表与冗长清单
- README 增加「界面」一节，6 张截图放在 `docs/screenshots/`，全部取自 demo 实例（虚构数据）。`privacy_check.py` 与 `.gitignore` 相应放行该目录，其他任何路径的图片仍然判 FAIL，规则见 `docs/screenshots.md`
- **补齐宏观与新闻的定时任务模板**：`references/automation-prompts.md` 之前只有「财报监控」和「盘中价格检查」两个模板，装着 skill 的人建了任务也不会去取宏观和新闻，两块永远空着。现在模板 A（09:30）加了宏观取数与日历提醒（第 14–16 步），模板 B（盘中）加了行业新闻取数（第 9 步，仅 `news_hours` 那两条整点执行）。不新增任务、不改调度节奏；没启用可选模块时要求整段删掉而不是留空步骤。`alert-rules.yaml.example` 相应新增 `news_hours` 字段，`instance.py` 补对应占位符默认值

## [0.1.0] - 2026-11-11

首次公开发布（初始能力包）。

### 新增

- `SKILL.md`：8 步工作流、截图录入的三层隐私提示、demo/live 物理隔离、交互 A（看板发起 → Agent 执行）、授权纪律
- `references/`：28 条实测踩坑清单、数据契约、方法论、调度规则、自动化 prompt 模板、免责声明
- `scripts/`：7 个参数化脚本，全部以 `--root` 显式接收实例目录，不推断 `__file__` 路径
  - `instance.py` 从模板实例化 demo/live 实例（模板占位符用 `string.Template`）
  - `build_dashboard.py` / `build_stock_pages.py` 输出单文件自包含 HTML
  - `check_sources.py` 数据源健康自检与自动降级
  - `record_nav.py` 每日净值埋点
  - `privacy_check.py` 仓库隐私扫描（默认拒绝式白名单）
  - `layout_check.py` 产物目录合规检查
- `assets/templates/`：`agent.md` 模板 + 5 份 `*.yaml.example`，全部用 `{{占位符}}`，不含任何具体金额、姓名、路径
- `assets/demo/`：完全虚构的演示行情与财报快照（`source: demo-fixture`）
- `example/`：demo-offline 生成的成品看板（首页 + 个股财报详情页）
- 看板交互：「+ 添加标的」「更新持仓」生成可复制指令，表单数据不写 `localStorage`、不拼 URL
- Apache-2.0 许可证、NOTICE、PRIVACY、SECURITY、隐私验收文档、CI 工作流

### 设计决策

- **开源的是能力，不是实例**：仓库只提交能力包与虚构演示，真实实例由用户在本机创建
- **默认拒绝式 `.gitignore`**：`*` + `!` 白名单，新增文件默认不进仓库
- **demo-offline 为默认**：零连接器、零网络即可从 clone 跑到成品
- **不打包任何供应商数据**：live 模式的数据合规义务由使用者承担
- **脚本不直连 MCP**：取数由 Agent 完成并落盘，脚本只读本地快照，便于复现与回测
