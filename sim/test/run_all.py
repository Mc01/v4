#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║             Commonwealth Protocol - Run All Tests                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Usage: python3 -m sim.test.run_all                (summary only)        ║
║         python3 -m sim.test.run_all -vv            (show failures)       ║
║         python3 -m sim.test.run_all -vvv           (show all tests)      ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
import sys

from . import helpers
from .helpers import TestResults, run_for_all_models, section_header
from . import test_conservation
from . import test_invariants
from . import test_scenarios
from . import test_curves
from . import test_stress
from . import test_yield_accounting
from . import test_coverage_gaps


def main():
    # Parse -v flags: -vv = failures only, -vvv = all tests
    v_count = 0
    for arg in sys.argv[1:]:
        if arg.startswith("-v"):
            v_count += len(arg) - 1  # -vv = 2, -vvv = 3
    # Map: -vv (2) → verbosity 1 (failures), -vvv (3+) → verbosity 2 (all)
    helpers.VERBOSITY = max(0, v_count - 1)

    results = TestResults()
    
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║       Commonwealth Protocol - Complete Test Suite                     ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    
    section_header("CONSERVATION TESTS")
    for name, test_fn in test_conservation.ALL_TESTS:
        run_for_all_models(results, test_fn, name)
    
    section_header("INVARIANT TESTS")
    for name, test_fn in test_invariants.ALL_TESTS:
        run_for_all_models(results, test_fn, name)
    
    section_header("SCENARIO TESTS")
    for name, test_fn in test_scenarios.ALL_TESTS:
        run_for_all_models(results, test_fn, name)
    
    section_header("CURVE TESTS")
    for name, test_fn in test_curves.ALL_TESTS:
        run_for_all_models(results, test_fn, name)

    section_header("STRESS TESTS")
    for name, test_fn in test_stress.ALL_TESTS:
        run_for_all_models(results, test_fn, name)

    section_header("YIELD ACCOUNTING TESTS")
    for name, test_fn in test_yield_accounting.ALL_TESTS:
        run_for_all_models(results, test_fn, name)

    section_header("COVERAGE GAP TESTS")
    for name, test_fn in test_coverage_gaps.ALL_TESTS:
        run_for_all_models(results, test_fn, name)
    
    success = results.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
