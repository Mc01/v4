"""
Commonwealth Protocol - Core Infrastructure

Contains all core classes, constants, and utilities used by run_model.py and scenarios.
"""
from decimal import Decimal as D
from typing import Callable, Dict, List, Optional, Tuple, TypedDict
from dataclasses import dataclass
from enum import Enum


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                              CONSTANTS                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

K = D(1_000)
B = D(1_000_000_000)

# Test environment bounds (see TEST.md)
EXPOSURE_FACTOR = 100 * K
CAP = 1 * B                # Maximum token supply
VIRTUAL_LIMIT = 100 * K    # Threshold where virtual liquidity tapers to zero

# Dust threshold: residuals below this from accumulated rounding are treated as zero
DUST = D("1E-12")

# Vault yield
VAULT_APY = D(5) / D(100)

# Token inflation for LPs: scales how much of vault APY is mirrored as token minting.
# 1.0 = same as vault APY (default), 0.0 = no token inflation.
TOKEN_INFLATION_FACTOR = D(1)

@dataclass(frozen=True)
class CurveConfig:
    """Immutable curve parameters. One instance per curve type."""
    base_price: D
    k: D
    max_price: D = D(0)    # Only used by sigmoid
    midpoint: D = D(0)     # Only used by sigmoid

# Calibrated for ~500 USDC test buys
EXP_CFG = CurveConfig(base_price=D(1), k=D("0.0002"))          # → ~477 tokens
SIG_CFG = CurveConfig(base_price=D(1), k=D("0.001"),
                      max_price=D(2), midpoint=D(0))            # → ~450 tokens
LOG_CFG = CurveConfig(base_price=D(1), k=D("0.01"))            # → ~510 tokens

# Backward-compatible aliases (used by curve functions and external imports)
EXP_BASE_PRICE, EXP_K = EXP_CFG.base_price, EXP_CFG.k
SIG_MAX_PRICE, SIG_K, SIG_MIDPOINT = SIG_CFG.max_price, SIG_CFG.k, SIG_CFG.midpoint
LOG_BASE_PRICE, LOG_K = LOG_CFG.base_price, LOG_CFG.k

# ┌───────────────────────────────────────────────────────────────────────────┐
# │ Testing & Debugging Configuration                                         │
# └───────────────────────────────────────────────────────────────────────────┘

# Strict mode: enable accounting assertions (performance overhead)
STRICT_MODE = False

# Disable virtual liquidity for isolation testing
DISABLE_VIRTUAL_LIQUIDITY = False

# Binary search precision for integral curves
BISECT_ITERATIONS = 200  # Increased from 100 for better precision


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         ENUMS & MODEL REGISTRY                            ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class CurveType(Enum):
    CONSTANT_PRODUCT = "C"
    EXPONENTIAL = "E"
    SIGMOID = "S"
    LOGARITHMIC = "L"

CURVE_NAMES: Dict[CurveType, str] = {
    CurveType.CONSTANT_PRODUCT: "Constant Product",
    CurveType.EXPONENTIAL: "Exponential",
    CurveType.SIGMOID: "Sigmoid",
    CurveType.LOGARITHMIC: "Logarithmic",
}


class ModelConfig(TypedDict):
    curve: CurveType
    yield_impacts_price: bool
    lp_impacts_price: bool
    deprecated: bool

# ┌───────────────────────────────────────────────────────────────────────────┐
# │ Auto-generate all 16 combinations (4 curves x 2 yield flags x 2 LP flags) │
# │ Active models: *YN (Yield->Price=Yes, LP->Price=No).                      │
# │ Archived: *YY, *NY, *NN (kept for backwards compatibility).               │
# └───────────────────────────────────────────────────────────────────────────┘

