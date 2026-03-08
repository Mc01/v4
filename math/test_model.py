"""
Commonwealth Protocol - Model Test Suite

Tests all 16 models defined in MODELS.md:
- 4 curve types: Constant Product (C), Exponential (E), Sigmoid (S), Logarithmic (L)
- 2 variable dimensions: Yield -> Price (Y/N), LP -> Price (Y/N)
- 2 fixed invariants: Token Inflation = always yes, Buy/Sell impacts price = always yes

Usage:
    python test_model.py                  # Compare all 16 models (single user)
    python test_model.py CYN              # Detailed scenarios for one model
    python test_model.py CYN,EYN,SYN      # Compare specific models
    python test_model.py --multi CYN      # Multi-user scenario for one model
    python test_model.py --bank CYN       # Bank run scenario for one model
"""
import argparse
import math
import sys
from decimal import Decimal as D
from typing import Dict, Optional
from enum import Enum

# =============================================================================
# Constants
# =============================================================================

K = D(1_000)
B = D(1_000_000_000)

# Test environment constants (see TEST.md)
EXPOSURE_FACTOR = 100 * K
CAP = 1 * B
VIRTUAL_LIMIT = 100 * K

# Vault
VAULT_APY = D(5) / D(100)

# Curve-specific constants (tuned for ~500 USDC test buys)
EXP_BASE_PRICE = 1.0
EXP_K = 0.0002           # 500 USDC -> ~477 tokens

SIG_MAX_PRICE = 2.0
SIG_K = 0.001             # 500 USDC -> ~450 tokens
SIG_MIDPOINT = 0.0

LOG_BASE_PRICE = 1.0
LOG_K = 0.01              # 500 USDC -> ~510 tokens

# =============================================================================
# Enums & Model Registry
# =============================================================================

class CurveType(Enum):
    CONSTANT_PRODUCT = "C"
    EXPONENTIAL = "E"
    SIGMOID = "S"
    LOGARITHMIC = "L"

CURVE_NAMES = {
    CurveType.CONSTANT_PRODUCT: "Constant Product",
    CurveType.EXPONENTIAL: "Exponential",
    CurveType.SIGMOID: "Sigmoid",
    CurveType.LOGARITHMIC: "Logarithmic",
}

MODELS = {}
for curve_code, curve_type in [("C", CurveType.CONSTANT_PRODUCT), ("E", CurveType.EXPONENTIAL),
                                ("S", CurveType.SIGMOID), ("L", CurveType.LOGARITHMIC)]:
    for yield_code, yield_price in [("Y", True), ("N", False)]:
        for lp_code, lp_price in [("Y", True), ("N", False)]:
            codename = f"{curve_code}{yield_code}{lp_code}"
            MODELS[codename] = {
                "curve": curve_type,
                "yield_impacts_price": yield_price,
                "lp_impacts_price": lp_price,
            }

# =============================================================================
# ANSI Colors
# =============================================================================

class Color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'
    STATS = '\033[90m'
    END = '\033[0m'

# =============================================================================
# Core Classes
# =============================================================================

class User:
    def __init__(self, name: str, usd: D = D(0), token: D = D(0)):
        self.name = name
        self.balance_usd = usd
        self.balance_token = token

class CompoundingSnapshot:
    def __init__(self, value: D, index: D):
        self.value = value
        self.index = index

class Vault:
    def __init__(self):
        self.apy = VAULT_APY
        self.balance_usd = D(0)
        self.compounding_index = D(1.0)
        self.snapshot: Optional[CompoundingSnapshot] = None
        self.compounds = 0

    def balance_of(self) -> D:
        if self.snapshot is None:
            return self.balance_usd
        return self.snapshot.value * (self.compounding_index / self.snapshot.index)

    def add(self, value: D):
        self.snapshot = CompoundingSnapshot(value + self.balance_of(), self.compounding_index)
        self.balance_usd = self.balance_of()

    def remove(self, value: D):
        if self.snapshot is None:
            raise Exception("Nothing staked!")
        self.snapshot = CompoundingSnapshot(self.balance_of() - value, self.compounding_index)
        self.balance_usd = self.balance_of()

    def compound(self, days: int):
        for _ in range(days):
            self.compounding_index *= D(1) + (self.apy / D(365))
        self.compounds += days

class UserSnapshot:
    def __init__(self, index: D):
        self.index = index

# =============================================================================
# Integral Curve Math (float-based for exp/log/trig)
# =============================================================================

def _exp_integral(a: float, b: float) -> float:
    """Integral of base * e^(k*x) from a to b."""
    # Overflow protection: math.exp() overflows around x > 709
    MAX_EXP_ARG = 700
    exp_b_arg = EXP_K * b
    exp_a_arg = EXP_K * a
    
    if exp_b_arg > MAX_EXP_ARG:
        return float('inf')  # Cost would be infinite, signal to bisection
    
    return (EXP_BASE_PRICE / EXP_K) * (math.exp(exp_b_arg) - math.exp(exp_a_arg))

def _exp_price(s: float) -> float:
    MAX_EXP_ARG = 700
    if EXP_K * s > MAX_EXP_ARG:
        return float('inf')
    return EXP_BASE_PRICE * math.exp(EXP_K * s)

