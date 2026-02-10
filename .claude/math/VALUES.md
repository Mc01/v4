# Reference Data — Manual Calculations & Scenario Traces

## Compounding Formula

```
Vault after N days = Principal * (1 + APY/365)^N
100 days @ 5% APY: multiplier = 1.013792, yield factor = 0.013792
```

---

## Whale Scenario (CYN) — Complete Trace

### Setup

5 regular users (500 USDC each, 1,000 balance) + 1 whale (50,000 USDC, 100,000 balance). Each: buys tokens, then adds LP. 100 days compound. All exit: remove LP then sell.

### Entry Phase

| User | Buy USDC | Tokens | Price After | LP USDC | k After LP |
|------|----------|--------|-------------|---------|------------|
| Alice | 500 | 476.19 | 1.04 | 497.38 | 104.5M |
| Bob | 500 | 456.84 | 1.09 | 497.49 | 109.1M |
| Carl | 500 | 439.01 | 1.13 | 497.59 | 113.7M |
| Diana | 500 | 422.52 | 1.18 | 497.68 | 118.2M |
| Eve | 500 | 407.23 | 1.22 | 497.76 | 122.8M |
| **Moby** | **50,000** | **8,049.83** | **5.67** | **45,613.32** | **578.4M** |

**Post-entry**: vault=100,601, buy_usdc=52,500, lp_usdc=48,101, minted=10,252, k=578.4M (5.79x initial!)

### Compound Phase

vault: 100,601 -> 101,989 (+1,387 yield), delta=1.013792

### LP Removal Phase

| User | LP USDC+yield | buy_usdc yield | Total out | Tokens back |
|------|--------------|----------------|-----------|-------------|
| Alice-Eve (each) | ~504 | ~6.90 | ~511 | ~430-483 |
| **Moby** | **46,242** | **690** | **46,932** | **8,161** |
| **TOTAL** | **48,765** | **724** | **49,489** | **10,393** |

Yield distributed: 663 (LP) + 724 (buy) = **1,387 = exactly total vault yield**.
**Vault after all LP removals: 52,500 = exactly buy_usdc.**

### Sell Phase

| User | Tokens | raw_out | Capped? | Actual out |
|------|--------|---------|:---:|------------|
| Alice | 483 | 2,610 | Yes | 2,439 |
| Bob | 463 | 289 | - | 289 |
| Carl | 445 | 116 | - | 116 |
| Diana | 428 | 114 | - | 114 |
| Eve | 413 | 112 | - | 112 |
| **Moby** | **8,161** | **23,597** | - | **23,597** |
| **TOTAL** | | | | **26,667** |

**Vault residual: 52,500 - 26,667 = 25,834 USDC**

### Conservation Check

```
Total IN:   100,601 (deposits) + 1,387 (yield) = 101,989 (vault after compound)
Total OUT:  49,489 (LP withdrawals) + 26,667 (sells) + 25,834 (residual) = 101,989  ✓
User cash:  10,788 (unspent USDC never deposited, stays in user wallets)
```

All USDC accounted for. The 25,834 residual = buy_usdc not recovered by sells (due to k-inflation).

---

## Whale Scenario — Actual Results (All Models, Post-FIX)

*Note: The trace above uses the whale scenario (5 users + 1 whale, 100 days). The table below uses the standard whale scenario config which differs in user count and amounts — hence the 25,834 trace residual vs the 0 standard residual for CYN.*

| Model | Total Profit | Vault Residual | Root Cause |
|-------|-------------|---------------|------------|
| **CYN** | **+1,479** | **0** | ✅ Resolved by FIX 1 |
| **EYN** | **+2,375** | **0** | ✅ Resolved by FIX 4 |
| **SYN** | **+1,454** | **0** | N/A |
| **LYN** | **+1,404** | **0** | ✅ Resolved by FIX 4 |

---

## Single User Scenario — Manual Calculation

Setup: Alice, 1,000 USDC. Buy 500, LP all tokens + 500 USDC. Compound 100 days. Full exit.

```
Buy:       500 USDC -> ~500 tokens
LP:        500 tokens + 500 USDC -> vault = 1,000
Compound:  vault = 1,000 * 1.013792 = 1,013.79  (yield = 13.79)
LP Remove: LP yield = 6.90, buy yield = 6.90 -> total = 513.79
           vault after = 1,013.79 - 513.79 = 500
Sell:      effective_usdc = 500*(500/500) = 500 (no appreciation)
           sell ~507 tokens -> ~500 USDC
           vault after = ~0
Total:     513.79 + 500 = 1,013.79 = vault after compound (EXACT)
Profit:    13.79 USDC
```

---

## Multi-User Scenario — Actual Results

Setup: 5 users, 500 USDC each, sequential buy+LP, 100 days compound, FIFO exit.

Expected total profit: ~51.72 USDC (3,750 * 0.013792).

| Model | Profit (+) | Loss (-) | Net | Winners | Losers | Vault Residual |
|-------|-----------|---------|-----|:---:|:---:|---:|
| CYN | +78 | -49 | +29 | 3 | 2 | 52 |
| EYN | +216 | -165 | +51 | 3 | 2 | 31 |
| SYN | +280 | -253 | +27 | 3 | 2 | 54 |
| LYN | +384 | -418 | -34 | 3 | 2 | 99 |

EYN net profit (+51) matches expected (+51.72). Exit order creates winners/losers in all models.

---

## Bank Run Scenario — Actual Results

Setup: 10 users, 365 days compound, sequential panic exit.

| Model | Winners | Losers | Vault Residual |
|-------|:---:|:---:|---:|
| CYN | 6 | 4 | 0 |
| EYN | 5 | 5 | 19 |
| SYN | 5 | 5 | 31 |
| LYN | 4 | 6 | 68 |

---

## Key Invariants (Verified)

1. **LP phase conservation**: After all LP removals, vault = buy_usdc (verified in whale trace)
2. **Yield distribution completeness**: LP yield + buy yield = total vault yield (verified: 663 + 724 = 1,387)
3. **System conservation**: deposits + yield = withdrawals + residual (verified in whale trace)
4. **buy_usdc unchanged by LP removal**: `remove_liquidity()` only decrements lp_usdc (verified in code)
