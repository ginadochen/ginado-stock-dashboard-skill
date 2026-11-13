# 隐私验收记录

本文件记录**方法与结论**，不记录任何敏感值。

## 验收原则

开源的是「造出看板的能力」，不是任何真实实例。因此验收目标不是「清理一次」，而是建立一套**默认拒绝 + 可重复执行**的机制。

## 检查项

| # | 检查 | 方法 | 结论 |
|---|---|---|---|
| 1 | 仓库从零创建，首次提交即干净 | 新建独立目录，只复制白名单文件；**不在生产实例里 `git init`** | ✅ 通过（本仓库为新建目录，无历史） |
| 2 | 默认拒绝式忽略规则 | `.gitignore` 首行 `*`，仅 `!` 放行白名单；`git check-ignore -q` 抽查 13 个路径 | ✅ 通过：7 个白名单文件可提交，`config.yaml` / `secret.jpg` / `data/` / `.sandbox/` / `dist/` / `__pycache__` 全部被忽略 |
| 3 | 敏感信息扫描 0 命中 | `python scripts/privacy_check.py --root . --strict` | ✅ 通过：0 命中；图片仅 `docs/screenshots/` 下的 6 张 demo 截图，逐条打印复核 |
| 4 | 模板无硬编码 | 扫描 `assets/templates/` 与 `references/` 中的金额、邮箱、绝对路径、token、UUID | ✅ 通过：0 命中 |
| 5 | 脚本无路径推断 | 扫描 `scripts/*.py` 中 `Path(__file__).parent.parent` 与硬编码盘符 | ✅ 通过：全部脚本以 `--root` 显式接收实例目录 |
| 6 | 演示数据虚构且可识别 | 所有 demo 快照 `source: demo-fixture`；金额明显整圆；无真实标的组合 | ✅ 通过：6 只演示标的与生产观察池及同业清单零重叠 |
| 7 | 产物不越界 | `layout_check.py` 检查白名单目录、临时目录清理、网页自包含 | ✅ 通过：7 个 HTML 页面全部自包含、链接可达、`tmp/` 干净 |
| 8 | 离线零依赖复现 | 屏蔽 PyYAML 后跑 `instance → build_dashboard → build_stock_pages → layout_check` | ✅ 通过：内置 YAML 子集解析器（含块标量）完整支撑，生成 7 页 |
| 9 | demo/live 物理隔离 | demo → live 切换后检查持仓、快照、demo 标记 | ✅ 通过：持仓为空、快照 0、标记清除、总资产归零 |
| 10 | skill 目录只读守卫 | 尝试 `--root .` 实例化 | ✅ 通过：被明确拒绝 |
| 11 | 交互不持久化表单数据 | 模拟 DOM 触发输入与滑块，检查 `localStorage` 写入键 | ✅ 通过：只有主题与清单勾选，表单值零持久化 |
| 12 | git 历史无残留 | `git log --all -p` 全文检索 | ✅ 通过（2026-11-11 发布时）：敏感值与真实 token 形态均 0 命中 |
| 13 | 独立 clone 复扫 | 全新 clone 到独立目录后复跑隐私扫描与离线复现 | ✅ 通过（2026-11-11）：46 个文件、扫描 0 命中、离线生成 7 页、页面自包含 |

> 说明：12、13 项已随 2026-11-11 公开发布补齐，详见下方「发布记录」。
>
> 本地自测记录（2026-11-11）：Python 编译、3 个脚本 self-test、隐私扫描、模板硬编码扫描、路径推断扫描、零依赖离线复现、布局检查、7 页 JS 语法与自包含、6 页柱状图模拟渲染（柱数/标签数/纵轴/月份/年份/0 线/零重叠/边界内）、无头浏览器截图目视，全部通过。

## 扫描器覆盖范围

`privacy_check.py` 检查以下模式（正则按类别分组，命中即失败）：

