# Operational Context

## How to Run

```bash
# Run a specific model scenario
./run_sim.sh CYN

# Run all models
./run_sim.sh

# Run tests
python3 -m sim.test.run_all

# Run a specific test module (all test files use relative imports)
python3 -m sim.test.run_all
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
| Virtual reserves (CYN) | 366-399 | `get_exposure`, `get_virtual_liquidity`, `_get_token/usdc_reserve` |
| `price` property | 406-425 | Spot price: CP uses reserves ratio; integral curves use `base * multiplier` |
| Fair share cap | 431-447 | `_apply_fair_share_cap`, `_get_fair_share_scaling` |
| `buy()` | 474-506 | USDC -> tokens. CP: k-invariant. Integral: bisect for token count. |
| `sell()` | 512-573 | Tokens -> USDC. Includes fair share cap, buy_usdc tracking. |
| `add_liquidity()` | 579-592 | Deposits tokens+USDC pair. |
| `remove_liquidity()` | 597-645 | LP withdrawal: principal + yield + token inflation. |

## Current Situation

**CYN and SYN have zero vault residuals. EYN and LYN have small residuals from multiplier asymmetry.**

| Model | Vault Residual | Root Cause | Fix Status |
|-------|---------------|-----------|------------|
| **CYN** | **0 USDC** | ~~`_update_k()` inflated k 5.79x~~ | ✅ FIX 1 resolved |
| **EYN** | ~7k USDC | Price multiplier asymmetry on exponential curve | Deferred |
| **SYN** | **0 USDC** | Sigmoid ceiling makes integral linear — perfect symmetry | ✅ No fix needed |
| **LYN** | ~33 USDC | Same multiplier asymmetry, dampened by log gentleness | Deferred (low impact) |

For root cause analysis, see [math/FINDINGS.md](./math/FINDINGS.md). For yield design rationale (why buy_usdc_yield to LPs is intentional), see [MISSION.md](./MISSION.md).

**Applied fixes**: FIX 1 (remove k-inflation), FIX 2 (guard negative raw_out), FIX 3 (parametrize token inflation). All 3 fixes applied and verified.
**Next steps**: See [math/PLAN.md](./math/PLAN.md) — Phase 3: Reassess EYN/LYN residuals; Phase 4: Update VALUES.md with fresh numbers.
