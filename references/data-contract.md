# 数据契约

所有落盘快照必须遵守本契约。字段名是脚本与模板之间的唯一约定，改动需同步 `docs/CHANGELOG`。

## 通用必填字段

每个快照 JSON 顶层必须有：

| 字段 | 说明 |
|---|---|
| `source` | 数据来源标识，如 `demo-fixture` / `westock-mcp` / `wind-mcp` / `manual` |
| `as_of` | 数据时点，`YYYY-MM-DD` 或带时分的 ISO 8601 |
| `currency` | 该快照金额所用币种（CNY / HKD / USD…） |

财报类额外需要 `quote_as_of`：**财报数字是各报告期的历史值，行情估值是当前值**，两者时点不同，必须分别标注，禁止把盘中价当收盘价。

## 快照文件

### `data/YYYY-MM/YYYY-MM-DD/quotes.json`

```
{ source, as_of, currency, calibration_source, conflict_policy,
  conflicts: [ {code, field, primary_value, calibration_value, reason} ],
  quotes: {
    "<主代码>": { name, price, prev_close, chg_pct, chg_ytd,
                  pe_ttm, pb, dividend_yield, high_52w, low_52w,
                  lot_size, trade_currency, status, time }
  } }
```

- `conflict_policy` 固定 `keep_both_and_flag`。双源分歧时**两个值都保留**在 `conflicts`，看板标「双源分歧」，禁止静默取一。
- 亏损股 PE 为负属正常，不要取绝对值。

### `valuation.json`

```
{ as_of, source, currency,
  percentiles_10y: { "<主代码>": { pe: {value, percentile}, pb: {...}, dividend_yield: {...} } },
  data_gap: { field, affected[], reason, policy },
  consensus: { "<主代码>": { target_price, institution_count, confidence, note } } }
```

- **缺失的分位必须是 `null` 或不出现，不能填价格分位**。
- `institution_count == 0` 的预测值必须标「平台测算值，非一手机构一致预期，需核实原文」。

### `dividends.json`

```
{ source, as_of, currency,
  coverage: { "<主代码>": "covered" | "not_covered" },
  plans: [ {code, ex_date, per_share, report_period, progress} ],
  ttm_calibration: { "<主代码>": { ttm_payout, implied_yield, note } } }
```

- 只记录**已实施**派息；不得虚构未来除权日。
- 未覆盖的市场/标的显式标 `not_covered`。
- 股息率双源分歧时，用实际派息实算并标注口径差（TTM 含中期分红 vs 仅年度方案）。

### `nav.json`

```
{ source, as_of, currency, date,
  total_assets_cny, cash_cny, position_value_cny, day_pnl_cny,
  benchmarks: { "<指数代码>": <收盘价> },
  method_note, first_written_at, updated_at }
```

- 账户数值只从 `config/portfolio.yaml` 读，**不写进日志、不出现在推送正文**。
- 不足 10 个交易日不画收益曲线。

### `earnings.json`

```
{ source, as_of, currency, schema_note, quote_as_of,
  limitations: [ ... ],
  financials: {
    "<主代码>": {
      name, currency, periods: [
        { period, publ, type, revenue, net_profit,
          rev_yoy, np_yoy, rev_yoy_q, np_yoy_q,
          gross, net_margin, roe, eps, debt, div_ttm }
      ] } },
  valuation_snapshot: {...},
  peers: { "<主代码>": [ {code, name, revenue, net_profit, gross, roe, pe, pb} ] },
  announcements: { "<主代码>": [ {id, time, title, type, url} ] },
  price_reaction: { "<主代码>": { d1, d5, d20, note } } }
```

- 金额单位统一「亿元（**本币**）」。`currency` 每个标的独立字段。
- **A 股 CNY 与港股 HKD 分开存**；跨市场同业横比只比毛利率、增速、ROE、PE/PB 等**比率**，不比绝对金额。
- 报告期按自然年季度对齐；A 股 Q3 与港股 H1 的周期差必须标注。
- 近 8 季不足时按实际期数，不补零、不编造；管理层措辞/指引、经营现金流、分部数据若无结构化字段，标「未覆盖」。

## 可选模块快照（宏观 / 新闻）

