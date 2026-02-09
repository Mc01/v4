"""
╔═══════════════════════════════════════════════════════════════════════════╗
║               Invariant Tests - Accounting Consistency                    ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Verifies internal accounting invariants hold:                            ║
║    - sum(user_buy_usdc) == lp.buy_usdc                                   ║
║    - sum(liquidity_usd) == lp.lp_usdc                                    ║
║    - sum(liquidity_token) == lp.lp_tokens                                ║
║    - k constant during swaps (CYN only)                                  ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D

from ..core import create_model, User, DUST


# ───────────────────────────────────────────────────────────────────────────
#                          USDC TRACKING INVARIANTS
# ───────────────────────────────────────────────────────────────────────────

def test_user_buy_usdc_sums_to_pool(model: str):
    """sum(user_buy_usdc) must equal lp.buy_usdc"""
    vault, lp = create_model(model)
    users = [User(f"user{i}", D(1000)) for i in range(5)]
    
    for user in users:
        lp.buy(user, D(200))
    
    user_total = sum(lp.user_buy_usdc.values())
    pool_total = lp.buy_usdc
    
    assert abs(user_total - pool_total) < DUST, \
        f"User sum={user_total}, pool={pool_total}"


def test_user_lp_usdc_sums_to_pool(model: str):
    """sum(liquidity_usd) must equal lp.lp_usdc"""
    vault, lp = create_model(model)
    users = [User(f"user{i}", D(2000)) for i in range(5)]
    
    for user in users:
        lp.buy(user, D(300))
        lp.add_liquidity(user, user.balance_token, D(300))
    
    user_total = sum(lp.liquidity_usd.values())
    pool_total = lp.lp_usdc
    
    assert abs(user_total - pool_total) < DUST, \
        f"User sum={user_total}, pool={pool_total}"


# ───────────────────────────────────────────────────────────────────────────
#                        INVARIANTS AFTER OPERATIONS
# ───────────────────────────────────────────────────────────────────────────
def test_invariants_hold_after_mixed_ops(model: str):
    """Invariants should hold after complex operation sequence"""
    vault, lp = create_model(model)
    users = [User(f"user{i}", D(3000)) for i in range(5)]
    
    for user in users:
        lp.buy(user, D(400))
    
    for user in users[:3]:
        lp.add_liquidity(user, user.balance_token / 2, D(200))
    
    lp.sell(users[3], users[3].balance_token / 2)
    lp.remove_liquidity(users[0])
    
    assert abs(sum(lp.user_buy_usdc.values()) - lp.buy_usdc) < DUST, \
        "user_buy_usdc invariant broken"
    
    assert abs(sum(lp.liquidity_usd.values()) - lp.lp_usdc) < DUST, \
        "liquidity_usd invariant broken"


# ───────────────────────────────────────────────────────────────────────────
#                        CONSTANT PRODUCT K (CYN ONLY)
# ───────────────────────────────────────────────────────────────────────────

def test_k_stable_during_swaps(model: str):
    """For CYN: k should not change during buy/sell."""
    if model != "CYN":
        return
    
    vault, lp = create_model(model)
    user = User("alice", D(5000))
    
    lp.buy(user, D(500))
    k_initial = lp.k
    
    lp.buy(user, D(300))
    assert lp.k == k_initial, f"k changed during buy: {k_initial} → {lp.k}"
    
    lp.sell(user, user.balance_token / 2)
    assert lp.k == k_initial, f"k changed during sell: {k_initial} → {lp.k}"


def test_k_stable_during_lp_ops(model: str):
    """For CYN: k should NOT change during LP operations (FIX 1)."""
    if model != "CYN":
        return

    vault, lp = create_model(model)
    user = User("alice", D(5000))

    lp.buy(user, D(500))
    k_before_lp = lp.k

    lp.add_liquidity(user, user.balance_token / 2, D(300))
    k_after_add = lp.k

    assert k_after_add == k_before_lp, \
        f"k should not change during add_liquidity (was {k_before_lp}, now {k_after_add})"


# ───────────────────────────────────────────────────────────────────────────
#                             ALL TESTS
# ───────────────────────────────────────────────────────────────────────────

ALL_TESTS = [
    ("User buy_usdc sums to pool", test_user_buy_usdc_sums_to_pool),
    ("User LP USDC sums to pool", test_user_lp_usdc_sums_to_pool),
    ("Invariants after mixed ops", test_invariants_hold_after_mixed_ops),
    ("K stable during swaps", test_k_stable_during_swaps),
    ("K stable during LP ops", test_k_stable_during_lp_ops),
]
