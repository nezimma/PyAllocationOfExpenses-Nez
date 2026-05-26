import csv

INPUT_FILE = "../DatasetK.csv"

# ─── НАСТРОЙКИ ────────────────────────────────────────────────
# Что заменить → на что. Можно добавить сколько угодно пар.
RENAME_MAP = {
    "Снеки":              "Ресторан и еда",
    "Кафе":               "Ресторан и еда",
    "Мебель":              "Жилье",
    "Коммуналка":               "Жилье",
    # "Старое название":  "Новое название",
}
# ──────────────────────────────────────────────────────────────

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    reader = csv.reader(f, delimiter="|")
    lines = list(reader)

changed = 0
counters: dict[str, int] = {}

for row in lines:
    if len(row) < 4:
        continue
    cat = row[3].strip()
    if cat in RENAME_MAP:
        new_cat = RENAME_MAP[cat]
        counters[f"{cat} → {new_cat}"] = counters.get(f"{cat} → {new_cat}", 0) + 1
        row[3] = new_cat
        changed += 1

with open(INPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter="|")
    writer.writerows(lines)

if changed:
    print(f"✅ Изменено {changed} строк:")
    for label, count in counters.items():
        print(f"   {label}: {count} шт")
else:
    print("⚠️  Ничего не найдено. Проверь названия в RENAME_MAP.")

# Показываем все уникальные категории после замены
categories = set()
for row in lines:
    if len(row) >= 4 and row[3].strip() and row[3].strip() != "category":
        categories.add(row[3].strip())
print(f"\nКатегории в датасете сейчас: {sorted(categories)}")