def _sig_integral(a: float, b: float) -> float:
    """Integral of max_p / (1 + e^(-k*(x-m))) from a to b."""
    MAX_EXP_ARG = 700
    def F(x):
        arg = SIG_K * (x - SIG_MIDPOINT)
        if arg > MAX_EXP_ARG:
            # For large x, sigmoid ≈ max_price, so integral ≈ max_price * x
            return (SIG_MAX_PRICE / SIG_K) * arg  # Approximation that avoids overflow
        return (SIG_MAX_PRICE / SIG_K) * math.log(1 + math.exp(arg))
    return F(b) - F(a)

def _sig_price(s: float) -> float:
    return SIG_MAX_PRICE / (1 + math.exp(-SIG_K * (s - SIG_MIDPOINT)))

def _log_integral(a: float, b: float) -> float:
    """Integral of base * ln(1 + k*x) from a to b."""
    def F(x):
        u = 1 + LOG_K * x
        if u <= 0:
            return 0.0
        return LOG_BASE_PRICE * ((u * math.log(u) - u) / LOG_K + x)
    return F(b) - F(a)

def _log_price(s: float) -> float:
    val = 1 + LOG_K * s
    return LOG_BASE_PRICE * math.log(val) if val > 0 else 0.0

def _bisect_tokens_for_cost(supply: float, cost: float, integral_fn, max_tokens: float = 1e9) -> float:
    """Find n tokens where integral(supply, supply+n) = cost using bisection."""
    if cost <= 0:
        return 0.0
    lo, hi = 0.0, min(max_tokens, 1e8)
    # Expand hi if needed
    while integral_fn(supply, supply + hi) < cost and hi < max_tokens:
        hi *= 2
    for _ in range(100):
        mid = (lo + hi) / 2
        mid_cost = integral_fn(supply, supply + mid)
        if mid_cost < cost:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

# =============================================================================
# LP (Liquidity Pool) - Parameterized by model dimensions
# =============================================================================

