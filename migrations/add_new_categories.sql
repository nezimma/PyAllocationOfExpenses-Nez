-- migrations/add_new_categories.sql
-- Добавляет три новые категории расходов: Образование, Развлечения, Здоровье
-- Запустить: psql -U <user> -d <db> -f migrations/add_new_categories.sql

INSERT INTO categories (name)
SELECT name FROM (VALUES
    ('Образование'),
    ('Развлечения'),
    ('Здоровье')
) AS new_cats(name)
WHERE NOT EXISTS (
    SELECT 1 FROM categories c WHERE c.name = new_cats.name
);
