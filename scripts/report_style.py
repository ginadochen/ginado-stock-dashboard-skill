"""给一次性网页（研报、财报速递等）注入与看板一致的视觉系统。

看板是深色金融面板，而一次性报告常常自带一套独立皮肤（比如浅色阅读风），
两处并排就像两个产品。这个脚本把看板的色板、字体、圆角、主题切换注入进去，
报告只保留自己的排版结构，不再保留自己的配色。

用法：
    python scripts/report_style.py reports/2026-11/*.html
    python scripts/report_style.py --dry-run reports/2026-11/*.html

行为：
  1. 用看板色板重定义报告页的常见变量名（--paper/--ink/--secondary/--line/--brand
     以及 --bg/--panel/--text/--border/--accent 两套命名都覆盖）
  2. 修正报告页里硬编码的浅色底（卡片、按钮、目录浮层），使其跟随主题
  3. 插入与看板相同的主题切换按钮，读写同一个 localStorage key，两处联动
  4. 深色下给内联 SVG 加白色底板——图表的坐标轴和文字多是硬编码深色，
     直接放深底上会看不清
幂等：重复运行只重建注入段，不会叠加。

色板来源：与 build_dashboard.py 里的 :root / html[data-theme="light"] 保持一致。
如果实例改过看板色板，改下面的 PALETTE 即可。
"""

import argparse
import glob
import re
import sys
from pathlib import Path

PALETTE = {
    "dark": {
        "bg": "#0f141c", "panel": "#182130", "panel2": "#1d2737",
        "text": "#e8eef7", "text2": "#aab8cc", "text3": "#7d8ca3",
        "border": "#2a3648", "accent": "#5b9cff", "warn": "#f0a94b",
    },
    "light": {
        "bg": "#f5f7fb", "panel": "#ffffff", "panel2": "#f3f6fb",
        "text": "#1b2433", "text2": "#4c5b70", "text3": "#7a879a",
        "border": "#dde4ef", "accent": "#2f6fd0", "warn": "#c07a18",
    },
}

THEME_KEY = "stock-dashboard-theme"
MARK_BEGIN = "<!-- unified-theme:begin -->"
MARK_END = "<!-- unified-theme:end -->"


def build_css() -> str:
    d, l = PALETTE["dark"], PALETTE["light"]

    def decl(p: dict) -> str:
        return (f'--rs-bg:{p["bg"]}; --rs-panel:{p["panel"]}; --rs-panel2:{p["panel2"]};'
                f' --rs-text:{p["text"]}; --rs-text2:{p["text2"]}; --rs-text3:{p["text3"]};'
                f' --rs-border:{p["border"]}; --rs-accent:{p["accent"]}; --rs-warn:{p["warn"]};')

    # 两套常见变量命名都映射到同一组 --rs-*，报告页无论原来叫什么都能接上
    alias = (
        '--paper:var(--rs-bg); --bg:var(--rs-bg);'
        '--surface:var(--rs-panel); --panel:var(--rs-panel); --card:var(--rs-panel);'
        '--tint:var(--rs-panel2);'
        '--ink:var(--rs-text); --text:var(--rs-text); --fg:var(--rs-text);'
        '--secondary:var(--rs-text2); --muted:var(--rs-text3);'
        '--line:var(--rs-border); --border:var(--rs-border);'
        '--brand:var(--rs-accent); --accent:var(--rs-accent);'
        '--warning:var(--rs-warn); --radius:14px;'
        '--font:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;'
    )

    return f"""
/* ===== 看板统一设计系统（scripts/report_style.py 注入，勿手改） ===== */
:root{{{decl(d)} color-scheme:dark; {alias}}}
html[data-theme="light"]{{{decl(l)} color-scheme:light;}}
body{{background:var(--rs-bg); color:var(--rs-text); font-family:var(--font,inherit)}}
a{{color:var(--rs-accent)}}
blockquote{{background:var(--rs-panel)}}
table thead th{{background:var(--rs-panel2)}}
.summary-card{{background:var(--rs-panel); border:1px solid var(--rs-border);
  border-top:3px solid var(--rs-accent); box-shadow:0 1px 2px rgba(0,0,0,.18)}}
.visual-canvas button{{background:var(--rs-panel2); border-color:var(--rs-border); color:var(--rs-text2)}}
.visual-canvas button[aria-pressed=true]{{border-color:var(--rs-accent); color:var(--rs-accent)}}
.article-rail-mark{{background:var(--rs-border)}}
.article-rail:is(:hover,:focus-within){{background:var(--rs-panel); border-color:var(--rs-border)}}
::selection{{background:rgba(91,156,255,.30); color:var(--rs-text)}}
[data-theme="dark"] .visual-canvas svg{{background:#fff; border-radius:10px; padding:10px}}
.theme-float{{position:fixed; right:18px; top:16px; z-index:60; width:34px; height:34px; padding:0;
  display:flex; align-items:center; justify-content:center; font-size:15px; line-height:1;
  border:1px solid var(--rs-border); border-radius:10px; background:var(--rs-panel);
  color:var(--rs-text2); cursor:pointer; transition:color .15s ease, border-color .15s ease}}
.theme-float:hover{{color:var(--rs-accent); border-color:var(--rs-accent)}}
@media print{{
  :root{{--rs-bg:#fff; --rs-panel:#fff; --rs-text:#111; --rs-text2:#333; --rs-text3:#666; --rs-border:#ddd}}
  body{{background:#fff; color:#111}}
  .theme-float{{display:none!important}}
  [data-theme="dark"] .visual-canvas svg{{background:transparent; padding:0}}
}}
"""


