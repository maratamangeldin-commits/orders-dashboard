# Modefica Orders Dashboard

Мини-дашборд заказов: RetailCRM → Supabase → Vercel + Telegram-бот.

## Стек
- **RetailCRM** — источник заказов
- **Supabase** — хранилище данных (PostgreSQL)
- **Vercel** — хостинг дашборда
- **Telegram Bot** — уведомления о крупных заказах (> 50 000 ₸)
- **Python 3.10+** — скрипты синхронизации

---

## Быстрый старт

### 1. Установка зависимостей
```bash
pip install requests
```

### 2. Создать таблицу в Supabase
Открой **Supabase → SQL Editor** и выполни:
```sql
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
```

> **Важно**: чтобы дашборд мог читать данные без авторизации,  
> отключи RLS: `ALTER TABLE orders DISABLE ROW LEVEL SECURITY;`

### 3. Загрузить тестовые заказы в RetailCRM
```bash
python scripts/upload_to_retailcrm.py
```

### 4. Синхронизировать RetailCRM → Supabase
```bash
python scripts/sync_to_supabase.py
```

### 5. Задеплоить дашборд на Vercel
```bash
npm i -g vercel
vercel --prod
```
Или подключи репозиторий через vercel.com → Import Project.

### 6. Запустить Telegram-бот
```bash
python scripts/telegram_bot.py
```
Бот будет опрашивать RetailCRM каждые 60 сек и присылать уведомление  
при появлении заказа на сумму **> 50 000 ₸**.

---

## Структура проекта
```
orders-dashboard/
├── scripts/
│   ├── upload_to_retailcrm.py   # Шаг 2: загрузка mock_orders.json
│   ├── sync_to_supabase.py      # Шаг 3: RetailCRM → Supabase
│   └── telegram_bot.py          # Шаг 5: Telegram уведомления
├── dashboard/
│   └── index.html               # Шаг 4: дашборд (Chart.js + Supabase)
├── mock_orders.json             # 50 тестовых заказов
├── vercel.json                  # Конфиг Vercel
├── .env.example                 # Пример переменных окружения
└── README.md
```

---

## Промпты Claude Code (что давал, где застрял)

### Промпт 1 — Структура проекта
```
Построй структуру проекта orders-dashboard для тестового задания.
Нужны скрипты: загрузка в RetailCRM, синхронизация в Supabase,
Telegram-бот. Дашборд на чистом HTML + Chart.js.
```
**Результат:** сгенерировал полную структуру папок с заглушками.

### Промпт 2 — upload_to_retailcrm.py
```
Напиши Python-скрипт для загрузки mock_orders.json в RetailCRM v5 API.
Создавай клиентов перед созданием заказа. Добавь обработку дубликатов.
```
**Застрял:** API RetailCRM возвращал ошибку на поле `offer` без `externalId`.  
**Решение:** добавил генерацию `externalId` из названия товара.

### Промпт 3 — sync_to_supabase.py
```
Напиши скрипт синхронизации RetailCRM → Supabase через REST API.
Upsert по полю id, обработка пагинации, нормализация полей.
```
**Застрял:** Supabase возвращал 409 без заголовка `Prefer: resolution=merge-duplicates`.  
**Решение:** добавил заголовок в SUPABASE_HEADERS.

### Промпт 4 — Дашборд
```
Сделай тёмный дашборд на HTML + Chart.js. Данные из Supabase REST API.
KPI: всего заказов, выручка, средний чек, крупные заказы > 50 000 ₸.
График по дням и donut статусов. Таблица всех заказов.
```
**Застрял:** CORS при запросе к Supabase из локального файла.  
**Решение:** дашборд работает только с деплоя (Vercel) или localhost с сервером.

### Промпт 5 — Telegram-бот
```
Напиши Telegram-бота на Python (без aiogram, только requests).
Поллинг RetailCRM каждые 60 сек, уведомление при заказе > 50 000 ₸.
Сохранять уже отправленные ID чтобы не дублировать.
```
**Застрял:** бот слал дубли при рестарте.  
**Решение:** добавил `.seen_orders.json` для персистентного хранения отправленных ID.

---

## Переменные окружения
Скопируй `.env.example` в `.env` и заполни:
```bash
cp .env.example .env
```
