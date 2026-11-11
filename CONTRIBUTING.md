# 贡献指南

欢迎提 issue 和 PR。几条规定能省掉很多往返：

## 提交前

```bash
python scripts/privacy_check.py --root .     # 必须 0 命中
python scripts/layout_check.py --root ./demo-instance
python scripts/build_dashboard.py --root ./demo-instance --self-test
```

## 硬规则

1. **任何真实个人数据都不得进入仓库**：金额、成本价、股数、姓名、聊天 ID、token、Windows 绝对路径、自动化 ID、邮箱/手机/IP、真实持仓截图。
2. **不要提交实例目录**：`config/`、`data/`、`state/`、`logs/`、`archive/`、`tmp/`、`.sandbox/`、`dist/` 全部被忽略。只改 `assets/templates/*.example` 和 `assets/demo/*.json`。
3. **模板里只能用 `{{占位符}}`**，不得写具体金额、比例、路径、标的或收件人。
4. **脚本必须显式 `--root`**，不得用 `Path(__file__).parent.parent` 推断实例目录。
5. **网页单文件自包含**，不引用外链 CSS/JS。
6. **不要编造数据**：没有就标「未覆盖 / 参考级」，不要用价格分位冒充估值分位。
7. 涉及价位、区间、仓位的输出或文案，末尾附 `references/disclaimer.md` 的免责声明。

## 风格

- 中文为主，代码注释与标识符用英文
- 日期 `YYYY-MM-DD`，文件名 `<日期>-<类型>-<主代码>.<ext>`
- 红涨绿跌（中国习惯），颜色必须配符号或箭头
- 新增顶层目录或改数据契约，先改 `assets/templates/agent.md` 与 `references/data-contract.md`，并在 `CHANGELOG.md` 记一笔

## 安全披露

发现误含个人信息，请走 [SECURITY.md](SECURITY.md)，不要开公开 issue。
