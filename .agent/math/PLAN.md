# Implementation Plan

## Overview

Vault residual fixes (FIX 1-4) are done. Phases 1-8 are complete. This file tracks future work only.

For historical root cause analysis, see [FINDINGS.md](./FINDINGS.md).
For raw verification data, see [VALUES.md](./VALUES.md).

---

## Completed Work (Summary)

| Phase | What | Key Result |
|-------|------|------------|
| 1-4 | FIX 1-4: vault residual elimination | All 7 models × all scenarios = 0 residual |
| 5 | Code cleanup (dead code, imports, typing, DU1 curve dispatch) | Clean codebase |
| 6 | Architecture (Vault.Snapshot, comments cleanup) | Simplified structure |
| 7 | Tests TG1-TG7 | 248 tests |
| 8 | Polynomial curves (P15YN/P20YN/P25YN), Reverse Whale, Stochastic | 434 tests, 7 active models |

---

## Phase 9: Math Issues Report

**Deliverable**: `.agent/math/math_analysis.md` — detailed report for specialist review.

| ID | Topic | Analysis needed |
|----|-------|----------------|
| MA1 | Sigmoid midpoint at 0 | Half the S-curve is in negative supply (never used). Effective behavior = half-sigmoid starting at `max_price/2`. Is this intentional? |
| MA2 | Log curve origin pricing | `_log_price(0) = 0` — first tokens are free. Integral is well-defined, but early buyers get extreme value. Risk? |
| MA3 | Bisect convergence | 200 iterations for Decimal(28) precision. ~93 iterations mathematically sufficient. Performance waste? |
| MA4 | FIX 4 sell/yield design | Sell never reflects yield. Users must LP to capture yield. Is this the intended tokenomics? |
| MA5 | CP price at empty pool | `_get_token_reserve()` returns `CAP - minted` when exposure=0. If all minted, price defaults to `D(1)`. Edge case? |

### Documentation Currency

After analysis, ensure these files reflect any new findings or changes:

- [VALUES.md](./VALUES.md) — updated with current scenario results
- [MATH.md](../../sim/MATH.md) — formulas and constants match code
- [FINDINGS.md](./FINDINGS.md) — audit tables refreshed with latest state

---

## Verification

After each phase:
```bash
cd /Users/mc01/Documents/V4 && python3 -m sim.test.run_all
```

Expected: 434 tests pass across 7 active models.
