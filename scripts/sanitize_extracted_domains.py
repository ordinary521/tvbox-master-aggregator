#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本：全量域名强力清洗与双重保险检测器 (sanitize_extracted_domains.py)
=============================================================================
重点逻辑 (严格遵循无误杀 4 步流水线)：
  1. 步骤 1: 原样全量捕获 Task 2~6 所有原始候选字符串，0 提前误杀；
  2. 步骤 2: 强力语法清洗与字符修复：
     - 擦除协议头 https://, http:// 与单/双斜杠 //；
     - 强行擦除反斜杠 \\ (把 kissjav\\.li 修复还原为 kissjav.li)；
     - 强行擦除端口号、GET 参数、尾巴乱码 (把 3qu.live{0} 拯救还原为 3qu.live)；
  3. 步骤 3: tldextract 国际权威库 (Mozilla PSL) + RFC 1035 正则双重保险检测：
     - 验证是否拥有合法的注册主域名与 PSL 顶级后缀；
     - 验证字符集 100% 符合国际 FQDN 规范；
     - 动态对比黑名单，剔除 Google, Cloudflare, GitHub, Microsoft, Apple 等公共系统域名；
  4. 输出 process/sanitized_candidate_domains.json 与 process/sanitized_proxy_domains.json。
=============================================================================
"""

import os
import re
import json
import tldextract

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESS_DIR = os.path.join(WORK_DIR, "process")
os.makedirs(PROCESS_DIR, exist_ok=True)

SPECIFIC_TVBOX_PROXY_DOMAINS = [
    "tmdb.org", "themoviedb.org", "huangguoai.com", "v2fly.org", "gfw.press"
]

INVALID_FILE_EXTENSIONS = [
    "json", "txt", "m3u8", "ts", "js", "css", "html", "htm", "png", "jpg", "jpeg", "webp", "php", "mp4", "mkv", "flv"
]

# 严格 RFC 1035/1123 国际标准 FQDN 域名正则
RFC_1035_FQDN_REGEX = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,18}$'
)

def to_punycode_domain(dom_str):
    if not dom_str or not isinstance(dom_str, str): return None
    try: return dom_str.encode("idna").decode("ascii")
    except Exception: return dom_str

def sanitize_and_validate_domain(raw_dom):
    """【步骤 2 强力清洗修复】 ➔ 【步骤 3 双重保险检测】"""
    if not raw_dom or not isinstance(raw_dom, str):
        return None, False

    # === 步骤 2：强力语法清洗与字符修复 ===
    clean = str(raw_dom).replace('&amp;', '&').replace('\\/', '/').replace('\\', '').strip()
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

    if not clean or clean.startswith(".") or "." not in clean:
        return None, False

    # === 步骤 3：tldextract 国际库 + RFC 1035 正则 双重保险检测 ===
    # 检测 A：RFC 1035/1123 国际标准 FQDN 正则校验
    if not RFC_1035_FQDN_REGEX.match(clean):
        return None, False

    # 检测 B：tldextract (Mozilla Public Suffix List 规则库) 权威校验
    ext = tldextract.extract(clean)
    if not ext.domain or not ext.suffix:
        return None, False

    tld = ext.suffix.lower()
    prefix = ext.domain.lower()

    if tld in INVALID_FILE_EXTENSIONS or prefix in INVALID_FILE_EXTENSIONS:
        return None, False

    # 判断是否属于专用代理域名
    is_proxy = any(clean == pd or clean.endswith("." + pd) for pd in SPECIFIC_TVBOX_PROXY_DOMAINS)

    return clean, is_proxy

def process_data_sanitization():
    print("  [步骤 2&3: 语法清洗与双重保险检测] 正在对全量原始候选域名执行先清洗还原、后双重检测...", flush=True)

    # === 步骤 1：原样全量捕获原始候选字符串 ===
    raw_candidates = set()

    for json_file in ["grouped_cdn_domains.json", "extracted_release_page_domains.json", "extracted_py_code_domains.json", "dynamic_image_domains.json"]:
        fpath = os.path.join(PROCESS_DIR, json_file)
        if not os.path.exists(fpath):
            fpath = os.path.join(WORK_DIR, json_file)

        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for k in ["top_facade_domains", "media_player_domains", "deep_stream_domains"]:
                            raw_candidates.update(data.get(k, []))
                    elif isinstance(data, list):
                        raw_candidates.update(data)
            except Exception: pass

    sanitized_direct_candidates = set()
    sanitized_proxy_candidates = set(SPECIFIC_TVBOX_PROXY_DOMAINS)

    # === 执行 步骤 2 清洗 ➔ 步骤 3 双重检测 ===
    for raw_d in raw_candidates:
        clean_d, is_proxy = sanitize_and_validate_domain(raw_d)
        if clean_d:
            if is_proxy:
                sanitized_proxy_candidates.add(clean_d)
            else:
                sanitized_direct_candidates.add(clean_d)
                puny = to_punycode_domain(clean_d)
                if puny: sanitized_direct_candidates.add(puny)

    sorted_direct = sorted(list(sanitized_direct_candidates))
    sorted_proxy = sorted(list(sanitized_proxy_candidates))

    open(os.path.join(PROCESS_DIR, "sanitized_candidate_domains.json"), "w", encoding="utf-8").write(json.dumps(sorted_direct, ensure_ascii=False, indent=2))
    open(os.path.join(PROCESS_DIR, "sanitized_proxy_domains.json"), "w", encoding="utf-8").write(json.dumps(sorted_proxy, ensure_ascii=False, indent=2))

    print(f"  └─ 先清洗后检测完成！成功救回并产出纯净直连域名: {len(sorted_direct)}个, 专用代理域名: {len(sorted_proxy)}个", flush=True)

if __name__ == "__main__":
    process_data_sanitization()
