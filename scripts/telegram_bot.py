"""
Шаг 5: Telegram-бот — уведомление при заказе на сумму > 50 000 ₸
Принцип: поллинг RetailCRM каждые 60 сек, сравниваем с уже отправленными.
Запуск: python scripts/telegram_bot.py
"""

import json
import requests
import time
import os
from datetime import datetime, timezone, timedelta

RETAILCRM_URL  = os.getenv("RETAILCRM_URL",  "https://maratamangeldin.retailcrm.ru")
RETAILCRM_KEY  = os.getenv("RETAILCRM_KEY",  "Tyz5iPvsWyIKYbTd5nTJhR98HzNrOnDb")
TG_BOT_TOKEN   = os.getenv("TG_BOT_TOKEN",   "8237392640:AAHAB7mnR-7GIiwZgIAcnnDdXuX_1h84umM")
TG_CHAT_ID     = os.getenv("TG_CHAT_ID",     "-1003969063295")
THRESHOLD      = float(os.getenv("ORDER_THRESHOLD", "50000"))
POLL_INTERVAL  = int(os.getenv("POLL_INTERVAL", "60"))   # секунды
SEEN_FILE      = os.path.join(os.path.dirname(__file__), ".seen_orders.json")

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def send_telegram(message: str):
    url  = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id":    TG_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML",
    })
    return resp.json()

def fetch_recent_orders(minutes_back=5):
    """Забираем заказы за последние N минут."""
    since = (datetime.now(timezone.utc) - timedelta(minutes=minutes_back)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    resp = requests.get(
        f"{RETAILCRM_URL}/api/v5/orders",
        params={
            "apiKey":              RETAILCRM_KEY,
            "filter[createdAtFrom]": since,
            "limit":               100,
        },
    )
    data = resp.json()
    if not data.get("success"):
        print(f"[RetailCRM error] {data}")
        return []
    return data.get("orders", [])

def format_notification(order) -> str:
    customer = order.get("customer") or {}
    first    = customer.get("firstName", "")
    last     = customer.get("lastName", "")
    phones   = customer.get("phones", [])
    phone    = phones[0].get("number", "") if phones else "—"

    items    = order.get("items", [])
    items_str = "\n".join(
        f"  • {i.get('productName','?')} × {i.get('quantity',1)} = {i.get('initialPrice',0):,} ₸"
        for i in items
    ) or "  —"

    total = float(order.get("totalSumm", 0))

    return (
        f"🔔 <b>Крупный заказ!</b>\n\n"
        f"📦 <b>Заказ:</b> {order.get('number','—')}\n"
        f"👤 <b>Клиент:</b> {first} {last}\n"
        f"📱 <b>Телефон:</b> {phone}\n"
        f"💰 <b>Сумма:</b> <b>{total:,.0f} ₸</b>\n"
        f"📊 <b>Статус:</b> {order.get('status','—')}\n\n"
        f"🛍 <b>Состав:</b>\n{items_str}\n\n"
        f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

def main():
    print(f"Telegram-бот запущен. Порог: {THRESHOLD:,.0f} ₸")
    print(f"Интервал опроса: {POLL_INTERVAL} сек\n")

    # Тестовое сообщение при старте
    send_telegram(
        f"✅ <b>Modefica Dashboard Bot запущен</b>\n"
        f"Слежу за заказами > {THRESHOLD:,.0f} ₸"
    )

    seen = load_seen()

    while True:
        try:
            orders = fetch_recent_orders(minutes_back=POLL_INTERVAL // 60 + 2)

            for order in orders:
                order_id = str(order.get("id"))
                total    = float(order.get("totalSumm", 0))

                if order_id in seen:
                    continue

                seen.add(order_id)

                if total >= THRESHOLD:
                    msg = format_notification(order)
                    result = send_telegram(msg)
                    if result.get("ok"):
                        print(f"✓ Уведомление отправлено: заказ {order.get('number')} — {total:,.0f} ₸")
                    else:
                        print(f"✗ Ошибка Telegram: {result}")

            save_seen(seen)

        except Exception as e:
            print(f"[Ошибка] {e}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
