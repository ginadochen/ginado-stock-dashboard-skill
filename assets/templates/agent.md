# {{PROJECT_NAME}} · 实例规则

> 本文件由 `assets/templates/agent.md` 实例化生成，是**本实例**目录纪律的唯一真值来源。
> 修改规则先改本文件，并在末尾追加变更记录。对话里的口头约定不覆盖本文件。

## 适用范围

- 实例根目录：`{{ROOT}}`
- 模式：`{{MODE}}`（demo | live）。`demo` 使用完全虚构数据，仅用于看样式。
- 所有产出写 `{{ROOT}}` 下的绝对路径；定时自动化 `cwds` 设为 `{{ROOT}}`。
- 数据源主源：`{{PRIMARY_SOURCE}}`；校准源：`{{CALIBRATION_SOURCE}}`（可缺失，需能降级）。
- 通知通道：`{{NOTIFY_CHANNEL}}`；收件人：`{{NOTIFY_TARGET}}`。
- skill 安装目录是**只读能力包**，任何产物都不得写入其中。

## 1. 目录纪律

```
{{ROOT}}\
├─ agent.md              本文件：规则唯一真值来源
├─ config\               人工维护、必须备份
│   ├─ instance.yaml     mode / 根目录 / 数据源开关
│   ├─ portfolio.yaml    持仓、成本、资金（敏感）
│   ├─ watchlist.yaml    标的清单 + 双源代码映射
│   ├─ buy-bands.yaml    买入区间基准库
│   ├─ alert-rules.yaml  阈值、时段、去重窗口
│   ├─ peers.yaml        同业清单（role: peer_only）
│   └─ journal.yaml      交易日记 / 买入理由
├─ state\                机器状态，去重唯一真值
│   ├─ dedupe.json
│   ├─ last-report-period.json
│   └─ source-health.json
├─ data\YYYY-MM\YYYY-MM-DD\  原始快照（quotes / valuation / dividends / nav / earnings）
├─ reports\YYYY-MM\     一次性网页：YYYY-MM-DD-<类型>-<主代码>.html
├─ dashboard\
│   ├─ index.html        唯一固定入口，覆盖更新，永不改名
│   └─ stocks\<主代码>.html  个股财报详情页，固定路径覆盖更新
├─ tmp\YYYYMMDD-HHMMSS-<用途>\  临时文件，一次任务一个子目录
├─ logs\YYYY-MM.log
└─ archive\YYYY\         超期归档，只进不出
```

- 根目录只允许 `agent.md` + 上述固定目录；禁止直接落 HTML / JSON / CSV / 图片 / 日志。
- 新增顶层目录必须先改本文件并追加变更记录。
- 日期一律 `YYYY-MM-DD`，按月分目录防单目录膨胀；文件名 `<日期>-<类型>-<主代码>.<ext>`。
- 代码统一用 `watchlist.yaml` 里的主代码；禁中文空格与特殊字符。

## 2. 临时文件

- 一律 `tmp/YYYYMMDD-HHMMSS-<用途>/`；任务结束即清，异常残留保留 7 天。
- 禁止写到工作区、桌面、下载、聊天附件目录或系统 temp；`tmp` 不进交付、不发布。

## 3. 网页

- `dashboard/index.html` 是**唯一固定入口**：路径永久不变，覆盖更新，不建带日期副本。
- `dashboard/stocks/<主代码>.html` 是**个股财报详情页**：固定路径、覆盖更新、单文件自包含。
- 一次性报告（财报速递等）进 `reports/YYYY-MM/`，按次生成、不覆盖。
- 所有网页必须**单文件自包含**（CSS/JS 内联）：预览面板会剥掉外链资源。
- 历史版本要留档就复制到 `archive/YYYY/` 并改名带日期，不得在 `dashboard/` 内堆版本。
- 网页内所有关键数字标注来源与数据时点；财报数字标 `as_of`、行情估值标 `quote_as_of`。
- **图表规范**：分组柱状图 + 真实金额纵轴 + 0 线；柱端数值必须常显（按量级自适应精度、逐个防重叠避让），悬停只作精度补充；横轴每个报告期一个刻度，禁止隔期抽稀，月份两位数字全量标注、年份合并为下方分组带，首尾留白 ≥ 28；正值标柱顶、亏损标柱底；窄屏可横向滚动，不得靠缩小字号硬塞。