class LP:
    def __init__(self, vault: Vault, curve_type: CurveType,
                 yield_impacts_price: bool, lp_impacts_price: bool):
        self.vault = vault
        self.curve_type = curve_type
        self.yield_impacts_price = yield_impacts_price
        self.lp_impacts_price = lp_impacts_price

        self.balance_usd = D(0)
        self.balance_token = D(0)
        self.minted = D(0)
        self.liquidity_token: Dict[str, D] = {}
        self.liquidity_usd: Dict[str, D] = {}
        self.user_buy_usdc: Dict[str, D] = {}
        self.user_snapshot: Dict[str, UserSnapshot] = {}
        self.buy_usdc = D(0)
        self.lp_usdc = D(0)

        # Constant product specific
        self.k: Optional[D] = None

    # ---- Dimension-aware USDC for price ----

    def _get_effective_usdc(self) -> D:
        """USDC amount used for price calculation, respecting yield/LP dimensions."""
        base = self.buy_usdc
        if self.lp_impacts_price:
            base += self.lp_usdc

        if self.yield_impacts_price:
            total_principal = self.buy_usdc + self.lp_usdc
            if total_principal > 0:
                compound_ratio = self.vault.balance_of() / total_principal
                return base * compound_ratio

        return base

    def _get_price_multiplier(self) -> D:
        """Multiplier for integral curve prices (effective_usdc / buy_usdc)."""
        if self.buy_usdc == 0:
            return D(1)
        return self._get_effective_usdc() / self.buy_usdc

    # ---- Constant Product helpers (TEST.md) ----

    def get_exposure(self) -> D:
        effective = min(self.minted * D(1000), CAP)
        exposure = EXPOSURE_FACTOR * (D(1) - effective / CAP)
        return max(D(0), exposure)

    def get_virtual_liquidity(self) -> D:
        base = CAP / EXPOSURE_FACTOR
        effective = min(self.buy_usdc, VIRTUAL_LIMIT)
        liquidity = base * (D(1) - effective / VIRTUAL_LIMIT)
        token_reserve = self._get_token_reserve()
        floor_liquidity = token_reserve - self._get_effective_usdc()
        return max(D(0), liquidity, floor_liquidity)

    def _get_token_reserve(self) -> D:
        exposure = self.get_exposure()
        return (CAP - self.minted) / exposure if exposure > 0 else CAP - self.minted

    def _get_usdc_reserve(self) -> D:
        return self._get_effective_usdc() + self.get_virtual_liquidity()

    def _update_k(self):
        self.k = self._get_token_reserve() * self._get_usdc_reserve()

    # ---- Price ----

    @property
    def price(self) -> D:
        if self.curve_type == CurveType.CONSTANT_PRODUCT:
            token_reserve = self._get_token_reserve()
            usdc_reserve = self._get_usdc_reserve()
            if token_reserve == 0:
                return D(1)
            return usdc_reserve / token_reserve
        else:
            # Integral curves: base curve at current supply * multiplier
            s = float(self.minted)
            if self.curve_type == CurveType.EXPONENTIAL:
                base = _exp_price(s)
            elif self.curve_type == CurveType.SIGMOID:
                base = _sig_price(s)
            elif self.curve_type == CurveType.LOGARITHMIC:
                base = _log_price(s)
            else:
                base = 1.0
            return D(str(base)) * self._get_price_multiplier()

    # ---- Fair share ----

    def _apply_fair_share_cap(self, requested: D, user_fraction: D) -> D:
        vault_available = self.vault.balance_of()
        fair_share = user_fraction * vault_available
        return min(requested, fair_share, vault_available)

    def _get_fair_share_scaling(self, requested_total_usdc: D, user_principal: D, total_principal: D) -> D:
        vault_available = self.vault.balance_of()
        if total_principal > 0 and requested_total_usdc > 0:
            fraction = user_principal / total_principal
            fair_share = fraction * vault_available
            return min(D(1), fair_share / requested_total_usdc, vault_available / requested_total_usdc)
        elif requested_total_usdc > 0:
            return min(D(1), vault_available / requested_total_usdc)
        return D(1)

    # ---- Core operations ----

    def mint(self, amount: D):
        if self.minted + amount > CAP:
            raise Exception("Cannot mint over cap")
        self.balance_token += amount
        self.minted += amount

    def rehypo(self):
        self.vault.add(self.balance_usd)
        self.balance_usd = D(0)

    def dehypo(self, amount: D):
        self.vault.remove(amount)
        self.balance_usd += amount

    def buy(self, user: User, amount: D):
        user.balance_usd -= amount
        self.balance_usd += amount

        if self.curve_type == CurveType.CONSTANT_PRODUCT:
            # x*y=k
            if self.k is None:
                self.k = self._get_token_reserve() * self._get_usdc_reserve()
            token_reserve = self._get_token_reserve()
            usdc_reserve = self._get_usdc_reserve()
            new_usdc = usdc_reserve + amount
            new_token = self.k / new_usdc
            out_amount = token_reserve - new_token
        else:
            # Integral curve
            mult = float(self._get_price_multiplier())
            effective_cost = float(amount) / mult if mult > 0 else float(amount)
            supply = float(self.minted)
            if self.curve_type == CurveType.EXPONENTIAL:
                n = _bisect_tokens_for_cost(supply, effective_cost, _exp_integral)
            elif self.curve_type == CurveType.SIGMOID:
                n = _bisect_tokens_for_cost(supply, effective_cost, _sig_integral)
            elif self.curve_type == CurveType.LOGARITHMIC:
                n = _bisect_tokens_for_cost(supply, effective_cost, _log_integral)
            else:
                n = float(amount)  # fallback
            out_amount = D(str(n))

        self.mint(out_amount)
        self.balance_token -= out_amount
        user.balance_token += out_amount
        self.buy_usdc += amount
        self.user_buy_usdc[user.name] = self.user_buy_usdc.get(user.name, D(0)) + amount
        self.rehypo()

        if self.curve_type == CurveType.CONSTANT_PRODUCT:
            self._update_k()

    def sell(self, user: User, amount: D):
        # Principal tracking before burn
        if self.minted > 0:
            principal_fraction = amount / self.minted
            principal_portion = self.buy_usdc * principal_fraction
        else:
            principal_portion = D(0)

        user_principal_reduction = min(
            self.user_buy_usdc.get(user.name, D(0)), principal_portion)

        user.balance_token -= amount

        if self.curve_type == CurveType.CONSTANT_PRODUCT:
            # x*y=k sell — calculate BEFORE decrementing minted
            if self.k is None:
                self.k = self._get_token_reserve() * self._get_usdc_reserve()
            token_reserve = self._get_token_reserve()
            usdc_reserve = self._get_usdc_reserve()
            new_token = token_reserve + amount
            new_usdc = self.k / new_token
            raw_out = usdc_reserve - new_usdc
            self.minted -= amount  # Decrement AFTER using reserves
        else:
            # Integral curves: safe to decrement first (they reconstruct supply_before)
            self.minted -= amount
            supply_after = float(self.minted)
            supply_before = supply_after + float(amount)
            if self.curve_type == CurveType.EXPONENTIAL:
                base_return = _exp_integral(supply_after, supply_before)
            elif self.curve_type == CurveType.SIGMOID:
                base_return = _sig_integral(supply_after, supply_before)
            elif self.curve_type == CurveType.LOGARITHMIC:
                base_return = _log_integral(supply_after, supply_before)
            else:
                base_return = float(amount)
            raw_out = D(str(base_return)) * self._get_price_multiplier()

        # Fair share cap
        original_minted = self.minted + amount
        if original_minted == 0:
            out_amount = min(raw_out, self.vault.balance_of())
        else:
            user_fraction = amount / original_minted
            out_amount = self._apply_fair_share_cap(raw_out, user_fraction)

        self.buy_usdc -= principal_portion
        if user.name in self.user_buy_usdc:
            self.user_buy_usdc[user.name] -= user_principal_reduction
            if self.user_buy_usdc[user.name] <= D(0):
                del self.user_buy_usdc[user.name]

        self.dehypo(out_amount)
        self.balance_usd -= out_amount
        user.balance_usd += out_amount

        if self.curve_type == CurveType.CONSTANT_PRODUCT:
            self._update_k()

    def add_liquidity(self, user: User, token_amount: D, usd_amount: D):
        user.balance_token -= token_amount
        user.balance_usd -= usd_amount
        self.balance_token += token_amount
        self.balance_usd += usd_amount
        self.lp_usdc += usd_amount
        self.rehypo()

        if self.curve_type == CurveType.CONSTANT_PRODUCT:
            self._update_k()

        self.user_snapshot[user.name] = UserSnapshot(self.vault.compounding_index)
        self.liquidity_token[user.name] = self.liquidity_token.get(user.name, D(0)) + token_amount
        self.liquidity_usd[user.name] = self.liquidity_usd.get(user.name, D(0)) + usd_amount

    def remove_liquidity(self, user: User):
        token_deposit = self.liquidity_token[user.name]
        usd_deposit = self.liquidity_usd[user.name]
        buy_usdc_principal = self.user_buy_usdc.get(user.name, D(0))

        delta = self.vault.compounding_index / self.user_snapshot[user.name].index

        # LP USDC yield
        usd_yield = usd_deposit * (delta - D(1))
        usd_amount_full = usd_deposit + usd_yield

        # Token inflation (fixed invariant: always yes)
        token_yield_full = token_deposit * (delta - D(1))

        # Buy USDC yield
        buy_usdc_yield_full = buy_usdc_principal * (delta - D(1))
        total_usdc_full = usd_amount_full + buy_usdc_yield_full

        # Fair share scaling
        principal = usd_deposit + buy_usdc_principal
        total_principal = self.lp_usdc + self.buy_usdc
        scaling_factor = self._get_fair_share_scaling(total_usdc_full, principal, total_principal)

        total_usdc = total_usdc_full * scaling_factor
        token_yield = token_yield_full * scaling_factor
        token_amount = token_deposit + token_yield
        
        # Calculate actual yield being withdrawn (for accounting fix)
        buy_usdc_yield_withdrawn = buy_usdc_yield_full * scaling_factor
        lp_usdc_yield_withdrawn = usd_yield * scaling_factor

        # Mint inflation tokens
        self.mint(token_yield)

        # Withdraw USDC
        self.dehypo(total_usdc)
        
        # Reduce lp_usdc by principal + yield withdrawn to keep compound_ratio accurate
        lp_usdc_reduction = usd_deposit + min(lp_usdc_yield_withdrawn, max(D(0), self.lp_usdc - usd_deposit))
        self.lp_usdc -= lp_usdc_reduction
        
        # Reduce buy_usdc by yield withdrawn to keep compound_ratio accurate
        if buy_usdc_yield_withdrawn > 0:
            self.buy_usdc -= min(buy_usdc_yield_withdrawn, self.buy_usdc)

        self.balance_token -= token_amount
        self.balance_usd -= total_usdc
        user.balance_token += token_amount
        user.balance_usd += total_usdc

        del self.liquidity_token[user.name]
        del self.liquidity_usd[user.name]
        
        # Update k after liquidity change
        if self.curve_type == CurveType.CONSTANT_PRODUCT:
            self._update_k()

    # ---- Pretty printing ----

    def print_stats(self, label: str = "Stats"):
        C = Color
        print(f"\n{C.CYAN}  ┌─ {label} ─────────────────────────────────────────{C.END}")

        if self.curve_type == CurveType.CONSTANT_PRODUCT:
            tr = self._get_token_reserve()
            ur = self._get_usdc_reserve()
            print(f"{C.CYAN}  │ Virtual Reserves:{C.END} token={C.YELLOW}{tr:.2f}{C.END}, usdc={C.YELLOW}{ur:.2f}{C.END}")
            k_val = f"{self.k:.2f}" if self.k else "None"
            print(f"{C.CYAN}  │ Bonding Curve k:{C.END} {C.YELLOW}{k_val}{C.END}")
            print(f"{C.CYAN}  │ Exposure:{C.END} {C.YELLOW}{self.get_exposure():.2f}{C.END}  Virtual Liq: {C.YELLOW}{self.get_virtual_liquidity():.2f}{C.END}")
        else:
            print(f"{C.CYAN}  │ Curve:{C.END} {C.YELLOW}{CURVE_NAMES[self.curve_type]}{C.END}  Multiplier: {C.YELLOW}{self._get_price_multiplier():.6f}{C.END}")

        total_principal = self.buy_usdc + self.lp_usdc
        buy_pct = (self.buy_usdc / total_principal * 100) if total_principal > 0 else D(0)
        lp_pct = (self.lp_usdc / total_principal * 100) if total_principal > 0 else D(0)
        print(f"{C.CYAN}  │ USDC Split:{C.END} buy={C.YELLOW}{self.buy_usdc:.2f}{C.END} ({buy_pct:.1f}%), lp={C.YELLOW}{self.lp_usdc:.2f}{C.END} ({lp_pct:.1f}%)")
        print(f"{C.CYAN}  │ Effective USDC:{C.END} {C.YELLOW}{self._get_effective_usdc():.2f}{C.END}")
        print(f"{C.CYAN}  │ Vault:{C.END} {C.YELLOW}{self.vault.balance_of():.2f}{C.END}  Index: {C.YELLOW}{self.vault.compounding_index:.6f}{C.END} ({self.vault.compounds}d)")
        print(f"{C.CYAN}  │ Price:{C.END} {C.GREEN}{self.price:.6f}{C.END}  Minted: {C.YELLOW}{self.minted:.2f}{C.END}")
        print(f"{C.CYAN}  └─────────────────────────────────────────────────────{C.END}\n")

