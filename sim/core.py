"""
Commonwealth Protocol - Core Infrastructure

Contains all core classes, constants, and utilities used by test_model.py and scenarios.
"""
import math
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
            # Active models: *YN (Yield->Price=Yes, LP->Price=No)
            # Archived: *YY, *NY, *NN (kept for backwards compatibility)
            is_deprecated = not (yield_price and not lp_price)
            MODELS[codename] = {
                "curve": curve_type,
                "yield_impacts_price": yield_price,
                "lp_impacts_price": lp_price,
                "deprecated": is_deprecated,
            }

# Active models (recommended for use)
ACTIVE_MODELS = [code for code, cfg in MODELS.items() if not cfg["deprecated"]]

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
    MAX_EXP_ARG = 700
    exp_b_arg = EXP_K * b
    exp_a_arg = EXP_K * a
    
    if exp_b_arg > MAX_EXP_ARG:
        return float('inf')
    
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
            return (SIG_MAX_PRICE / SIG_K) * arg
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
            if self.k is None:
                self.k = self._get_token_reserve() * self._get_usdc_reserve()
            token_reserve = self._get_token_reserve()
            usdc_reserve = self._get_usdc_reserve()
            new_usdc = usdc_reserve + amount
            new_token = self.k / new_usdc
            out_amount = token_reserve - new_token
        else:
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
                n = float(amount)
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
        if self.minted > 0:
            principal_fraction = amount / self.minted
            principal_portion = self.buy_usdc * principal_fraction
        else:
            principal_portion = D(0)

        user_principal_reduction = min(
            self.user_buy_usdc.get(user.name, D(0)), principal_portion)

        user.balance_token -= amount

        if self.curve_type == CurveType.CONSTANT_PRODUCT:
            if self.k is None:
                self.k = self._get_token_reserve() * self._get_usdc_reserve()
            token_reserve = self._get_token_reserve()
            usdc_reserve = self._get_usdc_reserve()
            new_token = token_reserve + amount
            new_usdc = self.k / new_token
            raw_out = usdc_reserve - new_usdc
            self.minted -= amount
        else:
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

        usd_yield = usd_deposit * (delta - D(1))
        usd_amount_full = usd_deposit + usd_yield

        token_yield_full = token_deposit * (delta - D(1))

        buy_usdc_yield_full = buy_usdc_principal * (delta - D(1))
        total_usdc_full = usd_amount_full + buy_usdc_yield_full

        principal = usd_deposit + buy_usdc_principal
        total_principal = self.lp_usdc + self.buy_usdc
        scaling_factor = self._get_fair_share_scaling(total_usdc_full, principal, total_principal)

        total_usdc = total_usdc_full * scaling_factor
        token_yield = token_yield_full * scaling_factor
        token_amount = token_deposit + token_yield
        
        buy_usdc_yield_withdrawn = buy_usdc_yield_full * scaling_factor
        lp_usdc_yield_withdrawn = usd_yield * scaling_factor

        self.mint(token_yield)

        self.dehypo(total_usdc)
        
        lp_usdc_reduction = usd_deposit + min(lp_usdc_yield_withdrawn, max(D(0), self.lp_usdc - usd_deposit))
        self.lp_usdc -= lp_usdc_reduction
        
        if buy_usdc_yield_withdrawn > 0:
            self.buy_usdc -= min(buy_usdc_yield_withdrawn, self.buy_usdc)

        self.balance_token -= token_amount
        self.balance_usd -= total_usdc
        user.balance_token += token_amount
        user.balance_usd += total_usdc

        del self.liquidity_token[user.name]
        del self.liquidity_usd[user.name]
        
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
    deprecated = " [archived]" if cfg["deprecated"] else ""
    return f"{codename} ({curve}, Yield→P={yp}, LP→P={lp}){deprecated}"
