"""Futures REST + WebSocket demo for The20 Simulation SDK."""

import os
import time

from _sdk_loader import load_sdk

sdk = load_sdk()
FuturesClient = sdk.FuturesClient
The20APIError = sdk.The20APIError

BASE_URL = os.getenv("THE20_BASE_URL", "http://localhost:8083")
USERNAME = os.getenv("THE20_USERNAME", "client")
PASSWORD = os.getenv("THE20_PASSWORD", "client123")
SESSION_KEY = os.getenv("THE20_FUTURES_SESSION_KEY", "your_futures_session_key")
SYMBOL = os.getenv("THE20_FUTURES_SYMBOL", "BTCUSDT")


def main() -> None:
    futures = FuturesClient(
        base_url=BASE_URL,
        username=USERNAME,
        password=PASSWORD,
        session_key=SESSION_KEY,
    )
    print(f"Logged in as user_id={futures.user_id}")

    try:
        print("Commission rate:", futures.get_commission_rate(SYMBOL))
        print("Balance:", futures.get_balance())
        print("Positions:", futures.get_positions(SYMBOL))

        # Example: set leverage and place a limit order
        # futures.set_leverage(SYMBOL, leverage=10)
        # order = futures.limit_buy(SYMBOL, quantity=0.01, price=50000.0)
        # print("Placed futures order:", order)
    except The20APIError as exc:
        print("API error (check THE20_FUTURES_SESSION_KEY):", exc)

    # Futures WebSocket example
    with futures.ws() as ws:
        ws.subscribe_orderbook(SYMBOL, on_message=lambda m: print("[FUT OB]", m))
        ws.subscribe_order_status(on_message=lambda m: print("[FUT STATUS]", m))
        time.sleep(2.0)


if __name__ == "__main__":
    main()
