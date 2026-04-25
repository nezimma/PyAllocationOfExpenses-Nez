#!/usr/bin/env python3
"""
Запуск Cloudflare Tunnel + автообновление API_BASE в docs/js/data.js + git push.

Использование:
    python start_tunnel.py

Требования:
    cloudflared.exe должен быть в PATH или в папке проекта.
    Скачать: https://github.com/cloudflare/cloudflared/releases/latest
"""
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

DATA_JS = Path(__file__).parent / "docs" / "js" / "data.js"
API_BASE_RE = re.compile(r"(const API_BASE\s*=\s*')[^']*(';)")
TUNNEL_URL_RE = re.compile(r"https://[a-z0-9\-]+\.trycloudflare\.com")

_tunnel_url: str | None = None
_url_found = threading.Event()


def _read_output(proc: subprocess.Popen) -> None:
    """Читает stdout+stderr cloudflared, ищет публичный URL."""
    global _tunnel_url
    for line in proc.stderr:
        text = line.decode(errors="replace").strip()
        print(f"[cloudflared] {text}", flush=True)
        if not _url_found.is_set():
            m = TUNNEL_URL_RE.search(text)
            if m:
                _tunnel_url = m.group(0)
                _url_found.set()


def update_data_js(url: str) -> None:
    content = DATA_JS.read_text(encoding="utf-8")
    new_content = API_BASE_RE.sub(lambda m: m.group(1) + url + m.group(2), content)
    if new_content == content:
        print(f"[tunnel] data.js уже содержит нужный URL, пропускаем запись.")
        return
    DATA_JS.write_text(new_content, encoding="utf-8")
    print(f"[tunnel] data.js обновлён → {url}")


def git_push() -> None:
    repo = Path(__file__).parent
    cmds = [
        ["git", "add", "docs/js/data.js"],
        ["git", "commit", "-m", "chore: update API_BASE for tunnel session"],
        ["git", "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
        if result.returncode != 0:
            # "nothing to commit" — не ошибка
            if "nothing to commit" in result.stdout + result.stderr:
                print("[git] Нечего коммитить, пропускаем.")
                return
            print(f"[git] Ошибка при {' '.join(cmd)}:\n{result.stderr}", file=sys.stderr)
            return
        print(f"[git] {' '.join(cmd)} — OK")


def main() -> None:
    print("[tunnel] Запускаю cloudflared...")
    try:
        proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", "http://localhost:8080"],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print(
            "[tunnel] ОШИБКА: cloudflared не найден.\n"
            "Скачайте cloudflared.exe и положите рядом с проектом или добавьте в PATH:\n"
            "https://github.com/cloudflare/cloudflared/releases/latest",
            file=sys.stderr,
        )
        sys.exit(1)

    reader = threading.Thread(target=_read_output, args=(proc,), daemon=True)
    reader.start()

    print("[tunnel] Жду URL от cloudflared (до 30 сек)...")
    if not _url_found.wait(timeout=30):
        proc.terminate()
        print("[tunnel] ОШИБКА: URL не получен за 30 секунд.", file=sys.stderr)
        sys.exit(1)

    print(f"\n[tunnel] Публичный URL: {_tunnel_url}\n")
    update_data_js(_tunnel_url)
    git_push()

    print("\n[tunnel] Туннель активен. Нажмите Ctrl+C для остановки.\n")
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n[tunnel] Останавливаю...")
        proc.terminate()
        time.sleep(1)


if __name__ == "__main__":
    main()
