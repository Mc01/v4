# Codebase Analysis — Comprehensive 4-Dimension Audit

Post-Phase 8 checkpoint: 848 lines core, 7 active models (CYN/EYN/SYN/LYN/P15YN/P20YN/P25YN), 434 tests, 10 scenarios.

---

## 1. Math

### Verified Correct

| Item | Status |
|------|--------|
| `_exp_integral`, `_exp_price` | ✅ Overflow guard at `MAX_EXP_ARG=700`, underflow → 0 gracefully |
| `_sig_integral`, `_sig_price` | ✅ Asymptotic linearization avoids Decimal overflow |
| `_log_integral`, `_log_price` | ✅ Guard for `u <= 0`, returns 0. Integral well-defined |
| `_poly_integral`, `_poly_price` | ✅ Fractional exponent guard (`max(a, 0)`). Formula correct |
| `_bisect_tokens_for_cost` | ✅ Early exit at DUST convergence; 200 iter cap is safe |
| Price multiplier mechanism | ✅ Buy: `amount / mult`, Sell: `base_return * sell_mult`. FIX 4 symmetric |
| Fair share scaling | ✅ `min(1, fair_share/requested, vault/requested)` — proportional cap |
| Vault compounding | ✅ Daily discrete: `index *= (1 + apy/365)` per day. O(days) loop |
| Token inflation | ✅ `inflation_delta = 1 + (delta-1) * FACTOR`. Cleanly parametrized |

### Open Issues

| ID | Severity | Issue | Location |
|----|----------|-------|----------|
| **M1** | Low | `_log_price(0) = 0` — first tokens are free | `core.py:320-323` |
| **M2** | Low | Sigmoid midpoint at 0 wastes half the S-curve (negative supply never used) | `SIG_CFG` midpoint=0 |
| **M3** | Info | `_poly_price(0) = 0` — same as log but by design for polynomial `s^n` | `core.py:349-351` |
| **M4** | Info | Bisect 200 iterations is ~2× needed for Decimal(28) precision; harmless overkill | `BISECT_ITERATIONS=200` |
| **M5** | Low | CP price defaults to `D(1)` when `token_reserve=0` — arbitrary fallback | `core.py:549` |

---

## 2. Python Refactoring

### Stale References (must fix)

| File | Line | Issue |
|------|------|-------|
| `test/__init__.py:17` | `MODELS = ["CYN", "EYN", "SYN", "LYN"]` | **Missing polynomial models.** Should use `ACTIVE_MODELS` from core |
| `run_model.py:6` | `"Tests 4 active models (*YN)"` | Stale docstring — 7 active models |
| `run_model.py:15` | `"Compare 4 active *YN models"` | Same |
| `run_model.py:231` | `"Compare 4 active *YN models (table view)"` | Same |

### Refactoring Opportunities

| ID | Priority | Description | Location |
|----|----------|-------------|----------|
| **R1** | Medium | `helpers.py` uses pre-3.9 `from typing import List, Callable, Tuple` — should be `list`, `tuple` | `helpers.py:6` |
| **R2** | Low | `run_model.py` CLI dispatch has 12 nearly identical `if args.X: for code in codes: X_scenario(code, v)` blocks — could be data-driven | `run_model.py:359-409` |
| **R3** | Low | `test/__init__.py` hardcodes a model list instead of importing `ACTIVE_MODELS` — brittle; any new model means two edits | `test/__init__.py:17` |
| **R4** | Info | `Vault.Snapshot` is indented inside `Vault` (L242-245) but appears AFTER `Vault` class body ends. Works in Python due to class scope rules but visually misleading | `core.py:242-245` |
| **R5** | Info | `LP.__init__` is 48 lines. Polynomial binding closure (L438-452) could extract to `_bind_curve_functions()` for clarity | `core.py:403-452` |
| **R6** | Info | `ScenarioResult` uses `total=False` TypedDict — all fields optional. Could split into required base + optional extension | `core.py:796-809` |
| **R7** | Low | `run_sim.sh` and its relationship to `run_model.py` is undocumented — `run_sim.sh` runs `python3 sim/run_model.py` with args but this isn't obvious | Project root |

### Clean Code Highlights

- `_CURVE_DISPATCH` table eliminates repeated if/elif chains ✅
- `CurveConfig` frozen dataclass with backward-compatible aliases ✅
- `create_model()` factory with optional overrides for testing ✅
- `itertools.product` for MODELS generation ✅
- All custom exceptions inherit `ProtocolError` ✅

---

## 3. Comments & Docstrings

