"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                       Real Life Scenario                                  ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Tests continuous flow mimicking real usage patterns.                     ║
║                                                                           ║
║  Unlike batch scenarios where everyone enters then everyone exits, this   ║
║  scenario has overlapping entries and exits:                              ║
║                                                                           ║
║  Timeline:                                                                ║
║    Day 0:   Alice, Bob enter                                              ║
║    Day 30:  Carl enters                                                   ║
║    Day 60:  Alice exits, Diana enters                                     ║
║    Day 90:  Eve, Frank enter                                              ║
║    Day 120: Bob, Carl exit, Grace enters                                  ║
║    Day 150: Diana exits, Henry enters                                     ║
║    Day 180: Eve exits                                                     ║
║    Day 210: All remaining exit                                            ║
║                                                                           ║
║  This tests protocol stability under realistic churn.                     ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, Color, ScenarioResult


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

INITIAL_USDC = D(2000)

# Timeline events: (day, event_type, user_name, buy_amount_if_entering)
TIMELINE: list[tuple[int, str, str, D]] = [
    # Day 0: Initial users
    (0, "enter", "Alice", D(500)),
    (0, "enter", "Bob", D(400)),
    
    # Day 30: Carl joins
    (30, "enter", "Carl", D(600)),
    
    # Day 60: Alice exits, Diana enters
    (60, "exit", "Alice", D(0)),
    (60, "enter", "Diana", D(350)),
    
    # Day 90: More enter
    (90, "enter", "Eve", D(450)),
    (90, "enter", "Frank", D(300)),
    
    # Day 120: Mid departures, new entry
    (120, "exit", "Bob", D(0)),
    (120, "exit", "Carl", D(0)),
    (120, "enter", "Grace", D(550)),
    
    # Day 150: Diana exits, Henry enters
    (150, "exit", "Diana", D(0)),
    (150, "enter", "Henry", D(400)),
    
    # Day 180: Eve exits
    (180, "exit", "Eve", D(0)),
    
    # Day 210: All remaining exit
    (210, "exit", "Frank", D(0)),
    (210, "exit", "Grace", D(0)),
    (210, "exit", "Henry", D(0)),
]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       CORE IMPLEMENTATION                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def real_life_scenario(codename: str, verbose: bool = True) -> ScenarioResult:
    """Run real life scenario with overlapping entries and exits."""
    vault, lp = create_model(codename)
    C = Color
    
    # Get unique user names and their buy amounts
    user_buys: dict[str, D] = {}
    for _, event, name, amount in TIMELINE:
        if event == "enter":
            user_buys[name] = amount
    
    users: dict[str, User] = {name: User(name.lower(), INITIAL_USDC) for name in user_buys}
    results: dict[str, D] = {}
    event_log: list[str] = []
    entry_day: dict[str, int] = {}
    exit_day: dict[str, int] = {}
    
    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  REAL LIFE - {model_label(codename):^50}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                      Process Timeline Events                          │
    # └───────────────────────────────────────────────────────────────────────┘
    
    current_day = 0
    
    for day, event, name, buy_amount in TIMELINE:
        # Compound to reach this event's day
        if day > current_day:
            days_to_compound = day - current_day
            vault.compound(days_to_compound)
            if verbose:
                print(f"\n{C.DIM}--- Day {day} (compound {days_to_compound}d) ---{C.END}")
                print(f"  Vault: {C.YELLOW}{vault.balance_of():.2f}{C.END}, Price: {C.GREEN}{lp.price:.6f}{C.END}")
            current_day = day
        
        u = users[name]
        
        if event == "enter":
            entry_day[name] = day
            event_log.append(f"Day {day}: {name} enters (buy {buy_amount})")
            
            lp.buy(u, buy_amount)
            tokens = u.balance_token
            usdc_for_lp = tokens * lp.price
            lp.add_liquidity(u, tokens, usdc_for_lp)
            
            if verbose:
                print(f"  {C.GREEN}↑{C.END} {name} enters: {buy_amount} USDC -> {tokens:.2f} tokens + LP")
        
        elif event == "exit":
            exit_day[name] = day
            days_in = day - entry_day[name]
            event_log.append(f"Day {day}: {name} exits (after {days_in}d)")
            
            if name in lp.liquidity_token:
                lp.remove_liquidity(u)
            
            tokens = u.balance_token
            if tokens > 0:
                lp.sell(u, tokens)
            
            profit = u.balance_usd - INITIAL_USDC
            results[name] = profit
            roi = (profit / user_buys[name]) * 100
            
            if verbose:
                pc = C.GREEN if profit > 0 else C.RED
                print(f"  {C.RED}↓{C.END} {name} exits: Profit: {pc}{profit:.2f}{C.END} ({roi:+.1f}%) after {days_in} days")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                            Summary                                    │
    # └───────────────────────────────────────────────────────────────────────┘
    
    if verbose:
        print(f"\n{C.BOLD}{'='*50}{C.END}")
        print(f"{C.BOLD}FINAL RESULTS{C.END}")
        print(f"{'='*50}")
        
        # Sort by exit day to show chronological order
        sorted_users = sorted(results.keys(), key=lambda n: exit_day.get(n, 999))
        
        for name in sorted_users:
            profit = results[name]
            buy = user_buys[name]
            roi = (profit / buy) * 100
            days_in = exit_day[name] - entry_day[name]
            pc = C.GREEN if profit > 0 else C.RED
            
            print(f"  {name:7s}: Entry day {entry_day[name]:3d}, Exit day {exit_day[name]:3d} ({days_in:3d}d)")
            print(f"           Invested: {buy}, Profit: {pc}{profit:8.2f}{C.END} ({roi:+.1f}%)")
        
        total = sum(results.values())
        winners = sum(1 for p in results.values() if p > 0)
        losers = sum(1 for p in results.values() if p <= 0)
        
        print(f"\n{C.BOLD}Total profit: {C.GREEN if total > 0 else C.RED}{total:.2f}{C.END}")
        print(f"Winners: {C.GREEN}{winners}{C.END}, Losers: {C.RED}{losers}{C.END}")
        print(f"Vault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")

    return {
        "codename": codename,
        "profits": results,
        "vault": vault.balance_of(),
        "timeline": event_log,
        "losers": sum(1 for p in results.values() if p <= 0),
        "winners": sum(1 for p in results.values() if p > 0),
        "total_profit": sum(results.values(), D(0)),
    }
