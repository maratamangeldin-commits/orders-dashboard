GBC — Orders Dashboard

Автоматизированный дашборд заказов: RetailCRM → Supabase → Vercel + Telegram-уведомления.

    Стек
- RetailCRM — источник заказов (API v5)
- Supabase — PostgreSQL-хранилище с REST API
- Vercel — хостинг статического дашборда
- Chart.js — визуализация данных
- Python 3.11 — скрипты синхронизации
- Telegram Bot API — уведомления о крупных заказах



    Архитектура


RetailCRM API
     │
     ▼
upload_to_retailcrm.py   ← загрузка тестовых заказов
     │
     ▼
sync_to_supabase.py      ← синхронизация в БД
     │
     ▼
Supabase (PostgreSQL)
     │
     ├──▶ dashboard/index.html   ← Vercel (Chart.js)
     │
     └──▶ telegram_bot.py        ← уведомления > 50 000 ₽




    Быстрый старт

   // 1. Установка зависимостей
bash
pip install requests python-dotenv


   // 2. Переменные окружения
bash
cp .env.example .env

Заполни `.env` своими ключами.

   // 3. Создать таблицу в Supabase
Выполни в Supabase → SQL Editor:
sql
CREATE TABLE IF NOT EXISTS orders (
    id             BIGINT PRIMARY KEY,
    number         TEXT,
    external_id    TEXT,
    status         TEXT,
    total_summ     NUMERIC,
    created_at     TIMESTAMPTZ,
    customer_name  TEXT,
    customer_phone TEXT,
    items          JSONB,
    synced_at      TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE orders DISABLE ROW LEVEL SECURITY;


   // 4. Загрузить тестовые заказы
bash
python scripts/upload_to_retailcrm.py
python scripts/sync_to_supabase.py


   // 5. Деплой дашборда
bash
// Подключи репозиторий на vercel.com
// Output Directory: dashboard


   // 6. Запустить Telegram-бот
bash
python scripts/telegram_bot.py




    Структура проекта

orders-dashboard/
├── .github/
│   └── workflows/
│       └── sync.yml             // Автосинхронизация каждые 5 мин
├── scripts/
│   ├── upload_to_retailcrm.py   // Загрузка mock_orders.json в RetailCRM
│   ├── sync_to_supabase.py      // RetailCRM → Supabase
│   └── telegram_bot.py          // Уведомления о крупных заказах
├── dashboard/
│   └── index.html               // Дашборд (Chart.js + Supabase REST)
├── mock_orders.json             // 50 тестовых заказов
├── .env.example
└── README.md




    Промпты Claude (prompt engineering)

   // Промпт 1 — Проектирование архитектуры

Спроектируй архитектуру мини-дашборда заказов со следующими требованиями:
- Источник данных: RetailCRM API v5
- Хранилище: Supabase (PostgreSQL)
- Фронтенд: статический HTML, деплой на Vercel
- Уведомления: Telegram Bot при заказах выше порогового значения

Предложи структуру проекта, список скриптов и порядок интеграции сервисов.
Учти rate limits API и обработку дублей при повторном запуске.


   // Промпт 2 — Загрузка заказов в RetailCRM

Напиши Python-скрипт для пакетной загрузки заказов из JSON-файла в RetailCRM API v5.

Требования:
- Сначала создавать клиента, затем привязывать к заказу
- Обрабатывать дубликаты (если клиент уже существует — найти по телефону)
- Маппинг статусов из внутреннего формата в RetailCRM
- Rate limiting: пауза между запросами чтобы не превысить лимит API
- Подробный вывод: успех/ошибка по каждому заказу с итоговой статистикой


   // Промпт 3 — Синхронизация в Supabase

Напиши скрипт синхронизации RetailCRM → Supabase через REST API.

Требования:
- Получать заказы постранично (pagination)
- Нормализовать вложенную структуру RetailCRM в плоскую таблицу
- Upsert по первичному ключу (не дублировать при повторном запуске)
- Корректно обрабатывать даты с timezone offset
- Выводить прогресс постранично


   // Промпт 4 — Дашборд

Создай одностраничный дашборд на чистом HTML + Chart.js без фреймворков.
Данные получать из Supabase REST API на клиенте.

Требования к UI:
- Тёмная тема, профессиональный вид
- KPI-карточки: всего заказов, выручка, средний чек, крупные заказы (> 50 000)
- Bar chart: количество заказов по дням
- Doughnut chart: распределение по статусам
- Таблица всех заказов с сортировкой по дате
- Автообновление каждые 60 секунд без перезагрузки страницы
- Визуальное выделение крупных заказов в таблице


   // Промпт 5 — Telegram-бот

Напиши Telegram-бота для мониторинга заказов на чистом Python (только requests, без aiogram).

Требования:
- Polling RetailCRM каждые N секунд (настраивается через env)
- Отправлять уведомление если сумма заказа превышает порог (настраивается)
- Исключить дубли: хранить ID уже отправленных уведомлений между перезапусками
- Форматированное сообщение: номер заказа, клиент, сумма, статус, состав
- Все параметры через переменные окружения (.env)





    Проблемы и решения

   // Формат даты отклонён RetailCRM API
Проблема: RetailCRM v5 возвращал ошибку `Invalid datetime` при загрузке заказов — ISO 8601 формат с timezone offset (`2025-03-01T09:15:00+06:00`) не принимался.

Решение: Преобразование даты в формат `Y-m-d H:i:s` через `datetime.fromisoformat().strftime()` перед отправкой в API.



   // Маппинг статусов RetailCRM
Проблема: 17 из 50 заказов не загружались — статус `processing` не существует в RetailCRM, система ожидала `in-processing`. Ошибка `Order is not loaded` не указывала на конкретное поле.

Решение: Дебаг через анализ паттерна ошибок (падали строго чётные заказы). Все нестандартные статусы замаплены на `new` как безопасный fallback.



   // Supabase schema cache
Проблема: Скрипт синхронизации падал с ошибкой `Could not find the 'external_id' column` несмотря на то что таблица была создана корректно.

Решение: Пересоздание таблицы через `DROP TABLE IF EXISTS` + `CREATE TABLE` сбросило кеш схемы Supabase и колонка стала видна.



   // Chart.js: повторная инициализация canvas
Проблема: При автообновлении дашборда каждые 60 секунд Chart.js падал с ошибкой `Canvas is already in use` — нельзя создать новый chart на canvas который уже занят.

Решение: Хранение инстансов графиков в переменных `chartDaily` и `chartStatus`. Перед каждым ре-рендером вызов `.destroy()` для очистки canvas.



   // Vercel деплоил первый коммит вместо последнего
Проблема: Несмотря на новые пуши, Vercel продолжал показывать `Initial commit` как источник деплоя. Форс-пуш и переподключение репозитория не помогали.

Решение: Полное удаление проекта на Vercel и создание нового с явным указанием `Output Directory: dashboard` в настройках билда. Конфигурация через `vercel.json` конфликтовала с настройками проекта.
