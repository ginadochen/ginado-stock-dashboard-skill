# 自动化 prompt 模板

以下模板由 Agent 实例化时用 `string.Template` 替换，替换值全部来自实例 `config/`。**模板里不得出现任何具体金额、姓名、绝对路径、标的代码或收件人**。

## 占位符清单

| 占位符 | 含义 | 来源 |
|---|---|---|
| `$ROOT` | 实例根目录绝对路径 | 用户指定 |
| `$CODES` | 主代码清单 | `config/watchlist.yaml` |
| `$OBSERVE_ONLY` | 仅观察标的代码 | `config/watchlist.yaml` |
| `$HOLDING` | 持仓标的代码 | `config/portfolio.yaml` |
| `$NOTIFY_CHANNEL` | 通知通道 | `config/alert-rules.yaml` |
| `$NOTIFY_TARGET` | 收件人 | 用户指定，默认当前授权人 |
| `$CONCENTRATION_LIMIT` | 单一标的占比上限 | `config/portfolio.yaml` |
| `$ADD_CAPITAL_LIMIT` | 加仓资金上限 | `config/portfolio.yaml` |
| `$DENOMINATOR` | 集中度分母（锁定值） | `config/portfolio.yaml` |
| `$MAX_ADD_SHARES` | 最大补仓股数 | `config/portfolio.yaml` |
| `$LOT_SIZE` | 整手单位 | `config/portfolio.yaml` |
| `$PEERS` | 同业清单路径 | `config/peers.yaml` |
| `$CHECK_HOURS` | 检查整点列表 | `config/alert-rules.yaml` |
| `$NEWS_HOURS` | 抓行业新闻的整点（默认 2 个，如 10:00 / 14:00） | `config/alert-rules.yaml` |

## 模板 A · 财报监控与速递（09:30，同时承担宏观低频取数）

适用：每日 09:30 一条。宏观挂在这里，不新增任务、不改盘中节奏。

