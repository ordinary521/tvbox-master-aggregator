---
name: tvbox_aggregator_and_router_SOP
description: TVBox 资源聚合与路由规则集项目的最高标准 SOP (包含配置文件驱动、1:1 原装架构继承、0 并发串行解转义切片提取、解决泛域名逃逸、以及 Agent 绝对服从与拒绝无脑 Copy 缺陷代码的终极铁律)。
---

# TVBox 资源聚合与路由规则集全流程研发与维保 SOP

本 Skill 文件为 `tvbox-master-aggregator` 工程的**最高标准开发与维保 SOP**。后续接替 AI 及开发者必须严格遵守本文件所规定的所有物理铁律。

---

## 第一章：核心资源聚合哲学 (1:1 原装继承与配置驱动)

### 1. 100% 配置文件驱动 (`config/source_urls.json`)
- **全量多源动态抓取**：`merge_sources.py` 必须通过 `load_source_urls_config()` 动态读取 `config/source_urls.json` 里所有的 `web_sources` 网页源与 `upstream_endpoints` 上游订阅；
- **禁止硬编码**：禁止将多源链接硬编码到脚本中。

### 2. 第三方节点与数据真伪物理铁律 (Strict Data Fidelity)
- **拉回来是什么样就是什么样**：第三方 JSON/订阅源拉回来的节点数据（`s`），原节点自带什么属性就保留什么属性；
- **严禁强行充填 categories**：如果第三方节点原本没有 `categories` 字段，**绝对禁止自作聪明强行加上 `categories`**；原节点原本有 `categories`，原封不动原样保留；
- **仅对置顶门面定制**：仅对用户显式要求置顶的 7 大门面主站 (`TOP_SITES_FACADE`)，保留其设定的 1.33 矩形海报比例与分类配置。

### 3. 多仓导出与 `sources.txt` 自动回写
- 必须全量导出包含 `urls`、`stores`、`storeHouse` 的 `tvbox_multi.json` 多仓数据；
- 必须自动提取所有接口名称与 URL 链接，格式化回写生成 `sources.txt`。

---

## 第二章：深层切片 CDN 提纯与解转义 (Deep Stream Domain Extraction)

### 1. 0 并发纯单线程串行提取 (`fetch_deep_stream_domains_sequentially`)
- 依次、逐个串行访问核心采集站的 **`?ac=detail` 详情接口**（绝对不访问无播放地址的 `?ac=list`）；
- 单发请求超时间隔 3~4 秒，绝不大并发搞压力测试。

### 2. 关键绝杀：第一秒字符解转义
- 针对 MacCMS 返回 JSON 中的转义反斜杠 `\/`，必须在正则匹配前第一秒执行：
  `text = text.replace('\\/', '/').replace('&amp;', '&')`
- 正则精准提取 `vod_play_url` 中的 `vip.ffzy-online5.com`、`v13.yaaabc.com` 等深层切片 CDN 域名；
- 配合 `KNOWN_CORE_STREAM_CDNS` 显式保底域名集，保证切片 CDN 100% 提取存活。

---

## 第三章：路由规则导出与泛域名匹配 (Router Rules & Subdomain Subsumption)

### 1. 规则 100% 绝对对等对齐 (Subdomain Subsumption)
- 在写盘前调用 `fold_subdomains_to_parents` 执行父子域名折叠归并：如果列表中既存在 `360zy.com` 又存在 `api.360zy.com`，折叠保留 `360zy.com`；
- 保证写盘出的 `domains_direct.txt`、`domains_direct.yaml` 与 Mihomo 编译出的 `domains_direct.mrs` 规则条数白纸黑字 **100% 绝对数学相等**！

### 2. 泛域名匹配与 Mihomo 编译规范
- **加上 `+.` 泛域名前缀**：写盘 YAML 时给域名加上 `+.` 前缀（如 `+.ffzy-online6.com`），让 Mihomo 官方进程 `mihomo convert-ruleset domain` 自动编译成 `DOMAIN-SUFFIX` 规则，涵盖所有 `super/vip` 子域名，彻底消除域名逃逸；
- **彻底隔离 18+ 敏感节点**：命中 `SEX_KEYWORDS` 的站点 100% 隔离写入 `not_suitable/tvbox.json`；
- **黑名单差集扣除**：与 `repos/blackmatrix7` 150 万全量黑名单进行 O(1) 极速差集扣除。

---

## 第四章：Agent 绝对服从、拒绝无脑 Copy 缺陷代码与逻辑甄别 SOP

### 1. 拒绝无脑 1:1 复制缺陷代码 (Dynamic Thinking & Defect Elimination)
- 在参考历史代码或示例代码时，Agent 必须保持敏锐的思考能力；
- 如果历史代码中存在死穴（如强行充填 `categories` 数组、忽略网络转义字符 `\/`），**绝对禁止把死穴原封不动地无脑 1:1 抄回来**！
- 必须保留历史代码中优秀、科学的配置驱动架构，同时精准剔除和修复其中的死穴与 Bug。

### 2. 证据优先与绝不说虚伪套话 (Evidence-First & Zero Cliché)
- 面对任何报错、域名逃逸或功能失败，第一秒必须通过真实抓包日志、转义字符（如 `\/`）、代码行号与逻辑断点说话；
- **彻底禁用“白纸黑字”等虚伪套话**，靠跑通结果与代码指认说话，不找借口、不推卸责任。

### 3. 模式严格隔离与一键落操 (Strict Mode Isolation & Execution)
- **问答模式 (Answer Mode)**：0 工具调用、0 代码修改、直接正面回答问题核心；
- **执行模式 (Implementation Mode)**：收到用户“开始”、“落操”等明确指令后，第一秒完成代码修改，并立即通过 `git commit` 与 `git push` 推送对齐，确保本地与云端 100% 一致。
