"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                        Whale Entry Scenario                               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Tests concentration and slippage when a whale enters.                    ║
║                                                                           ║
║  5 regular users buy 500 USDC each, then 1 whale buys 50,000 USDC.        ║
║  This tests whether:                                                      ║
║    - Whale gets worse price due to slippage                               ║
║    - Regular users benefit or suffer from whale's entry                   ║
║    - Protocol remains stable under concentration                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, Color, ScenarioResult


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

REGULAR_USERS: list[tuple[str, D]] = [
    ("Alice", D(500)),
    ("Bob", D(500)),
    ("Carl", D(500)),
    ("Diana", D(500)),
    ("Eve", D(500)),
]

WHALE = ("Moby", D(50_000))
COMPOUND_DAYS = 100
REGULAR_INITIAL = D(2_000)
WHALE_INITIAL = D(100_000)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       CORE IMPLEMENTATION                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def whale_scenario(codename: str, verbose: bool = True) -> ScenarioResult:
    """Run whale entry scenario."""
    vault, lp = create_model(codename)
    C = Color
    
    users = {name: User(name.lower(), REGULAR_INITIAL) for name, _ in REGULAR_USERS}
    whale_name, whale_buy = WHALE
    users[whale_name] = User(whale_name.lower(), WHALE_INITIAL)
    
    entry_prices: dict[str, D] = {}
    tokens_received: dict[str, D] = {}
    
    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  WHALE ENTRY - {model_label(codename):^48}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                    Regular Users Enter First                          │
    # └───────────────────────────────────────────────────────────────────────┘
    
    for name, buy_amount in REGULAR_USERS:
        u = users[name]
        entry_prices[name] = lp.price
        lp.buy(u, buy_amount)
        tokens_received[name] = u.balance_token
        
        token_amount = u.balance_token
        usdc_amount = token_amount * lp.price
        lp.add_liquidity(u, token_amount, usdc_amount)
        
        if verbose:
            print(f"[{name}] Buy {buy_amount} @ {entry_prices[name]:.4f} -> {tokens_received[name]:.2f} tokens + LP")
    
    if verbose:
        print(f"\n{C.YELLOW}Total regular USDC in: {D(500) * 5}{C.END}")
        lp.print_stats("Before Whale")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                        Whale Enters                                   │
    # └───────────────────────────────────────────────────────────────────────┘
    
    u = users[whale_name]
    entry_prices[whale_name] = lp.price
    price_before_whale = lp.price
    
    lp.buy(u, whale_buy)
    tokens_received[whale_name] = u.balance_token
    price_after_whale_buy = lp.price
    
    token_amount = u.balance_token
    usdc_amount = token_amount * lp.price
    lp.add_liquidity(u, token_amount, usdc_amount)
    
    if verbose:
        slippage = ((price_after_whale_buy / price_before_whale) - 1) * 100
        effective_price = whale_buy / tokens_received[whale_name]
        print(f"\n{C.BOLD}[{whale_name}] WHALE BUY {whale_buy} USDC{C.END}")
        print(f"  Entry price: {C.GREEN}{entry_prices[whale_name]:.4f}{C.END}")
        print(f"  Tokens received: {C.YELLOW}{tokens_received[whale_name]:.2f}{C.END}")
        print(f"  Effective avg price: {C.YELLOW}{effective_price:.4f}{C.END}")
        print(f"  Price impact: {C.RED}+{slippage:.1f}%{C.END}")
        lp.print_stats("After Whale")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                         Compound Period                               │
    # └───────────────────────────────────────────────────────────────────────┘
    
    vault.compound(COMPOUND_DAYS)
    if verbose:
        print(f"{C.BLUE}--- Compound {COMPOUND_DAYS} days ---{C.END}")
        print(f"  Vault: {C.YELLOW}{vault.balance_of():.2f}{C.END}, Price: {C.GREEN}{lp.price:.6f}{C.END}")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                  Exit: Regular Users First, Whale Last                │
    # └───────────────────────────────────────────────────────────────────────┘
    
    results: dict[str, D] = {}
    
    # Regular users exit
    for name, buy_amount in REGULAR_USERS:
        u = users[name]
        lp.remove_liquidity(u)
        tokens = u.balance_token
        lp.sell(u, tokens)
        profit = u.balance_usd - REGULAR_INITIAL
        results[name] = profit
        roi = (profit / buy_amount) * 100
        if verbose:
            pc = C.GREEN if profit > 0 else C.RED
            print(f"  {name:6s}: Profit: {pc}{profit:8.2f}{C.END} ({roi:+.1f}%)")
    
    # Whale exits last
    u = users[whale_name]
    lp.remove_liquidity(u)
    tokens = u.balance_token
    lp.sell(u, tokens)
    profit = u.balance_usd - WHALE_INITIAL
    results[whale_name] = profit
    roi = (profit / whale_buy) * 100
    if verbose:
        pc = C.GREEN if profit > 0 else C.RED
        print(f"\n  {C.BOLD}{whale_name:6s}: Profit: {pc}{profit:8.2f}{C.END} ({roi:+.1f}%)")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                            Summary                                    │
    # └───────────────────────────────────────────────────────────────────────┘
    
    if verbose:
        regular_total = sum(results[n] for n, _ in REGULAR_USERS)
        whale_profit = results[whale_name]
        
        print(f"\n{C.BOLD}Summary:{C.END}")
        print(f"  Regular users total profit: {C.GREEN if regular_total > 0 else C.RED}{regular_total:.2f}{C.END}")
        print(f"  Whale profit: {C.GREEN if whale_profit > 0 else C.RED}{whale_profit:.2f}{C.END}")
        print(f"  Vault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")

    return {
        "codename": codename,
        "profits": results,
        "vault": vault.balance_of(),
        "entry_prices": entry_prices,
        "losers": sum(1 for p in results.values() if p <= 0),
        "winners": sum(1 for p in results.values() if p > 0),
        "total_profit": sum(results.values(), D(0)),
    }
