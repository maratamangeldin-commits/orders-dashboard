"""
Шаг 2: Загрузка mock_orders.json в RetailCRM через API
Запуск: python scripts/upload_to_retailcrm.py
"""

import json
import requests
import time
import os
from datetime import datetime

RETAILCRM_URL = os.getenv("RETAILCRM_URL", "https://maratamangeldin.retailcrm.ru")
RETAILCRM_KEY = os.getenv("RETAILCRM_KEY", "Tyz5iPvsWyIKYbTd5nTJhR98HzNrOnDb")
ORDERS_FILE   = os.path.join(os.path.dirname(__file__), "..", "mock_orders.json")

STATUS_MAP = {
    "new":        "new",
    "processing": "in-processing",
    "complete":   "complete",
}

def load_orders():
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def create_customer(order):
    """Создаём клиента, возвращаем id."""
    customer_data = {
        "firstName": order["customer"]["firstName"],
        "lastName":  order["customer"]["lastName"],
        "phones":    [{"number": order["customer"]["phone"]}],
        "email":     order["customer"]["email"],
    }
    resp = requests.post(
        f"{RETAILCRM_URL}/api/v5/customers/create",
        data={"apiKey": RETAILCRM_KEY, "customer": json.dumps(customer_data)},
    )
    data = resp.json()
    if data.get("success"):
        return data.get("id")
    # Если уже существует — поиск по телефону
    search = requests.get(
        f"{RETAILCRM_URL}/api/v5/customers",
        params={"apiKey": RETAILCRM_KEY, "filter[phone]": order["customer"]["phone"]},
    ).json()
    customers = search.get("customers", [])
    if customers:
        return customers[0]["id"]
    return None

def create_order(order, customer_id):
    """Загружаем один заказ."""
    items = []
    for item in order.get("items", []):
        items.append({
            "offer":    {"externalId": f"product-{item['name'][:20].replace(' ', '-').lower()}"},
            "productName": item["name"],
            "quantity": item["quantity"],
            "initialPrice": item["price"],
        })

    order_data = {
        "number":    order["number"],
        "externalId": str(order["id"]),
        "status":    STATUS_MAP.get(order["status"], "new"),
        "createdAt": order["createdAt"],
        "totalSumm": order["totalSumm"],
        "customer":  {"id": customer_id} if customer_id else {
            "firstName": order["customer"]["firstName"],
            "lastName":  order["customer"]["lastName"],
            "phones":    [{"number": order["customer"]["phone"]}],
        },
        "items": items,
    }

    resp = requests.post(
        f"{RETAILCRM_URL}/api/v5/orders/create",
        data={"apiKey": RETAILCRM_KEY, "order": json.dumps(order_data)},
    )
    return resp.json()

def main():
    orders = load_orders()
    print(f"Загружаем {len(orders)} заказов в RetailCRM...\n")

    success_count = 0
    error_count   = 0

    for order in orders:
        try:
            # Создаём клиента
            customer_id = create_customer(order)

            # Создаём заказ
            result = create_order(order, customer_id)

            if result.get("success"):
                success_count += 1
                print(f"  ✓  {order['number']} — {order['totalSumm']:,} ₸ ({order['status']})")
            else:
                error_count += 1
                err = result.get("errorMsg") or result.get("errors", "неизвестная ошибка")
                print(f"  ✗  {order['number']} — ошибка: {err}")

            # Пауза чтобы не превысить лимит API (250 req/min)
            time.sleep(0.3)

        except Exception as e:
            error_count += 1
            print(f"  ✗  {order['number']} — исключение: {e}")

    print(f"\n{'='*40}")
    print(f"Готово: успешно {success_count}, ошибок {error_count}")

if __name__ == "__main__":
    main()
