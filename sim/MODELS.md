# Model Matrix

## What Defines a Model

Each model is defined by its **curve type** — the pricing function used for buy/sell operations:

- **C** = Constant Product
- **E** = Exponential
- **S** = Sigmoid
- **L** = Logarithmic
- **P** = Polynomial (configurable exponent)

All other dimensions (Yield → Price, LP → Price) are now fixed invariants.

---

## Fixed Invariants

These properties are the same across all active models:

| Property | Value | Rationale |
|----------|-------|-----------|
| **Token Inflation** | Always yes | LPs earn minted tokens at 5% APY on tokens provided as liquidity |
| **Buy/Sell Impacts Price** | Always yes | Core price discovery mechanism — without it, there is no market |
| **Yield → Price** | Always yes | Vault compounding feeds into price curve. Passive appreciation for holders. |
| **LP → Price** | Always no | Adding/removing liquidity is price-neutral. Clean separation of buy vs LP USDC. |
| **Vault APY** | 5% | All USDC is rehypothecated into yield vaults |

---

## Active Models

7 active models — 4 base curves + 3 polynomial exponent variants:

| Codename | Curve Type | Exponent | Yield → Price | LP → Price |
|----------|-----------|:---:|:---:|:---:|
| **CYN** | Constant Product | — | Yes | No |
| **EYN** | Exponential | — | Yes | No |
| **SYN** | Sigmoid | — | Yes | No |
| **LYN** | Logarithmic | — | Yes | No |
| **P15YN** | Polynomial | 1.5 | Yes | No |
| **P20YN** | Polynomial | 2.0 | Yes | No |
| **P25YN** | Polynomial | 2.5 | Yes | No |

### Codename Convention

`[Curve][Yield→Price][LP→Price]`

- **C** = Constant Product, **E** = Exponential, **S** = Sigmoid, **L** = Logarithmic, **P** = Polynomial
- **Y** = Yes, **N** = No
- Polynomial variants use numeric suffix for exponent: **P15** = n^1.5, **P20** = n^2, **P25** = n^2.5

---

## Archived Models

The following 12 models have been explored and archived. They remain available in the codebase for research and comparison but are not recommended for production use.

| Codename | Curve Type | Yield → Price | LP → Price | Archive Reason |
|----------|-----------|:---:|:---:|----------------|
| CYY | Constant Product | Yes | Yes | LP moves price |
| CNY | Constant Product | No | Yes | LP moves price, no passive appreciation |
| CNN | Constant Product | No | No | No passive appreciation |
| EYY | Exponential | Yes | Yes | LP moves price |
| ENY | Exponential | No | Yes | LP moves price, no passive appreciation |
| ENN | Exponential | No | No | No passive appreciation |
| SYY | Sigmoid | Yes | Yes | LP moves price |
| SNY | Sigmoid | No | Yes | LP moves price, no passive appreciation |
| SNN | Sigmoid | No | No | No passive appreciation |
| LYY | Logarithmic | Yes | Yes | LP moves price |
| LNY | Logarithmic | No | Yes | LP moves price, no passive appreciation |
| LNN | Logarithmic | No | No | No passive appreciation |


---

## Curve Type Summary

See [MATH.md](./MATH.md) for detailed formulas, integrals, and behavior analysis.

| Curve | Price Discovery | Slippage | Fairness | Complexity |
|-------|----------------|----------|----------|------------|
| **Constant Product** | Strong | High (both sides) | Moderate | Low |
| **Exponential** | Very strong | Very high at scale | Low (favors early) | Medium |
| **Sigmoid** | Phased (slow → fast → plateau) | Moderate | High | High |
| **Logarithmic** | Moderate | Decreasing over time | Moderate-High | Medium |
| **Polynomial** | Configurable (exponent) | Steep at high supply | Depends on n | Medium |

---

## Expected Tradeoffs

| Dimension | Effect on Fairness | Effect on Slippage | Effect on Price Discovery | Effect on Complexity |
|-----------|-------------------|-------------------|--------------------------|---------------------|
| **Yield → Price = Yes** | Late buyers enter at yield-inflated price | No direct effect | Passive growth signal | Requires yield-adjusted reserve tracking |
| **Yield → Price = No** | Price reflects pure demand | No direct effect | Cleaner signal | Simpler price calculation |
| **LP → Price = Yes** | LP events move price (can disadvantage) | LP adds/removes create slippage | Richer signal (demand + liquidity) | Unified reserves |
| **LP → Price = No** | LP is price-neutral (fairer) | No LP slippage | Price = pure buy/sell | Dual tracking (buy_usdc vs lp_usdc) |

For curve-specific tradeoffs, see the [Curve Type Summary](#curve-type-summary) above.