MODELS: Dict[str, ModelConfig] = {}
for curve_code, curve_type in [("C", CurveType.CONSTANT_PRODUCT), ("E", CurveType.EXPONENTIAL),
                                ("S", CurveType.SIGMOID), ("L", CurveType.LOGARITHMIC)]:
    for yield_code, yield_price in [("Y", True), ("N", False)]:
        for lp_code, lp_price in [("Y", True), ("N", False)]:
            codename = f"{curve_code}{yield_code}{lp_code}"
            is_deprecated = not (yield_price and not lp_price)
            MODELS[codename] = {
                "curve": curve_type,
                "yield_impacts_price": yield_price,
                "lp_impacts_price": lp_price,
                "deprecated": is_deprecated,
            }

ACTIVE_MODELS: List[str] = [code for code, cfg in MODELS.items() if not cfg["deprecated"]]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                             ANSI COLORS                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class Color:
    """ANSI color codes for terminal output. Single source of truth — import from here."""
    HEADER = '\033[95m'
    MAGENTA = '\033[95m'   # alias for HEADER (used by formatter)
    PURPLE = '\033[35m'
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


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                             CORE CLASSES                                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# ┌─────────────────────────────────────┐
# │              User                   │
# └─────────────────────────────────────┘

class User:
    """Simple wallet: holds USDC and token balances."""
    def __init__(self, name: str, usd: D = D(0), token: D = D(0)):
        self.name = name
        self.balance_usd = usd
        self.balance_token = token


# ┌─────────────────────────────────────┐
# │       CompoundingSnapshot           │
# └─────────────────────────────────────┘

class CompoundingSnapshot:
    """Captures vault value at a specific compounding index for delta calculations."""
    def __init__(self, value: D, index: D):
        self.value = value
        self.index = index


# ┌─────────────────────────────────────┐
# │              Vault                  │
# └─────────────────────────────────────┘

class Vault:
    """USDC vault with daily APY-based compounding.

    Tracks deposited USDC and grows it via a compounding index.
    Snapshots allow computing accrued yield between any two points in time.
    """
    def __init__(self, apy: D = VAULT_APY):
        self.apy: D = apy
        self.compounding_index: D = D(1)
        self.snapshot: Optional[CompoundingSnapshot] = None
        self.compounds: int = 0

    def balance_of(self) -> D:
        """Current vault value, scaled by compounding growth since last snapshot."""
        if self.snapshot is None:
            return D(0)
        return self.snapshot.value * (self.compounding_index / self.snapshot.index)

    def add(self, value: D):
        self.snapshot = CompoundingSnapshot(value + self.balance_of(), self.compounding_index)

    def remove(self, value: D):
        if self.snapshot is None:
            raise Exception("Nothing staked!")
        self.snapshot = CompoundingSnapshot(self.balance_of() - value, self.compounding_index)

    def compound(self, days: int):
        """Advance the compounding index by N days of daily APY accrual.

        Note: O(days) loop — each day multiplied individually to match
        discrete daily compounding. For Solidity translation, consider
        using exponentiation: index *= (1 + apy/365) ** days.
        """
        for _ in range(days):
            self.compounding_index *= D(1) + (self.apy / D(365))
        self.compounds += days


# ┌─────────────────────────────────────┐
# │          UserSnapshot               │
# └─────────────────────────────────────┘

class UserSnapshot:
    """Records the compounding index when a user adds liquidity (for yield delta)."""
    def __init__(self, index: D):
        self.index = index


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       INTEGRAL CURVE MATH                                 ║
# ║                    (Decimal-based for precision)                          ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
#
# Each curve defines:
#   - price(supply): spot price at a given supply level
#   - integral(a, b): total cost to move supply from a to b
#
# These are used by LP.buy/sell to compute token amounts for a given USDC cost.

# Maximum exponent argument to prevent overflow (Decimal can handle more than float)
MAX_EXP_ARG = D(700)


# ┌─────────────────────────────────────┐
# │      Exponential Curve              │
# └─────────────────────────────────────┘

def _exp_integral(a: D, b: D) -> D:
    """Integral of base * e^(k*x) from a to b.

    Note: For very negative exp_a_arg, exp() gracefully underflows to ~0
    in Python's Decimal. This is correct — the integral from -∞ is finite.
    """
    exp_b_arg = EXP_K * b
    exp_a_arg = EXP_K * a
    
    if exp_b_arg > MAX_EXP_ARG:
        return D('Inf')
    
    return (EXP_BASE_PRICE / EXP_K) * (exp_b_arg.exp() - exp_a_arg.exp())

