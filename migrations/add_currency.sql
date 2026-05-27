-- migrations/add_currency.sql
-- Добавляет поддержку мультивалютности.
-- Запуск: psql -U <user> -d allocationofexpenses -f migrations/add_currency.sql

ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'BYN';

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS preferred_currency VARCHAR(3) NOT NULL DEFAULT 'BYN';

-- Проверка
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name IN ('expenses', 'users')
  AND column_name IN ('currency', 'preferred_currency')
ORDER BY table_name, column_name;