# =============================================================================
# Model Factory
# =============================================================================

def create_model(codename: str):
    """Create a (Vault, LP) pair for the given model codename."""
    cfg = MODELS[codename]
    vault = Vault()
    lp = LP(vault, cfg["curve"], cfg["yield_impacts_price"], cfg["lp_impacts_price"])
    return vault, lp

def model_label(codename: str) -> str:
    cfg = MODELS[codename]
    curve = CURVE_NAMES[cfg["curve"]]
    yp = "Y" if cfg["yield_impacts_price"] else "N"
    lp = "Y" if cfg["lp_impacts_price"] else "N"
    return f"{codename} ({curve}, Yield→P={yp}, LP→P={lp})"

# =============================================================================
# Scenarios
# =============================================================================

def single_user_scenario(codename: str, verbose: bool = True,
                         user_initial_usd: D = 1 * K,
                         buy_amount: D = D(500),
                         compound_days: int = 100) -> dict:
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


def multi_user_scenario(codename: str, verbose: bool = True) -> dict:
    """4 users, staggered exits over 200 days."""
    vault, lp = create_model(codename)
    C = Color

    users_cfg = [
        ("Aaron", D(500), D(2000)),
        ("Bob", D(400), D(2000)),
        ("Carl", D(300), D(2000)),
        ("Dennis", D(600), D(2000)),
    ]
    users = {name: User(name.lower(), initial) for name, _, initial in users_cfg}
    compound_interval = 50

    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  MULTI-USER - {model_label(codename):^48}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")

    # All buy + add LP
    for name, buy_amt, _ in users_cfg:
        u = users[name]
        lp.buy(u, buy_amt)
        if verbose:
            print(f"[{name} Buy] {buy_amt} USDC -> {C.YELLOW}{u.balance_token:.2f}{C.END} tokens, Price: {C.GREEN}{lp.price:.6f}{C.END}")

        lp_tok = u.balance_token
        lp_usd = lp_tok * lp.price
        lp.add_liquidity(u, lp_tok, lp_usd)
        if verbose:
            print(f"[{name} LP] {lp_tok:.2f} tokens + {lp_usd:.2f} USDC")

    if verbose:
        lp.print_stats("After All Buy + LP")

    # Staggered exits: every 50 days one user exits
    results = {}
    for i, (name, buy_amt, initial) in enumerate(users_cfg):
        vault.compound(compound_interval)
        day = (i + 1) * compound_interval
        u = users[name]

        if verbose:
            print(f"\n{C.CYAN}=== {name} Exit (day {day}) ==={C.END}")

        usdc_before = u.balance_usd
        lp.remove_liquidity(u)
        usdc_from_lp = u.balance_usd - usdc_before

        tokens = u.balance_token
        usdc_before_sell = u.balance_usd
        lp.sell(u, tokens)
        usdc_from_sell = u.balance_usd - usdc_before_sell

        profit = u.balance_usd - initial
        results[name] = profit

        if verbose:
            gc = C.GREEN if profit > 0 else C.RED
            print(f"  LP USDC: {C.YELLOW}{usdc_from_lp:.2f}{C.END}, Sell: {C.YELLOW}{usdc_from_sell:.2f}{C.END}")
            print(f"  Final: {C.YELLOW}{u.balance_usd:.2f}{C.END}, Profit: {gc}{profit:.2f}{C.END}")

    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}=== FINAL SUMMARY ==={C.END}")
        total = D(0)
        for name, buy_amt, initial in users_cfg:
            p = results[name]
            total += p
            pc = C.GREEN if p > 0 else C.RED
            print(f"  {name:7s}: Invested {C.YELLOW}{buy_amt}{C.END}, Profit: {pc}{p:.2f}{C.END}")
        tc = C.GREEN if total > 0 else C.RED
        print(f"\n  {C.BOLD}Total profit: {tc}{total:.2f}{C.END}")
        print(f"  Vault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")

    return {"codename": codename, "profits": results, "vault": vault.balance_of()}


