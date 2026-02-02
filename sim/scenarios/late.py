"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                      Late Entrant Scenario                                ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Tests first-mover advantage: early users enter, compound, then late      ║
║  entrant joins at a higher price.                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, K, ScenarioResult
from ..formatter import Formatter, fmt


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

EARLY_USERS: list[tuple[str, D]] = [
    ("Alice", D(500)),
    ("Bob", D(500)),
    ("Carl", D(500)),
]

LATE_USER = ("Diana", D(500))
COMPOUND_AFTER_LATE = 100


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       SHARED IMPLEMENTATION                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def _late_impl(codename: str, wait_days: int, verbosity: int = 1) -> ScenarioResult:
    """Run late entrant scenario with specified wait period."""
    vault, lp = create_model(codename)
    f = Formatter(verbosity)
    f.set_lp(lp)
    
    late_name, late_buy = LATE_USER
    users = {name: User(name.lower(), 2 * K) for name, _ in EARLY_USERS}
    users[late_name] = User(late_name.lower(), 2 * K)
    
    total_users = len(EARLY_USERS) + 1
    entry_prices: dict[str, D] = {}
    
    f.header(f"LATE ENTRANT ({wait_days}d)", model_label(codename))

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                    Early Users Enter                                   │
    # └───────────────────────────────────────────────────────────────────────┘
    
    f.section("Early Entry Phase")
    
    for i, (name, buy_amount) in enumerate(EARLY_USERS, 1):
        u = users[name]
        entry_prices[name] = lp.price
        price_before = lp.price
        
        lp.buy(u, buy_amount)
        price_after = lp.price
        tokens = u.balance_token
        usdc = tokens * lp.price
        lp.add_liquidity(u, tokens, usdc)
        
        f.buy(i, total_users, name, buy_amount, price_before, tokens, price_after)
    
    f.stats("After Early Entry", lp, level=1)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                Wait Period Before Late Entry                           │
    # └───────────────────────────────────────────────────────────────────────┘
    
    vault_before = vault.balance_of()
    price_before = lp.price
    vault.compound(wait_days)
    f.compound(wait_days, vault_before, vault.balance_of(), price_before, lp.price)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                    Late User Enters                                    │
    # └───────────────────────────────────────────────────────────────────────┘
    
    f.section("Late Entry")
    
    u = users[late_name]
    entry_prices[late_name] = lp.price
    price_before = lp.price
    
    lp.buy(u, late_buy)
    price_after = lp.price
    tokens = u.balance_token
    usdc = tokens * lp.price
    lp.add_liquidity(u, tokens, usdc)
    
    # Calculate price increase vs first early user
    alice_entry = entry_prices["Alice"]
    if alice_entry > 0:
        price_increase = ((entry_prices[late_name] / alice_entry) - 1) * 100
        increase_str = f"+{price_increase:.1f}% vs early"
    else:
        increase_str = "early price was 0"

    f.buy(total_users, total_users, late_name, late_buy, price_before, tokens, price_after, emoji="⏰")
    f.info(f"  Late entry price: {fmt(entry_prices[late_name], 4)} ({increase_str})")
    f.stats("After Late Entry", lp, level=1)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │               Compound After Late Entry                                │
    # └───────────────────────────────────────────────────────────────────────┘
    
    vault_before = vault.balance_of()
    price_before = lp.price
    vault.compound(COMPOUND_AFTER_LATE)
    f.compound(COMPOUND_AFTER_LATE, vault_before, vault.balance_of(), price_before, lp.price)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                       Exit Phase                                       │
    # └───────────────────────────────────────────────────────────────────────┘
    
    f.section("Exit Phase")
    
    results: dict[str, D] = {}
    all_users = list(EARLY_USERS) + [LATE_USER]
    
    for i, (name, buy_amount) in enumerate(all_users, 1):
        u = users[name]
        initial = 2 * K
        price_before = lp.price
        
        lp.remove_liquidity(u)
        lp.sell(u, u.balance_token)
        price_after = lp.price
        
        profit = u.balance_usd - initial
        results[name] = profit
        roi = (profit / buy_amount) * 100
        
        is_late = name == late_name
        f.exit(i, total_users, name, profit, price_before, price_after, 
               emoji="⏰" if is_late else "", roi=roi)

    f.summary(results, vault.balance_of(), title=f"LATE ENTRANT ({wait_days}d) SUMMARY")

    return {
        "codename": codename,
        "profits": results,
        "vault": vault.balance_of(),
        "entry_prices": entry_prices,
        "losers": sum(1 for p in results.values() if p <= 0),
    }


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC API                                        ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def late_90_scenario(codename: str, verbosity: int = 1, verbose: bool = True) -> ScenarioResult:
    """Late entrant after 90 days of compounding."""
    v = verbosity if verbose else 0
    return _late_impl(codename, 90, v)


def late_180_scenario(codename: str, verbosity: int = 1, verbose: bool = True) -> ScenarioResult:
    """Late entrant after 180 days of compounding."""
    v = verbosity if verbose else 0
    return _late_impl(codename, 180, v)
