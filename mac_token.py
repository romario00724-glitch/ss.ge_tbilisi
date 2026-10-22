#!/usr/bin/env python3
"""
Mac бере ключ до API ss.ge і кладе його в секрет SSGE_API_TOKEN цього репозиторію на GitHub.

З 22.10.2026 ss.ge (Cloudflare) не пускає сервери GitHub на свої сторінки, а ключ є лише там.
Сам API серверам GitHub відкритий, тож ключ бере Mac (його інтернет ss.ge пускає), а бот на
GitHub ним користується. Ключ діє годину, тому launchd запускає цей скрипт кожні 20 хв.

launchd не має доступу до «Робочого столу», тому на Mac працює копія поза ним:
  ~/Library/Application Support/ss.ge_tbilisi/mac_token.py   (копія цього файлу)
  ~/Library/LaunchAgents/local.ss.ge_tbilisi.token.plist     (розклад)
  ~/Library/Logs/ss.ge_tbilisi_token.log                     (журнал)
Після зміни цього файлу — скопіювати його туди заново (див. CLAUDE.md).
"""

import json
import re
import subprocess
import sys
import time
from datetime import datetime

REPO = "romario00724-glitch/ss.ge_tbilisi"
SECRET = "SSGE_API_TOKEN"
HOME_PAGE = "https://home.ss.ge/ru/"
GH = "/opt/homebrew/bin/gh"
ATTEMPTS = 3          # після пробудження Mac інтернет з'являється не одразу
PAUSE_SECONDS = 30


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def fetch_token():
    from curl_cffi import requests
    resp = requests.get(HOME_PAGE, headers={"Accept-Language": "ru"}, impersonate="chrome", timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"ss.ge: HTTP {resp.status_code}")
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.S)
    if not match:
        raise RuntimeError("на сторінці ss.ge немає даних")
    props = json.loads(match.group(1)).get("props") or {}
    token = str((props.get("pageProps") or {}).get("credentialsToken") or "").strip()
    if not token:
        raise RuntimeError("на сторінці ss.ge немає ключа до API")
    return token


def save_secret(token):
    result = subprocess.run([GH, "secret", "set", SECRET, "-R", REPO], input=token, text=True,
                            capture_output=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"gh: {(result.stderr or result.stdout).strip()[:200]}")


def main():
    for attempt in range(1, ATTEMPTS + 1):
        try:
            save_secret(fetch_token())
            log("ключ оновлено")
            return 0
        except Exception as e:
            log(f"спроба {attempt}: {e}")
            if attempt < ATTEMPTS:
                time.sleep(PAUSE_SECONDS)
    return 1


if __name__ == "__main__":
    sys.exit(main())
