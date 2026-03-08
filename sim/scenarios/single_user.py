"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                      Single-User Scenario                                 ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Tests the complete lifecycle for a single user:                          ║
║    1. Buy tokens                                                          ║
║    2. Add liquidity                                                       ║
║    3. Compound for 100 days                                               ║
║    4. Remove liquidity                                                    ║
║    5. Sell tokens                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, K, SingleUserResult
from ..formatter import Formatter


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         PUBLIC API                                        ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def single_user_scenario(codename: str, verbosity: int = 1,
                         user_initial_usd: D = 1 * K,
                         buy_amount: D = D(500),
                         compound_days: int = 100) -> SingleUserResult:
    """Run single user full lifecycle scenario."""
    vault, lp = create_model(codename)
    v = verbosity
    f = Formatter(v)
    f.set_lp(lp)
    
    user = User("alice", user_initial_usd)
    
    f.header("SINGLE USER", model_label(codename))

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                              Buy                                       │
    # └───────────────────────────────────────────────────────────────────────┘
    
    f.section("Entry Phase")
    
    price_before = lp.price
    lp.buy(user, buy_amount)
    price_after_buy = lp.price
    tokens_bought = user.balance_token
    
    f.buy(1, 1, "Alice", buy_amount, price_before, tokens_bought, price_after_buy)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                         Add Liquidity                                  │
    # └───────────────────────────────────────────────────────────────────────┘
    
    token_amount = user.balance_token
    usdc_amount = token_amount * lp.price
    lp.add_liquidity(user, token_amount, usdc_amount)
    price_after_lp = lp.price
    
    f.add_lp("Alice", token_amount, usdc_amount)
    f.stats("After Entry", lp, level=1)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                         Compound Period                                │
    # └───────────────────────────────────────────────────────────────────────┘
    
    vault_before = vault.balance_of()
    price_before_compound = lp.price
    vault.compound(compound_days)
    price_after_compound = lp.price
    
    f.compound(compound_days, vault_before, vault.balance_of(), price_before_compound, price_after_compound)
    f.stats("After Compound", lp, level=2)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                         Exit Phase                                     │
    # └───────────────────────────────────────────────────────────────────────┘
    
    f.section("Exit Phase")
    
    price_before_exit = lp.price
    usdc_before_lp = user.balance_usd
    lp.remove_liquidity(user)
    usdc_from_lp = user.balance_usd - usdc_before_lp
    tokens_after_lp = user.balance_token

    f.remove_lp("Alice", tokens_after_lp, usdc_from_lp)

    lp.sell(user, user.balance_token)
    price_after_sell = lp.price
    final_usdc = user.balance_usd
    profit = final_usdc - user_initial_usd
    roi = (profit / buy_amount) * 100
    
    f.exit(1, 1, "Alice", profit, price_before_exit, price_after_sell, roi=roi)
    f.stats("After Exit", lp, level=2)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                           Summary                                      │
    # └───────────────────────────────────────────────────────────────────────┘
    
    f.summary({"Alice": profit}, vault.balance_of(), title="SINGLE USER SUMMARY")

    return {
        "codename": codename,
        "tokens_bought": tokens_bought,
        "price_after_buy": price_after_buy,
        "price_after_lp": price_after_lp,
        "price_after_compound": price_after_compound,
        "final_usdc": final_usdc,
        "profit": profit,
        "vault_remaining": vault.balance_of(),
    }
