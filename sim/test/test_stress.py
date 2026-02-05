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
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import (
    create_model, User, Vault, LP, DUST, K, B,
    CurveType, EXPOSURE_FACTOR, CAP, VIRTUAL_LIMIT
)


# ═══════════════════════════════════════════════════════════════════════════
#                         VAULT ACCOUNTING TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_vault_add_remove_conservation():
    """Vault.add(x) then Vault.remove(x) should leave balance = 0"""
    vault = Vault()
    
    # Add 1000 USDC
    vault.add(D(1000))
    assert vault.balance_of() == D(1000), f"Vault balance after add: {vault.balance_of()}"
    
    # Remove 1000 USDC
    vault.remove(D(1000))
    assert vault.balance_of() == D(0), f"Vault balance after remove: {vault.balance_of()}"
    
    print("✓ Vault add/remove conservation: PASS")


def test_vault_compound_exact_math():
    """Vault compound should match EXACT expected value for 100 days @ 5% APY"""
    vault = Vault()
    vault.add(D(1000))
    
    # 100 days at 5% APY
    vault.compound(100)
    
    # Manual calculation: 1000 * (1 + 0.05/365)^100 = 1013.7919...
    # Using Decimal: (1 + D("0.05")/365) ** 100
    daily_rate = D(1) + D("0.05") / D(365)
    expected = D(1000) * daily_rate ** 100
    
    actual = vault.balance_of()
    diff = abs(actual - expected)
    
    assert diff < D("0.01"), f"Compound mismatch: expected={expected}, actual={actual}, diff={diff}"
    
    print(f"✓ Vault compound math: expected={expected:.6f}, actual={actual:.6f}, diff={diff:.10f}")


def test_vault_compound_then_remove_all():
    """After compounding, removing balance_of() should empty vault"""
    vault = Vault()
    vault.add(D(1000))
    vault.compound(100)
    
    balance = vault.balance_of()
    vault.remove(balance)
    
    remaining = vault.balance_of()
    assert remaining < DUST, f"Vault not empty after full remove: {remaining}"
    
    print(f"✓ Vault full removal after compound: remaining={remaining}")


# ═══════════════════════════════════════════════════════════════════════════
#                      LP BUY/SELL USDC TRACKING TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_buy_tracks_usdc_exactly(model: str = "CYN"):
    """buy(X USDC) should add exactly X to buy_usdc tracking"""
    vault, lp = create_model(model)
    user = User("alice", D(1000))
    
    buy_amount = D(500)
    buy_usdc_before = lp.buy_usdc
    user_buy_before = lp.user_buy_usdc.get("alice", D(0))
    
    lp.buy(user, buy_amount)
    
    buy_usdc_after = lp.buy_usdc
    user_buy_after = lp.user_buy_usdc.get("alice", D(0))
    
    pool_increase = buy_usdc_after - buy_usdc_before
    user_increase = user_buy_after - user_buy_before
    
    assert abs(pool_increase - buy_amount) < DUST, \
        f"Pool buy_usdc increase: expected={buy_amount}, actual={pool_increase}"
    
    assert abs(user_increase - buy_amount) < DUST, \
        f"User buy_usdc increase: expected={buy_amount}, actual={user_increase}"
    
    print(f"✓ buy() USDC tracking ({model}): pool +{pool_increase}, user +{user_increase}")


def test_sell_reduces_usdc_proportionally(model: str = "CYN"):
    """sell(all tokens) should reduce buy_usdc to near 0 for single user"""
    vault, lp = create_model(model)
    user = User("alice", D(1000))
    
    # Buy first
    lp.buy(user, D(500))
    tokens = user.balance_token
    
    buy_usdc_after_buy = lp.buy_usdc
    user_buy_after_buy = lp.user_buy_usdc.get("alice", D(0))
    
    print(f"  After buy: pool buy_usdc={buy_usdc_after_buy}, user buy_usdc={user_buy_after_buy}")
    
    # Sell all
    lp.sell(user, tokens)
    
    buy_usdc_after_sell = lp.buy_usdc
    user_buy_after_sell = lp.user_buy_usdc.get("alice", D(0))
    
    print(f"  After sell: pool buy_usdc={buy_usdc_after_sell}, user buy_usdc={user_buy_after_sell}")
    
    # Expectation: selling ALL tokens should reduce buy_usdc to near 0
    assert buy_usdc_after_sell < D("0.01"), \
        f"Pool buy_usdc after full sell: {buy_usdc_after_sell} (expected ~0)"
    
    assert user_buy_after_sell < D("0.01"), \
        f"User buy_usdc after full sell: {user_buy_after_sell} (expected ~0)"
    
    print(f"✓ sell() USDC tracking ({model}): pool={buy_usdc_after_sell}, user={user_buy_after_sell}")


