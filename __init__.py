from .client import BaseClient, The20APIError
from .spot import SpotClient
from .futures import FuturesClient
from .ws import The20WSClient, WSStream

__all__ = [
    "BaseClient",
    "The20APIError",
    "SpotClient",
    "FuturesClient",
    "The20WSClient",
    "WSStream",
]

# Legacy wrappers kept optional so users without local Redis/`utils` can still import the SDK.
try:
    from .the20_private import The20Private
    from .the20_futures_private import The20FuturesPrivate

    __all__.extend(["The20Private", "The20FuturesPrivate"])
except Exception:
    pass
