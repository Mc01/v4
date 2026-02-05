# Operational Context

## How to Run

```bash
# Run a specific model scenario
python3 sim/run_model.py

# Run tests
python3 -m sim.test.run_all

# Run yield accounting test (documents the buy_usdc_yield behavior)
python3 sim/test/test_yield_accounting.py
```

## File Structure

```
sim/
  core.py              # ALL protocol logic: LP class, Vault, curves, buy/sell/LP operations
  run_model.py         # Scenario runner with formatted output
  formatter.py         # Output formatting
  scenarios/           # Scenario definitions (whale, multi_user, bank_run, etc.)
  test/                # Test suite (conservation, invariants, yield accounting, stress)
  MATH.md              # Mathematical reference (formulas, curves, price mechanics)
  MODELS.md            # Model matrix, codenames, archived models
  TEST.md              # Test environment mechanics (virtual reserves, exposure factor)

.claude/
  CLAUDE.md            # Agent orientation (entry point)
  CONTEXT.md           # This file — operational guide
  MISSION.md           # Design principles, yield philosophy
  math/FINDINGS.md     # Analysis results, root causes, mathematical proofs
  math/PLAN.md         # Implementation plan with exact code changes
  math/VALUES.md       # Manual calculations, scenario trace data
```

## Key Code Locations (`sim/core.py`)

| Component | Lines | What it does |
|-----------|-------|-------------|
| Constants & parameters | 15-54 | CAP, EXPOSURE_FACTOR, VIRTUAL_LIMIT, VAULT_APY, curve params |
| Curve integrals | 219-291 | `_exp_integral`, `_sig_integral`, `_log_integral`, `_bisect_tokens_for_cost` |
| `LP.__init__` | 305-335 | State: buy_usdc, lp_usdc, minted, k, user tracking dicts |
| `_get_effective_usdc()` | 338-355 | Yield-adjusted pricing input: `buy_usdc * (vault/principal)` |
| `_get_price_multiplier()` | 356-361 | `effective_usdc / buy_usdc` — scales integral curve prices |
| Virtual reserves (CYN) | 366-403 | `get_exposure`, `get_virtual_liquidity`, `_get_token/usdc_reserve`, `_update_k` |
| `price` property | 410-429 | Spot price: CP uses reserves ratio; integral curves use `base * multiplier` |
| Fair share cap | 435-448 | `_apply_fair_share_cap`, `_get_fair_share_scaling` |
| `buy()` | 478-510 | USDC -> tokens. CP: k-invariant. Integral: bisect for token count. |
| `sell()` | 516-577 | Tokens -> USDC. Includes fair share cap, buy_usdc tracking. |
| `add_liquidity()` | 583-601 | Deposits tokens+USDC. Calls `_update_k()` (BUG — see PLAN.md FIX 1). |
| `remove_liquidity()` | 607-659 | LP withdrawal: principal + yield + token inflation. |

## Current Situation

**SYN works. CYN, EYN, LYN have vault residuals.**

| Model | Vault Residual | Root Cause | Fix Status |
|-------|---------------|-----------|------------|
| **CYN** | ~20k USDC | `_update_k()` inflates k 5.79x during LP ops | FIX 1 ready |
| **EYN** | ~7k USDC | Price multiplier asymmetry on exponential curve | Under analysis |
| **SYN** | **0 USDC** | Sigmoid ceiling makes integral linear — perfect symmetry | Done |
| **LYN** | ~33 USDC | Same multiplier asymmetry, dampened by log gentleness | Low priority |

For root cause analysis, see [math/FINDINGS.md](./math/FINDINGS.md). For yield design rationale (why buy_usdc_yield to LPs is intentional), see [MISSION.md](./MISSION.md).

**Next steps**: See [math/PLAN.md](./math/PLAN.md) — FIX 1 (remove `_update_k` from LP ops) is highest-impact.
