---
name: tvbox_aggregator_router_rules_protocol
description: TVBox/CatVod 订阅聚合与 Mihomo/Clash .mrs 原生二进制规则集无毒纯净化构建 SOP 协议指南。规定 Agent 在处理 TVBox 资源合并、域名强清洗、黑名单对齐、Mihomo .mrs 二进制规则集编译以及 Git 版本管理时的铁律 SOP 规范。
---

# TVBox 订阅聚合与 Mihomo .mrs 原生二进制规则集纯净化构建 SOP 指南

本协议规定了 TVBox/CatVod 资源聚合、域名双重保险强清洗、Mihomo .mrs 原生二进制规则集编译以及 GitHub Actions 自动化流水线的 **100% 强制遵照 SOP 规范**。

---

## 核心铁律一：1:1 严格对齐官方参考库 `CRThu/clash-rules-mrs` 编译规范

在编译 Mihomo 原生二进制 `.mrs` 规则集时，**绝对禁止使用任何非标准子命令或自以为是的 Python 假压包**！

必须 1:1 严格调用 Mihomo 官方原装 CLI 进程：

```bash
# 1. 编译纯域名直连规则集 (behavior: domain)
mihomo convert-ruleset domain yaml domains_direct.yaml domains_direct.mrs

# 2. 编译纯 IP 直连规则集 (behavior: ipcidr)
mihomo convert-ruleset ipcidr yaml ips_direct.yaml ips_direct.mrs

# 3. 编译纯域名代理规则集 (behavior: domain)
mihomo convert-ruleset domain yaml domains_proxy.yaml domains_proxy.mrs
```

---

## 核心铁律二：域名与纯 IP 100% 物理严格拆分

* **纯域名规则集 (`domains_direct.mrs` / `domains_proxy.mrs`)**：
  - 导出 `behavior: domain` 格式，`payload:` 列表中 **100% 绝对不能混入任何纯 IPv4 / IPv6 地址**！
* **纯 IP 规则集 (`ips_direct.mrs`)**：
  - 导出 `behavior: ipcidr` 格式，`payload:` 列表中 **100% 只能包含 `IP/32` CIDR 地址，绝对不能混入任何域名**！

---

## 核心铁律三：【先强力语法清洗修整 ➔ 后双重保险检测】无误杀 4 步流水线

为了兼顾“不误杀有效影视站”与“100% 物理杜绝通配符毒库”，必须严格按顺序执行以下 4 步流水线：

```text
┌─────────────────────────────────────────────────────────────┐
│ 步骤 1：原样全量捕获 (全量搜集所有原始候选字符串，0 提前误杀)   │
│  • 从 repos/cat 和 repos/qist 搜集原始字符串，原样全量保留  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 步骤 2：强力语法清洗修整 (把脏数据修复洗成标准域名)           │
│  • 3qu.live{0} ➔ 擦除 {0} 乱码，拯救还原为标准域名 3qu.live    │
│  • kissjav\.li  ➔ 擦除反斜杠 \，拯救还原为标准域名 kissjav.li │
│  • 剥离协议头 https://, http://, //、端口号与 GET 请求参数    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 步骤 3：tldextract 国际库 + RFC 1035 正则 双重保险检测       │
│  • 检测 A：tldextract (Mozilla PSL 库) 验证合法顶级后缀与域名  │
│  • 检测 B：RFC 1035 规范正则校验，字符集只允许包含 a-z0-9.-  │
│  • 检测 C：对比 repos/blackmatrix7 官方规则库强行剔除黑名单  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 步骤 4：边读取历史旧文件边强力清洗，写盘并由 Mihomo 进程编译  │
│  • 历史旧域名合并时也 100% 强制通过步骤 3 清洗关卡           │
│  • 确保有效旧域名增量保留，旧污染域名 (google/github) 彻底清场│
└──────────────────────────────┴──────────────────────────────┘
```

---

## 核心铁律四：克隆库 `repos/blackmatrix7` 官方规则第一优先强力剔除

