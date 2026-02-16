"""
╔═══════════════════════════════════════════════════════════════════════════╗
║               Stress Tests - Atomic Accounting Verification               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  These tests verify internal accounting with MANUALLY COMPUTED VALUES.    ║
║  Each test is ATOMIC - tests ONE operation with explicit expectations.    ║
║                                                                           ║
║  KEY INSIGHT: Find EXACT point where accounting diverges from expected.   ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D

from ..core import create_model, User, Vault, DUST


# ═══════════════════════════════════════════════════════════════════════════
#                         VAULT ACCOUNTING TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_vault_add_remove_conservation(model: str):
    """Vault.add(x) then Vault.remove(x) should leave balance = 0."""
    vault = Vault()

    vault.add(D(1000))
    assert vault.balance_of() == D(1000), f"Vault balance after add: {vault.balance_of()}"

    vault.remove(D(1000))
    assert vault.balance_of() == D(0), f"Vault balance after remove: {vault.balance_of()}"


def test_vault_compound_exact_math(model: str):
    """Vault compound should match EXACT expected value for 100 days @ 5% APY."""
    vault = Vault()
    vault.add(D(1000))

    vault.compound(100)

    daily_rate = D(1) + D("0.05") / D(365)
    expected = D(1000) * daily_rate ** 100

    actual = vault.balance_of()
    diff = abs(actual - expected)

    assert diff < D("0.01"), f"Compound mismatch: expected={expected}, actual={actual}, diff={diff}"


def test_vault_compound_then_remove_all(model: str):
    """After compounding, removing balance_of() should empty vault."""
    vault = Vault()
    vault.add(D(1000))
    vault.compound(100)

    balance = vault.balance_of()
    vault.remove(balance)

    remaining = vault.balance_of()
    assert remaining < DUST, f"Vault not empty after full remove: {remaining}"


# ═══════════════════════════════════════════════════════════════════════════
#                      LP BUY/SELL USDC TRACKING TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_buy_tracks_usdc_exactly(model: str):
    """buy(X USDC) should add exactly X to buy_usdc tracking."""
    vault, lp = create_model(model)
    user = User("alice", D(1000))

    buy_amount = D(500)
    buy_usdc_before = lp.buy_usdc
    user_buy_before = lp.user_buy_usdc.get("alice", D(0))

    lp.buy(user, buy_amount)

    pool_increase = lp.buy_usdc - buy_usdc_before
    user_increase = lp.user_buy_usdc.get("alice", D(0)) - user_buy_before

    assert abs(pool_increase - buy_amount) < DUST, \
        f"Pool buy_usdc increase: expected={buy_amount}, actual={pool_increase}"

    assert abs(user_increase - buy_amount) < DUST, \
        f"User buy_usdc increase: expected={buy_amount}, actual={user_increase}"


def test_sell_reduces_usdc_proportionally(model: str):
    """sell(all tokens) should reduce buy_usdc to near 0 for single user."""
    vault, lp = create_model(model)
    user = User("alice", D(1000))

    lp.buy(user, D(500))
    tokens = user.balance_token

    lp.sell(user, tokens)

    buy_usdc_after_sell = lp.buy_usdc
    user_buy_after_sell = lp.user_buy_usdc.get("alice", D(0))

    assert buy_usdc_after_sell < D("0.01"), \
        f"Pool buy_usdc after full sell: {buy_usdc_after_sell} (expected ~0)"

    assert user_buy_after_sell < D("0.01"), \
        f"User buy_usdc after full sell: {user_buy_after_sell} (expected ~0)"


def test_buy_usdc_invariant_multi_user(model: str):
    """sum(user_buy_usdc) should ALWAYS equal buy_usdc."""
    vault, lp = create_model(model)
    users = [User(f"user{i}", D(1000)) for i in range(5)]

    # Buy phase
    for i, user in enumerate(users):
        lp.buy(user, D(100 * (i + 1)))  # 100, 200, 300, 400, 500 USDC

        user_sum = sum(lp.user_buy_usdc.values())
        diff = abs(user_sum - lp.buy_usdc)
        assert diff < DUST, f"Invariant broken after buy {i+1}: sum={user_sum}, pool={lp.buy_usdc}"

    # Sell phase - partial sells
    for i, user in enumerate(users):
        sell_amount = user.balance_token / 2
        lp.sell(user, sell_amount)

        user_sum = sum(lp.user_buy_usdc.values())
        diff = abs(user_sum - lp.buy_usdc)
        assert diff < DUST, f"Invariant broken after sell {i+1}: sum={user_sum}, pool={lp.buy_usdc}, diff={diff}"


# ═══════════════════════════════════════════════════════════════════════════
#                      LP LIQUIDITY ADD/REMOVE TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_add_liquidity_tracks_usdc_exactly(model: str):
    """add_liquidity deposits USDC, balance should go to vault."""
    vault, lp = create_model(model)
    user = User("alice", D(2000))

    lp.buy(user, D(500))
    tokens = user.balance_token

    vault_before = vault.balance_of()
    lp_usdc_before = lp.lp_usdc

    lp_usdc_amount = D(500)
    lp.add_liquidity(user, tokens, lp_usdc_amount)

    vault_increase = vault.balance_of() - vault_before
    lp_increase = lp.lp_usdc - lp_usdc_before

    assert abs(vault_increase - lp_usdc_amount) < DUST, \
        f"Vault didn't receive LP USDC: expected +{lp_usdc_amount}, got +{vault_increase}"

    assert abs(lp_increase - lp_usdc_amount) < DUST, \
        f"lp_usdc tracking wrong: expected +{lp_usdc_amount}, got +{lp_increase}"


def test_remove_liquidity_returns_principal_no_yield(model: str):
    """Without compounding, remove_liquidity should return EXACT principal."""
    vault, lp = create_model(model)
    user = User("alice", D(2000))

    lp.buy(user, D(500))
    tokens_for_lp = user.balance_token
    lp_usdc = D(500)
    lp.add_liquidity(user, tokens_for_lp, lp_usdc)

    # NO COMPOUNDING - remove immediately
    user_usdc_before = user.balance_usd
    user_tokens_before = user.balance_token

    lp.remove_liquidity(user)

    usdc_received = user.balance_usd - user_usdc_before
    tokens_received = user.balance_token - user_tokens_before

    usdc_diff = abs(usdc_received - lp_usdc)
    token_diff = abs(tokens_received - tokens_for_lp)

    assert usdc_diff < D("1.0"), \
        f"USDC mismatch: expected ~{lp_usdc}, got {usdc_received}, diff={usdc_diff}"

    assert token_diff < D("1.0"), \
        f"Token mismatch: expected ~{tokens_for_lp}, got {tokens_received}, diff={token_diff}"


def test_total_system_usdc_conservation(model: str):
    """
    CRITICAL TEST: Track EVERY USDC flow.

    Invariant: sum(user_usdc_final) + vault_remaining = sum(user_usdc_initial) + yield_created.

    No USDC should be created or destroyed (except by compounding).
    """
    vault, lp = create_model(model)

    users = [User(f"user{i}", D(2000)) for i in range(5)]
    total_initial = sum(u.balance_usd for u in users)

    # Phase 1: Buys
    for user in users:
        lp.buy(user, D(500))

    # Phase 2: LP
    for user in users:
        lp.add_liquidity(user, user.balance_token, D(400))

    vault_before_compound = vault.balance_of()

    # Phase 3: Compound (CREATES new USDC from external yield)
    vault.compound(100)
    yield_created = vault.balance_of() - vault_before_compound

    # Phase 4: Full exit
    for user in users:
        lp.remove_liquidity(user)
        lp.sell(user, user.balance_token)

    # Final accounting
    total_final = sum(u.balance_usd for u in users)
    vault_remaining = vault.balance_of()

    expected_total = total_initial + yield_created
    actual_total = total_final + vault_remaining
    diff = abs(actual_total - expected_total)

    assert diff < D("1.0"), \
        f"USDC not conserved: expected={expected_total}, actual={actual_total}, diff={diff}"


# ═══════════════════════════════════════════════════════════════════════════
#                              ALL TESTS
# ═══════════════════════════════════════════════════════════════════════════

ALL_TESTS = [
    ("Vault add/remove conservation", test_vault_add_remove_conservation),
    ("Vault compound exact math", test_vault_compound_exact_math),
    ("Vault compound then remove all", test_vault_compound_then_remove_all),
    ("Buy tracks USDC exactly", test_buy_tracks_usdc_exactly),
    ("Sell reduces USDC proportionally", test_sell_reduces_usdc_proportionally),
    ("Buy USDC invariant multi-user", test_buy_usdc_invariant_multi_user),
    ("Add liquidity tracks USDC", test_add_liquidity_tracks_usdc_exactly),
    ("Remove liquidity returns principal", test_remove_liquidity_returns_principal_no_yield),
    ("System USDC conservation", test_total_system_usdc_conservation),
]
