#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║             Commonwealth Protocol - Run All Tests                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Usage: python3 -m sim.test.run_all (from project root)                  ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
import sys

from .helpers import TestResults, run_for_all_models, section_header
from . import test_conservation
from . import test_invariants
from . import test_scenarios
from . import test_curves
from . import test_stress
from . import test_yield_accounting


def main():
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
    
    success = results.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

