"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    Bank Run Scenario (FIFO/LIFO)                          ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  10 users enter, compound for 365 days, then all exit sequentially.       ║
║  Tests protocol behavior under stress when everyone exits.                ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, K, BankRunResult
from ..formatter import Formatter


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

USERS_DATA: list[tuple[str, D]] = [
    ("Aaron", D(500)), ("Bob", D(400)), ("Carl", D(300)), ("Dennis", D(600)),
    ("Eve", D(350)), ("Frank", D(450)), ("Grace", D(550)),
    ("Henry", D(250)), ("Iris", D(380)), ("Jack", D(420)),
]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       SHARED IMPLEMENTATION                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def _bank_run_impl(codename: str, reverse: bool = False, verbosity: int = 1) -> BankRunResult:
    """Shared implementation for FIFO and LIFO bank run scenarios."""
    vault, lp = create_model(codename)
    f = Formatter(verbosity)
    f.set_lp(lp)
    label = "REVERSE BANK RUN (LIFO)" if reverse else "BANK RUN (FIFO)"
    users = {name: User(name.lower(), 3 * K) for name, _ in USERS_DATA}
    total_users = len(USERS_DATA)

    f.header(label, model_label(codename))

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │       Entry: Everyone Buys Tokens and Provides Liquidity              │
    # └───────────────────────────────────────────────────────────────────────┘

    f.section("Entry Phase")
    
    for i, (name, buy_amount) in enumerate(USERS_DATA, 1):
        u = users[name]
        price_before = lp.price
        lp.buy(u, buy_amount)
        price_after = lp.price
        tokens = u.balance_token
        usdc_amount = tokens * lp.price
        lp.add_liquidity(u, tokens, usdc_amount)
        
        f.buy(i, total_users, name, buy_amount, price_before, tokens, price_after)

    f.stats("After All Entry", lp, level=1)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │              Yield Accrual: Full Year of Compounding                  │
    # └───────────────────────────────────────────────────────────────────────┘

    vault_before = vault.balance_of()
    price_before = lp.price
    vault.compound(365)
    f.compound(365, vault_before, vault.balance_of(), price_before, lp.price)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │              Exit: All Users Withdraw (FIFO or LIFO)                  │
    # └───────────────────────────────────────────────────────────────────────┘

    f.section("Exit Phase")
    
    exit_order = list(reversed(USERS_DATA)) if reverse else list(USERS_DATA)
    results: dict[str, D] = {}
    winners, losers = 0, 0
    
    for i, (name, buy_amount) in enumerate(exit_order, 1):
        u = users[name]
        initial = 3 * K
        price_before = lp.price
        
        lp.remove_liquidity(u)
        lp.sell(u, u.balance_token)
        price_after = lp.price
        
        profit = u.balance_usd - initial
        results[name] = profit
        roi = (profit / buy_amount) * 100
        
        if profit > 0:
            winners += 1
        else:
            losers += 1
        
        f.exit(i, total_users, name, profit, price_before, price_after, roi=roi)

    f.summary(results, vault.balance_of(), title=f"{label} SUMMARY")

    return {
        "codename": codename,
        "profits": results,
        "winners": winners,
        "losers": losers,
        "total_profit": sum(results.values(), D(0)),
        "vault": vault.balance_of(),
    }


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC API                                        ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def bank_run_scenario(codename: str, verbosity: int = 1) -> BankRunResult:
    """FIFO exit: first buyer exits first."""
    v = verbosity
    return _bank_run_impl(codename, reverse=False, verbosity=v)


def reverse_bank_run_scenario(codename: str, verbosity: int = 1) -> BankRunResult:
    """LIFO exit: last buyer exits first."""
    v = verbosity
    return _bank_run_impl(codename, reverse=True, verbosity=v)