def bank_run_scenario(codename: str, verbose: bool = True) -> dict:
    """10 users, 365 days compound, all exit sequentially."""
    vault, lp = create_model(codename)
    C = Color

    users_data = [
        ("Aaron", D(500)), ("Bob", D(400)), ("Carl", D(300)), ("Dennis", D(600)),
        ("Eve", D(350)), ("Frank", D(450)), ("Grace", D(550)),
        ("Henry", D(250)), ("Iris", D(380)), ("Jack", D(420)),
    ]
    users = {name: User(name.lower(), 3 * K) for name, _ in users_data}

    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  BANK RUN - {model_label(codename):^50}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")

    # All buy + LP
    for name, buy_amt in users_data:
        u = users[name]
        lp.buy(u, buy_amt)
        lp_tok = u.balance_token
        lp_usd = lp_tok * lp.price
        lp.add_liquidity(u, lp_tok, lp_usd)
        if verbose:
            print(f"[{name}] Buy {buy_amt} + LP, Price: {C.GREEN}{lp.price:.6f}{C.END}")

    if verbose:
        lp.print_stats("After All Buy + LP")

    # Compound 365 days
    vault.compound(365)
    if verbose:
        print(f"{C.BLUE}--- Compound 365 days ---{C.END}")
        print(f"  Vault: {C.YELLOW}{vault.balance_of():.2f}{C.END}, Price: {C.GREEN}{lp.price:.6f}{C.END}")

    # All exit
    results = {}
    winners = 0
    losers = 0
    for name, buy_amt in users_data:
        u = users[name]
        lp.remove_liquidity(u)
        tokens = u.balance_token
        lp.sell(u, tokens)
        profit = u.balance_usd - 3 * K
        results[name] = profit
        if profit > 0:
            winners += 1
        else:
            losers += 1
        if verbose:
            pc = C.GREEN if profit > 0 else C.RED
            print(f"  {name:7s}: Invested {C.YELLOW}{buy_amt}{C.END}, Profit: {pc}{profit:.2f}{C.END}")

    total_profit = sum(results.values(), D(0))
    if verbose:
        print(f"\n{C.BOLD}Winners: {C.GREEN}{winners}{C.END}, Losers: {C.RED}{losers}{C.END}")
        tc = C.GREEN if total_profit > 0 else C.RED
        print(f"{C.BOLD}Total profit: {tc}{total_profit:.2f}{C.END}")
        print(f"Vault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")

    return {
        "codename": codename, "profits": results,
        "winners": winners, "losers": losers,
        "total_profit": total_profit, "vault": vault.balance_of(),
    }


