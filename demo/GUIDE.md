# The20 Simulation SDK — Demo & API Guide

## 1. Credentials & Connection Format

| Field | Description | Example |
| :--- | :--- | :--- |
| `base_url` | Simulation API base URL (`http://` → `ws://`, `https://` → `wss://`) | `"http://localhost:8083"` or `"https://simulation.the20.sg"` |
| `username` | Trader username | `"client"` |
| `password` | Trader password | `"client123"` |
| `token` | Optional JWT access token (if omitted, SDK calls `/api/v1/auth/login/trader` automatically) | `"eyJhbGci..."` |
| `session_key` | Simulation room/session key (from `get_sessions()` or UI sidebar) | `"dbukjqfiralc73cbcme0"` |

### Symbol Format
- **Spot REST**: `BASE_QUOTE_exchange` (e.g. `"BTC_USDT_binance"`)
- **Spot WebSocket**: Pass `"BTC_USDT_binance"` — the SDK automatically splits it into `symbol=BTC_USDT&exchange=binance` (or pass `exchange="binance"` explicitly).
- **Futures REST & WebSocket**: `"BTCUSDT"` or `"BTC_USDT_binance"` depending on session config.

### Precision Rules (`tickSize` / `stepSize`)
Before placing Spot orders, check `client.get_ticker_info(symbol)`:
```json
{
  "symbol": "BTC_USDT",
  "price_scale": 4,
  "qty_scale": 2,
  "tick_size": "0.0001",
  "step_size": "0.01"
}
```
Orders with more decimal places than `price_scale` or `qty_scale` are rejected with HTTP `400` (`The20APIError`).

---

## 2. REST API Reference

### Spot (`SpotClient`)
- `client.get_sessions()` → `GET /api/v1/simulation/sessions`
- `client.get_ticker_info(symbol)` → `GET /api/v1/simulation/ticker/info`
- `client.get_orderbook(symbol, limit=20)` → `GET /api/v1/simulation/depth`
- `client.get_klines(symbol, interval="1m", limit=100)` → `GET /api/v1/simulation/klines`
- `client.get_ticker_24hr(symbol)` → `GET /api/v1/simulation/ticker/24hr`
- `client.get_portfolio()` → `GET /api/v1/simulation/account/portfolio`
- `client.limit_buy(symbol, quantity, price)` / `client.limit_sell(...)` → `POST /api/v1/simulation/order`
- `client.market_buy(symbol, quantity)` / `client.market_sell(...)` → `POST /api/v1/simulation/order`
- `client.cancel_order(symbol, order_id=...)` → `DELETE /api/v1/simulation/order`
- `client.get_open_orders(symbol=None)` → `GET /api/v1/simulation/openOrders`
- `client.get_order_history(page=1, page_size=20)` → `GET /api/v1/simulation/order-history`
- `client.get_trade_history(page=1, page_size=20)` → `GET /api/v1/simulation/trade-history`

### Futures (`FuturesClient`)
- `futures.set_leverage(symbol, leverage=10)` → `POST /fapi/v1/simulation/future/leverage`
- `futures.set_margin_type(symbol, "ISOLATED" | "CROSSED")` → `POST /fapi/v1/simulation/future/marginType`
- `futures.limit_buy(...)` / `futures.market_buy(...)` → `POST /fapi/v1/simulation/future/order`
- `futures.get_positions(symbol=None)` → `GET /fapi/v1/simulation/future/positionRisk`
- `futures.get_balance()` → `GET /fapi/v1/simulation/future/balance`
- `futures.get_commission_rate(symbol=None)` → `GET /fapi/v1/simulation/future/commissionRate`

---

## 3. WebSocket Streams (`client.ws()`)

All WebSocket URLs are authenticated with `?token=<jwt>` automatically.

| Method | Spot Endpoint | Futures Endpoint |
| :--- | :--- | :--- |
| `ws.subscribe_orderbook(symbol, on_message)` | `/api/v1/simulation/ws/trader/orderbook` | `/api/v1/simulation/ws/trader/futures/orderbook` |
| `ws.subscribe_candles(symbol, interval, on_message)` | `/api/v1/simulation/ws/trader/candles` | `/api/v1/simulation/ws/trader/futures/candles` |
| `ws.subscribe_ticker(symbol, on_message)` | `/api/v1/simulation/ws/trader/ticker/24hr` | `/api/v1/simulation/ws/trader/futures/ticker/24hr` |
| `ws.subscribe_trades(symbol, on_message)` | `/api/v1/simulation/ws/trades` | `/api/v1/simulation/ws/futures/trades` |
| `ws.subscribe_order_status(on_message)` | `/api/v1/simulation/ws/trader/order-status` | `/api/v1/simulation/ws/trader/order-status-futures` |

### Sample Order Status Payload (`ws.subscribe_order_status`)
```json
{
  "type": "update",
  "status": "success",
  "request": "order-history",
  "total": 23,
  "page": 1,
  "data": [
    {
      "orderId": "1795169392018269720",
      "symbol": "BTC_USDT_binance",
      "type": "MARKET",
      "side": "SELL",
      "price": "0",
      "filledPrice": "64517.78",
      "origQty": "1",
      "executedQty": "1",
      "fee": "12.903556",
      "status": "FILLED"
    }
  ]
}
```

---

## 4. Running the Demos

```bash
export THE20_BASE_URL="http://localhost:8083"
export THE20_USERNAME="client"
export THE20_PASSWORD="client123"
export THE20_SESSION_KEY="dbukjqfiralc73cbcme0"

python demo/spot_rest_demo.py
python demo/spot_ws_demo.py
python demo/futures_demo.py
```
