-- migrations/add_new_categories.sql
-- Полный upsert всех 9 категорий: вставляет новые, обновляет description у существующих.
-- Запустить: psql -U <user> -d <db> -f migrations/add_new_categories.sql

DO $$
DECLARE
    cat RECORD;
BEGIN
    FOR cat IN
        SELECT *
        FROM (VALUES
            ('Рестораны и еда',  'Кафе, рестораны, фастфуд, продукты, доставка еды'),
            ('Транспорт',        'Такси, каршеринг, общественный транспорт, топливо, парковка'),
            ('Жилье',            'Аренда, ипотека, коммунальные услуги, электричество, вода'),
            ('Одежда',           'Одежда, обувь, аксессуары, интернет-магазины одежды'),
            ('Быт',              'Бытовая техника, мебель, посуда, хозтовары, уборка'),
            ('Техника',          'Смартфоны, ноутбуки, планшеты, гаджеты, электроника'),
            ('Образование',      'Онлайн-курсы, репетиторы, учебники, канцтовары, обучение'),
            ('Развлечения',      'Кино, театр, концерты, игры, стриминг, хобби, досуг'),
            ('Здоровье',         'Аптека, врачи, анализы, фитнес, массаж, лекарства')
        ) AS t(name, description)
    LOOP
        IF EXISTS (SELECT 1 FROM categories WHERE name = cat.name) THEN
            UPDATE categories
               SET description = cat.description
             WHERE name = cat.name;
        ELSE
            INSERT INTO categories (name, description)
            VALUES (cat.name, cat.description);
        END IF;
    END LOOP;
END;
$$;

-- Проверка результата
SELECT category_id, name, description FROM categories ORDER BY category_id;
