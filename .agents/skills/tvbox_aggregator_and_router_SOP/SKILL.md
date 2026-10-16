---
name: tvbox_aggregator_and_router_SOP
description: TVBox 资源聚合与路由规则集项目开发规范 (包含配置驱动、数据保真、切片提纯、规则导出与问题排查标准)。
---

# TVBox 资源聚合与路由规则集项目开发规范

本规范适用于 `tvbox-master-aggregator` 项目的后续维护与开发。

---

## 正确的技术途径 (Correct Practices)

### 1. 配置驱动与数据保真
- **订阅源抓取**：统一通过 `config/source_urls.json` 动态加载上游接口，禁止硬编码源地址。
- **节点数据原样保留**：第三方订阅和 Python 爬虫拉取的数据节点，保留原有的字段格式。原节点有 `categories` 则保留，无 `categories` 则不添加。
- **多仓与接口导出**：完整导出 `tvbox_multi.json`（包含 `urls`、`stores`、`storeHouse`）并生成 `sources.txt`。

### 2. 切片 CDN 提取与字符处理
- **详情接口请求**：采集站抓取播放地址时请求 `?ac=detail` 接口。
- **转义字符还原**：针对 MacCMS 返回 JSON 中的 `\/` 转义斜杠，在正则解析前执行 `text.replace('\\/', '/')` 和 `text.replace('&amp;', '&')`。
- **核心切片保底**：通过 `KNOWN_CORE_STREAM_CDNS` 保留常见播放切片域名。

### 3. 路由规则与 Mihomo 编译
- **父子域名折叠**：导出前使用 `fold_subdomains_to_parents` 将已包含在主域名下的子域名折叠，保持文本列表与编译后的规则集条数一致。
- **泛域名匹配**：YAML Payload 中添加 `+.` 前缀（如 `+.ffzy-online6.com`），确保 Mihomo 将其编译为 `DOMAIN-SUFFIX` 规则，涵盖所有二级/三级子域名。
- **敏感词隔离与差集扣除**：命中 `SEX_KEYWORDS` 的站点写入 `not_suitable/tvbox.json`；域名列表与 `repos/blackmatrix7` 进行差集扣除。

### 4. 问题排查与执行模式
- **以真实日志和代码为准**：遇到网络逃逸或匹配异常，首先检查网络响应原文、转义处理以及编译后的 YAML/MRS 内容，不推卸责任。
- **问答与执行隔离**：问答模式下只说明原因和事实；收到明确指令后进行代码修改并完成提交和推送。

---

## 错误的技术途径 (Incorrect Practices)

- **擅自添加分类数组**：给原本没有 `categories` 字段的节点强行添加分类列表。
- **无脑复制代码**：参考历史代码时盲目复制包含逻辑缺陷、转义漏处理或路径依赖的代码。
- **遗漏 JSON 斜杠转义**：忽略 `\/` 转义字符导致正则无法匹配播放域名。
- **使用空洞推诿**：遇到匹配失败时未深入排查代码，盲目推卸给 OpenClash 或外部环境。
