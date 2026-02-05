# Mathematical Findings & Known Issues

## Executive Summary

The vault residual is **not a yield distribution problem — it is a bonding curve symmetry problem.**

- The LP yield mechanism works correctly: after all LP removals, vault = buy_usdc exactly.
- All vault yield (LP USDC yield + buy USDC yield) is properly distributed during `remove_liquidity()`.
- The residual comes from the **sell phase**: bonding curve mechanics prevent full recovery of buy_usdc.
- SYN has 0 residual because the sigmoid ceiling makes its integral linear at the operating point.
- CYN has ~20k residual because `_update_k()` inflates k 5.79x during LP operations.
- EYN has ~7k because the exponential curve amplifies small price multiplier changes.
- LYN has ~33 because log growth is gentle, dampening the same multiplier asymmetry.

For the raw data behind these findings, see [VALUES.md](./VALUES.md).
For the fix plan, see [PLAN.md](./PLAN.md).

---

## Root Cause #1: CYN k-Invariant Inflation

**Impact**: ~90% of CYN's 20k+ vault residual.
**Location**: `core.py:401-402` (`_update_k`), called from `core.py:595-596` (`add_liquidity`) and `core.py:658-659` (`remove_liquidity`).

### The Problem

`_update_k()` computes `k = token_reserve * usdc_reserve` where both reserves include virtual components. When called inside `add_liquidity()`, reserves have shifted from buy operations (buy_usdc is higher, virtual liquidity decayed, exposure changed). This inflates k.

In the whale scenario: k goes from **100M to 578M** (5.79x). The whale's single LP operation causes a 4.7x jump. On sells, this inflated k makes the constant product curve extremely tight — selling ALL tokens recovers only ~51% of buy_usdc.

### Why k Should NOT Change During LP Operations (YN Models)

For active models (`yield=Yes, lp=No`):
- `effective_usdc = buy_usdc * (vault / total_principal)` — adding LP USDC increases both vault and total_principal by the same amount, ratio unchanged
- `virtual_liquidity` depends on `buy_usdc` — LP ops don't change buy_usdc
- `token_reserve` depends on `minted` and `exposure` — LP ops change neither
- **All reserves are invariant to LP operations.** Therefore k should not change.

### Evidence

See [VALUES.md](./VALUES.md) whale scenario trace for the full step-by-step accounting.

---

## Root Cause #2: EYN/LYN Price Multiplier Asymmetry

**Impact**: 7,056 USDC (EYN), 33 USDC (LYN).
**Location**: `core.py:493` (buy: `mult = _get_price_multiplier()`), `core.py:553` (sell: `raw_out = base_return * _get_price_multiplier()`).

### The Problem

Integral curves use a buy/sell pattern:
```
Buy:  effective_cost = amount / mult → tokens = bisect(supply, cost, integral)
Sell: raw_out = integral(supply_after, supply_before) * mult
```

The multiplier `mult = effective_usdc / buy_usdc` changes between buy and sell because: (1) the buy itself changes buy_usdc, (2) vault compounding changes the ratio, (3) other users' operations shift both values.

For a general nonlinear integral: `integral(a, a+n) / m1 * m2 != cost * (m2/m1)`. The nonlinearity means the buy/sell roundtrip doesn't perfectly conserve.

### Why Exponential Amplifies, Logarithmic Dampens

- **EXP**: Integral `(P0/k)(e^(kb) - e^(ka))` is dominated by `e^(kb)` at high supply. Small mult errors produce exponentially amplified USDC discrepancies.
- **LOG**: Integral `P0*[(u*ln(u) - u)/k + x]` (where `u = 1+kx`) grows sublinearly. Same mult errors produce tiny discrepancies.
- **SIG**: At ceiling saturation, integral ≈ `Pmax*(b-a)` (linear). Linear integrals satisfy `f(x/m)*m = x` exactly — zero asymmetry.

---

## Root Cause #3: Why SYN Has 0 Residual (Genuine, Not Masking)

The sigmoid `price(s) = 2 / (1 + exp(-0.001*s))` saturates at `SIG_MAX_PRICE = 2` at high supply.

