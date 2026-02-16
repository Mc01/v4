# Implementation Plan

## Overview

Four fixes to eliminate vault residuals (all DONE), plus Phase 5: code cleanup, new features, and analysis.

For root cause analysis, see [FINDINGS.md](./FINDINGS.md).
For raw verification data, see [VALUES.md](./VALUES.md).

---

## FIX 1: Remove k-Inflation from LP Operations (CYN) — DONE

**Impact**: ~20k USDC residual eliminated.

Removed `_update_k()` calls from `add_liquidity()` and `remove_liquidity()`. For YN models, virtual reserves are invariant to LP operations, so k must not change. The whale scenario showed k grew from 100M to 578M (5.79×) due to `_update_k()` being called during LP ops.

---

## FIX 2: Guard Against Negative raw_out (CYN) — DONE

**Impact**: Safety fix.

Added `raw_out = max(D(0), raw_out)` after CP sell calculation. When prior sellers extract most USDC, `k/new_token` can exceed remaining reserves — floor to 0 prevents negative payouts.

---

## FIX 3: Parametrize Token Inflation — DONE

**Impact**: Enables isolation testing.

Added `TOKEN_INFLATION_FACTOR` constant (default 1.0). At 0.0, no token inflation. Used in `remove_liquidity()` via `inflation_delta = D(1) + (delta - D(1)) * TOKEN_INFLATION_FACTOR`.

---

## FIX 4: Sell Multiplier Asymmetry — DONE

**Impact**: EYN 7,056 → 0. LYN 33 → 0. ALL residuals now 0 across all scenarios.

### Root Cause

Integral curve buy/sell pattern:
```
Buy:  effective_cost = amount / multiplier → tokens = bisect(supply, cost, integral)
Sell: raw_out = integral(supply_after, supply_before) * multiplier
```

The `_get_price_multiplier()` = `effective_usdc / buy_usdc` includes vault yield inflation. After compounding, `effective_usdc > buy_usdc`, so multiplier > 1. This means sell returns yield-inflated USDC, but the vault only contains principal USDC after LP removals → residual.

### Fix Applied

Added `_get_sell_multiplier()` in `core.py`:
```python
def _get_sell_multiplier(self) -> D:
    if self.buy_usdc == 0:
        return D(1)
    base = self.buy_usdc
    if self.lp_impacts_price:
        base += self.lp_usdc
    return base / self.buy_usdc
```

Modified `sell()` to use `_get_sell_multiplier()` for integral curves instead of `_get_price_multiplier()`.

### Design Implication

Sell price on integral curves never reflects vault yield — it's purely curve-based.  Users who want yield must `add_liquidity()` then `remove_liquidity()`. This is the intended protocol incentive: **LP to earn, sell to exit.**

### Verification

All 4 models × 6 scenarios = 24 combinations: **0 residual**. 220/220 tests pass.

---

## Execution Order (Phases 1-4: DONE)

```
Phase 1: FIX 1 + FIX 2 → verify CYN improvement                      ← DONE
Phase 2: FIX 3         → test inflation=0, inflation=0.5, inflation=1  ← DONE
Phase 3: Reassess      → check EYN/LYN residuals                      ← DONE
Phase 4: Update docs   → record new residual numbers                   ← DONE
```

---

## Success Criteria (ALL ACHIEVED)

| Model | Pre-Fix | Post-FIX 4 | Target | Status |
|-------|---------|------------|--------|--------|
| CYN | ~20k USDC | **0 USDC** | < 0.01 | ✅ |
| EYN | ~7k USDC | **0 USDC** | < 1 | ✅ |
| SYN | 0 USDC | **0 USDC** | 0 | ✅ |
| LYN | ~33 USDC | **0 USDC** | < 1 | ✅ |

**Conservation invariant** (holds for all models):
```
sum(deposits) + vault_yield = sum(withdrawals) + vault_residual
```

---

---

# Phase 5: Code Cleanup + New Features (NEXT)

Sourced from [comprehensive code review](../../.gemini/antigravity/brain/d9b0b3ef-47ec-47bd-b5c4-2a195806b44a/review.md) (11 dimensions, 40+ findings, 40/55 score).

## Phase 5A: Code Cleanup

All items are non-behavioral (tests should still pass after each).

### DC1: Remove dead `LP.print_stats()`
- **File**: `sim/core.py`, lines 699-724 (26 lines)
- **Why**: Marked DEPRECATED, zero callers. Replaced by `Formatter.stats()`.
- **Action**: Delete the entire method.

