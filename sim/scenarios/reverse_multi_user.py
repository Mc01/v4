"""
Reverse Multi-User Scenario (LIFO)

4 users enter sequentially, then exit in REVERSE order (LIFO):
1. All users buy tokens and add liquidity
2. Every 50 days, one user exits (Dennis first, Aaron last)

Tests whether late entrants benefit from exiting first.
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, Color, K


def reverse_multi_user_scenario(codename: str, verbose: bool = True) -> dict:
    """4 users, staggered exits over 200 days — REVERSE exit order (last buyer exits first)."""
    vault, lp = create_model(codename)
    C = Color

    users_cfg = [
        ("Aaron", D(500), D(2000)),
        ("Bob", D(400), D(2000)),
        ("Carl", D(300), D(2000)),
        ("Dennis", D(600), D(2000)),
    ]
    users = {name: User(name.lower(), initial) for name, _, initial in users_cfg}
    compound_interval = 50

    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  REVERSE MULTI-USER - {model_label(codename):^40}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")

    # All buy + add LP (same order)
    for name, buy_amt, _ in users_cfg:
        u = users[name]
        lp.buy(u, buy_amt)
        if verbose:
            print(f"[{name} Buy] {buy_amt} USDC -> {C.YELLOW}{u.balance_token:.2f}{C.END} tokens, Price: {C.GREEN}{lp.price:.6f}{C.END}")

        lp_tok = u.balance_token
        lp_usd = lp_tok * lp.price
        lp.add_liquidity(u, lp_tok, lp_usd)
        if verbose:
            print(f"[{name} LP] {lp_tok:.2f} tokens + {lp_usd:.2f} USDC")

    if verbose:
        lp.print_stats("After All Buy + LP")

    # Staggered exits: REVERSE order (Dennis first, Aaron last)
    results = {}
    reversed_cfg = list(reversed(users_cfg))
    for i, (name, buy_amt, initial) in enumerate(reversed_cfg):
        vault.compound(compound_interval)
        day = (i + 1) * compound_interval
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

    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}=== FINAL SUMMARY ==={C.END}")
        total = D(0)
        for name, buy_amt, initial in users_cfg:
            p = results[name]
            total += p
            pc = C.GREEN if p > 0 else C.RED
            print(f"  {name:7s}: Invested {C.YELLOW}{buy_amt}{C.END}, Profit: {pc}{p:.2f}{C.END}")
        tc = C.GREEN if total > 0 else C.RED
        print(f"\n  {C.BOLD}Total profit: {tc}{total:.2f}{C.END}")
        print(f"  Vault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")

    return {"codename": codename, "profits": results, "vault": vault.balance_of()}
