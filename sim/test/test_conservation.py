"""
╔═══════════════════════════════════════════════════════════════════════════╗
║              Conservation Tests - USDC Accounting Verification            ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Verifies that USDC is conserved at each operation:                       ║
║    - buy: USDC goes to vault                                              ║
║    - sell: USDC comes from vault                                          ║
║    - add_liquidity: USDC goes to vault                                    ║
║    - remove_liquidity: USDC comes from vault                              ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D

from ..core import create_model, User, DUST


# ───────────────────────────────────────────────────────────────────────────
#                              BUY CONSERVATION
# ───────────────────────────────────────────────────────────────────────────

def test_buy_deposits_to_vault(model: str):
    """Buy should deposit exact USDC amount to vault"""
    vault, lp = create_model(model)
    user = User("alice", D(1000))
    
    buy_amount = D(500)
    vault_before = vault.balance_of()
    
    lp.buy(user, buy_amount)
    
    vault_after = vault.balance_of()
    vault_increase = vault_after - vault_before
    
    assert abs(vault_increase - buy_amount) < DUST, \
        f"Vault +{vault_increase}, expected +{buy_amount}"


def test_multiple_buys_accumulate(model: str):
    """Multiple buys should accumulate correctly in vault"""
    vault, lp = create_model(model)
    users = [User(f"user{i}", D(1000)) for i in range(5)]
    
    total_bought = D(0)
    vault_before = vault.balance_of()
    
    for user in users:
        amount = D(200)
        lp.buy(user, amount)
        total_bought += amount
    
    vault_increase = vault.balance_of() - vault_before
    
    assert abs(vault_increase - total_bought) < DUST, \
        f"Vault +{vault_increase}, expected +{total_bought}"


# ───────────────────────────────────────────────────────────────────────────
#                             SELL CONSERVATION
# ───────────────────────────────────────────────────────────────────────────

def test_sell_withdraws_from_vault(model: str):
    """Sell should withdraw USDC from vault to user"""
    vault, lp = create_model(model)
    user = User("alice", D(1000))
    
    lp.buy(user, D(500))
    tokens = user.balance_token
    
    vault_before = vault.balance_of()
    user_usdc_before = user.balance_usd
    
    lp.sell(user, tokens)
    
    usdc_received = user.balance_usd - user_usdc_before
    vault_decrease = vault_before - vault.balance_of()
    
    assert abs(usdc_received - vault_decrease) < DUST, \
        f"User got {usdc_received}, vault -{vault_decrease}"


def test_buy_then_sell_preserves_system(model: str):
    """Buy then immediate sell: system USDC should be conserved"""
    vault, lp = create_model(model)
    user = User("alice", D(1000))
    
    buy_amount = D(500)
    
    lp.buy(user, buy_amount)
    tokens = user.balance_token
    
    lp.sell(user, tokens)
    
    vault_balance = vault.balance_of()
    
    assert vault_balance < buy_amount * D("0.1"), \
        f"Vault has {vault_balance} (excessive - more than 10% slippage)"


# ───────────────────────────────────────────────────────────────────────────
#                         LIQUIDITY CONSERVATION
# ───────────────────────────────────────────────────────────────────────────

def test_add_liquidity_deposits_to_vault(model: str):
    """Add liquidity should deposit USDC to vault"""
    vault, lp = create_model(model)
    user = User("alice", D(2000))
    
    lp.buy(user, D(500))
    token_amount = user.balance_token
    usdc_amount = D(500)
    
    vault_before = vault.balance_of()
    
    lp.add_liquidity(user, token_amount, usdc_amount)
    
    vault_increase = vault.balance_of() - vault_before
    
    assert abs(vault_increase - usdc_amount) < DUST, \
        f"Vault +{vault_increase}, expected +{usdc_amount}"


def test_remove_liquidity_withdraws_from_vault(model: str):
    """Remove liquidity should withdraw USDC from vault"""
    vault, lp = create_model(model)
    user = User("alice", D(2000))
    
    lp.buy(user, D(500))
    lp.add_liquidity(user, user.balance_token, D(500))
    
    vault_before = vault.balance_of()
    user_usdc_before = user.balance_usd
    
    lp.remove_liquidity(user)
    
    usdc_received = user.balance_usd - user_usdc_before
    vault_decrease = vault_before - vault.balance_of()
    
    assert abs(usdc_received - vault_decrease) < DUST, \
        f"User got {usdc_received}, vault -{vault_decrease}"


# ───────────────────────────────────────────────────────────────────────────
#                             ALL TESTS
# ───────────────────────────────────────────────────────────────────────────

ALL_TESTS = [
    ("Buy deposits to vault", test_buy_deposits_to_vault),
    ("Multiple buys accumulate", test_multiple_buys_accumulate),
    ("Sell withdraws from vault", test_sell_withdraws_from_vault),
    ("Buy then sell preserves system", test_buy_then_sell_preserves_system),
    ("Add liquidity deposits to vault", test_add_liquidity_deposits_to_vault),
    ("Remove liquidity withdraws from vault", test_remove_liquidity_withdraws_from_vault),
]
