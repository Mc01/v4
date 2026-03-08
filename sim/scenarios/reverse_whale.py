"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                      Reverse Whale Scenario                               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Same as whale scenario but exit order reversed: whale exits FIRST.       ║
║                                                                           ║
║  Tests whether early large withdrawals adversely affect remaining          ║
║  smaller users who entered before the whale.                              ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, ScenarioResult
from ..formatter import Formatter


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

def reverse_whale_scenario(codename: str, verbosity: int = 1) -> ScenarioResult:
    """Run reverse whale scenario: whale exits FIRST, regulars exit last."""
    vault, lp = create_model(codename)
    f = Formatter(verbosity)
    f.set_lp(lp)

    users = {name: User(name.lower(), REGULAR_INITIAL) for name, _ in REGULAR_USERS}
    whale_name, whale_buy = WHALE
    users[whale_name] = User(whale_name.lower(), WHALE_INITIAL)

    entry_prices: dict[str, D] = {}
    tokens_received: dict[str, D] = {}
    total_users = len(REGULAR_USERS) + 1

    f.header("REVERSE WHALE", model_label(codename))

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                    Regular Users Enter First                          │
    # └───────────────────────────────────────────────────────────────────────┘

    f.section("Entry Phase")

    for i, (name, buy_amount) in enumerate(REGULAR_USERS, 1):
        u = users[name]
        entry_prices[name] = lp.price
        price_before = lp.price

        lp.buy(u, buy_amount)
        tokens_received[name] = u.balance_token
        price_after_buy = lp.price

        token_amount = u.balance_token
        usdc_amount = token_amount * lp.price
        lp.add_liquidity(u, token_amount, usdc_amount)

        f.buy(i, total_users, name, buy_amount, price_before, tokens_received[name], price_after_buy)
        f.add_lp(name, token_amount, usdc_amount)

    f.stats("Before Whale", lp, level=1)

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

    f.buy(total_users, total_users, whale_name, whale_buy,
          price_before_whale, tokens_received[whale_name], price_after_whale_buy, emoji="🐋")
    f.add_lp(whale_name, token_amount, usdc_amount, emoji="🐋")

    f.stats("After Whale", lp, level=1)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                         Compound Period                               │
    # └───────────────────────────────────────────────────────────────────────┘

    vault_before = vault.balance_of()
    price_before_compound = lp.price
    vault.compound(COMPOUND_DAYS)
    f.compound(COMPOUND_DAYS, vault_before, vault.balance_of(), price_before_compound, lp.price)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │               Exit: Whale FIRST, Regular Users Last                   │
    # └───────────────────────────────────────────────────────────────────────┘

    f.section("Exit Phase (Whale First)")

    results: dict[str, D] = {}

    # Whale exits first
    u = users[whale_name]
    price_before_exit = lp.price

    usdc_before_lp = u.balance_usd
    lp.remove_liquidity(u)
    tokens = u.balance_token
    usdc_from_lp = u.balance_usd - usdc_before_lp

    lp.sell(u, tokens)
    price_after_exit = lp.price

    profit = u.balance_usd - WHALE_INITIAL
    results[whale_name] = profit
    roi = (profit / whale_buy) * 100

    f.remove_lp(whale_name, tokens, usdc_from_lp, emoji="🐋")
    f.exit(1, total_users, whale_name, profit,
           price_before_exit, price_after_exit, emoji="🐋", roi=roi)

    # Regular users exit after whale
    for i, (name, buy_amount) in enumerate(REGULAR_USERS, 2):
        u = users[name]
        price_before_exit = lp.price

        usdc_before_lp = u.balance_usd
        lp.remove_liquidity(u)
        tokens = u.balance_token
        usdc_from_lp = u.balance_usd - usdc_before_lp

        lp.sell(u, tokens)
        price_after_exit = lp.price

        profit = u.balance_usd - REGULAR_INITIAL
        results[name] = profit
        roi = (profit / buy_amount) * 100

        f.remove_lp(name, tokens, usdc_from_lp)
        f.exit(i, total_users, name, profit, price_before_exit, price_after_exit, roi=roi)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                            Summary                                    │
    # └───────────────────────────────────────────────────────────────────────┘

    f.summary(results, vault.balance_of(), title="REVERSE WHALE SUMMARY")

    return {
        "codename": codename,
        "profits": results,
        "vault": vault.balance_of(),
        "entry_prices": entry_prices,
        "losers": sum(1 for p in results.values() if p <= 0),
        "winners": sum(1 for p in results.values() if p > 0),
        "total_profit": sum(results.values(), D(0)),
    }
