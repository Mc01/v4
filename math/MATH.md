# Protocol Math

## Overview

This document describes the mathematical mechanics shared across all 16 commonwealth models. Each model combines a **curve type** with two boolean dimensions (Yield → Price, LP → Price). The core operations — buy, add liquidity, compound, remove liquidity, sell — are described generically with `price(supply)` as a pluggable function.

For curve-specific formulas and behavior, see [CURVES.md](./CURVES.md).
For the full model matrix and dimension analysis, see [MODELS.md](./MODELS.md).

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
- **LP → Price = Yes:** LP USDC contributes to price reserves. Price moves.
- **LP → Price = No:** LP USDC tracked separately (`lp_usdc`). Price unchanged.

### 3. Vault Compounding

All USDC in vault earns 5% APY, compounded daily.

```
vault_balance = principal * (1 + apy/365) ^ days
compound_index = vault_balance / total_principal
```

Where `total_principal = buy_usdc + lp_usdc` (sum of all deposited USDC).

**Dimension behavior:**
- **Yield → Price = Yes:** `buy_usdc_with_yield = buy_usdc * compound_index`. Price uses the yield-adjusted value.
- **Yield → Price = No:** Price uses `buy_usdc` (original principal). Yield accrues separately.

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

## Curve-Specific Formulas

Each curve defines `price(supply)` and the integral used to compute buy cost / sell return over a range of supply. See [CURVES.md](./CURVES.md) for full details.

### Constant Product (x * y = k)

```
token_reserve * usdc_reserve = k

Buy:  (token_reserve - tokens_out) * (usdc_reserve + usdc_in) = k
Sell: (token_reserve + tokens_in) * (usdc_reserve - usdc_out) = k

price = usdc_reserve / token_reserve
```

### Exponential

```
price(s) = base_price * e^(k * s)

buy_cost(s, n) = integral from s to s+n of base_price * e^(k*x) dx
             = (base_price / k) * (e^(k*(s+n)) - e^(k*s))
```

### Sigmoid

```
price(s) = max_price / (1 + e^(-k * (s - midpoint)))

buy_cost(s, n) = integral from s to s+n of price(x) dx
             = (max_price / k) * ln(1 + e^(k*(s+n-midpoint))) - ln(1 + e^(k*(s-midpoint)))
```

### Logarithmic

```
price(s) = base_price * ln(1 + k * s)

buy_cost(s, n) = integral from s to s+n of base_price * ln(1 + k*x) dx
             = base_price * [((1 + k*(s+n)) * ln(1 + k*(s+n)) - (1 + k*s) * ln(1 + k*s)) / k - n]
```

---

## Variable Dimension Math

### Yield → Price

Controls how vault compounding interacts with the price function.

**Yes — yield feeds into price:**
```
compound_ratio = vault.balance / (buy_usdc + lp_usdc)
buy_usdc_with_yield = buy_usdc * compound_ratio

# Price calculation uses buy_usdc_with_yield
price = f(buy_usdc_with_yield, ...)
```

Vault yield grows `buy_usdc` proportionally, pushing price up over time even without new buys.

**No — yield distributed separately:**
```
# Price calculation uses buy_usdc (principal only)
price = f(buy_usdc, ...)

# Yield tracked separately
total_yield = vault.balance - (buy_usdc + lp_usdc)
user_yield = total_yield * (user_principal / total_principal)
```

Price is pure market signal. Yield is distributed as USDC on exit.

### LP → Price

Controls whether LP USDC contributes to the bonding curve reserves.

**Yes — LP USDC in price reserves:**
```
# Constant product example:
usdc_reserve = buy_usdc + lp_usdc  # Both contribute
price = usdc_reserve / token_reserve
```

Adding liquidity increases reserves, moving price. Removing decreases reserves.

**No — LP USDC tracked separately:**
```
# Constant product example:
usdc_reserve = buy_usdc  # Only buy USDC
price = usdc_reserve / token_reserve

# lp_usdc tracked independently for yield calculations
```

Price is isolated from liquidity flows. LP operations are price-neutral.

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
| Exponential | `base_price`, `k` (growth rate) |
| Sigmoid | `max_price`, `k` (steepness), `midpoint` |
| Logarithmic | `base_price`, `k` (scaling factor) |
