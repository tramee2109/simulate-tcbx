"""Spot trading REST client for The20 Simulation API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .client import BaseClient


class SpotClient(BaseClient):
    """High-level Spot client for market data, orders, and account queries."""

    API_PREFIX = "/api/v1/simulation"

    def ws(self, session_key: Optional[str] = None, auto_reconnect: bool = True):
        """Return a `The20WSClient` configured for Spot using this client's token."""
        from .ws import The20WSClient

        if not self.token:
            self.login()
        return The20WSClient(
            base_url=self.base_url,
            token=self.token or "",
            session_key=session_key or self.session_key,
            market="spot",
            user_id=self.user_id,
            auto_reconnect=auto_reconnect,
        )

    # ── Market Data ──────────────────────────────────────────────────────────

    def get_ticker_info(self, symbol: str, session_key: Optional[str] = None) -> Dict[str, Any]:
        """Get symbol precision (`priceScale`, `qtyScale`, `tickSize`, `stepSize`)."""
        return self.request(
            "GET",
            f"{self.API_PREFIX}/ticker/info",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key)},
        )

    def get_exchange_info(self, session_key: Optional[str] = None) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/exchangeInfo",
            params={"session_key": session_key or self.session_key or None},
        )

    def get_orderbook(self, symbol: str, session_key: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/depth",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key), "limit": limit},
        )

    def get_klines(
        self,
        symbol: str,
        interval: str = "1m",
        session_key: Optional[str] = None,
        limit: int = 100,
    ) -> Any:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "session_key": self._require_session_key(session_key),
                "limit": limit,
            },
        )

    def get_ticker_24hr(self, symbol: str, session_key: Optional[str] = None) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/ticker/24hr",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key)},
        )

    def get_ticker_price(self, symbol: str, session_key: Optional[str] = None) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/ticker/price",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key)},
        )

    # ── Trading ──────────────────────────────────────────────────────────────

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        quote_order_qty: Optional[float] = None,
        session_key: Optional[str] = None,
        time_in_force: str = "GTC",
        client_order_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "session_key": self._require_session_key(session_key),
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
        }
        if order_type.upper() == "LIMIT" and time_in_force:
            body["timeInForce"] = time_in_force
        if quantity is not None:
            body["quantity"] = float(quantity)
        if quote_order_qty is not None:
            body["quoteOrderQty"] = float(quote_order_qty)
        if price is not None:
            body["price"] = float(price)
        if client_order_id:
            body["newClientOrderId"] = client_order_id
        if strategy_name:
            body["strategyName"] = strategy_name
        if take_profit is not None:
            body["takeProfit"] = float(take_profit)
        if stop_loss is not None:
            body["stopLoss"] = float(stop_loss)
        if extra is not None:
            body["extra"] = extra

        return self.request("POST", f"{self.API_PREFIX}/order", json_body=body)

    def limit_buy(self, symbol: str, quantity: float, price: float, **kwargs: Any) -> Dict[str, Any]:
        return self.place_order(symbol, "BUY", "LIMIT", quantity=quantity, price=price, **kwargs)

    def limit_sell(self, symbol: str, quantity: float, price: float, **kwargs: Any) -> Dict[str, Any]:
        return self.place_order(symbol, "SELL", "LIMIT", quantity=quantity, price=price, **kwargs)

    def market_buy(self, symbol: str, quantity: float, **kwargs: Any) -> Dict[str, Any]:
        return self.place_order(symbol, "BUY", "MARKET", quantity=quantity, **kwargs)

    def market_sell(self, symbol: str, quantity: float, **kwargs: Any) -> Dict[str, Any]:
        return self.place_order(symbol, "SELL", "MARKET", quantity=quantity, **kwargs)

    def cancel_order(
        self,
        symbol: str,
        order_id: Optional[int | str] = None,
        client_order_id: Optional[str] = None,
        session_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "symbol": symbol,
            "session_key": self._require_session_key(session_key),
        }
        if order_id is not None:
            params["orderId"] = str(order_id)
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        return self.request("DELETE", f"{self.API_PREFIX}/order", params=params)

    def cancel_all_orders(self, symbol: Optional[str] = None, session_key: Optional[str] = None) -> Any:
        return self.request(
            "DELETE",
            f"{self.API_PREFIX}/openOrders",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key)},
        )

    def get_order(
        self,
        symbol: str,
        order_id: Optional[int | str] = None,
        client_order_id: Optional[str] = None,
        session_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "symbol": symbol,
            "session_key": self._require_session_key(session_key),
        }
        if order_id is not None:
            params["orderId"] = str(order_id)
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        return self.request("GET", f"{self.API_PREFIX}/order", params=params)

    def get_open_orders(
        self,
        symbol: Optional[str] = None,
        session_key: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/openOrders",
            params={
                "symbol": symbol,
                "session_key": self._require_session_key(session_key),
                "page": page,
                "pageSize": page_size,
            },
        )

    def get_order_history(
        self,
        symbol: Optional[str] = None,
        session_key: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/order-history",
            params={
                "symbol": symbol,
                "session_key": self._require_session_key(session_key),
                "page": page,
                "pageSize": page_size,
            },
        )

    def get_trade_history(
        self,
        symbol: Optional[str] = None,
        session_key: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/trade-history",
            params={
                "symbol": symbol,
                "session_key": self._require_session_key(session_key),
                "page": page,
                "pageSize": page_size,
            },
        )

    # ── Account ──────────────────────────────────────────────────────────────

    def get_portfolio(self, session_key: Optional[str] = None) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/account/portfolio",
            params={"session_key": self._require_session_key(session_key)},
        )

    def get_balance(self, session_key: Optional[str] = None) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/account/balance",
            params={"session_key": self._require_session_key(session_key)},
        )
