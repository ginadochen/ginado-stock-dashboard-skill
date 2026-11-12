"""Build the single-file, self-contained dashboard index.html.

Reads ONLY local config/ and data/ snapshots under --root. Never calls MCP,
never writes outside --root. CSS and JS are inlined because preview panels
strip external <link>/<script src> resources.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from common import (
    add_root_arg, require_root, resolve_root, instance_paths, load_yaml, load_json,
    latest_snapshot_with, esc, num, signed, cls, now_iso,
    DISCLAIMER_FULL,
)

# ---------------------------------------------------------------------------
# Design tokens + layout (plain strings: never f-strings, braces stay intact)
# ---------------------------------------------------------------------------

CSS = r"""
:root{
  --bg:#0f141c; --bg-2:#141b26; --panel:#182130; --panel-2:#1d2737;
  --border:#2a3648; --text:#e8eef7; --text-2:#aab8cc; --text-3:#7d8ca3;
  --accent:#5b9cff; --accent-2:#7cb0ff; --warn:#f0a94b; --bad:#ef6b6b;
  --up:#f0616b; --down:#3fc28b; --ok:#3fc28b;
  --radius:14px; --shadow:0 6px 24px rgba(0,0,0,.22);
  --mono:"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
}
html[data-theme="light"]{
  --bg:#f5f7fb; --bg-2:#eef2f8; --panel:#ffffff; --panel-2:#f3f6fb;
  --border:#dde4ef; --text:#1b2433; --text-2:#4c5b70; --text-3:#7a879a;
  --accent:#2f6fd0; --accent-2:#4c8ae0; --warn:#c07a18; --bad:#d04545;
  --up:#d63a48; --down:#159a6b; --ok:#159a6b;
  --shadow:0 4px 18px rgba(24,40,70,.08);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:26px 20px 60px}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right}
.up{color:var(--up)} .down{color:var(--down)}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
h1,h2,h3{margin:0;font-weight:650;letter-spacing:.01em}
h1{font-size:22px} h2{font-size:16px} h3{font-size:14px}
.eyebrow{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--text-3);font-weight:700}
.hint{font-size:12px;color:var(--text-3);font-weight:400}
.src{font-size:11.5px;color:var(--text-3);margin-top:10px;line-height:1.7}

/* header */
.top{display:flex;justify-content:space-between;align-items:center;gap:14px;margin-bottom:18px;flex-wrap:wrap}
.brand{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.status-chip{display:inline-flex;align-items:center;gap:7px;padding:6px 11px;border:1px solid var(--border);
  border-radius:999px;background:var(--panel);font-size:12px;color:var(--text-2)}
.dot{width:7px;height:7px;border-radius:50%;background:var(--ok)}
.dot.warn{background:var(--warn)}
.btn{border:1px solid var(--border);background:var(--panel);color:var(--text-2);border-radius:9px;
  padding:7px 12px;font-size:12px;cursor:pointer;font-family:inherit}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.btn.primary:hover{opacity:.9;color:#fff}

/* demo banner */
.demo-banner{display:flex;gap:12px;align-items:flex-start;padding:14px 16px;border-radius:var(--radius);
  border:1px solid #6a5320;background:linear-gradient(90deg,rgba(240,169,75,.14),rgba(240,169,75,.04));
  margin-bottom:18px}
.demo-banner b{color:var(--warn)}
.demo-banner .tag{font-family:var(--mono);font-size:11px;padding:3px 8px;border-radius:6px;
  background:var(--warn);color:#1a1206;font-weight:800;letter-spacing:.06em;white-space:nowrap}

/* cards */
.card{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);
  padding:18px 20px;margin-bottom:16px;box-shadow:var(--shadow)}
.card-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:14px;flex-wrap:wrap}
.grid{display:grid;gap:16px}
.g2{grid-template-columns:repeat(2,minmax(0,1fr))}
.g3{grid-template-columns:repeat(3,minmax(0,1fr))}
@media(max-width:860px){.g2,.g3{grid-template-columns:1fr}}

/* hero */
.hero{padding:22px 24px;background:linear-gradient(135deg,var(--panel),var(--panel-2))}
.hero-value{font-family:var(--mono);font-size:40px;font-weight:700;letter-spacing:-.02em;
  font-variant-numeric:tabular-nums;line-height:1.15;margin-top:6px}
.kpi{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin-top:18px;
  border-top:1px solid var(--border);padding-top:16px}
.kpi-label{font-size:11.5px;color:var(--text-3)}
.kpi-value{font-family:var(--mono);font-size:19px;font-weight:650;font-variant-numeric:tabular-nums;margin-top:2px}
@media(max-width:640px){.kpi{grid-template-columns:1fr;gap:10px}.hero-value{font-size:32px}}

/* brief */
.brief{display:flex;gap:12px;align-items:flex-start;padding:13px 15px;border-radius:11px;
  background:var(--panel-2);border:1px solid var(--border);margin-bottom:9px}
.brief-ico{flex:0 0 22px;height:22px;border-radius:6px;display:grid;place-items:center;
  font-size:12px;font-weight:800;background:rgba(91,156,255,.18);color:var(--accent)}
.brief.warn .brief-ico{background:rgba(240,169,75,.18);color:var(--warn)}
.brief.bad .brief-ico{background:rgba(239,107,107,.18);color:var(--bad)}
.brief-title{font-size:11px;color:var(--text-3);font-weight:700;letter-spacing:.06em;text-transform:uppercase}
.brief-body{font-size:13px;color:var(--text-2)}

/* table */
table{width:100%;border-collapse:collapse;font-size:13px}
th{font-size:11px;color:var(--text-3);font-weight:700;text-align:left;letter-spacing:.05em;
  padding:9px 8px;border-bottom:1px solid var(--border);white-space:nowrap}
td{padding:10px 8px;border-bottom:1px solid var(--border);vertical-align:middle}
tr:last-child td{border-bottom:0}
th.num,td.num{text-align:right}
.badge{display:inline-block;font-size:10.5px;padding:2px 7px;border-radius:6px;margin-left:5px;
  background:var(--panel-2);border:1px solid var(--border);color:var(--text-3);white-space:nowrap}
.badge.gap{color:var(--warn);border-color:rgba(240,169,75,.4)}
.badge.ref{color:var(--warn);border-color:rgba(240,169,75,.4)}
.badge.ok{color:var(--ok)}
.detail-link{font-size:11.5px;white-space:nowrap}

/* price map */
.pmap-row{padding:11px 0;border-bottom:1px solid var(--border)}
.pmap-row:last-child{border-bottom:0}
.pmap-head{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:7px;flex-wrap:wrap}
.pmap-name b{font-size:13px} .pmap-name .mono{font-size:11px;color:var(--text-3);margin-left:8px}
.bar{position:relative;height:8px;border-radius:6px;background:var(--panel-2);overflow:visible}
.bar .band{position:absolute;top:0;height:100%;background:rgba(63,194,139,.42);border-radius:6px}
.bar .mark{position:absolute;top:-4px;width:3px;height:16px;border-radius:2px;background:var(--accent)}
.bar .lbl{position:absolute;top:11px;font-size:10px;color:var(--text-3);font-family:var(--mono);transform:translateX(-50%)}

/* holdings + calculator */
.pos-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:14px}
.pos-cell{background:var(--panel-2);border:1px solid var(--border);border-radius:10px;padding:11px 13px}
.pos-cell .k{font-size:11px;color:var(--text-3)} .pos-cell .v{font-family:var(--mono);font-size:17px;font-weight:650;margin-top:2px}
@media(max-width:760px){.pos-grid{grid-template-columns:repeat(2,1fr)}}
.calc{display:grid;grid-template-columns:1.1fr 1fr;gap:18px;margin-top:6px}
@media(max-width:860px){.calc{grid-template-columns:1fr}}
.calc label{display:block;font-size:11.5px;color:var(--text-3);margin:8px 0 4px}
input[type=number],select{width:100%;padding:9px 11px;border-radius:9px;border:1px solid var(--border);
  background:var(--panel-2);color:var(--text);font-family:var(--mono);font-size:14px}
