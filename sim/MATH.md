# Protocol Math

## Overview

This document describes the mathematical mechanics of the commonwealth protocol. The core operations — buy, add liquidity, compound, remove liquidity, sell — work with any bonding curve, using `price(supply)` as a pluggable function.

For curve-specific formulas and behavior, see [CURVES.md](./CURVES.md).
For the model matrix and fixed invariants, see [MODELS.md](./MODELS.md).

---

## Core Mechanics

### 1. Buy Tokens

User sends USDC, receives tokens. Price is determined by the bonding curve.

**Generic flow:**
```
tokens_out = solve_curve(usdc_in, current_supply)
minted += tokens_out
buy_usdc += usdc_in
vault.deposit(usdc_in)
```

- USDC goes to vault (rehypothecation)
- `buy_usdc` increases (always affects price — fixed invariant)
- Price increases per the curve function

### 2. Add Liquidity

User deposits tokens + USDC as a symmetric pair at current price.

**Generic flow:**
```
usdc_required = tokens_in * price(current_supply)
lp_usdc += usdc_required
vault.deposit(usdc_required)
record LP position: { tokens, usdc, entry_index, timestamp }
```

- User deposits equal value of tokens and USDC
- USDC goes to vault for yield generation
- LP position is recorded for yield tracking

**Dimension behavior:**
- LP USDC tracked separately (`lp_usdc`). Price unchanged.

### 3. Vault Compounding

All USDC in vault earns 5% APY, compounded daily.

```
vault_balance = principal * (1 + apy/365) ^ days
compound_index = vault_balance / total_principal
```

Where `total_principal = buy_usdc + lp_usdc`. The `compound_index` grows over time, which increases `buy_usdc_with_yield` and pushes price up.

### 4. Remove Liquidity

LP withdraws their position, receiving tokens + USDC with accrued yield.

**Generic flow:**
```
delta = current_index / entry_index
lp_usdc_yield = lp_usdc_deposited * (delta - 1)
token_inflation = tokens_deposited * (delta - 1)
buy_usdc_yield = user_share_of_buy_yield(delta)

total_usdc_out = lp_usdc_deposited + lp_usdc_yield + buy_usdc_yield
total_tokens_out = tokens_deposited + token_inflation

apply fair_share_scaling(total_usdc_out, total_tokens_out)
```

**What the LP receives:**
- Original LP USDC + yield on LP USDC
- Original tokens + inflated tokens (5% APY)
- Their share of buy USDC yield

### 5. Sell Tokens

User sells tokens back to the protocol, receives USDC.

**Generic flow:**
```
usdc_out = solve_curve_sell(tokens_in, current_supply)
usdc_out = min(usdc_out, fair_share_cap)
vault.withdraw(usdc_out)
burn(tokens_in)
minted -= tokens_in
```

- Tokens are burned (removed from supply)
- USDC withdrawn from vault
- Price decreases per the curve function
- Fair share cap prevents draining vault beyond entitlement

---

## Price Factors

Understanding what moves price is essential for protocol participants.

### What Increases Price

| Action | Mechanism |
|--------|-----------|
| **Buy tokens** | Adds USDC to `buy_usdc`, which feeds directly into price calculation |
| **Vault compounding** | Grows `compound_ratio`, multiplying `buy_usdc` into higher `buy_usdc_with_yield` |

### What Decreases Price

| Action | Mechanism |
|--------|-----------|
| **Sell tokens** | Removes USDC from `buy_usdc` proportional to tokens sold |
| **Withdraw yield** | Reduces vault balance, lowering `compound_ratio` |

### What Does NOT Affect Price

| Action | Why |
|--------|-----|
| **Add liquidity** | LP USDC tracked separately in `lp_usdc`, not included in price reserves |
| **Remove LP principal** | Only `lp_usdc` decreases, which doesn't feed into price |

### Price Formula

```
compound_ratio = vault.balance / (buy_usdc + lp_usdc)
buy_usdc_with_yield = buy_usdc * compound_ratio
price = curve_price(supply, buy_usdc_with_yield)
```

**Key insight:** Vault compounding grows `buy_usdc_with_yield` over time, creating passive price appreciation even without new buys. This is because both `buy_usdc` and `lp_usdc` earn yield in the vault, but only `buy_usdc` feeds into price.

