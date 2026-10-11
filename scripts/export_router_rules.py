#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本十：策略导出器 (Task 10: 原版 YAML 与 Mihomo .mrs 二进制双重导出)
=============================================================================
重点逻辑 (遵循先清洗修整、后双重检测流水线)：
  1. 步骤 2 强力语法清洗修整 (擦除协议头/反斜杠/端口号/尾巴乱码 {0})；
  2. 步骤 3 tldextract (Mozilla PSL) + RFC 1035 正则双重保险检测，并动态对比黑名单强行剔除；
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
import urllib.request
import subprocess
import tldextract

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESS_DIR = os.path.join(WORK_DIR, "process")
CONFIG_DIR = os.path.join(WORK_DIR, "config")
os.makedirs(CONFIG_DIR, exist_ok=True)

BLACKMATRIX7_RAW_URLS = [
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Google/Google_Classical.yaml",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/YouTube/YouTube_Classical.yaml",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Cloudflare/Cloudflare_Classical.yaml",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/GitHub/GitHub_Classical.yaml",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Microsoft/Microsoft_Classical.yaml",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Apple/Apple_Classical.yaml",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Global/Global_Classical.yaml",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Advertising/Advertising_Classical.yaml"
]

INVALID_FILE_EXTENSIONS = [
    "json", "txt", "m3u8", "ts", "js", "css", "html", "htm", "png", "jpg", "jpeg", "webp", "php", "mp4", "mkv", "flv"
]

RFC_1035_FQDN_REGEX = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,18}$'
)

_DYNAMIC_SYSTEM_DOMAINS_CACHE = None

def load_dynamic_blackmatrix7_system_domains():
    """动态读取 blackmatrix7 官方 Raw 链接/本地缓存，解析全量黑名单，禁止任何硬编码"""
    global _DYNAMIC_SYSTEM_DOMAINS_CACHE
    if _DYNAMIC_SYSTEM_DOMAINS_CACHE is not None:
        return _DYNAMIC_SYSTEM_DOMAINS_CACHE

    system_doms = set()
    cache_file = os.path.join(CONFIG_DIR, "dynamic_blackmatrix7_system_domains.json")

    for raw_url in BLACKMATRIX7_RAW_URLS:
        try:
            req = urllib.request.Request(raw_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
                for line in text.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("payload:"):
                        m = re.search(r'(?:DOMAIN-SUFFIX|DOMAIN|DOMAIN-KEYWORD)?\s*,?\s*[\'"]?([a-zA-Z0-9\.\-_]+)[\'"]?', line, re.I)
                        if m:
                            clean_d = m.group(1).lower().strip(".")
                            if clean_d and "." in clean_d and not clean_d.replace('.', '').isdigit():
                                system_doms.add(clean_d)
        except Exception: pass

    if system_doms:
        try:
            open(cache_file, "w", encoding="utf-8").write(json.dumps(sorted(list(system_doms)), ensure_ascii=False, indent=2))
        except Exception: pass
    elif os.path.exists(cache_file):
        try:
            system_doms.update(json.load(open(cache_file, "r", encoding="utf-8")))
        except Exception: pass

    _DYNAMIC_SYSTEM_DOMAINS_CACHE = system_doms
    return _DYNAMIC_SYSTEM_DOMAINS_CACHE

def to_punycode_domain(dom_str):
    if not dom_str or not isinstance(dom_str, str): return None
    try: return dom_str.encode("idna").decode("ascii")
    except Exception: return dom_str

def is_system_or_global_domain(dom):
    if not dom or not isinstance(dom, str): return False
    dom_l = dom.lower().strip()
    sys_doms = load_dynamic_blackmatrix7_system_domains()
    return any(dom_l == sd or dom_l.endswith("." + sd) for sd in sys_doms)

def final_clean_before_write(dom):
    """写盘前最后一关：【步骤 2 强力语法清洗修整】 ➔ 【步骤 3 tldextract + RFC 正则 + 黑名单 双重保险检测】"""
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

    # 检测 C：动态比对 blackmatrix7 官方 Raw 规则文件，精准剔除系统/公共/广告域名
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
    print("  [Task 10: 策略导出器] 正在执行【先清洗修复 ➔ 后双重保险检测】的强力写盘与 .mrs 编译...", flush=True)

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

    # 读取历史规则增量累加，严格分离域名与纯 IP
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
    ips_direct_yaml = os.path.join(work_dir, "ips_direct.yaml")
    with open(os.path.join(work_dir, "ips_direct.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频切片纯 IPv4 地址直连列表\n")
        for ip in sorted_ips: f.write(f"{ip}\n")

    with open(ips_direct_yaml, "w", encoding="utf-8") as f:
        f.write("# TVBox 纯 IP Mihomo / Clash 直连规则集 (behavior: ipcidr)\npayload:\n")
        for ip in sorted_ips:
            if "/" in ip: f.write(f"  - '{ip}'\n")
            else: f.write(f"  - '{ip}/32'\n")

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

def export_all_router_rules(work_dir, sites=None, deep_cdn_domains=None, dynamic_image_domains=None, extracted_ips=None, release_page_domains=None, py_code_domains=None):
    return export_grouped_router_rules(work_dir, sites, deep_cdn_domains, dynamic_image_domains, extracted_ips, release_page_domains, py_code_domains)

if __name__ == "__main__":
    export_grouped_router_rules(WORK_DIR)