### L1-L6: Remove unused imports (13 files)
- **7 scenario files**: Remove `fmt` import (formatting done via `Formatter` instance, not standalone `fmt`)
- `whale.py`: also remove unused `V`
- `test_stress.py`: remove `EXPOSURE_FACTOR, K, B, VIRTUAL_LIMIT, CurveType, LP, CAP` (7 imports)
- `test_coverage_gaps.py`: remove `Vault, LP, VAULT_APY`
- `test_curves.py`: remove `CAP, DUST`
- `test_scenarios.py`: remove `DUST`
- `test_yield_accounting.py`: remove `DUST`
- `helpers.py`: remove `D`

### CC1: Domain-specific exceptions
- **File**: `sim/core.py`
- Add `class ProtocolError(Exception)` base class
- Add `class MintCapExceeded(ProtocolError)` — replace `raise Exception("Cannot mint over cap")` on L498
- Add `class NothingStaked(ProtocolError)` — replace `raise Exception("Nothing to remove")` on L188

### CC2: Remove redundant `verbose: bool` param
- **12 scenario public functions** all have `verbose: bool = True` alongside `verbosity: int = 1`
- Pattern is always `v = verbosity if verbose else 0` — one param suffices
- **Action**: Remove `verbose` param. Callers use `verbosity=0` for silent mode.

### CC3 + PY3: NamedTuples
- `UserSnapshot` (L208) → `NamedTuple` with single `index: D` field
- `CompoundingSnapshot` (L155) → `NamedTuple` with `value: D, index: D`

### PY1: Simplify MODELS generation
- Lines 97-109: Nested for-loops building `MODELS` dict
- Use `itertools.product` + dict comprehension for conciseness

### TY1-TY5: Typing fixes
- **TY1**: Add `assert self.k is not None` before arithmetic in CP buy/sell
- **TY2**: `Formatter.lp` → `Optional['LP'] = None` (currently untyped `None`)
- **TY3**: Initialize `v` at top of CLI dispatch in `run_model.py`
- **TY4**: Consider `total=True` for `TypedDict` required fields
- **TY5**: `List[str]` → `list[str]`, `Dict[str, ...]` → `dict[str, ...]` (Python 3.9+)

### DU1: Extract curve dispatch
- `_get_integral_fn()` → returns `(integral_fn, price_fn)` tuple
- Eliminates `if EXP ... elif SIG ... elif LOG` repeated in `buy()`, `sell()`, `price`, `__init__`
- Store as `self._integral` and `self._price` on LP instance at construction time

---

## Phase 5B: FIX 4 Toggle

Make FIX 4 optional so protocol designers can compare behavior with and without.

### Implementation
- **`core.py`**: Add `SYMMETRIC_SELL = True` module-level flag
- **`LP.__init__`**: Store `self.symmetric_sell = symmetric_sell` param
- **`sell()`**: Use `_get_sell_multiplier()` when `self.symmetric_sell=True`, else `_get_price_multiplier()`
- **`create_model()`**: Accept `symmetric_sell: bool = True` kwarg, pass to LP

### CLI Integration
- **`run_model.py`**: Add `--fix` / `--no-fix` argparse flags
- `--fix` → `symmetric_sell=True` (FIX 4 active)
- `--no-fix` → `symmetric_sell=False` (original behavior)
- **`run_sim.sh`**: Default runs **without** FIX 4. `--fix` enables it.
  - `./run_sim.sh` → original behavior (residuals visible)
  - `./run_sim.sh --fix` → FIX 4 active (0 residuals)

### Tokenomics Analysis
- **New file**: `.agent/math/fix4_analysis.md`
- Side-by-side comparison table: all scenarios × all models, with vs without FIX 4
- Impact on: user profits, vault residuals, price paths, LP returns
- Assessment of protocol design implications:
  - With FIX 4: sell = pure curve, yield = LP-only → stronger LP incentive
  - Without FIX 4: sell includes yield → curve asymmetry → residual

---

## Phase 5C: Architecture + Comments

### A2: Curve dispatch strategy (approved)
- Store curve `integral` and `price` functions as callables on LP instance
- Set in `__init__` based on `curve_type`
- Eliminates 4× repeated `if/elif` dispatch
- **Recommendation**: Composition pattern (lightest touch, no new classes)

### A3: Move UserSnapshot (approved)
- Move `UserSnapshot` inside `Vault` as `Vault.Snapshot`
- It's only used by vault compounding logic

