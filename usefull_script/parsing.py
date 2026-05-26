from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import csv
import re

# ── Настрой под каждый запуск ──────────────────────────────────
OUTPUT_FILE = "../DatasetK.csv"
DELIMITER = "|"
URL = "https://tech.onliner.by/tests"
CATEGORY = "Техника"
TARGET = 350     # сколько строк хотим (100–200)
MAX_PER_ARTICLE = 20  # не брать больше N строк из одной статьи
# ───────────────────────────────────────────────────────────────



def _parse_article(driver, limit: int) -> list[str]:
    result = []
    try:
        news_text = driver.find_element(By.CLASS_NAME, "news-text")
        for p in news_text.find_elements(By.TAG_NAME, "p"):
            if len(result) >= limit:
                break
            text = p.text.strip()
            if len(text) < 30:
                continue
            lower = text.lower()
            if any(w in lower for w in ["реклам", "партнёр", "партнер", "спонсор"]):
                continue
            sentences = re.split(r"(?<=[.!?])\s+", text)
            combined = " ".join(sentences[:3]).strip()
            if len(combined) >= 30:
                result.append(combined)
    except Exception as e:
        print(f"  ⚠️ Ошибка чтения тела: {e}")
    return result


driver = webdriver.Chrome()
driver.get(URL)
time.sleep(5)

rows: list[tuple[str, str]] = []
visited: set[str] = set()
i = 0
stall = 0  # сколько раз подряд не загрузились новые посты

while len(rows) < TARGET:
    posts = driver.find_elements(By.CLASS_NAME, "news-tiles__stub")

    # дошли до конца — пробуем загрузить ещё
    if i >= len(posts[4:]):
        prev = len(posts[4:])
        try:
            btn = driver.find_element(By.CLASS_NAME, "news-more__control")
            driver.execute_script("arguments[0].click();", btn)
            print("🔄 'Показать ещё'")
        except Exception:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print("🔄 Скролл вниз")
        time.sleep(3)

        if len(driver.find_elements(By.CLASS_NAME, "news-tiles__stub")) == prev:
            stall += 1
            if stall >= 3:
                print("❌ Новые посты не появляются — выходим")
                break
        else:
            stall = 0
        continue

    post = posts[4:][i]

    try:
        post.click()
    except Exception as e:
        print(f"⚠️ [{i}] не удалось кликнуть: {e}")
        i += 1
        continue

    time.sleep(3)
    current_url = driver.current_url

    # реклама — увела на внешний сайт
    if "onliner.by" not in current_url:
        print(f"⏭️ [{i}] реклама ({current_url[:60]}) — назад")
        driver.back()
        time.sleep(2)
        i += 1
        continue

    # уже видели эту статью
    if current_url in visited:
        driver.back()
        time.sleep(2)
        i += 1
        continue

    visited.add(current_url)

    try:
        title = driver.find_element(By.CLASS_NAME, "news-header__title").text
    except Exception:
        title = ""

    want = min(MAX_PER_ARTICLE, TARGET - len(rows))
    got = _parse_article(driver, want)
    for text in got:
        rows.append((title, text))

    print(f"  ✅ [{i}] «{title[:55]}» +{len(got)} (итого {len(rows)}/{TARGET})")

    driver.back()
    time.sleep(3)
    i += 1

# запись
with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter=DELIMITER)
    for title, text in rows:
        writer.writerow([0, URL, title, CATEGORY, text])

print(f"\n✅ Записано строк: {len(rows)}")
driver.quit()
