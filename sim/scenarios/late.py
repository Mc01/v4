"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                      Late Entrant Scenario                                ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Tests first-mover advantage vs late entry.                               ║
║                                                                           ║
║  Early users enter at day 0, LP, and compound. A late user enters after   ║
║  price has appreciated (due to Y→P), buys at higher price, LPs, then all  ║
║  exit. Configurable wait periods: 90 or 180 days.                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, Color, ScenarioResult


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

EARLY_USERS: list[tuple[str, D]] = [
    ("Alice", D(500)),
    ("Bob", D(400)),
    ("Carl", D(300)),
]

LATE_USER = ("Luna", D(500))
FINAL_COMPOUND = 90
INITIAL_USDC = D(2_000)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       CORE IMPLEMENTATION                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def _late_impl(codename: str, wait_days: int, verbose: bool = True) -> ScenarioResult:
    """Run late entrant scenario with specified wait period."""
    vault, lp = create_model(codename)
    C = Color
    label = f"LATE ENTRANT ({wait_days}d wait)"
    
    users = {name: User(name.lower(), INITIAL_USDC) for name, _ in EARLY_USERS}
    late_name, late_buy = LATE_USER
    users[late_name] = User(late_name.lower(), INITIAL_USDC)
    
    entry_prices: dict[str, D] = {}
    
    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  {label} - {model_label(codename):^40}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                    Early Users Enter (Day 0)                          │
    # └───────────────────────────────────────────────────────────────────────┘
    
    for name, buy_amount in EARLY_USERS:
        u = users[name]
        entry_prices[name] = lp.price
        lp.buy(u, buy_amount)
        token_amount = u.balance_token
        usdc_amount = token_amount * lp.price
        lp.add_liquidity(u, token_amount, usdc_amount)
        if verbose:
            print(f"[{name}] Buy {buy_amount} @ {C.GREEN}{entry_prices[name]:.6f}{C.END} + LP")
    
    if verbose:
        lp.print_stats("After Early Users")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                  Wait Period (Price Appreciates)                      │
    # └───────────────────────────────────────────────────────────────────────┘
    
    vault.compound(wait_days)
    if verbose:
        print(f"{C.BLUE}--- Wait {wait_days} days (Y→P compounds) ---{C.END}")
        print(f"  Vault: {C.YELLOW}{vault.balance_of():.2f}{C.END}, Price: {C.GREEN}{lp.price:.6f}{C.END}")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                    Late User Enters (Day N)                           │
    # └───────────────────────────────────────────────────────────────────────┘
    
    u = users[late_name]
    entry_prices[late_name] = lp.price
    lp.buy(u, late_buy)
    token_amount = u.balance_token
    usdc_amount = token_amount * lp.price
    lp.add_liquidity(u, token_amount, usdc_amount)
    if verbose:
        price_increase = ((entry_prices[late_name] / entry_prices["Alice"]) - 1) * 100
        print(f"[{late_name}] Buy {late_buy} @ {C.YELLOW}{entry_prices[late_name]:.6f}{C.END} (+{price_increase:.1f}% vs early) + LP")
        lp.print_stats("After Late Entry")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                    Final Compound Period                              │
    # └───────────────────────────────────────────────────────────────────────┘
    
    vault.compound(FINAL_COMPOUND)
    if verbose:
        print(f"{C.BLUE}--- Final compound {FINAL_COMPOUND} days ---{C.END}")
        print(f"  Vault: {C.YELLOW}{vault.balance_of():.2f}{C.END}, Price: {C.GREEN}{lp.price:.6f}{C.END}")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                        Exit (FIFO Order)                              │
    # └───────────────────────────────────────────────────────────────────────┘
    
    results: dict[str, D] = {}
    all_users = list(EARLY_USERS) + [LATE_USER]
    
    for name, buy_amount in all_users:
        u = users[name]
        lp.remove_liquidity(u)
        tokens = u.balance_token
        lp.sell(u, tokens)
        profit = u.balance_usd - INITIAL_USDC
        results[name] = profit
        roi = (profit / buy_amount) * 100
        if verbose:
            pc = C.GREEN if profit > 0 else C.RED
            entry_label = "LATE" if name == late_name else "early"
            print(f"  {name:6s} ({entry_label}): Entry @ {entry_prices[name]:.4f}, Profit: {pc}{profit:.2f}{C.END} ({roi:+.1f}%)")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                            Summary                                    │
    # └───────────────────────────────────────────────────────────────────────┘
    
    if verbose:
        # Compare ROI
        early_avg_roi = sum((results[n] / b) * 100 for n, b in EARLY_USERS) / len(EARLY_USERS)
        late_roi = (results[late_name] / late_buy) * 100
        
        print(f"\n{C.BOLD}Early users avg ROI: {C.GREEN}{early_avg_roi:.1f}%{C.END}")
        print(f"{C.BOLD}Late user ROI: ", end="")
        if late_roi >= early_avg_roi:
            print(f"{C.GREEN}{late_roi:.1f}%{C.END} (≥ early avg)")
        else:
            diff = early_avg_roi - late_roi
            print(f"{C.YELLOW}{late_roi:.1f}%{C.END} (< early avg by {diff:.1f}pp)")
        print(f"Vault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")

    return {
        "codename": codename,
        "profits": results,
        "vault": vault.balance_of(),
        "entry_prices": entry_prices,
        "losers": sum(1 for p in results.values() if p <= 0),
        "winners": sum(1 for p in results.values() if p > 0),
        "total_profit": sum(results.values(), D(0)),
    }


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC ENTRY POINTS                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def late_90_scenario(codename: str, verbose: bool = True) -> ScenarioResult:
    """Late entrant joins 90 days after early users."""
    return _late_impl(codename, 90, verbose)

def late_180_scenario(codename: str, verbose: bool = True) -> ScenarioResult:
    """Late entrant joins 180 days after early users."""
    return _late_impl(codename, 180, verbose)
