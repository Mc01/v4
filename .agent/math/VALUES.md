# Reference Data — Current Scenario Results

All data captured post-price-offset (log/poly start at base_price=1.0).
5 active models: CYN, EYN, SYN, LYN, P12YN, P15YN.

---

## Compounding Formula

```
Vault after N days = Principal * (1 + APY/365)^N
100 days @ 5% APY: multiplier = 1.013792, yield factor = 0.013792
```

---

## Comparison Table (All Models × All Scenarios)

`+` = total profits, `-` = total losses, `#` = loser count, `V` = vault residual

| Scenario | CYN +/- | EYN +/- | SYN +/- | LYN +/- | P12YN +/- | P15YN +/- |
|----------|---------|---------|---------|---------|-----------|-----------|
| **Single** | +14 / 0 | +14 / 0 | +15 / 0 | +16 / 0 | +14 / 0 | +14 / 0 |
| **Multi** | +1337 / -1201 (1L) | +218 / -137 (2L) | +288 / -207 (2L) | +419 / -338 (2L) | +84 / -3 (1L) | +112 / -31 (1L) |
| **Multi R** | +1797 / -1611 (2L) | +128 / -14 (1L) | +128 / -14 (1L) | +129 / -12 (1L) | +125 / -13 (1L) | +126 / -14 (1L) |
| **Bank** | +7140 / -5788 (3L) | +988 / -551 (5L) | +964 / -526 (4L) | +1119 / -676 (5L) | +590 / -159 (1L) | +667 / -234 (2L) |
| **Bank R** | +7861 / -6509 (6L) | +581 / -143 (1L) | +578 / -140 (1L) | +579 / -136 (1L) | +569 / -138 (1L) | +573 / -140 (1L) |
| **Hold Bfr** | +1225 / -1139 (2L) | +120 / -82 (1L) V:11 | +134 / -111 (1L) V:26 | +139 / -154 (1L) V:64 | +54 / -6 (1L) | +65 / -17 (2L) |
| **Hold Wth** | +240 / -173 (2L) | +211 / -170 (2L) V:8 | +282 / -250 (2L) V:18 | +412 / -409 (2L) V:48 | +58 / -9 (1L) | +84 / -36 (2L) |
| **Hold Aft** | +240 / -173 (2L) | +211 / -170 (2L) V:8 | +282 / -250 (2L) V:18 | +412 / -409 (2L) V:48 | +58 / -9 (1L) | +84 / -36 (2L) |
| **Late 90d** | +1376 / -1229 (1L) | +251 / -156 (2L) | +323 / -227 (2L) | +456 / -358 (2L) | +122 / -29 (1L) | +150 / -57 (1L) |
| **Late 180** | +1445 / -1242 (1L) | +298 / -164 (1L) | +365 / -230 (2L) | +501 / -362 (2L) | +179 / -48 (1L) | +208 / -76 (1L) |
| **PartialLP** | +159 / -106 (2L) | +208 / -174 (2L) V:11 | +278 / -254 (2L) V:21 | +408 / -413 (2L) V:50 | +50 / -7 (1L) | +81 / -38 (2L) |
| **Whale** | +41461 / -39982 (1L) | +17012 / -14637 (1L) | +1454 / 0 (0L) | +3085 / -1529 (1L) | +1563 / 0 (0L) | +7480 / -5518 (1L) |
| **Whale R** | +15240 / -13761 (1L) | +298 / -1769 (3L) V:3846 | +2447 / -993 (3L) | +2555 / -999 (3L) | +2370 / -807 (2L) | +1322 / -27 (2L) V:667 |
| **RealLife** | +1425 / -1337 (2L) | +183 / -121 (1L) | +244 / -183 (2L) | +359 / -300 (1L) | +73 / -10 (1L) | +97 / -35 (1L) |
| **Stochastic** | +7476 / -7045 (3L) | +944 / -781 (6L) | +844 / -681 (6L) | +1015 / -848 (6L) | +226 / -67 (2L) | +471 / -311 (5L) |

`L` = losers, `V` = vault residual (only shown when non-zero).

---

## Key Observations

| Observation | Detail |
|------------|--------|
| **Zero residual** | Most scenarios across all models show V=0. Residuals appear mainly in Hold, PartialLP, and Reverse Whale. |
| **P12YN is ideal** | Sub-quadratic scaling minimizes losers globally. 0 losers in the Whale scenario ensures high net worth actors are protected. |
| **P15YN is steeper** | Acts as an upper bound for polynomial curves. Noticeable slippage on massive exits vs P12YN. |
| **SYN whale-proof** | Whale scenario: SYN and P12YN both exhibit 0 losers due to managed slip limits. |
| **Reverse whale stress** | P12YN resolves the large residuals seen in steeper curves by preserving earlier liquidity thresholds. |

---

## Key Invariants (Verified)

1. **LP phase conservation**: After all LP removals, vault ≈ buy_usdc
2. **Yield distribution completeness**: LP yield + buy yield = total vault yield
3. **System conservation**: deposits + yield = withdrawals + residual
4. **buy_usdc unchanged by LP removal**: `remove_liquidity()` only decrements lp_usdc
5. **All curves start at base_price = 1.0**: EXP, SIG, LOG, POLY all return p(0) ≈ 1.0
