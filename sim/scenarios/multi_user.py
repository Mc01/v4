"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                     Multi-User Scenario (FIFO/LIFO)                       ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  4 users enter, compound, then exit in staggered intervals.               ║
║  Tests yield distribution and exit timing effects.                        ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, K, MultiUserResult
from ..formatter import Formatter, fmt


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# (name, buy_amount, initial_balance)
USERS_CFG: list[tuple[str, D, D]] = [
    ("Alice", D(500), 1 * K),
    ("Bob", D(500), 2 * K),
    ("Carl", D(500), 3 * K),
    ("Diana", D(500), 4 * K),
]

# Exit schedule: day of exit for each user (FIFO order)
EXIT_DAYS = [100, 130, 160, 200]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       SHARED IMPLEMENTATION                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def _multi_user_impl(codename: str, reverse: bool = False, verbosity: int = 1) -> MultiUserResult:
    """Shared implementation for FIFO and LIFO multi-user scenarios."""
    vault, lp = create_model(codename)
    f = Formatter(verbosity)
    f.set_lp(lp)
    label = "MULTI-USER (LIFO)" if reverse else "MULTI-USER (FIFO)"
    users = {name: User(name.lower(), initial) for name, _, initial in USERS_CFG}
    total_users = len(USERS_CFG)

    f.header(label, model_label(codename))

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │         Entry: All Users Buy Tokens and Provide Liquidity             │
    # └───────────────────────────────────────────────────────────────────────┘

    f.section("Entry Phase")
    
    for i, (name, buy_amount, _) in enumerate(USERS_CFG, 1):
        u = users[name]
        price_before = lp.price
        lp.buy(u, buy_amount)
        price_after = lp.price
        tokens = u.balance_token
        usdc_amount = tokens * lp.price
        lp.add_liquidity(u, tokens, usdc_amount)
        
        f.buy(i, total_users, name, buy_amount, price_before, tokens, price_after)

    f.stats("After All Entry", lp, level=1)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │       Staggered Exits: Users Leave at Different Time Points           │
    # └───────────────────────────────────────────────────────────────────────┘

    f.section("Exit Phase")
    
    exit_order = list(reversed(USERS_CFG)) if reverse else list(USERS_CFG)
    exit_days = list(reversed(EXIT_DAYS)) if reverse else EXIT_DAYS
    
    results: dict[str, D] = {}
    prev_day = 0
    
    for i, ((name, buy_amount, initial), day) in enumerate(zip(exit_order, exit_days), 1):
        days_to_add = day - prev_day
        if days_to_add > 0:
            vault_before = vault.balance_of()
            price_before = lp.price
            vault.compound(days_to_add)
            f.compound(days_to_add, vault_before, vault.balance_of(), price_before, lp.price)
        prev_day = day
        
        u = users[name]
        price_before = lp.price
        
        lp.remove_liquidity(u)
        lp.sell(u, u.balance_token)
        price_after = lp.price
        
        profit = u.balance_usd - initial
        results[name] = profit
        roi = (profit / buy_amount) * 100
        
        f.exit(i, total_users, name, profit, price_before, price_after, roi=roi)

    f.summary(results, vault.balance_of(), title=f"{label} SUMMARY")

    return {
        "codename": codename,
        "profits": results,
        "vault": vault.balance_of(),
    }


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC API                                        ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def multi_user_scenario(codename: str, verbosity: int = 1, verbose: bool = True) -> MultiUserResult:
    """FIFO exit: first buyer exits first."""
    v = verbosity if verbose else 0
    return _multi_user_impl(codename, reverse=False, verbosity=v)


def reverse_multi_user_scenario(codename: str, verbosity: int = 1, verbose: bool = True) -> MultiUserResult:
    """LIFO exit: last buyer exits first."""
    v = verbosity if verbose else 0
    return _multi_user_impl(codename, reverse=True, verbosity=v)
