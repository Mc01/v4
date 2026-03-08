"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                     Test Helpers - Shared Utilities                       ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from typing import Callable

from ..core import ACTIVE_MODELS

MODELS = ACTIVE_MODELS

# Verbosity levels (controlled by -v flags on run_all.py)
#   0 = summary only (default)
#   1 = show failed tests only (-vv)
#   2 = show all tests (-vvv)
VERBOSITY = 0


class TestResults:
    """Track test results"""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.failures: list[tuple[str, str, str]] = []
    
    def record_pass(self, model: str, test_name: str):
        self.total += 1
        self.passed += 1
    
    def record_fail(self, model: str, test_name: str, error: str):
        self.total += 1
        self.failed += 1
        self.failures.append((model, test_name, error))
    
    def print_summary(self):
        print(f"\n{'═' * 60}")
        print(f"  RESULTS: {self.passed} passed, {self.failed} failed (total: {self.total})")
        print(f"{'═' * 60}")
        
        if self.failures:
            print("\n❌ FAILURES:")
            for model, test_name, error in self.failures:
                print(f"\n  {model} - {test_name}:")
                print(f"    {error}")
            return False
        else:
            print("\n✅ All tests passed!")
            return True


def run_test(results: TestResults, test_fn: Callable, model: str):
    """Run a single test and record result."""
    try:
        test_fn(model)
        results.record_pass(model, test_fn.__name__)
        if VERBOSITY >= 2:
            print(f"  ✓ {model}")
        return True
    except AssertionError as e:
        results.record_fail(model, test_fn.__name__, str(e))
        if VERBOSITY >= 1:
            print(f"  ✗ {model}: {e}")
        return False
    except Exception as e:
        results.record_fail(model, test_fn.__name__, f"Error: {e}")
        if VERBOSITY >= 1:
            print(f"  ✗ {model}: Error - {e}")
        return False


def run_for_all_models(results: TestResults, test_fn: Callable, test_name: str):
    """Run a test for all models."""
    if VERBOSITY >= 1:
        print(f"\n[TEST] {test_name}")
        print("-" * 50)
    for model in MODELS:
        run_test(results, test_fn, model)


def section_header(title: str):
    """Print a section header."""
    if VERBOSITY >= 1:
        print(f"\n{'═' * 60}")
        print(f"  {title}")
        print(f"{'═' * 60}")