### Stale Comments

| File | Line | Issue |
|------|------|-------|
| `run_model.py:6-7` | Docstring says "4 active models" and lists only 4 curve types | Missing Polynomial |
| `test/__init__.py:7-12` | Category listing only shows 4 test modules (conservation, invariants, scenarios, curves) | Missing stress, yield_accounting, coverage_gaps |
| `core.py:399-400` | LP header block says "Supports 4 bonding curve types" | Should be 5 |
| `core.py:117` | MODELS generation comment says "4 base curves" | Should mention polynomial variants below |

### Good Documentation Patterns

- All test modules have ASCII art headers describing purpose ✅
- FIX 4 rationale documented inline in `_get_sell_multiplier()` ✅
- `Vault.compound()` has Solidity translation note ✅
- All curve functions have integral formulas in docstrings ✅
- `_CURVE_DISPATCH` table clearly commented ✅

### Missing Docstrings

| Function | File |
|----------|------|
| `mint()` | Has docstring ✅ |
| `rehypo()` / `dehypo()` | Minimal one-liners ✅ |
| All test functions | All have docstrings or leading comments ✅ |

---

## 4. Test Architecture

### Overall Structure

| Aspect | Current | Assessment |
|--------|---------|------------|
| **Framework** | Custom runner with `TestResults` class | ✅ Adequate for project scale; no `pytest` dep |
| **Pattern** | Each test takes `model: str`, runs for all 7 active models | ✅ Good parametrization pattern |
| **Organization** | 7 modules by concern (conservation, invariants, yield, stress, curves, scenarios, gaps) | ✅ Well-organized |
| **Total** | 64 test functions × 7 models = 434 tests (some skip CYN/PYN) | ✅ Good coverage |

### Coverage Assessment

| Area | Tests | Gaps |
|------|-------|------|
| Buy/Sell USDC flow | 6+3 = 9 tests | ✅ Thorough |
| Accounting invariants | 5 tests | ✅ buy_usdc tracking, LP tracking, k stability |
| Yield distribution | 3 tests | Could add: multi-LP yield proportionality |
| Vault mechanics | 3 tests | ✅ add/remove/compound |
| Curve math | 9 tests | ✅ Price movement, overflow, bisect, LP neutrality |
| Scenarios (end-to-end) | 13 tests | ✅ Single, multi, bank, hold, late, partial, whale |
| Coverage gaps | 18 tests | ✅ Dimensions, edge cases, FIX 4 regression |
| **Polynomial-specific** | Auto-extended via parametrization | ✅ P15YN/P20YN/P25YN run all tests |
| **Reverse whale** | Via scenario tests | Only smoke-tested via `run_comparison` (TG7) |
| **Stochastic** | Via scenario tests | Same — no dedicated unit test |

### Test Criteria Concerns

| ID | Priority | Concern |
|----|----------|---------|
| **T1** | Medium | `test_buy_then_sell_preserves_system` uses 10% slippage tolerance — very loose. Polynomial n=2.5 may approach this | 
| **T2** | Low | `test_multi_user_full_exit_empties_vault` uses `< D("0.01")` threshold — good precision |
| **T3** | Low | `test_exit_order_preserves_conservation` uses `< D("1.0")` — appropriate for multi-user FIFO/LIFO |
| **T4** | Info | Several tests do `if model == "CYN": return` — these exclusions should document WHY more clearly |
| **T5** | Info | `test_run_comparison_smoke` runs only for `ACTIVE_MODELS[0]` — good for avoiding 7× overhead, but only tests one model's path |

### Architecture Notes

- **No `pytest`**: Custom test runner works but lacks fixtures, parametrize, and mark. Appropriate for project scope.
- **`ALL_TESTS` registry**: Each module exports `ALL_TESTS: List[Tuple[str, Callable]]`. Simple and explicit.
- **Model skip pattern**: Tests use `if model != "CYN": return` or `if model == "CYN": return`. Consistent but could use a decorator.
- **Test isolation**: Each test creates fresh `Vault`+`LP` via `create_model()`. Good isolation.

---

## Summary

| Dimension | Critical Issues | Medium | Low/Info |
|-----------|:---:|:---:|:---:|
| **Math** | 0 | 0 | 5 |
| **Refactoring** | 4 stale refs | 1 | 5 |
| **Comments** | 4 stale comments | 0 | 0 |
| **Tests** | 0 | 1 | 4 |

**The 4 stale Python references and 4 stale comments are the only MUST-FIX items.** Everything else is incremental improvement.
