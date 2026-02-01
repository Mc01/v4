"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                  Partial Liquidity Provision Scenario                     ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Tests heterogeneous LP strategies.                                       ║
║                                                                           ║
║  Users buy the same amount but LP different fractions of their tokens:    ║
║    - Alice: 100% LP                                                       ║
║    - Bob: 50% LP, 50% hold                                                ║
║    - Carl: 25% LP, 75% hold                                               ║
║    - Diana: 0% LP (pure hold)                                             ║
║                                                                           ║
║  Key insight: Yield rewards are divided proportionally to provided        ║
║  liquidity. All USDC yield is considered common among LP participants.    ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, Color, ScenarioResult


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# (name, buy_amount, lp_fraction)
USERS_CFG: list[tuple[str, D, D]] = [
    ("Alice", D(500), D("1.0")),    # 100% LP
    ("Bob", D(500), D("0.5")),      # 50% LP
    ("Carl", D(500), D("0.25")),    # 25% LP
    ("Diana", D(500), D("0.0")),    # 0% LP (pure hold)
]

COMPOUND_DAYS = 100
INITIAL_USDC = D(2000)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       CORE IMPLEMENTATION                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def partial_lp_scenario(codename: str, verbose: bool = True) -> ScenarioResult:
    """Run partial LP scenario comparing different LP strategies."""
    vault, lp = create_model(codename)
    C = Color
    
    users = {name: User(name.lower(), INITIAL_USDC) for name, _, _ in USERS_CFG}
    strategies: dict[str, D] = {}
    
    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  PARTIAL LP - {model_label(codename):^50}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                    Entry: Buy + Partial LP                            │
    # └───────────────────────────────────────────────────────────────────────┘
    
    for name, buy_amount, lp_fraction in USERS_CFG:
        u = users[name]
        strategies[name] = lp_fraction
        
        # Buy tokens
        lp.buy(u, buy_amount)
        tokens_bought = u.balance_token
        
        # LP only the specified fraction
        lp_tokens = tokens_bought * lp_fraction
        held_tokens = tokens_bought - lp_tokens
        
        if lp_tokens > 0:
            usdc_for_lp = lp_tokens * lp.price
            lp.add_liquidity(u, lp_tokens, usdc_for_lp)
        
        if verbose:
            lp_pct = int(lp_fraction * 100)
            print(f"[{name}] Buy {buy_amount} -> {tokens_bought:.2f} tokens, LP {lp_pct}% ({lp_tokens:.2f}), Hold {held_tokens:.2f}")
    
    if verbose:
        lp.print_stats("After Entry")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                         Compound Period                               │
    # └───────────────────────────────────────────────────────────────────────┘
    
    vault.compound(COMPOUND_DAYS)
    if verbose:
        print(f"{C.BLUE}--- Compound {COMPOUND_DAYS} days ---{C.END}")
        print(f"  Vault: {C.YELLOW}{vault.balance_of():.2f}{C.END}, Price: {C.GREEN}{lp.price:.6f}{C.END}")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                              Exit                                     │
    # └───────────────────────────────────────────────────────────────────────┘
    
    results: dict[str, D] = {}
    
    for name, buy_amount, lp_fraction in USERS_CFG:
        u = users[name]
        
        # Remove LP if user has LP position
        if lp_fraction > 0 and name in lp.liquidity_token:
            lp.remove_liquidity(u)
        
        # Sell all held tokens
        tokens = u.balance_token
        if tokens > 0:
            lp.sell(u, tokens)
        
        profit = u.balance_usd - INITIAL_USDC
        results[name] = profit
        
        roi = (profit / buy_amount) * 100
        lp_pct = int(lp_fraction * 100)
        if verbose:
            pc = C.GREEN if profit > 0 else C.RED
            print(f"  {name:6s} ({lp_pct:3d}% LP): Profit: {pc}{profit:8.2f}{C.END} ({roi:+.1f}%)")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                            Summary                                    │
    # └───────────────────────────────────────────────────────────────────────┘
    
    if verbose:
        print(f"\n{C.BOLD}Strategy Analysis:{C.END}")
        # Sort by profit to show which strategy won
        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
        for i, (name, profit) in enumerate(sorted_results):
            lp_pct = int(strategies[name] * 100)
            medal = ["🥇", "🥈", "🥉", "  "][i]
            print(f"  {medal} {name} ({lp_pct}% LP): {C.GREEN if profit > 0 else C.RED}{profit:.2f}{C.END}")
        
        print(f"\nVault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")

    return {
        "codename": codename,
        "profits": results,
        "vault": vault.balance_of(),
        "strategies": strategies,
        "losers": sum(1 for p in results.values() if p <= 0),
        "winners": sum(1 for p in results.values() if p > 0),
        "total_profit": sum(results.values(), D(0)),
    }
