# Changelog

All notable changes to this project are documented here. Dates use `YYYY-MM-DD`.

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