---

## Curve-Specific Formulas

Each curve defines `price(supply)` and the integral used to compute buy cost / sell return over a range of supply. See [CURVES.md](./CURVES.md) for full details.

### Constant Product (x * y = k)

The classic AMM formula where the product of reserves stays constant. Price emerges from the ratio of reserves. Most capital-efficient for high-volume trading.

**High-level:**
```
token_reserve * usdc_reserve = k

Buy:  (token_reserve - tokens_out) * (usdc_reserve + usdc_in) = k
Sell: (token_reserve + tokens_in) * (usdc_reserve - usdc_out) = k

price = usdc_reserve / token_reserve
```

**Exact formulas:**
```
k = x · y                                           # invariant
p = y / x                                           # spot price
Δx = x - k/(y + Δy)                                 # tokens out for Δy USDC in
Δy = y - k/(x + Δx)                                 # USDC out for Δx tokens in
```

| ✅ Strengths | ❌ Weaknesses |
|-------------|---------------|
| Battle-tested (Uniswap) | High slippage on large trades |
| Simple, predictable | No built-in price floor |
| Always liquid | Impermanent loss for LPs |
| Gas efficient | Requires significant reserves |

---

### Exponential

Price grows exponentially with supply. Creates strong price appreciation as tokens are minted, rewarding early participants. Can lead to extreme prices at high supply.

**High-level:**
```
price(s) = base_price * e^(k * s)

buy_cost(s, n) = integral from s to s+n of base_price * e^(k*x) dx
             = (base_price / k) * (e^(k*(s+n)) - e^(k*s))
```

**Exact formulas:**
```
p(s) = P₀ · eᵏˢ                                     # price at supply s

∫ₐᵇ P₀ · eᵏˣ dx = (P₀/k) · (eᵏᵇ - eᵏᵃ)             # cost from a to b
```

**Copyable (Python/code):**
```python
price = P0 * exp(k * s)
cost = (P0 / k) * (exp(k * b) - exp(k * a))
```

| ✅ Strengths | ❌ Weaknesses |
|-------------|---------------|
| Strong early-mover rewards | Can overflow at high supply |
| Aggressive price discovery | Late buyers face steep costs |
| Clear growth trajectory | Requires careful k tuning |
| Good for scarce assets | Extreme prices deter adoption |

---

### Sigmoid

Price follows an S-curve, starting low, accelerating through a midpoint, then asymptoting to a maximum. Models natural adoption curves where growth saturates.

**High-level:**
```
price(s) = max_price / (1 + e^(-k * (s - midpoint)))

buy_cost(s, n) = integral from s to s+n of price(x) dx
             = (max_price / k) * ln(1 + e^(k*(s+n-midpoint))) - ln(1 + e^(k*(s-midpoint)))
```

**Exact formulas:**
```
p(s) = Pₘₐₓ / (1 + e⁻ᵏ⁽ˢ⁻ᵐ⁾)                        # price at supply s

∫ₐᵇ p(x) dx = (Pₘₐₓ/k) · [ln(1 + eᵏ⁽ᵇ⁻ᵐ⁾) - ln(1 + eᵏ⁽ᵃ⁻ᵐ⁾)]
```

**Copyable (Python/code):**
```python
price = Pmax / (1 + exp(-k * (s - m)))
cost = (Pmax / k) * (log(1 + exp(k * (b - m))) - log(1 + exp(k * (a - m))))
```

| ✅ Strengths | ❌ Weaknesses |
|-------------|---------------|
| Price ceiling prevents runaways | Complex integral calculation |
| Models real adoption curves | Slow growth near extremes |
| Predictable max price | Less reward for early buyers |
| Smooth price transitions | Midpoint tuning critical |

---

### Logarithmic

Price grows logarithmically — fast initially, then slowing down. Creates diminishing returns for later participants, making the curve more accessible over time.

**High-level:**
```
price(s) = base_price * ln(1 + k * s)

buy_cost(s, n) = integral from s to s+n of base_price * ln(1 + k*x) dx
             = base_price * [((1 + k*(s+n)) * ln(1 + k*(s+n)) - (1 + k*s) * ln(1 + k*s)) / k - n]
```

