#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 本地专用：一键真实宽带网络 DNS/CDN 连通性探测器 (local_probe_runner.py)
=============================================================================
注意：
  1. 本脚本 100% 仅供本地环境 (中国国内真实宽带) 手动一键运行；
  2. 云端 GitHub Actions 流水线 100% 绝对不会运行本脚本；
  3. 功能：在本地真实国内网络下，对全量候选域名执行真实 DNS 解析与 CDN 连通性探针，
     精准识别在国内真实被墙/被阻断的切片域名，直接写入 process/ 固化存盘并重新编译 .mrs。
=============================================================================
"""

import os
import re
import json
import socket
import ssl
import urllib.request
import subprocess

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESS_DIR = os.path.join(WORK_DIR, "process")
os.makedirs(PROCESS_DIR, exist_ok=True)

# 导入 Task 10 导出器
sys_path = os.path.join(WORK_DIR, "scripts")
if sys_path not in sys.path:
    sys.path.append(sys_path)

try:
    from export_router_rules import export_grouped_router_rules, final_clean_before_write
except Exception:
    def final_clean_before_write(d, is_proxy_context=False): return d

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

def probe_domain_connectivity(domain, timeout=2.5):
    """在本地中国宽带环境下，实测域名的 DNS 解析与 TCP/HTTP 连通性"""
    if not domain or not isinstance(domain, str):
        return False, None

    clean_d = domain.lower().strip()

    # 1. 本地 DNS 解析实测
    try:
        ip = socket.gethostbyname(clean_d)
    except Exception:
        return False, "dns_failed"

    # 2. 本地 HTTP/HTTPS 连通性探针
    for proto in ["https://", "http://"]:
        try:
            url = f"{proto}{clean_d}"
            req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
                if resp.status in [200, 206, 301, 302, 403, 404]:
                    return True, ip
        except Exception:
            pass

    return False, ip

def run_local_probe():
    print("=================================================================", flush=True)
    print(" 🚀 本地专用：中国国内真实宽带 DNS/CDN 连通性一键探测器", flush=True)
    print("=================================================================", flush=True)

    # 搜集所有候选域名
    candidate_domains = set()

    for jf in ["sanitized_candidate_domains.json", "grouped_cdn_domains.json", "downloads_supplement_direct.json"]:
        fpath = os.path.join(PROCESS_DIR, jf)
        if os.path.exists(fpath):
            try:
                data = json.load(open(fpath, "r", encoding="utf-8"))
                if isinstance(data, list):
                    candidate_domains.update(data)
                elif isinstance(data, dict):
                    for k in ["top_facade_domains", "media_player_domains", "deep_stream_domains"]:
                        candidate_domains.update(data.get(k, []))
            except Exception: pass

    print(f"  ├─ 成功搜集本地待测候选域名: {len(candidate_domains)} 个！", flush=True)
    print("  ├─ 正在本地国内网络环境中逐个探针 (超时 2.5 秒)...", flush=True)

    local_direct_domains = set()
    local_proxy_domains = set()

    count = 0
    total = len(candidate_domains)

    for dom in sorted(list(candidate_domains)):
        count += 1
        clean_d = final_clean_before_write(dom)
        if not clean_d: continue

        is_ok, ip_info = probe_domain_connectivity(clean_d)

        if is_ok:
            local_direct_domains.add(clean_d)
            print(f"  [{count}/{total}] [国内直连 OK] {clean_d} (IP: {ip_info})", flush=True)
        else:
            local_proxy_domains.add(clean_d)
            print(f"  [{count}/{total}] [被墙/超时 ➔ 归入代理] {clean_d} (原因: {ip_info})", flush=True)

    # 写盘 process/ 目录持久化
    open(os.path.join(PROCESS_DIR, "sanitized_candidate_domains.json"), "w", encoding="utf-8").write(
        json.dumps(sorted(list(local_direct_domains)), ensure_ascii=False, indent=2)
    )
    open(os.path.join(PROCESS_DIR, "sanitized_proxy_domains.json"), "w", encoding="utf-8").write(
        json.dumps(sorted(list(local_proxy_domains)), ensure_ascii=False, indent=2)
    )

    print("\n  ├─ 本地实测完成！写盘保存 process/ 目录，正在重新调用编译 .mrs...", flush=True)

    # 本地重新编译写盘 .mrs
    try:
        export_grouped_router_rules(WORK_DIR)
        print("  └─ 本地一键探测与 .mrs 编译打包 100% 成功完成！", flush=True)
        print("     提示：您可以运行 `git add .` 与 `git commit -m 'feat: update local probe results'` 将本地最准实测结果推送至 GitHub！", flush=True)
    except Exception as e:
        print(f"  └─ 编译打包异常: {e}", flush=True)

if __name__ == "__main__":
    run_local_probe()
