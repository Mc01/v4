"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                        Stochastic Scenario                                ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Time-distributed user arrivals with compounding between trades.          ║
║                                                                           ║
║  10 users arrive on random days over 180 days (seeded RNG for            ║
║  reproducibility). Each buys 200-1000 USDC. Compounds between trades.    ║
║  All exit at end in FIFO order.                                           ║
║                                                                           ║
║  Models more realistic market behavior than batch buy-compound-sell.      ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
import random
from decimal import Decimal as D
from ..core import create_model, model_label, User, ScenarioResult
from ..formatter import Formatter


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          CONFIGURATION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

NUM_USERS = 10
TOTAL_DAYS = 180
INITIAL_BALANCE = D(5_000)
MIN_BUY = 200
MAX_BUY = 1000
SEED = 42  # Deterministic for reproducibility


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       CORE IMPLEMENTATION                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def stochastic_scenario(codename: str, verbosity: int = 1) -> ScenarioResult:
    """Run stochastic scenario with time-distributed arrivals."""
    rng = random.Random(SEED)
    vault, lp = create_model(codename)
    f = Formatter(verbosity)
    f.set_lp(lp)

    total_users = NUM_USERS

    f.header("STOCHASTIC", model_label(codename))

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │              Generate Random Arrival Schedule                         │
    # └───────────────────────────────────────────────────────────────────────┘

    arrivals: list[tuple[int, str, D]] = []
    for i in range(NUM_USERS):
        day = rng.randint(0, TOTAL_DAYS - 30)  # Arrive by day 150 (30 days to compound)
        buy_amount = D(rng.randint(MIN_BUY, MAX_BUY))
        name = f"User{i+1:02d}"
        arrivals.append((day, name, buy_amount))

    # Sort by arrival day
    arrivals.sort(key=lambda x: x[0])

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                    Entry Phase: Staggered Arrivals                    │
    # └───────────────────────────────────────────────────────────────────────┘

    f.section("Entry Phase (staggered)")

    users: dict[str, User] = {}
    entry_prices: dict[str, D] = {}
    tokens_received: dict[str, D] = {}
    current_day = 0

    for i, (day, name, buy_amount) in enumerate(arrivals, 1):
        # Compound between arrivals
        days_gap = day - current_day
        if days_gap > 0:
            vault_before = vault.balance_of()
            price_before_compound = lp.price
            vault.compound(days_gap)
            if days_gap >= 10:  # Only print significant gaps
                f.compound(days_gap, vault_before, vault.balance_of(),
                          price_before_compound, lp.price)
            current_day = day

        user = User(name.lower(), INITIAL_BALANCE)
        users[name] = user
        entry_prices[name] = lp.price
        price_before = lp.price

        lp.buy(user, buy_amount)
        tokens_received[name] = user.balance_token
        price_after_buy = lp.price

        # Add liquidity with matched USDC
        token_amount = user.balance_token
        usdc_amount = token_amount * lp.price
        lp.add_liquidity(user, token_amount, usdc_amount)

        f.buy(i, total_users, name, buy_amount, price_before,
              tokens_received[name], price_after_buy)
        f.add_lp(name, token_amount, usdc_amount)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                   Final Compound to Day 180                           │
    # └───────────────────────────────────────────────────────────────────────┘

    remaining_days = TOTAL_DAYS - current_day
    if remaining_days > 0:
        vault_before = vault.balance_of()
        price_before_compound = lp.price
        vault.compound(remaining_days)
        f.compound(remaining_days, vault_before, vault.balance_of(),
                  price_before_compound, lp.price)

    f.stats("Before Exits", lp, level=1)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                  Exit Phase: FIFO (earliest entrant first)            │
    # └───────────────────────────────────────────────────────────────────────┘

    f.section("Exit Phase (FIFO)")

    results: dict[str, D] = {}

    for i, (day, name, buy_amount) in enumerate(arrivals, 1):
        user = users[name]
        price_before_exit = lp.price

        usdc_before_lp = user.balance_usd
        lp.remove_liquidity(user)
        tokens = user.balance_token
        usdc_from_lp = user.balance_usd - usdc_before_lp

        lp.sell(user, tokens)
        price_after_exit = lp.price

        profit = user.balance_usd - INITIAL_BALANCE
        results[name] = profit
        roi = (profit / buy_amount) * 100

        f.remove_lp(name, tokens, usdc_from_lp)
        f.exit(i, total_users, name, profit, price_before_exit, price_after_exit, roi=roi)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                            Summary                                    │
    # └───────────────────────────────────────────────────────────────────────┘

    f.summary(results, vault.balance_of(), title="STOCHASTIC SCENARIO SUMMARY")

    return {
        "codename": codename,
        "profits": results,
        "vault": vault.balance_of(),
        "entry_prices": entry_prices,
        "losers": sum(1 for p in results.values() if p <= 0),
        "winners": sum(1 for p in results.values() if p > 0),
        "total_profit": sum(results.values(), D(0)),
    }
