"""
engine/account_manager.py
Manages 20 TCEX accounts, authentication, credentials validation, and balance reconciliation.
"""

import csv
import os
import re
from typing import Any, Dict, List, Optional
from exchange.tcex_adapter import TCEXSpotAdapter
from monitoring.logger import get_logger, mask_sensitive_text

logger = get_logger("account_manager")


class AccountManager:
    """Manages the 20 provisioned TCEX accounts (ACC-01 .. ACC-20)."""

    def __init__(
        self,
        csv_path: str,
        base_url: str,
        session_key: str,
    ):
        self.csv_path = csv_path
        self.base_url = base_url
        self.session_key = session_key
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self.adapters: Dict[str, TCEXSpotAdapter] = {}

    def load_accounts(self) -> Dict[str, Dict[str, Any]]:
        """Load and map existing 20 accounts from the CSV source of truth."""
        if not os.path.isfile(self.csv_path):
            raise FileNotFoundError(f"Account CSV file not found: {self.csv_path}")

        loaded: Dict[str, Dict[str, Any]] = {}

        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                acc_id = f"ACC-{idx:02d}"
                username = row.get("username", "").strip()
                nickname = row.get("nickname", "").strip()
                label = row.get("label", "").strip()
                group_name = row.get("group_name", "").strip()
                scope = row.get("scope", "").strip()
                api_key = row.get("api_key", "").strip()
                secret_key = row.get("secret_key", "").strip()

                # Basic credential format validation
                key_valid = bool(re.match(r"^mm_[a-f0-9]{32}$", api_key))
                secret_valid = bool(re.match(r"^[a-f0-9]{64}$", secret_key))

                loaded[acc_id] = {
                    "account_id": acc_id,
                    "username": username,
                    "nickname": nickname,
                    "label": label,
                    "group_name": group_name,
                    "scope": scope,
                    "api_key": api_key,
                    "secret_key": secret_key,
                    "credential_valid": key_valid and secret_valid,
                    "initial_capital_vnd": 150_000_000.0,
                    "deployable_budget_vnd": 90_000_000.0,
                    "reserve_vnd": 60_000_000.0,
                    "actual_vnd": 0.0,
                    "actual_btc": 0.0,
                    "connection_status": "UNTESTED",
                    "verification_status": "ACCOUNT_UNVERIFIED",
                    "reconciliation_status": "PENDING",
                }

                if not (key_valid and secret_valid):
                    logger.warning(
                        f"Account [{acc_id}] has invalid credential format (masked API key: {mask_sensitive_text(api_key)})"
                    )

        self.accounts = loaded
        logger.info(f"Loaded and mapped {len(self.accounts)} accounts from CSV.")
        return self.accounts

    def verify_all_accounts(self) -> Dict[str, Dict[str, Any]]:
        """Verify authentication, retrieve balances, and reconcile proposed budget."""
        logger.info("Beginning read-only verification for all 20 accounts...")

        for acc_id, acc in self.accounts.items():
            if not acc["credential_valid"]:
                acc["connection_status"] = "INVALID_CREDENTIALS"
                acc["verification_status"] = "ACCOUNT_UNVERIFIED"
                acc["reconciliation_status"] = "FAILED"
                continue

            try:
                adapter = TCEXSpotAdapter(
                    base_url=self.base_url,
                    session_key=self.session_key,
                    api_key=acc["api_key"],
                    secret_key=acc["secret_key"],
                )
                balances = adapter.get_balances()
                acc["actual_vnd"] = balances.get("VND", 0.0)
                acc["actual_btc"] = balances.get("BTC", 0.0)
                acc["connection_status"] = "CONNECTED"

                # Balance reconciliation: consider both cash VND and held BTC
                btc_price_est = 1_500_000_000.0
                total_equity = acc["actual_vnd"] + (acc["actual_btc"] * btc_price_est)
                if acc["actual_vnd"] >= acc["initial_capital_vnd"] or total_equity >= acc["initial_capital_vnd"]:
                    acc["reconciliation_status"] = "MATCHED_OR_EXCEEDED"
                    acc["verification_status"] = "VERIFIED"
                elif acc["actual_vnd"] >= acc["deployable_budget_vnd"] or total_equity >= acc["deployable_budget_vnd"]:
                    acc["reconciliation_status"] = "SUFFICIENT_FOR_DEPLOYMENT"
                    acc["verification_status"] = "VERIFIED"
                elif total_equity > 0:
                    acc["reconciliation_status"] = "ACTIVE_WITH_PORTFOLIO"
                    acc["verification_status"] = "VERIFIED"
                else:
                    acc["reconciliation_status"] = "INSUFFICIENT_FUNDS"
                    acc["verification_status"] = "ACCOUNT_UNVERIFIED"

                self.adapters[acc_id] = adapter
                logger.info(
                    f"Verified {acc_id} ({acc['nickname']}): VND={acc['actual_vnd']:,.2f}, "
                    f"BTC={acc['actual_btc']:.4f} -> {acc['verification_status']}"
                )

            except Exception as e:
                acc["connection_status"] = f"ERROR: {str(e)[:50]}"
                acc["verification_status"] = "ACCOUNT_UNVERIFIED"
                acc["reconciliation_status"] = "ERROR"
                logger.error(f"Verification failed for account [{acc_id}]: {e}")

        return self.accounts

    def get_adapter(self, account_id: str) -> Optional[TCEXSpotAdapter]:
        if account_id not in self.adapters and account_id in self.accounts:
            acc = self.accounts[account_id]
            if acc.get("credential_valid", True):
                self.adapters[account_id] = TCEXSpotAdapter(
                    base_url=self.base_url,
                    session_key=self.session_key,
                    api_key=acc["api_key"],
                    secret_key=acc["secret_key"],
                )
        return self.adapters.get(account_id)

    def get_account_status_summary(self) -> List[Dict[str, Any]]:
        """Return clean account status list without secrets for reporting."""
        summary = []
        for acc_id, acc in sorted(self.accounts.items()):
            summary.append({
                "account_id": acc["account_id"],
                "nickname": acc["nickname"],
                "label": acc["label"],
                "username": acc["username"],
                "scope": acc["scope"],
                "actual_vnd": acc["actual_vnd"],
                "actual_btc": acc["actual_btc"],
                "connection_status": acc["connection_status"],
                "verification_status": acc["verification_status"],
                "reconciliation_status": acc["reconciliation_status"],
            })
        return summary