def _exp_price(s: D) -> D:
    if EXP_K * s > MAX_EXP_ARG:
        return D('Inf')
    return EXP_BASE_PRICE * (EXP_K * s).exp()


# ┌─────────────────────────────────────┐
# │         Sigmoid Curve               │
# └─────────────────────────────────────┘

def _sig_integral(a: D, b: D) -> D:
    """Integral of max_p / (1 + e^(-k*(x-m))) from a to b."""
    def F(x: D) -> D:
        arg = SIG_K * (x - SIG_MIDPOINT)
        if arg > MAX_EXP_ARG:
            # For large arg, ln(1+e^x) ≈ x (linear). Avoids Decimal overflow.
            return (SIG_MAX_PRICE / SIG_K) * arg
        return (SIG_MAX_PRICE / SIG_K) * (D(1) + arg.exp()).ln()
    return F(b) - F(a)

def _sig_price(s: D) -> D:
    return SIG_MAX_PRICE / (D(1) + (-SIG_K * (s - SIG_MIDPOINT)).exp())


# ┌─────────────────────────────────────┐
# │       Logarithmic Curve             │
# └─────────────────────────────────────┘

def _log_integral(a: D, b: D) -> D:
    """Integral of base * ln(1 + k*x) from a to b."""
    def F(x: D) -> D:
        u = D(1) + LOG_K * x
        if u <= 0:
            return D(0)
        return LOG_BASE_PRICE * ((u * u.ln() - u) / LOG_K + x)
    return F(b) - F(a)

def _log_price(s: D) -> D:
    """Logarithmic spot price. Returns 0 at s=0 (ln(1)=0) — this is by design;
    the integral from 0 is well-defined and the first tokens cost near-zero USDC."""
    val = D(1) + LOG_K * s
    return LOG_BASE_PRICE * val.ln() if val > 0 else D(0)


# ┌─────────────────────────────────────┐
# │     Binary Search for Tokens        │
# └─────────────────────────────────────┘

