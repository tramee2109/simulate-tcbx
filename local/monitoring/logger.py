"""
monitoring/logger.py
Structured logging system with credential masking, audit trails, and dedicated order logs.
Ensures logs are cleanly routed to local/logs/ for transparent monitoring and control.
"""

import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional

# Anchor default log directory to simulate-sdk/local/logs
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOG_DIR = os.path.join(BASE_DIR, "logs")

# Regex patterns to detect and mask credentials
SENSITIVE_PATTERNS = [
    (re.compile(r"(mm_[a-f0-9]{32})", re.IGNORECASE), r"mm_****[MASKED]"),
    (re.compile(r"([a-f0-9]{64})", re.IGNORECASE), r"****[SECRET_MASKED]"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_.+/=]*", re.IGNORECASE), r"\1****[JWT_MASKED]"),
    (re.compile(r"('api_key':\s*')[^']+(\')", re.IGNORECASE), r"\1****[MASKED]\2"),
    (re.compile(r"('secret_key':\s*')[^']+(\')", re.IGNORECASE), r"\1****[MASKED]\2"),
    (re.compile(r'("api_key":\s*")[^"]+(")', re.IGNORECASE), r'\1****[MASKED]\2'),
    (re.compile(r'("secret_key":\s*")[^"]+(")', re.IGNORECASE), r'\1****[MASKED]\2'),
]


def mask_sensitive_text(text: str) -> str:
    """Mask credentials and secrets in log messages."""
    masked = str(text)
    for pattern, replacement in SENSITIVE_PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked


class SensitiveDataFilter(logging.Filter):
    """Filter to ensure no sensitive credentials appear in log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_sensitive_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: mask_sensitive_text(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(mask_sensitive_text(str(a)) for a in record.args)
        return True


# Dedicated module loggers
_order_logger: Optional[logging.Logger] = None
_audit_logger: Optional[logging.Logger] = None
_initialized_dir: Optional[str] = None


def setup_logger(
    name: str = "tcex_engine",
    log_dir: Optional[str] = None,
    log_level: int = logging.INFO,
    console: bool = True,
    max_bytes: int = 20 * 1024 * 1024,  # 20MB
    backup_count: int = 10,
) -> logging.Logger:
    """
    Initialize and configure structured engine logger with multi-sink output:
    1. Console (stdout)
    2. Master log: logs/tcex_engine.log
    3. Orders log: logs/orders.log
    4. Audit log: logs/audit_events.log
    """
    global _order_logger, _audit_logger, _initialized_dir

    if not log_dir:
        resolved_log_dir = DEFAULT_LOG_DIR
    elif not os.path.isabs(log_dir):
        resolved_log_dir = os.path.join(BASE_DIR, log_dir)
    else:
        resolved_log_dir = log_dir

    os.makedirs(resolved_log_dir, exist_ok=True)
    _initialized_dir = resolved_log_dir

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Avoid duplicate handlers on re-initialization
    if logger.handlers:
        return logger

    mask_filter = SensitiveDataFilter()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(module)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(mask_filter)
        logger.addHandler(console_handler)

    # 2. Master file handler (tcex_engine.log)
    master_log_file = os.path.join(resolved_log_dir, f"{name}.log")
    file_handler = RotatingFileHandler(
        master_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(mask_filter)
    logger.addHandler(file_handler)

    # 3. Dedicated Orders file handler (orders.log)
    orders_log_file = os.path.join(resolved_log_dir, "orders.log")
    order_formatter = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    order_handler = RotatingFileHandler(
        orders_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    order_handler.setLevel(logging.INFO)
    order_handler.setFormatter(order_formatter)
    order_handler.addFilter(mask_filter)

    _order_logger = logging.getLogger("tcex_engine.orders")
    _order_logger.setLevel(logging.INFO)
    _order_logger.handlers = []  # reset if any
    _order_logger.addHandler(order_handler)
    _order_logger.propagate = False

    # 4. Dedicated Audit file handler (audit_events.log)
    audit_log_file = os.path.join(resolved_log_dir, "audit_events.log")
    audit_handler = RotatingFileHandler(
        audit_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(formatter)
    audit_handler.addFilter(mask_filter)

    _audit_logger = logging.getLogger("tcex_engine.audit")
    _audit_logger.setLevel(logging.INFO)
    _audit_logger.handlers = []  # reset if any
    _audit_logger.addHandler(audit_handler)
    _audit_logger.propagate = False

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Retrieve logger instance."""
    base_name = "tcex_engine"
    if name:
        return logging.getLogger(f"{base_name}.{name}")
    return logging.getLogger(base_name)


def get_order_logger() -> logging.Logger:
    """Retrieve dedicated order events logger."""
    global _order_logger
    if _order_logger is None:
        setup_logger()
    return _order_logger or logging.getLogger("tcex_engine.orders")


def get_audit_logger() -> logging.Logger:
    """Retrieve dedicated audit events logger."""
    global _audit_logger
    if _audit_logger is None:
        setup_logger()
    return _audit_logger or logging.getLogger("tcex_engine.audit")


def get_log_dir() -> str:
    """Return the current active log directory."""
    global _initialized_dir
    return _initialized_dir or DEFAULT_LOG_DIR


def log_order_event(
    event_type: str,
    account_id: str,
    strategy_id: str,
    side: str,
    price: float,
    quantity: float,
    order_id: str,
    status: str,
    details: str = "",
):
    """
    Log a structured order event to logs/orders.log.
    Example:
    [ORDER_SUBMITTED] [ACC-01] [STR-001] SIDE=BUY | QTY=0.0100 BTC | PRICE=1,520,000.00 VND | ID=TCEX_... | STATUS=NEW | Details=Mode=PAPER
    """
    order_log = get_order_logger()
    notional = price * quantity
    msg = (
        f"[{event_type.upper()}] [{account_id}] [{strategy_id}] "
        f"SIDE={side.upper():<4} | QTY={quantity:>.4f} BTC | PRICE={price:>14,.2f} VND | "
        f"NOTIONAL={notional:>16,.2f} VND | ID={order_id} | STATUS={status}"
    )
    if details:
        msg += f" | {details}"
    order_log.info(msg)


def log_audit_event(
    event_type: str,
    account_id: str,
    strategy_id: str,
    reason: str,
    details: str = "",
):
    """
    Log a structured risk/audit event to logs/audit_events.log.
    Example:
    [RISK_REJECTED] [ACC-01] [STR-001] Reason=Order type MARKET forbidden | Details=Price=0
    """
    audit_log = get_audit_logger()
    msg = f"[{event_type.upper()}] [{account_id}] [{strategy_id}] Reason={reason}"
    if details:
        msg += f" | Details={details}"
    audit_log.warning(msg)