```
你在维护 $ROOT 下的股票看板。先读 $ROOT/agent.md 并严格遵守其中的目录、命名、
数据口径、状态与敏感信息规则。

标的（主代码）：$CODES。仅观察：$OBSERVE_ONLY。持仓：$HOLDING。
同业对比清单见 $PEERS（role=peer_only）。

第 0 步（每次必做，先于任何取数）：运行 python $ROOT/scripts/check_sources.py
--root $ROOT，读 state/source-health.json。
- 校准源 status != up 时：跳过该源全部调用，不重试、不等待、不报错中断，
  以主源为唯一来源，在看板标注数据缺口。
- 工具索引里找不到该源工具时同样按不可用处理；不要反复重试、不要请求宿主重连。
- 若端点刚恢复且工具确实已注册：补取缺失的近 10 年 PE/PB/股息率历史分位，
  更新快照，把 config/buy-bands.yaml 中对应标的的锚改为真实估值分位、
  confidence 从 reference 改为 standard 并移除 data_gap，重算区间后重建页面。
  禁止用 K 线价格分位冒充估值分位。

任务：检测是否有新财报发布，有则生成对比分析、更新个股财报详情页并推送。

1. 读 config/watchlist.yaml、config/peers.yaml、config/buy-bands.yaml、
   state/last-report-period.json、state/dedupe.json。
2. 用主源的「按代码公告清单」（时间增量）、「预约披露日期」、「最新报告期与实际披露日」
   三个信号判定新财报。禁止用语义检索式公告工具（实测会串到别家公司）。
3. 对照 state 去重；无新财报时静默结束，不发任何消息（除权检测例外）。
4. 有新财报时：生成同比、环比、近 8 季趋势、毛利率/现金流/指引与措辞变化分析。
   跨市场按自然年季度对齐，不用「最新一期」直接横比。
   财报记账本位币、股价币种、账户展示币种三者分开标注。
5. 一致预期必须标「平台测算值，非一手机构一致预期，需核实原文」；
   无可靠预期写「无可靠一致预期」，不编造。
6. 报告写入 reports/YYYY-MM/YYYY-MM-DD-earnings-<主代码>.html，
   关键数字标注来源与时点。
7. 重算该股买入区间（估值锚变化、除权除息、财报逻辑破坏时尤其要改），
   在 config/buy-bands.yaml 注明原因与日期。confidence=reference 的标的
   保持参考级标注，不得把价格位置写成估值分位。
8. 重建页面：先运行 python $ROOT/scripts/build_stock_pages.py --root $ROOT，
   再运行 python $ROOT/scripts/build_dashboard.py --root $ROOT。
9. 更新 state/last-report-period.json 与 state/dedupe.json，先读后写。
10. 用 $NOTIFY_CHANNEL 向 $NOTIFY_TARGET 发送速递：标的、报告期、
    3 个最关键数字与同比、超/不及预期方向、对买入区间的影响、报告与详情页路径。
    涉及 confidence=reference 的标的须附「参考级 / 低置信度，需人工确认」。
11. 分红与除权检测（每轮必做）：比对最新 dividends.json 的 ex_date，
    出现新除权日则重算该股买入区间并注明原因与日期。
    接口未返回时标「未覆盖」，不得虚构未来除权日。
12. 加仓相关推送必须附「先写 config/journal.yaml 的买入理由与失效条件，
    再看摊薄数字」。交易日记由人工或明确授权的会话先读后写，自动化不擅自写入。
13. 检测到新财报时按 data-contract.md 的 schema 更新 earnings.json：
    near-8 季财务、公告清单、披露日前后 K 线、该股与同业估值。
    A 股与港股币种分开，跨市场只比比率与增速；缺口标未覆盖，不编造。
14. 宏观取数（**只在启用了 config/macro.yaml 时做**；每周一全量，
    周二至周五只做第 15 步的日历检查，不重复拉指标）：
   (a) 按 config/macro.yaml 的指标定义取数。**参数只用条数与年份，禁用时间区间**——
       实测传时间区间会返回整段历史（百万字符级），直接撑爆上下文。
   (b) 中国侧：同一张表里同一期可能混装多行（消费价格行 / 工业品价格行 /
       购进价格行各一条），必须按日期排序后再按「该行是否含目标字段」判断行类型，
       **禁止取第一条**。另外分组名不等于字段名：名为 CPI 的分组里可能只有 PPI 字段，
       CPI 得去另一张表取。
   (c) 美国侧是乱序「事件表」：同一张通胀表混装核心 PCE、联储预期、密歇根预期、
       PPI 月率，同一张就业表混装 JOLTs、时薪、工时、初请，返回顺序与日期无关。
       必须本地按日期降序 + 按 IndicatorName 精确匹配后取值，
       **禁止取第一条当「最新值」**。ForecastValue 会为空串，ActualValue 会出现「未公布」。
   (d) 预期值为空时显示「—」，不填 0；取不到就写 status=uncovered + reason，
       **禁止用旧值补位、禁止推算**。
   (e) 写入 data/YYYY-MM/YYYY-MM-DD/macro.json，schema 见 data-contract.md，
       带 source/as_of/currency。每张卡必须同时标 period（数据期）与 published（披露日），
       不能把两个月前的数据写成「今天」。中美两侧只并排看方向，
       不画同一条曲线、不算差值（一边是当期值+同比，一边是实际/预期/前值，频率也不同）。
   (f) 与 state/dedupe.json 的宏观记录比对（period 与 published 都变才算新数据），
       先读后写。
15. 宏观日历与提醒：
   (a) 取未来日历，按 config/macro.yaml 的白名单关键词过滤
       （CPI / PPI / GDP / 国民经济运行 / 利率决议 / 议息会议 等）。
       匹配不到就写 next_publish=null，**绝不按历史规律推算公布日期**——
       日历里经常没有你想等的那条，这是正常状态，不是故障。
   (b) 只有决策类事件（利率决议 / 议息会议）提前 1 天提醒；
       官员讲话只在看板里列出，不推送。
   (c) 本轮取过宏观或日历，就重跑第 8 步重建看板。
16. 有新宏观数据、或次日有决策事件时，**并入第 10 步的同一条消息**
    （一天最多一条汇总，不额外多发）：格式「宏观｜{指标} {值}{单位}（截至 X 月，公布 X 月 X 日）」。
    无变化不说话。

约束：MCP 调用串行、控制并发；不要写平台原生提醒（未获单独授权）；
不要在根目录或非白名单目录落文件；所有输出末尾附免责声明（disclaimer.md）。
无新财报时不推送（除权检测有变化、或第 16 步宏观有新数据/次日有决策事件，才通知）。
```

## 模板 B · 盘中价格检查（单整点，共 N 条）

适用：每个盘中整点一条（如 10:00 / 11:00 / 14:00 / 15:00 / 16:00）。
行业新闻挂在其中 2 条（$NEWS_HOURS），其余整点自动跳过那一步，不新增任务。

