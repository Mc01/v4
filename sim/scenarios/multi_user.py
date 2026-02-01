"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                   Multi-User Scenario (FIFO)                              ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  4 users enter sequentially, then exit in the same order (FIFO):          ║
║    1. All users buy tokens and add liquidity                              ║
║    2. Every 50 days, one user exits (Aaron first, Dennis last)            ║
║                                                                           ║
║  Tests fairness across multiple participants with staggered exits.        ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, Color, MultiUserResult


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# (name, buy_amount, initial_usdc)
USERS_CFG: list[tuple[str, D, D]] = [
    ("Aaron", D(500), D(2000)),
    ("Bob", D(400), D(2000)),
    ("Carl", D(300), D(2000)),
    ("Dennis", D(600), D(2000)),
]

COMPOUND_INTERVAL = 50


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       SHARED IMPLEMENTATION                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def _multi_user_impl(codename: str, reverse: bool = False, verbose: bool = True) -> MultiUserResult:
    """Shared implementation for FIFO and LIFO multi-user scenarios."""
    vault, lp = create_model(codename)
    C = Color
    label = "REVERSE MULTI-USER" if reverse else "MULTI-USER"
    width = 40 if reverse else 48
    users = {name: User(name.lower(), initial) for name, _, initial in USERS_CFG}

    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  {label} - {model_label(codename):^{width}}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │       Entry: Everyone Buys Tokens and Provides Liquidity              │
    # └───────────────────────────────────────────────────────────────────────┘

    for name, buy_amount, _ in USERS_CFG:
        u = users[name]
        lp.buy(u, buy_amount)
        if verbose:
            print(f"[{name} Buy] {buy_amount} USDC -> {C.YELLOW}{u.balance_token:.2f}{C.END} tokens, Price: {C.GREEN}{lp.price:.6f}{C.END}")

        token_amount = u.balance_token
        usdc_amount = token_amount * lp.price
        lp.add_liquidity(u, token_amount, usdc_amount)
        if verbose:
            print(f"[{name} LP] {token_amount:.2f} tokens + {usdc_amount:.2f} USDC")

    if verbose:
        lp.print_stats("After All Buy + LP")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │      Staggered Exits: One User Leaves Every 50 Days (FIFO/LIFO)       │
    # └───────────────────────────────────────────────────────────────────────┘

    exit_order = list(reversed(USERS_CFG)) if reverse else list(USERS_CFG)
    results: dict[str, D] = {}
    for i, (name, buy_amount, initial) in enumerate(exit_order):
        vault.compound(COMPOUND_INTERVAL)
        day = (i + 1) * COMPOUND_INTERVAL
        u = users[name]

        if verbose:
            print(f"\n{C.CYAN}=== {name} Exit (day {day}) ==={C.END}")

        usdc_before = u.balance_usd
        lp.remove_liquidity(u)
        usdc_from_lp = u.balance_usd - usdc_before

        tokens = u.balance_token
        usdc_before_sell = u.balance_usd
        lp.sell(u, tokens)
        usdc_from_sell = u.balance_usd - usdc_before_sell

        profit = u.balance_usd - initial
        results[name] = profit

        if verbose:
            gc = C.GREEN if profit > 0 else C.RED
            print(f"  LP USDC: {C.YELLOW}{usdc_from_lp:.2f}{C.END}, Sell: {C.YELLOW}{usdc_from_sell:.2f}{C.END}")
            print(f"  Final: {C.YELLOW}{u.balance_usd:.2f}{C.END}, Profit: {gc}{profit:.2f}{C.END}")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │       Summary: Always Printed in Entry Order for Comparability        │
    # └───────────────────────────────────────────────────────────────────────┘

    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}=== FINAL SUMMARY ==={C.END}")
        total: D = D(0)
        for name, buy_amount, initial in USERS_CFG:
            p: D = results[name]
            total += p
            pc = C.GREEN if p > 0 else C.RED
            print(f"  {name:7s}: Invested {C.YELLOW}{buy_amount}{C.END}, Profit: {pc}{p:.2f}{C.END}")
        tc = C.GREEN if total > 0 else C.RED
        print(f"\n  {C.BOLD}Total profit: {tc}{total:.2f}{C.END}")
        print(f"  Vault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")

    return {"codename": codename, "profits": results, "vault": vault.balance_of()}


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC ENTRY POINT                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def multi_user_scenario(codename: str, verbose: bool = True) -> MultiUserResult:
    """4 users, staggered exits over 200 days."""
    return _multi_user_impl(codename, reverse=False, verbose=verbose)
