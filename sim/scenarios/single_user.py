"""
Single User Scenario

One user goes through the full protocol cycle:
1. Buy tokens with USDC
2. Add liquidity (tokens + USDC)
3. Wait for compounding
4. Remove liquidity
5. Sell tokens

Tests basic protocol flow and single-user profitability.
"""
from decimal import Decimal as D
from ..core import create_model, model_label, User, Color, K, SingleUserResult


def single_user_scenario(codename: str, verbose: bool = True,
                         user_initial_usd: D = 1 * K,
                         buy_amount: D = D(500),
                         compound_days: int = 100) -> SingleUserResult:
    """Run single user full cycle. Returns result dict."""
    vault, lp = create_model(codename)
    user = User("aaron", user_initial_usd)
    C = Color

    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  SINGLE USER - {model_label(codename):^50}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")
        print(f"{C.CYAN}[Initial]{C.END} USDC: {C.YELLOW}{user.balance_usd}{C.END}")
        lp.print_stats("Initial")

    # Buy
    lp.buy(user, buy_amount)
    price_after_buy = lp.price
    tokens_bought = user.balance_token
    if verbose:
        print(f"{C.BLUE}--- Buy {buy_amount} USDC ---{C.END}")
        print(f"  Got {C.YELLOW}{tokens_bought:.2f}{C.END} tokens, Price: {C.GREEN}{price_after_buy:.6f}{C.END}")
        lp.print_stats("After Buy")

    # Add liquidity
    lp_tokens = user.balance_token
    lp_usdc = lp_tokens * lp.price
    price_before_lp = lp.price
    lp.add_liquidity(user, lp_tokens, lp_usdc)
    price_after_lp = lp.price
    if verbose:
        print(f"{C.BLUE}--- Add Liquidity ({lp_tokens:.2f} tokens + {lp_usdc:.2f} USDC) ---{C.END}")
        print(f"  Price: {C.GREEN}{price_before_lp:.6f}{C.END} -> {C.GREEN}{price_after_lp:.6f}{C.END}")
        lp.print_stats("After LP")

    # Compound
    price_before_compound = lp.price
    vault.compound(compound_days)
    price_after_compound = lp.price
    if verbose:
        print(f"{C.BLUE}--- Compound {compound_days} days ---{C.END}")
        print(f"  Vault: {C.YELLOW}{vault.balance_of():.2f}{C.END}")
        print(f"  Price: {C.GREEN}{price_before_compound:.6f}{C.END} -> {C.GREEN}{price_after_compound:.6f}{C.END} ({C.GREEN}+{price_after_compound - price_before_compound:.6f}{C.END})")
        lp.print_stats(f"After {compound_days}d Compound")

    # Remove liquidity
    usdc_before = user.balance_usd
    lp.remove_liquidity(user)
    usdc_from_lp = user.balance_usd - usdc_before
    if verbose:
        gc = C.GREEN if usdc_from_lp > 0 else C.RED
        print(f"{C.BLUE}--- Remove Liquidity ---{C.END}")
        print(f"  USDC gained: {gc}{usdc_from_lp:.2f}{C.END}, Tokens: {C.YELLOW}{user.balance_token:.2f}{C.END}")
        lp.print_stats("After Remove LP")

    # Sell
    tokens_to_sell = user.balance_token
    usdc_before_sell = user.balance_usd
    lp.sell(user, tokens_to_sell)
    usdc_from_sell = user.balance_usd - usdc_before_sell
    if verbose:
        print(f"{C.BLUE}--- Sell {tokens_to_sell:.2f} tokens ---{C.END}")
        print(f"  Got {C.YELLOW}{usdc_from_sell:.2f}{C.END} USDC")
        lp.print_stats("After Sell")

    # Summary
    profit = user.balance_usd - user_initial_usd
    if verbose:
        pc = C.GREEN if profit > 0 else C.RED
        print(f"\n{C.BOLD}Final USDC: {C.YELLOW}{user.balance_usd:.2f}{C.END}")
        print(f"{C.BOLD}Profit: {pc}{profit:.2f}{C.END}")
        print(f"Vault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")

    return {
        "codename": codename,
        "tokens_bought": tokens_bought,
        "price_after_buy": price_after_buy,
        "price_after_lp": price_after_lp,
        "price_after_compound": price_after_compound,
        "final_usdc": user.balance_usd,
        "profit": profit,
        "vault_remaining": vault.balance_of(),
    }
