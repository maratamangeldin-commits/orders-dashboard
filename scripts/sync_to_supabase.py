"""
Шаг 3: RetailCRM → Supabase
Забирает заказы из RetailCRM API и кладёт в таблицу orders в Supabase.
Запуск: python scripts/sync_to_supabase.py
"""

import json
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

RETAILCRM_URL  = os.getenv("RETAILCRM_URL", "https://maratamangeldin.retailcrm.ru")
RETAILCRM_KEY  = os.getenv("RETAILCRM_KEY", "Tyz5iPvsWyIKYbTd5nTJhR98HzNrOnDb")
SUPABASE_URL   = os.getenv("SUPABASE_URL",  "https://kwhaxppswuezfngowwur.supabase.co")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY",  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt3aGF4cHBzd3VlemZuZ293d3VyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYxNjQ2OTEsImV4cCI6MjA5MTc0MDY5MX0.STFRpfPiXx0bbH1xrpVGSKSYgZR7J6GPdMMAQdhGTW8")

SUPABASE_HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "resolution=merge-duplicates",
}

def create_supabase_table():
    """
    SQL для создания таблицы — выполни один раз в Supabase SQL Editor:

    CREATE TABLE IF NOT EXISTS orders (
        id            BIGINT PRIMARY KEY,
        number        TEXT,
        external_id   TEXT,
        status        TEXT,
        total_summ    NUMERIC,
        created_at    TIMESTAMPTZ,
        customer_name TEXT,
        customer_phone TEXT,
        items         JSONB,
        synced_at     TIMESTAMPTZ DEFAULT NOW()
    );
    """
    print("ℹ  Таблица orders должна быть создана в Supabase SQL Editor.")
    print("   Скопируй SQL из комментария в начале этого файла и выполни.\n")

def fetch_retailcrm_orders(page=1, limit=100):
    """Получаем заказы постранично из RetailCRM."""
    resp = requests.get(
        f"{RETAILCRM_URL}/api/v5/orders",
        params={
            "apiKey": RETAILCRM_KEY,
            "limit":  limit,
            "page":   page,
        },
    )
    data = resp.json()
    if not data.get("success"):
        print(f"Ошибка RetailCRM: {data}")
        return [], 0
    pagination = data.get("pagination", {})
    total_pages = pagination.get("totalPageCount", 1)
    return data.get("orders", []), total_pages

def normalize_order(order):
    """Приводим заказ RetailCRM к плоской структуре для Supabase."""
    customer = order.get("customer") or {}
    first    = customer.get("firstName", "")
    last     = customer.get("lastName", "")
    phones   = customer.get("phones", [])
    phone    = phones[0].get("number", "") if phones else ""

    items = []
    for item in order.get("items", []):
        items.append({
            "name":     item.get("productName", ""),
            "quantity": item.get("quantity", 1),
            "price":    item.get("initialPrice", 0),
        })

    # Дата создания
    created_raw = order.get("createdAt", "")
    try:
        created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).isoformat()
    except Exception:
        created_at = created_raw

    return {
        "id":            order.get("id"),
        "number":        order.get("number", ""),
        "external_id":   str(order.get("externalId", "")),
        "status":        order.get("status", ""),
        "total_summ":    float(order.get("totalSumm", 0)),
        "created_at":    created_at,
        "customer_name": f"{first} {last}".strip(),
        "customer_phone": phone,
        "items":         json.dumps(items, ensure_ascii=False),
        "synced_at":     datetime.utcnow().isoformat() + "Z",
    }

def upsert_to_supabase(orders_batch):
    """Вставляем/обновляем заказы в Supabase (upsert по id)."""
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/orders",
        headers=SUPABASE_HEADERS,
        json=orders_batch,
    )
    if resp.status_code in (200, 201):
        return True, len(orders_batch)
    else:
        return False, resp.text

def main():
    create_supabase_table()

    print("Синхронизация RetailCRM → Supabase\n")
    page = 1
    total_synced = 0
    total_errors = 0

    while True:
        print(f"  Страница {page}...")
        orders_raw, total_pages = fetch_retailcrm_orders(page=page)

        if not orders_raw:
            print("  Нет заказов.")
            break

        batch = [normalize_order(o) for o in orders_raw]

        ok, result = upsert_to_supabase(batch)
        if ok:
            total_synced += result
            print(f"  ✓  Записано {result} заказов")
        else:
            total_errors += len(batch)
            print(f"  ✗  Ошибка Supabase: {result}")

        if page >= total_pages:
            break
        page += 1

    print(f"\n{'='*40}")
    print(f"Синхронизировано: {total_synced} заказов, ошибок: {total_errors}")

if __name__ == "__main__":
    main()