```
你在维护 $ROOT 下的股票看板，先读 $ROOT/agent.md 并严格遵守规则。
本任务只在交易日一个固定整点触发一次（$CHECK_HOURS 共 N 条同流程自动化），
交易时段外、午休、盘前、盘后、夜间均不触发，不要写成轮询。

标的：$CODES。仅观察：$OBSERVE_ONLY（不给买入区间、不推价格提醒）。持仓：$HOLDING。

1. 用交易日历分别查 A 股与港股当日是否为交易日；非交易日立即静默结束
   （不取数、不自检、不写文件、不发消息）。判断当前属于盘中检查还是收盘汇总。
2. 运行 python $ROOT/scripts/check_sources.py --root $ROOT 并读
   state/source-health.json。不可用时跳过该源调用、不重试、不请求重连；
   恢复且工具已注册时补取估值分位并把 confidence 升回 standard。
   禁止用 K 线价格分位冒充估值分位。
3. 用主源一次批量取全部标的，写入 data/YYYY-MM/YYYY-MM-DD/quotes.json，
   字段含 source/as_of/currency；双源分歧同时保留并标 conflict，绝不编造数字。
4. 运行 python $ROOT/scripts/build_dashboard.py --root $ROOT 重建
   dashboard/index.html（覆盖更新，路径不变）。
5. 读 config/buy-bands.yaml 比对可接受价格带与加仓分档触发价。
   到价不等于买点：需收盘确认、无放量杀跌、非盘中插针、失效条件未触发。
   confidence=reference 标的触发时推送须附「参考级/低置信度、需人工确认」。
   加仓受硬约束：分母锁定 $DENOMINATOR、占比 ≤ $CONCENTRATION_LIMIT、
   最多补 $MAX_ADD_SHARES 股、$LOT_SIZE 股整手、资金上限 $ADD_CAPITAL_LIMIT；
   被动越线只标红停止提示补仓，不提示减仓；摊薄只改账面成本，
   看板要同时显示仓位变化。
6. 读 state/dedupe.json 去重，同一档位只推一次，先读后写。
7. 仅在触发时用 $NOTIFY_CHANNEL 向 $NOTIFY_TARGET 发摘要：标的、现价与时点、
   区间与偏贵程度、触发档位、确认条件、失效条件。无触发不推送；
   收盘那次发「今日无触发/今日触发汇总」日汇总。
   推送不暴露持仓金额细节、不发布看板到公网。
   加仓相关推送附一句「先写 config/journal.yaml 的买入理由与失效条件」。
8. 仅收盘汇总那次额外做：取基准指数收盘价，运行
   python $ROOT/scripts/record_nav.py --root $ROOT --date <今日> ...
   落盘 nav.json；不足 10 个交易日不画收益曲线。
   比对 dividends.json 的 ex_date，有新除权日则重算买入区间。
9. 行业新闻取数（**只在启用了 config/industry-topics.yaml 时做，且仅 $NEWS_HOURS
   这两个整点做**，其余整点直接跳过本步）：
   (a) 拉最近 24 小时全量快讯（按发布时间倒序），用 config/industry-topics.yaml 的
       细分词表做**本地字面匹配**（标题或正文包含即命中），命中即 B 类。
       这一层不依赖检索服务，所以不会串。
   (b) A 类：用公司全名调资讯检索，**只有返回的关联代码落在观察池 + 同业白名单内
       才算命中**；近似名（「XX 黄金国际」之于「XX 矿业」）不算。
       该接口是语义相关、不是字面匹配（实测搜「版号」会返回核电项目开工），
       所有结果必须本地复检关键词是否真的出现在标题或正文里，不通过直接丢弃。
   (c) 标题含 研报 / 评级 / 维持 / 目标价 / 推荐买入 / 金股 的整条丢弃，
       不展示研报结论、不判断利好利空。聚合稿（24h / 盘前线索 / 盘点 / 周报 /
       早报 / 晚报 / 一览）与板块代码归 C 类。
   (d) 写入 data/YYYY-MM/YYYY-MM-DD/news.json，schema 见 data-contract.md，
       只保留 48 小时内。被丢弃的写进 excluded 并给 reason，便于事后复核。
   (e) 与 state/dedupe.json 的新闻记录比对去重，先读后写。
   (f) 重跑第 4 步重建看板。
   (g) 只有**新增的 A 类**才推送，并入当日汇总（一天最多一条）：
       标题、来源、发布时间、链接。B / C 类只进看板，不推。不摘录正文。
10. 所有推送末尾附免责声明（disclaimer.md）。

约束：仅观察标的不给区间、不推价格提醒；不要写平台原生提醒（未获单独授权）；
MCP 调用串行、控制并发；所有产出写 $ROOT 绝对路径。
```

## 使用说明

- 每条任务一个整点，创建后逐条核对 `nextRunAt` 时区。
- **可选模块不新增任务**：宏观只挂在模板 A（09:30），新闻只挂在模板 B 里 `$NEWS_HOURS`
  那 2 条整点。总任务数不变，调度节奏也不变。
- 实例没有启用可选模块时（`config/` 里没有 `macro.yaml` / `industry-topics.yaml`），
  把对应的整段步骤（模板 A 的第 14–16 步、模板 B 的第 9 步）**整段删掉**，
  不要留一个「本步跳过」的空壳。
- 宏观是周/月频，新闻是日频，两者都不跟行情快照绑定；快照按「含该文件的最新目录」
  单独读取，所以某天没跑行情不影响这两块的展示。
- 模板不含任何真实数据；实例化后的 prompt 由 Agent 生成，**不写回仓库**。
- 用户可随时暂停/删除任务；skill 不负责清理已经创建的自动化。
