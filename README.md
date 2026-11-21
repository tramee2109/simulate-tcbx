# The20 Exchange Python SDK (`the20_exchange`)

Lightweight REST + WebSocket SDK for **Spot** and **Futures** trading on the The20 Simulation API (no local Redis required).

## Requirements

```bash
pip install requests websocket-client
```

## Quick Start (Spot REST + WebSocket)

```python
import time
from the20_exchange import SpotClient

client = SpotClient(
    base_url="http://localhost:8083",  # or https://simulation.the20.sg
    username="client",
    password="your_password",
    session_key="dbukjqfiralc73cbcme0",
)

# 1. Market data & precision
info = client.get_ticker_info("BTC_USDT_binance")
book = client.get_orderbook("BTC_USDT_binance", limit=10)
portfolio = client.get_portfolio()

# 2. Place & cancel orders
order = client.limit_buy("BTC_USDT_binance", quantity=0.01, price=60000.0)
print("Placed:", order)

open_orders = client.get_open_orders("BTC_USDT_binance")
history = client.get_order_history(page=1, page_size=20)
trades = client.get_trade_history(page=1, page_size=20)

# 3. Real-time WebSocket streams
with client.ws() as ws:
    ws.subscribe_orderbook("BTC_USDT_binance", on_message=lambda msg: print("OB:", msg))
    ws.subscribe_trades("BTC_USDT_binance", on_message=lambda msg: print("TRADE:", msg))
    ws.subscribe_order_status(on_message=lambda msg: print("ORDER:", msg))
    time.sleep(5)
```

## Quick Start (Futures REST + WebSocket)

```python
import time
from the20_exchange import FuturesClient

futures = FuturesClient(
    base_url="http://localhost:8083",
    username="client",
    password="your_password",
    session_key="your_futures_session_key",
)

futures.set_leverage("BTCUSDT", leverage=10)
order = futures.market_buy("BTCUSDT", quantity=0.01)
positions = futures.get_positions("BTCUSDT")

with futures.ws() as ws:
    ws.subscribe_orderbook("BTCUSDT", on_message=lambda msg: print("FUT OB:", msg))
    ws.subscribe_order_status(on_message=lambda msg: print("FUT ORDER:", msg))
    time.sleep(5)
```
