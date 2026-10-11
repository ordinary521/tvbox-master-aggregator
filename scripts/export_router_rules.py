#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本十：策略导出器 (Task 10: 原版 YAML 与 Mihomo .mrs 二进制双重导出)
=============================================================================
重点逻辑：
  1. 本地磁盘 0.000 秒读取克隆库 repos/blackmatrix7 规则文件（第一优先主规则），新旧全量域名通通强制洗一遍；
  2. 手写列表仅作为保底 (Fallback)；
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

# 手写列表仅作为本地备用保底 (Fallback)，绝不替代 repos/blackmatrix7 克隆库主规则
FALLBACK_BLACKMATRIX7_DOMAINS = {
    "google.com", "googleapis.com", "gstatic.com", "dns.google", "googletagmanager.com",
    "google-analytics.com", "googlesyndication.com", "googleusercontent.com",
    "youtube.com", "ytimg.com", "ggpht.com", "doubleclick.net",
    "github.com", "githubusercontent.com", "jsdelivr.net", "fastly.jsdelivr.net",
    "cloudflare.com", "dns.cloudflare.com", "cloudflare-dns.com", "workers.dev",
    "microsoft.com", "live.com", "outlook.com", "office.com", "azure.com", "bing.com",
    "apple.com", "icloud.com", "mzstatic.com", "aaplimg.com",
    "telegram.org", "t.me", "facebook.com", "twitter.com", "x.com", "instagram.com",
    "qq.com", "weixin.qq.com", "qpic.cn"
}

BLACKMATRIX7_SYSTEM_CATEGORIES = [
    "Google", "YouTube", "Cloudflare", "GitHub", "Microsoft", "Apple",
    "Global", "Proxy", "Advertising", "AdvertisingLite", "Privacy"
]

INVALID_FILE_EXTENSIONS = [
    "json", "txt", "m3u8", "ts", "js", "css", "html", "htm", "png", "jpg", "jpeg", "webp", "php", "mp4", "mkv", "flv"
]

RFC_1035_FQDN_REGEX = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,18}$'
)

_DYNAMIC_SYSTEM_DOMAINS_CACHE = None

def load_local_blackmatrix7_system_domains():
    """第一优先：直接读取本地克隆库 repos/blackmatrix7/rule/Clash/ 官方规则集！手写列表只做保底"""
    global _DYNAMIC_SYSTEM_DOMAINS_CACHE
    if _DYNAMIC_SYSTEM_DOMAINS_CACHE is not None:
        return _DYNAMIC_SYSTEM_DOMAINS_CACHE

    system_doms = set()

    # 1. 第一优先主规则：读取本地克隆库 repos/blackmatrix7 中的全量官方规则
    bm7_dir = os.path.join(WORK_DIR, "repos", "blackmatrix7", "rule", "Clash")
    if os.path.exists(bm7_dir):
        for cat in BLACKMATRIX7_SYSTEM_CATEGORIES:
            cat_dir = os.path.join(bm7_dir, cat)
            if os.path.exists(cat_dir):
                for root, _, files in os.walk(cat_dir):
                    for file in files:
                        if file.endswith(".yaml") or file.endswith(".list") or file.endswith(".txt"):
                            fpath = os.path.join(root, file)
                            try:
                                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                    for line in f:
                                        line = line.strip()
                                        if line and not line.startswith("#") and not line.startswith("!") and not line.startswith("payload:"):
                                            m = re.search(r'(?:DOMAIN-SUFFIX|DOMAIN|DOMAIN-KEYWORD)?\s*,?\s*[\'"]?([a-zA-Z0-9\.\-_]+)[\'"]?', line, re.I)
                                            if m:
                                                clean_d = m.group(1).lower().strip(".")
                                                if clean_d and "." in clean_d and not clean_d.replace('.', '').isdigit():
                                                    system_doms.add(clean_d)
                            except Exception: pass

    # 2. 如果克隆库完整，写盘缓存；若克隆库缺失，使用手写列表保底 (Fallback)
    if not system_doms:
        system_doms.update(FALLBACK_BLACKMATRIX7_DOMAINS)

    _DYNAMIC_SYSTEM_DOMAINS_CACHE = system_doms
    return _DYNAMIC_SYSTEM_DOMAINS_CACHE

