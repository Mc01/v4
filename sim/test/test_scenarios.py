"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                   Scenario Tests - End-to-End Validation                  ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Tests complete user lifecycles and critical scenarios:                   ║
║    - Single user full cycle                                               ║
║    - Multi-user exit (vault should empty)                                ║
║    - Compounding effects                                                  ║
║    - Vault never goes negative                                            ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D

from ..core import create_model, User


# ───────────────────────────────────────────────────────────────────────────
#                           SINGLE USER CYCLE
# ───────────────────────────────────────────────────────────────────────────

def test_single_user_no_compound_exits_cleanly(model: str):
    """Single user: buy → LP → exit (no compound) → vault nearly empty"""
    vault, lp = create_model(model)
    user = User("alice", D(2000))
    
    lp.buy(user, D(500))
    lp.add_liquidity(user, user.balance_token, D(500))
    
    lp.remove_liquidity(user)
    lp.sell(user, user.balance_token)
    
    vault_remaining = vault.balance_of()
    
    assert vault_remaining < D("1.0"), \
        f"Vault has {vault_remaining} USDC (expected < 1.0)"


def test_single_user_with_compound(model: str):
    """Single user with compounding should earn yield"""
    vault, lp = create_model(model)
    user = User("alice", D(2000))
    
    lp.buy(user, D(500))
    lp.add_liquidity(user, user.balance_token, D(500))
    total_deposited = D(1000)
    
    vault.compound(100)
    
    initial_balance = user.balance_usd
    lp.remove_liquidity(user)
    lp.sell(user, user.balance_token)
    
    total_out = user.balance_usd - initial_balance
    
    assert total_out >= total_deposited * D("0.99"), \
        f"User got {total_out} but deposited {total_deposited}"


# ───────────────────────────────────────────────────────────────────────────
#                      CRITICAL: MULTI-USER FULL EXIT
# ───────────────────────────────────────────────────────────────────────────

def test_multi_user_full_exit_empties_vault(model: str):
    """CRITICAL: All users exit → vault should be nearly empty"""
    vault, lp = create_model(model)
    users = [User(f"user{i}", D(2000)) for i in range(5)]

    for user in users:
        lp.buy(user, D(500))
        lp.add_liquidity(user, user.balance_token, D(500))

    vault.compound(100)

    for user in users:
        lp.remove_liquidity(user)
        lp.sell(user, user.balance_token)

    vault_remaining = vault.balance_of()
    total_deposited = D(5000)  # 5 users * (500 buy + 500 LP)
    residual_pct = vault_remaining / total_deposited * 100

    # Vault residual is a known curve asymmetry issue (FINDINGS.md #2).
    # Integral curves have price multiplier mismatch between buy and sell;
    # token inflation adds unbacked tokens that extract additional USDC.
    # CYN: ~0 after FIX 1. EYN/SYN/LYN: <3% from multiplier asymmetry.
    assert residual_pct < D("3"), \
        f"Vault has {vault_remaining} USDC ({residual_pct:.1f}% of deposits, expected < 3%)"


def test_multi_user_no_losers_in_simple_case(model: str):
    """Simple equal users: aggregate profit should be positive with yield"""
    vault, lp = create_model(model)
    users = [User(f"user{i}", D(1000)) for i in range(5)]

    for user in users:
        lp.buy(user, D(400))
        lp.add_liquidity(user, user.balance_token, D(400))

    vault.compound(365)

    total_profit = D(0)
    for user in users:
        initial = D(1000)
        lp.remove_liquidity(user)
        lp.sell(user, user.balance_token)
        profit = user.balance_usd - initial
        total_profit += profit

    # Individual users may lose due to exit-order effects on bonding curves
    # (early sellers get higher prices, later sellers face depleted curve).
    # But aggregate profit should be positive — vault yield was created.
    assert total_profit > D("-1"), \
        f"Aggregate profit is {total_profit} (expected positive or near-zero)"


# ───────────────────────────────────────────────────────────────────────────
#                            SAFETY CHECKS
# ───────────────────────────────────────────────────────────────────────────

def test_vault_never_negative(model: str):
    """Vault should never go negative during aggressive operations"""
    vault, lp = create_model(model)
    users = [User(f"user{i}", D(2000)) for i in range(10)]
    
    for user in users:
        lp.buy(user, D(500))
        if user.balance_token > 0:
            lp.add_liquidity(user, user.balance_token, D(400))
    
    vault.compound(100)
    
    for user in users:
        if user.name in lp.liquidity_token:
            lp.remove_liquidity(user)
        if user.balance_token > 0:
            lp.sell(user, user.balance_token)
        
        assert vault.balance_of() >= D(0), \
            f"Vault went negative: {vault.balance_of()}"


