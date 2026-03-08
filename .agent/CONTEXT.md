# Operational Context

## How to Run

```bash
# Run comparison table (all 7 active models × all scenarios)
./run_sim.sh

# Run a specific model (all scenarios, verbose)
./run_sim.sh CYN

# Run specific scenario flag
./run_sim.sh --whale CYN
./run_sim.sh --bank
./run_sim.sh --multi CYN,EYN

# Run full test suite (434 tests, 7 modules)
python3 -m sim.test.run_all
```

## Virtual Environment

The project relies on a local virtual environment located in the `venv/` directory. Ensure appropriate dependencies (e.g. `jupyter`, `matplotlib`) are installed and run python commands from this environment when working with external tools or notebooks.

## File Structure

```
sim/
  core.py              # ALL protocol logic: LP class, Vault, curves, buy/sell/LP operations (848 lines)
  run_model.py         # CLI entry point: argparse, comparison table, scenario dispatch
  formatter.py         # Output formatting: Formatter class, verbosity levels, ASCII art
  scenarios/           # 10 scenario files: single_user, multi_user, bank_run, whale, hold, late, partial_lp, real_life, reverse_whale, stochastic
  test/                # 7 test modules: conservation, invariants, yield_accounting, stress, curves, scenarios, coverage_gaps
  MATH.md              # Mathematical reference (formulas, curves, price mechanics)
  MODELS.md            # Model matrix, codenames, archived models
  TEST.md              # Test environment mechanics (virtual reserves, exposure factor)

.agent/
  AGENT.md             # Agent orientation (entry point, reading order, glossary)
  CONTEXT.md           # This file — operational guide, code locations, current state
  FINDINGS.md          # Proposed Python cleanup and modular architecture refactoring plan
  MISSION.md           # Design principles, yield philosophy, "common yield" rationale
  GUIDELINES.md        # Coding standards (typing, comments, testing, benchmarking)
  math/PLAN.md         # Implementation plan: FIX 1-4 (DONE), Phases 1-9 (DONE)
  math/VALUES.md       # Manual calculations, scenario traces, actual results
```

## Key Code Locations (`sim/core.py`)

| Component | Lines | What it does |
|-----------|-------|-------------|
| Exceptions | 17-24 | `ProtocolError`, `MintCapExceeded`, `NothingStaked` |
| Constants & CurveConfig | 27-80 | CAP, EXPOSURE_FACTOR, VIRTUAL_LIMIT, VAULT_APY, `CurveConfig` dataclass, `EXP_CFG`/`SIG_CFG`/`LOG_CFG` |
| Enums & Model registry | 86-145 | `CurveType`, `ModelConfig`, `MODELS` dict, `ACTIVE_MODELS` = CYN, EYN, SYN, LYN, P15YN, P20YN, P25YN |
| Core classes | 159-221 | `User`, `CompoundingSnapshot`, `Vault` (with inner `Snapshot`) |
| Curve integrals | 230-328 | `_exp_integral`, `_sig_integral`, `_log_integral`, `_bisect_tokens_for_cost` |
| Curve dispatch | 331-341 | `_CURVE_DISPATCH` table mapping `CurveType` → `(integral_fn, spot_price_fn)` |
| `LP.__init__` | 355-389 | State: buy_usdc, lp_usdc, minted, k, user tracking, `self._integral`/`self._spot_price` |
| `_get_effective_usdc()` | 395-411 | `buy_usdc * (vault / total_principal)` — yield inflates pricing input |
| `_get_price_multiplier()` | 413-421 | `effective_usdc / buy_usdc` — scales integral curve **buy** prices |
| `_get_sell_multiplier()` | 423-436 | FIX 4: `(buy_usdc + lp_usdc) / buy_usdc` — principal-only, no yield inflation |
| Virtual reserves (CYN) | 442-475 | `get_exposure`, `get_virtual_liquidity`, `_get_token/usdc_reserve` |
| `price` property | 481-492 | CP: `usdc_reserve / token_reserve`. Integral: `base_price(s) * multiplier` |
| Fair share cap | 498-514 | `_apply_fair_share_cap`, `_get_fair_share_scaling` — prevents vault drain |
| `buy()` | 541-566 | USDC → tokens. CP: k-invariant swap. Integral: bisect for token count |
| `sell()` | 572-633 | Tokens → USDC. Integral curves use `_get_sell_multiplier()` (FIX 4) |
| `add_liquidity()` | 638-650 | Deposits tokens + USDC pair into vault |
| `remove_liquidity()` | 656-704 | LP withdrawal: principal + yield (LP USDC + buy USDC) + token inflation |
| Result types | 712-751 | `SingleUserResult`, `MultiUserResult`, `BankRunResult`, `ScenarioResult` |
| Model factory | 758-787 | `create_model()`, `model_label()` |

## Current State

### All Residuals Eliminated

**ALL 7 models × all scenarios = 0 vault residual.**

| Model | Vault Residual | Fix Applied |
|-------|:---:|-------------|
| **CYN** | **0** | FIX 1: removed `_update_k()` from LP ops (k was inflated 5.79×) |
| **EYN** | **0** | FIX 4: `_get_sell_multiplier()` (principal-only, no yield in sell) |
| **SYN** | **0** | None needed — sigmoid ceiling makes integral linear → perfect symmetry |
| **LYN** | **0** | FIX 4: same as EYN (log gentleness dampened it to 33 USDC, now 0) |

### Applied Fixes (all verified, 434/434 tests pass)

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

62 test functions × 7 active models = 434 tests across 7 modules:

| Module | Tests | What |
|--------|:---:|------|
| test_conservation | 4×7=28 | System USDC conservation across scenarios |
| test_invariants | 7×7=49 | buy_usdc tracking, sell proportion, LP math |
| test_yield_accounting | 3×7=21 | LP yield channels, duration scaling |
| test_stress | 9×7=63 | Atomic vault/LP accounting, multi-user invariants |
| test_curves | 9×7=63 | Integral math, overflow guards, bisect precision |
| test_scenarios | 13×7=91 | End-to-end scenario validation |
| test_coverage_gaps | 18×7=126-7=119 | Edge cases, FIX 4 regression, sigmoid edges, multi-LP |

### Completed Phases

| Phase | Scope |
|-------|-------|
| **1-4** | FIX 1-4: vault residual elimination |
| **5** | Code cleanup (dead code, unused imports, typing, DU1 curve dispatch) |
| **6** | Architecture (Vault.Snapshot, comments cleanup) |
| **7** | Tests TG1-TG7 (28 new tests, 248 total) |
| **8** | Polynomial curves (P15YN/P20YN/P25YN), Reverse Whale, Stochastic (434 tests) |
| **9** | Math issues analysis (MA1-MA5), log/poly price offset fix |
| **10 (Planned)** | Architecture modularization & Python code cleanup (see `FINDINGS.md`) |

For yield design rationale, see [MISSION.md](./MISSION.md).
