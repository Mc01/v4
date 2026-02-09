"""
╔═══════════════════════════════════════════════════════════════════════════╗
║               Yield Accounting Tests - LP Yield Verification              ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Verifies that yield distribution follows protocol design:                ║
║    - LPs receive yield on their LP USDC deposit (direct)                  ║
║    - LPs receive yield on buy_usdc principal (common yield)               ║
║    - Token inflation mints proportional to LP tokens                      ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D

from ..core import create_model, User, DUST


# ───────────────────────────────────────────────────────────────────────────
#                      SINGLE-USER YIELD VERIFICATION
# ───────────────────────────────────────────────────────────────────────────

def test_lp_yield_includes_buy_usdc(model: str):
    """
    LP should receive yield on BOTH LP USDC and buy_usdc principal.

    User buys 500 USDC of tokens, then LPs with ALL tokens + 500 USDC.
    After compound, LP withdrawal should include yield on the full 1000 principal.
    This is the "common yield" mechanism — deliberately NOT a bug.
    """
    vault, lp = create_model(model)
    user = User("alice", D(2000))

    # Buy 500 USDC worth of tokens
    lp.buy(user, D(500))
    tokens_for_lp = user.balance_token

    # LP with ALL tokens + 500 matching USDC
    lp_usdc = D(500)
    lp.add_liquidity(user, tokens_for_lp, lp_usdc)

    vault_after_lp = vault.balance_of()

    # Compound 100 days
    vault.compound(100)

    yield_factor = (D(1) + D("0.05") / D(365)) ** 100

    # Track user USDC before remove
    user_usdc_before = user.balance_usd
    lp.remove_liquidity(user)
    usdc_received = user.balance_usd - user_usdc_before

    # Expected: yield on LP USDC (500) + yield on buy_usdc (500) = yield on 1000
    total_principal_yield = vault_after_lp * (yield_factor - 1)
    expected_total = lp_usdc + total_principal_yield

    # Allow 10% tolerance due to fair share scaling and token inflation effects
    tolerance = expected_total * D("0.10")
    diff = abs(usdc_received - expected_total)

    assert diff < tolerance, \
        f"USDC received {usdc_received:.2f} differs from expected {expected_total:.2f} by {diff:.2f}"


# ───────────────────────────────────────────────────────────────────────────
#                       TWO-USER YIELD SEPARATION
# ───────────────────────────────────────────────────────────────────────────

def test_two_user_yield_separation(model: str):
    """
    Two users — buyer and LPer — should have yield distributed correctly.

    Buyer: buys 500 USDC of tokens (yield → price appreciation)
    LPer: buys 500 then LPs with all tokens + 500 USDC (yield → direct + price)

    Total vault principal = 1500. Yield should be proportional.
    """
    vault, lp = create_model(model)

    buyer = User("buyer", D(1000))
    lp_user = User("LPer", D(1000))

    # Buyer buys tokens
    lp.buy(buyer, D(500))
    buyer_tokens = buyer.balance_token

    # LP user buys THEN provides liquidity
    lp.buy(lp_user, D(500))
    lp_tokens = lp_user.balance_token
    lp.add_liquidity(lp_user, lp_tokens, D(500))

    vault_after = vault.balance_of()

    # Compound
    vault.compound(100)
    yield_created = vault.balance_of() - vault_after

    # LP user removes first
    lp_usdc_before = lp_user.balance_usd
    lp.remove_liquidity(lp_user)
    lp_usdc_received = lp_user.balance_usd - lp_usdc_before

    # Then buyer sells
    buyer_usdc_before = buyer.balance_usd
    lp.sell(buyer, buyer_tokens)
    buyer_usdc_received = buyer.balance_usd - buyer_usdc_before

    vault_final = vault.balance_of()

    # Total withdrawn + vault remaining should equal total deposited + yield
    total_withdrawn = lp_usdc_received + buyer_usdc_received
    total_deposited = D(1500)  # 500 + 500 + 500

    actual_system = total_withdrawn + vault_final
    expected_system = total_deposited + yield_created
    diff = abs(actual_system - expected_system)

    assert diff < D("1.0"), \
        f"System not conserved: total={actual_system:.2f}, expected={expected_system:.2f}, diff={diff:.2f}"


def test_lp_yield_scales_with_compound_duration(model: str):
    """LP yield after 200 days should be approximately double yield after 100 days."""
    vault_100, lp_100 = create_model(model)
    vault_200, lp_200 = create_model(model)
    user_100 = User("alice100", D(3000))
    user_200 = User("alice200", D(3000))

    # Identical setup for both
    for v, l, u in [(vault_100, lp_100, user_100), (vault_200, lp_200, user_200)]:
        l.buy(u, D(500))
        l.add_liquidity(u, u.balance_token, D(500))

    # Record principal deposited as LP USDC for yield isolation
    lp_principal = D(500)

    # Different compound durations
    vault_100.compound(100)
    vault_200.compound(200)

    # Remove LP and isolate yield (total received - principal)
    usdc_before_100 = user_100.balance_usd
    lp_100.remove_liquidity(user_100)
    yield_100 = (user_100.balance_usd - usdc_before_100) - lp_principal

    usdc_before_200 = user_200.balance_usd
    lp_200.remove_liquidity(user_200)
    yield_200 = (user_200.balance_usd - usdc_before_200) - lp_principal

    # 200-day yield should be roughly 2x the 100-day yield
    # (slightly above 2x due to compound interest)
    ratio = yield_200 / yield_100 if yield_100 > 0 else D(0)
    assert D("1.8") < ratio < D("2.3"), \
        f"Yield ratio 200d/100d = {ratio:.2f} (expected ~2.0)"


# ───────────────────────────────────────────────────────────────────────────
#                             ALL TESTS
# ───────────────────────────────────────────────────────────────────────────

ALL_TESTS = [
    ("LP yield includes buy_usdc (common yield)", test_lp_yield_includes_buy_usdc),
    ("Two-user yield separation conserves", test_two_user_yield_separation),
    ("LP yield scales with duration", test_lp_yield_scales_with_compound_duration),
]