def reverse_multi_user_scenario(codename: str, verbose: bool = True) -> dict:
    """4 users, staggered exits over 200 days — REVERSE exit order (last buyer exits first)."""
    vault, lp = create_model(codename)
    C = Color

    users_cfg = [
        ("Aaron", D(500), D(2000)),
        ("Bob", D(400), D(2000)),
        ("Carl", D(300), D(2000)),
        ("Dennis", D(600), D(2000)),
    ]
    users = {name: User(name.lower(), initial) for name, _, initial in users_cfg}
    compound_interval = 50

    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  REVERSE MULTI-USER - {model_label(codename):^40}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")

    # All buy + add LP (same order)
    for name, buy_amt, _ in users_cfg:
        u = users[name]
        lp.buy(u, buy_amt)
        if verbose:
            print(f"[{name} Buy] {buy_amt} USDC -> {C.YELLOW}{u.balance_token:.2f}{C.END} tokens, Price: {C.GREEN}{lp.price:.6f}{C.END}")

        lp_tok = u.balance_token
        lp_usd = lp_tok * lp.price
        lp.add_liquidity(u, lp_tok, lp_usd)
        if verbose:
            print(f"[{name} LP] {lp_tok:.2f} tokens + {lp_usd:.2f} USDC")

    if verbose:
        lp.print_stats("After All Buy + LP")

    # Staggered exits: REVERSE order (Dennis first, Aaron last)
    results = {}
    reversed_cfg = list(reversed(users_cfg))
    for i, (name, buy_amt, initial) in enumerate(reversed_cfg):
        vault.compound(compound_interval)
        day = (i + 1) * compound_interval
        u = users[name]

        if verbose:
            print(f"\n{C.CYAN}=== {name} Exit (day {day}) ==={C.END}")

        usdc_before = u.balance_usd
        lp.remove_liquidity(u)
        usdc_from_lp = u.balance_usd - usdc_before

        tokens = u.balance_token
        usdc_before_sell = u.balance_usd
        lp.sell(u, tokens)
        usdc_from_sell = u.balance_usd - usdc_before_sell

        profit = u.balance_usd - initial
        results[name] = profit

        if verbose:
            gc = C.GREEN if profit > 0 else C.RED
            print(f"  LP USDC: {C.YELLOW}{usdc_from_lp:.2f}{C.END}, Sell: {C.YELLOW}{usdc_from_sell:.2f}{C.END}")
            print(f"  Final: {C.YELLOW}{u.balance_usd:.2f}{C.END}, Profit: {gc}{profit:.2f}{C.END}")

    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}=== FINAL SUMMARY ==={C.END}")
        total = D(0)
        for name, buy_amt, initial in users_cfg:
            p = results[name]
            total += p
            pc = C.GREEN if p > 0 else C.RED
            print(f"  {name:7s}: Invested {C.YELLOW}{buy_amt}{C.END}, Profit: {pc}{p:.2f}{C.END}")
        tc = C.GREEN if total > 0 else C.RED
        print(f"\n  {C.BOLD}Total profit: {tc}{total:.2f}{C.END}")
        print(f"  Vault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")

    return {"codename": codename, "profits": results, "vault": vault.balance_of()}


