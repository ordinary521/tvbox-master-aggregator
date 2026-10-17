#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立任务一：全网资源配置合并、全量 PY 爬虫源码内嵌域名深度提纯与 18+ 隔离 (1:1 原装+深度提取版)
=============================================================================
重点更新：
  1. 100% 配置文件驱动：动态读取 config/source_urls.json (含 web_sources 与 upstream_endpoints 全量订阅源)；
  2. 磁盘 PY 源码深度提取：全量读取 repos/ 下所有 .py 脚本内部源码，解转义 \\/ 后爆抓源码内部所有内嵌域名；
  3. JSON 字段全量提取：不仅抓 api，深度提取 ext, jar, playUrl 中的内嵌链接；
  4. 0 并发纯单线程串行提取核心采集站 ?ac=detail 详情解转义 vod_play_url 深层切片 CDN (如 v13.yaaabc.com, super.ffzy-online6.com)；
  5. 18+ 点播隔离 (SEX_KEYWORDS 含“叔叔”、“侄女”、“cao”、“十八”等)，隔离写入 not_suitable/tvbox.json；
  6. 7 大顶级置顶门面 (TOP_SITES_FACADE，带 1.33 矩形海报比例与完整 Header)；
  7. 全套 IJK 软硬解码、ADS 广告拦截、tvbox_multi.json 多仓导出与 sources.txt 接口回写。
