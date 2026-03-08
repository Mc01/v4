# Model Matrix

## What Defines a Model

Each model is a unique combination of three dimensions:

1. **Curve Type** — the pricing function used for buy/sell operations
2. **Yield → Price** — whether vault yield feeds back into the price curve
3. **LP → Price** — whether adding/removing liquidity affects token price

This gives us **4 curves × 2 × 2 = 16 models**.

---

## Fixed Invariants

These properties are the same across all 16 models:

| Property | Value | Rationale |
|----------|-------|-----------|
| **Token Inflation** | Always yes | LPs earn minted tokens at 5% APY on tokens provided as liquidity |
| **Buy/Sell Impacts Price** | Always yes | Core price discovery mechanism — without it, there is no market |
| **Vault APY** | 5% | All USDC is rehypothecated into yield vaults |

---

## Variable Dimensions

### Yield → Price

Controls whether vault compounding grows the token price or is distributed separately.

| Value | Mechanic |
|-------|----------|
| **Yes** | `buy_usdc` grows with vault yield. Price = f(buy_usdc_with_yield). Vault compounding directly pushes price up. Holders benefit passively from price appreciation. |
| **No** | `buy_usdc` principal stays fixed for price calculation. Vault yield accrues separately and is distributed as USDC on exit. Price only moves from buys/sells. |

**Tradeoff:** "Yes" creates passive price growth (attractive to holders) but may disadvantage late buyers who enter at yield-inflated prices. "No" keeps price as pure market signal but yield is invisible until exit.

### LP → Price

Controls whether liquidity provision affects the bonding curve reserves.

| Value | Mechanic |
|-------|----------|
| **Yes** | LP USDC contributes to price reserves. Adding liquidity pushes price up; removing pushes it down. LP and buy USDC are unified in the curve. |
| **No** | LP USDC is tracked separately (`lp_usdc`). Adding/removing liquidity is price-neutral. Only `buy_usdc` feeds into the bonding curve. |

**Tradeoff:** "Yes" means LPs directly contribute to price discovery but creates price jumps on large LP events. "No" isolates price from liquidity flows but requires separate accounting for buy vs LP USDC.

---

## The 16 Models

### Codename Convention

`[Curve][Yield→Price][LP→Price]`

- **C** = Constant Product, **E** = Exponential, **S** = Sigmoid, **L** = Logarithmic
- **Y** = Yes, **N** = No

### Full Matrix

| Codename | Curve Type | Yield → Price | LP → Price |
|----------|-----------|:---:|:---:|
| CYY | Constant Product | Yes | Yes |
| CYN | Constant Product | Yes | No |
| CNY | Constant Product | No | Yes |
| CNN | Constant Product | No | No |
| EYY | Exponential | Yes | Yes |
| EYN | Exponential | Yes | No |
| ENY | Exponential | No | Yes |
| ENN | Exponential | No | No |
| SYY | Sigmoid | Yes | Yes |
| SYN | Sigmoid | Yes | No |
| SNY | Sigmoid | No | Yes |
| SNN | Sigmoid | No | No |
| LYY | Logarithmic | Yes | Yes |
| LYN | Logarithmic | Yes | No |
| LNY | Logarithmic | No | Yes |
| LNN | Logarithmic | No | No |

---

## Curve Type Summary

Each curve type brings different characteristics to the model. See [CURVES.md](./CURVES.md) for detailed formulas and behavior analysis.

| Curve | Price Discovery | Slippage | Fairness | Complexity |
|-------|----------------|----------|----------|------------|
| **Constant Product** | Strong | High (both sides) | Moderate | Low |
| **Exponential** | Very strong | Very high at scale | Low (favors early) | Medium |
| **Sigmoid** | Phased (slow → fast → plateau) | Moderate | High | High |
| **Logarithmic** | Moderate | Decreasing over time | Moderate-High | Medium |

### Constant Product

Standard AMM (`x * y = k`). Proven in production. Natural price discovery with symmetric slippage on both buy and sell. Moderate fairness — slippage creates buy/sell spread that disadvantages round-trip trades.

### Exponential

Price grows exponentially with supply (`base_price * e^(k*s)`). Aggressive price discovery that heavily rewards early participants. Steep curve creates high slippage at scale. May conflict with the "common good" principle by structurally favoring early entrants.

### Sigmoid

S-shaped price curve with three phases: slow start, rapid growth, plateau (`max_price / (1 + e^(-k*(s - midpoint)))`). Fair to both early and late participants. Bounded price ceiling provides stability at maturity but may reduce incentive in plateau phase.

### Logarithmic

Diminishing growth (`base_price * ln(1 + k*s)`). Early buyers rewarded but not excessively. Slippage decreases as supply grows, favoring larger/later pools. Unbounded price but with diminishing returns that may reduce late-stage interest.

---

## Expected Tradeoffs

| Dimension | Effect on Fairness | Effect on Slippage | Effect on Price Discovery | Effect on Complexity |
|-----------|-------------------|-------------------|--------------------------|---------------------|
| **Yield → Price = Yes** | Late buyers enter at yield-inflated price | No direct effect | Passive growth signal | Requires yield-adjusted reserve tracking |
| **Yield → Price = No** | Price reflects pure demand | No direct effect | Cleaner signal | Simpler price calculation |
| **LP → Price = Yes** | LP events move price (can disadvantage) | LP adds/removes create slippage | Richer signal (demand + liquidity) | Unified reserves |
| **LP → Price = No** | LP is price-neutral (fairer) | No LP slippage | Price = pure buy/sell | Dual tracking (buy_usdc vs lp_usdc) |
| **Constant Product** | Moderate | High | Strong | Low |
| **Exponential** | Low (early bias) | Very high | Very strong | Medium |
| **Sigmoid** | High (lifecycle) | Moderate | Phased | High |
| **Logarithmic** | Moderate-High | Decreasing | Moderate | Medium |
