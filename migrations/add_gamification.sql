-- migrations/add_gamification.sql — таблицы геймификации

-- ── 1. Финансовые вызовы ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS challenges (
    challenge_id    SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category_key    TEXT    NOT NULL,                  -- 'restaurants', 'transport', ...
    category_label  TEXT    NOT NULL,                  -- 'Рестораны и еда', ...
    title           TEXT    NOT NULL,
    target_amount   NUMERIC(12,2) NOT NULL,
    currency        TEXT    NOT NULL DEFAULT 'BYN',
    period_start    DATE    NOT NULL,
    period_end      DATE    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'active',  -- active | success | failed | cancelled
    notified_pct    INTEGER NOT NULL DEFAULT 0,          -- 0 / 50 / 80 / 90 (уже отправлено)
    next_notify_at  TIMESTAMPTZ,
    avg_amount      NUMERIC(12,2),                     -- среднее за прошлые месяцы (для инфо)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_challenges_user_status
    ON challenges(user_id, status);

CREATE INDEX IF NOT EXISTS idx_challenges_notify
    ON challenges(next_notify_at)
    WHERE status = 'active';

-- ── 2. Каталог достижений ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS achievements (
    achievement_id  SERIAL PRIMARY KEY,
    code            TEXT UNIQUE NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    icon            TEXT NOT NULL DEFAULT '🏆',
    condition_type  TEXT NOT NULL
);

INSERT INTO achievements (code, title, description, icon, condition_type) VALUES
    ('first_win',  'Первая победа',    'Успешно завершён первый финансовый вызов',        '🏆', 'challenge_success'),
    ('saver_3',    'Экономный ×3',     'Три успешных вызова подряд',                      '🥉', 'streak_3'),
    ('saver_5',    'Мастер бюджета',   'Пять успешных вызовов подряд',                    '🥇', 'streak_5'),
    ('big_save',   'Большая экономия', 'Сэкономлено более 500 Br в одном вызове',         '💰', 'saved_amount_500'),
    ('iron_will',  'Железная воля',    'Принял новый вызов после неудачи',                '💪', 'retry_after_fail'),
    ('no_spend',   'Ноль трат',        'Ничего не потрачено в категории за весь месяц',   '🌟', 'zero_spend'),
    ('under_50',   'С большим запасом','Выполнил вызов, потратив менее 50% лимита',       '🎯', 'under_50pct')
ON CONFLICT (code) DO NOTHING;

-- ── 3. Достижения пользователей ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_achievements (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    achievement_id  INTEGER NOT NULL REFERENCES achievements(achievement_id),
    challenge_id    INTEGER REFERENCES challenges(challenge_id),
    earned_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, achievement_id)
);

CREATE INDEX IF NOT EXISTS idx_user_achievements_user
    ON user_achievements(user_id);
