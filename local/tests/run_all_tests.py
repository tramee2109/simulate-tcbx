"""
tests/run_all_tests.py
Master automated test runner executing all unit and integration test suites.
"""

import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def run_all_tests() -> bool:
    """Discover and execute all test suites."""
    print("=" * 70)
    print("TCEX BTC/VND STRATEGY ENGINE — AUTOMATED TEST SUITE")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=os.path.join(BASE_DIR, "tests"), pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 70)
    print(f"Total Tests Run : {result.testsRun}")
    print(f"Failures        : {len(result.failures)}")
    print(f"Errors          : {len(result.errors)}")
    print(f"Overall Result  : {'PASSED (ALL TESTS GREEN)' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
