"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                Reverse Multi-User Scenario (LIFO)                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  4 users enter sequentially, then exit in REVERSE order (LIFO):           ║
║    1. All users buy tokens and add liquidity                              ║
║    2. Every 50 days, one user exits (Dennis first, Aaron last)            ║
║                                                                           ║
║  Tests whether late entrants benefit from exiting first.                  ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from ..core import MultiUserResult
from .multi_user import _multi_user_impl


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC ENTRY POINT                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def reverse_multi_user_scenario(codename: str, verbose: bool = True) -> MultiUserResult:
    """4 users, staggered exits over 200 days — REVERSE exit order."""
    return _multi_user_impl(codename, reverse=True, verbose=verbose)
