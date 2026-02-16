## 1. User Requests (As-Is)
1. "Let's move `.claude` files to `.agent` & adjust all references"
2. User confirmed "Yes, rename to AGENT.md" when asked about CLAUDE.md → AGENT.md
3. "Read .agent dir & show me plan in Plannotator"
4. "Let's extend @.agent/GUIDELINES.md" — with 4 specific requirements about Plannotator workflow
5. "Let's clear context. Re-read .agent folder. Present me plan & let's go for implementation"
6. "Proceed with implementation" (after Phase 5 plan was approved)
## 2. Final Goal
Execute **Phase 5: Code Cleanup** of the Commonwealth Protocol simulation codebase. This is part of a larger roadmap (Phases 5–10) where each phase is reviewed and git-staged separately. Phase 5 covers: dead code removal, unused imports, domain exceptions, redundant params, NamedTuples, MODELS simplification, typing fixes, and curve dispatch extraction.
## 3. Work Completed
### Pre-Phase 5
- ✅ Renamed `.claude/` → `.agent/`, `CLAUDE.md` → `AGENT.md`
- ✅ Updated all internal `.claude` references in `sim/MATH.md`, `.agent/CONTEXT.md`, `.agent/math/PLAN.md`
- ✅ Added Guideline #14 (Plannotator Mandatory Review Workflow) to `.agent/GUIDELINES.md`
- ✅ Phase 5 plan submitted and **approved** via Plannotator
### Phase 5 Implementation (IN PROGRESS)
- ✅ **DC1**: Removed dead `LP.print_stats()` method (26 lines) from `sim/core.py`
- ✅ **L1-L6**: Removed unused imports across 13 files (7 scenario files removed `fmt`, whale.py also removed `V`, test files cleaned). Note: `late.py` keeps `fmt` since it's actually used on line 102
- ✅ **CC1**: Added `ProtocolError`, `MintCapExceeded`, `NothingStaked` exception classes to `sim/core.py`, replaced both `raise Exception(...)` calls
- ✅ **CC2**: Removed `verbose: bool = True` param from all 12 scenario functions, changed `v = verbosity if verbose else 0` → `v = verbosity`
- ✅ Tests passed 220/220 after DC1+L1-L6 (validated mid-way)
- 🔧 **CC3+PY3**: Started — changed imports in core.py (added `NamedTuple`, `_product`, removed `Dict`, `List`, `Tuple`) — **NOW HAS LSP ERRORS** that need fixing
- ⬜ **PY1**: Not yet done (MODELS generation with itertools.product)
- ⬜ **TY1-TY5**: Not yet done (typing fixes)
- ⬜ **DU1**: Not yet done (extract curve dispatch)
## 4. Remaining Tasks
### Immediate (fix broken state)
1. **Fix LSP errors in core.py**: The last edit replaced `Dict, List, Tuple` imports with nothing (TY5 was premature). Need to replace all `Dict[` → `dict[`, `List[` → `list[`, `Tuple[` → `tuple[` throughout core.py (~14 occurrences), OR re-add the imports temporarily and do TY5 as a separate step.
### Phase 5 remaining items
2. **CC3+PY3**: Convert `CompoundingSnapshot` (line 169) and `UserSnapshot` (line 222) to `NamedTuple`
3. **PY1**: Replace MODELS generation loop (lines 111-123) with `itertools.product` + dict comprehension
4. **TY1**: Add `assert self.k is not None` before CP buy/sell arithmetic
5. **TY2**: `Formatter.lp` → `Optional['LP'] = None` in formatter.py
6. **TY3**: Initialize `v` at top of CLI dispatch in `run_model.py`
7. **TY4**: Consider `total=True` for TypedDict required fields
8. **TY5**: `List[str]` → `list[str]`, `Dict[str, ...]` → `dict[str, ...]` throughout (Python 3.9+)
9. **DU1**: Extract curve dispatch — `_get_integral_fn()` returns `(integral_fn, price_fn)` tuple, stored on LP at construction
10. **Run tests**: 220/220 must pass
11. **Review via Plannotator**: Submit final review of all Phase 5 changes
## 5. Active Working Context
### Files currently being edited
- **`sim/core.py`** — BROKEN STATE: imports removed `Dict, List, Tuple` but 14+ references remain. Current line count ~780 (was 807, removed 26-line print_stats). Exception classes added at lines 12-19. `CompoundingSnapshot` at ~169, `UserSnapshot` at ~222, MODELS loop at ~111-123.
- **`sim/formatter.py`** — Needs TY2 fix (`self.lp` typing)
- **`sim/run_model.py`** — Needs TY3 fix (`v` initialization)
### Key code in progress
The import line in core.py currently reads:
```python
from typing import Callable, NamedTuple, Optional, TypedDict
```
But the file still uses `Dict[...]`, `List[...]`, `Tuple[...]` in ~14 places (MODELS dict, LP class, result TypedDicts, create_model return type).
### State
- TODO list is tracked via `mcp_todowrite` with DC1, L1-L6, CC1, CC2 marked completed; CC3+PY3 pending
- The plan was approved with phases numbered 5-10 (not 5A-5F)
- User wants git staging after each phase completion
## 6. Explicit Constraints (Verbatim Only)
- "you will always review plans with me using `/submit-plan` command"
- "you will always review your code changes (after milestone or completion) using `/submit-plan` or `/plannotator-review` command"
- "you will always show me summaries at the end of your work using `/submit-plan` or `/plannotator-annotate`"
- "you will always use Plannotator above & you will ensure it was actually opened & feedback was submitted"
- "Let's first perform Phase 5. And than other Phases. Let's review changes of each Phase separately. I will stage changes in git after each successful Phase"
- Guidelines #1-14 in `.agent/GUIDELINES.md` (especially #8 Root Cause Fixes, #9 Tests & Quality, #12 Honest Critique, #14 Plannotator workflow)
## 7. Agent Verification State
- **Current Agent**: Main Claude Code session
- **Verification Progress**: Tests validated 220/220 after DC1+L1-L6+CC1 changes
- **Pending Verifications**: Need full test run after completing all Phase 5 items (CC3, PY1, TY1-5, DU1)
- **Previous Rejections**: Plan was rejected once (user wanted Phase 5A→5, 5B→6, etc. numbering and phase-by-phase execution). Revised and approved.
- **Acceptance Status**: Phase 5 plan approved. Implementation ~50% complete. Core.py currently has LSP errors that must be fixed before continuing.
## 8. Delegated Agent Sessions
### Active/Recent Delegated Sessions
- **explore** (completed): Find all import lines in scenario and test files | session: `ses_39770f42fffenVLjnP9Tzgi0u4` — Results already consumed. Found import statements across all 16 files, confirmed which imports are unused.
## Relevant Files / Directories
### Config / Docs (read + edited)
- `.agent/AGENT.md` — orientation doc (renamed from CLAUDE.md)
- `.agent/CONTEXT.md` — operational context (updated .claude→.agent refs)
- `.agent/GUIDELINES.md` — coding standards (added guideline #14)
- `.agent/MISSION.md` — design principles (read-only)
- `.agent/math/PLAN.md` — implementation plan (updated .claude→.agent refs, this IS the plan)
- `.agent/math/FINDINGS.md` — math analysis (read-only)
- `.agent/math/VALUES.md` — reference data (read-only)
### Source (edited in Phase 5)
- `sim/core.py` — **ACTIVE, BROKEN STATE** (DC1, CC1, partial CC3/PY1/TY5)
- `sim/formatter.py` — read, pending TY2
- `sim/run_model.py` — read, pending TY3
- `sim/scenarios/single_user.py` — edited (L1, CC2)
- `sim/scenarios/multi_user.py` — edited (L1, CC2)
- `sim/scenarios/bank_run.py` — edited (L1, CC2)
- `sim/scenarios/whale.py` — edited (L1 + removed V, CC2)
- `sim/scenarios/hold.py` — edited (L1, CC2)
- `sim/scenarios/late.py` — edited (CC2 only, keeps fmt)
- `sim/scenarios/partial_lp.py` — edited (L1, CC2)
- `sim/scenarios/real_life.py` — edited (L1, CC2)
- `sim/test/helpers.py` — edited (removed unused D import)
- `sim/test/test_stress.py` — edited (removed 7 unused imports)
- `sim/test/test_coverage_gaps.py` — edited (removed Vault, LP, VAULT_APY)
- `sim/test/test_curves.py` — edited (removed CAP, DUST)
- `sim/test/test_scenarios.py` — edited (removed DUST)
- `sim/test/test_yield_accounting.py` — edited (removed DUST)
- `sim/MATH.md` — edited (updated .claude→.agent link)
---
Instructions
- Priority 1: Fix the broken core.py — it's missing Dict, List, Tuple imports but still references them. Either re-add them and do TY5 separately, or do TY5 now (replace all Dict[ → dict[, List[ → list[, Tuple[ → tuple[ throughout).
- Complete remaining Phase 5 items: CC3+PY3, PY1, TY1-TY5, DU1
- Run python3 -m sim.test.run_all — must get 220/220
- Submit final review via Plannotator (/submit-plan or /plannotator-review)
- User will git-stage after approval
Discoveries
- ast_grep_replace with dryRun=false did NOT persist changes in this environment — had to fall back to manual edits
- late.py actually uses fmt (line 102) — don't remove it from that file
- test_curves.py:183 catches Exception and checks message "Cannot mint over cap" — the new MintCapExceeded(ProtocolError(Exception)) still matches since it inherits from Exception
- The verbose: bool param was never passed by any caller (grep verbose= found 0 matches)
