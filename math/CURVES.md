# Bonding Curve Types

This document describes each bonding curve type available as a building block for commonwealth models.

---

## 1. Constant Product (x * y = k)

The standard AMM formula used by Uniswap v2.

**Formula:**
```
token_reserve * usdc_reserve = k

Buy:  (token_reserve - token_out) * (usdc_reserve + usdc_in) = k
Sell: (token_reserve + token_in) * (usdc_reserve - usdc_out) = k
```

**Price:** `usdc_reserve / token_reserve` (marginal price)

**Behavior:**
- Price increases with buys, decreases with sells
- Slippage grows with trade size relative to reserves
- Asymptotic – price approaches infinity as reserves deplete

**Pros:**
- Proven in production (Uniswap)
- Natural price discovery
- Simple math

**Cons:**
- Slippage on both buy and sell (~5% for moderate trades)
- Double slippage problem: user loses on entry AND exit

---

## 2. Exponential

Price grows exponentially with supply.

**Formula:**
```
price(supply) = base_price * e^(k * supply)

Buy cost:  integral from s to s+n of base_price * e^(k*x) dx
Sell return: same integral in reverse
```

**Behavior:**
- Early buyers get low prices, price accelerates sharply
- Strong incentive for early entry
- Steep curve creates high slippage at scale

**Pros:**
- Aggressive price discovery
- Rewards early participants heavily
- Well-defined mathematically

**Cons:**
- Late entrants face very high prices
- Can feel extractive (early vs late)
- May conflict with "common good" principle

---

## 3. Sigmoid (S-Curve)

Price follows a logistic / S-shaped curve. Slow start, rapid middle growth, plateau at maturity.

**Formula:**
```
price(supply) = max_price / (1 + e^(-k * (supply - midpoint)))

Buy cost:  integral of sigmoid over token range
Sell return: same integral in reverse
```

**Behavior:**
- Phase 1 (early): Price grows slowly – accessible entry
- Phase 2 (growth): Price accelerates – demand-driven discovery
- Phase 3 (mature): Price plateaus – stability

**Pros:**
- Natural lifecycle (bootstrap → growth → stability)
- Fair to both early and late participants
- Bounded price ceiling prevents runaway

**Cons:**
- More complex math (integral of sigmoid)
- Requires tuning (midpoint, steepness, max_price)
- Plateau may reduce incentive at maturity

---

## 4. Logarithmic

Price grows logarithmically with supply. Fast initial growth that decelerates.

**Formula:**
```
price(supply) = base_price * ln(1 + k * supply)

Buy cost:  integral from s to s+n of base_price * ln(1 + k*x) dx
Sell return: same integral in reverse
```

**Behavior:**
- Strong initial price appreciation
- Growth rate decreases over time
- Slippage decreases as supply grows (flatter curve)

**Pros:**
- Early buyers rewarded but not excessively
- Decreasing slippage favors larger / later pools
- Simple formula

**Cons:**
- Unbounded (no price ceiling)
- Diminishing returns may reduce late-stage interest
- Less aggressive price discovery than exponential

---

---

## Comparison

| Curve | Slippage | Price Discovery | Fairness | Complexity | Best For |
|-------|----------|-----------------|----------|------------|----------|
| **Constant Product** | High (both sides) | Strong | Moderate | Low | Market dynamics |
| **Exponential** | Very high at scale | Very strong | Low (favors early) | Medium | Aggressive growth |
| **Sigmoid** | Moderate | Phased | High | High | Lifecycle protocols |
| **Logarithmic** | Decreasing | Moderate | Moderate-High | Medium | Balanced growth |