## 4. 数据口径

- 每个快照必须带 `source` / `as_of` / `currency` 三字段。
- 双源冲突标 `conflict: true` 并**同时保留两个值**，禁止静默取一。
- 三重币种分离：财报记账本位币、股价交易币种、账户展示币种。
- 跨市场只比比率与增速，不比绝对金额；A/H 按自然年季度对齐并标注周期差。
- **禁止口径伪装**：估值分位缺失时不得用 K 线价格分位冒充 PE/PB 历史分位；替代锚标 `confidence: reference`，通知附「低置信度、需人工确认」。
- 一致预期若机构数为 0，标「平台测算值，非一手机构一致预期，需核实原文」；无可靠预期就写「无可靠一致预期」。
- 数据源降级：取数前跑 `python {{SKILL_SCRIPTS}}/check_sources.py --root {{ROOT}}` 并读 `state/source-health.json`；不可用时跳过全部该源调用、不重试、不请求重连、不中断；恢复后自动补取并重算。
- 每日净值快照：`nav.json` 记录总资产、现金、持仓市值、基准收盘；账户数值只从 `config/portfolio.yaml` 读，不写日志、不进通知。
- 分红与除权基线：`dividends.json` 保存已实施派息与最新 `ex_date`；检测到新除权日必须重算该股买入区间并注明原因与日期；未覆盖标 `not_covered`，不得虚构未来除权日。
- 财报快照按 `references/data-contract.md` 的 schema；近 8 季不足按实际期数，缺口标未覆盖，不编造。
- demo 与 live 物理隔离：切换 live 时强制清空演示持仓与快照并二次确认。

## 5. 状态与写入

- `state/` 只增不改不重建，写入一律**先读后写**。
- `config/` 由人工或明确授权的会话维护；自动化只读 `config/`。
- 平台原生提醒是写操作且常为全量覆盖语义，改前必须读回全部字段回填，并单独获得授权。

## 6. 敏感信息

- `config/portfolio.yaml`、`config/journal.yaml` 含金额与成本：不发布公网、不写进日志、不复制到 `tmp/`。
- 持仓截图默认不落盘；如留存只能写 `archive/` 且必须被 `.gitignore` 排除。
- 看板若要在线访问必须加口令；日志与通知正文脱敏，不暴露持仓金额细节。

## 7. 保留与清理

| 目录 | 策略 |
|---|---|
| `tmp/` | 7 天后删除 |
| `data/` | 90 天后移入 `archive/` |
| `logs/` | 180 天后移入 `archive/` |
| `reports/` `config/` `state/` | 永久保留，变动前备份 |

清理只由自动化执行、只针对白名单目录，禁用递归删除和通配符。

## 8. 调度纪律

- 只在开盘时段跑；采用**多条单整点规则**，禁用 `HOURLY` 全天轮询（实测多 `BYHOUR` 会把 nextRunAt 算到非交易时段）。
- 节假日由任务内交易日历静默退出；A/H 分别判断。
- 收盘那一次负责日汇总、净值埋点、除权检测，不是盘中空跑。
- 无触发不推送；同一档位只推一次；收盘给一条日汇总。

## 9. 与 skill 的关系

- 本实例由 `{{SKILL_NAME}}` skill 生成；skill 目录只读，实例目录是唯一产物落点。
- 所有脚本通过 `--root` 显式接收根目录，不得用 `Path(__file__).parent.parent` 推断。
- 宿主自建的 `.workbuddy/` 记忆与自动化记录属系统机制，不迁移、不删除、不登记为项目产出。

## 变更记录

| 日期 | 变更 |
|---|---|
| {{CREATED_AT}} | 初始建立：由 skill 模板实例化，模式 `{{MODE}}` |