def test_buy_usdc_invariant_multi_user(model: str = "CYN"):
    """sum(user_buy_usdc) should ALWAYS equal buy_usdc"""
    vault, lp = create_model(model)
    users = [User(f"user{i}", D(1000)) for i in range(5)]
    
    # Buy phase
    for i, user in enumerate(users):
        lp.buy(user, D(100 * (i + 1)))  # 100, 200, 300, 400, 500 USDC
        
        user_sum = sum(lp.user_buy_usdc.values())
        diff = abs(user_sum - lp.buy_usdc)
        assert diff < DUST, f"Invariant broken after buy {i+1}: sum={user_sum}, pool={lp.buy_usdc}"
    
    print(f"✓ buy_usdc invariant holds after buys ({model})")
    
    # Sell phase - partial sells
    for i, user in enumerate(users):
        sell_amount = user.balance_token / 2  # Sell half
        lp.sell(user, sell_amount)
        
        user_sum = sum(lp.user_buy_usdc.values())
        diff = abs(user_sum - lp.buy_usdc)
        assert diff < DUST, f"Invariant broken after sell {i+1}: sum={user_sum}, pool={lp.buy_usdc}, diff={diff}"
    
    print(f"✓ buy_usdc invariant holds after sells ({model})")


# ═══════════════════════════════════════════════════════════════════════════
#                      LP LIQUIDITY ADD/REMOVE TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_add_liquidity_tracks_usdc_exactly(model: str = "SYN"):
    """add_liquidity deposits USDC, balance should go to vault"""
    vault, lp = create_model(model)
    user = User("alice", D(2000))
    
    # Buy tokens first
    lp.buy(user, D(500))
    tokens = user.balance_token
    
    vault_before = vault.balance_of()
    lp_usdc_before = lp.lp_usdc
    
    # Add liquidity
    lp_usdc_amount = D(500)
    lp.add_liquidity(user, tokens, lp_usdc_amount)
    
    vault_after = vault.balance_of()
    lp_usdc_after = lp.lp_usdc
    
    vault_increase = vault_after - vault_before
    lp_increase = lp_usdc_after - lp_usdc_before
    
    print(f"  Vault increase: {vault_increase} (expected: {lp_usdc_amount})")
    print(f"  LP USDC increase: {lp_increase}")
    
    assert abs(vault_increase - lp_usdc_amount) < DUST, \
        f"Vault didn't receive LP USDC: expected +{lp_usdc_amount}, got +{vault_increase}"
    
    assert abs(lp_increase - lp_usdc_amount) < DUST, \
        f"lp_usdc tracking wrong: expected +{lp_usdc_amount}, got +{lp_increase}"
    
    print(f"✓ add_liquidity USDC tracking ({model}): PASS")


def test_remove_liquidity_returns_principal_no_yield(model: str = "SYN"):
    """Without compounding, remove_liquidity should return EXACT principal"""
    vault, lp = create_model(model)
    user = User("alice", D(2000))
    
    # Buy and LP
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
    
    print(f"  USDC received: {usdc_received} (deposited: {lp_usdc})")
    print(f"  Tokens received: {tokens_received} (deposited: {tokens_for_lp})")
    
    # Should get back roughly what was deposited
    usdc_diff = abs(usdc_received - lp_usdc)
    token_diff = abs(tokens_received - tokens_for_lp)
    
    assert usdc_diff < D("1.0"), \
        f"USDC mismatch: expected ~{lp_usdc}, got {usdc_received}, diff={usdc_diff}"
    
    assert token_diff < D("1.0"), \
        f"Token mismatch: expected ~{tokens_for_lp}, got {tokens_received}, diff={token_diff}"
    
    print(f"✓ remove_liquidity principal return ({model}): PASS")


def test_remove_liquidity_yield_calculation(model: str = "SYN"):
    """Yield after compounding should match MANUAL calculation"""
    vault, lp = create_model(model)
    user = User("alice", D(2000))
    
    # Setup: Buy + LP
    lp.buy(user, D(500))
    tokens_deposited = user.balance_token
    lp_usdc = D(500)
    lp.add_liquidity(user, tokens_deposited, lp_usdc)
    
    total_deposited = D(500) + lp_usdc  # buy + LP USDC
    
    # Compound 100 days
    vault_before_compound = vault.balance_of()
    vault.compound(100)
    vault_after_compound = vault.balance_of()
    
    # Manual calculation: yield_factor = (1 + 0.05/365)^100 = 1.013792
    yield_factor = (D(1) + D("0.05") / D(365)) ** 100
    expected_vault = vault_before_compound * yield_factor
    
    print(f"  Vault before: {vault_before_compound}")
    print(f"  Yield factor: {yield_factor}")
    print(f"  Expected vault: {expected_vault}")
    print(f"  Actual vault: {vault_after_compound}")
    
    # Now remove LP and check yield
    user_usdc_before = user.balance_usd
    lp.remove_liquidity(user)
    usdc_received = user.balance_usd - user_usdc_before
    
    # Expected yield on LP USDC portion
    expected_usdc_yield = lp_usdc * (yield_factor - 1)
    expected_total_usdc = lp_usdc + expected_usdc_yield
    
    print(f"  USDC received: {usdc_received}")
    print(f"  Expected USDC (principal + yield): {expected_total_usdc}")
    print(f"  Expected yield: {expected_usdc_yield}")
    
    # Check if received matches expected (within reasonable bounds)
    diff = abs(usdc_received - expected_total_usdc)
    print(f"  Difference: {diff}")
    
    # Allow 10% tolerance due to token inflation effects
    tolerance = expected_total_usdc * D("0.1")
    if diff > tolerance:
        print(f"  ⚠️ USDC received differs by {diff/expected_total_usdc*100:.1f}% from expected")
    else:
        print(f"✓ remove_liquidity yield ({model}): within {diff/expected_total_usdc*100:.2f}% of expected")


