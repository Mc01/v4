"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    Partial LP Scenario                                    ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Tests different LP strategies: users provide varying fractions of        ║
║  their tokens as liquidity while holding the rest.                        ║
║    - 100% LP: full liquidity provision                                    ║
║    - 50% LP: half liquidity, half hold                                    ║
║    - 0% LP: pure holder                                                   ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, K, ScenarioResult
from ..formatter import Formatter


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# (name, buy_amount, lp_fraction)
USERS_CFG: list[tuple[str, D, D]] = [
    ("Alice", D(500), D(1)),      # 100% LP
    ("Bob", D(500), D("0.75")),   # 75% LP
    ("Carl", D(500), D("0.5")),   # 50% LP
    ("Diana", D(500), D(0)),      # 0% LP (holder)
]

COMPOUND_DAYS = 100


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC API                                        ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def partial_lp_scenario(codename: str, verbosity: int = 1) -> ScenarioResult:
    """Run partial LP strategy comparison scenario."""
    vault, lp = create_model(codename)
    v = verbosity
    f = Formatter(v)
    f.set_lp(lp)
    
    users = {name: User(name.lower(), 2 * K) for name, _, _ in USERS_CFG}
    total_users = len(USERS_CFG)
    
    f.header("PARTIAL LP STRATEGIES", model_label(codename))

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │              Entry: Users Buy with Different LP Fractions             │
    # └───────────────────────────────────────────────────────────────────────┘
    
    f.section("Entry Phase")
    
    tokens_bought: dict[str, D] = {}
    lp_tokens: dict[str, D] = {}
    held_tokens: dict[str, D] = {}
    
    for i, (name, buy_amount, lp_fraction) in enumerate(USERS_CFG, 1):
        u = users[name]
        price_before = lp.price
        
        lp.buy(u, buy_amount)
        price_after = lp.price
        tokens = u.balance_token
        tokens_bought[name] = tokens
        
        lp_pct = int(lp_fraction * 100)
        f.buy(i, total_users, f"{name} ({lp_pct}% LP)", buy_amount, 
              price_before, tokens, price_after)
        
        # Calculate LP portion
        lp_token_amount = tokens * lp_fraction
        lp_tokens[name] = lp_token_amount
        held_tokens[name] = tokens - lp_token_amount
        
        if lp_token_amount > 0:
            usdc_amount = lp_token_amount * lp.price
            lp.add_liquidity(u, lp_token_amount, usdc_amount)
            f.add_lp(name, lp_token_amount, usdc_amount)
    
    f.stats("After Entry", lp, level=1)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                         Compound Period                                │
    # └───────────────────────────────────────────────────────────────────────┘
    
    vault_before = vault.balance_of()
    price_before = lp.price
    vault.compound(COMPOUND_DAYS)
    f.compound(COMPOUND_DAYS, vault_before, vault.balance_of(), price_before, lp.price)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                          Exit Phase                                    │
    # └───────────────────────────────────────────────────────────────────────┘
    
    f.section("Exit Phase")
    
    results: dict[str, D] = {}
    strategies: dict[str, D] = {}
    
    for i, (name, buy_amount, lp_fraction) in enumerate(USERS_CFG, 1):
        u = users[name]
        initial = 2 * K
        price_before = lp.price
        
        # Remove LP if any
        if lp_fraction > 0:
            lp.remove_liquidity(u)
        
        # Sell all tokens
        lp.sell(u, u.balance_token)
        price_after = lp.price
        
        profit = u.balance_usd - initial
        results[name] = profit
        strategies[name] = lp_fraction
        roi = (profit / buy_amount) * 100
        
        lp_pct = int(lp_fraction * 100)
        f.exit(i, total_users, f"{name} ({lp_pct}% LP)", profit,
               price_before, price_after, roi=roi)

    f.summary(results, vault.balance_of(), title="PARTIAL LP SUMMARY")

    return {
        "codename": codename,
        "profits": results,
        "vault": vault.balance_of(),
        "strategies": strategies,
        "losers": sum(1 for p in results.values() if p <= 0),
    }