def _bisect_tokens_for_cost(supply: D, cost: D, integral_fn: Callable[[D, D], D], max_tokens: D = D("1e9")) -> D:
    """Binary search: find n tokens where integral(supply, supply+n) = cost."""
    if cost <= 0:
        return D(0)
    lo, hi = D(0), min(max_tokens, D("1e8"))
    while integral_fn(supply, supply + hi) < cost and hi < max_tokens:
        hi *= 2
    for _ in range(BISECT_ITERATIONS):
        mid = (lo + hi) / 2
        mid_cost = integral_fn(supply, supply + mid)
        if mid_cost < cost:
            lo = mid
        else:
            hi = mid
        # Early exit if converged to desired precision
        if abs(mid_cost - cost) < DUST:
            break
    return (lo + hi) / 2


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          LIQUIDITY POOL (LP)                              ║
# ╠═══════════════════════════════════════════════════════════════════════════╣
# ║ Parameterized by two model dimensions:                                    ║
# ║   - yield_impacts_price: vault compounding growth feeds back into price   ║
# ║   - lp_impacts_price: LP deposits contribute to effective USDC for pricing║
# ║                                                                           ║
# ║ Supports 4 bonding curve types. Constant Product uses virtual reserves;   ║
# ║ Exponential/Sigmoid/Logarithmic use integral math with a price multiplier.║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class LP:
    def __init__(self, vault: Vault, curve_type: CurveType,
                 yield_impacts_price: bool, lp_impacts_price: bool,
                 token_inflation_factor: D = TOKEN_INFLATION_FACTOR):
        self.vault = vault
        self.curve_type = curve_type
        self.yield_impacts_price = yield_impacts_price
        self.lp_impacts_price = lp_impacts_price
        self.token_inflation_factor = token_inflation_factor

        # Pool balances
        self.balance_usd = D(0)
        self.balance_token = D(0)
        self.minted = D(0)

        # Per-user LP positions and buy tracking
        self.liquidity_token: Dict[str, D] = {}
        self.liquidity_usd: Dict[str, D] = {}
        self.user_buy_usdc: Dict[str, D] = {}
        self.user_snapshot: Dict[str, UserSnapshot] = {}

        # Aggregate USDC tracking — the split is the core of model dimensions:
        # - buy_usdc: always contributes to effective_usdc (price base)
        # - lp_usdc: only contributes to price if lp_impacts_price=True
        # Both compound together in the vault. Yield scales via compound_ratio.
        self.buy_usdc = D(0)
        self.lp_usdc = D(0)

        # Constant product invariant
        self.k: Optional[D] = None

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                   Dimension-Aware Pricing                             │
    # └───────────────────────────────────────────────────────────────────────┘

    def _get_effective_usdc(self) -> D:
        """USDC amount used for price calculation, respecting yield/LP dimensions.

        Base is always buy_usdc. LP deposits add to it if lp_impacts_price.
        Yield compounds scale the total if yield_impacts_price.
        """
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
        """Scaling factor for integral curve buys: effective_usdc / buy_usdc.
        
        Includes yield inflation when yield_impacts_price=True.
        Used for buy pricing — more expensive tokens when vault has compounded.
        """
        if self.buy_usdc == 0:
            return D(1)
        return self._get_effective_usdc() / self.buy_usdc

    def _get_sell_multiplier(self) -> D:
        """Scaling factor for integral curve sells: principal-only, no yield.

        FIX 4: Sell returns are based on principal USDC only, not
        yield-inflated vault. This ensures sell is symmetric with buy
        (both scale by the same principal ratio) and yield flows
        exclusively through remove_liquidity.
        """
        if self.buy_usdc == 0:
            return D(1)
        base = self.buy_usdc
        if self.lp_impacts_price:
            base += self.lp_usdc
        return base / self.buy_usdc

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │               Constant Product Virtual Reserves                       │
    # └───────────────────────────────────────────────────────────────────────┘

    def get_exposure(self) -> D:
        """How much of the supply is exposed to price impact."""
        # D(1000) scaling: at ~1M minted tokens, exposure reaches 0 and the
        # curve flattens. Makes small test buys (500 USDC) produce visible
        # price movement against a 1B token cap.
        effective = min(self.minted * D(1000), CAP)
        exposure = EXPOSURE_FACTOR * (D(1) - effective / CAP)
        return max(D(0), exposure)

    def get_virtual_liquidity(self) -> D:
        """Virtual USDC liquidity that tapers off as buy_usdc approaches VIRTUAL_LIMIT.

        Prevents extreme price swings on early, low-liquidity trades.
        """
        # Allow disabling for isolation testing
        if DISABLE_VIRTUAL_LIQUIDITY:
            return D(0)
        
        base = CAP / EXPOSURE_FACTOR
        effective = min(self.buy_usdc, VIRTUAL_LIMIT)
        liquidity = base * (D(1) - effective / VIRTUAL_LIMIT)
        
        # Removed floor_liquidity - it can go negative and causes accounting drift
        # Virtual liquidity should decay smoothly to zero based only on buy_usdc
        return max(D(0), liquidity)

    def _get_token_reserve(self) -> D:
        """Available tokens for CP curve: (CAP - minted) / exposure_factor."""
        exposure = self.get_exposure()
        return (CAP - self.minted) / exposure if exposure > 0 else CAP - self.minted

    def _get_usdc_reserve(self) -> D:
        """USDC side of CP curve: effective_usdc + virtual_liquidity."""
        return self._get_effective_usdc() + self.get_virtual_liquidity()

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                            Price                                      │
    # └───────────────────────────────────────────────────────────────────────┘

    @property
    def price(self) -> D:
        """Current spot price. CP: reserve ratio. Integral curves: base_price * multiplier."""
        if self.curve_type == CurveType.CONSTANT_PRODUCT:
            token_reserve = self._get_token_reserve()
            usdc_reserve = self._get_usdc_reserve()
            if token_reserve == 0:
                return D(1)  # Fallback: no tokens available, default to base price
            return usdc_reserve / token_reserve
        else:
            # Integral curves: base curve price at current supply, scaled by multiplier
            s = self.minted
            if self.curve_type == CurveType.EXPONENTIAL:
                base = _exp_price(s)
            elif self.curve_type == CurveType.SIGMOID:
                base = _sig_price(s)
            elif self.curve_type == CurveType.LOGARITHMIC:
                base = _log_price(s)
            else:
                base = D(1)
            return base * self._get_price_multiplier()

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │         Fair Share: Caps Withdrawals to Prevent Vault Drain           │
    # └───────────────────────────────────────────────────────────────────────┘

    def _apply_fair_share_cap(self, requested: D, user_fraction: D) -> D:
        """Hard cap on a single withdrawal to user's proportional vault share."""
        vault_available = self.vault.balance_of()
        fair_share = user_fraction * vault_available
        return min(requested, fair_share, vault_available)

    def _get_fair_share_scaling(self, requested_total_usdc: D, user_principal: D, total_principal: D) -> D:
        """Scaling factor (0-1) to proportionally reduce all LP withdrawal components.
        Returns min(1, fair_share/requested, vault/requested)."""
        vault_available = self.vault.balance_of()
        if total_principal > 0 and requested_total_usdc > 0:
            fraction = user_principal / total_principal
            fair_share = fraction * vault_available
            return min(D(1), fair_share / requested_total_usdc, vault_available / requested_total_usdc)
        elif requested_total_usdc > 0:
            return min(D(1), vault_available / requested_total_usdc)
        return D(1)

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                       Core Operations                                 │
    # └───────────────────────────────────────────────────────────────────────┘

    def mint(self, amount: D):
        """Mint new tokens into pool. Reverts if would exceed CAP."""
        if self.minted + amount > CAP:
            raise Exception("Cannot mint over cap")
        self.balance_token += amount
        self.minted += amount

    def rehypo(self):
        """Sweep pool USDC into the vault for yield."""
        self.vault.add(self.balance_usd)
        self.balance_usd = D(0)

    def dehypo(self, amount: D):
        """Pull USDC back from vault into the pool."""
        self.vault.remove(amount)
        self.balance_usd += amount

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                              BUY                                      │
    # └───────────────────────────────────────────────────────────────────────┘

    def buy(self, user: User, amount: D):
        """User spends USDC to receive tokens. Curve determines token output."""
        user.balance_usd -= amount
        self.balance_usd += amount

        if self.curve_type == CurveType.CONSTANT_PRODUCT:
            if self.k is None:
                self.k = self._get_token_reserve() * self._get_usdc_reserve()
            assert self.k is not None  # type narrowing for pyright
            token_reserve = self._get_token_reserve()
            usdc_reserve = self._get_usdc_reserve()
            new_usdc = usdc_reserve + amount
            new_token = self.k / new_usdc
            out_amount = token_reserve - new_token
        else:
            # Integral curves: divide cost by multiplier, bisect for token count
            mult = self._get_price_multiplier()
            effective_cost = amount / mult if mult > 0 else amount
            supply = self.minted
            if self.curve_type == CurveType.EXPONENTIAL:
                out_amount = _bisect_tokens_for_cost(supply, effective_cost, _exp_integral)
            elif self.curve_type == CurveType.SIGMOID:
                out_amount = _bisect_tokens_for_cost(supply, effective_cost, _sig_integral)
            elif self.curve_type == CurveType.LOGARITHMIC:
                out_amount = _bisect_tokens_for_cost(supply, effective_cost, _log_integral)
            else:
                out_amount = amount

        self.mint(out_amount)
        self.balance_token -= out_amount
        user.balance_token += out_amount
        self.buy_usdc += amount
        self.user_buy_usdc[user.name] = self.user_buy_usdc.get(user.name, D(0)) + amount
        self.rehypo()

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                             SELL                                      │
    # └───────────────────────────────────────────────────────────────────────┘

    def sell(self, user: User, amount: D):
        """User returns tokens for USDC. Fair share cap prevents vault drain."""

        # Track principal fraction being sold (for buy_usdc bookkeeping)
        if self.minted > 0:
            principal_fraction = amount / self.minted
            principal_portion = self.buy_usdc * principal_fraction
        else:
            principal_portion = D(0)

        user_principal_reduction = min(
            self.user_buy_usdc.get(user.name, D(0)), principal_portion)

        user.balance_token -= amount

        # Compute raw USDC output from the bonding curve
        if self.curve_type == CurveType.CONSTANT_PRODUCT:
            if self.k is None:
                self.k = self._get_token_reserve() * self._get_usdc_reserve()
            assert self.k is not None  # type narrowing for pyright
            token_reserve = self._get_token_reserve()
            usdc_reserve = self._get_usdc_reserve()
            new_token = token_reserve + amount
            new_usdc = self.k / new_token
            # CP curve boundary: when USDC is depleted by prior sells,
            # k/new_token can exceed remaining reserves. Floor to 0
            # (user receives nothing). This is geometrically expected
            # on a fully-drained curve, not a math error.
            raw_out = max(D(0), usdc_reserve - new_usdc)
            self.minted -= amount
        else:
            self.minted -= amount
            supply_after = self.minted
            supply_before = supply_after + amount
            if self.curve_type == CurveType.EXPONENTIAL:
                base_return = _exp_integral(supply_after, supply_before)
            elif self.curve_type == CurveType.SIGMOID:
                base_return = _sig_integral(supply_after, supply_before)
            elif self.curve_type == CurveType.LOGARITHMIC:
                base_return = _log_integral(supply_after, supply_before)
            else:
                base_return = amount
            raw_out = base_return * self._get_sell_multiplier()

        # Cap output to fair share of vault
        original_minted = self.minted + amount
        if original_minted == 0:
            out_amount = min(raw_out, self.vault.balance_of())
        else:
            user_fraction = amount / original_minted
            out_amount = self._apply_fair_share_cap(raw_out, user_fraction)

        # Update buy_usdc tracking
        self.buy_usdc -= principal_portion
        if user.name in self.user_buy_usdc:
            self.user_buy_usdc[user.name] -= user_principal_reduction
            if self.user_buy_usdc[user.name] <= D(0):
                del self.user_buy_usdc[user.name]

        # Clear dust from accumulated rounding when supply is effectively zero
        if self.minted < DUST:
            self.minted = D(0)
            self.buy_usdc = D(0)

        self.dehypo(out_amount)
        self.balance_usd -= out_amount
        user.balance_usd += out_amount

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                        ADD LIQUIDITY                                  │
    # └───────────────────────────────────────────────────────────────────────┘

    def add_liquidity(self, user: User, token_amount: D, usd_amount: D):
        """User deposits tokens + USDC as a liquidity position."""
        user.balance_token -= token_amount
        user.balance_usd -= usd_amount
        self.balance_token += token_amount
        self.balance_usd += usd_amount
        self.lp_usdc += usd_amount
        self.rehypo()

        # Snapshot compounding index for yield calculation on removal
        self.user_snapshot[user.name] = UserSnapshot(self.vault.compounding_index)
        self.liquidity_token[user.name] = self.liquidity_token.get(user.name, D(0)) + token_amount
        self.liquidity_usd[user.name] = self.liquidity_usd.get(user.name, D(0)) + usd_amount

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                      REMOVE LIQUIDITY                                 │
    # └───────────────────────────────────────────────────────────────────────┘

    def remove_liquidity(self, user: User):
        """Withdraw LP position: original deposit + accrued yield (fair-share capped)."""
        token_deposit = self.liquidity_token[user.name]
        usd_deposit = self.liquidity_usd[user.name]
        buy_usdc_principal = self.user_buy_usdc.get(user.name, D(0))

        # Yield delta since deposit
        delta = self.vault.compounding_index / self.user_snapshot[user.name].index

        # Uncapped yield on LP deposit, tokens, and buy principal
        usd_yield = usd_deposit * (delta - D(1))
        usd_amount_full = usd_deposit + usd_yield

        inflation_delta = D(1) + (delta - D(1)) * self.token_inflation_factor
        token_yield_full = token_deposit * (inflation_delta - D(1))

        buy_usdc_yield_full = buy_usdc_principal * (delta - D(1))
        total_usdc_full = usd_amount_full + buy_usdc_yield_full

        # Fair share scaling to prevent over-withdrawal from vault
        principal = usd_deposit + buy_usdc_principal
        total_principal = self.lp_usdc + self.buy_usdc
        scaling_factor = self._get_fair_share_scaling(total_usdc_full, principal, total_principal)

        # Apply scaling
        total_usdc = total_usdc_full * scaling_factor
        token_yield = token_yield_full * scaling_factor
        token_amount = token_deposit + token_yield
        
        buy_usdc_yield_withdrawn = buy_usdc_yield_full * scaling_factor
        lp_usdc_yield_withdrawn = usd_yield * scaling_factor

        # Mint yield tokens and pull USDC from vault
        self.mint(token_yield)
        self.dehypo(total_usdc)
        
        # Update aggregate USDC tracking (principal only, never yield)
        self.lp_usdc -= usd_deposit
        if self.lp_usdc < DUST:
            self.lp_usdc = D(0)

        # Transfer to user
        self.balance_token -= token_amount
        self.balance_usd -= total_usdc
        user.balance_token += token_amount
        user.balance_usd += total_usdc

        del self.liquidity_token[user.name]
        del self.liquidity_usd[user.name]

    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                        Debug Output                                   │
    # └───────────────────────────────────────────────────────────────────────┘

    def print_stats(self, label: str = "Stats"):
        """Debug output: reserves, price, k, vault balance.

        DEPRECATED: Use Formatter.stats(label, lp) instead for consistent output.
        """
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


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                            RESULT TYPES                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class SingleUserResult(TypedDict):
    codename: str
    tokens_bought: D
    price_after_buy: D
    price_after_lp: D
    price_after_compound: D
    final_usdc: D
    profit: D
    vault_remaining: D


