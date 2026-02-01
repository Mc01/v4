"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    Hold Without LP Scenario                               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Tests passive holder dilution from token inflation.                      ║
║                                                                           ║
║  When a user buys tokens but doesn't LP, their USDC goes into the vault   ║
║  benefiting LPers, but they receive no yield tokens. Three timing         ║
║  variants test whether entry timing affects dilution:                     ║
║    - hold_before: Passive enters 90d before LPers                         ║
║    - hold_with: Passive enters with LPers                                 ║
║    - hold_after: Passive enters 90d after LPers                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from typing import Literal
from ..core import create_model, model_label, User, Color, ScenarioResult


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

LP_USERS: list[tuple[str, D]] = [
    ("Alice", D(500)),
    ("Bob", D(500)),
    ("Carl", D(500)),
    ("Diana", D(500)),
]

PASSIVE_USER = ("Passive", D(500))
COMPOUND_DAYS = 100
OFFSET_DAYS = 90
INITIAL_USDC = D(2000)

HoldVariant = Literal["before", "with", "after"]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       CORE IMPLEMENTATION                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def _hold_impl(codename: str, variant: HoldVariant, verbose: bool = True) -> ScenarioResult:
    """Run hold scenario with specified timing variant."""
    vault, lp = create_model(codename)
    C = Color
    variant_labels = {"before": "BEFORE", "with": "WITH", "after": "AFTER"}
    label = f"HOLD ({variant_labels[variant]} LPers)"
    
    # Create all users
    users = {name: User(name.lower(), INITIAL_USDC) for name, _ in LP_USERS}
    passive_name, passive_buy = PASSIVE_USER
    users[passive_name] = User(passive_name.lower(), INITIAL_USDC)
    
    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  {label} - {model_label(codename):^40}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                    Variant: Passive BEFORE LPers                      │
    # └───────────────────────────────────────────────────────────────────────┘
    
    if variant == "before":
        # Passive buys first
        u = users[passive_name]
        lp.buy(u, passive_buy)
        if verbose:
            print(f"[{passive_name} Buy] {passive_buy} USDC -> {C.YELLOW}{u.balance_token:.2f}{C.END} tokens (NO LP)")
        
        # Compound before LPers enter
        vault.compound(OFFSET_DAYS)
        if verbose:
            print(f"{C.DIM}  ... {OFFSET_DAYS} days pass ...{C.END}")
        
        # LPers enter and LP
        for name, buy_amount in LP_USERS:
            u = users[name]
            lp.buy(u, buy_amount)
            token_amount = u.balance_token
            usdc_amount = token_amount * lp.price
            lp.add_liquidity(u, token_amount, usdc_amount)
            if verbose:
                print(f"[{name}] Buy {buy_amount} + LP, Price: {C.GREEN}{lp.price:.6f}{C.END}")
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                    Variant: Passive WITH LPers                        │
    # └───────────────────────────────────────────────────────────────────────┘
    
    elif variant == "with":
        # All enter together - LPers first, then Passive
        for name, buy_amount in LP_USERS:
            u = users[name]
            lp.buy(u, buy_amount)
            token_amount = u.balance_token
            usdc_amount = token_amount * lp.price
            lp.add_liquidity(u, token_amount, usdc_amount)
            if verbose:
                print(f"[{name}] Buy {buy_amount} + LP, Price: {C.GREEN}{lp.price:.6f}{C.END}")
        
        u = users[passive_name]
        lp.buy(u, passive_buy)
        if verbose:
            print(f"[{passive_name} Buy] {passive_buy} USDC -> {C.YELLOW}{u.balance_token:.2f}{C.END} tokens (NO LP)")
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                    Variant: Passive AFTER LPers                       │
    # └───────────────────────────────────────────────────────────────────────┘
    
    elif variant == "after":
        # LPers enter and LP first
        for name, buy_amount in LP_USERS:
            u = users[name]
            lp.buy(u, buy_amount)
            token_amount = u.balance_token
            usdc_amount = token_amount * lp.price
            lp.add_liquidity(u, token_amount, usdc_amount)
            if verbose:
                print(f"[{name}] Buy {buy_amount} + LP, Price: {C.GREEN}{lp.price:.6f}{C.END}")
        
        # Compound before Passive enters
        vault.compound(OFFSET_DAYS)
        if verbose:
            print(f"{C.DIM}  ... {OFFSET_DAYS} days pass ...{C.END}")
        
        # Passive buys at higher price
        u = users[passive_name]
        lp.buy(u, passive_buy)
        if verbose:
            print(f"[{passive_name} Buy] {passive_buy} USDC -> {C.YELLOW}{u.balance_token:.2f}{C.END} tokens (NO LP)")

    if verbose:
        lp.print_stats("After Entry Phase")

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
    
    # LPers exit: remove liquidity + sell
    for name, buy_amount in LP_USERS:
        u = users[name]
        lp.remove_liquidity(u)
        tokens = u.balance_token
        lp.sell(u, tokens)
        profit = u.balance_usd - INITIAL_USDC
        results[name] = profit
        if verbose:
            pc = C.GREEN if profit > 0 else C.RED
            print(f"  {name:8s}: Invested {C.YELLOW}{buy_amount}{C.END}, Profit: {pc}{profit:.2f}{C.END}")
    
    # Passive exits: just sell tokens (no LP to remove)
    u = users[passive_name]
    tokens = u.balance_token
    lp.sell(u, tokens)
    profit = u.balance_usd - INITIAL_USDC
    results[passive_name] = profit
    if verbose:
        pc = C.GREEN if profit > 0 else C.RED
        print(f"  {passive_name:8s}: Invested {C.YELLOW}{passive_buy}{C.END}, Profit: {pc}{profit:.2f}{C.END} (NO LP)")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                            Summary                                    │
    # └───────────────────────────────────────────────────────────────────────┘
    
    if verbose:
        total = sum(results.values())
        losers = sum(1 for p in results.values() if p <= 0)
        tc = C.GREEN if total > 0 else C.RED
        print(f"\n{C.BOLD}Total profit: {tc}{total:.2f}{C.END}")
        print(f"Vault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")
        if results[passive_name] < 0:
            print(f"{C.RED}⚠ Passive holder DILUTED by {-results[passive_name]:.2f} USDC{C.END}")
        else:
            print(f"{C.GREEN}✓ Passive holder profit: {results[passive_name]:.2f}{C.END}")

    return {
        "codename": codename,
        "profits": results,
        "vault": vault.balance_of(),
        "losers": sum(1 for p in results.values() if p <= 0),
        "winners": sum(1 for p in results.values() if p > 0),
        "total_profit": sum(results.values(), D(0)),
    }


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC ENTRY POINTS                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def hold_before_scenario(codename: str, verbose: bool = True) -> ScenarioResult:
    """Passive holder enters 90 days BEFORE LPers."""
    return _hold_impl(codename, "before", verbose)

def hold_with_scenario(codename: str, verbose: bool = True) -> ScenarioResult:
    """Passive holder enters WITH LPers (same day)."""
    return _hold_impl(codename, "with", verbose)

def hold_after_scenario(codename: str, verbose: bool = True) -> ScenarioResult:
    """Passive holder enters 90 days AFTER LPers."""
    return _hold_impl(codename, "after", verbose)
