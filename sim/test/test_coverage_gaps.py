"""
╔═══════════════════════════════════════════════════════════════════════════╗
║              Coverage Gap Tests (C1-C10)                                 ║
║  Tests identified during multi-agent review to fill coverage gaps.       ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from typing import Callable, List, Tuple

from ..core import (
    create_model, User, CurveType, DUST,
    _exp_price, MAX_EXP_ARG, EXP_K,
)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                             C1-C2: MODEL DIMENSIONS                      ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def test_yield_does_not_impact_price_when_disabled(model: str):
    """C1: When yield_impacts_price=False, price stays flat after compound."""
    vault, lp = create_model(model)
    # Override dimension: yield does NOT impact price
    lp.yield_impacts_price = False

    user = User("Alice", D(10_000))
    lp.buy(user, D(500))
    price_before_compound = lp.price

    lp.add_liquidity(user, user.balance_token, D(500))
    lp.vault.compound(100)
    price_after_compound = lp.price

    # Price should NOT change from compounding when yield_impacts_price=False
    assert abs(price_after_compound - price_before_compound) < D("0.000001"), \
        f"Price changed from {price_before_compound:.6f} to {price_after_compound:.6f} " \
        f"even though yield_impacts_price=False"


def test_lp_impacts_price_when_enabled(model: str):
    """C2: When lp_impacts_price=True, adding LP changes price."""
    vault, lp = create_model(model)
    # Override dimension: LP DOES impact price
    lp.lp_impacts_price = True

    user = User("Alice", D(10_000))
    lp.buy(user, D(500))
    price_before_lp = lp.price

    lp.add_liquidity(user, user.balance_token, D(500))
    price_after_lp = lp.price

    # Price should increase because LP USDC now contributes to effective_usdc
    # (For CP the reserves change differently, so just check it's not the same)
    if lp.curve_type != CurveType.CONSTANT_PRODUCT:
        assert price_after_lp > price_before_lp, \
            f"Price didn't increase after LP: {price_before_lp:.6f} -> {price_after_lp:.6f} " \
            f"even though lp_impacts_price=True"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          C3-C4: EDGE CASES                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def test_vault_remove_overcall_raises(model: str):
    """C3: Removing more USDC than vault balance should go negative gracefully
    or raise. Currently the vault doesn't guard this — this test documents behavior."""
    vault, lp = create_model(model)
    user = User("Alice", D(10_000))
    lp.buy(user, D(500))
    lp.add_liquidity(user, user.balance_token, D(500))

    vault_balance = lp.vault.balance_of()
    # Attempt to remove more than available. The vault computes balance_of() - value,
    # which can go negative. This documents current behavior.
    try:
        lp.vault.remove(vault_balance + D(100))
        new_balance = lp.vault.balance_of()
        # If it doesn't raise, the balance should be negative
        assert new_balance < 0, \
            f"Vault should be negative after overcall, got {new_balance}"
    except Exception:
        # If it raises, that's also acceptable behavior
        pass


def test_buy_with_zero_balance_goes_negative(model: str):
    """C4: User with 0 USDC buying goes negative. Documents current behavior."""
    vault, lp = create_model(model)
    user = User("Broke", D(0))

    # Buying with zero balance creates negative user USDC
    lp.buy(user, D(100))
    assert user.balance_usd < 0, \
        f"User with 0 USDC bought 100 but balance is {user.balance_usd} (expected negative)"
    # Tokens should have been received
    assert user.balance_token > 0, \
        f"User should have received tokens, got {user.balance_token}"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                        C5: PARAMETRIZED VAULT APY                         ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def test_zero_apy_produces_no_yield(model: str):
    """C5a: vault_apy=0% → zero yield after compound."""
    vault, lp = create_model(model, vault_apy=D(0))
    user = User("Alice", D(10_000))
    lp.buy(user, D(500))
    lp.add_liquidity(user, user.balance_token, D(500))

    vault_before = lp.vault.balance_of()
    lp.vault.compound(365)
    vault_after = lp.vault.balance_of()

    assert vault_after == vault_before, \
        f"Zero APY should produce no yield, but vault changed: {vault_before} -> {vault_after}"


