"""
tests/test_accounts.py
Tests account loading, CSV mapping, credential format validation, and balance verification.
"""

import os
import unittest
from engine.account_manager import AccountManager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestAccounts(unittest.TestCase):

    def setUp(self):
        csv_path = os.path.join(BASE_DIR, "new-temp-accounts-global (1).csv")
        self.mgr = AccountManager(
            csv_path=csv_path,
            base_url="https://simulation.the20.sg",
            session_key="dc1tpbu76rkff8gccfug",
        )

    def test_load_20_accounts(self):
        accounts = self.mgr.load_accounts()
        self.assertEqual(len(accounts), 20)

        # Verify ACC-01
        acc1 = accounts["ACC-01"]
        self.assertEqual(acc1["nickname"], "Mu #1")
        self.assertEqual(acc1["label"], "mu_acc #1")
        self.assertEqual(acc1["username"], "tmp_dc34ha676rk5eukbqbvg")
        self.assertTrue(acc1["credential_valid"])

        # Verify ACC-20
        acc20 = accounts["ACC-20"]
        self.assertEqual(acc20["nickname"], "Mu #20")
        self.assertEqual(acc20["label"], "mu_acc #20")
        self.assertEqual(acc20["username"], "tmp_dc34ham76rk5eukbqc90")
        self.assertTrue(acc20["credential_valid"])

    def test_read_only_verification(self):
        self.mgr.load_accounts()
        verified = self.mgr.verify_all_accounts()
        self.assertEqual(len(verified), 20)
        for aid, acc in verified.items():
            self.assertEqual(acc["connection_status"], "CONNECTED", f"{aid} must connect successfully")
            self.assertEqual(acc["verification_status"], "VERIFIED", f"{aid} must be VERIFIED")
            self.assertTrue(acc["actual_vnd"] > 0 or acc["actual_btc"] > 0, f"{aid} must have positive assets")


if __name__ == "__main__":
    unittest.main()