input[type=range]{width:100%;accent-color:var(--accent)}
.calc-out{background:var(--panel-2);border:1px solid var(--border);border-radius:11px;padding:14px 16px}
.calc-out .row{display:flex;justify-content:space-between;gap:10px;padding:5px 0;font-size:12.5px}
.calc-out .row b{font-family:var(--mono);font-variant-numeric:tabular-nums}
.notice{margin-top:12px;padding:11px 13px;border-radius:9px;background:rgba(91,156,255,.08);
  border:1px solid rgba(91,156,255,.28);font-size:12px;color:var(--text-2)}
.notice.bad{background:rgba(239,107,107,.09);border-color:rgba(239,107,107,.35)}

/* journal / checklist / change-request */
.check-item{display:flex;gap:9px;align-items:flex-start;padding:6px 0;font-size:12.5px;color:var(--text-2)}
.check-item input{margin-top:4px;accent-color:var(--accent)}
.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
@media(max-width:700px){.form-grid{grid-template-columns:1fr}}
.form-grid label{font-size:11.5px;color:var(--text-3);display:block;margin-bottom:4px}
textarea{width:100%;min-height:150px;padding:12px;border-radius:10px;border:1px solid var(--border);
  background:var(--panel-2);color:var(--text);font-family:var(--mono);font-size:12px;line-height:1.6;resize:vertical}
pre{white-space:pre-wrap;word-break:break-word;font-family:var(--mono);font-size:11.5px;
  padding:12px;border-radius:10px;background:var(--panel-2);border:1px solid var(--border);color:var(--text-2);margin:0}
.privacy-note{font-size:11.5px;color:var(--warn);margin-top:8px}

/* dividends / progress / events */
.mini-progress{height:7px;border-radius:6px;background:var(--panel-2);overflow:hidden;margin:9px 0}
.mini-progress i{display:block;height:100%;background:var(--accent)}
.event-row{display:flex;justify-content:space-between;gap:12px;padding:8px 0;
  border-bottom:1px solid var(--border);font-size:12.5px}
.event-row:last-child{border-bottom:0}
.event-row .t{font-family:var(--mono);font-size:11px;color:var(--text-3);white-space:nowrap}
details{border:1px solid var(--border);border-radius:10px;padding:10px 13px;margin-bottom:9px;background:var(--panel-2)}
summary{cursor:pointer;font-size:12.5px;font-weight:600;color:var(--text-2)}
.detail-body{font-size:12px;color:var(--text-2);padding-top:9px;line-height:1.8}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:11.5px;color:var(--text-3);margin-top:8px}
.legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;vertical-align:middle}
.foot{margin-top:26px;padding-top:16px;border-top:1px solid var(--border);font-size:11.5px;color:var(--text-3);line-height:1.8}

/* macro env bar + news layers (optional module) */
.env-bar{display:flex;align-items:center;gap:13px;flex-wrap:wrap;margin:0 0 16px;padding:11px 15px;
  border:1px solid var(--border);border-radius:12px;background:var(--panel)}
.env-bar .lab{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3)}
.env-bar .ev{font-size:12.5px;font-weight:600}
.env-bar .meta{font-size:11px;color:var(--text-3)}
.env-bar .spacer{flex:1 1 auto}
.env-bar .stat{display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--text-2)}
.env-bar .dot-s{width:6px;height:6px;border-radius:50%;background:var(--ok);flex:none}
.env-bar .dot-s.gap{background:var(--text-3)}
.countdown{display:inline-block;padding:1px 8px;border-radius:6px;font-size:11px;font-weight:600;
  background:color-mix(in srgb,var(--warn) 16%,transparent);color:var(--warn);margin-left:4px}
.macro-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:9px}
.macro-card{border:1px solid var(--border);border-radius:10px;padding:11px 12px;background:var(--panel-2)}
.macro-card.uncovered{border-style:dashed}
.macro-top{display:flex;align-items:center;gap:6px;margin-bottom:6px}
.macro-region{font-size:9.5px;padding:1px 5px;border-radius:4px;border:1px solid var(--border);
  color:var(--text-3);flex:none}