class MultiUserResult(TypedDict):
    codename: str
    profits: Dict[str, D]
    vault: D


class BankRunResult(TypedDict):
    codename: str
    profits: Dict[str, D]
    winners: int
    losers: int
    total_profit: D
    vault: D


class ScenarioResult(TypedDict, total=False):
    """Unified result type for new scenarios. Uses total=False — all fields optional."""
    # Core fields (always present in practice)
    codename: str
    profits: Dict[str, D]
    vault: D
    
    # Scenario-specific metadata
    winners: int
    losers: int
    total_profit: D
    strategies: Dict[str, D]       # LP fraction per user (partial_lp)
    entry_prices: Dict[str, D]     # Price when user entered (late)
    timeline: List[str]            # Event log (real_life)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                           MODEL FACTORY                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def create_model(
    codename: str,
    *,
    vault_apy: Optional[D] = None,
    token_inflation_factor: Optional[D] = None,
) -> Tuple[Vault, LP]:
    """Create a (Vault, LP) pair for the given model codename.

    Optional overrides allow tests to vary parameters without monkeypatching globals.
    """
    cfg = MODELS[codename]
    vault = Vault(apy=vault_apy if vault_apy is not None else VAULT_APY)
    lp = LP(
        vault, cfg["curve"], cfg["yield_impacts_price"], cfg["lp_impacts_price"],
        token_inflation_factor=(
            token_inflation_factor if token_inflation_factor is not None
            else TOKEN_INFLATION_FACTOR
        ),
    )
    return vault, lp

def model_label(codename: str) -> str:
    """Human-readable label: 'CYN (Constant Product, Yield->P=Y, LP->P=N)'."""
    cfg = MODELS[codename]
    curve = CURVE_NAMES[cfg["curve"]]
    yp = "Y" if cfg["yield_impacts_price"] else "N"
    lp = "Y" if cfg["lp_impacts_price"] else "N"
    deprecated = " [archived]" if cfg["deprecated"] else ""
    return f"{codename} ({curve}, Yield→P={yp}, LP→P={lp}){deprecated}"
