"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                       Test Package - __init__.py                          ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Commonwealth Protocol Test Suite                                         ║
║                                                                           ║
║  Test Categories:                                                         ║
║    - test_conservation.py:  USDC conservation at each operation           ║
║    - test_invariants.py:    Accounting invariants and consistency          ║
║    - test_scenarios.py:     End-to-end scenario tests                     ║
║    - test_curves.py:        Bonding curve correctness                     ║
║    - test_stress.py:        Stress tests and system limits                ║
║    - test_yield_accounting: Yield distribution verification               ║
║    - test_coverage_gaps.py: Edge cases and coverage gaps                  ║
║                                                                           ║
║  Run all tests: python3 -m sim.test.run_all                               ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

from ..core import ACTIVE_MODELS
MODELS = ACTIVE_MODELS