**Three reinforcing factors**:
1. **Price ceiling makes integral linear.** At the whale's operating point, `price ≈ 2.0` (constant), so `integral(a,b) ≈ 2*(b-a)`. Linear integrals produce exact buy/sell symmetry regardless of multiplier changes.
2. **Binary search is well-conditioned.** The sigmoid integral is smooth without explosive growth. Precision of `DUST=1e-12` maps to negligible USDC error.
3. **Multiplier asymmetry self-cancels.** At saturation, `mult_sell/mult_buy ≈ 1` because price is constant. The 1.38% yield change over 100 days produces negligible asymmetry on a linear integral.

**This is a mathematical property, not a coincidence.** Raising `SIG_MAX_PRICE` to 100 (making it behave like EXP) would introduce residual.

---

## Root Cause #4: Negative raw_out in CYN Sell

**Impact**: Safety bug — users can compute negative USDC from selling tokens.
**Location**: `core.py:539` — `raw_out = usdc_reserve - new_usdc`, no guard against negative values.

When sell order changes (e.g., whale sells first), later sellers face a curve where `k/new_token > current_usdc_reserve`, producing negative raw_out.

---

## Mathematical Proof: LP Yield Distribution Conserves

### Single-User Case

Setup: User deposits `B` (buy) + `L` (LP). `P = B + L`. After compound: `V = P * delta`.

LP removal extracts:
```
total_lp_withdrawal = L*delta + B*(delta-1)
```

Vault after: `V - withdrawal = P*delta - L*delta - B*delta + B = B`

effective_usdc after: `B * (B / B) = B` — price falls back to base. User sells at original price, gets ~B.

Total received: `L*delta + B*(delta-1) + B = P*delta = V`. **Conservation: exact.**

### Multi-User Case

The LP removal phase conserves perfectly across all models — verified in the whale scenario (vault = 52,500 = buy_usdc after all 6 LP removals, with all 1,387 USDC of yield distributed).

The sell phase is where curve-specific mechanics create residual. Each seller sees a price based on `effective_usdc`, but the vault's real balance constrains actual payouts. The fair share cap prevents over-extraction but leaves residual when the curve over-promises.

---

## Three Yield Distribution Architectures

These were analyzed as potential design directions:

| Architecture | Yield Channel | Conservation? | Common Yield? |
|-------------|--------------|:---:|:---:|
| **A: Price only** | Remove buy_usdc_yield from LP | Yes (proven) | No |
| **B: LP direct only** | Disable yield->price | Yes (trivial) | Yes |
| **C: Both (current)** | Price + direct LP | Yes if curves symmetric | Yes |

**Architecture C is the current design and the correct one** per the protocol's mission. The requirement is to fix the curves to be symmetric, not to change the yield distribution.

---

## Lower Priority Issues

| # | Issue | Impact | Status |
|---|-------|--------|--------|
| 5 | Virtual liquidity phantom USDC (CYN) | Partially addressed by FIX 1 | Re-evaluate after fix |
| 6 | Fair share cap orphaning USDC | ~10% of CYN residual | Re-evaluate after fix |
| 7 | Token inflation tied to VAULT_APY | Cannot isolate impact | FIX 3 ready |
| 8 | Price multiplier edge case (buy_usdc=0) | Not observed in practice | Monitor |
| 9 | Binary search precision | Negligible (1e-12) | Not a concern |
| 10 | buy_usdc tracking invariant | Not observed broken | Add assertion |

---

## Parameter Sensitivity (Summary)

Most impactful parameters on vault residual, ranked:

1. **Token inflation** (currently on, tied to VAULT_APY) — mints unbacked tokens that extract USDC
2. **`_update_k()` in LP ops** — CYN only, 5.79x inflation — FIX 1 target
3. **VAULT_APY** — higher = more yield mismatch; at 0% residual is from pure slippage only
4. **VIRTUAL_LIMIT** — CYN only; virtual liquidity creates buy/sell asymmetry
5. **yield_impacts_price = False** — counterintuitively INCREASES residual (yield trapped in vault)
6. **EXP_K** — higher = steeper exponential = more multiplier asymmetry

Full parameter catalog available in the codebase at `core.py:15-54`.