def reverse_bank_run_scenario(codename: str, verbose: bool = True) -> dict:
    """10 users, 365 days compound, all exit sequentially — REVERSE order (last buyer exits first)."""
    vault, lp = create_model(codename)
    C = Color

    users_data = [
        ("Aaron", D(500)), ("Bob", D(400)), ("Carl", D(300)), ("Dennis", D(600)),
        ("Eve", D(350)), ("Frank", D(450)), ("Grace", D(550)),
        ("Henry", D(250)), ("Iris", D(380)), ("Jack", D(420)),
    ]
    users = {name: User(name.lower(), 3 * K) for name, _ in users_data}

    if verbose:
        print(f"\n{C.BOLD}{C.HEADER}{'='*70}{C.END}")
        print(f"{C.BOLD}{C.HEADER}  REVERSE BANK RUN - {model_label(codename):^42}{C.END}")
        print(f"{C.BOLD}{C.HEADER}{'='*70}{C.END}\n")

    # All buy + LP (same order)
    for name, buy_amt in users_data:
        u = users[name]
        lp.buy(u, buy_amt)
        lp_tok = u.balance_token
        lp_usd = lp_tok * lp.price
        lp.add_liquidity(u, lp_tok, lp_usd)
        if verbose:
            print(f"[{name}] Buy {buy_amt} + LP, Price: {C.GREEN}{lp.price:.6f}{C.END}")

    if verbose:
        lp.print_stats("After All Buy + LP")

    # Compound 365 days
    vault.compound(365)
    if verbose:
        print(f"{C.BLUE}--- Compound 365 days ---{C.END}")
        print(f"  Vault: {C.YELLOW}{vault.balance_of():.2f}{C.END}, Price: {C.GREEN}{lp.price:.6f}{C.END}")

    # All exit — REVERSE order (Jack first, Aaron last)
    results = {}
    winners = 0
    losers = 0
    for name, buy_amt in reversed(users_data):
        u = users[name]
        lp.remove_liquidity(u)
        tokens = u.balance_token
        lp.sell(u, tokens)
        profit = u.balance_usd - 3 * K
        results[name] = profit
        if profit > 0:
            winners += 1
        else:
            losers += 1
        if verbose:
            pc = C.GREEN if profit > 0 else C.RED
            print(f"  {name:7s}: Invested {C.YELLOW}{buy_amt}{C.END}, Profit: {pc}{profit:.2f}{C.END}")

    total_profit = sum(results.values(), D(0))
    if verbose:
        print(f"\n{C.BOLD}Winners: {C.GREEN}{winners}{C.END}, Losers: {C.RED}{losers}{C.END}")
        tc = C.GREEN if total_profit > 0 else C.RED
        print(f"{C.BOLD}Total profit: {tc}{total_profit:.2f}{C.END}")
        print(f"Vault remaining: {C.YELLOW}{vault.balance_of():.2f}{C.END}")

    return {
        "codename": codename, "profits": results,
        "winners": winners, "losers": losers,
        "total_profit": total_profit, "vault": vault.balance_of(),
    }

# =============================================================================
# Comparison Output
# =============================================================================

def run_comparison(codenames: list[str]):
    """Run all scenarios for each model and print comprehensive comparison table."""
    C = Color
    all_results = []
    
    print(f"\n{C.DIM}Running scenarios...{C.END}", end="", flush=True)
    
    for code in codenames:
        single_r = single_user_scenario(code, verbose=False)
        multi_r = multi_user_scenario(code, verbose=False)
        bank_r = bank_run_scenario(code, verbose=False)
        rmulti_r = reverse_multi_user_scenario(code, verbose=False)
        rbank_r = reverse_bank_run_scenario(code, verbose=False)
        all_results.append({
            "codename": code,
            "single": single_r,
            "multi": multi_r,
            "bank": bank_r,
            "rmulti": rmulti_r,
            "rbank": rbank_r,
        })
        print(f"{C.DIM}.{C.END}", end="", flush=True)
    
    print(f"\r{' ' * 40}\r", end="")  # Clear progress line

    # Header
    print(f"\n{C.BOLD}{C.HEADER}{'='*175}{C.END}")
    print(f"{C.BOLD}{C.HEADER}  MODEL COMPARISON - All Scenarios (FIFO vs LIFO){C.END}")
    print(f"{C.BOLD}{C.HEADER}{'='*175}{C.END}\n")

    # Short curve names
    SHORT_CURVE = {
        CurveType.CONSTANT_PRODUCT: "CP",
        CurveType.EXPONENTIAL: "Exp",
        CurveType.SIGMOID: "Sig",
        CurveType.LOGARITHMIC: "Log",
    }

    # Column headers - V = Vault after each scenario
    print(f"  {C.BOLD}{'Model':<6} {'Crv':<3}  │ {'S':>6} │ {'M+':>6} {'M-':>6} {'#':>2} {'V':>5} │ {'B+':>6} {'B-':>7} {'#':>2} {'V':>5} │ {'RM+':>6} {'RM-':>6} {'#':>2} {'V':>5} │ {'RB+':>6} {'RB-':>7} {'#':>2} {'V':>5}{C.END}")
    print(f"  {'─'*6} {'─'*3}  │ {'─'*6} │ {'─'*6} {'─'*6} {'─'*2} {'─'*5} │ {'─'*6} {'─'*7} {'─'*2} {'─'*5} │ {'─'*6} {'─'*6} {'─'*2} {'─'*5} │ {'─'*6} {'─'*7} {'─'*2} {'─'*5}")

    for r in all_results:
        code = r["codename"]
        cfg = MODELS[code]
        curve = SHORT_CURVE[cfg["curve"]]
        
        # Single user profit
        single_profit = r["single"]["profit"]
        single_color = C.GREEN if single_profit > 0 else C.RED
        
        # Helper to compute profits/losses/losers
        def calc_stats(profits_dict):
            gains = sum(p for p in profits_dict.values() if p > 0)
            losses = sum(p for p in profits_dict.values() if p < 0)
            losers = sum(1 for p in profits_dict.values() if p < 0)
            return gains, losses, losers
        
        # Multi (FIFO)
        m_gains, m_losses, m_losers = calc_stats(r["multi"]["profits"])
        m_vault = r["multi"]["vault"]
        mv_color = C.GREEN if m_vault == 0 else C.YELLOW
        
        # Bank (FIFO)
        b_gains, b_losses, b_losers = calc_stats(r["bank"]["profits"])
        b_vault = r["bank"]["vault"]
        bv_color = C.GREEN if b_vault == 0 else C.YELLOW
        
        # RMulti (LIFO)
        rm_gains, rm_losses, rm_losers = calc_stats(r["rmulti"]["profits"])
        rm_vault = r["rmulti"]["vault"]
        rmv_color = C.GREEN if rm_vault == 0 else C.YELLOW
        
        # RBank (LIFO)
        rb_gains, rb_losses, rb_losers = calc_stats(r["rbank"]["profits"])
        rb_vault = r["rbank"]["vault"]
        rbv_color = C.GREEN if rb_vault == 0 else C.YELLOW
        
        print(f"  {C.BOLD}{code:<6}{C.END} {curve:<3}  │ "
              f"{single_color}{single_profit:>6.1f}{C.END} │ "
              f"{C.GREEN}{m_gains:>6.0f}{C.END} {C.RED}{m_losses:>6.0f}{C.END} {m_losers:>2} {mv_color}{m_vault:>5.0f}{C.END} │ "
              f"{C.GREEN}{b_gains:>6.0f}{C.END} {C.RED}{b_losses:>7.0f}{C.END} {b_losers:>2} {bv_color}{b_vault:>5.0f}{C.END} │ "
              f"{C.GREEN}{rm_gains:>6.0f}{C.END} {C.RED}{rm_losses:>6.0f}{C.END} {rm_losers:>2} {rmv_color}{rm_vault:>5.0f}{C.END} │ "
              f"{C.GREEN}{rb_gains:>6.0f}{C.END} {C.RED}{rb_losses:>7.0f}{C.END} {rb_losers:>2} {rbv_color}{rb_vault:>5.0f}{C.END}")

    print()
    
    # Legend
    print(f"  {C.DIM}S = Single user profit │ M = Multi (4 users, FIFO) │ B = Bank run (10 users, FIFO) │ RM/RB = Reverse (LIFO){C.END}")
    print(f"  {C.DIM}+ = profits, - = losses, # = losers, V = vault remaining │ Crv: CP/Exp/Sig/Log{C.END}")
    print()

# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Commonwealth Protocol - Model Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_model.py                    # Compare all 16 models (table view)
  python test_model.py CYN                # All scenarios for one model (verbose)
  python test_model.py CYN,EYN,SYN        # Compare specific models (table view)
  python test_model.py --single           # Single-user scenario for all models (verbose)
  python test_model.py --single CYN,EYN   # Single-user scenario for specific models (verbose)
  python test_model.py --multi            # Multi-user scenario for all models
  python test_model.py --multi CYN        # Multi-user scenario for one model
  python test_model.py --bank CYN,EYN     # Bank run scenario for specific models
  python test_model.py --rmulti           # Reverse multi-user (last buyer exits first)
  python test_model.py --rbank            # Reverse bank run (last buyer exits first)
"""
    )
    parser.add_argument(
        "models", nargs="?", default=None,
        help="Model code(s) to test, comma-separated (e.g., CYN or CYN,EYN,SYN). Default: all models."
    )
    parser.add_argument(
        "--single", action="store_true",
        help="Run single-user scenario (verbose output per model)"
    )
    parser.add_argument(
        "--multi", action="store_true",
        help="Run multi-user scenario"
    )
    parser.add_argument(
        "--bank", action="store_true",
        help="Run bank run scenario"
    )
    parser.add_argument(
        "--rmulti", action="store_true",
        help="Run reverse multi-user scenario (last buyer exits first)"
    )
    parser.add_argument(
        "--rbank", action="store_true",
        help="Run reverse bank run scenario (last buyer exits first)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed output for each model (only applies when running single model)"
    )

    args = parser.parse_args()

    # Parse model codes
    if args.models:
        codes = [c.strip().upper() for c in args.models.split(",")]
        # Validate
        for code in codes:
            if code not in MODELS:
                print(f"Unknown model: {code}")
                print(f"Available: {', '.join(sorted(MODELS.keys()))}")
                sys.exit(1)
    else:
        codes = list(MODELS.keys())

    # Determine which scenarios to run
    run_single = args.single
    run_multi = args.multi
    run_bank = args.bank
    run_rmulti = args.rmulti
    run_rbank = args.rbank

    # If no scenario flags specified, use smart defaults
    if not (run_single or run_multi or run_bank or run_rmulti or run_rbank):
        if len(codes) == 1:
            # Single model: run all scenarios with verbose output
            code = codes[0]
            single_user_scenario(code, verbose=True)
            multi_user_scenario(code, verbose=True)
            bank_run_scenario(code, verbose=True)
            reverse_multi_user_scenario(code, verbose=True)
            reverse_bank_run_scenario(code, verbose=True)
            sys.exit(0)
        else:
            # Multiple models: run comparison table
            run_comparison(codes)
            sys.exit(0)

    # Run requested scenarios
    if run_single:
        for code in codes:
            single_user_scenario(code, verbose=True)

    if run_multi:
        for code in codes:
            multi_user_scenario(code, verbose=True)

    if run_bank:
        for code in codes:
            bank_run_scenario(code, verbose=True)

    if run_rmulti:
        for code in codes:
            reverse_multi_user_scenario(code, verbose=True)

    if run_rbank:
        for code in codes:
            reverse_bank_run_scenario(code, verbose=True)