- 高精度金额（含小数点的货币数字）、真实持仓股数
- 中文姓名、常见收件人称谓
- 聊天 / 群 ID、`chat_id`、企业微信 ID 形态
- Windows 绝对路径、盘符路径、UNC 路径
- 自动化任务 UUID、`hosts.yml`
- token 前缀：`ghp_` / `github_pat_` / `gho_` / `ghs_` / `ghr_` / `github_pat_11`
- 邮箱（含 noreply）、手机号、IPv4
- 私钥头 `-----BEGIN ... PRIVATE KEY-----`
- 图片/截图二进制文件（唯一例外见下）
- **私有观察池的标的组合**（可选）：单个证券代码是公开信息，但一组代码的组合能反推个人偏好。本仓库**不硬编码任何人的标的清单**；用 `--codes A,B,C` 或环境变量 `PRIVACY_WATCH_CODES` 在扫描时动态注入，规则仅在传入 ≥3 个代码时启用

允许项：`assets/demo/` 中的虚构数值（带 `demo-fixture` 标记）、`example/` 成品、`docs/screenshots/` 下的 demo 截图、LICENSE/NOTICE 中的年份与署名、CI 配置里的版本号。

> **图片唯一例外（2026-11-12 起）**：README 需要成品图，因此放行 `docs/screenshots/*.png`。约束是只能由 demo 实例（虚构数据）截图生成，其他路径的图片仍然判 FAIL，规则细节见 [screenshots.md](screenshots.md)。扫描器会把放行的文件逐条打印，便于人工复核。

## 已知边界

- 扫描器是**模式匹配**，不能保证识别所有形式的个人信息。人工复核不可省略。
- 公开仓库一旦误推，按已泄露处理；撤销 commit 不算数（见 `SECURITY.md`）。
- 本工具提供的是「机制被执行且有验收记录」的保证，不是「绝对零风险」的承诺。

## 运行方式

```bash
python scripts/privacy_check.py --root . --strict
# 若担心自己的观察池组合被误提交，扫描时临时传入（不写进仓库）：
python scripts/privacy_check.py --root . --strict --codes CODE1,CODE2,CODE3
```

退出码 0 表示 0 命中；非 0 时输出命中文件与类别（不输出命中内容的完整值）。

## 发布记录

- **2026-11-11 首次公开发布**：`github.com/ginadochen/stock-dashboard-skill`（public）。46 个文件、2 条提交，作者与提交者均为项目署名 ID；`git log --all -p` 全文检索无敏感值。
- **2026-11-12 仓库更名为** `github.com/ginadochen/ginado-stock-dashboard-skill`。GitHub 对旧地址保留重定向；仓库内容、提交历史、可见性（public）均未变动，未涉及任何文件级隐私影响。
- 发布方式：本地干净 git 历史 + GitHub REST API 校验，未从生产实例复制任何文件、未在生产实例内初始化仓库。
- 全局 git 身份（含真实姓名与个人邮箱）未被改动；本仓库使用**仓库级**署名覆盖。
- **CI 未启用**：发布凭据缺少 `workflow` scope，而 GitHub 对 `.github/workflows/` 目录下**任何**文件（含 `.example` 后缀）都要求该 scope。CI 模板以 `docs/verify.yml.example` 保留，启用方式见 README。
- 独立 clone 复扫（第 13 项）在发布后立即执行：全新目录 clone → `privacy_check --strict` 0 命中 → demo 实例化 → 生成 7 个页面 → 布局检查通过。
- **2026-11-13 v0.5.0 变更复扫**：新增 `scripts/report_style.py`、`references/remote-access.md`，修改 `SKILL.md`、`CHANGELOG.md`、`references/pitfalls.md`。`privacy_check.py --root . --strict` 0 命中。新增内容只含通用占位（`stock.example.com`、`localhost`），不含真实域名、账号 ID、Access 应用 ID、邮箱或密码。
- 同次修正 `ipv4` 规则：放行 `127.0.0.1` 与 `0.0.0.0`。这两个是回环/通配地址，不构成隐私泄露；原规则会把任何讲「源站回源到本机端口」的文档误判为违规，属于假阳性。其余内网与公网 IPv4 仍然命中。
- 演示验证在 `.sandbox/` 内完成（demo 实例 + 虚构报告），验证后已删除，未进入仓库。
