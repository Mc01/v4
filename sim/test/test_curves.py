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

from ..core import create_model, User, DUST


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
    """Price should never go negative or zero"""
    vault, lp = create_model(model)
    user = User("alice", D(5000))
    
    lp.buy(user, D(2000))
    assert lp.price > D(0), f"Price not positive after buy: {lp.price}"
    
    lp.sell(user, user.balance_token)
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
]