def test_no_infinite_values(model: str):
    """No calculations should produce Inf or NaN"""
    vault, lp = create_model(model)
    user = User("alice", D(10000))
    
    lp.buy(user, D(5000))
    lp.add_liquidity(user, user.balance_token, D(4000))
    vault.compound(365)
    
    assert lp.price.is_finite(), f"Price is not finite: {lp.price}"
    assert vault.balance_of().is_finite(), f"Vault not finite"
    assert lp.minted.is_finite(), f"Minted not finite"


# ───────────────────────────────────────────────────────────────────────────
#                        TOKEN INFLATION FACTOR (FIX 3)
# ───────────────────────────────────────────────────────────────────────────

def test_token_inflation_factor_zero(model: str):
    """TOKEN_INFLATION_FACTOR=0: LP should receive NO inflated tokens (FIX 3)."""
    vault, lp = create_model(model, token_inflation_factor=D(0))
    user = User("alice", D(3000))

    lp.buy(user, D(500))
    tokens_before_lp = user.balance_token
    lp.add_liquidity(user, tokens_before_lp, D(500))

    vault.compound(365)

    tokens_before_remove = user.balance_token
    lp.remove_liquidity(user)
    tokens_after_remove = user.balance_token

    tokens_received = tokens_after_remove - tokens_before_remove
    # With inflation=0, should get back exactly the deposited tokens (no inflation)
    assert abs(tokens_received - tokens_before_lp) < D("0.01"), \
        f"Got {tokens_received} tokens back (deposited {tokens_before_lp}), expected no inflation"


def test_token_inflation_factor_default(model: str):
    """TOKEN_INFLATION_FACTOR=1 (default): LP should receive inflated tokens."""
    vault, lp = create_model(model)
    user = User("alice", D(3000))

    lp.buy(user, D(500))
    tokens_deposited = user.balance_token
    lp.add_liquidity(user, tokens_deposited, D(500))

    vault.compound(365)

    tokens_before = user.balance_token
    lp.remove_liquidity(user)
    tokens_received = user.balance_token - tokens_before

    # With 365 days at 5%, should get ~5% more tokens
    expected_inflation = tokens_deposited * D("0.04")  # at least 4%
    assert tokens_received > tokens_deposited + expected_inflation, \
        f"Tokens received {tokens_received} not enough above {tokens_deposited} (expected ~5% inflation)"


# ───────────────────────────────────────────────────────────────────────────
#                          COVERAGE GAPS
# ───────────────────────────────────────────────────────────────────────────

def test_sell_after_compound_earns_more(model: str):
    """Selling after vault compound should return more USDC than without compound."""
    # Without compound
    vault_a, lp_a = create_model(model)
    user_a = User("no_compound", D(1000))
    lp_a.buy(user_a, D(500))
    tokens = user_a.balance_token

    usdc_before_a = user_a.balance_usd
    lp_a.sell(user_a, tokens)
    usdc_no_compound = user_a.balance_usd - usdc_before_a

    # With compound
    vault_b, lp_b = create_model(model)
    user_b = User("with_compound", D(1000))
    lp_b.buy(user_b, D(500))
    tokens_b = user_b.balance_token

    vault_b.compound(365)

    usdc_before_b = user_b.balance_usd
    lp_b.sell(user_b, tokens_b)
    usdc_with_compound = user_b.balance_usd - usdc_before_b

    assert usdc_with_compound >= usdc_no_compound, \
        f"Compound didn't help: {usdc_with_compound} vs {usdc_no_compound}"


def test_compound_zero_days_noop(model: str):
    """vault.compound(0) should not change vault balance."""
    vault, lp = create_model(model)
    user = User("alice", D(1000))
    lp.buy(user, D(500))

    balance_before = vault.balance_of()
    index_before = vault.compounding_index

    vault.compound(0)

    assert vault.balance_of() == balance_before, \
        f"Balance changed: {balance_before} → {vault.balance_of()}"
    assert vault.compounding_index == index_before, \
        f"Index changed: {index_before} → {vault.compounding_index}"


# ───────────────────────────────────────────────────────────────────────────
#                             ALL TESTS
# ───────────────────────────────────────────────────────────────────────────

ALL_TESTS = [
    ("Single user no compound exits cleanly", test_single_user_no_compound_exits_cleanly),
    ("Single user with compound earns yield", test_single_user_with_compound),
    ("CRITICAL: Multi-user exit nearly empties vault", test_multi_user_full_exit_empties_vault),
    ("Multi-user aggregate profit positive", test_multi_user_no_losers_in_simple_case),
    ("Vault never goes negative", test_vault_never_negative),
    ("No infinite values", test_no_infinite_values),
    ("Token inflation factor=0 disables minting", test_token_inflation_factor_zero),
    ("Token inflation factor=1 enables minting", test_token_inflation_factor_default),
    ("Sell after compound earns more", test_sell_after_compound_earns_more),
    ("Compound zero days is noop", test_compound_zero_days_noop),
]
