# 截图目录约定

`docs/screenshots/` 是仓库里**唯一**允许存放图片的目录，README 引用这里的图。

## 为什么只开这一个口子

看板截图天生带敏感信息。真实持仓的截图里有总资产、可用资金、持股数、成本价，即使裁掉账户名也一样敏感。所以仓库的默认规则是「任何图片都不许进」，`privacy_check.py` 见到二进制文件直接判 FAIL。

README 需要展示成品，所以开了这一处例外，条件是：

1. 只能放在 `docs/screenshots/`，其他任何路径的图片仍然会被判 FAIL
2. 只允许 `.png`
3. **必须是 demo 实例的截图**，也就是 `example/` 或 `python scripts/instance.py --mode demo` 生成出来的页面，数据全是虚构的

`privacy_check.py` 会把放行的文件逐条打印出来，方便人再核一眼。

## 怎么重新生成

```bash
# 1. 先确保 example/ 是最新的 demo 产物
python scripts/instance.py        --root ../shot --mode demo
python scripts/build_dashboard.py --root ../shot
python scripts/build_stock_pages.py --root ../shot

# 2. 用无头浏览器按区块截图（1400 宽视口，deviceScaleFactor=2，最后缩到 1400 宽）
#    截图后放到 docs/screenshots/，文件名用 01- 到 06- 的前缀
```

不要截 `live` 模式的页面，也不要用自己的真实实例页面临时替换后再截图。
