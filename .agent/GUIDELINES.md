# Project Guidelines

These guidelines define the standards for code quality, style, and philosophy for this project.

1.  **Clean & Readable Code**
    - Write clean, concise, and readable code.
    - Code should be self-explanatory where possible.

2.  **Consistency**
    - Look for existing patterns and principles.
    - Maintain consistent ordering, rules, and naming conventions throughout the codebase.

3.  **Comments & Cleanup**
    - Cleanup files from unnecessary comments.
    - Comments should be helpful and increase readability, not just describe obvious code.
    - Remove unused imports.
    - Ensure files are up to date with documentation.

4.  **Structure & Visuals**
    - Favour comment blocks / ASCII-art style banners to group code blocks into sections.
    - This improves readability and navigation.

5.  **Rich Output**
    - Rich pretty-printing is important.
    - Fit output into verbosity levels:
        - `-v`: (Default) Necessary printing.
        - `-vv`: Extended, enriches info for debugging.
        - `-vvv`: Maximum information.

6.  **Typing**
    - Use strong typing.
    - Ensure `pylance` and `pyright` linters/type-checkers run flawlessly.

7.  **Math & Precision**
    - Favour `Decimal` over `float` or `integer` where clean and sensible.
    - Treat math like an art.

8.  **Root Cause Fixes**
    - Always aim to fix the real issue.
    - Avoid shortcuts, dirty solutions, or hiding/clamping errors.

9.  **Tests & Quality**
    - Treat code, math, and comments like an art.
    - Treat tests as the preference to ensure this art runs flawlessly.
    - Extend tests often: add unit tests or new tests based on findings/bugs.
    - Run tests to confirm modifications at the end.

10. **Benchmarking**
    - Treat running scenarios as benchmarks.
    - Aim for the best numbers possible and improve them.
    - Recommend and consult on ideas to improve scenarios, models, and outputs.

11. **Documentation Consistency**
    - Documentation (e.g., `CONTEXT.md`) MUST be accurate.
    - If you find a command or instruction that doesn't work, fix the documentation immediately.
    - Don't leave broken instructions for others to stumble over.

12. **Honest Critique Phase**
    - After completing a task, launch a "subagent" (or rigorous self-review) to critique the work.
    - Check for: regressions, unclean code, potential improvements.
    - **Ask critical questions**:
        - "If I removed X, what mechanism now ensures Y works?"
        - "Who else relied on this code/state?"
        - "What happens if external state (e.g., yield, time) changes?"
    - Be honest: identify if a solution is "dirty" or "clamped" vs "real fix".
    - Include this critique in your final summary.

13. **Unexpected Issues -> Return to Planning**
    - When finding something unexpected, difficult, or a bug:
    - ALWAYS go back to the PLANNING phase.
    - Work with the user to explore, structure, and formalize a well-thought plan.
    - Do not just "patch" it on the fly.

14. **Mandatory Review Workflow**
    - All plans, code reviews, and summaries MUST be presented to the user for interactive review.
    - **Environment-aware tooling**:
        - **opencode** + Plannotator installed: Use Plannotator (`/submit-plan`, `/plannotator-review`, `/plannotator-annotate`).
        - **Antigravity / Cursor IDE**: Use the built-in plan verification and review tools provided by the environment.
    - **Plans**: Always verify the plan with the user at the beginning. Wait for explicit approval before proceeding.
    - **Code reviews**: After each milestone, review code changes in detail with the user. Walk through what changed and why.
    - **Summaries**: Always present summaries to the user at the end of work.
    - **Confirmation required**: Always require explicit confirmation from the user before continuing. Do not assume approval — wait for a response.
    - Never skip this step. Silent completion without review is not acceptable.
