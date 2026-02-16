# Operational Context

## How to Run

```bash
# Run comparison table (all 4 active models × all scenarios)
./run_sim.sh

# Run a specific model (all scenarios, verbose)
./run_sim.sh CYN

# Run specific scenario flag
./run_sim.sh --whale CYN
./run_sim.sh --bank
./run_sim.sh --multi CYN,EYN

# Run full test suite (220 tests, 7 modules)
python3 -m sim.test.run_all
```

## File Structure

```
sim/
  core.py              # ALL protocol logic: LP class, Vault, curves, buy/sell/LP operations (807 lines)
  run_model.py         # CLI entry point: argparse, comparison table, scenario dispatch (394 lines)
  formatter.py         # Output formatting: Formatter class, verbosity levels, ASCII art (326 lines)
  scenarios/           # 8 scenario files: single_user, multi_user, bank_run, whale, hold, late, partial_lp, real_life
  test/                # 7 test modules: conservation, invariants, yield_accounting, stress, curves, scenarios, coverage_gaps
  MATH.md              # Mathematical reference (formulas, curves, price mechanics)
  MODELS.md            # Model matrix, codenames, archived models
  TEST.md              # Test environment mechanics (virtual reserves, exposure factor)

.agent/
  AGENT.md             # Agent orientation (entry point, reading order, glossary)
  CONTEXT.md           # This file — operational guide, code locations, current state
  MISSION.md           # Design principles, yield philosophy, "common yield" rationale
  GUIDELINES.md        # Coding standards (typing, comments, testing, benchmarking)
  math/FINDINGS.md     # Root cause analysis, mathematical proofs, parameter sensitivity
  math/PLAN.md         # Implementation plan: FIX 1-4 (DONE) + Phase 5 (NEXT)
  math/VALUES.md       # Manual calculations, scenario traces, actual results
```

## Key Code Locations (`sim/core.py`)

| Component | Lines | What it does |
|-----------|-------|-------------|
| Constants & CurveConfig | 15-65 | CAP, EXPOSURE_FACTOR, VIRTUAL_LIMIT, VAULT_APY, `CurveConfig` dataclass, `EXP_CFG`/`SIG_CFG`/`LOG_CFG` instances |
| Model registry | 85-111 | `ModelConfig`, `MODELS` dict (16 combos), `ACTIVE_MODELS` = CYN, EYN, SYN, LYN |
| Curve integrals | 233-311 | `_exp_integral`, `_sig_integral`, `_log_integral`, `_bisect_tokens_for_cost` |
| `LP.__init__` | 326-357 | State: buy_usdc, lp_usdc, minted, k, user tracking dicts |
| `_get_effective_usdc()` | 361-377 | `buy_usdc * (vault / total_principal)` — yield inflates pricing input |
| `_get_price_multiplier()` | 379-387 | `effective_usdc / buy_usdc` — scales integral curve **buy** prices |
| `_get_sell_multiplier()` | 389-405 | FIX 4: `(buy_usdc + lp_usdc) / buy_usdc` — principal-only, no yield inflation |
| Virtual reserves (CYN) | 408-441 | `get_exposure`, `get_virtual_liquidity`, `_get_token/usdc_reserve` |
| `price` property | 448-467 | CP: `usdc_reserve / token_reserve`. Integral: `base_price(s) * multiplier` |
| Fair share cap | 473-489 | `_apply_fair_share_cap`, `_get_fair_share_scaling` — prevents vault drain |
| `buy()` | 516-553 | USDC → tokens. CP: k-invariant swap. Integral: bisect for token count |
| `sell()` | 555-625 | Tokens → USDC. Integral curves use `_get_sell_multiplier()` (FIX 4) |
| `add_liquidity()` | 627-641 | Deposits tokens + USDC pair into vault |
| `remove_liquidity()` | 645-694 | LP withdrawal: principal + yield (LP USDC + buy USDC) + token inflation |

## Current State

### All Residuals Eliminated

