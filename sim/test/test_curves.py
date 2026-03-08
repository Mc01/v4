"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    Curve Tests - Bonding Curve Correctness                ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Tests curve-specific behavior:                                           ║
║    - Price increases with buys                                            ║
║    - Price decreases with sells                                           ║
║    - Price stays positive                                                 ║
║    - Curve-specific characteristics (sigmoid ceiling, etc)               ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D

from ..core import create_model, User, _bisect_tokens_for_cost, _exp_integral


# ───────────────────────────────────────────────────────────────────────────
#                          PRICE MOVEMENT
# ───────────────────────────────────────────────────────────────────────────

def test_price_increases_on_buy(model: str):
    """Price should increase after a buy"""
    vault, lp = create_model(model)
    user = User("alice", D(2000))
    
    price_before = lp.price
    lp.buy(user, D(500))
    price_after = lp.price
    
    assert price_after > price_before, \
        f"Price didn't increase: {price_before} → {price_after}"


def test_price_decreases_on_sell(model: str):
    """Price should decrease after a sell"""
    vault, lp = create_model(model)
    user = User("alice", D(2000))
    
    lp.buy(user, D(1000))
    price_before = lp.price
    
    lp.sell(user, user.balance_token / 2)
    price_after = lp.price
    
    assert price_after < price_before, \
        f"Price didn't decrease: {price_before} → {price_after}"


def test_price_stays_positive(model: str):
    """Price should never go negative (zero allowed for log curves at empty supply)"""
    vault, lp = create_model(model)
    user = User("alice", D(5000))

    lp.buy(user, D(2000))
    assert lp.price > D(0), f"Price not positive after buy: {lp.price}"

    lp.sell(user, user.balance_token)
    if lp.curve_type.value == "L" or lp.curve_type.value == "P":
        # Logarithmic: price = base * ln(1 + k*supply). At supply=0, ln(1)=0.
        # Polynomial: price = base * k * supply^n. At supply=0, 0^n=0.
        assert lp.price >= D(0), f"Price went negative after sell: {lp.price}"
    else:
        assert lp.price > D(0), f"Price not positive after sell: {lp.price}"


# ───────────────────────────────────────────────────────────────────────────
#                        LP DOESN'T AFFECT PRICE
# ───────────────────────────────────────────────────────────────────────────

def test_add_liquidity_price_neutral(model: str):
    """Adding liquidity should not significantly affect price"""
    vault, lp = create_model(model)
    user = User("alice", D(5000))
    
    lp.buy(user, D(1000))
    price_before = lp.price
    
    lp.add_liquidity(user, user.balance_token / 2, D(500))
    price_after = lp.price
    
    price_change_pct = abs(price_after - price_before) / price_before
    assert price_change_pct < D("0.01"), \
        f"Price changed too much on LP: {price_change_pct:.2%}"


def test_remove_liquidity_price_neutral(model: str):
    """Removing liquidity should not significantly affect price"""
    vault, lp = create_model(model)
    user = User("alice", D(5000))
    
    lp.buy(user, D(1000))
    lp.add_liquidity(user, user.balance_token, D(800))
    
    price_before = lp.price
    lp.remove_liquidity(user)
    price_after = lp.price
    
    price_change_pct = abs(price_after - price_before) / price_before
    assert price_change_pct < D("0.01"), \
        f"Price changed too much on LP removal: {price_change_pct:.2%}"


# ───────────────────────────────────────────────────────────────────────────
#                        CURVE CHARACTERISTICS
# ───────────────────────────────────────────────────────────────────────────

def test_tokens_received_reasonable(model: str):
    """Tokens received for buy should be reasonable"""
    vault, lp = create_model(model)
    user = User("alice", D(1000))
    
    lp.buy(user, D(500))
    tokens = user.balance_token
    
    assert tokens > D("100"), f"Got too few tokens: {tokens}"
    assert tokens < D("10000"), f"Got too many tokens: {tokens}"


def test_usdc_received_reasonable(model: str):
    """USDC received for sell should be reasonable"""
    vault, lp = create_model(model)
    user = User("alice", D(2000))
    
    lp.buy(user, D(1000))
    tokens = user.balance_token
    usdc_before = user.balance_usd
    
    lp.sell(user, tokens)
    usdc_received = user.balance_usd - usdc_before
    
    assert usdc_received > D(500), f"Got too little USDC: {usdc_received}"
    assert usdc_received <= D(1000), f"Got more than deposited: {usdc_received}"


def test_sell_never_returns_negative(model: str):
    """Sell should never return negative USDC, even on a depleted curve (FIX 2)."""
    vault, lp = create_model(model)
    users = [User(f"user{i}", D(5000)) for i in range(5)]

    # All users buy, building up the curve
    for user in users:
        lp.buy(user, D(2000))

    # First 4 users sell everything — depletes the curve
    for user in users[:4]:
        lp.sell(user, user.balance_token)

    # Last user sells on the depleted curve
    usdc_before = users[4].balance_usd
    lp.sell(users[4], users[4].balance_token)
    usdc_received = users[4].balance_usd - usdc_before

    assert usdc_received >= D(0), \
        f"Sell returned negative USDC: {usdc_received}"


def test_sell_zero_tokens_noop(model: str):
    """Selling 0 tokens should not change any balances."""
    vault, lp = create_model(model)
    user = User("alice", D(1000))
    lp.buy(user, D(500))

    usdc_before = user.balance_usd
    tokens_before = user.balance_token
    vault_before = vault.balance_of()

    lp.sell(user, D(0))

    assert user.balance_usd == usdc_before, "USDC changed on zero sell"
    assert user.balance_token == tokens_before, "Tokens changed on zero sell"
    assert vault.balance_of() == vault_before, "Vault changed on zero sell"


def test_buy_near_cap(model: str):
    """Buying a large amount near CAP should not crash."""
    vault, lp = create_model(model)
    user = User("whale", D(1_000_000_000))

    # Buy increasingly large amounts — should not throw
    for amount in [D(1000), D(10_000), D(100_000)]:
        try:
            lp.buy(user, amount)
        except Exception as e:
            if "Cannot mint over cap" in str(e):
                break  # Expected when hitting cap
            raise

    assert user.balance_token > 0, "Should have received some tokens"


def test_bisect_zero_cost(model: str):
    """_bisect_tokens_for_cost with cost=0 should return 0 tokens."""
    result = _bisect_tokens_for_cost(D(0), D(0), _exp_integral)
    assert result == D(0), f"Expected 0 tokens for 0 cost, got {result}"


# ───────────────────────────────────────────────────────────────────────────
#                             ALL TESTS
# ───────────────────────────────────────────────────────────────────────────

ALL_TESTS = [
    ("Price increases on buy", test_price_increases_on_buy),
    ("Price decreases on sell", test_price_decreases_on_sell),
    ("Price stays positive", test_price_stays_positive),
    ("Add liquidity price neutral", test_add_liquidity_price_neutral),
    ("Remove liquidity price neutral", test_remove_liquidity_price_neutral),
    ("Tokens received reasonable", test_tokens_received_reasonable),
    ("USDC received reasonable", test_usdc_received_reasonable),
    ("Sell never returns negative", test_sell_never_returns_negative),
    ("Sell zero tokens is noop", test_sell_zero_tokens_noop),
    ("Buy near cap doesn't crash", test_buy_near_cap),
    ("Bisect zero cost returns zero", test_bisect_zero_cost),
]