两个模块都是**可选**的：文件不存在就不渲染对应区块，不影响首页其余部分。两者均按「含该文件的最新目录」独立读取，**不与 `quotes.json` 绑定**——宏观是周/月频、新闻是日频，跟着行情快照走会读不到。

### macro.json

```
{
  "source": "...", "as_of": "...", "currency": "mixed",
  "indicators": [
    { "key": "cn_cpi", "region": "CN", "name": "CPI 同比",
      "value": 0.4, "unit": "%",
      "period": "2025-12",            // 数据截止期
      "published": "2026-01-03",      // 数据披露日
      "indicator_name": "CPI:当期同比:月(%)",
      "status": "ok",                 // ok | uncovered
      "forecast": null, "former": null,
      "reason": null }                // status=uncovered 时必填
  ],
  "calendar": {
    "next_publish": { "region": "...", "event": "...", "date": "...", "time": "...", "matched": "..." },
    "decision_events": [ { "region": "...", "date": "...", "event": "...", "kind": "decision" } ],
    "events": [ { "region": "...", "date": "...", "time": "...", "event": "...", "kind": "data|policy_speech|other" } ]
  },
  "coverage": {
    "total_cards": 8, "with_value": 7,
    "uncovered": ["us_policy_rate"],
    "cn_us_note": "中国为当期值+同比，美国为实际/预期/前值，不可直接比较"
  }
}
```

- `period` 与 `published` **必须分开存**。「11 月看到 9 月的数」是常态，只写一个 `as_of` 会让人误以为是当期值。
- `status: uncovered` 时 `value` 置 null、`reason` 必填；**禁止用旧值或推算值填充**。
- 中美口径不同（当期值+同比 vs 实际/预期/前值），`coverage.cn_us_note` 里必须写明「不可直接比较」；页面只并排看方向。
- `next_publish` 为 null 是合法状态：日历里确实可能没有白名单事件。**不允许按历史规律补一个日期**。

### news.json

```
{
  "source": "...", "as_of": "...", "window_hours": 48, "terms_version": 1,
  "items": [
    { "id": "...", "tier": "A",              // A 个股 / B 行业 / C 背景
      "title": "...", "source_media": "...",
      "publish_time": 1767579300,            // Unix 秒
      "url": "", "matched_term": "净息差", "owner": "sh601398",
      "relate_stock": [ { "code": "sh601398", "name": "..." } ] }
  ],
  "stats": { "A": 2, "B": 2, "C": 2 },
  "excluded": [ { "title": "...", "reason": "...", "would_be_tier": "A" } ]
}
```

- `tier` 只有 A / B / C。A 以 `relate_stock` 命中 watchlist + peers 白名单为**唯一**判据；B 由本地字面匹配产生；C 是板块代码、聚合稿与语义检索补充。
- `publish_time` 统一 Unix 秒，由构建脚本按 `window_hours` 过滤并格式化，避免时区与格式歧义。
- `excluded` 必须保留：它既是「过滤确实生效」的证据，也是排查误杀的入口。
- 只存标题、来源、时间、链接与命中词，**不存正文**，避免版权与语境失真。

## 置信度

| 值 | 含义 | 通知要求 |
|---|---|---|
| `standard` | 有一手估值分位/财务数据支撑 | 正常 |
| `reference` | 参考级：用价格位置代理、平台测算值或数据缺口下的替代锚 | 必须附「参考级 / 低置信度、需人工确认」，不得表述为估值分位支持的买点 |

`confidence` 写在 `config/buy-bands.yaml` 每个标的条目里。数据源恢复后按 `degradation.recovery` 补数重算，从 `reference` 升回 `standard`。

## 币种与代码

- 三重币种分离：`reporting_currency`（财报）、`trade_currency`（股价）、`display_currency`（账户展示）。
- 双源代码映射**只在 `config/watchlist.yaml` 维护一份**；文件名一律用主代码。
- 同业清单只在 `config/peers.yaml` 维护，标 `role: peer_only`，不进主清单、不参与价格告警、不给买入区间。

## 演示数据

`demo` 模式的快照 `source` 必须是 `demo-fixture`，并在实例 `config/instance.yaml` 里带 `mode: demo`。所有虚构数字要明显不真实（整圆数值），页面常驻「演示数据」横幅。`privacy_check.py` 会识别该标记。
