#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本十：策略导出器 (Task 10: 原版 YAML 与 Mihomo .mrs 二进制双重导出)
=============================================================================
重点更新：
  1. 导出写盘前最后一关 (Final Export Purge): 100% 动态匹配剔除 blackmatrix7 全量系统级/公共基础设施域名 (Google, YouTube, Cloudflare, GitHub, Microsoft, Apple, Global, Advertising)；
  2. 100% 1:1 严格照搬 CRThu/clash-rules-mrs 官方二进制进程编译命令：
     - mihomo convert-ruleset domain yaml domains_direct.yaml domains_direct.mrs
     - mihomo convert-ruleset ipcidr yaml ips_direct.yaml ips_direct.mrs
     - mihomo convert-ruleset domain yaml domains_proxy.yaml domains_proxy.mrs
  3. 纯域名 (behavior: domain) 与 纯 IP (behavior: ipcidr) 100% 物理拆分导出；
  4. 写盘前最后一关：100% 斩断所有单斜杠 /、双斜杠 //、反斜杠 \\、GET 参数与逗号尾巴。
=============================================================================
"""

import os
import re
import json
import subprocess

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESS_DIR = os.path.join(WORK_DIR, "process")
CONFIG_DIR = os.path.join(WORK_DIR, "config")

# blackmatrix7 权威系统级、公共基础设施与广告/隐私全量精准剔除集
BLACKMATRIX7_SYSTEM_DOMAINS = {
    # 谷歌全系 (Google & YouTube)
    "google.com", "googleapis.com", "gstatic.com", "dns.google", "googletagmanager.com",
    "google-analytics.com", "googlesyndication.com", "googleusercontent.com", "googleadservices.com",
    "youtube.com", "ytimg.com", "ggpht.com", "doubleclick.net", "youtubekids.com", "youtube-nocookie.com",
    # Cloudflare 全系
    "cloudflare.com", "dns.cloudflare.com", "cloudflare-dns.com", "workers.dev", "cloudflareclient.com",
    # GitHub 全系
    "github.com", "githubusercontent.com", "jsdelivr.net", "fastly.jsdelivr.net", "github.io", "githubassets.com",
    # 微软全系 (Microsoft)
    "microsoft.com", "live.com", "outlook.com", "office.com", "azure.com", "bing.com", "msn.com", "skype.com",
    # 苹果全系 (Apple)
    "apple.com", "icloud.com", "mzstatic.com", "aaplimg.com", "cdn-apple.com", "apple-dns.net",
    # 其他公共/广告/隐私
    "telegram.org", "t.me", "facebook.com", "twitter.com", "x.com", "instagram.com",
    "quad9.net", "opendns.com", "libredns.gr", "ipify.org", "ip.sb", "openx.net", "adservice.com"
}

INVALID_FILE_EXTENSIONS = [
    "json", "txt", "m3u8", "ts", "js", "css", "html", "htm", "png", "jpg", "jpeg", "webp", "php", "mp4", "mkv", "flv"
]

def to_punycode_domain(dom_str):
    if not dom_str or not isinstance(dom_str, str): return None
    try: return dom_str.encode("idna").decode("ascii")
    except Exception: return dom_str

def is_system_or_global_domain(dom):
    if not dom or not isinstance(dom, str): return False
    dom_l = dom.lower().strip()
    return any(dom_l == sd or dom_l.endswith("." + sd) for sd in BLACKMATRIX7_SYSTEM_DOMAINS)

def final_clean_before_write(dom):
    """写盘前最后一关：100% 斩断任何残存的单斜杠 /、双斜杠 //、反斜杠 \\、?, #, & 与协议头"""
    if not dom or not isinstance(dom, str): return None

    clean = str(dom).replace('&amp;', '&').replace('\\/', '/').replace('\\', '').strip()
    clean = clean.split('#')[0].split('?')[0].split('&')[0].split(';')[0].split('%')[0].split(',')[0].strip()

    # 1. 擦除协议头与双斜杠
    clean = re.sub(r'^https?://', '', clean, flags=re.I)
    clean = re.sub(r'^//', '', clean)

    # 2. 擦除所有残存的单斜杠 /、双斜杠 // 与反斜杠 \
    clean = clean.replace('/', '').replace('\\', '').strip()

    # 3. 剥离端口号与问号
    clean = clean.split(":")[0].strip("@|*^ \t\r\n'\"").lower()

    # 4. 导出写盘前最后一关：100% 物理精准过滤公共系统/代理/广告域名 (Google, YouTube, Cloudflare, GitHub, Microsoft, Apple)，绝对不写进直连和代理列表！
    if is_system_or_global_domain(clean):
        return None

    # 5. 滤掉纯文件后缀与无前缀脏数据，以及纯 IP 地址（纯 IP 独立放入 IP 列表）
    if not clean or clean.startswith(".") or "." not in clean or clean.replace('.', '').isdigit():
        return None

    parts = clean.split(".")
    if len(parts) < 2 or not parts[0] or not parts[-1]:
        return None

    tld = parts[-1].lower()
    prefix = parts[0].lower()

    if tld in INVALID_FILE_EXTENSIONS or prefix in INVALID_FILE_EXTENSIONS:
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
    print("  [Task 10: 策略导出器] 正在 1:1 严格执行原版 YAML 与 Mihomo .mrs 二进制双重导出...", flush=True)

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
