"""
monitoring/health.py
Heartbeat, error isolation, watchdog and subsystem status reporting.
"""

import time
from typing import Any, Callable, Dict, List, Optional
from monitoring.logger import get_logger

logger = get_logger("health")


class HealthMonitor:
    """Manages subsystem heartbeats, failure isolation, and health checks."""

    def __init__(self):
        self._heartbeats: Dict[str, float] = {}
        self._subsystem_status: Dict[str, str] = {}
        self._error_counts: Dict[str, int] = {}
        self._last_error: Dict[str, str] = {}
        self._is_running = True

    def beat(self, subsystem: str):
        self._heartbeats[subsystem] = time.time()
        self._subsystem_status[subsystem] = "HEALTHY"

    def report_error(self, subsystem: str, error_msg: str):
        self._error_counts[subsystem] = self._error_counts.get(subsystem, 0) + 1
        self._last_error[subsystem] = error_msg
        self._subsystem_status[subsystem] = "DEGRADED"
        logger.warning(f"Subsystem [{subsystem}] reported error: {error_msg}")

    def safe_execute(self, target_name: str, fn: Callable, *args, **kwargs) -> Any:
        """Execute a function while guaranteeing error containment (never crash parent loop)."""
        try:
            res = fn(*args, **kwargs)
            self.beat(target_name)
            return res
        except Exception as e:
            self.report_error(target_name, str(e))
            logger.error(f"Error isolated in [{target_name}]: {e}", exc_info=True)
            return None

    def get_health_report(self, timeout_sec: float = 60.0) -> Dict[str, Any]:
        now = time.time()
        subsystems = {}
        for sub, last_beat in self._heartbeats.items():
            age = now - last_beat
            status = "STALE" if age > timeout_sec else self._subsystem_status.get(sub, "UNKNOWN")
            subsystems[sub] = {
                "status": status,
                "seconds_since_heartbeat": round(age, 1),
                "error_count": self._error_counts.get(sub, 0),
                "last_error": self._last_error.get(sub, ""),
            }
        return {
            "timestamp": now,
            "overall_status": "OK" if all(s["status"] == "HEALTHY" for s in subsystems.values()) else "ATTENTION_REQUIRED",
            "subsystems": subsystems,
        }
