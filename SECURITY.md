# 安全政策

## 误传个人信息

若你发现本仓库误含个人信息（真实金额、姓名、截图、token、绝对路径等）：

1. **不要**在公开 issue 里贴出具体内容
2. 通过 GitHub 私密渠道联系仓库维护者（Security Advisory / 私信）
3. 说明文件路径与大致类型，不要复制敏感值

**重要**：公开仓库一旦 push，内容可能已被抓取、缓存或 fork。**删除 commit 或 force push 不算撤销**，请按「已泄露」处理——立即轮换相关凭据、通知可能受影响的人。

## 凭据

- 本仓库**不应包含**任何 token、私钥、`hosts.yml`、`.env` 或 OAuth 授权文件
- `privacy_check.py` 会扫描 `ghp_` / `github_pat_` / `github_pat_11` / `hosts.yml` / 私钥头
- 使用 `gh` 或 git 时，凭据应留在系统凭据管理器或用户目录，**不要**放进仓库目录树
- commit 邮箱建议使用 `users.noreply.github.com` 的隐私邮箱

## 依赖与供应链

- 运行时只依赖 Python 标准库 + PyYAML（demo 模式提供内置最小化解析，可零依赖）
- 脚本不直连 MCP、不发起外部网络请求（`check_sources.py` 只探测可达性，目标由实例配置给出，默认关闭）
- CI 只做隐私扫描与离线回归，不上传任何产物

## 支持的版本

| 版本 | 支持 |
|---|---|
| 最新提交 | ✅ |
| 更早版本 | ❌ |

## 免责

本项目不提供投资建议、不执行交易。安全问题的处理不影响 `references/disclaimer.md` 中的免责声明。
