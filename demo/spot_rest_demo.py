"""Spot REST trading demo for The20 Simulation SDK."""

import os
import time

from _sdk_loader import load_sdk

sdk = load_sdk()
SpotClient = sdk.SpotClient
The20APIError = sdk.The20APIError

BASE_URL = os.getenv("THE20_BASE_URL", "http://localhost:8083")
USERNAME = os.getenv("THE20_USERNAME", "client")
PASSWORD = os.getenv("THE20_PASSWORD", "client123")
SESSION_KEY = os.getenv("THE20_SESSION_KEY", "dbukjqfiralc73cbcme0")
SYMBOL = os.getenv("THE20_SYMBOL", "BTC_USDT_binance")


def main() -> None:
    client = SpotClient(
        base_url=BASE_URL,
        username=USERNAME,
        password=PASSWORD,
        session_key=SESSION_KEY,
    )
    print(f"Logged in as user_id={client.user_id}")

    # 1. Precision & market info
    ticker_info = client.get_ticker_info(SYMBOL)
    print("Ticker info:", ticker_info)

    book = client.get_orderbook(SYMBOL, limit=5)
    bids = book.get("bids")
    asks = book.get("asks")
    best_bid = next(iter(bids.items()), None) if isinstance(bids, dict) else (bids[0] if bids else None)
    best_ask = next(iter(asks.items()), None) if isinstance(asks, dict) else (asks[0] if asks else None)
    print(f"Best Bid: {best_bid} | Best Ask: {best_ask}")

    # 2. Portfolio balance
    portfolio = client.get_portfolio()
    print("Portfolio:", portfolio.get("data"))

    # 3. Place a far-away limit order (respecting tickSize / stepSize) and cancel it
    qty_scale = int(ticker_info.get("qty_scale", 2))
    price_scale = int(ticker_info.get("price_scale", 4))
    qty = round(10 ** (-qty_scale), qty_scale)
    limit_price = round(10000.0, price_scale)

    try:
        placed = client.limit_buy(SYMBOL, quantity=qty, price=limit_price)
        order_id = placed.get("orderId")
        print("Placed limit order:", order_id, placed.get("status"))

        time.sleep(0.5)
        canceled = client.cancel_order(SYMBOL, order_id=order_id)
        print("Canceled order:", canceled)
    except The20APIError as exc:
        print("Order error:", exc)

    # 4. Query history & trades (including fee)
    history = client.get_order_history(page=1, page_size=5)
    trades = client.get_trade_history(page=1, page_size=5)
    print(f"Order history total={history.get('total')}, latest={history.get('data', [])[:1]}")
    print(f"Trade history total={trades.get('total')}, latest={trades.get('data', [])[:1]}")


if __name__ == "__main__":
    main()
