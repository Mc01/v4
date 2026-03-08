# Operational Context

## How to Run

```bash
# Run comparison table (all 5 active models × all scenarios)
./run_sim.sh

# Run a specific model (all scenarios, verbose)
./run_sim.sh CYN

# Run specific scenario flag
./run_sim.sh --whale CYN
./run_sim.sh --bank
./run_sim.sh --multi CYN,EYN

# Run full test suite (434 tests, 7 modules)
./run_test.sh          # Summary only
./run_test.sh -vv      # Show failures only
./run_test.sh -vvv     # Show all individual tests
```

## Virtual Environment

The project relies on a local virtual environment located in the `venv/` directory. Ensure appropriate dependencies (e.g. `jupyter`, `matplotlib`) are installed and run python commands from this environment when working with external tools or notebooks.

## File Structure

```
sim/
  core.py              # ALL protocol logic: LP class, Vault, curves, buy/sell/LP operations (853 lines)
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
  workflows/           # Agent operating modes (e.g., ULTRAWORK)
  math/
    VALUES.md          # Manual calculations, scenario traces, actual results
    curves.ipynb       # Interactive math curve visualizations
```

## Key Code Locations (`sim/core.py`)

| Component | Lines | What it does |
|-----------|-------|-------------|
| Exceptions | 17-24 | `ProtocolError`, `MintCapExceeded`, `NothingStaked` |
| Constants & CurveConfig | 27-80 | CAP, EXPOSURE_FACTOR, VIRTUAL_LIMIT, VAULT_APY, `CurveConfig` dataclass, `EXP_CFG`/`SIG_CFG`/`LOG_CFG` |
| Enums & Model registry | 86-151 | `CurveType`, `ModelConfig`, `MODELS` dict, `ACTIVE_MODELS` = CYN, EYN, SYN, LYN, P12YN, P15YN |
| Core classes | 152-228 | `Color`, `User`, `CompoundingSnapshot`, `Vault` (with inner `Snapshot`) |
| Curve integrals | 268-382 | `_exp_integral`, `_poly_integral`, `_log_integral`, `_bisect_tokens_for_cost` |
| Curve dispatch | 388-400 | `_CURVE_DISPATCH` table mapping `CurveType` → `(integral_fn, spot_price_fn)` |
| `LP.__init__` | 407-458 | State: buy_usdc, lp_usdc, minted, k, user tracking, `self._integral`/`self._spot_price` |
| `_get_effective_usdc()` | 462-475 | `buy_usdc * (vault / total_principal)` — yield inflates pricing input |
| `_get_price_multiplier()` | 480-488 | `effective_usdc / buy_usdc` — scales integral curve **buy** prices |
| `_get_sell_multiplier()` | 490-504 | `(buy_usdc + lp_usdc) / buy_usdc` — principal-only, no yield inflation |
| Virtual reserves (CYN) | 509-544 | `get_exposure`, `get_virtual_liquidity`, `_get_token/usdc_reserve` |
| `price` property | 547-558 | CP: `usdc_reserve / token_reserve`. Integral: `base_price(s) * multiplier` |
| Fair share cap | 563-580 | `_apply_fair_share_cap`, `_get_fair_share_scaling` — prevents vault drain |
| `buy()` | 606-633 | USDC → tokens. CP: k-invariant swap. Integral: bisect for token count |
| `sell()` | 637-695 | Tokens → USDC. Integral curves use `_get_sell_multiplier()` |
| `add_liquidity()` | 703-718 | Deposits tokens + USDC pair into vault |
| `remove_liquidity()` | 721-768 | LP withdrawal: principal + yield (LP USDC + buy USDC) + token inflation |
| Result types | 774-810 | `SingleUserResult`, `MultiUserResult`, `BankRunResult`, `ScenarioResult` |
| Model factory | 820-853 | `create_model()`, `model_label()` |

---

## Protocol State & Invariants

**Current Status:** Validating 5 active models.

1. **Zero Vault Residual Guarantee:** Across all 5 models and 10 scenarios, vault residual is **0 USDC**.
2. **Symmetric Buy/Sell:** Sell operations use a principal-only multiplier `(buy_usdc + lp_usdc) / buy_usdc`. Yield does *not* inflate sell prices.
3. **Yield Realization:** Users *must* `add_liquidity()` then `remove_liquidity()` to capture yield. Selling tokens directly forfeits vault yield.
4. **Inflation Isolation:** Token inflation is decoupled via `TOKEN_INFLATION_FACTOR`.
5. **K-Invariant Stabilized:** LP operations do *not* artificially inflate `k` in CYN models.

---

## Test Suite Reference

372 Total Tests traversing 5 models across 7 domains to guarantee mathematical fidelity:

- `test_conservation`: System USDC strict conservation.
- `test_invariants`: State tracking, sell proportions.
- `test_yield_accounting`: LP yield distribution and time-scaling.
- `test_stress`: Atomic vault/LP accounting boundaries.
- `test_curves`: Integral bounds, bisect precision, overflow guards.
- `test_scenarios`: End-to-end integration traces.
- `test_coverage_gaps`: Regression guards (multi-LP edges).

*(See [FINDINGS.md](./FINDINGS.md) for future improvements and modularization plans).*
