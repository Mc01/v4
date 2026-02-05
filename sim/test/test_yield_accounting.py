"""
╔═══════════════════════════════════════════════════════════════════════════╗
║            CRITICAL TEST: Buy USDC Double-Counting in LP Withdrawal      ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  HYPOTHESIS: remove_liquidity() adds buy_usdc_yield to LP withdrawal,    ║
║  but this yield belongs to token holders (via price), not LPs directly.  ║
║                                                                           ║
║  BUG LOCATION: core.py lines 605-606                                     ║
║    buy_usdc_yield_full = buy_usdc_principal * (delta - 1)                ║
║    total_usdc_full = usd_amount_full + buy_usdc_yield_full <-- WRONG!    ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import create_model, User, Vault, LP, DUST


def test_lp_only_user_should_get_exact_yield():
    """
    SCENARIO: User buys tokens, then LPs with ALL tokens + matching USDC.
    
    The ONLY yield source should be the LP USDC (500 USDC).
    Yield on buy_usdc (500) should NOT be given again - it's inside the vault
    and already backing the user's tokens.
    
    Expected after 100 days @ 5%:
    - LP USDC yield = 500 * 0.013792 = 6.90 USDC
    - TOTAL USDC return = 500 + 6.90 = 506.90 USDC
    
    ACTUAL (with bug):
    - Returns ~513.79 USDC (adds yield on buy_usdc too)
    - Difference = 6.89 USDC = exactly the yield on buy_usdc!
    """
    print("\n" + "="*70)
    print("TEST: LP user should receive yield ONLY on LP USDC deposit")
    print("="*70)
    
    for model in ["CYN", "SYN"]:
        print(f"\n[{model}]")
        vault, lp = create_model(model)
        user = User("alice", D(2000))
        
        # Buy 500 USDC worth of tokens
        lp.buy(user, D(500))
        tokens_for_lp = user.balance_token
        print(f"  Buy: 500 USDC → {tokens_for_lp:.2f} tokens")
        
        # LP with ALL tokens + 500 matching USDC
        lp_usdc = D(500)
        lp.add_liquidity(user, tokens_for_lp, lp_usdc)
        print(f"  LP: {tokens_for_lp:.2f} tokens + {lp_usdc} USDC")
        
        # Vault now has 1000 USDC total (500 buy + 500 LP)
        vault_after_lp = vault.balance_of()
        print(f"  Vault balance: {vault_after_lp}")
        
        # Compound 100 days
        vault.compound(100)
        vault_after_compound = vault.balance_of()
        
        # Calculate expected values
        yield_factor = (D(1) + D("0.05") / D(365)) ** 100
        expected_vault = vault_after_lp * yield_factor
        
        print(f"  After compound: {vault_after_compound:.2f} (expected: {expected_vault:.2f})")
        
        # Track user USDC before remove
        user_usdc_before = user.balance_usd
        
        # Remove LP
        lp.remove_liquidity(user)
        usdc_received = user.balance_usd - user_usdc_before
        
        # Expected: Only yield on LP USDC (500)
        expected_lp_yield = lp_usdc * (yield_factor - 1)
        expected_usdc_return = lp_usdc + expected_lp_yield
        
        # What the bug gives: yield on LP + yield on buy_usdc
        buy_usdc_in_vault = D(500)
        buggy_extra_yield = buy_usdc_in_vault * (yield_factor - 1)
        buggy_expected = expected_usdc_return + buggy_extra_yield
        
        print(f"\n  ACTUAL USDC received: {usdc_received:.6f}")
        print(f"  EXPECTED (correct):   {expected_usdc_return:.6f}")
        print(f"  EXPECTED (with bug):  {buggy_expected:.6f}")
        print(f"  Difference from correct: {usdc_received - expected_usdc_return:.6f}")
        print(f"  Expected difference (buy_usdc yield): {buggy_extra_yield:.6f}")
        
        # The difference should match the buy_usdc yield if the bug exists
        diff_from_correct = usdc_received - expected_usdc_return
        if abs(diff_from_correct - buggy_extra_yield) < D("0.01"):
            print(f"\n  ❌ BUG CONFIRMED: LP is receiving yield on buy_usdc ({buggy_extra_yield:.4f})")
        else:
            print(f"\n  ✓ No buy_usdc yield leakage detected")
        
        # Check vault residual
        vault_remaining = vault.balance_of()
        print(f"  Vault remaining: {vault_remaining:.6f}")


def test_two_user_yield_accounting():
    """
    SCENARIO: Two users - one buys, one LPs
    
    User A: Buys 500 USDC of tokens
    User B: LPs 500 tokens + 500 USDC
    
    After compound, where should the yield go?
    - Yield on User A's 500: Should increase token value (price goes up)
    - Yield on User B's 500 LP USDC: Should go to User B directly
    
    TOTAL yield in vault = 1000 * 0.013792 = 13.79 USDC
    
    If User B removes LP first:
    - User B should get: 500 + 6.90 = 506.90 USDC
    - Vault should still have: 500 (buy principal) + 6.90 (yield for A)
    
    With bug:
    - User B gets: 506.90 + 6.90 = 513.79 (steals A's yield)
    - Vault has: 500 + 0 = 500 (A's yield was stolen!)
    """
    print("\n" + "="*70)
    print("TEST: Two users - yield should be separate for buyer vs LP")
    print("="*70)
    
    for model in ["CYN", "SYN"]:
        print(f"\n[{model}]")
        vault, lp = create_model(model)
        
        buyer = User("buyer", D(1000))
        lp_user = User("LPer", D(1000))
        
        # Buyer buys tokens
        lp.buy(buyer, D(500))
        buyer_tokens = buyer.balance_token
        print(f"  Buyer: 500 USDC → {buyer_tokens:.2f} tokens")
        
        # LP user buys THEN provides liquidity (needs tokens for LP)
        lp.buy(lp_user, D(500))
        lp_tokens = lp_user.balance_token
        lp.add_liquidity(lp_user, lp_tokens, D(500))
        print(f"  LPer: provides {lp_tokens:.2f} tokens + 500 USDC")
        
        # Total in vault: 500 (buyer) + 500 (LP buy) + 500 (LP deposit) = 1500
        vault_after = vault.balance_of()
        print(f"  Vault: {vault_after} USDC")
        
        # Compound
        vault.compound(100)
        yield_created = vault.balance_of() - vault_after
        print(f"  Yield created: {yield_created:.4f} USDC")
        
        # LP user removes first
        lp_usdc_before = lp_user.balance_usd
        lp.remove_liquidity(lp_user)
        lp_usdc_received = lp_user.balance_usd - lp_usdc_before
        
        vault_after_lp_exit = vault.balance_of()
        
        print(f"\n  LPer USDC received: {lp_usdc_received:.4f}")
        print(f"  Vault after LP exit: {vault_after_lp_exit:.4f}")
        
        # Now buyer sells
        buyer_usdc_before = buyer.balance_usd
        lp.sell(buyer, buyer_tokens)
        buyer_usdc_received = buyer.balance_usd - buyer_usdc_before
        
        vault_final = vault.balance_of()
        
        print(f"  Buyer USDC received: {buyer_usdc_received:.4f}")
        print(f"  Vault final: {vault_final:.4f}")
        
        total_withdrawn = lp_usdc_received + buyer_usdc_received
        total_deposited = D(1500)  # 500 + 500 + 500
        profit = total_withdrawn - total_deposited + vault_final
        
        print(f"\n  Total withdrawn: {total_withdrawn:.2f}")
        print(f"  Expected (deposits + yield): {total_deposited + yield_created:.2f}")
        
        # LPer's buy contribution also had 500 USDC, so:
        # Total principal = 1500
        # Yield should be distributed proportionally to PRINCIPAL
        lp_principal = D(1000)  # 500 buy + 500 LP USDC
        buyer_principal = D(500)
        total_principal = D(1500)
        
        expected_lp_yield = yield_created * (lp_principal / total_principal)
        expected_buyer_yield = yield_created * (buyer_principal / total_principal)
        
        print(f"\n  Expected LP yield (2/3 of {yield_created:.4f}): {expected_lp_yield:.4f}")
        print(f"  Expected Buyer yield (1/3): {expected_buyer_yield:.4f}")


if __name__ == "__main__":
    test_lp_only_user_should_get_exact_yield()
    test_two_user_yield_accounting()
    
    print("\n" + "="*70)
    print("CONCLUSION:")
    print("="*70)
    print("""
If the tests show that LP receives ~2x expected yield, the bug is confirmed:

  BUG: remove_liquidity() includes buy_usdc_yield in LP withdrawal
  
  FIX: Line 606 should be:
    total_usdc_full = usd_amount_full  # NOT including buy_usdc_yield!
  
  The buy_usdc yield is already in the vault and should be distributed
  via token price increase, not directly to LPs.
""")