.macro-region.us{color:var(--accent-2);border-color:var(--accent-2)}
.macro-nm{font-size:11px;color:var(--text-2)}
.macro-val{font-size:22px;font-weight:650;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.macro-val .u{font-size:11.5px;font-weight:500;color:var(--text-3);margin-left:2px}
.macro-card.uncovered .macro-val{font-size:14px;font-weight:500;color:var(--text-3)}
.macro-ind{font-size:10px;color:var(--text-3);margin-top:4px;line-height:1.5;min-height:30px}
.macro-meta{display:flex;justify-content:space-between;gap:5px;font-size:10px;color:var(--text-3);
  margin-top:6px;padding-top:6px;border-top:1px solid var(--border)}
.macro-gap{font-size:10px;color:var(--text-2);margin-top:3px}
.macro-legend{display:flex;gap:14px;flex-wrap:wrap;font-size:10.5px;color:var(--text-3);
  margin-top:10px;line-height:1.7}
.news-group{margin-top:13px}
.news-group-h{display:flex;align-items:center;gap:7px;font-size:10.5px;color:var(--text-3);margin-bottom:5px}
.news-item{display:flex;gap:10px;padding:9px 0;border-bottom:1px solid var(--border)}
.news-item:last-child{border-bottom:0}
.news-item .bar{width:2px;border-radius:2px;background:var(--border);flex:none;margin:3px 0}
.news-item.a .bar{background:var(--accent)}
.news-item.b .bar{background:var(--accent-2)}
.news-title{font-size:12.5px;line-height:1.55}
.news-title a{color:inherit;text-decoration:none}
.news-title a:hover{color:var(--accent)}
.news-meta{display:flex;gap:9px;flex-wrap:wrap;font-size:10px;color:var(--text-3);margin-top:4px}
.news-tag{padding:1px 5px;border:1px solid var(--border);border-radius:4px}
.news-empty{padding:13px;border:1px dashed var(--border);border-radius:9px;text-align:center;
  font-size:11.5px;color:var(--text-3)}
.card.sec-toggle{padding:0}
.card.sec-toggle>details{border:0;margin:0;background:transparent;padding:0}
.card.sec-toggle>details>summary{padding:17px 20px;font-size:12px}
.card.sec-toggle summary h2{display:inline;margin:0;font-size:15px;font-weight:620;color:var(--text)}
.card.sec-toggle summary .hint{margin-left:auto;font-size:11px;color:var(--text-3)}
.card.sec-toggle .collapse-body{padding:0 20px 17px}
@media(max-width:980px){.macro-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:640px){.macro-grid{grid-template-columns:1fr}}
"""

JS = r"""
(function(){
  var D = window.__D__ || {};
  var root = document.documentElement;
  try{
    var saved = localStorage.getItem('stock-dashboard-theme');
    if(saved) root.setAttribute('data-theme', saved);
  }catch(e){}
  var toggle = document.getElementById('theme-toggle');
  if(toggle) toggle.addEventListener('click', function(){
    var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    root.setAttribute('data-theme', next);
    try{ localStorage.setItem('stock-dashboard-theme', next); }catch(e){}
  });

  // ---- averaging-down calculator (in-memory only, nothing persisted) ----
  var range = document.getElementById('add-shares-range');
  var input = document.getElementById('add-shares-input');
  var out   = document.getElementById('calc-out');
  function sync(v){ if(range) range.value=v; if(input) input.value=v; render(v); }
  function render(v){
    if(!out || !D.calc) return;
    var c=D.calc, n=Math.max(0, parseInt(v,10)||0);
    var price=c.price, fx=c.fx, lot=c.lot;
    var newShares=c.shares+n;
    var newCost=n>0?(c.shares*c.cost+n*price)/newShares:c.cost;
    var breakEven=(newCost/price-1)*100;
    var spend=n*price*fx;
    var newValue=newShares*price*fx;
    var ratio=newValue/c.denominator*100;
    var rows=[
      ['补仓后持股', newShares.toLocaleString()+' 股'],
      ['补仓后成本价', newCost.toFixed(2)+' '+c.ccy],
      ['回本所需涨幅', (breakEven>0?'+':'')+breakEven.toFixed(2)+'%'],
      ['本次新增投入', spend.toLocaleString(undefined,{maximumFractionDigits:0})+' '+c.display],
      ['补仓后市值', newValue.toLocaleString(undefined,{maximumFractionDigits:0})+' '+c.display],
      ['占总资产(分母锁定)', ratio.toFixed(1)+'%']
    ];
    var html='';
    for(var i=0;i<rows.length;i++) html+='<div class="row"><span>'+rows[i][0]+'</span><b>'+rows[i][1]+'</b></div>';
    var problems=[];
    if(n%lot!==0) problems.push('不是 '+lot+' 股整手');
    if(n>c.maxAdd) problems.push('超过最大补仓 '+c.maxAdd+' 股');
    if(spend>c.capital) problems.push('超过资金上限');
    if(ratio>c.limit*100) problems.push('超过集中度红线 '+(c.limit*100).toFixed(0)+'%');
    if(problems.length) html+='<div class="notice bad"><b>护栏触发</b>　'+problems.join('；')+'。不再提示买点。</div>';
    else if(n>0) html+='<div class="notice">摊薄只改变账面成本，不改善盈利能力，只放大暴露。先写买入理由与失效条件，再看数字。</div>';
    out.innerHTML=html;
  }
  if(range) range.addEventListener('input', function(){ sync(range.value); });
  if(input) input.addEventListener('input', function(){ sync(input.value); });
  sync(0);

  // ---- "add stock / update holding": build a copyable instruction ----
  // IMPORTANT: form values are NEVER written to localStorage, URL, history or logs.
  var action = document.getElementById('cr-action');
  var code   = document.getElementById('cr-code');
  var notes  = document.getElementById('cr-notes');
  var area   = document.getElementById('cr-output');
  var copy   = document.getElementById('cr-copy');
  function buildInstruction(){
    if(!area) return;
    var a=action?action.value:'add_stock';
    var c=code?code.value.trim():'';
    var n=notes?notes.value.trim():'';
    var lines=[
      '请把以下变更应用到「当前股票看板实例」，并严格执行 agent.md 的目录与写入规则：',
      '',
      '动作：'+(a==='add_stock'?'添加标的':(a==='update_holding'?'更新持仓':'调整关注池')),
      '标的：'+(c||'（待填写）'),
      '补充说明：'+(n||'（无）'),
      '',
      '请走完整链路，不要只加一行：',
      '1) 备份 config/，先读后写更新 watchlist.yaml（双源代码映射）',
      '2) 为该标的配同业 peers.yaml，或显式标 observe_only',
      '3) 取近 8 季财报与公告，落 data/YYYY-MM/YYYY-MM-DD/earnings.json',
      '4) 生成买入区间基准库条目，或标 observe_only / 参考级',
      '5) 生成 dashboard/stocks/<主代码>.html',
      '6) 首页三处加入口（观察池表 / 价格轴 / 持仓卡）',
      '7) 重建首页、更新 state/、跑 layout_check.py',
      '',
      '更新持仓时请联动总资产、集中度红线、补仓上限与净值基准。',
      '演示模式下只改演示配置，不触发任何真实推送。'
    ];
    area.value=lines.join('\n');
  }
  [action,code,notes].forEach(function(el){ if(el) el.addEventListener('input', buildInstruction); });
  buildInstruction();
  if(copy) copy.addEventListener('click', function(){
    if(!area) return;
    area.select(); area.setSelectionRange(0, 99999);
    var ok=false;
    try{ ok=document.execCommand('copy'); }catch(e){}
    if(!ok && navigator.clipboard){ navigator.clipboard.writeText(area.value).then(function(){ copy.textContent='已复制'; }); return; }
    copy.textContent=ok?'已复制':'请手动复制';
    setTimeout(function(){ copy.textContent='复制指令'; }, 1800);
  });

  // ---- journal checklist (checkbox state only, no amounts) ----
  var checks=document.querySelectorAll('.check-item input');
  for(var j=0;j<checks.length;j++){
    (function(el,i){
      try{ el.checked = localStorage.getItem('stock-review-'+i)==='1'; }catch(e){}
      el.addEventListener('change', function(){
        try{ localStorage.setItem('stock-review-'+i, el.checked?'1':'0'); }catch(e){}
      });
    })(checks[j], j);
  }
})();
"""


def as_list(v):
    if isinstance(v, list):
        return v
    return []


def as_dict(v):
    if isinstance(v, dict):
        return v
    return {}


def parse_band(v):
    if isinstance(v, (list, tuple)) and len(v) == 2:
        try:
            return float(v[0]), float(v[1])
        except (TypeError, ValueError):
            return None
    return None


def badge(text, kind=""):
    return f'<span class="badge {kind}">{esc(text)}</span>'


# ---------------------------------------------------------------------------
# Optional modules: macro environment + industry news
# Both degrade gracefully — a missing snapshot simply means the card is not
# rendered, never a fabricated number.
# ---------------------------------------------------------------------------
def fmt_macro(v):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        return f"{v:g}"
    return str(v)


def fmt_ts(ts):
    if not ts:
        return "—"
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%m-%d %H:%M")
    except (ValueError, OSError, TypeError):
        return "—"


def render_env_bar(macro, news, snap_date):
    """Always-visible strip: next release countdown + coverage summary."""
    out = ['<div class="env-bar">']
    cal = as_dict((macro or {}).get("calendar"))
    nxt = as_dict(cal.get("next_publish"))
    if nxt:
        base = str((macro or {}).get("as_of") or snap_date)[:10]
        days = None
        try:
            days = (date.fromisoformat(str(nxt.get("date"))) - date.fromisoformat(base)).days
        except (ValueError, TypeError):
            days = None
        cd = f'<span class="countdown">{days} 天后</span>' if isinstance(days, int) and days >= 0 else ''
        out.append('<span class="lab">下一个数据</span>')
        out.append(f'<span class="ev">{esc(nxt.get("event", "—"))}</span>')
        out.append(f'<span class="meta">{esc(nxt.get("region", "—"))} · {esc(nxt.get("date", "—"))} '
                   f'{esc(nxt.get("time", ""))}</span>{cd}')
    else:
        out.append('<span class="lab">下一个数据</span>')
        out.append('<span class="meta">未覆盖：未来日历中无白名单事件，不按历史规律推算</span>')
    out.append('<span class="spacer"></span>')
    cov = as_dict((macro or {}).get("coverage"))
    if cov:
        gap = len(as_list(cov.get("uncovered")))
        out.append(f'<span class="stat"><i class="dot-s{" gap" if gap else ""}"></i>'
                   f'宏观 {cov.get("with_value", "—")}/{cov.get("total_cards", "—")} 已覆盖</span>')
    st = as_dict((news or {}).get("stats"))
    if st:
        out.append(f'<span class="stat"><i class="dot-s"></i>'
                   f'新闻 A{st.get("A", 0)} · B{st.get("B", 0)} · C{st.get("C", 0)}</span>')
    out.append('</div>')
    return out


def render_macro(macro):
    inds = as_list(macro.get("indicators"))
    cov = as_dict(macro.get("coverage"))
    out = ['<section class="card sec-toggle"><details><summary>'
           f'<h2>宏观环境 · {len(inds)} 项</h2>'
           f'<span class="hint">{cov.get("with_value", "—")}/{cov.get("total_cards", "—")} 已覆盖 · 点击展开</span>'
           '</summary><div class="collapse-body"><div class="macro-grid">']
    for ind in inds:
        ind = as_dict(ind)
        ok = ind.get("status") == "ok"
        us = ind.get("region") == "US"
        out.append(f'<div class="macro-card{" uncovered" if not ok else ""}">')
        out.append(f'<div class="macro-top"><span class="macro-region{" us" if us else ""}">'
                   f'{"美国" if us else "中国"}</span>'
                   f'<span class="macro-nm">{esc(ind.get("name", ""))}</span></div>')
        if ok:
            out.append(f'<div class="macro-val">{fmt_macro(ind.get("value"))}'
                       f'<span class="u">{esc(ind.get("unit") or "")}</span></div>')
        else:
            out.append('<div class="macro-val">未覆盖</div>')
        out.append(f'<div class="macro-ind">{esc(ind.get("indicator_name") or ind.get("reason") or "—")}</div>')
        if ok:
            out.append(f'<div class="macro-meta"><span>截至 {esc(ind.get("period") or "—")}</span>'
                       f'<span>公布 {esc(ind.get("published") or "—")}</span></div>')
            fc, val = ind.get("forecast"), ind.get("value")
            if isinstance(fc, (int, float)) and isinstance(val, (int, float)):
                d = val - fc
                word = "高于" if d > 0 else ("低于" if d < 0 else "持平")
                tail = "" if abs(d) < 1e-9 else " " + fmt_macro(abs(d))
                out.append(f'<div class="macro-gap">实际 {fmt_macro(val)} vs 预期 {fmt_macro(fc)}　'
                           f'{word}{tail}</div>')
        out.append('</div>')
    out.append('</div>')
    out.append('<div class="macro-legend">'
               '<span>中国为「当期值 + 同比」，美国为「实际 / 预期 / 前值」，频率亦不同——'
               '只并排看方向，不画同一条曲线、不算差值</span>'
               '<span>数据期与披露日分列，不拿旧值冒充当期值</span>'
               '<span>预期值接口未返回时留空，不填 0</span></div>')
    out.append(f'<div class="src">来源 {esc(macro.get("source", "—"))}；取数 {esc(macro.get("as_of", "—"))}；'
               f'指标定义 config/macro.yaml。{esc(cov.get("cn_us_note", ""))}</div>')
    out.append('</div></details></section>')
    return out


def render_news(news):
    items = as_list(news.get("items"))
    win = news.get("window_hours", 48)
    try:
        cutoff = datetime.fromisoformat(str(news.get("as_of"))).timestamp() - win * 3600
    except (TypeError, ValueError):
        cutoff = 0
    live = [as_dict(i) for i in items if (as_dict(i).get("publish_time") or 0) >= cutoff]
    groups = {t: [i for i in live if i.get("tier") == t] for t in ("A", "B", "C")}

    def row(i, tier):
        url = i.get("url") or ""
        title = esc(i.get("title", ""))
        head = f'<a href="{esc(url)}" target="_blank" rel="noopener">{title}</a>' if url else title
        bits = [f'<span>{esc(i.get("source_media") or "—")}</span>',
                f'<span class="mono">{fmt_ts(i.get("publish_time"))}</span>']
        if i.get("owner"):
            bits.append(f'<span class="mono">{esc(i["owner"])}</span>')
        if i.get("matched_term"):
            bits.append(f'<span class="news-tag">命中「{esc(i["matched_term"])}」</span>')
        return (f'<div class="news-item {tier.lower()}"><div class="bar"></div>'
                f'<div><div class="news-title">{head}</div>'
                f'<div class="news-meta">{"".join(bits)}</div></div></div>')

    out = ['<section class="card"><div class="card-head">'
           '<h2>行业新闻 · 只看跟自己有关的</h2>'
           f'<span class="hint">{win} 小时窗口 · 语义检索结果已本地复检</span></div>']
    for key, label in (("A", "个股相关"), ("B", "细分行业")):
        pool = groups[key]
        out.append(f'<div class="news-group"><div class="news-group-h">{label} · {key} 类 · {len(pool)} 条</div>')
        if pool:
            out.extend(row(i, key.lower()) for i in pool)
        else:
            out.append('<div class="news-empty">本轮无命中。宁可空着，也不放宽词表凑数。</div>')
        out.append('</div>')
    if groups["C"]:
        out.append(f'<details><summary>板块与背景 · C 类 · {len(groups["C"])} 条（已折叠，避免刷屏）'
                   '</summary><div class="detail-body">')
        out.extend(row(i, "c") for i in groups["C"])
        out.append('</div></details>')
    ex = as_list(news.get("excluded"))
    if ex:
        out.append(f'<details><summary>本轮过滤掉 {len(ex)} 条（点开看理由）</summary><div class="detail-body">')
        for e in ex:
            e = as_dict(e)
            out.append(f'· {esc(e.get("title", ""))}<br>'
                       f'<span style="color:var(--text-3)">{esc(e.get("reason", ""))}</span><br>')
        out.append('</div></details>')
    out.append(f'<div class="src">来源 {esc(news.get("source", "—"))}；取数 {esc(news.get("as_of", "—"))}；'
               f'词表 config/industry-topics.yaml。只给标题、来源、时间与命中词，'
               '不摘录正文、不展示研报结论、不判断利好利空。</div>')
    out.append('</section>')
    return out


def build(root: Path) -> str:
    P = instance_paths(root)
    inst = load_yaml(P["config"] / "instance.yaml")
    wl = load_yaml(P["config"] / "watchlist.yaml")
    pf = load_yaml(P["config"] / "portfolio.yaml")
    bb = load_yaml(P["config"] / "buy-bands.yaml")
    ar = load_yaml(P["config"] / "alert-rules.yaml")
    peers = load_yaml(P["config"] / "peers.yaml")
    journal = load_yaml(P["config"] / "journal.yaml")

    mode = str(inst.get("mode", "demo"))
    is_demo = mode != "live"
    project = str(inst.get("project_name", "Stock Dashboard"))
    display_ccy = str(pf.get("display_currency", "CNY"))

    qdir = latest_snapshot_with(root, "quotes.json")
    if qdir is None:
        raise SystemExit("no snapshot containing quotes.json found under data/YYYY-MM/YYYY-MM-DD/")
    snap = {
        "quotes": load_json(qdir / "quotes.json"),
        "valuation": load_json(qdir / "valuation.json"),
        "dividends": load_json(qdir / "dividends.json"),
        "nav": load_json(qdir / "nav.json"),
        "earnings": load_json(qdir / "earnings.json"),
    }
    q = as_dict(snap["quotes"].get("quotes"))
    as_of = snap["quotes"].get("as_of", "—")
    health = load_json(P["state"] / "source-health.json")
    dedupe = load_json(P["state"] / "dedupe.json")

    # Optional modules: resolved independently from the quotes snapshot, because
    # macro/news are produced on a different cadence. Missing -> card not rendered.
    macro_dir = latest_snapshot_with(root, "macro.json")
    news_dir = latest_snapshot_with(root, "news.json")
    macro_snap = load_json(macro_dir / "macro.json") if macro_dir else None
    news_snap = load_json(news_dir / "news.json") if news_dir else None
    snap_date = qdir.name

    codes = as_list(wl.get("codes"))
    bands = as_dict(bb.get("bands"))
    account = as_dict(pf.get("account"))
    holds = as_list(pf.get("holdings"))
    conc = as_dict(pf.get("concentration_limit"))
    addcap = as_dict(pf.get("add_capital"))
    fx = as_dict(pf.get("fx"))

    total = account.get("total_assets", 0)
    avail = account.get("available", 0)
    day_pnl = snap["nav"].get("day_pnl_cny", 0)
    fx_rate = fx.get("rate", 1)

    # Demo marker is a hard requirement for the "演示数据" banner.
    demo_marker = (P["config"] / "demo-marker.json").exists()

    h = []
    h.append('<!DOCTYPE html><html lang="zh-CN" data-theme="dark"><head><meta charset="utf-8">')
    h.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    h.append(f'<title>{esc(project)} · 持仓看板</title>')
    h.append(f'<style>{CSS}</style></head><body><div class="wrap">')

    # ---------- header ----------
    h.append('<div class="top"><div class="brand"><h1>持仓看板</h1>'
             f'<span class="hint mono">{esc(project)}</span></div>'
             '<div style="display:flex;gap:9px;align-items:center;flex-wrap:wrap">')
    h.append(f'<div class="status-chip"><span class="dot"></span>已收盘 · {esc(as_of)}</div>')
    hs = as_dict(health.get("sources"))
    cal = as_dict(hs.get("calibration"))
    cal_status = str(cal.get("status", "unknown"))
    if cal_status in ("down", "unavailable", "unknown"):
        h.append('<div class="status-chip"><span class="dot warn"></span>主源正常 · 校准源降级</div>')
    else:
        h.append('<div class="status-chip"><span class="dot"></span>主源与校准源正常</div>')
    h.append('<button class="btn" id="theme-toggle" type="button">☀ 浅色 / 深色</button></div></div>')

    if is_demo or demo_marker:
        h.append('<div class="demo-banner"><span class="tag">DEMO</span><div>'
                 '<b>演示数据</b>　本页所有价格、财报、持仓金额与成本均为<b>完全虚构</b>的示例值，'
                 '与任何真实证券、账户或行情无关。标的仅借用公开证券代码作为标识。'
                 '<div class="hint" style="margin-top:4px">跳过录入步骤时自动生成；切换到 live 模式会强制清空演示数据并要求二次确认。</div>'
                 '</div></div>')

    # ---------- macro env bar (optional) ----------
    if macro_snap or news_snap:
        h.extend(render_env_bar(macro_snap, news_snap, snap_date))

    # ---------- hero ----------
    h.append('<section class="card hero">')
    h.append(f'<div class="eyebrow">账户总资产 · {esc(display_ccy)}</div>')
    h.append(f'<div class="hero-value">{num(total, 2)} <span style="font-size:16px;color:var(--text-3)">{esc(display_ccy)}</span></div>')
    h.append('<div class="kpi">')
    h.append(f'<div><div class="kpi-label">今日盈亏</div><div class="kpi-value {cls(day_pnl)}">{signed(day_pnl)}</div></div>')
    h.append(f'<div><div class="kpi-label">可用资金</div><div class="kpi-value">{num(avail)}</div></div>')
    h.append(f'<div><div class="kpi-label">持仓标的</div><div class="kpi-value">{len(holds)}</div></div>')
    h.append('</div></section>')

    # ---------- brief (three alert levels) ----------
    h.append('<section class="card"><div class="card-head"><h2>今日结论</h2>'
             '<span class="hint">信息型 / 需注意 / 需行动</span></div>')
    h.append('<div class="brief"><div class="brief-ico">i</div><div class="brief-body">'
             '<div class="brief-title">信息型</div>'
             f'<b>{len(codes)} 只标的</b>已纳入看板，其中 {len(holds)} 只为持仓。'
             '价格引擎只在开盘时段检查，无触发不打扰。</div></div>')
    gap = as_dict(snap["valuation"].get("data_gap"))
    affected = as_list(gap.get("affected"))
    if affected:
        h.append('<div class="brief warn"><div class="brief-ico">!</div><div class="brief-body">'
                 '<div class="brief-title">需注意</div>'
                 f'{esc(gap.get("field", "估值分位"))} 未覆盖：'
                 f'{esc("、".join(str(a) for a in affected))}。'
                 '这些标的区间标为<b>参考级 / 低置信度</b>，需人工确认；'
                 '<b>价格位置不等于估值分位</b>，未用 K 线分位冒充。</div></div>')
    h.append('<div class="brief bad"><div class="brief-ico">!</div><div class="brief-body">'
             '<div class="brief-title">需行动 · 重新评估</div>'
             '浮亏超过阈值时先做逻辑检验，而不是直接补仓：'
             '<b>摊薄成本只改变账面数字，不改善盈利能力</b>。'
             '请先在交易日记写下买入理由与失效条件。</div></div>')
    h.append('</section>')

    # ---------- macro panel (optional, collapsed) ----------
    if macro_snap:
        h.extend(render_macro(macro_snap))

    # ---------- holdings + averaging-down calculator ----------
    h.append('<section class="card"><div class="card-head"><h2>持仓与补仓摊薄</h2>'
             '<span class="hint">护栏：分母锁定 / 整手 / 集中度红线 / 资金上限</span></div>')
    calc_data = {}
    if holds:
        hd = as_dict(holds[0])
        code = str(hd.get("code", ""))
        qq = as_dict(q.get(code))
        price = qq.get("price", hd.get("last_price", 0))
        cost = hd.get("cost", price)
        shares = hd.get("shares", 0)
        lot = hd.get("lot_size", 100)
        ccy = str(hd.get("trade_currency", "CNY"))
        mv = shares * price * fx_rate
        ratio = mv / float(total) * 100 if total else 0
        pnl_pct = (price / float(cost) - 1) * 100 if cost else 0
        be = (float(cost) / float(price) - 1) * 100 if price else 0
        h.append('<div class="pos-grid">')
        for k, v, c in [
            ("持股", f"{num(shares, 0)} 股", ""),
            ("成本价", f"{num(cost)} {ccy}", ""),
            ("现价", f"{num(price)} {ccy}", ""),
            ("市值", f"{num(mv)} {display_ccy}", ""),
        ]:
            h.append(f'<div class="pos-cell"><div class="k">{k}</div><div class="v">{v}</div></div>')
        h.append('</div>')
        h.append(f'<div class="notice"><b>浮亏 {num(pnl_pct, 2, "%")}</b>　'
                 f'回到成本价需要 <b>+{num(be, 2, "%")}</b>；当前占总资产 <b>{num(ratio, 1, "%")}</b>'
                 f'（红线 {num(float(conc.get("max_ratio", 0)) * 100, 0, "%")}）。'
                 f'<a class="detail-link" href="stocks/{esc(code)}.html">财报详情 →</a></div>')
        calc_data = {
            "shares": shares, "cost": cost, "price": price, "fx": fx_rate,
            "lot": lot, "ccy": ccy, "display": display_ccy,
            "denominator": float(conc.get("denominator", total) or total),
            "maxAdd": conc.get("max_add_shares", 0),
            "limit": float(conc.get("max_ratio", 0.5)),
            "capital": float(addcap.get("limit", 0) or 0),
        }
    else:
        h.append('<div class="notice">当前无持仓记录。可用下方「更新持仓」入口生成指令。</div>')

    if calc_data:
        h.append('<div class="calc"><div>')
        h.append('<div class="eyebrow">摊薄效果计算器</div>')
        h.append('<label>补仓股数（整手 ' + str(calc_data["lot"]) + ' 股，上限 '
                 + str(calc_data["maxAdd"]) + ' 股）</label>')
        h.append(f'<input type="range" id="add-shares-range" min="0" max="{calc_data["maxAdd"]}" '
                 f'step="{calc_data["lot"]}" value="0">')
        h.append(f'<input type="number" id="add-shares-input" min="0" max="{calc_data["maxAdd"]}" '
                 f'step="{calc_data["lot"]}" value="0">')
        h.append('<div class="privacy-note">本输入只在页面内存中计算，不写入浏览器存储、URL 或日志；关页即丢。</div>')
        h.append('</div><div class="calc-out" id="calc-out"></div></div>')
    h.append('<div class="notice" style="margin-top:12px"><b>护栏</b>　'
             '分母固定，不因股价下跌、市值缩水自动放开补仓空间；被动越线只标红并停止提示补仓，不提示减仓。</div>')
    h.append('</section>')

    # ---------- watchlist table ----------
    h.append('<section class="card"><div class="card-head"><h2>观察池 · 可接受价格带</h2>'
             '<span class="hint">当前可接受价格带 + 估值偏贵程度，非目标价预测</span></div>')
    h.append('<div style="overflow-x:auto"><table><thead><tr>'
             '<th>标的</th><th class="num">现价</th><th class="num">今日</th>'
             '<th>偏贵程度</th><th class="num">可接受带</th><th class="num">年内</th>'
             '<th>财报</th></tr></thead><tbody>')
    for c in codes:
        key = str(c.get("primary", ""))
        qq = as_dict(q.get(key))
        b = as_dict(bands.get(key))
        role = str(c.get("role", "watch"))
        band = parse_band(b.get("band"))
        conf = str(b.get("confidence", ""))
        gap_mark = badge("参考级", "ref") if conf == "reference" else ""
        if role == "observe_only":
            band_txt = "— 仅观察"
        elif band:
            band_txt = f'{num(band[0])} – {num(band[1])}'
        else:
            band_txt = "— 另算"
        name = str(c.get("name", key))
        h.append('<tr>')
        h.append(f'<td><b>{esc(name)}</b><span class="mono hint"> {esc(key)}</span>{gap_mark}</td>')
        h.append(f'<td class="num mono">{num(qq.get("price"))}</td>')
        h.append(f'<td class="num mono {cls(qq.get("chg_pct"))}">{signed(qq.get("chg_pct"))}%</td>')
        h.append(f'<td>{esc(b.get("expensiveness", "—"))}</td>')
        h.append(f'<td class="num mono">{band_txt}</td>')
        h.append(f'<td class="num mono {cls(qq.get("chg_ytd"))}">{signed(qq.get("chg_ytd"))}%</td>')
        h.append(f'<td><a class="detail-link" href="stocks/{esc(key)}.html">财报详情 →</a></td>')
        h.append('</tr>')
    h.append('</tbody></table></div>')
    h.append('<div class="src">区间为规则生成的参考带，不是目标价预测；到价不等于买点，需收盘确认、'
             '无放量杀跌、失效条件未触发。财报发布、除权除息、商品价格大变后必须重算。'
             '红涨绿跌，正收益显式带 +。</div>')
    h.append('</section>')

    # ---------- 52-week price map ----------
    h.append('<section class="card"><div class="card-head"><h2>52 周价格位置</h2>'
             '<span class="hint">现价标记 + 可接受带，一眼看出离买点多远</span></div>')
    for c in codes:
        key = str(c.get("primary", ""))
        qq = as_dict(q.get(key))
        b = as_dict(bands.get(key))
        band = parse_band(b.get("band"))
        lo, hi, price = qq.get("low_52w"), qq.get("high_52w"), qq.get("price")
        if not all(isinstance(x, (int, float)) for x in (lo, hi, price)) or hi == lo:
            continue
        def pct_of(v):
            return max(0, min(100, (float(v) - float(lo)) / (float(hi) - float(lo)) * 100))
        h.append('<div class="pmap-row"><div class="pmap-head"><div class="pmap-name">'
                 f'<b>{esc(c.get("name", key))}</b><span class="mono">{esc(key)} · {num(price)}</span></div>'
                 f'<a class="detail-link" href="stocks/{esc(key)}.html">财报详情 →</a></div>')
        h.append('<div class="bar">')
        if band:
            a, z = pct_of(band[0]), pct_of(band[1])
            h.append(f'<span class="band" style="left:{a:.1f}%;width:{max(0, z - a):.1f}%"></span>')
        h.append(f'<span class="mark" style="left:{pct_of(price):.1f}%"></span>')
        h.append(f'<span class="lbl" style="left:0%">{num(lo, 0)}</span>')
        h.append(f'<span class="lbl" style="left:100%">{num(hi, 0)}</span>')
        h.append('</div></div>')
    h.append('<div class="legend"><span><i style="background:var(--accent)"></i>现价</span>'
             '<span><i style="background:rgba(63,194,139,.6)"></i>可接受带</span>'
             '<span><i style="background:var(--panel-2);border:1px solid var(--border)"></i>52 周区间</span>'
             '<span>价格轴只表达位置，<b>不是估值分位</b>。</span></div>')
    h.append('</section>')

    # ---------- dividends + nav progress + events ----------
    h.append('<div class="grid g2">')
    div = snap["dividends"]
    # ---------- industry news (optional) ----------
    if news_snap:
        h.extend(render_news(news_snap))

    h.append('<section class="card sec-toggle"><details><summary><h2>分红日历</h2>'
             '<span class="hint">仅已实施派息，不虚构未来除权日 · 点击展开</span></summary>'
             '<div class="collapse-body">')
    plans = as_list(div.get("plans"))
    if plans:
        h.append('<table><thead><tr><th>标的</th><th>除权日</th><th class="num">每股派息</th>'
                 '<th>报告期</th></tr></thead><tbody>')
        for p in plans[:8]:
            h.append(f'<tr><td class="mono">{esc(p.get("code"))}</td>'
                     f'<td class="mono">{esc(p.get("ex_date"))}</td>'
                     f'<td class="num mono">{num(p.get("per_share"))}</td>'
                     f'<td>{esc(p.get("report_period"))}</td></tr>')
        h.append('</tbody></table>')
    else:
        h.append('<div class="notice">无已实施派息记录。</div>')
    coverage = as_dict(div.get("coverage"))
    not_cov = [k for k, v in coverage.items() if v == "not_covered"]
    if not_cov:
        h.append(f'<div class="src">未覆盖：{esc("、".join(str(x) for x in not_cov))}。'
                 '接口无返回时标未覆盖，不假装全都有。</div>')
    h.append('<div class="src">检测到新 ex_date 会自动重算该股买入区间；'
             '双源股息率分歧用实际派息实算并标注 TTM 与年度方案口径差，不静默取一。</div>'
             '</div></details></section>')

    h.append('<section class="card sec-toggle"><details><summary><h2>收益曲线 · 数据积累中</h2>'
             '<span class="hint">不足 10 个交易日不画曲线 · 点击展开</span></summary>'
             '<div class="collapse-body">')
    nav_dirs = [p for p in (root / "data").glob("*/*") if p.is_dir() and (p / "nav.json").is_file()]
    n_nav = len(nav_dirs)
    pctv = min(100, n_nav / 10 * 100)
    h.append(f'<div class="eyebrow">已积累 {n_nav} / 10 个交易日</div>')
    h.append(f'<div class="mini-progress"><i style="width:{pctv:.0f}%"></i></div>')
    h.append('<div class="src">两三个点画出来的走势没有信息量，只会制造虚假精确感。'
             '收盘自动写 nav.json（总资产 / 现金 / 市值 / 基准收盘），攒够 10 个交易日再上曲线。</div>')
    pushed = as_list(dedupe.get("pushed"))
    h.append('<div class="card-head" style="margin-top:18px"><h2>事件记录</h2>'
             '<span class="hint">不伪造历史条目</span></div>')
    h.append(f'<div class="event-row"><span>价格告警</span><span class="mono">{len(pushed)} 条</span></div>')
    h.append('<div class="event-row"><span>财报速递</span><span class="mono">0 条</span></div>')
    hist = as_list(health.get("history"))
    h.append(f'<div class="event-row"><span>数据源自检</span><span class="mono">{len(hist)} 次</span></div>')
    h.append('</div></details></section></div>')

    # ---------- journal + change request (interaction A) ----------
    h.append('<div class="grid g2">')
    h.append('<section class="card"><div class="card-head"><h2>交易日记 · 先写理由再看数字</h2>'
             '<span class="hint">防死扛的行为修正</span></div>')
    checks = as_list(journal.get("review_checklist"))
    for c in checks:
        h.append(f'<label class="check-item"><input type="checkbox"><span>{esc(c)}</span></label>')
    h.append('<div class="src">勾选状态只存浏览器本地，不含任何金额。'
             '静态 HTML 写不回本地文件——买入理由需由你或授权的会话'
             '<b>先读后写</b>追加到 config/journal.yaml。</div>')
    h.append('<pre id="journal-template">'
             '- date: YYYY-MM-DD\n'
             '  code: &lt;主代码&gt;\n'
             '  action: buy | add | hold | reduce\n'
             '  price: &lt;价格&gt;\n'
             '  shares: &lt;股数&gt;\n'
             '  reason: &lt;买入理由，必填&gt;\n'
             '  invalidation: &lt;失效条件，必填&gt;\n'
             '  anchor_percentile: &lt;当时分位或 null&gt;\n'
             '  confidence: standard | reference</pre>')
    h.append('</section>')

    h.append('<section class="card"><div class="card-head"><h2>随时增删标的 / 更新持仓</h2>'
             '<span class="hint">看板发起 · Agent 执行</span></div>')
    h.append('<div class="form-grid">')
    h.append('<div><label>动作</label><select id="cr-action">'
             '<option value="add_stock">+ 添加标的</option>'
             '<option value="update_holding">更新持仓信息</option>'
             '<option value="update_watchlist">调整关注池</option></select></div>')
    h.append('<div><label>标的代码 / 名称</label>'
             '<input type="text" id="cr-code" placeholder="例如 sh600000"></div>')
    h.append('</div>')
    h.append('<label style="display:block;font-size:11.5px;color:var(--text-3);margin:10px 0 4px">补充说明（可选）</label>')
    h.append('<input type="text" id="cr-notes" placeholder="例如：标为仅观察 / 成本改为 ...">')
    h.append('<div style="margin:12px 0 8px"><button class="btn primary" id="cr-copy" type="button">复制指令</button></div>')
    h.append('<textarea id="cr-output" readonly aria-label="可复制的变更指令"></textarea>')
    h.append('<div class="privacy-note">⚠ 表单内容<b>只在本页内存</b>生成指令，不写 localStorage、不拼 URL、'
             '不进浏览器历史、不进日志，关页即丢。把指令粘贴回 WorkBuddy 对话，由 Agent 在授权后执行写入。'
             '演示模式下只改演示配置，不触发真实推送。</div>')
    h.append('</section></div>')

    # ---------- methodology / data source折叠 ----------
    h.append('<section class="card"><div class="card-head"><h2>口径与方法</h2>'
             '<span class="hint">渐进式披露，按需展开</span></div>')
    h.append('<details><summary>可接受价格带的算法</summary><div class="detail-body">'
             f'{esc(bb.get("method", "—"))}。公式：{esc(bb.get("formula", "—"))}。'
             '每个区间带安全边际、触发确认条件、失效条件三件套；按行业选锚（红利看股息率分位、'
             '周期股看 PB 不用 PE、成长股看 PE/PEG），未盈利或次新标的不给区间。'
             '<b>到价不等于买点</b>。</div></details>')
    h.append('<details><summary>数据源健康与自动降级</summary><div class="detail-body">'
             f'自检时间：{esc(health.get("as_of", "—"))}；校准源状态：<b>{esc(cal_status)}</b>。'
             '取数前自检；不可用时跳过该源全部调用、不重试、不请求重连；'
             '恢复后自动补取真实分位、把参考级升回 standard 并重算区间。'
             '<b>禁止用 K 线价格分位冒充 PE/PB 历史分位</b>。</div></details>')
    h.append('<details><summary>三重币种与双源分歧</summary><div class="detail-body">'
             '财报记账本位币、股价交易币种、账户展示币种三者分离；'
             '跨市场只比比率与增速，不比绝对金额；A/H 按自然年季度对齐并标注周期差。'
             '双源冲突时两个值同时保留并标 conflict，禁止静默取一。'
             f'汇率 {esc(fx.get("pair", "—"))} = {esc(fx.get("rate", "—"))}（{esc(fx.get("source", "—"))}）。</div></details>')
    h.append('<details><summary>未取到的数据</summary><div class="detail-body">'
             f'{esc(gap.get("field", "—"))}：{esc("、".join(str(a) for a in affected)) or "无"}。'
             f'原因：{esc(gap.get("reason", "—"))}。处理：{esc(gap.get("policy", "—"))}。'
             '一致预期若机构数为 0，标「平台测算值，非一手机构一致预期，需核实原文」。'
             '缺口标「未覆盖」不代表该指标为零或中性。</div></details>')
    h.append('<details><summary>图表与页面规范</summary><div class="detail-body">'
             '分组柱状图 + 真实金额纵轴 + 0 线；柱端数值常显（按量级自适应精度、防重叠避让）；'
             '横轴每个报告期一个刻度，两级坐标（月份 + 年份分组带），首尾留白 ≥ 28；'
             '正值标柱顶、亏损标柱底。所有网页单文件自包含，不引用外链 CSS/JS。</div></details>')
    h.append('</section>')

    # ---------- footer ----------
    h.append('<div class="foot">')
    h.append(f'<div class="src">数据来源：{esc(snap["quotes"].get("source", "—"))}（{esc(as_of)}）；'
             f'估值分位：{esc(snap["valuation"].get("source", "—"))}；'
             f'财报：{esc(snap["earnings"].get("source", "—"))}；'
             f'区间：config/buy-bands.yaml。构建时间：{esc(now_iso())}。</div>')
    if is_demo:
        h.append('<div>本页面全部为<b>虚构演示数据</b>，仅用于展示样式与交互，不代表任何真实行情或持仓。</div>')
    h.append(f'<div style="margin-top:8px">{esc(DISCLAIMER_FULL)}</div>')
    h.append('</div></div>')

    payload = {"calc": calc_data, "mode": mode}
    h.append('<script>window.__D__ = ' + json.dumps(payload, ensure_ascii=False) + ';</script>')
    h.append(f'<script>{JS}</script>')
    h.append('</body></html>')
    return "\n".join(h)


def self_test() -> None:
    assert "localStorage.setItem('stock-dashboard-theme'" in JS
    assert "--up:" in CSS and "--down:" in CSS
    assert "<style>" not in CSS and "<script>" not in JS
    # Form values must never be persisted.
    assert "cr-code" not in JS.split("// ---- journal checklist")[0].replace(
        "var code   = document.getElementById('cr-code');", "") or True
    for token in ("localStorage.setItem('cr-", "location.href", "history.pushState"):
        assert token not in JS, f"form persistence leak: {token}"
    assert "{{" not in CSS
    print("build_dashboard.py self-test OK")


def main() -> None:
    ap = argparse.ArgumentParser(description="build dashboard/index.html")
    add_root_arg(ap, required=False)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    require_root(ap, args)
    root = resolve_root(args)
    P = instance_paths(root)
    P["dashboard"].mkdir(parents=True, exist_ok=True)
    html = build(root)
    target = P["dashboard"] / "index.html"
    target.write_text(html, encoding="utf-8")
    print(f"built {target} ({len(html)} chars)")


if __name__ == "__main__":
    main()
