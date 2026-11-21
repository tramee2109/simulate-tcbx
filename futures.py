"""Futures trading REST client for The20 Simulation API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .client import BaseClient


class FuturesClient(BaseClient):
    """High-level Futures client for market data, orders, positions, and margin."""

    API_PREFIX = "/fapi/v1/simulation/future"

    def ws(self, session_key: Optional[str] = None, auto_reconnect: bool = True):
        """Return a `The20WSClient` configured for Futures using this client's token."""
        from .ws import The20WSClient

        if not self.token:
            self.login()
        return The20WSClient(
            base_url=self.base_url,
            token=self.token or "",
            session_key=session_key or self.session_key,
            market="future",
            user_id=self.user_id,
            auto_reconnect=auto_reconnect,
        )

    # ── Market Data ──────────────────────────────────────────────────────────

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

    def get_recent_trades(self, symbol: str, session_key: Optional[str] = None, limit: int = 50) -> Any:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/recent-trades",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key), "limit": limit},
        )

    def get_funding_rate(self, symbol: Optional[str] = None, session_key: Optional[str] = None) -> Any:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/fundingRate",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key)},
        )

    def get_premium_index(self, symbol: Optional[str] = None, session_key: Optional[str] = None) -> Any:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/premiumIndex",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key)},
        )

    # ── Trading ──────────────────────────────────────────────────────────────

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        position_side: str = "BOTH",
        leverage: Optional[int] = None,
        session_key: Optional[str] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        client_order_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "session_key": self._require_session_key(session_key),
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "positionSide": position_side.upper(),
            "quantity": float(quantity),
        }
        if order_type.upper() == "LIMIT" and time_in_force:
            body["timeInForce"] = time_in_force
        if price is not None:
            body["price"] = float(price)
        if leverage is not None:
            body["leverage"] = int(leverage)
        if reduce_only:
            body["reduceOnly"] = True
        if take_profit is not None:
            body["takeProfit"] = float(take_profit)
        if stop_loss is not None:
            body["stopLoss"] = float(stop_loss)
        if client_order_id:
            body["newClientOrderId"] = client_order_id
        if strategy_name:
            body["strategyName"] = strategy_name
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
            f"{self.API_PREFIX}/allOpenOrders",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key)},
        )

    def get_open_orders(self, symbol: Optional[str] = None, session_key: Optional[str] = None) -> Any:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/openOrders",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key)},
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

    def get_user_trades(self, symbol: Optional[str] = None, session_key: Optional[str] = None, limit: int = 50) -> Any:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/userTrades",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key), "limit": limit},
        )

    # ── Positions & Margin ───────────────────────────────────────────────────

    def get_positions(self, symbol: Optional[str] = None, session_key: Optional[str] = None) -> Any:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/positionRisk",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key)},
        )

    def set_leverage(self, symbol: str, leverage: int, session_key: Optional[str] = None) -> Any:
        return self.request(
            "POST",
            f"{self.API_PREFIX}/leverage",
            json_body={
                "symbol": symbol,
                "leverage": int(leverage),
                "session_key": self._require_session_key(session_key),
            },
        )

    def set_margin_type(self, symbol: str, margin_type: str, session_key: Optional[str] = None) -> Any:
        return self.request(
            "POST",
            f"{self.API_PREFIX}/marginType",
            json_body={
                "symbol": symbol,
                "marginType": margin_type.upper(),
                "session_key": self._require_session_key(session_key),
            },
        )

    def get_balance(self, session_key: Optional[str] = None) -> Any:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/balance",
            params={"session_key": self._require_session_key(session_key)},
        )

    def get_commission_rate(self, symbol: Optional[str] = None, session_key: Optional[str] = None) -> Any:
        return self.request(
            "GET",
            f"{self.API_PREFIX}/commissionRate",
            params={"symbol": symbol, "session_key": self._require_session_key(session_key)},
        )
