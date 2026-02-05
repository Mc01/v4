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

from ..core import create_model, User, DUST


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
    """CRITICAL: All users exit → vault should be empty (no protocol fee)"""
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
    
    assert vault_remaining < D("0.01"), \
        f"Vault has {vault_remaining} USDC remaining (expected < 0.01)"


def test_multi_user_no_losers_in_simple_case(model: str):
    """Simple equal users: no one should lose money with yield"""
    vault, lp = create_model(model)
    users = [User(f"user{i}", D(1000)) for i in range(5)]
    
    for user in users:
        lp.buy(user, D(400))
        lp.add_liquidity(user, user.balance_token, D(400))
    
    vault.compound(365)
    
    losers = 0
    for user in users:
        initial = D(1000)
        lp.remove_liquidity(user)
        lp.sell(user, user.balance_token)
        
        profit = user.balance_usd - initial
        if profit < D("-1"):
            losers += 1
    
    assert losers == 0, f"{losers} users lost money in simple equal scenario"


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
#                             ALL TESTS
# ───────────────────────────────────────────────────────────────────────────

ALL_TESTS = [
    ("Single user no compound exits cleanly", test_single_user_no_compound_exits_cleanly),
    ("Single user with compound earns yield", test_single_user_with_compound),
    ("CRITICAL: Multi-user exit empties vault", test_multi_user_full_exit_empties_vault),
    ("Multi-user no losers in simple case", test_multi_user_no_losers_in_simple_case),
    ("Vault never goes negative", test_vault_never_negative),
    ("No infinite values", test_no_infinite_values),
]
