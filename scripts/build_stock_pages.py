"""Build one self-contained financial-report page per watched ticker.

Reads local data/YYYY-MM/YYYY-MM-DD/earnings.json plus config/peers.yaml.
Outputs dashboard/stocks/<primary-code>.html (fixed path, overwritten).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import (
    add_root_arg, require_root, resolve_root, instance_paths, load_yaml, load_json,
    latest_snapshot_with, esc, num, signed, cls, now_iso,
    DISCLAIMER_FULL,
)

CSS = r"""
:root{
  --bg:#0f141c; --panel:#182130; --panel-2:#1d2737; --border:#2a3648;
  --text:#e8eef7; --text-2:#aab8cc; --text-3:#7d8ca3;
  --accent:#5b9cff; --warn:#f0a94b; --bad:#ef6b6b;
  --up:#f0616b; --down:#3fc28b; --ok:#3fc28b;
  --mono:"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
}
html[data-theme="light"]{
  --bg:#f5f7fb; --panel:#fff; --panel-2:#f3f6fb; --border:#dde4ef;
  --text:#1b2433; --text-2:#4c5b70; --text-3:#7a879a;
  --accent:#2f6fd0; --warn:#c07a18; --bad:#d04545;
  --up:#d63a48; --down:#159a6b; --ok:#159a6b;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-size:14px;line-height:1.6;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:24px 20px 60px}
.mono,.num{font-family:var(--mono);font-variant-numeric:tabular-nums}
.num{text-align:right}
.up{color:var(--up)}.down{color:var(--down)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
h1{font-size:22px;margin:0}h2{font-size:16px;margin:0}h3{font-size:13px;margin:0}
.eyebrow{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--text-3);font-weight:700}
.hint{font-size:12px;color:var(--text-3);font-weight:400}
.src{font-size:11.5px;color:var(--text-3);margin-top:10px;line-height:1.75}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap}
.btn{border:1px solid var(--border);background:var(--panel);color:var(--text-2);border-radius:9px;
  padding:7px 12px;font-size:12px;cursor:pointer;font-family:inherit}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.back-link{font-size:12.5px}
.banner{padding:12px 15px;border-radius:11px;border:1px solid #6a5320;
  background:rgba(240,169,75,.12);color:var(--warn);font-size:12.5px;margin-bottom:14px}
.banner b{color:var(--warn)}
.card{background:var(--panel);border:1px solid var(--border);border-radius:14px;
  padding:18px 20px;margin-bottom:15px;box-shadow:0 6px 24px rgba(0,0,0,.18)}
.card-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;
  margin-bottom:14px;flex-wrap:wrap}
.meta{display:flex;gap:9px;flex-wrap:wrap;margin-top:10px}
.chip{font-size:11.5px;padding:4px 10px;border-radius:999px;background:var(--panel-2);
  border:1px solid var(--border);color:var(--text-2)}
.chip.warn{color:var(--warn);border-color:rgba(240,169,75,.4)}
.conclusion{padding:14px 16px;border-radius:11px;background:var(--panel-2);
  border:1px solid var(--border);font-size:13.5px;line-height:1.85}
.conclusion b{color:var(--accent)}
.kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:14px}
.kpi-cell{background:var(--panel-2);border:1px solid var(--border);border-radius:10px;padding:11px 13px}
.kpi-cell .k{font-size:11px;color:var(--text-3)}
.kpi-cell .v{font-family:var(--mono);font-size:18px;font-weight:650;margin-top:2px}
.kpi-cell .s{font-size:11px;color:var(--text-3);margin-top:2px}
@media(max-width:760px){.kpi-grid{grid-template-columns:repeat(2,1fr)}}
select{padding:8px 11px;border-radius:9px;border:1px solid var(--border);
  background:var(--panel-2);color:var(--text);font-family:var(--mono);font-size:13px}
.trend-wrap{background:var(--panel-2);border-radius:12px;padding:14px;margin-top:12px;overflow-x:auto}
.trend-svg{width:100%;min-width:520px;height:auto;display:block}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:11.5px;color:var(--text-3);margin-top:8px}
.legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{font-size:11px;color:var(--text-3);text-align:left;padding:8px 7px;
  border-bottom:1px solid var(--border);white-space:nowrap}
