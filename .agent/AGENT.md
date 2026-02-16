# Commonwealth Protocol — Agent Orientation

Commonwealth is a yield-bearing LP token protocol. Users buy tokens with USDC, provide liquidity, and earn yield from vault rehypothecation (5% APY). All vault yield is shared proportionally among liquidity providers — including yield from non-LPing users' USDC. This "common yield" is the core value proposition. We are validating the math in Python before writing Solidity.

**Start here, then read [CONTEXT.md](./CONTEXT.md) for operational details.**

---

## Reading Order

| # | File | When to read | What you learn |
|---|------|-------------|----------------|
| 1 | **[CONTEXT.md](./CONTEXT.md)** | Always | How to run, code locations, current problems, file map |
| 2 | **[MISSION.md](./MISSION.md)** | For design decisions | Value proposition, yield design, why buy_usdc_yield to LPs is intentional |
| 3 | **[math/FINDINGS.md](./math/FINDINGS.md)** | For analysis context | Root causes of vault residuals, mathematical proofs, known issues |
| 4 | **[math/PLAN.md](./math/PLAN.md)** | For implementation work | Exact code changes, execution order, success criteria |
| 5 | **[math/VALUES.md](./math/VALUES.md)** | For reference data | Manual calculations, scenario traces, actual vs expected numbers |
| 6 | **[../sim/MATH.md](../sim/MATH.md)** | For protocol math | All formulas, curve integrals, price multiplier mechanism |
| 7 | **[../sim/MODELS.md](../sim/MODELS.md)** | For model matrix | Codename convention, archived models, tradeoffs |
| 8 | **[../sim/TEST.md](../sim/TEST.md)** | For test env specifics | Virtual reserves, exposure factor, test-only mechanics |
| 9 | **[GUIDELINES.md](./GUIDELINES.md)** | For coding standards | Code style, principles, testing philosophy |

---

## Glossary

| Term | Definition |
|------|-----------|
| **Commonwealth** | Internal name for this protocol |
| **Bonding Curve** | Pricing function: determines token price from supply/reserves |
| **Vault** | External yield protocol (Spark/Sky/Aave) where all USDC earns 5% APY |
| **Rehypothecation** | Deploying user-deposited USDC into yield vaults |
| **LP** | Liquidity Provider — deposits tokens + USDC pair to earn yield |
| **Minting/Burning** | Creating/destroying tokens on buy/sell |
| **Token Inflation** | Minting new tokens for LPs at configurable APY |
| **Common Yield** | All vault yield shared among LPs — the core value proposition |
| **buy_usdc** | Aggregate USDC from token purchases (feeds into price) |
| **lp_usdc** | Aggregate USDC from LP deposits (does NOT feed into price in active models) |
| **effective_usdc** | `buy_usdc * (vault_balance / total_principal)` — yield-adjusted pricing input |
| **Price Multiplier** | `effective_usdc / buy_usdc` — how yield scales integral curve prices |
| **Fair Share Cap** | Limits withdrawals to proportional vault share (prevents bank runs) |
| **CYN/EYN/SYN/LYN** | Active models: [C]onstant/[E]xp/[S]igmoid/[L]og + [Y]ield->Price + [N]o LP->Price |

---

## Working Rules

1. **This is a testbed.** Validate math first. Get the math right before Solidity.
2. **Keep it simple.** Complexity should come from economic mechanics, not scaffolding.
3. **Track what matters.** Every model reports: total yield, yield per user, profit/loss per user, vault residual.
4. **Dual goal.** Attractive to users (everyone earns) AND sustainable for the protocol.
5. **Common good.** Models that structurally disadvantage late entrants must be identified and avoided.