**Exact formulas:**
```
p(s) = P₀ · ln(1 + ks)                              # price at supply s

F(x) = P₀ · [(u·ln(u) - u)/k + x]  where u = 1 + kx  # antiderivative

∫ₐᵇ p(x) dx = F(b) - F(a)
```

**Copyable (Python/code):**
```python
price = P0 * log(1 + k * s)

def F(x):
    u = 1 + k * x
    return P0 * ((u * log(u) - u) / k + x)

cost = F(b) - F(a)
```

| ✅ Strengths | ❌ Weaknesses |
|-------------|---------------|
| Accessible to late joiners | Early movers get less upside |
| No overflow risk | Slower price appreciation |
| Gentle growth curve | May not incentivize early buys |
| Sustainable long-term | Complex antiderivative |

---

## Token Inflation (Fixed Invariant)

All models mint new tokens for LPs at 5% APY on tokens provided as liquidity.

```
delta = current_index / entry_index
token_inflation = tokens_in_lp * (delta - 1)
```

Where `delta` reflects the time-weighted compound growth. At 5% APY compounded daily over `d` days:

```
delta = (1 + 0.05/365) ^ d
```

Inflated tokens are minted and given to the LP on exit. This is curve-agnostic — every model mints tokens the same way.

---

## Fair Share Scaling

Prevents bank runs by ensuring no user can withdraw more than their proportional share of the vault.

```
user_principal = lp_usdc_deposited + buy_usdc_deposited
total_principal = sum(all users' principals)
user_fraction = user_principal / total_principal

vault_available = vault.balance
fair_share = user_fraction * vault_available

scaling_factor = min(1, fair_share / requested, vault_available / requested)
```

Applied to **both** USDC withdrawal and token inflation proportionally:
```
actual_usdc = requested_usdc * scaling_factor
actual_tokens = requested_tokens * scaling_factor
```

This is curve-agnostic — fair share scaling works the same regardless of curve type or dimension settings.

---

## USDC Tracking

The protocol tracks two categories of USDC:

| Tracker | Source | Role |
|---------|--------|------|
| `buy_usdc` | USDC from buy operations | Backs minted tokens. Used in price calculation (always). |
| `lp_usdc` | USDC from add_liquidity operations | LP yield pool. Used in price calculation only if LP → Price = Yes. |

Both are deposited into the same vault and compound together. The split is maintained for accounting:

```
compound_ratio = vault.balance / (buy_usdc + lp_usdc)
buy_usdc_with_yield = buy_usdc * compound_ratio
lp_usdc_with_yield = lp_usdc * compound_ratio
```

This proportional allocation applies regardless of curve type.

---

## Constants

```
VAULT_APY = 5%          # Annual percentage yield, compounded daily
TOKEN_INFLATION = 5%    # Annual token minting rate for LPs, compounded daily
```

Curve-specific constants (vary per implementation):

| Curve | Constants |
|-------|-----------|
| Constant Product | Initial reserves (or virtual reserve parameters) |
| Exponential | `P₀ = 1`, `k = 0.0002` (growth rate) |
| Sigmoid | `Pₘₐₓ = 2`, `k = 0.001` (steepness), `m = 0` (midpoint) |
| Logarithmic | `P₀ = 1`, `k = 0.01` (scaling factor) |

---

## Quick Reference

| Curve | Price Formula | Integral (a → b) |
|-------|---------------|------------------|
| Constant Product | `y / x` | AMM swap formula |
| Exponential | `P₀ · eᵏˢ` | `(P₀/k) · (eᵏᵇ - eᵏᵃ)` |
| Sigmoid | `Pₘₐₓ / (1 + e⁻ᵏ⁽ˢ⁻ᵐ⁾)` | `(Pₘₐₓ/k) · [ln(1+eᵏ⁽ᵇ⁻ᵐ⁾) - ln(1+eᵏ⁽ᵃ⁻ᵐ⁾)]` |
| Logarithmic | `P₀ · ln(1+ks)` | `F(b) - F(a)` where `F(x) = P₀·[(u·ln(u)-u)/k + x]` |
