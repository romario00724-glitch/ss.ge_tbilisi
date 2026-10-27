#!/usr/bin/env python3
"""
Запуск бота на Mac (з 27.10.2026) — те саме, що робив workflow на GitHub: оновити код,
один прохід по ss.ge (watcher.py --once) і зберегти state.json на GitHub.

27.10.2026 ~16:15 ss.ge сховав за Cloudflare і API (api-gateway.ss.ge): сервери GitHub отримують
403 навіть із правильним ключем. З Mac усе відкривається, тож перевірки тепер робить Mac.

launchd не має доступу до «Робочого столу», тому працює окрема копія репозиторію:
  ~/Library/Application Support/ss.ge_tbilisi/repo/       (git clone плюс telegram.json)
  ~/Library/LaunchAgents/local.ss.ge_tbilisi.watch.plist  (розклад: :05, :15, :25…)
  ~/Library/Logs/ss.ge_tbilisi.log                        (журнал)
Код оновлюється сам: перед кожним проходом — git pull (цей файл теж).
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
WATCHER_TIMEOUT = 8 * 60  # як timeout-minutes у workflow


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO_DIR, capture_output=True, text=True, timeout=120)


def rebase_onto_github(*extra):
    """git pull --rebase; якщо не вийшло — повернути все як було, щоб наступний запуск не застряг."""
    result = git("pull", "-q", "--rebase", "--autostash", *extra)
    if result.returncode:
        git("rebase", "--abort")
    return result


def save_state():
    """Як крок «Save state.json» у workflow: закомітити state.json і викласти на GitHub.
    Викладає й коміти, що не дійшли минулого разу (git push чи git pull тоді не вдався)."""
    if (REPO_DIR / "state.json").exists():
        git("add", "state.json")
        if git("diff", "--cached", "--quiet").returncode:
            git("commit", "-q", "-m", "state: update [skip ci]")
    if git("rev-list", "--count", "@{u}..HEAD").stdout.strip() == "0":
        return  # на GitHub уже все є
    for _ in range(3):
        if git("push", "-q").returncode == 0:
            return
        rebase_onto_github("-X", "theirs")
        time.sleep(3)
    log("не вдалося зберегти state.json на GitHub — спробую наступного запуску")


def main():
    pull = rebase_onto_github()
    if pull.returncode:
        log(f"git pull не вдався, перевіряю з поточним кодом: {(pull.stderr or pull.stdout).strip()[:200]}")
    try:
        subprocess.run([sys.executable, "watcher.py", "--once"], cwd=REPO_DIR, timeout=WATCHER_TIMEOUT)
    except subprocess.TimeoutExpired:
        log(f"watcher.py працював понад {WATCHER_TIMEOUT // 60} хв — зупинено")
    save_state()


if __name__ == "__main__":
    main()
