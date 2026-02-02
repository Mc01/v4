"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                     Hold Scenario (Passive Holder)                        ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Tests passive holder behavior relative to LP providers.                  ║
║  Three variants:                                                          ║
║    - BEFORE: Passive holder buys before LPers enter                       ║
║    - WITH:   Passive holder buys at same time as LPers                    ║
║    - AFTER:  Passive holder buys after LPers have entered                 ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from typing import Literal
from ..core import create_model, model_label, User, K, ScenarioResult
from ..formatter import Formatter, fmt


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

LP_USERS: list[tuple[str, D]] = [
    ("Bob", D(500)),
    ("Carl", D(500)),
    ("Diana", D(500)),
]

PASSIVE_USER = ("Alice", D(500))  # Holds tokens, no LP
COMPOUND_DAYS = 100

HoldVariant = Literal["before", "with", "after"]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       SHARED IMPLEMENTATION                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def _hold_impl(codename: str, variant: HoldVariant, verbosity: int = 1) -> ScenarioResult:
    """Shared implementation for all hold variants."""
    vault, lp = create_model(codename)
    f = Formatter(verbosity)
    f.set_lp(lp)
    label = f"HOLD - {variant.upper()}"
    
    passive_name, passive_buy = PASSIVE_USER
    passive = User(passive_name.lower(), 2 * K)
    lpers = {name: User(name.lower(), 2 * K) for name, _ in LP_USERS}
    
    total_users = len(LP_USERS) + 1
    
    f.header(label, model_label(codename))

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                          Entry Phase                                   │
    # └───────────────────────────────────────────────────────────────────────┘
    
    f.section("Entry Phase")
    
    entry_num = 0
    
    if variant == "before":
        # Passive holder enters first (no LP)
        entry_num += 1
        price_before = lp.price
        lp.buy(passive, passive_buy)
        price_after = lp.price
        f.buy(entry_num, total_users, f"{passive_name} (NO LP)", passive_buy, 
              price_before, passive.balance_token, price_after)
    
    # LPers enter
    for name, buy_amount in LP_USERS:
        entry_num += 1
        u = lpers[name]
        price_before = lp.price
        lp.buy(u, buy_amount)
        price_after = lp.price
        tokens = u.balance_token
        usdc = tokens * lp.price
        lp.add_liquidity(u, tokens, usdc)
        f.buy(entry_num, total_users, name, buy_amount, price_before, tokens, price_after)
    
    if variant == "with":
        # Passive holder enters with LPers (no LP)
        entry_num += 1
        price_before = lp.price
        lp.buy(passive, passive_buy)
        price_after = lp.price
        f.buy(entry_num, total_users, f"{passive_name} (NO LP)", passive_buy,
              price_before, passive.balance_token, price_after)
    
    if variant == "after":
        # Passive holder enters after LPers (no LP)
        entry_num += 1
        price_before = lp.price
        lp.buy(passive, passive_buy)
        price_after = lp.price
        f.buy(entry_num, total_users, f"{passive_name} (NO LP)", passive_buy,
              price_before, passive.balance_token, price_after)
    
    f.stats("After Entry", lp, level=1)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                         Compound Period                                │
    # └───────────────────────────────────────────────────────────────────────┘
    
    vault_before = vault.balance_of()
    price_before_compound = lp.price
    vault.compound(COMPOUND_DAYS)
    f.compound(COMPOUND_DAYS, vault_before, vault.balance_of(), price_before_compound, lp.price)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                          Exit Phase                                    │
    # └───────────────────────────────────────────────────────────────────────┘
    
    f.section("Exit Phase")
    
    results: dict[str, D] = {}
    exit_num = 0
    
    # LPers exit
    for name, buy_amount in LP_USERS:
        exit_num += 1
        u = lpers[name]
        initial = 2 * K
        price_before = lp.price
        
        lp.remove_liquidity(u)
        lp.sell(u, u.balance_token)
        price_after = lp.price
        
        profit = u.balance_usd - initial
        results[name] = profit
        roi = (profit / buy_amount) * 100
        f.exit(exit_num, total_users, name, profit, price_before, price_after, roi=roi)
    
    # Passive holder exits (sell only, no LP to remove)
    exit_num += 1
    initial = 2 * K
    price_before = lp.price
    lp.sell(passive, passive.balance_token)
    price_after = lp.price
    
    profit = passive.balance_usd - initial
    results[passive_name] = profit
    roi = (profit / passive_buy) * 100
    f.exit(exit_num, total_users, f"{passive_name} (NO LP)", profit, 
           price_before, price_after, roi=roi)

    f.summary(results, vault.balance_of(), title=f"{label} SUMMARY")

    return {
        "codename": codename,
        "profits": results,
        "vault": vault.balance_of(),
        "losers": sum(1 for p in results.values() if p <= 0),
    }


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC API                                        ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def hold_scenario(codename: str, variant: HoldVariant, verbosity: int = 1) -> ScenarioResult:
    """Run hold scenario with specified variant."""
    return _hold_impl(codename, variant, verbosity)


def hold_before_scenario(codename: str, verbosity: int = 1, verbose: bool = True) -> ScenarioResult:
    """Passive holder buys BEFORE LPers."""
    v = verbosity if verbose else 0
    return _hold_impl(codename, "before", v)


def hold_with_scenario(codename: str, verbosity: int = 1, verbose: bool = True) -> ScenarioResult:
    """Passive holder buys WITH LPers."""
    v = verbosity if verbose else 0
    return _hold_impl(codename, "with", v)


def hold_after_scenario(codename: str, verbosity: int = 1, verbose: bool = True) -> ScenarioResult:
    """Passive holder buys AFTER LPers."""
    v = verbosity if verbose else 0
    return _hold_impl(codename, "after", v)
