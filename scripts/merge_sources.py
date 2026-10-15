# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本一：纯净分类合并器 (merge_sources.py)
=============================================================================
重点更新：
  1. 100% 原封不动完整保留原装 categories (分类数组)、ext、style、header 等全量属性，绝不乱删精简；
  2. 动态继承 7 大置顶主站的 categories 完整分类标签，彻底解决前几名主站顶部分类丢惨问题；
  3. 扩充 18+ 黑名单敏感词：加入“叔叔”、“侄女”、“侄女儿”、“cao”、“十八”等词汇；
  4. 确定性拼音 A-Z 优雅排序 + 代码级安全去重 (同名同 API 才合并，同名不同 API 编号保留)；
  5. 100% 零外联网络请求 (0 发包/0 探测)。
=============================================================================
"""

import os
import re
import json

try:
    import pypinyin
    def get_pinyin(text):
        return "".join(pypinyin.lazy_pinyin(text)).lower()
except Exception:
    def get_pinyin(text):
        return str(text).lower()

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESS_DIR = os.path.join(WORK_DIR, "process")
NOT_SUITABLE_DIR = os.path.join(WORK_DIR, "not_suitable")
os.makedirs(PROCESS_DIR, exist_ok=True)
os.makedirs(NOT_SUITABLE_DIR, exist_ok=True)

# 18+ 敏感词过滤正则 (扩展“叔叔”、“侄女”、“侄女儿”、“cao”、“十八”)
ADULT_KEYWORDS_PATTERN = re.compile(
    r'(色情|无码|有码|麻豆|果冻|天美|果冻传媒|星空传媒|糖心|皇家|精东|九一|91|探花|猎奇|黑料|约炮|自拍|偷拍|黄|成人|AV|乱伦|强奸|变态|国产精品|日韩精品|欧美无码|三级|18\+|性爱|高潮|湿透|强暴|幼女|萝莉|熟女|孕妇|重口|BDSM|SM|绑架|调教|虐待|喷水|口交|乳交|肛交|换妻|群交|破处|大鸟|黑人|巨乳|人妻|奶水|男同|女同|LGBT|勾引|出轨|绿帽|空姐|技师|少妇|后宫|性奴|迷奸|代孕|叔叔|侄女|侄女儿|cao|十八)',
    re.IGNORECASE
)

# 7 大黄金原装置顶主站基础门面 (TOP_SITES_FACADE_BASE)
TOP_SITES_FACADE_BASE = [
    {
        "key": "kkys_master",
        "name": "💎可可影视┃4K高清",
        "type": 3,
        "api": "https://raw.githubusercontent.com/royalhayga/tvbox-master-aggregator/main/scripts/kkys_master.py",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "categories": ["电影", "连续剧", "动漫", "综艺", "短剧"]
    },
    {
        "key": "py_czzy",
        "name": "💎厂长资源┃1080P",
        "type": 3,
        "api": "https://raw.githubusercontent.com/jie20091116/cat/main/TVBOX/PY/czzy.py",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "categories": ["电影", "电视剧", "动漫", "综艺", "纪录片"]
    },
    {
        "key": "ok_zy",
        "name": "🔥OK-资源",
        "type": 1,
        "api": "http://api.okzyw.net/api.php/provide/vod/from/okm3u8/at/xml",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1
    },
    {
        "key": "yaya_zy",
        "name": "🦆鸭鸭资源",
        "type": 1,
        "api": "https://cj.yayazy.net/api.php/provide/vod/from/yym3u8/at/xml",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1
    },
    {
        "key": "360_zy",
        "name": "🦚360┃采集",
        "type": 1,
        "api": "https://360zy.com/api.php/provide/vod?",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1
    },
    {
        "key": "suoni_zy",
        "name": "🐉索尼┃高清4K",
        "type": 1,
        "api": "https://suoniapi.com/api.php/provide/vod/?ac=list",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1
    },
    {
        "key": "js_zy",
        "name": "⚡极速┃云播",
        "type": 1,
        "api": "https://jszyapi.com/api.php/provide/vod/",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1
    }
]

def extract_surface_domain(url):
    """从 URL 中直接提取明面上的表面域名 (xxx.com)"""
    if not url or not isinstance(url, str): return None
    clean = url.strip()
    m = re.search(r'https?://([^/:\?#]+)', clean, re.I)
    if m:
        dom = m.group(1).lower().strip()
        if dom and "." in dom and not dom.replace('.', '').isdigit():
            return dom
    return None

def is_adult_content(text):
    if not text: return False
    return bool(ADULT_KEYWORDS_PATTERN.search(str(text)))

def scan_repos_for_py_spiders():
    """全量扫描 repos/ 下所有 .py 爬虫源码，提取明面上的表面域名与节点信息"""
    py_sites = []
    surface_domains = set()
    repos_dir = os.path.join(WORK_DIR, "repos")

    facade_keys = {s["key"] for s in TOP_SITES_FACADE_BASE}

    if os.path.exists(repos_dir):
        for root, _, files in os.walk(repos_dir):
            for file in sorted(files):
                if file.endswith(".py") and not file.startswith("test_"):
                    fpath = os.path.join(root, file)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        urls = re.findall(r'https?://[a-zA-Z0-9\.\-_]+', content)
                        for u in urls:
                            dom = extract_surface_domain(u)
                            if dom: surface_domains.add(dom)

                        m_name = re.search(r'def\s+getName\s*\([^)]*\):\s*return\s*["\']([^"\']+)["\']', content)
                        sname = m_name.group(1).strip() if m_name else os.path.splitext(file)[0]

                        rel_path = os.path.relpath(fpath, WORK_DIR).replace("\\", "/")
                        raw_api = f"https://raw.githubusercontent.com/royalhayga/tvbox-master-aggregator/main/{rel_path}"
                        skey = f"py_{os.path.splitext(file)[0]}"

                        if skey in facade_keys:
                            continue

                        site_node = {
                            "key": skey,
                            "name": sname,
                            "type": 3,
                            "api": raw_api,
                            "searchable": 1,
                            "quickSearch": 1,
                            "filterable": 1
                        }

                        if not is_adult_content(sname) and not is_adult_content(content[:500]):
                            py_sites.append(site_node)
                    except Exception: pass

    # 按中文名称拼音 A-Z 优雅排序
    py_sites.sort(key=lambda s: get_pinyin(s["name"]))
    return py_sites, sorted(list(surface_domains))

def parse_qist_tvbox_json():
    """解析 repos/qist 里的接口配置，100% 完整保留 categories、ext、style 等全量原装属性，绝不精简！"""
    qist_sites = []
    adult_sites = []
    surface_domains = set()
    facade_sites_map = {}

    qist_json_path = os.path.join(WORK_DIR, "repos", "qist", "tvbox.json")
    if os.path.exists(qist_json_path):
        try:
            with open(qist_json_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
                sites = data.get("sites", [])
                for s in sites:
                    # 原封不动保留整个字典 s 的全量属性！
                    api = str(s.get("api", ""))
                    name = str(s.get("name", ""))
                    key = str(s.get("key", ""))
                    dom = extract_surface_domain(api)
                    if dom: surface_domains.add(dom)

                    # 动态捕获并继承 7 大置顶主站的 categories / ext 等完整原装属性：
                    if "okzy" in api or "okzyw" in api:
                        s_copy = dict(s)
                        s_copy["name"] = "🔥OK-资源"
                        facade_sites_map["ok_zy"] = s_copy
                        continue
                    elif "360zy" in api:
                        s_copy = dict(s)
                        s_copy["name"] = "🦚360┃采集"
                        facade_sites_map["360_zy"] = s_copy
                        continue
                    elif "suoni" in api:
                        s_copy = dict(s)
                        s_copy["name"] = "🐉索尼┃高清4K"
                        facade_sites_map["suoni_zy"] = s_copy
                        continue
                    elif "jszy" in api:
                        s_copy = dict(s)
                        s_copy["name"] = "⚡极速┃云播"
                        facade_sites_map["js_zy"] = s_copy
                        continue
                    elif "yayazy" in api:
                        s_copy = dict(s)
                        s_copy["name"] = "🦆鸭鸭资源"
                        facade_sites_map["yaya_zy"] = s_copy
                        continue

                    if is_adult_content(name) or s.get("style", {}).get("type") == "rect":
                        adult_sites.append(s)
                    else:
                        qist_sites.append(s)
        except Exception: pass

    # 按中文名称拼音 A-Z 优雅排序
    qist_sites.sort(key=lambda s: get_pinyin(s["name"]))
    return qist_sites, adult_sites, sorted(list(surface_domains)), facade_sites_map

def deduplicate_sites_safely(raw_sites):
    """【代码级安全去重 (0 误杀资源)】
    - 只有【名称相同】且【api 链接相同】时才合并去重；
    - 若【名称相同】但【api 链接不同】(代表不同接口资源)，绝对不删除，自动重命名扩展 [二]、[三] 100% 完整保留！
    """
    seen_api_set = set()
    name_count_map = {}
    clean_sites = []

    for s in raw_sites:
        api_val = str(s.get("api", "")).strip()
        name_val = str(s.get("name", "")).strip()

        # 1. 名称相同且 api 链接 100% 相同的真实重复节点 ➔ 合并去重
        dedup_key = f"{name_val}:::{api_val}"
        if dedup_key in seen_api_set:
            continue
        seen_api_set.add(dedup_key)

        # 2. 名称相同但 api 链接不同 (不同切片源) ➔ 100% 完整保留，重命名区分 [二]、[三]
        if name_val in name_count_map:
            name_count_map[name_val] += 1
            num_str = ["二", "三", "四", "五", "六", "七", "八", "九", "十"][min(name_count_map[name_val] - 2, 8)]
            s["name"] = f"{name_val} [{num_str}]"
        else:
            name_count_map[name_val] = 1

        clean_sites.append(s)

    return clean_sites

def merge_sources():
    print("  [01_merge_sources] 开始全量资源合并、categories 原装属性完整保留与安全去重 (0 联网发包版)...", flush=True)

    py_sites, py_domains = scan_repos_for_py_spiders()
    qist_sites, adult_sites, qist_domains, facade_sites_map = parse_qist_tvbox_json()

    # 动态将原装库里富含 categories 的字典替换回置顶门面列表
    top_facade_full = []
    for base_node in TOP_SITES_FACADE_BASE:
        fkey = base_node["key"]
        if fkey in facade_sites_map:
            top_facade_full.append(facade_sites_map[fkey])
        else:
            top_facade_full.append(base_node)

    facade_domains = [extract_surface_domain(s["api"]) for s in top_facade_full if extract_surface_domain(s.get("api"))]
    all_surface_domains = sorted(list(set(facade_domains + py_domains + qist_domains)))

    # 黄金 7 大原装置顶门面坐镇 tvbox.json 最顶端 1~7 名
    raw_all_sites = top_facade_full + py_sites + qist_sites

    # 执行【代码级安全去重】
    all_clean_sites = deduplicate_sites_safely(raw_all_sites)

    # 写盘 process/grouped_cdn_domains.json
    grouped_data = {
        "top_facade_domains": all_surface_domains,
        "media_player_domains": [],
        "deep_stream_domains": []
    }
    open(os.path.join(PROCESS_DIR, "grouped_cdn_domains.json"), "w", encoding="utf-8").write(
        json.dumps(grouped_data, ensure_ascii=False, indent=2)
    )

    # 写盘 tvbox.json (100% 完整保留 categories、ext、style、header 等原装全量属性！)
    tvbox_data = {"sites": all_clean_sites}
    open(os.path.join(WORK_DIR, "tvbox.json"), "w", encoding="utf-8").write(
        json.dumps(tvbox_data, ensure_ascii=False, indent=2)
    )
    open(os.path.join(WORK_DIR, "tvbox_full.json"), "w", encoding="utf-8").write(
        json.dumps(tvbox_data, ensure_ascii=False, indent=2)
    )
    open(os.path.join(WORK_DIR, "tvbox_multi.json"), "w", encoding="utf-8").write(
        json.dumps(tvbox_data, ensure_ascii=False, indent=2)
    )

    # 写盘隔离 18+ 点播配置
    open(os.path.join(NOT_SUITABLE_DIR, "tvbox.json"), "w", encoding="utf-8").write(
        json.dumps({"sites": adult_sites}, ensure_ascii=False, indent=2)
    )

    # 写盘 live.txt
    live_content = "# IPTV 纯净直播源\nCCTV-1,http://111.13.138.83/m3u8/cctv1.m3u8\nCCTV-13,http://111.13.138.83/m3u8/cctv13.m3u8\n"
    open(os.path.join(WORK_DIR, "live.txt"), "w", encoding="utf-8").write(live_content)

    print(f"  └─ [01_merge_sources] 100% 完整保留原装 categories 属性，收录 {len(all_clean_sites)} 个纯净站点！", flush=True)
    return all_clean_sites

if __name__ == "__main__":
    merge_sources()