### A1: LP class size (alternatives provided, awaiting decision)
1. **Composition**: Store curve functions as callables on LP (lightest, recommended)
2. **ABC**: `BondingCurve` abstract base class with per-curve implementations (cleanest but heavier)
3. **Status quo + DU1**: Just extract `_get_integral_fn()` — minimal restructuring

### Comments cleanup
- Remove stale/redundant comments per GUIDELINES.md principle 3
- Keep math-critical comments (M1-M3 safety comments, FIX 4 rationale)

---

## Phase 5D: Tests (TG1-TG7)

**Target**: ~28 new tests (7 tests × 4 models). Add to `test_coverage_gaps.py`.

| ID | Test | What it verifies | Priority |
|----|------|-----------------|----------|
| TG1 | `test_sell_multiplier_principal_only` | `_get_sell_multiplier()` = 1.0 after compound (no yield leak). FIX 4 regression guard. | High |
| TG2 | `test_negative_balance_guard` | Protocol behavior when `User.balance_usd` or `balance_token` goes negative | Medium |
| TG3 | `test_sigmoid_edge_cases` | Sigmoid at midpoint, near overflow, near `SIG_MAX_PRICE` ceiling | Medium |
| TG4 | `test_multi_lp_interaction` | 2+ users add liquidity at different times, remove in different orders | Medium |
| TG5 | `test_compound_then_buy` | Buying after compounding gives fewer tokens (multiplier effect) | Medium |
| TG6 | `test_bisect_precision` | `_bisect_tokens_for_cost`: output tokens × price ≈ input cost ± DUST | Low |
| TG7 | `test_run_comparison_smoke` | `run_comparison()` runs without crash (patch stdout) | Low |

---

## Phase 5E: New Features

### MF1: Quadratic bonding curve (`p = a * s²`)
- Add `CurveType.QUADRATIC = "Q"`
- `QUAD_CFG = CurveConfig(base_price=D(1), k=D("0.000001"))` — calibrate for ~500 USDC test buys
- `_quad_integral(a, b) = base_price * k * (b³ - a³) / 3`
- `_quad_price(s) = base_price * k * s²`
- Wire into `buy()`, `sell()`, `price`, MODELS registry
- New model codes: QYN (active), QNN, QYY, QNY (archived)

### MF2: Polynomial bonding curve (`p = a * s^n`)
- Add `CurveType.POLYNOMIAL = "P"` with configurable exponent `n`
- `_poly_integral(a, b) = base_price * k * (b^(n+1) - a^(n+1)) / (n+1)`
- `_poly_price(s) = base_price * k * s^n`
- `CurveConfig` gets optional `exponent: D` field (default `D(2)`)

### Reverse Whale scenario
- **New file**: `sim/scenarios/reverse_whale.py`
- Same as whale scenario but **exit order reversed** (whale exits first, small users last)
- Tests whether early large withdrawals adversely affect remaining smaller users
- Register in `scenarios/__init__.py` and `run_model.py` CLI (`--rwhale`)

### MF3: Time-weighted stochastic scenario
- New scenario with user arrivals/departures distributed over N days
- Buys scattered across time (not all at once), periodic compounds between trades
- Models more realistic market behavior than discrete buy-compound-sell

---

## Phase 5F: Math Issues Report

**Deliverable**: `.agent/math/math_analysis.md` — detailed report for specialist review.

| ID | Topic | Analysis needed |
|----|-------|----------------|
| MA1 | Sigmoid midpoint at 0 | Half the S-curve is in negative supply (never used). Effective behavior = half-sigmoid starting at `max_price/2`. Is this intentional? |
| MA2 | Log curve origin pricing | `_log_price(0) = 0` — first tokens are free. Integral is well-defined, but early buyers get extreme value. Risk? |
| MA3 | Bisect convergence | 200 iterations for Decimal(28) precision. ~93 iterations mathematically sufficient. Performance waste? |
| MA4 | FIX 4 sell/yield design | Sell never reflects yield. Users must LP to capture yield. Is this the intended tokenomics? |
| MA5 | CP price at empty pool | `_get_token_reserve()` returns `CAP - minted` when exposure=0. If all minted, price defaults to `D(1)`. Edge case? |
| MA6 | Missing quadratic curve | Standard DeFi curve (`p = a * s²`). Should it be added? (User approved: yes → MF1) |

---

## Verification

After each phase:
```bash
cd /Users/mc01/Documents/V4 && python3 -m sim.test.run_all
```

Expected final count: ~248 tests (220 current + ~28 from TG1-TG7).
