"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                      Real Life Scenario                                   ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Simulates realistic protocol usage with overlapping entries and exits.   ║
║  Users enter and exit at various points during the simulation.            ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, K, ScenarioResult
from ..formatter import Formatter


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# Timeline: (day, event, name, amount)
TIMELINE: list[tuple[int, str, str, D]] = [
    (0, "enter", "Alice", D(500)),
    (10, "enter", "Bob", D(300)),
    (30, "enter", "Carl", D(700)),
    (50, "exit", "Alice", D(0)),
    (60, "enter", "Diana", D(400)),
    (90, "exit", "Bob", D(0)),
    (120, "enter", "Eve", D(600)),
    (150, "exit", "Carl", D(0)),
    (180, "exit", "Diana", D(0)),
    (200, "exit", "Eve", D(0)),
]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC API                                        ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def real_life_scenario(codename: str, verbosity: int = 1) -> ScenarioResult:
    """Run realistic overlapping entry/exit scenario."""
    vault, lp = create_model(codename)
    v = verbosity
    f = Formatter(v)
    f.set_lp(lp)
    
    # Determine unique users and count
    user_buys: dict[str, D] = {}
    for _, event, name, amount in TIMELINE:
        if event == "enter":
            user_buys[name] = amount
    
    users = {name: User(name.lower(), 5 * K) for name in user_buys}
    total_users = len(user_buys)
    
    f.header("REAL LIFE", model_label(codename))

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                     Process Timeline                                   │
    # └───────────────────────────────────────────────────────────────────────┘
    
    f.section("Timeline Events")
    
    results: dict[str, D] = {}
    entry_day: dict[str, int] = {}
    exit_day: dict[str, int] = {}
    entry_order: dict[str, int] = {}
    exit_order: dict[str, int] = {}
    
    prev_day = 0
    entry_count = 0
    exit_count = 0
    
    for day, event, name, buy_amount in TIMELINE:
        # Compound if days have passed
        days_to_compound = day - prev_day
        if days_to_compound > 0:
            vault_before = vault.balance_of()
            price_before = lp.price
            vault.compound(days_to_compound)
            f.compound(days_to_compound, vault_before, vault.balance_of(), 
                      price_before, lp.price)
        prev_day = day
        
        u = users[name]
        
        if event == "enter":
            entry_count += 1
            entry_day[name] = day
            entry_order[name] = entry_count
            
            price_before = lp.price
            lp.buy(u, buy_amount)
            price_after = lp.price
            tokens = u.balance_token
            usdc = tokens * lp.price
            lp.add_liquidity(u, tokens, usdc)
            
            f.buy(entry_count, total_users, f"{name} (day {day})", buy_amount,
                  price_before, tokens, price_after)
            f.stats(f"After {name} Entry", lp, level=2)
        
        elif event == "exit":
            exit_count += 1
            exit_day[name] = day
            exit_order[name] = exit_count
            
            initial = 5 * K
            price_before = lp.price
            
            lp.remove_liquidity(u)
            lp.sell(u, u.balance_token)
            price_after = lp.price
            
            profit = u.balance_usd - initial
            results[name] = profit
            days_in = day - entry_day[name]
            roi = (profit / user_buys[name]) * 100
            
            f.exit(exit_count, total_users, f"{name} ({days_in}d in)", profit,
                   price_before, price_after, roi=roi)
            f.stats(f"After {name} Exit", lp, level=2)

    f.summary(results, vault.balance_of(), title="REAL LIFE SUMMARY")

    return {
        "codename": codename,
        "profits": results,
        "vault": vault.balance_of(),
        "timeline": [f"d{d}: {e} {n}" for d, e, n, _ in TIMELINE],
        "losers": sum(1 for p in results.values() if p <= 0),
    }