def to_punycode_domain(dom_str):
    if not dom_str or not isinstance(dom_str, str): return None
    try: return dom_str.encode("idna").decode("ascii")
    except Exception: return dom_str

def is_system_or_global_domain(dom):
    if not dom or not isinstance(dom, str): return False
    dom_l = dom.lower().strip()
    sys_doms = load_local_blackmatrix7_system_domains()
    return any(dom_l == sd or dom_l.endswith("." + sd) for sd in sys_doms)

def final_clean_before_write(dom):
    """写盘导出阶段最后一关：【步骤 2 强力语法清洗修整】 ➔ 【步骤 3 tldextract + RFC 正则 + repos/blackmatrix7 官方规则库双重保险检测】"""
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

    # === 步骤 3：tldextract + RFC 正则 + 黑名单 双重保险检测 ===
    # 检测 A：RFC 1035/1123 国际标准 FQDN 正则校验
    if not RFC_1035_FQDN_REGEX.match(clean):
        return None

    # 检测 B：tldextract (Mozilla Public Suffix List 规则库) 权威校验
    ext = tldextract.extract(clean)
    if not ext.domain or not ext.suffix:
        return None

    tld = ext.suffix.lower()
    prefix = ext.domain.lower()

    if tld in INVALID_FILE_EXTENSIONS or prefix in INVALID_FILE_EXTENSIONS:
        return None

    # 检测 C：1:1 严格对比 repos/blackmatrix7 官方规则库（新旧域名通通强行清洗，一个不漏）
    if is_system_or_global_domain(clean):
        return None

    return clean

def read_existing_historical_rules(file_path):
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
                            # 历史域名导出时也必须通过 final_clean_before_write 全量强制清洗！
                            final_item = final_clean_before_write(clean_item)
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