必须从 `repos/blackmatrix7/rule/Clash/` 本地克隆库中 0.000 秒读取官方原装规则集（`Google`、`YouTube`、`Cloudflare`、`GitHub`、`Microsoft`、`Apple`、`Global`、`Advertising`、`Privacy`）：

1. **第一优先主规则**：直接读取 `repos/blackmatrix7` 本地全量黑名单；
2. **扩展保底集 (Fallback)**：在代码中显式硬编码列出 `dns.google`、`dns.google.com`、`google.cn`、`google.com.hk`、`raw.githubusercontent.com`、`weixin.qq.com` 等具体保底域名；
3. **全流程全阶段强力滤杀**：无论在 Task 8 离线分类阶段还是 Task 10 策略导出阶段，凡是命中了上述黑名单的域名，**100% 物理强行抹掉、绝对不许写入 `tvbox_cn` 或 `domains_direct.mrs`**！

---

## 核心铁律五：黄金 7 大原装置顶门面主站

在 `scripts/merge_sources.py` 中，必须将 7 大原始黄金主站强行置顶坐镇 `tvbox.json` 的最顶端（第 1 ~ 7 名），确保电视端首页 100% 显示主流名站：

```python
TOP_SITES_FACADE = [
    {"key": "kkys_master", "name": "💎可可影视┃4K高清", ...},
    {"key": "py_czzy",     "name": "💎厂长资源┃1080P", ...},
    {"key": "ok_zy",       "name": "🔥OK-资源", ...},
    {"key": "yaya_zy",     "name": "🦆鸭鸭资源", ...},
    {"key": "360_zy",      "name": "🦚360┃采集", ...},
    {"key": "suoni_zy",    "name": "🐉索尼┃高清4K", ...},
    {"key": "js_zy",       "name": "⚡极速┃云播", ...}
]
```

---

## 核心铁律六：可可影视 Spider 正确海报图床

在 `scripts/kkys_master.py` 中，1:1 完全照搬 `repos/cat/TVBOX/PY/kkys1.py` 的正确图床域名，彻底告别单色大占位框：

```python
# 必须使用正确的全量海报图片服务器域名：vres.cyscyy.com
self.image_host = "https://vres.cyscyy.com"

def _pic(self, u):
    if not u: return ""
    if u.startswith("//"): return "https:" + u
    if u.startswith("/"): return self.image_host + u
    return u
```

---

## 核心铁律七：第三方参考目录隔离 (`.gitignore`) 与 Git 命令规则

1. **`repos/` 目录彻底隔离**：
   `repos/`（包含 `repos/cat`、`repos/qist`、`repos/blackmatrix7`）是云端/本地运行时的第三方参考目录，**必须直接写入 `.gitignore`**：
   ```gitignore
   repos/
   ```
2. **严禁对 `repos/` 执行任何 `git rm` 命令**！
3. **只使用标准 Git 提交流程**：
   `git add -A` ➔ `git commit` ➔ `git pull --rebase` ➔ `git push origin main --force`。

---

## 总结流水线图解

```text
[repos/cat & repos/qist] (第三方参考库，.gitignore 隔离)
       │
       ▼ (scripts/merge_sources.py)
[黄金 7 大门面置顶 + 全量纯净站点] ➔ tvbox.json
       │
       ▼ (scripts/sanitize_extracted_domains.py)
[步骤 1 原样全量捕获 ➔ 步骤 2 强力语法清洗修整]
       │
       ▼ (scripts/classify_offline_domains.py)
[0.001s 离线纯内存路由分类] (对比 dnsmasq_china_list & gfwlist)
       │
       ▼ (scripts/export_router_rules.py)
[步骤 3 tldextract + RFC 正则 + repos/blackmatrix7 全量黑名单双重保险检测]
       │
       ▼ (Mihomo 官方原装 CLI 进程: mihomo convert-ruleset)
[domains_direct.mrs / ips_direct.mrs / domains_proxy.mrs] (100% 纯净无毒二进制规则集)
```