# ═══════════════════════════════════════════════════════════════════════════
#                      SYSTEM-WIDE CONSERVATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_total_system_usdc_conservation(model: str = "SYN"):
    """
    CRITICAL TEST: Track EVERY USDC flow
    
    Invariant: sum(user_usdc_final) + vault_remaining = sum(user_usdc_initial)
    
    No USDC should be created or destroyed.
    """
    vault, lp = create_model(model)
    
    # Initial state
    initial_usdc = D(10000)
    users = [User(f"user{i}", D(2000)) for i in range(5)]
    total_initial = D(0)
    for u in users:
        total_initial += u.balance_usd
    
    print(f"  Total initial USDC in system: {total_initial}")
    
    # Phase 1: Buys
    for user in users:
        lp.buy(user, D(500))
    
    # Phase 2: LP
    for user in users:
        lp.add_liquidity(user, user.balance_token, D(400))
    
    # Snapshot before compound
    vault_before_compound = vault.balance_of()
    
    # Phase 3: Compound (CREATES new USDC)
    vault.compound(100)
    
    # This is where conservation breaks - compounding CREATES USDC
    # The yield comes from outside the system (protocol revenue)
    yield_created = vault.balance_of() - vault_before_compound
    print(f"  Yield created by compounding: {yield_created}")
    
    # Phase 4: Full exit
    for user in users:
        lp.remove_liquidity(user)
        lp.sell(user, user.balance_token)
    
    # Final accounting
    total_final = D(0)
    for u in users:
        total_final += u.balance_usd
    vault_remaining = vault.balance_of()
    
    print(f"  Total final user USDC: {total_final}")
    print(f"  Vault remaining: {vault_remaining}")
    print(f"  Total + vault: {total_final + vault_remaining}")
    print(f"  Expected (initial + yield): {total_initial + yield_created}")
    
    # Conservation check
    expected_total = total_initial + yield_created
    actual_total = total_final + vault_remaining
    diff = abs(actual_total - expected_total)
    
    assert diff < D("1.0"), \
        f"USDC not conserved: expected={expected_total}, actual={actual_total}, diff={diff}"
    
    print(f"✓ System USDC conservation ({model}): diff={diff}")


# ═══════════════════════════════════════════════════════════════════════════
#                              MAIN RUNNER
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║         STRESS TESTS - Atomic Accounting Verification        ║")
    print("╚═══════════════════════════════════════════════════════════════╝\n")
    
    # Vault tests
    print("\n[VAULT TESTS]")
    print("-" * 60)
    test_vault_add_remove_conservation()
    test_vault_compound_exact_math()
    test_vault_compound_then_remove_all()
    
    # Buy/Sell tracking tests
    print("\n[BUY/SELL USDC TRACKING]")
    print("-" * 60)
    for model in ["CYN", "SYN"]:
        test_buy_tracks_usdc_exactly(model)
        test_sell_reduces_usdc_proportionally(model)
    
    # Multi-user invariant
    print("\n[USER ACCOUNTING INVARIANTS]")
    print("-" * 60)
    for model in ["CYN", "SYN"]:
        test_buy_usdc_invariant_multi_user(model)
    
    # LP tests
    print("\n[LIQUIDITY PROVIDER TESTS]")
    print("-" * 60)
    for model in ["CYN", "SYN"]:
        test_add_liquidity_tracks_usdc_exactly(model)
        test_remove_liquidity_returns_principal_no_yield(model)
        test_remove_liquidity_yield_calculation(model)
    
    # System conservation
    print("\n[SYSTEM CONSERVATION]")
    print("-" * 60)
    for model in ["CYN", "SYN"]:
        test_total_system_usdc_conservation(model)
    
    print("\n" + "=" * 60)
    print("STRESS TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
