-- Инициализация базы данных для Telegram-бота музыкального фестиваля

-- Пользователи
CREATE TABLE IF NOT EXISTS users (
                                     id BIGINT PRIMARY KEY,
                                     username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Обращения в поддержку (обновленная структура)
CREATE TABLE IF NOT EXISTS support_tickets (
                                               id SERIAL PRIMARY KEY,
                                               user_id BIGINT,
                                               email VARCHAR(255),
    message TEXT,
    photo_file_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'open',
    thread_id INTEGER,
    initial_message_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Ответы сотрудников поддержки и администраторов (обновленная структура)
CREATE TABLE IF NOT EXISTS support_responses (
                                                 id SERIAL PRIMARY KEY,
                                                 ticket_id INTEGER REFERENCES support_tickets(id),
    staff_user_id BIGINT,                    -- ID сотрудника/администратора
    response_text TEXT,
    is_admin BOOLEAN DEFAULT FALSE,          -- Флаг: администратор или сотрудник
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Отзывы
CREATE TABLE IF NOT EXISTS feedback (
                                        id SERIAL PRIMARY KEY,
                                        user_id BIGINT,
                                        category VARCHAR(100),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Расписание
CREATE TABLE IF NOT EXISTS schedule (
                                        id SERIAL PRIMARY KEY,
                                        day INTEGER CHECK (day >= 1 AND day <= 5),
    time TIME,
    artist_name VARCHAR(255),
    stage VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Локации
CREATE TABLE IF NOT EXISTS locations (
                                         id SERIAL PRIMARY KEY,
                                         name VARCHAR(255) UNIQUE,
    description TEXT,
    coordinates VARCHAR(100),
    map_image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Активности
CREATE TABLE IF NOT EXISTS activities (
                                          id SERIAL PRIMARY KEY,
                                          name VARCHAR(255),
    type VARCHAR(100),
    description TEXT,
    schedule_info TEXT,
    location VARCHAR(255),
    registration_required BOOLEAN DEFAULT FALSE,
    registration_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Статистика использования
CREATE TABLE IF NOT EXISTS usage_stats (
                                           id SERIAL PRIMARY KEY,
                                           user_id BIGINT,
                                           action VARCHAR(255),
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_thread_id ON support_tickets(thread_id);
CREATE INDEX IF NOT EXISTS idx_feedback_category ON feedback(category);
CREATE INDEX IF NOT EXISTS idx_schedule_day ON schedule(day);
CREATE INDEX IF NOT EXISTS idx_usage_stats_action ON usage_stats(action);
CREATE INDEX IF NOT EXISTS idx_usage_stats_created_at ON usage_stats(created_at);

-- Добавление тестовых данных расписания
INSERT INTO schedule (day, time, artist_name, stage, description) VALUES
                                                                      (1, '14:00', 'Jazz Quartet "Midnight"', 'Главная сцена', 'Открытие фестиваля'),
                                                                      (1, '16:00', 'Saxophone Solo Project', 'Малая сцена', 'Инструментальный джаз'),
                                                                      (1, '18:00', 'The Blue Notes', 'Главная сцена', 'Классический джаз'),
                                                                      (1, '20:00', 'Modern Jazz Collective', 'Главная сцена', 'Современные интерпретации'),

                                                                      (2, '12:00', 'Youth Jazz Band', 'Малая сцена', 'Молодые таланты'),
                                                                      (2, '14:00', 'Piano & Vocals', 'Главная сцена', 'Джазовые стандарты'),
                                                                      (2, '16:00', 'Fusion Experiment', 'Малая сцена', 'Джаз-фьюжн'),
                                                                      (2, '18:00', 'Big Band Orchestra', 'Главная сцена', 'Оркестровый джаз'),
                                                                      (2, '20:00', 'Electro-Jazz', 'Главная сцена', 'Электронный джаз'),

                                                                      (3, '12:00', 'Acoustic Duo', 'Малая сцена', 'Акустический сет'),
                                                                      (3, '14:00', 'Latin Jazz Ensemble', 'Главная сцена', 'Латиноамериканский джаз'),
                                                                      (3, '16:00', 'Vocal Jazz Group', 'Малая сцена', 'Вокальный джаз'),
                                                                      (3, '18:00', 'International Jazz Stars', 'Главная сцена', 'Звезды мирового джаза'),
                                                                      (3, '20:00', 'Jam Session', 'Главная сцена', 'Открытая джем-сессия'),

                                                                      (4, '12:00', 'Student Showcase', 'Малая сцена', 'Студенческие проекты'),
                                                                      (4, '14:00', 'Smooth Jazz', 'Главная сцена', 'Смуз-джаз'),
                                                                      (4, '16:00', 'Bebop Revival', 'Малая сцена', 'Возрождение бибопа'),
                                                                      (4, '18:00', 'World Jazz Fusion', 'Главная сцена', 'Мировой джаз-фьюжн'),
                                                                      (4, '20:00', 'Closing Ceremony', 'Главная сцена', 'Церемония закрытия'),

                                                                      (5, '12:00', 'Jazz Brunch', 'Малая сцена', 'Джаз-бранч'),
                                                                      (5, '14:00', 'Retrospective Concert', 'Главная сцена', 'Ретроспектива фестиваля'),
                                                                      (5, '16:00', 'Final Jam', 'Главная сцена', 'Финальная джем-сессия'),
                                                                      (5, '18:00', 'Awards Ceremony', 'Главная сцена', 'Награждение участников')
    ON CONFLICT DO NOTHING;

-- Добавление локаций
INSERT INTO locations (name, description, coordinates) VALUES
                                                           ('Главная сцена', 'Основная концертная площадка', '55.7558,37.6176'),
                                                           ('Малая сцена', 'Камерная площадка для небольших составов', '55.7560,37.6180'),
                                                           ('Фудкорт', 'Зона питания с различными кухнями', '55.7562,37.6174'),
                                                           ('Зона мастер-классов', 'Образовательная зона', '55.7556,37.6182'),
                                                           ('Лекционный зал', 'Зона для проведения лекций и семинаров', '55.7559,37.6179'),
                                                           ('VIP-зона', 'Зона для VIP-гостей', '55.7559,37.6178')
    ON CONFLICT DO NOTHING;

-- Добавление активностей
INSERT INTO activities (name, type, description, schedule_info, location, registration_required, registration_url) VALUES
                                                                                                                       ('Основы игры на гитаре', 'мастер-класс', 'Изучение базовых аккордов и техник', 'Ежедневно 12:00-13:30', 'Зона мастер-классов', true, 'https://festival.com/register/guitar'),
                                                                                                                       ('Создание музыки на компьютере', 'мастер-класс', 'Digital Audio Workstation для начинающих', 'Ежедневно 14:00-15:30', 'Зона мастер-классов', true, 'https://festival.com/register/daw'),
                                                                                                                       ('Вокальная техника', 'мастер-класс', 'Развитие вокальных навыков', 'Ежедневно 16:00-17:30', 'Зона мастер-классов', true, 'https://festival.com/register/vocal'),
                                                                                                                       ('Написание песен', 'мастер-класс', 'Основы сочинения музыки и текстов', 'Ежедневно 18:00-19:30', 'Зона мастер-классов', true, 'https://festival.com/register/songwriting'),

-- Лекторий
                                                                                                                       ('История джаза', 'лекция', 'От истоков до наших дней', 'Ежедневно 10:00-11:00', 'Лекционный зал', false, null),
                                                                                                                       ('Музыкальная индустрия сегодня', 'лекция', 'Современные тренды и вызовы', 'Ежедневно 11:30-12:30', 'Лекционный зал', false, null),
                                                                                                                       ('Авторское право в музыке', 'лекция', 'Правовые аспекты музыкального творчества', 'Ежедневно 13:00-14:00', 'Лекционный зал', false, null),
                                                                                                                       ('Психология творчества', 'лекция', 'Креативность и вдохновение', 'Ежедневно 15:00-16:00', 'Лекционный зал', false, null),
                                                                                                                       ('Продвижение музыканта', 'лекция', 'Маркетинг в цифровую эпоху', 'Ежедневно 16:30-17:30', 'Лекционный зал', false, null)
    ON CONFLICT DO NOTHING;

-- Добавляем тестового пользователя-администратора (опционально)
-- INSERT INTO users (id, username, first_name, last_name) VALUES
-- (123456789, 'admin_user', 'Администратор', 'Фестиваля')
-- ON CONFLICT DO NOTHING;