**ALL 4 models × 6 scenarios = 24 combinations show 0 vault residual.**

| Model | Vault Residual | Fix Applied |
|-------|:---:|-------------|
| **CYN** | **0** | FIX 1: removed `_update_k()` from LP ops (k was inflated 5.79×) |
| **EYN** | **0** | FIX 4: `_get_sell_multiplier()` (principal-only, no yield in sell) |
| **SYN** | **0** | None needed — sigmoid ceiling makes integral linear → perfect symmetry |
| **LYN** | **0** | FIX 4: same as EYN (log gentleness dampened it to 33 USDC, now 0) |

### Applied Fixes (all verified, 220/220 tests pass)

| Fix | What it does | Impact |
|-----|-------------|--------|
| **FIX 1** | Remove `_update_k()` calls from `add/remove_liquidity()` | CYN: 20k → 0 |
| **FIX 2** | `raw_out = max(D(0), raw_out)` after CP sell calc | Safety: no negative USDC |
| **FIX 3** | `TOKEN_INFLATION_FACTOR` constant (default 1.0) | Enables inflation isolation |
| **FIX 4** | `_get_sell_multiplier()` for integral curve sells | EYN: 7k → 0, LYN: 33 → 0 |

### Recent Structural Changes

| Change | What |
|--------|------|
| **T2** | `CurveConfig` frozen dataclass groups `base_price`, `k`, `max_price`, `midpoint`. Instances: `EXP_CFG`, `SIG_CFG`, `LOG_CFG`. Backward-compatible aliases kept |
| **T6** | `Vault.balance_usd` field removed. `balance_of()` returns `D(0)` when no snapshot exists |
| **T1** | `Color` class unified in `core.py`, imported by `formatter.py` (no more duplicate) |
| **T5** | ANSI regex pre-compiled as `_ANSI_RE` in `formatter.py` |

### FIX 4 Mechanism (Critical Design Change)

**Problem**: Buy divides by multiplier, sell multiplied by multiplier. After compounding, multiplier includes yield inflation → sell returns excess USDC → vault residual.

**Fix**: New `_get_sell_multiplier()` returns `(buy_usdc + lp_usdc) / buy_usdc` (or `1` when `lp_impacts_price=False`). This is the **principal-only** ratio — no vault yield. Sell is now symmetric with buy. Yield flows exclusively through `remove_liquidity()`.

**Design implication**: Users who sell tokens get only curve-based pricing (no yield). To capture yield, users must add liquidity first, then `remove_liquidity()`. This is the intended protocol incentive.

### Test Suite

220 tests across 7 modules:

| Module | Tests | What |
|--------|:---:|------|
| test_conservation | 4×4=16 | System USDC conservation across scenarios |
| test_invariants | 7×4=28 | buy_usdc tracking, sell proportion, LP math |
| test_yield_accounting | 3×4=12 | LP yield channels, duration scaling |
| test_stress | 9×4=36 | Atomic vault/LP accounting, multi-user invariants |
| test_curves | 9×4=36 | Integral math, overflow guards, bisect precision |
| test_scenarios | 13×4=52 | End-to-end scenario validation |
| test_coverage_gaps | 10×4=40 | Edge cases: yield flags, parametrized APY, fair share |

### Next Steps

See [math/PLAN.md](./math/PLAN.md) — **Phase 5** (6 sub-phases):
- A: Code cleanup (dead code, unused imports, typing, duplicates)
- B: FIX 4 toggle (`--fix` / `--no-fix` CLI flag + tokenomics analysis)
- C: Architecture (curve dispatch strategy, comments)
- D: Tests TG1-TG7 (FIX 4 regression, sigmoid edges, multi-LP, etc.)
- E: New features (quadratic/polynomial curves, reverse whale, time-weighted scenario)
- F: Math report (MA1-MA6 detailed analysis for specialist review)

For root cause analysis, see [math/FINDINGS.md](./math/FINDINGS.md). For yield design rationale, see [MISSION.md](./MISSION.md).
