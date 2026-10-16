---
name: tvbox_aggregator_and_router_SOP
description: TVBox 全量资源聚合与多源配置驱动规范 (包含 source_urls.json 驱动、第三方节点原样保真、ac=detail 详情解转义与多仓导出)。
---

# TVBox 资源聚合与多源配置驱动规范

本规范定义 `tvbox-master-aggregator` 项目中资源抓取、解析与配置合并的核心工程标准。

---

## 1. 配置驱动与多源聚合
- **源配置驱动**：必须动态读取 `config/source_urls.json` 文件中的 `web_sources` 与 `upstream_endpoints` 订阅源，禁止硬编码网络接口。
- **磁盘 PY 爬虫扫描**：遍历 `repos/` 下所有克隆仓库中的 `.py` 爬虫脚本（如 `repos/cat`、`repos/qist`），为其分配对应的代理托管前缀 (`GH_PROXY_PREFIX`)。

## 2. 节点数据保真原则
- **第三方节点数据不强加字段**：从上游订阅和磁盘爬虫提取的节点，保持其原有字段。如果节点原本没有 `categories` 字段，绝不添加；原本有则原样保留。
- **门面主站定制**：仅对 `TOP_SITES_FACADE` 列表中置顶的 7 大门面主站，保留矩形海报比例（`ratio: 1.33`）、请求头 (`header`) 及分类配置。

## 3. 切片提纯与字符解转义
- **详情接口访问**：提取播放切片地址时，统一访问 `?ac=detail` 详情接口，不使用无播放地址的 `?ac=list` 接口。
- **JSON 转义斜杠还原**：MacCMS 返回的 JSON 文本中包含转义斜杠 `\/`，在进行正则表达式提取前，必须优先执行 `text.replace('\\/', '/')` 与 `text.replace('&amp;', '&')`。
- **核心切片域名保底**：配合 `KNOWN_CORE_STREAM_CDNS` 列表（如 `ffzy-online6.com`、`ffzy-play5.com`、`yaaabc.com` 等），确保核心播放切片域名稳固存活。

## 4. 多仓与接口回写
- **多仓 JSON 导出**：生成包含 `urls`、`stores` 和 `storeHouse` 完整结构的 `tvbox_multi.json` 文件。
- **接口列表回写**：提取所有有效站点的名称与 API 链接，格式化回写生成 `sources.txt`。
