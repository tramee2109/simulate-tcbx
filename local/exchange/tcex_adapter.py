"""
exchange/tcex_adapter.py
TCEX Spot API adapter strictly configured for BTC/VND execution.
LIMIT orders only. No short selling, no margin, no leverage.
"""

import time
import math
from typing import Any, Dict, List, Optional
from monitoring.logger import get_logger

logger = get_logger("tcex_adapter")


class TCEXAdapterError(Exception):
    """Raised for TCEX adapter specific errors."""
    pass


class TCEXSpotAdapter:
    """
    Adapter interfacing with TCEX Spot API for BTC/VND.
    Enforces venue constraints: LIMIT only, VND quote accounting, BTC base accounting.
    """

    ALLOWED_SYMBOL = "BTC_VND"
    ALLOWED_ORDER_TYPES = ["LIMIT"]

    def __init__(
        self,
        base_url: str,
        session_key: str,
        api_key: str,
        secret_key: str,
        price_scale: int = 2,
        qty_scale: int = 2,
        min_qty: float = 0.01,
        step_size: float = 0.01,
        tick_size: float = 0.01,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.session_key = session_key
        self.api_key = api_key
        self.secret_key = secret_key
        self.price_scale = price_scale
        self.qty_scale = qty_scale
        self.min_qty = min_qty
        self.step_size = step_size
        self.tick_size = tick_size
        self.timeout = timeout

        # Load client via package-aware loader to avoid relative import issues
        self.client = self._create_client()

    def _create_client(self):
        import importlib.util
        import os
        import sys

        if "the20_simulate_sdk" in sys.modules:
            sdk = sys.modules["the20_simulate_sdk"]
            return sdk.SpotClient(
                base_url=self.base_url,
                api_key=self.api_key,
                api_secret=self.secret_key,
                session_key=self.session_key,
                timeout=self.timeout,
            )

        cur = os.path.dirname(os.path.abspath(__file__))
        sdk_dir = None
        while cur and cur != os.path.dirname(cur):
            if os.path.isfile(os.path.join(cur, "spot.py")) and os.path.isfile(os.path.join(cur, "client.py")):
                sdk_dir = cur
                break
            cur = os.path.dirname(cur)
        if not sdk_dir:
            sdk_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        spec = importlib.util.spec_from_file_location(
            "the20_simulate_sdk",
            os.path.join(sdk_dir, "__init__.py"),
            submodule_search_locations=[sdk_dir],
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules["the20_simulate_sdk"] = mod
            spec.loader.exec_module(mod)
            return mod.SpotClient(
                base_url=self.base_url,
                api_key=self.api_key,
                api_secret=self.secret_key,
                session_key=self.session_key,
                timeout=self.timeout,
            )
        raise ImportError(f"Cannot initialize SpotClient from {sdk_dir}")

    def round_price(self, price: float) -> float:
        """Round price according to tick size and price scale."""
        factor = 10 ** self.price_scale
        return math.floor(price * factor + 0.5) / factor

    def round_quantity(self, quantity: float) -> float:
        """Round quantity down according to step size and qty scale."""
        factor = 10 ** self.qty_scale
        return math.floor(quantity * factor) / factor

    def validate_order_params(self, symbol: str, side: str, order_type: str, quantity: float, price: float) -> Dict[str, Any]:
        """Strict validation of order parameters before sending to exchange."""
        if symbol != self.ALLOWED_SYMBOL:
            raise TCEXAdapterError(f"Forbidden symbol: {symbol}. Only {self.ALLOWED_SYMBOL} is allowed.")

        side_upper = side.upper()
        if side_upper not in ("BUY", "SELL"):
            raise TCEXAdapterError(f"Invalid side: {side}. Must be BUY or SELL.")

        type_upper = order_type.upper()
        if type_upper not in self.ALLOWED_ORDER_TYPES:
            raise TCEXAdapterError(f"Rejected order type: {order_type}. Strict LIMIT-only venue enforcement.")

        if price is None or price <= 0:
            raise TCEXAdapterError(f"LIMIT order requires positive price, got: {price}")

        valid_qty = self.round_quantity(quantity)
        if valid_qty < self.min_qty:
            raise TCEXAdapterError(
                f"Quantity {valid_qty} is below minimum allowed lot size ({self.min_qty} BTC)"
            )

        valid_price = self.round_price(price)
        return {
            "symbol": self.ALLOWED_SYMBOL,
            "side": side_upper,
            "type": "LIMIT",
            "quantity": valid_qty,
            "price": valid_price,
            "notional_vnd": valid_qty * valid_price,
        }

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        client_order_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit validated LIMIT order to TCEX."""
        params = self.validate_order_params(symbol, side, "LIMIT", quantity, price)

        logger.info(
            f"Submitting LIMIT {params['side']} order: {params['quantity']} BTC @ {params['price']:,.2f} VND "
            f"(Notional: {params['notional_vnd']:,.2f} VND, ClientOID: {client_order_id})"
        )

        try:
            res = self.client.place_order(
                symbol=params["symbol"],
                side=params["side"],
                order_type="LIMIT",
                quantity=params["quantity"],
                price=params["price"],
                client_order_id=client_order_id,
                strategy_name=strategy_name,
                session_key=self.session_key,
            )
            return res
        except Exception as e:
            logger.error(f"TCEX order submission failed: {e}")
            raise TCEXAdapterError(f"Order submission failed: {e}") from e

    def cancel_order(self, symbol: str, order_id: Optional[str] = None, client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """Cancel an open order."""
        valid_symbols = (self.ALLOWED_SYMBOL, "BTC_VND_binance")
        if symbol not in valid_symbols:
            raise TCEXAdapterError(f"Cannot cancel order on forbidden symbol: {symbol}")
        try:
            # TCEX session maps BTC_VND to BTC_VND_binance internally
            target_symbol = "BTC_VND_binance" if "binance" in symbol else symbol
            try:
                return self.client.cancel_order(
                    symbol=target_symbol,
                    order_id=order_id,
                    client_order_id=client_order_id,
                    session_key=self.session_key,
                )
            except Exception:
                # Fallback to alternate symbol representation
                alt_symbol = self.ALLOWED_SYMBOL if target_symbol == "BTC_VND_binance" else "BTC_VND_binance"
                return self.client.cancel_order(
                    symbol=alt_symbol,
                    order_id=order_id,
                    client_order_id=client_order_id,
                    session_key=self.session_key,
                )
        except Exception as e:
            logger.error(f"TCEX cancel order failed: {e}")
            raise TCEXAdapterError(f"Cancel order failed: {e}") from e

    def get_open_orders(self) -> List[Dict[str, Any]]:
        """Retrieve all open orders for this account in this session."""
        try:
            # Query session open orders (allowing both BTC_VND and BTC_VND_binance)
            res = self.client.get_open_orders(symbol=None, session_key=self.session_key)
            orders: List[Dict[str, Any]] = []
            if isinstance(res, list):
                orders = res
            elif isinstance(res, dict):
                orders = res.get("data") or res.get("orders") or []

            # Filter for BTC/VND venue orders
            return [
                o for o in orders
                if str(o.get("symbol", "")).startswith("BTC_VND")
            ]
        except Exception as e:
            logger.error(f"Failed to fetch open orders: {e}")
            raise TCEXAdapterError(f"Fetch open orders failed: {e}") from e

    def get_balances(self) -> Dict[str, float]:
        """
        Fetch actual account balances.
        Returns dict with keys 'VND', 'BTC' (and any other assets).
        """
        try:
            res = self.client.get_balance(session_key=self.session_key)
            data = res.get("data", {}) if isinstance(res, dict) else {}
            balances: Dict[str, float] = {}

            for asset, val in data.items():
                if asset == "Total":
                    continue
                if isinstance(val, dict):
                    balances[asset] = float(val.get("amount", 0.0))
                elif isinstance(val, (int, float, str)):
                    balances[asset] = float(val)

            # Ensure baseline keys
            balances.setdefault("VND", 0.0)
            balances.setdefault("BTC", 0.0)
            return balances
        except Exception as e:
            logger.error(f"Failed to fetch balances: {e}")
            raise TCEXAdapterError(f"Fetch balances failed: {e}") from e

    def verify_connection(self) -> bool:
        """Verify API authentication and session access."""
        try:
            balances = self.get_balances()
            return True
        except Exception as e:
            logger.warning(f"Connection verification failed: {e}")
            return False
