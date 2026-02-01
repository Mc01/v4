"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    Bank Run Scenario (FIFO)                               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  10 users enter, compound for 365 days, then all exit sequentially (FIFO):║
║    1. All users buy tokens and add liquidity                              ║
║    2. Compound for 365 days                                               ║
║    3. All users exit in order (Aaron first, Jack last)                    ║
║                                                                           ║
║  Tests protocol behavior under stress when everyone exits.                ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, Color, K, BankRunResult


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# (name, buy_amount) -- each user starts with 3K USDC
USERS_DATA: list[tuple[str, D]] = [
    ("Aaron", D(500)), ("Bob", D(400)), ("Carl", D(300)), ("Dennis", D(600)),
    ("Eve", D(350)), ("Frank", D(450)), ("Grace", D(550)),
    ("Henry", D(250)), ("Iris", D(380)), ("Jack", D(420)),
]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       SHARED IMPLEMENTATION                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def _bank_run_impl(codename: str, reverse: bool = False, verbose: bool = True) -> BankRunResult:
    """Shared implementation for FIFO and LIFO bank run scenarios."""
    vault, lp = create_model(codename)
    C = Color
    label = "REVERSE BANK RUN" if reverse else "BANK RUN"
    width = 42 if reverse else 50
    users = {name: User(name.lower(), 3 * K) for name, _ in USERS_DATA}

    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  {label} - {model_label(codename):^{width}}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │       Entry: Everyone Buys Tokens and Provides Liquidity              │
    # └───────────────────────────────────────────────────────────────────────┘

    for name, buy_amount in USERS_DATA:
        u = users[name]
        lp.buy(u, buy_amount)
        token_amount = u.balance_token
        usdc_amount = token_amount * lp.price
        lp.add_liquidity(u, token_amount, usdc_amount)
        if verbose:
            print(f"[{name}] Buy {buy_amount} + LP, Price: {C.GREEN}{lp.price:.6f}{C.END}")

    if verbose:
        lp.print_stats("After All Buy + LP")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │              Yield Accrual: Full Year of Compounding                  │
    # └───────────────────────────────────────────────────────────────────────┘

    vault.compound(365)
    if verbose:
        print(f"{C.BLUE}--- Compound 365 days ---{C.END}")
        print(f"  Vault: {C.YELLOW}{vault.balance_of():.2f}{C.END}, Price: {C.GREEN}{lp.price:.6f}{C.END}")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │              Exit: All Users Withdraw (FIFO or LIFO)                  │
    # └───────────────────────────────────────────────────────────────────────┘

    exit_order = reversed(USERS_DATA) if reverse else iter(USERS_DATA)
    results: dict[str, D] = {}
    winners = 0
    losers = 0
    for name, buy_amount in exit_order:
        u = users[name]
        lp.remove_liquidity(u)
        tokens = u.balance_token
        lp.sell(u, tokens)
        profit = u.balance_usd - 3 * K
        results[name] = profit
        if profit > 0:
            winners += 1
        else:
            losers += 1
        if verbose:
            pc = C.GREEN if profit > 0 else C.RED
            print(f"  {name:7s}: Invested {C.YELLOW}{buy_amount}{C.END}, Profit: {pc}{profit:.2f}{C.END}")

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                            Summary                                    │
    # └───────────────────────────────────────────────────────────────────────┘

    total_profit: D = sum(results.values(), D(0))
    if verbose:
        print(f"\n{C.BOLD}Winners: {C.GREEN}{winners}{C.END}, Losers: {C.RED}{losers}{C.END}")
        tc = C.GREEN if total_profit > 0 else C.RED
        print(f"{C.BOLD}Total profit: {tc}{total_profit:.2f}{C.END}")
        print(f"Vault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")

    return {
        "codename": codename, "profits": results,
        "winners": winners, "losers": losers,
        "total_profit": total_profit, "vault": vault.balance_of(),
    }


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC ENTRY POINT                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def bank_run_scenario(codename: str, verbose: bool = True) -> BankRunResult:
    """10 users, 365 days compound, all exit sequentially."""
    return _bank_run_impl(codename, reverse=False, verbose=verbose)
