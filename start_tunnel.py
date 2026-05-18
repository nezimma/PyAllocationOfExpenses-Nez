#!/usr/bin/env python3
"""
Запуск ngrok tunnel + автообновление API_BASE в docs/js/data.js + git push.

Использование:
    python start_tunnel.py

Требования:
    ngrok.exe должен быть в PATH или в папке проекта.
    Скачать: https://ngrok.com/download
    Настроить: ngrok config add-authtoken ВАШ_ТОКЕН
"""
import json
import re
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

DATA_JS = Path(__file__).parent / "docs" / "js" / "data.js"
API_BASE_RE = re.compile(r"(const API_BASE\s*=\s*')[^']*(';)")

_tunnel_url: str | None = None
_url_found = threading.Event()


def _read_output(proc: subprocess.Popen) -> None:
    for line in proc.stdout:
        text = line.decode(errors="replace").strip()
        if text:
            print(f"[ngrok] {text}", flush=True)


def _wait_for_url(timeout: int = 30) -> str | None:
    """Опрашивает ngrok API до получения публичного URL."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=2) as r:
                data = json.loads(r.read())
                for tunnel in data.get("tunnels", []):
                    url = tunnel.get("public_url", "")
                    if url.startswith("https://"):
                        return url
        except Exception:
            pass
        time.sleep(1)
    return None


def update_data_js(url: str) -> None:
    content = DATA_JS.read_text(encoding="utf-8")
    new_content = API_BASE_RE.sub(lambda m: m.group(1) + url + m.group(2), content)
    if new_content == content:
        print("[tunnel] data.js уже содержит нужный URL, пропускаем запись.")
        return
    DATA_JS.write_text(new_content, encoding="utf-8")
    print(f"[tunnel] data.js обновлён → {url}")


def git_push() -> None:
    repo = Path(__file__).parent
    stage_and_commit = [
        ["git", "add", "docs/js/data.js"],
        ["git", "commit", "-m", "chore: update API_BASE for tunnel session"],
    ]
    for cmd in stage_and_commit:
        result = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
        if result.returncode != 0:
            if "nothing to commit" in result.stdout + result.stderr:
                print("[git] Нечего коммитить, пропускаем.")
                return
            print(f"[git] Ошибка при {' '.join(cmd)}:\n{result.stderr}", file=sys.stderr)
            return
        print(f"[git] {' '.join(cmd)} — OK")

    for remote in ("origin", "sourcecraft"):
        cmd = ["git", "push", remote, "main"]
        result = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[git] Ошибка push → {remote}:\n{result.stderr}", file=sys.stderr)
        else:
            print(f"[git] push → {remote} — OK")


def main() -> None:
    print("[tunnel] Запускаю ngrok...")
    ngrok_exe = "ngrok"
    local_ngrok = Path(__file__).parent / "ngrok.exe"
    if local_ngrok.exists():
        ngrok_exe = str(local_ngrok)

    try:
        proc = subprocess.Popen(
            [ngrok_exe, "http", "8080"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        print(
            "[tunnel] ОШИБКА: ngrok не найден.\n"
            "Скачайте ngrok.exe: https://ngrok.com/download\n"
            "Настройте токен: ngrok config add-authtoken ВАШ_ТОКЕН",
            file=sys.stderr,
        )
        sys.exit(1)

    reader = threading.Thread(target=_read_output, args=(proc,), daemon=True)
    reader.start()

    print("[tunnel] Жду публичный URL от ngrok (до 30 сек)...")
    url = _wait_for_url(timeout=30)

    if not url:
        proc.terminate()
        print("[tunnel] ОШИБКА: URL не получен за 30 секунд.", file=sys.stderr)
        sys.exit(1)

    print(f"\n[tunnel] Публичный URL: {url}\n")
    update_data_js(url)
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
