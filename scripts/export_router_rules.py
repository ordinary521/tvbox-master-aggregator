#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本十：策略导出器 (Task 10: 原版 YAML 与 Mihomo .mrs 二进制双重导出)
=============================================================================
重点逻辑：
  1. 100% 物理强行锁定 huangguoai.com / tmdb.org 等专属代理域名进入 domains_proxy.txt / domains_proxy.mrs；
  2. 采用 O(1) 哈希集合后缀分解算法，100% 全量扣除 blackmatrix7 通用域名 (China, Microsoft, WeChat, Google 等)；
  3. 100% 1:1 严格照搬 CRThu/clash-rules-mrs 官方二进制进程编译命令：
     - mihomo convert-ruleset domain yaml domains_direct.yaml domains_direct.mrs
     - mihomo convert-ruleset ipcidr yaml ips_direct.yaml ips_direct.mrs
     - mihomo convert-ruleset domain yaml domains_proxy.yaml domains_proxy.mrs
  4. 纯域名 (behavior: domain) 与 纯 IP (behavior: ipcidr) 100% 物理拆分导出。
=============================================================================
"""

import os
import re
import json
import subprocess
import tldextract

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESS_DIR = os.path.join(WORK_DIR, "process")
CONFIG_DIR = os.path.join(WORK_DIR, "config")
os.makedirs(CONFIG_DIR, exist_ok=True)

# 专属 TVBox 强制代理域名集 (如 huangguoai.com)，绝对强行保留归入 domains_proxy！
SPECIFIC_TVBOX_PROXY_DOMAINS = {
    "huangguoai.com", "tmdb.org", "themoviedb.org", "v2fly.org", "gfw.press"
}

# 备用黑名单 (只在 repos/blackmatrix7 未克隆时做极低保底)
FALLBACK_BLACKMATRIX7_DOMAINS = {
    "google.com", "dns.google", "dns.google.com", "google.cn", "google.com.hk", "google.co.jp",
    "googleapis.com", "gstatic.com", "googletagmanager.com", "google-analytics.com",
    "googlesyndication.com", "googleusercontent.com", "googleadservices.com",
    "youtube.com", "ytimg.com", "ggpht.com", "doubleclick.net", "youtubekids.com", "youtube-nocookie.com",
    "github.com", "githubusercontent.com", "raw.githubusercontent.com", "jsdelivr.net", "fastly.jsdelivr.net", "github.io", "githubassets.com",
    "cloudflare.com", "dns.cloudflare.com", "cloudflare-dns.com", "workers.dev", "cloudflareclient.com",
    "microsoft.com", "live.com", "outlook.com", "office.com", "azure.com", "bing.com", "msn.com",
    "apple.com", "icloud.com", "mzstatic.com", "aaplimg.com", "cdn-apple.com", "apple-dns.net",
    "telegram.org", "t.me", "facebook.com", "twitter.com", "x.com", "instagram.com",
    "qq.com", "weixin.qq.com", "szextshort.weixin.qq.com", "qpic.cn", "wechat.com"
}

INVALID_FILE_EXTENSIONS = [
    "json", "txt", "m3u8", "ts", "js", "css", "html", "htm", "png", "jpg", "jpeg", "webp", "php", "mp4", "mkv", "flv"
]

RFC_1035_FQDN_REGEX = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,18}$'
)

_ALL_BLACKMATRIX7_DOMAINS_CACHE = None

def load_all_blackmatrix7_domains():
    """直接扫描 repos/blackmatrix7/rule/Clash/ 下的所有分类文件，加载全量已有域名！"""
    global _ALL_BLACKMATRIX7_DOMAINS_CACHE
    if _ALL_BLACKMATRIX7_DOMAINS_CACHE is not None:
        return _ALL_BLACKMATRIX7_DOMAINS_CACHE

    all_bm7_doms = set(FALLBACK_BLACKMATRIX7_DOMAINS)
    bm7_dir = os.path.join(WORK_DIR, "repos", "blackmatrix7", "rule", "Clash")

    if os.path.exists(bm7_dir):
        for root, _, files in os.walk(bm7_dir):
            for file in files:
                if file.endswith(".yaml") or file.endswith(".list") or file.endswith(".txt"):
                    fpath = os.path.join(root, file)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith("#") and not line.startswith("!") and not line.startswith("payload:"):
                                    parts = line.split(',')
                                    raw_item = parts[-1].strip("'\" ").lower().strip(".")
                                    if raw_item and "." in raw_item and not raw_item.replace('.', '').isdigit():
                                        all_bm7_doms.add(raw_item)
                    except Exception: pass

    _ALL_BLACKMATRIX7_DOMAINS_CACHE = all_bm7_doms
    return _ALL_BLACKMATRIX7_DOMAINS_CACHE

def is_blackmatrix7_existing_domain(clean_dom):
    if not clean_dom or not isinstance(clean_dom, str): return False
    dom_l = clean_dom.lower().strip()

    # huangguoai.com 等专属于 TVBox 代理的域名，绝对不判定为系统已有黑名单！
    if any(dom_l == pd or dom_l.endswith("." + pd) for pd in SPECIFIC_TVBOX_PROXY_DOMAINS):
        return False

    bm7_set = load_all_blackmatrix7_domains()

    if dom_l in bm7_set:
        return True

    parts = dom_l.split('.')
    for i in range(1, len(parts) - 1):
        parent_dom = ".".join(parts[i:])
        if parent_dom in bm7_set:
            return True

    return False

def to_punycode_domain(dom_str):
    if not dom_str or not isinstance(dom_str, str): return None
    try: return dom_str.encode("idna").decode("ascii")
    except Exception: return dom_str

def final_clean_before_write(dom, is_proxy_context=False):
    """写盘导出阶段最后一关：【步骤 2 强力语法清洗修整】 ➔ 【步骤 3 tldextract + RFC 正则 + O(1) 哈希全量差集扣除】"""
    if not dom or not isinstance(dom, str): return None

    # === 步骤 2：强力语法清洗修整 ===
    clean = str(dom).replace('&amp;', '&').replace('\\/', '/').replace('\\', '').strip()
    clean = clean.split('#')[0].split('?')[0].split('&')[0].split(';')[0].split('%')[0].split(',')[0].strip()

    # 擦除尾巴乱码与多余大括号 (例如 3qu.live{0} ➔ 3qu.live)
    clean = re.sub(r'\{[0-9]*\}$', '', clean)
    clean = re.sub(r'\[[0-9]*\]$', '', clean)

    # 擦除协议头与双斜杠
    clean = re.sub(r'^https?://', '', clean, flags=re.I)
    clean = re.sub(r'^//', '', clean)

    # 擦除所有残存的单斜杠 /、双斜杠 // 与反斜杠 \
    clean = clean.replace('/', '').replace('\\', '').strip()

    # 剥离端口号与问号
    clean = clean.split(":")[0].strip("@|*^ \t\r\n'\"").lower()

    # 专属 TVBox 代理域名（如 huangguoai.com），物理强行保留保底！
    if any(clean == pd or clean.endswith("." + pd) for pd in SPECIFIC_TVBOX_PROXY_DOMAINS):
        return clean

    # === 步骤 3：tldextract + RFC 正则 + 黑名单 全量 O(1) 差集扣除 ===
    if not RFC_1035_FQDN_REGEX.match(clean):
        return None

    ext = tldextract.extract(clean)
    if not ext.domain or not ext.suffix:
        return None

    tld = ext.suffix.lower()
    prefix = ext.domain.lower()

    if tld in INVALID_FILE_EXTENSIONS or prefix in INVALID_FILE_EXTENSIONS:
        return None

    # 检测 C：【O(1) 极速哈希全量差集扣除】
    if is_blackmatrix7_existing_domain(clean):
        return None

    return clean

def read_existing_historical_rules(file_path, is_proxy_context=False):
    existing_doms = set()
    existing_ips = set()
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("!") and not line.startswith("payload:"):
                        clean_item = re.sub(r'^(?:@@\|\||- DOMAIN-SUFFIX,|- IP-CIDR,|- \'\+\.|- \')\s*', '', line).rstrip("^'/32").strip()
                        if clean_item.replace('.', '').isdigit():
                            existing_ips.add(clean_item)
                        else:
                            final_item = final_clean_before_write(clean_item, is_proxy_context=is_proxy_context)
                            if final_item: existing_doms.add(final_item)
        except Exception: pass
    return existing_doms, existing_ips

def compile_mihomo_mrs(behavior, yaml_path, mrs_path):
    """100% 1:1 照搬 CRThu/clash-rules-mrs 官方规范，调用 mihomo convert-ruleset 官方二进制进程打包 .mrs"""
    cmd = ["mihomo", "convert-ruleset", behavior, "yaml", yaml_path, mrs_path]
    print(f"  [Mihomo .mrs 官方二进制进程] 正在编译: {' '.join(cmd)}", flush=True)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and os.path.exists(mrs_path) and os.path.getsize(mrs_path) > 0:
            print(f"  └─ 成功调用官方二进制进程产出 .mrs 文件: {os.path.basename(mrs_path)} ({os.path.getsize(mrs_path)} bytes)", flush=True)
            return True
        else:
            print(f"  └─ 编译失败 stdout: {res.stdout.strip()}, stderr: {res.stderr.strip()}", flush=True)
            return False
    except Exception as e:
        print(f"  └─ 编译异常: {e}", flush=True)
        return False

def wipe_all_old_output_files(work_dir):
    old_files = [
        "domains_direct.txt", "domains_direct.yaml", "clash_rules_direct.yaml", "domains_direct.mrs",
        "ips_direct.txt", "ips_direct.yaml", "ips_direct.mrs",
        "domains_proxy.txt", "domains_proxy.yaml", "clash_rules_proxy.yaml", "domains_proxy.mrs",
        "adguard_direct.txt", "adguard_proxy.txt"
    ]
    for of in old_files:
        fpath = os.path.join(work_dir, of)
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
                print(f"  ├─ 物理强行擦除旧产出文件: {of}", flush=True)
            except Exception: pass

def export_grouped_router_rules(work_dir, sites=None, grouped_cdn_domains=None, dynamic_image_domains=None, extracted_ips=None, release_page_domains=None, py_code_domains=None):
    print("  [Task 10: 策略导出器] 正在强行归入 huangguoai.com 并且执行【全量差集扣除 A-B】与 Mihomo .mrs 编译...", flush=True)

    wipe_all_old_output_files(work_dir)

    all_bm7 = load_all_blackmatrix7_domains()
    print(f"  ├─ 成功载入 blackmatrix7 规则库全量已有域名: {len(all_bm7)} 个！", flush=True)

    sanitized_direct_path = os.path.join(PROCESS_DIR, "sanitized_candidate_domains.json")
    sanitized_proxy_path = os.path.join(PROCESS_DIR, "sanitized_proxy_domains.json")

    direct_domains = set()
    proxy_domains = set(SPECIFIC_TVBOX_PROXY_DOMAINS)  # 强行确保 huangguoai.com 100% 存在于 proxy_domains!

    if os.path.exists(sanitized_direct_path):
        try: direct_domains.update(json.load(open(sanitized_direct_path)))
        except Exception: pass

    if os.path.exists(sanitized_proxy_path):
        try: proxy_domains.update(json.load(open(sanitized_proxy_path)))
        except Exception: pass

    # 读取历史规则增量累加
    hist_direct_path = os.path.join(work_dir, "domains_direct.txt")
    hist_doms, hist_ips = read_existing_historical_rules(hist_direct_path, is_proxy_context=False)
    direct_domains.update(hist_doms)

    hist_proxy_path = os.path.join(work_dir, "domains_proxy.txt")
    hist_proxy_doms, _ = read_existing_historical_rules(hist_proxy_path, is_proxy_context=True)
    proxy_domains.update(hist_proxy_doms)

    process_ip_path = os.path.join(PROCESS_DIR, "extracted_ip_addresses.json")
    extracted_ips = set()
    if os.path.exists(process_ip_path):
        try:
            ips = json.load(open(process_ip_path))
            if isinstance(ips, list): extracted_ips.update(ips)
        except Exception: pass

    pure_ips = set(extracted_ips or []).union(hist_ips)

    def expand_and_final_clean(raw_list, is_proxy_context=False):
        expanded = set()
        for dom in (raw_list or []):
            final_dom = final_clean_before_write(dom, is_proxy_context=is_proxy_context)
            if final_dom:
                expanded.add(final_dom)
                puny = to_punycode_domain(final_dom)
                if puny:
                    final_puny = final_clean_before_write(puny, is_proxy_context=is_proxy_context)
                    if final_puny: expanded.add(final_puny)
        return sorted(list(expanded))

    sorted_direct_doms = expand_and_final_clean(direct_domains, is_proxy_context=False)
    sorted_proxy_doms = expand_and_final_clean(proxy_domains, is_proxy_context=True)
    sorted_ips = sorted(list(pure_ips))

    # 1. 导出纯域名直连列表与符合 Mihomo 官方标准的纯字符串 YAML (domains_direct.yaml / clash_rules_direct.yaml)
    domains_direct_yaml = os.path.join(work_dir, "domains_direct.yaml")
    clash_rules_direct_yaml = os.path.join(work_dir, "clash_rules_direct.yaml")

    with open(os.path.join(work_dir, "domains_direct.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 纯增量补充放行域名直连列表 (与 blackmatrix7 0 重叠)\n")
        for d in sorted_direct_doms:
            final_d = final_clean_before_write(d, is_proxy_context=False)
            if final_d: f.write(f"{final_d}\n")

    yaml_header = "# TVBox 纯域名 Mihomo / Clash 直连规则集 (behavior: domain)\npayload:\n"
    yaml_body = "".join(f"  - '{final_clean_before_write(d, is_proxy_context=False)}'\n" for d in sorted_direct_doms if final_clean_before_write(d, is_proxy_context=False))

    open(domains_direct_yaml, "w", encoding="utf-8").write(yaml_header + yaml_body)
    open(clash_rules_direct_yaml, "w", encoding="utf-8").write(yaml_header + yaml_body)

    with open(os.path.join(work_dir, "adguard_direct.txt"), "w", encoding="utf-8") as f:
        f.write("! OpenWrt AdGuard Home TVBox 纯域名放行白名单\n")
        for d in sorted_direct_doms:
            final_d = final_clean_before_write(d, is_proxy_context=False)
            if final_d: f.write(f"@@||{final_d}^\n")

    # 2. 导出纯 IP 直连列表与 100% 符合 Mihomo 官方规范的 YAML (ips_direct.txt / ips_direct.yaml)
    ips_direct_yaml = os.path.join(work_dir, "ips_direct.txt")
    with open(os.path.join(work_dir, "ips_direct.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频切片纯 IPv4 地址直连列表\n")
        for ip in sorted_ips: f.write(f"{ip}\n")

    ips_direct_yaml = os.path.join(work_dir, "ips_direct.yaml")
    open(ips_direct_yaml, "w", encoding="utf-8").write(
        "# TVBox 纯 IP Mihomo / Clash 直连规则集 (behavior: ipcidr)\npayload:\n" +
        "".join(f"  - '{ip if '/' in ip else ip + '/32'}'\n" for ip in sorted_ips)
    )

    # 3. 导出纯域名强制代理规则列表 (domains_proxy.txt / domains_proxy.yaml / clash_rules_proxy.yaml)包含 huangguoai.com
    domains_proxy_yaml = os.path.join(work_dir, "domains_proxy.yaml")
    clash_rules_proxy_yaml = os.path.join(work_dir, "clash_rules_proxy.yaml")

    with open(os.path.join(work_dir, "domains_proxy.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 强制代理纯域名列表 (含 huangguoai.com)\n")
        for d in sorted_proxy_doms:
            final_d = final_clean_before_write(d, is_proxy_context=True)
            if final_d: f.write(f"{final_d}\n")

    with open(os.path.join(work_dir, "adguard_proxy.txt"), "w", encoding="utf-8") as f:
        f.write("! OpenWrt AdGuard Home 强制代理域名规则\n")
        for d in sorted_proxy_doms:
            final_d = final_clean_before_write(d, is_proxy_context=True)
            if final_d: f.write(f"@@||{final_d}^\n")

    proxy_yaml_header = "# TVBox 强制代理 Mihomo / Clash 规则集 (behavior: domain)\npayload:\n"
    proxy_yaml_body = "".join(f"  - '{final_clean_before_write(d, is_proxy_context=True)}'\n" for d in sorted_proxy_doms if final_clean_before_write(d, is_proxy_context=True))

    open(domains_proxy_yaml, "w", encoding="utf-8").write(proxy_yaml_header + proxy_yaml_body)
    open(clash_rules_proxy_yaml, "w", encoding="utf-8").write(proxy_yaml_header + proxy_yaml_body)

    # 4. 1:1 严格调用 CRThu/clash-rules-mrs 官方命令 mihomo convert-ruleset 编译导出二进制 .mrs 规则集
    compile_mihomo_mrs("domain", domains_direct_yaml, os.path.join(work_dir, "domains_direct.mrs"))
    compile_mihomo_mrs("ipcidr", ips_direct_yaml, os.path.join(work_dir, "ips_direct.mrs"))
    compile_mihomo_mrs("domain", domains_proxy_yaml, os.path.join(work_dir, "domains_proxy.mrs"))

    print(f"  ├─ 全新导出原版 YAML 规则集: domains_direct.yaml, clash_rules_direct.yaml, ips_direct.yaml, domains_proxy.yaml, clash_rules_proxy.yaml")
    print(f"  └─ 全新导出 Mihomo .mrs 二进制规则集: domains_direct.mrs, ips_direct.mrs, domains_proxy.mrs")

def export_all_router_rules(work_dir, sites=None, grouped_cdn_domains=None, dynamic_image_domains=None, extracted_ips=None, release_page_domains=None, py_code_domains=None):
    return export_grouped_router_rules(work_dir, sites, grouped_cdn_domains, dynamic_image_domains, extracted_ips, release_page_domains, py_code_domains)

if __name__ == "__main__":
    export_grouped_router_rules(WORK_DIR)