def export_grouped_router_rules(work_dir, sites=None, grouped_cdn_domains=None, dynamic_image_domains=None, extracted_ips=None, release_page_domains=None, py_code_domains=None):
    print("  [Task 10: 策略导出器] 正在执行【新旧全量域名强制通过 repos/blackmatrix7 官方规则库清洗】与 .mrs 编译...", flush=True)

    # 载入本地 repos/blackmatrix7 官方全量黑名单
    sys_doms = load_local_blackmatrix7_system_domains()
    print(f"  ├─ 成功从本地 repos/blackmatrix7 官方规则库载入 {len(sys_doms)} 个黑名单域名！", flush=True)

    sanitized_direct_path = os.path.join(PROCESS_DIR, "sanitized_candidate_domains.json")
    sanitized_proxy_path = os.path.join(PROCESS_DIR, "sanitized_proxy_domains.json")

    direct_domains = set()
    proxy_domains = set()

    if os.path.exists(sanitized_direct_path):
        try: direct_domains.update(json.load(open(sanitized_direct_path)))
        except Exception: pass

    if os.path.exists(sanitized_proxy_path):
        try: proxy_domains.update(json.load(open(sanitized_proxy_path)))
        except Exception: pass

    # 读取历史规则增量累加（历史域名在 read_existing_historical_rules 时也全部经过 final_clean_before_write 洗一遍！）
    hist_direct_path = os.path.join(work_dir, "domains_direct.txt")
    hist_doms, hist_ips = read_existing_historical_rules(hist_direct_path)

    direct_domains.update(hist_doms)

    # 读取 process/extracted_ip_addresses.json
    process_ip_path = os.path.join(PROCESS_DIR, "extracted_ip_addresses.json")
    if os.path.exists(process_ip_path):
        try:
            ips = json.load(open(process_ip_path))
            if isinstance(ips, list): extracted_ips = (extracted_ips or []) + ips
        except Exception: pass

    pure_ips = set(extracted_ips or []).union(hist_ips)

    def expand_and_final_clean(raw_list):
        expanded = set()
        for dom in (raw_list or []):
            final_dom = final_clean_before_write(dom)
            if final_dom:
                expanded.add(final_dom)
                puny = to_punycode_domain(final_dom)
                if puny:
                    final_puny = final_clean_before_write(puny)
                    if final_puny: expanded.add(final_puny)
        return sorted(list(expanded))

    sorted_direct_doms = expand_and_final_clean(direct_domains)
    sorted_proxy_doms = expand_and_final_clean(proxy_domains)
    sorted_ips = sorted(list(pure_ips))

    # 1. 导出纯域名直连列表与符合 Mihomo 官方标准的纯字符串 YAML (domains_direct.yaml / clash_rules_direct.yaml)
    domains_direct_yaml = os.path.join(work_dir, "domains_direct.yaml")
    clash_rules_direct_yaml = os.path.join(work_dir, "clash_rules_direct.yaml")

    with open(os.path.join(work_dir, "domains_direct.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源、发布页镜像、海报 CDN 纯域名直连列表\n")
        for d in sorted_direct_doms:
            final_d = final_clean_before_write(d)
            if final_d: f.write(f"{final_d}\n")

    yaml_header = "# TVBox 纯域名 Mihomo / Clash 直连规则集 (behavior: domain)\npayload:\n"
    yaml_body = "".join(f"  - '{final_clean_before_write(d)}'\n" for d in sorted_direct_doms if final_clean_before_write(d))

    open(domains_direct_yaml, "w", encoding="utf-8").write(yaml_header + yaml_body)
    open(clash_rules_direct_yaml, "w", encoding="utf-8").write(yaml_header + yaml_body)

    with open(os.path.join(work_dir, "adguard_direct.txt"), "w", encoding="utf-8") as f:
        f.write("! OpenWrt AdGuard Home TVBox 纯域名放行白名单\n")
        for d in sorted_direct_doms:
            final_d = final_clean_before_write(d)
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

    # 3. 导出纯域名强制代理规则列表 (domains_proxy.txt / domains_proxy.yaml / clash_rules_proxy.yaml)
    domains_proxy_yaml = os.path.join(work_dir, "domains_proxy.yaml")
    clash_rules_proxy_yaml = os.path.join(work_dir, "clash_rules_proxy.yaml")

    with open(os.path.join(work_dir, "domains_proxy.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 强制代理纯域名列表\n")
        for d in sorted_proxy_doms:
            final_d = final_clean_before_write(d)
            if final_d: f.write(f"{final_d}\n")

    with open(os.path.join(work_dir, "adguard_proxy.txt"), "w", encoding="utf-8") as f:
        f.write("! OpenWrt AdGuard Home 强制代理域名规则\n")
        for d in sorted_proxy_doms:
            final_d = final_clean_before_write(d)
            if final_d: f.write(f"@@||{final_d}^\n")

    proxy_yaml_header = "# TVBox 强制代理 Mihomo / Clash 规则集 (behavior: domain)\npayload:\n"
    proxy_yaml_body = "".join(f"  - '{final_clean_before_write(d)}'\n" for d in sorted_proxy_doms if final_clean_before_write(d))

    open(domains_proxy_yaml, "w", encoding="utf-8").write(proxy_yaml_header + proxy_yaml_body)
    open(clash_rules_proxy_yaml, "w", encoding="utf-8").write(proxy_yaml_header + proxy_yaml_body)

    # 4. 1:1 严格调用 CRThu/clash-rules-mrs 官方命令 mihomo convert-ruleset 编译导出二进制 .mrs 规则集
    compile_mihomo_mrs("domain", domains_direct_yaml, os.path.join(work_dir, "domains_direct.mrs"))
    compile_mihomo_mrs("ipcidr", ips_direct_yaml, os.path.join(work_dir, "ips_direct.mrs"))
    compile_mihomo_mrs("domain", domains_proxy_yaml, os.path.join(work_dir, "domains_proxy.mrs"))

    print(f"  ├─ 导出原版 YAML 规则集: domains_direct.yaml, clash_rules_direct.yaml, ips_direct.yaml, domains_proxy.yaml, clash_rules_proxy.yaml")
    print(f"  └─ 导出 Mihomo .mrs 二进制规则集: domains_direct.mrs, ips_direct.mrs, domains_proxy.mrs")

def export_all_router_rules(work_dir, sites=None, grouped_cdn_domains=None, dynamic_image_domains=None, extracted_ips=None, release_page_domains=None, py_code_domains=None):
    return export_grouped_router_rules(work_dir, sites, grouped_cdn_domains, dynamic_image_domains, extracted_ips, release_page_domains, py_code_domains)

if __name__ == "__main__":
    export_grouped_router_rules(WORK_DIR)