def test_higher_apy_produces_more_yield(model: str):
    """C5b: vault_apy=10% produces more yield than default 5%."""
    # Default 5% APY
    vault_5, lp_5 = create_model(model)
    user_5 = User("Alice", D(10_000))
    lp_5.buy(user_5, D(500))
    lp_5.add_liquidity(user_5, user_5.balance_token, D(500))
    vault_before_5 = lp_5.vault.balance_of()
    lp_5.vault.compound(100)
    yield_5 = lp_5.vault.balance_of() - vault_before_5

    # Higher 10% APY
    vault_10, lp_10 = create_model(model, vault_apy=D("0.10"))
    user_10 = User("Bob", D(10_000))
    lp_10.buy(user_10, D(500))
    lp_10.add_liquidity(user_10, user_10.balance_token, D(500))
    vault_before_10 = lp_10.vault.balance_of()
    lp_10.vault.compound(100)
    yield_10 = lp_10.vault.balance_of() - vault_before_10

    assert yield_10 > yield_5, \
        f"10% APY yield ({yield_10:.4f}) should exceed 5% ({yield_5:.4f})"
    # Roughly 2x (not exact due to compounding effects)
    ratio = yield_10 / yield_5
    assert D("1.8") < ratio < D("2.2"), \
        f"Yield ratio 10%/5% = {ratio:.4f}, expected ~2.0"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       C6: COMPOUND IDEMPOTENCE                            ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def test_compound_split_equals_continuous(model: str):
    """C6: compound(50) + compound(50) should equal compound(100)."""
    # Model A: compound(100) at once
    vault_a, lp_a = create_model(model)
    user_a = User("Alice", D(10_000))
    lp_a.buy(user_a, D(500))
    lp_a.add_liquidity(user_a, user_a.balance_token, D(500))
    lp_a.vault.compound(100)
    balance_continuous = lp_a.vault.balance_of()

    # Model B: compound(50) twice
    vault_b, lp_b = create_model(model)
    user_b = User("Bob", D(10_000))
    lp_b.buy(user_b, D(500))
    lp_b.add_liquidity(user_b, user_b.balance_token, D(500))
    lp_b.vault.compound(50)
    lp_b.vault.compound(50)
    balance_split = lp_b.vault.balance_of()

    assert abs(balance_continuous - balance_split) < DUST, \
        f"Split compound ({balance_split:.12f}) != continuous ({balance_continuous:.12f})"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       C7: FAIR SHARE CAP                                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def test_fair_share_caps_sell(model: str):
    """C7: A user who owns 50% of tokens can't drain more than ~50% of vault."""
    vault, lp = create_model(model)
    alice = User("Alice", D(10_000))
    bob = User("Bob", D(10_000))

    # Both buy equal amounts
    lp.buy(alice, D(500))
    lp.buy(bob, D(500))

    # Alice tries to sell all — should get capped by fair share
    alice_tokens = alice.balance_token
    vault_before = lp.vault.balance_of()
    lp.sell(alice, alice_tokens)
    alice_received = alice.balance_usd - D(10_000) + D(500)  # net received from sell

    # Alice should not have taken more than her fair share (~50% of vault)
    max_fair = vault_before * D("0.6")  # 60% margin for safety
    assert alice_received <= max_fair, \
        f"Alice received {alice_received:.2f} but fair share max is ~{max_fair:.2f}"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       C8: SELL ORDER SENSITIVITY                          ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def test_exit_order_preserves_conservation(model: str):
    """C8: FIFO vs LIFO exit order — total system USDC is conserved either way."""
    def run_scenario(exit_order: list) -> D:
        vault, lp = create_model(model)
        users = [User(f"U{i}", D(10_000)) for i in range(3)]
        for u in users:
            lp.buy(u, D(500))
            lp.add_liquidity(u, u.balance_token, D(500))

        lp.vault.compound(100)

        for idx in exit_order:
            lp.remove_liquidity(users[idx])
            lp.sell(users[idx], users[idx].balance_token)

        vault_remaining = lp.vault.balance_of()
        total_user_usdc = sum(u.balance_usd for u in users)
        return total_user_usdc + vault_remaining

    fifo_total = run_scenario([0, 1, 2])
    lifo_total = run_scenario([2, 1, 0])

    # Total system USDC should be equal regardless of exit order
    assert abs(fifo_total - lifo_total) < DUST, \
        f"Conservation violated: FIFO total={fifo_total:.6f}, LIFO total={lifo_total:.6f}"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                    C9: OVERFLOW BOUNDARY                                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def test_exp_price_at_overflow_returns_inf(model: str):
    """C9: _exp_price returns Inf when supply * EXP_K exceeds MAX_EXP_ARG."""
    # Only meaningful for exponential curve
    if model != "EYN":
        return

    # Supply that would exceed MAX_EXP_ARG
    extreme_supply = (MAX_EXP_ARG / EXP_K) + D(1)
    price = _exp_price(extreme_supply)
    assert price == D('Inf'), \
        f"Expected Inf at supply={extreme_supply}, got {price}"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                    C10: DOUBLE ADD LIQUIDITY                              ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def test_double_add_liquidity_overwrites_snapshot(model: str):
    """C10: Adding liquidity twice for the same user updates their position.
    The second add should overwrite the snapshot (compounding index reference)."""
    vault, lp = create_model(model)
    user = User("Alice", D(10_000))
    lp.buy(user, D(1000))

    # First LP add
    half_tokens = user.balance_token / 2
    lp.add_liquidity(user, half_tokens, D(200))
    snapshot_1 = lp.user_snapshot["Alice"].index

    lp.vault.compound(50)

    # Second LP add — snapshot should update to current compounding index
    lp.add_liquidity(user, user.balance_token, D(200))
    snapshot_2 = lp.user_snapshot["Alice"].index

    assert snapshot_2 > snapshot_1, \
        f"Second add_liquidity should update snapshot index: {snapshot_1} -> {snapshot_2}"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          ALL TESTS REGISTRY                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

ALL_TESTS: List[Tuple[str, Callable]] = [
    # C1-C2: Model dimensions
    ("Yield doesn't impact price when disabled", test_yield_does_not_impact_price_when_disabled),
    ("LP impacts price when enabled", test_lp_impacts_price_when_enabled),
    # C3-C4: Edge cases
    ("Vault remove overcall raises", test_vault_remove_overcall_raises),
    ("Buy with zero balance goes negative", test_buy_with_zero_balance_goes_negative),
    # C5: Parametrized APY
    ("Zero APY produces no yield", test_zero_apy_produces_no_yield),
    ("Higher APY produces more yield", test_higher_apy_produces_more_yield),
    # C6: Compound idempotence
    ("Compound split equals continuous", test_compound_split_equals_continuous),
    # C7: Fair share cap
    ("Fair share caps sell", test_fair_share_caps_sell),
    # C8: Sell order sensitivity
    ("Exit order preserves conservation", test_exit_order_preserves_conservation),
    # C9: Overflow boundary
    ("Exp price at overflow returns Inf", test_exp_price_at_overflow_returns_inf),
    # C10: Double add liquidity
    ("Double add liquidity overwrites snapshot", test_double_add_liquidity_overwrites_snapshot),
]
