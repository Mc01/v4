"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                 Reverse Bank Run Scenario (LIFO)                          ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  10 users enter, compound for 365 days, then all exit in REVERSE (LIFO):  ║
║    1. All users buy tokens and add liquidity                              ║
║    2. Compound for 365 days                                               ║
║    3. All users exit in reverse order (Jack first, Aaron last)            ║
║                                                                           ║
║  Tests whether protocol is fairer when late entrants exit first.          ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from ..core import BankRunResult
from .bank_run import _bank_run_impl


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC ENTRY POINT                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def reverse_bank_run_scenario(codename: str, verbose: bool = True) -> BankRunResult:
    """10 users, 365 days compound, all exit sequentially — REVERSE order."""
    return _bank_run_impl(codename, reverse=True, verbose=verbose)