def build_js() -> str:
    return """
<script id="unified-theme-js">
(function(){
  var KEY="%s";
  var root=document.documentElement, btn=document.getElementById("theme-toggle");
  function apply(mode){
    root.setAttribute("data-theme", mode);
    if(btn){
      btn.textContent = mode==="dark" ? "\\u2600" : "\\u263E";
      btn.setAttribute("title", mode==="dark" ? "切换浅色" : "切换深色");
    }
  }
  var saved=null;
  try{ saved=window.localStorage.getItem(KEY); }catch(e){}
  apply(saved==="light" ? "light" : "dark");
  if(btn){
    btn.addEventListener("click", function(){
      var next = root.getAttribute("data-theme")==="dark" ? "light" : "dark";
      apply(next);
      try{ window.localStorage.setItem(KEY, next); }catch(e){}
    });
  }
})();
</script>
""" % THEME_KEY


BUTTON = ('<button id="theme-toggle" class="theme-float" type="button" '
          'title="切换浅色" aria-label="切换主题">\u2600</button>')


def strip_previous(html: str) -> str:
    html = re.sub(r'<style id="unified-theme">.*?</style>\s*', "", html, flags=re.S)
    html = re.sub(re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\s*", "", html, flags=re.S)
    return html


def inject(html: str) -> str:
    html = strip_previous(html)
    if "</head>" not in html or "</body>" not in html:
        raise ValueError("找不到 </head> 或 </body>，不是完整 HTML 文档")
    html = html.replace("</head>", f'<style id="unified-theme">{build_css()}</style>\n</head>', 1)
    html = html.replace("</body>", f"{MARK_BEGIN}{BUTTON}{build_js()}{MARK_END}\n</body>", 1)
    return html


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="HTML 文件或通配符")
    ap.add_argument("--dry-run", action="store_true", help="只报告会改哪些文件，不写入")
    args = ap.parse_args()

    paths = []
    for pattern in args.files:
        hits = sorted(glob.glob(pattern))
        paths.extend(Path(h) for h in (hits or [pattern]))

    changed = skipped = 0
    for p in paths:
        if p.suffix.lower() not in (".html", ".htm") or not p.exists():
            print(f"skip  {p}")
            skipped += 1
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        try:
            out = inject(src)
        except ValueError as e:
            print(f"skip  {p.name}: {e}")
            skipped += 1
            continue
        if out == src:
            print(f"same  {p.name}")
            continue
        if not args.dry_run:
            p.write_text(out, encoding="utf-8")
        changed += 1
        print(f"{'plan' if args.dry_run else 'done'}  {p.name}  ({len(out)} 字符)")

    verb = "待更新" if args.dry_run else "已更新"
    print(f"\n{changed} 个文件{verb}，{skipped} 个跳过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
