"""
engine/execution_engine.py
Execution engine supporting PAPER and LIVE execution modes.
In PAPER mode, matches orders against live TCEX BTC/VND orderbook depth.
In LIVE mode, routes real LIMIT orders to TCEXSpotAdapter (strictly gated by confirmation).
"""

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from storage.models import OrderRecord, FillRecord
from monitoring.logger import get_logger, log_order_event

logger = get_logger("execution_engine")


class ExecutionEngine:
    """Execution engine orchestrator with dual PAPER / LIVE capability."""

    def __init__(
        self,
        mode: str = "PAPER",  # PAPER or LIVE
        account_manager: Any = None,
        capital_manager: Any = None,
        portfolio_manager: Any = None,
        risk_manager: Any = None,
        database_manager: Any = None,
        maker_fee_bps: float = 10.0,  # 0.10%
        taker_fee_bps: float = 10.0,  # 0.10%
    ):
        self.mode = mode.upper()
        self.account_manager = account_manager
        self.capital_manager = capital_manager
        self.portfolio_manager = portfolio_manager
        self.risk_manager = risk_manager
        self.database_manager = database_manager
        self.maker_fee_bps = maker_fee_bps
        self.taker_fee_bps = taker_fee_bps

        # In-memory tracking of open orders: client_order_id -> OrderRecord
        self.open_orders: Dict[str, OrderRecord] = {}

    def submit_limit_order(
        self,
        account_id: str,
        strategy_id: str,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        market_data_age_sec: float = 0.0,
        current_market_depth: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str], str]:
        """
        Validate, create, and submit a LIMIT order.
        Returns (success, client_order_id, message).
        """
        side_upper = side.upper()

        # 1. Validate through RiskManager
        passed, reason = self.risk_manager.validate_order(
            account_id=account_id,
            strategy_id=strategy_id,
            symbol=symbol,
            side=side_upper,
            order_type="LIMIT",
            price=price,
            quantity=quantity,
            market_data_age_sec=market_data_age_sec,
        )

        if not passed:
            logger.warning(f"Order rejected by RiskManager: {reason}")
            log_order_event("REJECTED", account_id, strategy_id, side_upper, price, quantity, "N/A", "REJECTED", f"Reason={reason}")
            return False, None, reason

        client_order_id = f"TCEX_{strategy_id}_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
        order_id = client_order_id  # default in PAPER

        order = OrderRecord(
            order_id=order_id,
            client_order_id=client_order_id,
            account_id=account_id,
            strategy_id=strategy_id,
            symbol=symbol,
            side=side_upper,
            order_type="LIMIT",
            price=price,
            quantity=quantity,
            filled_quantity=0.0,
            status="NEW",
            mode=self.mode,
            created_at=time.time(),
            updated_at=time.time(),
        )

        self.open_orders[client_order_id] = order
        if self.database_manager:
            self.database_manager.insert_order(order)

        logger.info(
            f"[{self.mode}] Placed LIMIT {side_upper} order {client_order_id} "
            f"for {strategy_id}@{account_id}: {quantity:.4f} BTC @ {price:,.2f} VND"
        )
        log_order_event("SUBMITTED", account_id, strategy_id, side_upper, price, quantity, client_order_id, "NEW", f"Mode={self.mode}")

        # 2. Execution Routing
        if self.mode == "LIVE":
            # LIVE execution via TCEXSpotAdapter
            adapter = self.account_manager.get_adapter(account_id)
            if not adapter:
                order.status = "REJECTED"
                order.notes = "No active adapter for account"
                self.risk_manager.order_closed(account_id, strategy_id)
                return False, client_order_id, "No active adapter for account"

            try:
                res = adapter.place_limit_order(
                    symbol=symbol,
                    side=side_upper,
                    quantity=quantity,
                    price=price,
                    client_order_id=client_order_id,
                    strategy_name=strategy_id,
                )
                order.order_id = str(res.get("orderId") or client_order_id)
                return True, client_order_id, "SUBMITTED_LIVE"
            except Exception as e:
                order.status = "REJECTED"
                order.notes = str(e)
                self.risk_manager.order_closed(account_id, strategy_id)
                log_order_event("FAILED", account_id, strategy_id, side_upper, price, quantity, client_order_id, "REJECTED", f"Error={e}")
                return False, client_order_id, f"LIVE submission failed: {e}"

        else:
            # PAPER execution simulation: evaluate immediate fill against orderbook depth
            if current_market_depth:
                self.process_paper_matching(current_market_depth)
            return True, client_order_id, "SUBMITTED_PAPER"

    def process_paper_matching(self, market_depth: Dict[str, Any]):
        """
        Simulate order matching against live TCEX BTC/VND orderbook.
        BUY matches if limit price >= best ask.
        SELL matches if limit price <= best bid.
        """
        bids = market_depth.get("bids", [])
        asks = market_depth.get("asks", [])

        best_bid = bids[0]["price"] if bids else None
        best_ask = asks[0]["price"] if asks else None

        active_order_ids = list(self.open_orders.keys())
        for cl_oid in active_order_ids:
            order = self.open_orders.get(cl_oid)
            if not order or order.status not in ("NEW", "PARTIALLY_FILLED"):
                continue

            fill_price = None
            if order.side == "BUY" and best_ask and order.price >= best_ask:
                fill_price = best_ask
            elif order.side == "SELL" and best_bid and order.price <= best_bid:
                fill_price = best_bid

            if fill_price:
                # Execute full fill
                fill_qty = order.quantity - order.filled_quantity
                cost_vnd = fill_price * fill_qty
                fee_vnd = cost_vnd * (self.taker_fee_bps / 10_000.0)

                order.filled_quantity = order.quantity
                order.status = "FILLED"
                order.updated_at = time.time()

                fill_id = f"FILL_{uuid.uuid4().hex[:10]}"
                fill = FillRecord(
                    fill_id=fill_id,
                    order_id=order.order_id,
                    account_id=order.account_id,
                    strategy_id=order.strategy_id,
                    symbol=order.symbol,
                    side=order.side,
                    price=fill_price,
                    quantity=fill_qty,
                    fee_vnd=fee_vnd,
                    pnl_vnd=0.0,
                    timestamp=time.time(),
                )

                if self.database_manager:
                    self.database_manager.insert_order(order)
                    self.database_manager.insert_fill(fill)

                # Update portfolio balances
                if self.portfolio_manager:
                    self.portfolio_manager.record_fill(
                        account_id=order.account_id,
                        strategy_id=order.strategy_id,
                        side=order.side,
                        price=fill_price,
                        quantity=fill_qty,
                        fee_vnd=fee_vnd,
                    )

                # Clean open order tracking
                self.open_orders.pop(cl_oid, None)
                if self.risk_manager:
                    self.risk_manager.order_closed(order.account_id, order.strategy_id)

                logger.info(
                    f"[PAPER_FILL] Order {cl_oid} FILLED: {fill_qty:.4f} BTC @ {fill_price:,.2f} VND "
                    f"(Fee: {fee_vnd:,.2f} VND) for {order.strategy_id}@{order.account_id}"
                )
                log_order_event(
                    "FILLED",
                    order.account_id,
                    order.strategy_id,
                    order.side,
                    fill_price,
                    fill_qty,
                    cl_oid,
                    "FILLED",
                    f"Mode=PAPER | Fee={fee_vnd:,.2f} VND",
                )

    def cancel_order(self, client_order_id: str) -> bool:
        """Cancel an open order."""
        order = self.open_orders.get(client_order_id)
        if not order or order.status not in ("NEW", "PARTIALLY_FILLED"):
            return False

        if self.mode == "LIVE":
            adapter = self.account_manager.get_adapter(order.account_id)
            if adapter:
                try:
                    adapter.cancel_order(symbol=order.symbol, client_order_id=client_order_id)
                except Exception as e:
                    logger.error(f"LIVE cancel order failed: {e}")
                    return False

        order.status = "CANCELED"
        order.updated_at = time.time()
        self.open_orders.pop(client_order_id, None)

        if self.database_manager:
            self.database_manager.insert_order(order)
        if self.risk_manager:
            self.risk_manager.order_closed(order.account_id, order.strategy_id)

        logger.info(f"Canceled order {client_order_id} for [{order.strategy_id}@{order.account_id}]")
        log_order_event(
            "CANCELED",
            order.account_id,
            order.strategy_id,
            order.side,
            order.price,
            order.quantity,
            client_order_id,
            "CANCELED",
        )
        return True