td{padding:9px 7px;border-bottom:1px solid var(--border)}
tr:last-child td{border-bottom:0}
th.num,td.num{text-align:right}
.notice{padding:11px 13px;border-radius:9px;background:rgba(91,156,255,.08);
  border:1px solid rgba(91,156,255,.28);font-size:12px;color:var(--text-2);margin-top:10px}
.notice.warn{background:rgba(240,169,75,.08);border-color:rgba(240,169,75,.3)}
details{border:1px solid var(--border);border-radius:10px;padding:10px 13px;
  margin-bottom:9px;background:var(--panel-2)}
summary{cursor:pointer;font-size:12.5px;font-weight:600;color:var(--text-2)}
.detail-body{font-size:12px;color:var(--text-2);padding-top:9px;line-height:1.8}
ul{margin:6px 0 0;padding-left:18px}li{margin:3px 0}
.foot{margin-top:24px;padding-top:15px;border-top:1px solid var(--border);
  font-size:11.5px;color:var(--text-3);line-height:1.8}
"""

JS = r"""
(function(){
  var D=window.__D__||{}, P=D.periods||[];
  var root=document.documentElement;
  try{ var t=localStorage.getItem('stock-dashboard-theme'); if(t) root.setAttribute('data-theme',t); }catch(e){}
  var toggle=document.getElementById('theme-toggle');
  if(toggle) toggle.addEventListener('click',function(){
    var n=root.getAttribute('data-theme')==='light'?'dark':'light';
    root.setAttribute('data-theme',n);
    try{localStorage.setItem('stock-dashboard-theme',n);}catch(e){}
  });
  function fmt(v,d){ if(v===null||v===undefined||v==='') return '—';
    return Number(v).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d}); }
  function compact(v){ if(v===null||v===undefined) return '—';
    var a=Math.abs(v);
    if(a>=1000) return Math.round(v).toString();
    if(a>=100) return v.toFixed(1);
    return v.toFixed(2); }
  function tick(v){ var a=Math.abs(v);
    if(a>=1000) return Math.round(v).toString();
    if(a>=100) return v.toFixed(0);
    if(a>=10) return v.toFixed(0);
    return v.toFixed(1); }

  // ---- grouped bars with REAL amounts, y-axis, 0-line, always-on value labels ----
  function renderTrend(idx){
    var svg=document.getElementById('trend-svg'); if(!svg||!P.length) return;
    var chron=P.slice().reverse(), n=chron.length, ci=n-1-idx;
    var W=620,H=224,padL=50,padR=26,padT=24,padB=50,axisY=H-padB;
    var vals=[];
    for(var q=0;q<n;q++){ ['revenue','net_profit'].forEach(function(k){
      var v=chron[q][k]; if(v!==null&&v!==undefined) vals.push(Number(v)); }); }
    var mn=Math.min.apply(null,vals.concat([0])), mx=Math.max.apply(null,vals.concat([0]));
    var span=mx-mn; if(span<=0) span=1;
    var pad=span*0.12; mn-=pad; mx+=pad; span=mx-mn;
    // nice ticks
    var raw=span/5, mag=Math.pow(10,Math.floor(Math.log(raw)/Math.LN10)), norm=raw/mag;
    var step=(norm<=1?1:norm<=2?2:norm<=2.5?2.5:norm<=5?5:10)*mag;
    var ticks=[], t0=Math.ceil(mn/step)*step;
    for(var t=t0;t<=mx+1e-9;t+=step) ticks.push(Math.abs(t)<1e-9?0:t);
    if(!ticks.length) ticks=[0];
    // Bars use a band (slot-center) layout, not a point layout: with
    // i/(n-1) the first and last bar groups spill outside the plot area.
    var gw=(W-padL-padR)/Math.max(1,n);
    function X(i){ return padL+gw*(i+0.5); }
    function Y(v){ return padT+(axisY-padT)*(1-(v-mn)/span); }
    var out=[];
    // y grid + labels
    for(var ti=0;ti<ticks.length;ti++){
      var ty=Y(ticks[ti]);
      out.push('<line x1="'+padL+'" y1="'+ty.toFixed(1)+'" x2="'+(W-padR)+'" y2="'+ty.toFixed(1)+
               '" stroke="var(--border)" stroke-width="'+(ticks[ti]===0?'1.2':'1')+'" opacity="'+(ticks[ti]===0?'1':'0.55')+'"/>');
      out.push('<text x="43" y="'+(ty+2.6).toFixed(1)+'" font-size="7.5" fill="var(--text-3)" text-anchor="end">'+tick(ticks[ti])+'</text>');
    }
    out.push('<text x="8" y="16" font-size="7.5" fill="var(--text-3)">亿元 · '+D.currency+'</text>');
    // selected-period highlight
    var hx=X(ci), half=gw*0.46;
    out.push('<rect x="'+(hx-half).toFixed(1)+'" y="'+padT+'" width="'+(half*2).toFixed(1)+
             '" height="'+(axisY-padT)+'" fill="var(--accent)" opacity="0.09" rx="4"/>');
    // bars + label collection
    var bw=Math.min(20,gw*0.30), gap=3, labels=[];
    for(var j=0;j<n;j++){
      var cx=X(j), p=chron[j], isCur=(j===ci), y0=Y(0), left=cx-bw-gap/2;
      [['revenue','var(--accent)'],['net_profit','var(--warn)']].forEach(function(pair,s){
        var val=p[pair[0]]; if(val===null||val===undefined) return;
        var y1=Y(Number(val)), top=Math.min(y0,y1), hh=Math.max(1.5,Math.abs(y1-y0));
        var bx=left+s*(bw+gap);
        out.push('<rect x="'+bx.toFixed(1)+'" y="'+top.toFixed(1)+'" width="'+bw.toFixed(1)+
                 '" height="'+hh.toFixed(1)+'" rx="2" fill="'+pair[1]+'" opacity="'+(isCur?'1':'0.82')+'"/>');
        var neg=Number(val)<0, bottom=top+hh, txt=compact(Number(val));
        var ly=neg?bottom+9:top-4;
        labels.push({x:bx+bw/2,y:ly,bottom:bottom,t:txt,w:txt.length*4.2,
                     c:pair[1],neg:neg,bold:isCur,inside:false});
      });
    }
    // collision avoidance (vertical offset), clamped inside plot
    labels.sort(function(a,b){return a.y-b.y;});
    for(var a=0;a<labels.length;a++){
      var L=labels[a], hit=null;
      for(var b=0;b<a;b++){
        var M=labels[b];
        if(Math.abs(L.x-M.x)<(L.w+M.w)/2+2 && Math.abs(L.y-M.y)<9){hit=M;break;}
      }
      if(hit) L.y=(hit.y-9.5>=padT+6)?hit.y-9.5:hit.y+9.5;
      if(L.y<padT+6){L.y=padT+6;}
      if(L.y>axisY-3){L.y=Math.max(padT+20,L.bottom-7);L.inside=true;}
    }
    for(var k=0;k<labels.length;k++){
      var Q=labels[k];
      out.push('<text x="'+Q.x.toFixed(1)+'" y="'+Q.y.toFixed(1)+'" font-size="7.5" font-weight="'+
               (Q.bold?'700':'400')+'" fill="'+Q.c+'" text-anchor="middle" stroke="var(--panel-2)" stroke-width="2" '+
               'paint-order="stroke fill">'+Q.t+'</text>');
    }
    // two-level x axis: every period gets a month tick, years grouped below
    for(var m=0;m<n;m++){
      var lx=X(m), mm=chron[m].period.slice(5,7), cur=(m===ci);
      out.push('<line x1="'+lx.toFixed(1)+'" y1="'+axisY+'" x2="'+lx.toFixed(1)+'" y2="'+(axisY+5)+
               '" stroke="var(--border)" stroke-width="1"/>');
      out.push('<text x="'+lx.toFixed(1)+'" y="'+(axisY+17)+'" font-size="8" font-weight="'+(cur?'700':'400')+
               '" fill="'+(cur?'var(--accent)':'var(--text-3)')+'" text-anchor="middle">'+mm+'</text>');
    }
    var groups=[];
    for(var g=0;g<n;g++){
      var yy=chron[g].period.slice(0,4);
      if(!groups.length||groups[groups.length-1].year!==yy) groups.push({year:yy,a:g,b:g});
      else groups[groups.length-1].b=g;
    }
    for(var r=0;r<groups.length;r++){
      var G=groups[r], xa=Math.max(padL,X(G.a)-16), xb=Math.min(W-padR,X(G.b)+16);
      out.push('<line x1="'+xa.toFixed(1)+'" y1="'+(axisY+34)+'" x2="'+xb.toFixed(1)+'" y2="'+(axisY+34)+
               '" stroke="var(--border)" stroke-width="1"/>');
      out.push('<text x="'+((xa+xb)/2).toFixed(1)+'" y="'+(axisY+46)+'" font-size="7.5" fill="var(--text-3)" text-anchor="middle">'+G.year+'</text>');
    }
    // hover is only a precision supplement, never the only way to read values
    for(var z=0;z<n;z++){
      var qx=X(z), p2=chron[z];
      var tip=p2.period+' · 营业收入 '+fmt(p2.revenue,2)+' 亿 '+D.currency+
              ' · 归母净利 '+fmt(p2.net_profit,2)+' 亿 '+D.currency;
      out.push('<rect x="'+(qx-12).toFixed(1)+'" y="'+padT+'" width="24" height="'+(axisY-padT)+
               '" fill="transparent"><title>'+tip+'</title></rect>');
    }
    svg.innerHTML=out.join('');
  }

  // ---- period switch: update KPI cards + chart ----
  function renderPeriod(idx){
    var p=P[idx]; if(!p) return;
    function set(id,v,d,suf){ var el=document.getElementById(id); if(el) el.textContent=fmt(v,d)+(suf||''); }
    set('k-rev',p.revenue,2,''); set('k-np',p.net_profit,2,'');
    set('k-rev-yoy',p.rev_yoy,2,'%'); set('k-np-yoy',p.np_yoy,2,'%');
    set('k-gross',p.gross,2,'%'); set('k-margin',p.net_margin,2,'%');
    set('k-eps',p.eps,2,''); set('k-debt',p.debt,2,'%');
    var yoy=document.getElementById('k-np-yoy');
    if(yoy){ yoy.className='v '+(Number(p.np_yoy)>0?'up':(Number(p.np_yoy)<0?'down':'')); }
    var label=document.getElementById('period-label');
    if(label) label.textContent=p.period+' · 披露 '+(p.publ||'—');
    renderTrend(idx);
  }
  var sel=document.getElementById('period-select');
  if(sel){
    sel.addEventListener('change',function(){ renderPeriod(parseInt(this.value,10)); });
    renderPeriod(0);
  }
})();
"""


def as_list(v):
    return v if isinstance(v, list) else []


def as_dict(v):
    return v if isinstance(v, dict) else {}


def conclusion_block(name, latest, conf, n_periods):
    rev_yoy = latest.get("rev_yoy")
    np_yoy = latest.get("np_yoy")
    direction = "持平"
    try:
        if float(np_yoy) > 3:
            direction = "利润增速高于营收，边际改善"
        elif float(np_yoy) < -3:
            direction = "利润同比下滑，需关注盈利质量与失效条件"
        else:
            direction = "整体持平"
    except (TypeError, ValueError):
        direction = "数据不足，不做方向判定"
    return (
        f'<div class="conclusion"><b>机器判定，需人工确认</b>　{esc(name)} 最新报告期 '
        f'<b>{esc(latest.get("period"))}</b>：营收同比 {signed(rev_yoy)}%、归母净利同比 {signed(np_yoy)}%，'
        f'{esc(direction)}。'
        f'结论基于结构化财务数字与近 {n_periods} 期趋势，'
        '不含管理层措辞与指引的语义对比（未覆盖）。'
        f'当前区间置信度：<b>{esc(conf)}</b>'
        + (" —— 参考级 / 低置信度，需人工确认，不得作为决策依据。" if conf == "reference" else "。")
        + '</div>'
    )


def build_page(root: Path, code: str, name: str, info: dict, earnings: dict,
               peers_cfg: dict, valuation: dict, bands: dict, mode: str) -> str:
    periods = as_list(info.get("periods"))
    if not periods:
        return ""
    # Snapshots are stored oldest -> newest. The newest period is the LAST item.
    # JS payload is reversed (newest first) so selector index 0 == newest.
    newest = periods[-1]
    currency = str(info.get("currency", "CNY"))
    fin_ccy_note = (
        "财报记账本位币与股价交易币种分离；本页金额单位：亿元（本币）。"
        "跨市场只比比率与增速，不比绝对金额。"
    )
    vsnap = as_dict(earnings.get("valuation_snapshot")).get(code, {})
    conf = str(vsnap.get("confidence") or as_dict(bands.get(code)).get("confidence") or "standard")
    peer_rows = as_list(as_dict(earnings.get("peers")).get(code))
    anns = as_list(as_dict(earnings.get("announcements")).get(code))
    reaction = as_dict(as_dict(earnings.get("price_reaction")).get(code))
    band = as_dict(bands.get(code))
    limitations = as_list(earnings.get("limitations"))
    is_demo = mode != "live"

    # JS payload: reverse chronological (newest first) for the selector
    payload = {"periods": list(reversed(periods)), "currency": currency, "code": code}

    h = []
    h.append('<!DOCTYPE html><html lang="zh-CN" data-theme="dark"><head><meta charset="utf-8">')
    h.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    h.append(f'<title>{esc(name)} · 财报详情</title><style>{CSS}</style></head><body><div class="wrap">')
    h.append('<div class="top"><div><a class="back-link" href="../index.html" '
             'onclick="if(document.referrer && document.referrer.indexOf(\'index.html\')>=0)'
             '{history.back();return false;}">← 返回看板</a></div>'
             '<button class="btn" id="theme-toggle" type="button">☀ 浅色 / 深色</button></div>')
    if is_demo:
        h.append('<div class="banner"><b>DEMO · 演示数据</b>　本页所有财务数字、行情与公告均为'
                 '<b>完全虚构</b>的示例值，与任何真实公司财报无关。</div>')

    h.append(f'<section class="card"><h1>{esc(name)} <span class="hint mono">{esc(code)}</span></h1>')
    h.append('<div class="meta">')
    h.append(f'<span class="chip">最新报告期 {esc(newest.get("period"))}</span>')
    h.append(f'<span class="chip">实际披露 {esc(newest.get("publ"))}</span>')
    h.append(f'<span class="chip">财报币种 {esc(currency)}</span>')
    h.append(f'<span class="chip">数据时点 {esc(earnings.get("as_of"))}</span>')
    h.append(f'<span class="chip">行情时点 {esc(earnings.get("quote_as_of"))}</span>')
    h.append(f'<span class="chip {"warn" if conf == "reference" else ""}">置信度 {esc(conf)}</span>')
    h.append(f'<span class="chip">共 {len(periods)} 期</span>')
    h.append('</div>')
    h.append(f'<div class="src">{esc(fin_ccy_note)} {esc(info.get("period_note", ""))} '
             '财报数字是各报告期历史值，行情估值是快照时点值，两者分别标注，不把盘中价当收盘价。</div>')
    h.append('</section>')

    h.append('<section class="card"><div class="card-head"><h2>一句话结论</h2>'
             '<span class="hint">规则生成，非投资建议</span></div>')
    h.append(conclusion_block(name, newest, conf, len(periods)))
    h.append('</section>')

    # ---- period switch ----
    h.append(f'<section class="card"><div class="card-head"><h2>报告期切换 · 近 {len(periods)} 期</h2>'
             '<span class="hint">切换即时更新数字卡与柱状图</span></div>')
    h.append('<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">')
    h.append('<select id="period-select">')
    # JS payload is newest-first, so option value i maps to reversed(periods)[i].
    for i, p in enumerate(reversed(periods)):
        h.append(f'<option value="{i}">{esc(p.get("period"))} · {esc(p.get("type"))}</option>')
    h.append('</select>')
    h.append(f'<span class="hint mono" id="period-label">{esc(newest.get("period"))}</span></div>')
    h.append('<div class="kpi-grid">')
    for kid, label, key, suf in [
        ("k-rev", "营业收入", "revenue", " 亿"),
        ("k-np", "归母净利", "net_profit", " 亿"),
        ("k-rev-yoy", "营收同比", "rev_yoy", "%"),
        ("k-np-yoy", "净利同比", "np_yoy", "%"),
    ]:
        v = newest.get(key)
        c = cls(v) if key.endswith("yoy") else ""
        h.append(f'<div class="kpi-cell"><div class="k">{label}</div>'
                 f'<div class="v {c}" id="{kid}">{num(v, 2)}{suf}</div></div>')
    h.append('</div>')

    h.append('<div class="trend-wrap"><div class="eyebrow" style="margin-bottom:6px">'
             f'近 {len(periods)} 期营收 / 归母净利（亿元 · {esc(currency)}）</div>'
             '<svg id="trend-svg" class="trend-svg" viewBox="0 0 620 224" role="img" '
             'aria-label="营收与归母净利分组柱状图"></svg>'
             '<div class="legend"><span><i style="background:var(--accent)"></i>营业收入</span>'
             '<span><i style="background:var(--warn)"></i>归母净利</span>'
             '<span><i style="background:var(--accent);opacity:.25"></i>当前报告期</span></div>'
             '<div class="src"><b>柱端直接标注金额</b>（按量级自适应精度，悬停仅补充完整日期与 2 位小数原值）；'
             '纵轴为绝对金额（亿元 · 本页财报币种），亏损期柱体向下延伸；'
             '横轴每个刻度对应一个报告期（月份），下方短线按所属年份分组。'
             '净利柱明显矮于营收柱是真实量级差，不是绘图误差；'
             'A 股 CNY 与港股 HKD 不比绝对金额。</div></div>')
    h.append('</section>')

    # ---- 4-layer comparison + quality ----
    h.append('<section class="card"><div class="card-head"><h2>四层对比与盈利质量</h2>'
             '<span class="hint">绝对值优先于百分比</span></div>')
    h.append('<div style="overflow-x:auto"><table><thead><tr><th>层次</th><th>指标</th>'
             '<th>覆盖</th><th class="num">说明</th></tr></thead><tbody>')
    h.append(f'<tr><td><b>同比</b></td><td>营收 / 归母净利</td><td>{len(periods)} 期</td>'
             '<td class="num">数字卡随报告期切换</td></tr>')
    h.append('<tr><td><b>单季同比</b></td><td>rev_yoy_q / np_yoy_q</td><td>已覆盖</td>'
             '<td class="num">见快照字段</td></tr>')
    h.append(f'<tr><td><b>近 {len(periods)} 期趋势</b></td><td>营收 / 归母净利</td><td>{len(periods)} 期</td>'
             '<td class="num">见上方柱状图，可切换报告期</td></tr>')
    h.append('<tr><td><b>管理层措辞 / 指引</b></td><td>公告正文语义对比</td>'
             '<td><b>未覆盖</b></td><td class="num">无结构化字段，不编造</td></tr>')
    h.append('</tbody></table></div>')
    h.append('<div class="kpi-grid" style="margin-top:14px">')
    for label, key, elem_id, suf in [
        ("毛利率", "gross", "k-gross", "%"),
        ("净利率", "net_margin", "k-margin", "%"),
        ("EPS", "eps", "k-eps", ""),
        ("资产负债率", "debt", "k-debt", "%"),
    ]:
        h.append(f'<div class="kpi-cell"><div class="k">{label}</div>'
                 f'<div class="v" id="{elem_id}">{num(newest.get(key), 2)}{suf}</div></div>')
    h.append('</div>')
    h.append('<div class="notice warn">经营现金流 ÷ 净利润、分部结构无结构化字段，'
             '标「未覆盖」，不做估算。</div>')
    h.append('</section>')

    # ---- valuation linkage ----
    h.append('<section class="card"><div class="card-head"><h2>估值联动与买入区间</h2>'
             '<span class="hint">财报发布 / 除权后必须重算</span></div>')
    h.append('<div style="overflow-x:auto"><table><thead><tr><th>指标</th><th class="num">值</th>'
             '<th>口径</th></tr></thead><tbody>')
    for label, key, suf in [
        ("PE(TTM)", "pe_ttm", ""), ("PB", "pb", ""),
        ("股息率", "dividend_yield", "%"), ("10 年分位", "percentile", "%"),
    ]:
        h.append(f'<tr><td>{label}</td><td class="num mono">{num(vsnap.get(key), 2)}{suf}</td>'
                 '<td class="hint">快照值，带 source/as_of/currency</td></tr>')
    h.append('</tbody></table></div>')
    b = band
    band_val = b.get("band")
    if isinstance(band_val, (list, tuple)) and len(band_val) == 2:
        h.append('<div class="notice"><b>可接受价格带</b>　'
                 f'{num(band_val[0])} – {num(band_val[1])} '
                 f'（{esc(b.get("expensiveness", "—"))}；主锚 {esc(b.get("anchor", "—"))}；'
                 f'置信度 {esc(b.get("confidence", "—"))}）。'
                 f'失效观察：{esc(b.get("invalidation", "—"))}</div>')
    elif b.get("role") == "holding":
        h.append('<div class="notice"><b>持仓标的</b>　走补仓三档与摊薄计算器，'
                 '受分母锁定、整手、集中度红线与资金上限约束；摊薄只改账面成本，不改善盈利能力。</div>')
    else:
        h.append('<div class="notice"><b>不给买入区间</b>　'
                 + esc(b.get("note", "仅观察：无正 PE / 上市不足一年，算合理区间是虚假精确感"))
                 + '。只做观察、事件提醒与仓位上限提示。</div>')
    gap = as_dict(valuation.get("data_gap"))
    if conf == "reference" or code in as_list(gap.get("affected")):
        h.append('<div class="notice warn"><b>参考级</b>　估值分位未覆盖或为平台测算替代锚，'
                 '低置信度、需人工确认。<b>价格位置不等于估值分位</b>，未用 K 线分位冒充。</div>')
    h.append('</section>')

    # ---- peers ----
    h.append('<section class="card"><div class="card-head"><h2>同业横比</h2>'
             '<span class="hint">只比比率与增速，不比绝对金额</span></div>')
    if peer_rows:
        h.append('<div style="overflow-x:auto"><table><thead><tr><th>同业</th><th>代码</th>'
                 '<th class="num">毛利率</th><th class="num">ROE</th><th class="num">PE</th>'
                 '<th class="num">PB</th></tr></thead><tbody>')
        for p in peer_rows:
            h.append(f'<tr><td>{esc(p.get("name"))}</td><td class="mono">{esc(p.get("code"))}</td>'
                     f'<td class="num mono">{num(p.get("gross"))}%</td>'
                     f'<td class="num mono">{num(p.get("roe"))}%</td>'
                     f'<td class="num mono">{num(p.get("pe"))}</td>'
                     f'<td class="num mono">{num(p.get("pb"))}</td></tr>')
        h.append('</tbody></table></div>')
    else:
        h.append('<div class="notice warn">未配置同业标的。同业横比只在同行业内做；'
                 '若观察池里没有同行业对子，应显式补同业或如实写「本层不可用」。</div>')
    h.append(f'<div class="src">{esc(as_dict(peers_cfg).get("comparison_rule", ""))} '
             f'{esc(as_dict(peers_cfg).get("currency_rule", ""))} '
             '同业清单 role: peer_only，不进主清单、不参与价格告警、不给买入区间。</div>')
    h.append('</section>')

    # ---- price reaction + consensus ----
    h.append('<div class="grid" style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px">')
    h.append('<section class="card"><div class="card-head"><h2>股价反应校验</h2>'
             '<span class="hint">headline 是否错位</span></div>')
    h.append('<table><thead><tr><th>窗口</th><th class="num">涨跌</th></tr></thead><tbody>')
    for k, label in [("d1", "披露后 1 日"), ("d5", "5 日"), ("d20", "20 日")]:
        v = reaction.get(k)
        h.append(f'<tr><td>{label}</td><td class="num mono {cls(v)}">{signed(v)}%</td></tr>')
    h.append('</tbody></table>')
    h.append(f'<div class="src">{esc(reaction.get("note", ""))} '
             '财报数字与股价反应若方向不一致，需人工复核，不自动下结论。</div></section>')
    h.append('<section class="card"><div class="card-head"><h2>预期差</h2>'
             '<span class="hint">不编造预期值</span></div>')
    cons = as_dict(as_dict(valuation.get("consensus")).get(code))
    if cons and cons.get("institution_count") == 0:
        h.append('<div class="notice warn"><b>无可靠一致预期</b>　'
                 '平台测算值，机构数为 0，非一手机构一致预期，需核实原文。'
                 '本页不做超预期/不及预期的硬判定。</div>')
    elif cons:
        h.append(f'<div class="notice">目标价 {num(cons.get("target_price"))} '
                 f'（机构数 {esc(cons.get("institution_count"))}，置信度 {esc(cons.get("confidence"))}）。'
                 '低置信度数字不做强视觉标记，也不画成价格轴上的买点。</div>')
    else:
        h.append('<div class="notice warn"><b>无可靠一致预期</b>　'
                 '不得用近四季趋势外推后包装成「预期值」。</div>')
    h.append('<div class="src">若有一手预期，实际 vs 预测方向可在此展示；'
             '缺失时如实写「无可靠一致预期」。</div></section>')
    h.append('</div>')

    # ---- announcements + limitations ----
    h.append('<section class="card"><div class="card-head"><h2>公告溯源</h2>'
             '<span class="hint">按时间倒序，精确到秒</span></div>')
    if anns:
        h.append('<div style="overflow-x:auto"><table><thead><tr><th>时间</th><th>标题</th>'
                 '<th>类型</th></tr></thead><tbody>')
        for a in anns:
            title = esc(a.get("title"))
            url = a.get("url")
            if url:
                title = f'<a href="{esc(url)}">{title}</a>'
            h.append(f'<tr><td class="mono hint">{esc(a.get("time"))}</td>'
                     f'<td>{title}</td><td>{esc(a.get("type"))}</td></tr>')
        h.append('</tbody></table></div>')
    else:
        h.append('<div class="notice">无公告记录。</div>')
    h.append('<div class="src">公告按代码取清单做时间增量，不用语义检索（实测会串到别家公司）。'
             '关键数字均标注来源与取数时间。</div>')
    h.append('</section>')

    h.append('<section class="card"><div class="card-head"><h2>口径与限制</h2>'
             '<span class="hint">渐进式披露</span></div>')
    h.append('<details><summary>本页未覆盖的内容</summary><div class="detail-body"><ul>')
    for item in limitations:
        h.append(f'<li>{esc(item)}</li>')
    h.append('</ul></div></details>')
    h.append('<details><summary>三重币种与周期对齐</summary><div class="detail-body">'
             '财报记账本位币、股价交易币种、账户展示币种三者分离；'
             'A 股与港股报告周期不对齐，按自然年季度映射后再比，不用「最新一期」直接横比；'
             '跨市场只比毛利率、增速、ROE、PE/PB 等比率，不比绝对金额。</div></details>')
    h.append('<details><summary>图表规范</summary><div class="detail-body">'
             '分组柱状图使用真实金额与 0 线，亏损向下；柱端数值常显并按量级自适应精度、'
             '逐个防重叠避让；横轴每个报告期一个刻度，两级坐标（月份 + 年份分组带），'
             '首尾留白 ≥ 28；窄屏可横向滚动，不靠缩小字号硬塞；悬停只作精度补充。</div></details>')
    h.append('</section>')

    h.append('<div class="foot">')
    h.append(f'<div class="src">财报快照：{esc(earnings.get("source"))} '
             f'（{esc(earnings.get("as_of"))}）；行情估值：{esc(earnings.get("quote_as_of"))}；'
             f'构建时间：{esc(now_iso())}。固定路径 dashboard/stocks/{esc(code)}.html，覆盖更新不改名。</div>')
    if is_demo:
        h.append('<div>本页面全部为<b>虚构演示数据</b>。</div>')
    h.append(f'<div style="margin-top:8px">{esc(DISCLAIMER_FULL)}</div>')
    h.append('</div></div>')
    h.append('<script>window.__D__ = ' + json.dumps(payload, ensure_ascii=False) + ';</script>')
    h.append(f'<script>{JS}</script></body></html>')
    return "\n".join(h)


def main() -> None:
    ap = argparse.ArgumentParser(description="build per-stock financial report pages")
    add_root_arg(ap, required=False)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        assert "paint-order=\"stroke fill\"" in JS
        assert "j%2" not in JS and "polyline" not in JS
        assert "period.slice(5,7)" in JS
        for token in ("localStorage.setItem('cr-", "location.href", "history.pushState"):
            assert token not in JS, f"persistence leak: {token}"
        print("build_stock_pages.py self-test OK")
        return

    require_root(ap, args)
    root = resolve_root(args)
    P = instance_paths(root)
    inst = load_yaml(P["config"] / "instance.yaml")
    mode = str(inst.get("mode", "demo"))
    wl = load_yaml(P["config"] / "watchlist.yaml")
    bands = as_dict(load_yaml(P["config"] / "buy-bands.yaml").get("bands"))
    peers_cfg = load_yaml(P["config"] / "peers.yaml")
    edir = latest_snapshot_with(root, "earnings.json")
    if edir is None:
        raise SystemExit("no snapshot containing earnings.json")
    earnings = load_json(edir / "earnings.json")
    valuation = load_json(edir / "valuation.json")
    fin = as_dict(earnings.get("financials"))

    P["stocks"].mkdir(parents=True, exist_ok=True)
    made = []
    for c in as_list(wl.get("codes")):
        code = str(c.get("primary", ""))
        if not code or code not in fin:
            continue
        html = build_page(root, code, str(c.get("name", code)), as_dict(fin[code]),
                          earnings, peers_cfg, valuation, bands, mode)
        if not html:
            continue
        (P["stocks"] / f"{code}.html").write_text(html, encoding="utf-8")
        made.append(code)
    print(f"built {len(made)} stock pages: {', '.join(made)}")


if __name__ == "__main__":
    main()
