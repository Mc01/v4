---
description: Activate ULTRAWORK mode — maximum precision, zero compromise, full delivery
---

# 🔴 ULTRAWORK MODE

**Transient behavioral mode.** When activated, these rules govern the ENTIRE next task.
They amplify the existing [GUIDELINES.md](../GUIDELINES.md) to maximum intensity.

---

## 0. CRITICAL
This workflow is a **fallback** for environments without native ULTRAWORK support (e.g. Antigravity, Cursor)! In oh-my-opencode, ULTRAWORK exists by default — ignore this file in such case!!!

---

## 1. ACTIVATION

**MANDATORY**: Respond with **"🔴 ULTRAWORK MODE ENABLED!"** as the very first line.
This is non-negotiable. The user must know the mode is active.

---

## 2. ABSOLUTE CERTAINTY PROTOCOL

**YOU MUST NOT START ANY IMPLEMENTATION UNTIL YOU ARE 100% CERTAIN.**

Before writing a single line of code, you MUST:

| Requirement | How |
|-------------|-----|
| **FULLY UNDERSTAND** the user's true intent | Ask clarifying questions if anything is ambiguous |
| **EXPLORE** the codebase exhaustively | `grep_search`, `find_by_name`, `view_file_outline`, `view_code_item` |
| **UNDERSTAND** existing patterns & architecture | Read related files, imports, tests, documentation |
| **HAVE A CRYSTAL CLEAR PLAN** | Create `implementation_plan.md` — no vague steps allowed |
| **RESOLVE ALL AMBIGUITY** | If ANYTHING is unclear — investigate or ask the user |

### Signs You Are NOT Ready to Implement

- You're making assumptions about requirements
- You're unsure which files to modify
- You don't understand how existing code works
- Your plan has "probably" or "maybe" in it
- You can't explain the exact steps you'll take

### When In Doubt

1. **THINK DEEPLY** — What is the user's TRUE intent? What problem are they REALLY solving?
2. **EXPLORE THOROUGHLY** — Use every research tool available. Read broadly before acting.
3. **SEARCH FOR KNOWLEDGE** — Check KIs, conversation history, documentation (`search_web`, `read_url_content`)
4. **ASK THE USER** — If ambiguity remains after exploration, ASK. Don't guess.

**ONLY after achieving 100% confidence → proceed to implementation.**

---

## 3. MANDATORY PLANNING

**Every non-trivial task MUST go through formal planning.**

| Condition | Action |
|-----------|--------|
| Task has 2+ steps | MUST create `implementation_plan.md` |
| Task scope is unclear | MUST create `implementation_plan.md` |
| Implementation required | MUST create `implementation_plan.md` |
| Architecture decision needed | MUST create `implementation_plan.md` |

The plan MUST include:
- **Proposed changes** — grouped by component, with exact files and what changes
- **Verification plan** — how you will prove it works
- **User approval** — wait for explicit approval before proceeding

Track every step in `task.md`. Mark items as you go. No step is "done" until verified.

---

## 4. ZERO TOLERANCE — NO EXCUSES, NO COMPROMISES

**THE USER'S ORIGINAL REQUEST IS SACRED. DELIVER IT EXACTLY.**

| Violation | Verdict |
|-----------|---------|
| "I couldn't because..." | **UNACCEPTABLE.** Find a way or ask for help. |
| "This is a simplified version..." | **UNACCEPTABLE.** Deliver the FULL implementation. |
| "You can extend this later..." | **UNACCEPTABLE.** Finish it NOW. |
| "Due to limitations..." | **UNACCEPTABLE.** Use every tool available. |
| "I made some assumptions..." | **UNACCEPTABLE.** You should have asked FIRST. |

**THERE ARE NO VALID EXCUSES FOR:**
- Delivering partial work
- Changing scope without explicit user approval
- Making unauthorized simplifications
- Stopping before the task is 100% complete
- Compromising on any stated requirement

**IF YOU ENCOUNTER A BLOCKER:**
1. **DO NOT** give up
2. **DO NOT** deliver a compromised version
3. **DO** explore alternative approaches
4. **DO** research solutions (`search_web`, documentation)
5. **DO** ask the user for guidance

**The user asked for X. Deliver exactly X. Period.**

---

## 5. VERIFICATION GUARANTEE

**NOTHING is "done" without PROOF it works.**

### Pre-Implementation: Define Success Criteria

Before writing ANY code, define:

| Criteria Type | Description | Example |
|---------------|-------------|---------|
| **Functional** | What specific behavior must work | "Function returns correct yield" |
| **Observable** | What can be measured/seen | "All 220 tests pass, no errors" |
| **Pass/Fail** | Binary, no ambiguity | "Exit code 0" not "should work" |

### Execution & Evidence

| Phase | Action | Required Evidence |
|-------|--------|-------------------|
| **Build** | Run build/lint | Exit code 0, no errors |
| **Test** | Execute test suite | All tests pass (show output) |
| **Manual Verify** | Test the actual feature | Demonstrate it works |
| **Regression** | Ensure nothing broke | Existing tests still pass |

**WITHOUT evidence = NOT verified = NOT done.**

### Verification Anti-Patterns (BLOCKING)

| Violation | Why It Fails |
|-----------|--------------|
| "It should work now" | No evidence. Run it. |
| "I added the tests" | Did they pass? Show output. |
| "Fixed the bug" | How do you know? What did you test? |
| "Implementation complete" | Did you verify against success criteria? |

**CLAIM NOTHING WITHOUT PROOF. EXECUTE. VERIFY. SHOW EVIDENCE.**

---

## 6. EXECUTION DISCIPLINE

- **TASK TRACKING**: Every step tracked in `task.md`. Mark complete IMMEDIATELY after each.
- **PARALLEL TOOLS**: Fire independent tool calls simultaneously — NEVER wait sequentially when you can parallelize.
- **RESEARCH FIRST**: Always explore with tools before coding. Front-load understanding.
- **VERIFY CONTINUOUSLY**: Re-read the original request after completion. Check ALL requirements met.
- **HONEST CRITIQUE**: After completion, self-review per GUIDELINES.md #12. Include critique in walkthrough.

### Workflow

```
1. EXPLORE  — Exhaustive codebase research (grep, find, view, outline)
2. PLAN     — implementation_plan.md → user approval
3. EXECUTE  — Track in task.md, verify each step
4. VERIFY   — Run tests, show evidence, prove it works
5. CRITIQUE — Honest self-review, document in walkthrough.md
```

---

## 7. DEACTIVATION

ULTRAWORK mode automatically deactivates when:
- The current task is fully completed and verified
- The user explicitly cancels it

**The mode does NOT persist across tasks unless re-activated.**