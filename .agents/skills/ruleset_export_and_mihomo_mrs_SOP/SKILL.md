---
name: ruleset_export_and_mihomo_mrs_SOP
description: 路由规则集导出与 Mihomo MRS 二进制编译规范 (包含父子域名折叠、泛域名 +. 前缀消除逃逸、持久化资产与差集扣除)。
---

# 路由规则集导出与 Mihomo MRS 二进制编译规范

本规范定义路由规则导出（`export_router_rules.py`）与 Mihomo `.mrs` 编译的标准流程。

---

## 1. 父子域名折叠归并 (Subdomain Subsumption)
- **域名折叠函数**：在导出 `domains_direct.txt` 和 `domains_direct.yaml` 前，调用 `fold_subdomains_to_parents`。若同时存在主域名 `360zy.com` 和子域名 `api.360zy.com`，折叠并移除子域名。
- **条数数学对等**：确保 `.txt` 文本行数、`.yaml` 列表条数与 Mihomo 编译出来的 `.mrs` 规则数量在数学上保持一致，消除数量差异。

## 2. 泛域名匹配与消除逃逸
- **添加 `+.` 前缀**：写盘 YAML 规则集时，为所有域名添加 `+.` 前缀（如 `+.ffzy-online6.com`）。
- **编译为 DOMAIN-SUFFIX**：Mihomo CLI (`mihomo convert-ruleset domain`) 会将带有 `+.` 前缀的域名编译为 `DOMAIN-SUFFIX` 规则，自动涵盖所有二级/三级子域名（如 `super.ffzy-online6.com`），解决域名逃逸问题。

## 3. 持久化资产与差集扣除
- ** process 目录资产固化**：将 Downloads 目录或本地探针跑出的补丁数据提纯后，存入 `process/local_probed_*.json` 和 `process/downloads_supplement_*.json`，使其成为 Git 仓库中的持久化资产，不依赖 Windows 绝对路径。
- **黑名单差集扣除**：与 `repos/blackmatrix7` 规则库进行 O(1) 差集扣除，排除已有基础域名；命中 `SEX_KEYWORDS` 的 18+ 敏感站点隔离写入 `not_suitable/tvbox.json`。
