# Commonwealth Protocol — Design Principles

## Core Value Proposition: The Common Yield

> **All USDC deposited by all users generates yield. That yield is shared proportionally among liquidity providers.**

- When a user **buys tokens**, their USDC goes to the vault and earns yield
- When a user **provides liquidity**, their LP USDC also goes to the vault
- **LPs receive yield from ALL vault USDC** — including USDC from users who did NOT LP
- Non-LP users effectively donate their buy_usdc yield to the LP collective
- This creates the incentive: **LP and you share in everyone's yield**

---

## Protocol Goals (Priority Order)

1. **Mathematical correctness** — vault residual must be ~0 when all users exit. Validate in Python before Solidity.
2. **Incentivize buy + hold + LP** — LPs earn the most; buyers contribute to the commons; holders support price.
3. **Sustainability & fairness** — late entrants not structurally disadvantaged; fewest users lose money.
4. **Attractive returns** — real yield from vault rehypothecation (Spark/Sky/Aave, ~5% APY).

---

## Yield Design

### Three Channels for LPs

| Channel | Source | Mechanism |
|---------|--------|-----------|
| **LP USDC yield** | Yield on USDC provided as liquidity | Direct withdrawal in `remove_liquidity()` |
| **Buy USDC yield** | Yield on USDC used to buy tokens | Direct withdrawal + price appreciation |
| **Token inflation** | New tokens minted proportional to LP tokens | Configurable rate (can be 0%) |

### Who Gets What

| User Type | LP USDC Yield | Own Buy Yield | Others' Buy Yield | Token Inflation |
|-----------|:---:|:---:|:---:|:---:|
| Buyer only (no LP) | - | Via price only | - | - |
| Buyer + LP | Direct | Direct + price | Proportional share | Yes |

### Key Design Decision

**The buy_usdc_yield going to LPs in `remove_liquidity()` is INTENTIONAL.**

```python
# core.py:622-623 — THIS IS CORRECT, NOT A BUG
buy_usdc_yield_full = buy_usdc_principal * (delta - D(1))
total_usdc_full = usd_amount_full + buy_usdc_yield_full
```

This is the mechanism for distributing the "common yield." Without it, LPs only earn on their own USDC — there's no incentive to LP beyond individual yield.

---

## Model Architecture

Four bonding curves, all sharing the same invariants:

| Invariant | Value | Why |
|-----------|-------|-----|
| Yield -> Price | Yes | Vault growth inflates token price via `effective_usdc` |
| LP -> Price | No | Adding/removing liquidity is price-neutral |
| Token Inflation | Yes | LPs earn minted tokens (configurable rate) |
| Buy/Sell -> Price | Yes | Core price discovery mechanism |

Active models: **CYN** (Constant Product), **EYN** (Exponential), **SYN** (Sigmoid), **LYN** (Logarithmic). See [../sim/MODELS.md](../sim/MODELS.md).

### Two Yield Channels Operate Simultaneously

1. **Price appreciation**: `effective_usdc = buy_usdc * (vault / total_principal)` inflates the curve
2. **Direct LP withdrawal**: `remove_liquidity()` pays LPs yield as USDC

In single-user scenarios, these cancel out perfectly (mathematically proven — see [math/FINDINGS.md](./math/FINDINGS.md)). In multi-user scenarios, the bonding curve must be symmetric for conservation to hold. SYN achieves this; CYN/EYN/LYN have curve-specific issues being fixed.
