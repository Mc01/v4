# Test Environment

These are implementation aids added to the Python test models to better visualise protocol mechanics at small scale. They are not part of the core protocol math — they are "extra sugar" that makes bonding curve behavior observable when working with small USDC amounts (hundreds, not millions).

For the actual protocol math, see [MATH.md](./MATH.md).

---

## Virtual Reserves

The bonding curve needs existing reserves to function. Virtual reserves provide the curve with a starting state so that price discovery works from the very first buy.

```python
token_reserve = (CAP - minted) / exposure_factor
usdc_reserve = buy_usdc_with_yield + virtual_liquidity
k = token_reserve * usdc_reserve
```

- `token_reserve` is derived from the remaining supply, scaled down by the exposure factor
- `usdc_reserve` combines real USDC (from buys) with virtual liquidity (bootstrap)
- `k` is the constant product invariant, set once on first trade and never updated. Virtual reserves drift from k between trades by design — exposure decay and virtual liquidity are the bonding curve dynamics.

Without virtual reserves, the curve would start with zero on one side and no trades could execute.

---

## Dynamic Exposure Factor

Amplifies price movement so that small test amounts (e.g. 500 USDC) produce visible price changes against a 1 billion token cap.

```python
exposure_factor = EXPOSURE_FACTOR * (1 - min(minted * 1000, CAP) / CAP)
```

- At 0 minted: `exposure_factor = EXPOSURE_FACTOR` (100,000)
- At 1M tokens minted: `exposure_factor` approaches 0
- Effective token reserve = `CAP / exposure_factor` = 10,000 initially

This creates a steeper bonding curve at the start (price is sensitive to small buys) that flattens as more tokens are minted. Without it, buying 500 USDC worth of tokens from a 1B supply would produce negligible price movement.

---

## Dynamic Virtual Liquidity

Bootstrap liquidity that prevents division by zero and creates smooth price discovery from launch. Vanishes as real USDC accumulates.

```python
base = CAP / EXPOSURE_FACTOR  # 10,000
virtual_liquidity = base * (1 - min(buy_usdc, VIRTUAL_LIMIT) / VIRTUAL_LIMIT)
```

- At 0 USDC deposited: `virtual_liquidity = 10,000`
- At 100K USDC deposited: `virtual_liquidity` approaches 0
- Smoothly transitions from bootstrapped to fully organic reserves

~~**Floor constraint** (removed):~~
The original floor constraint (`floor = token_reserve - buy_usdc`) was removed from `core.py` because it could go negative and cause accounting drift. Virtual liquidity now decays smoothly to zero based only on `buy_usdc`, with a simple `max(0, ...)` guard.

---

## Constants

```python
CAP = 1_000_000_000      # 1 billion max token supply
EXPOSURE_FACTOR = 100_000 # Price movement amplification for test scale
VIRTUAL_LIMIT = 100_000   # USDC threshold where virtual liquidity vanishes
```