=============================================================================
"""

import json
import os
import re
import ssl
import sys
import time
import subprocess
import urllib.parse
from urllib.parse import urlparse

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(WORK_DIR, "config")
PROCESS_DIR = os.path.join(WORK_DIR, "process")
NOT_SUITABLE_DIR = os.path.join(WORK_DIR, "not_suitable")
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(PROCESS_DIR, exist_ok=True)
os.makedirs(NOT_SUITABLE_DIR, exist_ok=True)

CF_PROXY = os.environ.get("CF_PROXY", "")
GH_PROXY_PREFIX = "https://gh-proxy.com/"

CLEANED_51_CATEGORIES = [
    "动漫", "动作片", "喜剧片", "爱情片", "科幻片", "恐怖片", "剧情片", "战争片",
    "国产剧", "欧美剧", "韩剧", "日剧", "港剧", "台剧", "泰剧", "纪录片",
    "海外剧", "大陆综艺", "日韩综艺", "港台综艺", "欧美综艺", "国产动漫", "日韩动漫", "欧美动漫",
    "动画片", "港台动漫", "海外动漫", "演唱会", "体育赛事", "篮球", "足球", "预告片",
    "斯诺克", "影视解说", "爽文短剧", "4K电影", "有声动漫", "女频恋爱", "反转爽剧", "古装仙侠",
    "年代穿越", "脑洞悬疑", "现代都市", "邵氏电影", "Netflix自制剧", "Netflix电影", "科普学习", "漫剧"
]

KNOWN_CORE_STREAM_CDNS = [
    "ffzy-online.com", "ffzy-online5.com", "ffzy-online6.com", "ffzy-play5.com",
    "ffzy-play1.com", "ffzy-play3.com", "ffm3u8.com", "ffzyapi.com", "ffzy5.tv",
    "yaaabc.com", "cyscyy.com", "wkcyvs.cn", "okzyw.org", "okzyw.net",
    "jszyapi.com", "360zy.com", "suoniapi.com", "yayazy.net", "wolongzyw.com",
    "bfzyapi.com", "lziapi.com", "feisuzyapi.com", "hongniuzy2.com"
]

CORE_MACCMS_DETAIL_APIS = [
    ("非凡资源", "https://ffzy5.tv/api.php/provide/vod/?ac=detail&pg=1"),
    ("OK资源", "http://api.okzyw.net/api.php/provide/vod/?ac=detail&pg=1"),
    ("360采集", "https://360zy.com/api.php/provide/vod/?ac=detail&pg=1"),
    ("索尼高清", "https://suoniapi.com/api.php/provide/vod/?ac=detail&pg=1"),
    ("极速云播", "https://jszyapi.com/api.php/provide/vod/?ac=detail&pg=1"),
    ("鸭鸭资源", "https://cj.yayazy.net/api.php/provide/vod/?ac=detail&pg=1"),
    ("卧龙资源", "https://collect.wolongzyw.com/api.php/provide/vod/?ac=detail&pg=1"),
    ("暴风资源", "https://bfzyapi.com/api.php/provide/vod/?ac=detail&pg=1"),
    ("飞速资源", "https://feisuzyapi.com/api.php/provide/vod/?ac=detail&pg=1"),
    ("量子资源", "https://cj.lziapi.com/api.php/provide/vod/?ac=detail&pg=1"),
    ("红牛资源", "https://www.hongniuzy2.com/api.php/provide/vod/?ac=detail&pg=1")
]

TOP_SITES_FACADE = [
    {
        "key": "kkys_master",
        "name": "💎可可影视┃4K高清",
        "type": 3,
        "api": "https://gh-proxy.com/https://raw.githubusercontent.com/royalhayga/tvbox-master-aggregator/main/scripts/kkys_master.py",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "header": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.kkys20.com/"
        },
        "style": { "type": "rect", "ratio": 1.33 }
    },
    {
        "key": "czzy_py",
        "name": "💎厂长资源┃1080P",
        "type": 3,
        "api": "https://gh-proxy.com/https://raw.githubusercontent.com/jie20091116/cat/a201c9690267c1ab4e3f65d5a1fca80662438fa0/TVBOX/PY/czzy.py",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "style": { "type": "rect", "ratio": 1.33 }
    },
    {
        "key": "OK资源",
        "name": "🔥OK-资源",
        "type": 0,
        "api": "http://api.okzyw.net/api.php/provide/vod/from/okm3u8/at/xml",
        "playUrl": "https://jiexi.okzyw.org/m3u8/?url=",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "categories": CLEANED_51_CATEGORIES
    },
    {
        "key": "鸭鸭资源",
        "name": "🦆鸭鸭资源",
        "type": 0,
        "api": "https://cj.yayazy.net/api.php/provide/vod/from/yym3u8/at/xml",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "categories": CLEANED_51_CATEGORIES
    },
    {
        "key": "360资源",
        "name": "🦚360┃采集",
        "type": 1,
        "api": "https://360zy.com/api.php/provide/vod?",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "categories": [
            "动作片", "喜剧片", "爱情片", "科幻片", "恐怖片", "剧情片", "战争片", "古装片",
            "悬疑片", "犯罪片", "灾难片", "国产剧", "香港剧", "韩国剧", "欧美剧", "台湾剧",
            "日本剧", "海外剧", "泰国剧", "大陆综艺", "港台综艺", "日韩综艺", "欧美综艺", "国产动漫",
            "欧美动漫", "日韩动漫", "现代都市", "脑洞悬疑", "年代穿越", "古装仙侠", "女频恋爱", "成长逆袭", "爽文短剧"
        ]
    },
    {
        "key": "索尼资源",
        "name": "🐉索尼┃高清4K",
        "type": 1,
        "api": "https://suoniapi.com/api.php/provide/vod/?ac=list",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "categories": [
            "动作片", "喜剧片", "科幻片", "恐怖片", "爱情片", "剧情片", "战争片", "记录片",
            "国产剧", "欧美剧", "香港剧", "韩国剧", "台湾剧", "日本剧", "海外剧", "泰国剧",
            "国产动漫", "日韩动漫", "欧美动漫", "港台动漫", "海外动漫", "大陆综艺", "港台综艺", "日韩综艺", "欧美综艺"
        ]
    },
    {
        "key": "极速资源",
        "name": "⚡极速┃云播",
        "type": 1,
        "api": "https://jszyapi.com/api.php/provide/vod/",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "categories": CLEANED_51_CATEGORIES
    }
]

SEX_KEYWORDS = [
    "x站", "18+", "色情", "伦理", "成人", "福利", "三级", "激情", "av",
    "杏吧", "极品x", "免费x", "嘿嘿", "火速", "红楼", "优优", "天美",
    "香蕉", "番茄", "黑料", "黄色仓库", "小鸡", "细胞", "大地", "奶香香",
    "桃花", "ck伦理", "大奶子", "搜av", "奥斯卡", "jkun", "滴滴", "豆豆",
    "精品x", "鲨鱼", "辣椒", "森林", "155", "色猫", "乐播", "玉兔",
    "老色p", "老色批", "番号", "sex", "adult", "porn", "91", "黄",
    "久草", "大x子", "老色x", "写真",
    "①⑧", "🔞", "18/", "小师妹", "奶茶", "探探", "pgx", "小师妹资源", "奶茶资源", "探探资源", "pgx资源",
    "18av", "4kav", "18jtv", "2048", "777wuye", "8x8x", "91porn", "91crdj", "asmrhoney", "adult",
    "mamazipai", "missav", "mitaoav", "nanrenbense", "owoav", "seba", "sebo", "shaofu", "sinparty",
    "xhamster", "yiqicao", "youav", "zhengmeiav", "色播", "风欲", "萝莉av", "xxx", "nsfw", "叔",
    "色", "阴", "撸", "少女", "侄女", "妻", "草榴", "萝莉", "鉴黄", "黄色", "香肠", "叔叔", "cao", "18"
]

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_surface_domain(url):
    if not url or not isinstance(url, str): return None
    clean = url.strip()
    m = re.search(r'https?://([^/:\?#]+)', clean, re.I)
    if m:
        dom = m.group(1).lower().strip()
        if dom and "." in dom and not dom.replace('.', '').isdigit():
            return dom
    return None

def is_blacklisted(text):
    if not text: return False
    lower_text = str(text).lower()
    return any(kw in lower_text for kw in SEX_KEYWORDS)

def is_garbled_name(name):
    if not name: return True
    if re.search(r'[рҹв”еҗҲйӣҶзҒ«]', name):
        return True
    return False

def curl(url, timeout=10, via_proxy=False):
    actual_url = f"{CF_PROXY}?u={urllib.parse.quote(url, safe='')}" if (via_proxy and CF_PROXY) else url
    try:
        r = subprocess.run(["curl", "-s", "-L", "--connect-timeout", str(timeout),
                           "--max-time", str(timeout*2), "-A", "Mozilla/5.0", actual_url],
                          capture_output=True, timeout=timeout*2+5)
        return r.stdout.decode("utf-8", errors="replace")
    except Exception:
        return ""

def parse_json(raw):
    if not raw: return None
    raw = raw.lstrip('﻿')
    raw = re.sub(r',(\s*[}\]])', r'\1', raw)
    try: return json.loads(raw, strict=False)
    except Exception:
        s, e = raw.find('{'), raw.rfind('}')
        if s >= 0 and e > s:
            try: return json.loads(raw[s:e+1], strict=False)
            except Exception: pass
    return None

def resolve_spider(spider, source_url):
    if not spider: return ""
    if spider.startswith("http"):
        if "raw.githubusercontent.com" in spider or "github.com" in spider:
            return f"{GH_PROXY_PREFIX}{spider}"
        return spider
    if spider.startswith("./"):
        p = urlparse(source_url)
        return f"{p.scheme}://{p.netloc}{spider[1:]}"
    return spider

def clean_api_url(api):
    if not api: return ""
    api = str(api).strip()
    api = re.sub(r'[\?&]ac=(list|detail|videolist|vod).*$', '', api, flags=re.I)
    return api.rstrip("/")

def fetch_deep_stream_domains_sequentially():
    """纯单线程串行请求 20 核心采集站 ?ac=detail 详情接口，解转义后爆抓 vod_play_url 深层切片 CDN"""
    deep_domains = set(KNOWN_CORE_STREAM_CDNS)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for name, api_url in CORE_MACCMS_DETAIL_APIS:
        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=4) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
                text = text.replace('\\/', '/').replace('&amp;', '&')
                urls = re.findall(r'https?://[a-zA-Z0-9\.\-_]+', text)
                for u in urls:
                    dom = extract_surface_domain(u)
                    if dom:
                        deep_domains.add(dom)
        except Exception: pass

    return sorted(list(deep_domains))

def scan_all_py_scripts_from_repos():
    """扫描 repos/ 下所有已克隆仓库中的 .py 爬虫源码，全量读取 .py 内部源码提取所有内嵌域名"""
    print("  [磁盘 PY 源码深度扫描器] 正在全量扫描 repos/ 下所有 .py 爬虫源码内容...", flush=True)
    scanned_sites = []
    inner_code_domains = set()

    repos_dir = os.path.join(WORK_DIR, "repos")
    if os.path.exists(repos_dir):
        for root, _, files in os.walk(repos_dir):
            for fname in sorted(files):
                if fname.endswith(".py") and not fname.startswith("test") and not fname.startswith("setup"):
                    clean_stem = fname[:-3]
                    if is_blacklisted(fname) or is_blacklisted(clean_stem):
                        continue

                    fpath = os.path.join(root, fname)

                    # 深度读取 .py 源码文件内容，提取内嵌 HTTP/HTTPS 目标域名
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            py_code = f.read()
                            # 先将转义斜杠 \/ 替换还原
                            py_code_clean = py_code.replace('\\/', '/').replace('&amp;', '&')
                            raw_urls = re.findall(r'https?://[a-zA-Z0-9\.\-_]+', py_code_clean)
                            for u in raw_urls:
                                dom = extract_surface_domain(u)
                                if dom:
                                    inner_code_domains.add(dom)
                    except Exception: pass

                    rel_path = os.path.relpath(fpath, repos_dir).replace("\\", "/")
                    parts = rel_path.split("/")
                    repo_name = parts[0]
                    sub_path = "/".join(parts[1:])

                    repo_github_map = {
                        "cat": "https://raw.githubusercontent.com/jie20091116/cat/a201c9690267c1ab4e3f65d5a1fca80662438fa0/TVBOX/PY/",
                        "qist": "https://raw.githubusercontent.com/qist/tvbox/main/py/"
                    }

                    if repo_name in repo_github_map:
                        raw_github_url = f"{repo_github_map[repo_name]}{os.path.basename(fname)}"
                    else:
                        raw_github_url = f"https://raw.githubusercontent.com/{repo_name}/main/{sub_path}"

                    proxied_url = f"{GH_PROXY_PREFIX}{raw_github_url}"

                    site_obj = {
                        "key": f"py_{repo_name}_{clean_stem}",
                        "name": f"💎{clean_stem}┃[{repo_name.upper()}]",
                        "type": 3,
                        "api": proxied_url,
                        "searchable": 1,
                        "quickSearch": 1,
                        "filterable": 1,
                        "style": { "type": "rect", "ratio": 1.33 }
                    }
                    scanned_sites.append(site_obj)

    print(f"  └─ 本地磁盘 PY 源码深度提取完成！捕获 {len(scanned_sites)} 个 PY 节点，提纯源码内嵌域名 {len(inner_code_domains)} 个！", flush=True)
    return scanned_sites, sorted(list(inner_code_domains))

def load_source_urls_config():
    """动态读取 config/source_urls.json 配置文件 (0 代码硬编码)"""
    config_path = os.path.join(CONFIG_DIR, "source_urls.json")
    sources = []
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("web_sources", []):
                    u = item.get("url", "").strip()
                    if u:
                        html = curl(u, 20)
                        src_urls = re.findall(r'data-url="([^"]+)"', html)
                        src_names = re.findall(r'<td class="td-name">([^<]+)</td>', html)
                        for n_str, u_str in zip(src_names, src_urls):
                            if u_str.strip() and not u_str.strip().startswith("#"):
                                sources.append((n_str.strip(), u_str.strip().replace("&amp;", "&")))

                for item in data.get("upstream_endpoints", []):
                    n_str = item.get("name", "upstream")
                    u_str = item.get("url", "").strip()
                    if u_str:
                        sources.append((n_str, u_str))
        except Exception as e:
            print(f"  └─ 读取 config/source_urls.json 出错: {e}")
    return sources

def merge_sources():
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] [01_merge_sources] 开始全量多源抓取、PY 源码深度爆抓与 1:1 黄金原装重构...")

    spider_jars = {}
    sources = load_source_urls_config()

    # 1. 串行拉取 20 核心采集站解转义切片 CDN (含 KNOWN_CORE_STREAM_CDNS)
    deep_stream_domains = fetch_deep_stream_domains_sequentially()

    # 2. 深度扫描 repos/ 下所有 .py 源码文件，提取内嵌全量域名
    all_scanned_py, py_inner_domains = scan_all_py_scripts_from_repos()

    all_sites = list(TOP_SITES_FACADE) + all_scanned_py
    all_lives, all_parses = [], []
    adult_ns_sites = []

    seen_site_signatures = set()
    seen_keys = set()

    json_inner_domains = set()

    for facade in all_sites:
        sig = f"{facade.get('api')}_{facade.get('ext')}_{facade.get('jar')}"
        seen_site_signatures.add(sig)
        seen_keys.add(facade["key"])

    rest_sites = []

    for name, url in sources:
        raw_json_str = curl(url, 15)
        # 从原始 JSON 字符串中全量正则表达式提取所有网址
        if raw_json_str:
            clean_json_str = raw_json_str.replace('\\/', '/').replace('&amp;', '&')
            for u_match in re.findall(r'https?://[a-zA-Z0-9\.\-_]+', clean_json_str):
                dom_m = extract_surface_domain(u_match)
                if dom_m:
                    json_inner_domains.add(dom_m)

        data = parse_json(raw_json_str)
        if not data: continue

        spider = data.get("spider", "")
        if spider:
            abs_spider = resolve_spider(spider, url)
            spider_jars[abs_spider] = spider_jars.get(abs_spider, 0) + 1

        for s in (data.get("sites") or []):
            key = s.get("key", "")
            raw_name = s.get("name", key)
            api = s.get("api", "")
            ext = s.get("ext", "")
            jar = s.get("jar", "")

            clean_n = re.sub(r'^\[.*?\]\s*', '', raw_name).strip()
            clean_api = clean_api_url(api) if (isinstance(api, str) and api.startswith("http")) else api

            if not key or is_blacklisted(raw_name) or is_blacklisted(str(api)):
                adult_ns_sites.append(s)
                continue

            if is_garbled_name(clean_n): continue

            site_sig = f"{clean_api}_{json.dumps(ext) if isinstance(ext, (dict, list)) else ext}_{jar}"
            if site_sig in seen_site_signatures:
                continue
            seen_site_signatures.add(site_sig)

            if key in seen_keys:
                key = f"{key}_{len(seen_keys)}"
            seen_keys.add(key)

            s["key"] = key
            s["name"] = f"[{name}] {clean_n}"
            if clean_api:
                s["api"] = clean_api

            if isinstance(s.get("api"), str) and ("raw.githubusercontent.com" in s["api"] or "github.com" in s["api"]) and not s["api"].startswith(GH_PROXY_PREFIX):
                s["api"] = f"{GH_PROXY_PREFIX}{s['api']}"

            if isinstance(s.get("jar"), str) and ("raw.githubusercontent.com" in s["jar"] or "github.com" in s["jar"]) and not s["jar"].startswith(GH_PROXY_PREFIX):
                s["jar"] = f"{GH_PROXY_PREFIX}{s['jar']}"

            if spider and "jar" not in s and "spider" not in s:
                s["jar"] = resolve_spider(spider, url)

            if s.get("type") == 3 or (isinstance(s.get("api"), str) and s["api"].endswith(".py")):
                s["searchable"] = 1
                s["quickSearch"] = 1
                s["filterable"] = 1

            rest_sites.append(s)

        for l in (data.get("lives") or []):
            u = l.get("url", "")
            if u: all_lives.append(l)
        for p in (data.get("parses") or []):
            u = p.get("url", "")
            if u: all_parses.append(p)

    all_sites.extend(rest_sites)

    for s in all_sites:
        if s.get("type") == 3 or (isinstance(s.get("api"), str) and s["api"].endswith(".py")):
            s["searchable"] = 1
            s["quickSearch"] = 1
            s["filterable"] = 1

    # 全量提取明面与内嵌域名 (切片 + PY 源码内嵌 + 上游 JSON 全字段)
    all_combined_domains = set(deep_stream_domains).union(py_inner_domains).union(json_inner_domains)
    for s in all_sites:
        dom = extract_surface_domain(s.get("api", ""))
        if dom: all_combined_domains.add(dom)

    sorted_surface_domains = sorted(list(all_combined_domains))

    grouped_data = {
        "top_facade_domains": sorted_surface_domains,
        "media_player_domains": sorted(list(set(deep_stream_domains).union(py_inner_domains))),
        "deep_stream_domains": sorted(list(set(deep_stream_domains).union(py_inner_domains)))
    }
    open(os.path.join(PROCESS_DIR, "grouped_cdn_domains.json"), "w", encoding="utf-8").write(
        json.dumps(grouped_data, ensure_ascii=False, indent=2)
    )

    DEFAULT_FLAGS = ["youku", "qq", "iqiyi", "qiyi", "letv", "sohu", "tudou", "pptv", "mgtv", "wasu"]
    DEFAULT_IJK = [
        {"group": "软解码", "options": [{"category": 4, "name": "opensles", "value": "0"}, {"category": 4, "name": "overlay-format", "value": "842225234"}, {"category": 4, "name": "framedrop", "value": "1"}, {"category": 4, "name": "soundtouch", "value": "1"}, {"category": 4, "name": "start-on-prepared", "value": "1"}, {"category": 1, "name": "http-detect-range-support", "value": "0"}, {"category": 1, "name": "fflags", "value": "fastseek"}, {"category": 2, "name": "skip_loop_filter", "value": "48"}, {"category": 4, "name": "reconnect", "value": "1"}, {"category": 4, "name": "max-buffer-size", "value": "5242880"}, {"category": 4, "name": "enable-accurate-seek", "value": "0"}, {"category": 4, "name": "mediacodec", "value": "0"}, {"category": 4, "name": "mediacodec-auto-rotate", "value": "0"}, {"category": 4, "name": "mediacodec-handle-resolution-change", "value": "0"}, {"category": 4, "name": "mediacodec-hevc", "value": "0"}]},
        {"group": "硬解码", "options": [{"category": 4, "name": "opensles", "value": "0"}, {"category": 4, "name": "overlay-format", "value": "842225234"}, {"category": 4, "name": "framedrop", "value": "1"}, {"category": 4, "name": "soundtouch", "value": "1"}, {"category": 4, "name": "start-on-prepared", "value": "1"}, {"category": 1, "name": "http-detect-range-support", "value": "0"}, {"category": 1, "name": "fflags", "value": "fastseek"}, {"category": 2, "name": "skip_loop_filter", "value": "48"}, {"category": 4, "name": "reconnect", "value": "1"}, {"category": 4, "name": "max-buffer-size", "value": "5242880"}, {"category": 4, "name": "enable-accurate-seek", "value": "0"}, {"category": 4, "name": "mediacodec", "value": "1"}, {"category": 4, "name": "mediacodec-auto-rotate", "value": "1"}, {"category": 4, "name": "mediacodec-handle-resolution-change", "value": "1"}, {"category": 4, "name": "mediacodec-hevc", "value": "1"}]}
    ]
    DEFAULT_ADS = [
        "mimg.0c1q0l.cn", "www.googletagmanager.com", "www.google-analytics.com", "mc.usihnbcq.cn", "mg.g1mm3d.cn", "mscs.svaeuzh.cn", "cnzz.hhttm.top", "tp.vinuxhome.com", "cnzz.mmstat.com", "www.baihuillq.com", "s23.cnzz.com", "z3.cnzz.com", "c.cnzz.com", "stj.v1vo.top", "z12.cnzz.com", "img.mosflower.cn", "tips.gamevvip.com", "ehwe.yhdtns.com", "xdn.cqqc3.com", "www.jixunkyy.cn", "sp.chemacid.cn", "hm.baidu.com", "s9.cnzz.com", "z6.cnzz.com", "um.cavuc.com", "mav.mavuz.com", "wofwk.aoidf3.com", "z5.cnzz.com", "xc.hubeijieshikj.cn", "tj.tianwenhu.com", "xg.gars57.cn", "k.jinxiuzhilv.com", "cdn.bootcss.com", "ppl.xunzhuo123.com", "xomk.jiangjunmh.top", "img.xunzhuo123.com", "z1.cnzz.com", "s13.cnzz.com", "xg.huataisangao.cn", "z7.cnzz.com", "xg.huataisangao.cn", "z2.cnzz.com", "s96.cnzz.com", "q11.cnzz.com", "thy.dacedsfa.cn", "xg.whsbpw.cn", "s19.cnzz.com", "z8.cnzz.com", "s4.cnzz.com", "f5w.as12df.top", "ae01.alicdn.com", "www.92424.cn", "k.wudejia.com", "vivovip.mmszxc.top", "qiu.xixiqiu.com", "cdnjs.hnfenxun.com", "cms.qdwght.com"
    ]

    master_lives = [
        {
            "name": "🔥TVBox 高清央视/卫视/美英直播源",
            "type": 0,
            "url": "https://gh-proxy.com/https://raw.githubusercontent.com/royalhayga/tvbox-master-aggregator/main/live.txt"
        }
    ]

    master_config = {
        "spider": "",
        "wallpaper": "https://bing.img.run/1920x1080.php",
        "sites": all_sites,
        "lives": master_lives,
        "parses": all_parses[:20],
        "flags": DEFAULT_FLAGS,
        "ijk": DEFAULT_IJK,
        "ads": DEFAULT_ADS,
        "note": "本配置由 TVBox 全量资源抓取、PY 源码内嵌域名深度爆抓与深层切片提纯引擎生成。"
    }

    with open(os.path.join(WORK_DIR, "tvbox.json"), "w", encoding="utf-8") as f:
        json.dump(master_config, f, ensure_ascii=False, indent=2)

    with open(os.path.join(WORK_DIR, "tvbox_full.json"), "w", encoding="utf-8") as f:
        json.dump(master_config, f, ensure_ascii=False, indent=2)

    multi_stores = [{"sourceName": name, "sourceUrl": url} for name, url in sources]
    multi = {
        "urls": [{"name": m["sourceName"], "url": m["sourceUrl"]} for m in multi_stores],
        "stores": multi_stores,
        "storeHouse": multi_stores
    }
    with open(os.path.join(WORK_DIR, "tvbox_multi.json"), "w", encoding="utf-8") as f:
        json.dump(multi, f, ensure_ascii=False, indent=2)

    with open(os.path.join(WORK_DIR, "sources.txt"), "w", encoding="utf-8") as f:
        f.write(f"# {ts}\n\n")
        for s in all_sites:
            api = s.get("api", "")
            if isinstance(api, str) and api.startswith("http"):
                f.write(f"{s['name']}\n{api}\n\n")

    ns_dir = os.path.join(WORK_DIR, "not_suitable")
    os.makedirs(ns_dir, exist_ok=True)

    ns_config = dict(master_config)
    ns_config["sites"] = adult_ns_sites
    ns_config["note"] = "本文件放置于隔离目录 not_suitable/，单独收录 18+ 点播采集站。"

    with open(os.path.join(ns_dir, "tvbox.json"), "w", encoding="utf-8") as f:
        json.dump(ns_config, f, ensure_ascii=False, indent=2)

    print(f"  ├─ 成功隔离 {len(adult_ns_sites)} 个 18+ 点播采集站写入: not_suitable/tvbox.json")
    print(f"  └─ [01_merge_sources] 完成！全量合并收录 {len(all_sites)} 个有效纯净站点，提纯内嵌域名 {len(sorted_surface_domains)} 个到 grouped_cdn_domains.json！")
    return all_sites

if __name__ == "__main__":
    merge_sources()
