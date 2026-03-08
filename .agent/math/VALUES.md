# Reference Data — Current Scenario Results

All data captured post-price-offset (log/poly start at base_price=1.0).
7 active models: CYN, EYN, SYN, LYN, P15YN, P20YN, P25YN.

---

## Compounding Formula

```
Vault after N days = Principal * (1 + APY/365)^N
100 days @ 5% APY: multiplier = 1.013792, yield factor = 0.013792
```

---

## Comparison Table (All Models × All Scenarios)

`+` = total profits, `-` = total losses, `#` = loser count, `V` = vault residual

| Scenario | CYN +/- | EYN +/- | SYN +/- | LYN +/- | P15YN +/- | P20YN +/- | P25YN +/- |
|----------|---------|---------|---------|---------|-----------|-----------|-----------|
| **Single** | +14 / 0 | +14 / 0 | +15 / 0 | +16 / 0 | +14 / 0 | +15 / 0 | +20 / 0 |
| **Multi** | +1337 / -1201 (1L) | +218 / -137 (2L) | +288 / -207 (2L) | +419 / -338 (2L) | +112 / -31 (1L) | +557 / -476 (2L) | +1212 / -1129 (3L) |
| **Multi R** | +1797 / -1611 (2L) | +128 / -14 (1L) | +128 / -14 (1L) | +129 / -12 (1L) | +126 / -14 (1L) | +136 / -17 (1L) | +142 / -24 (1L) V:14 |
| **Bank** | +7140 / -5788 (3L) | +988 / -551 (5L) | +964 / -526 (4L) | +1119 / -676 (5L) | +667 / -234 (2L) | +2030 / -1581 (7L) | +3221 / -2747 (8L) |
| **Bank R** | +7861 / -6509 (6L) | +581 / -143 (1L) | +578 / -140 (1L) | +579 / -136 (1L) | +573 / -140 (1L) | +601 / -151 (1L) | +312 / -115 (4L) V:276 |
| **Hold Bfr** | +1225 / -1139 (2L) | +120 / -82 (1L) V:11 | +134 / -111 (1L) V:26 | +139 / -154 (1L) V:64 | +65 / -17 (2L) | +317 / -292 (3L) V:26 | +201 / -486 (2L) V:338 |
| **Hold Wth** | +240 / -173 (2L) | +211 / -170 (2L) V:8 | +282 / -250 (2L) V:18 | +412 / -409 (2L) V:48 | +84 / -36 (2L) | +550 / -501 (2L) V:3 | +1212 / -1155 (3L) |
| **Hold Aft** | +240 / -173 (2L) | +211 / -170 (2L) V:8 | +282 / -250 (2L) V:18 | +412 / -409 (2L) V:48 | +84 / -36 (2L) | +550 / -501 (2L) V:3 | +1212 / -1155 (3L) |
| **Late 90d** | +1376 / -1229 (1L) | +251 / -156 (2L) | +323 / -227 (2L) | +456 / -358 (2L) | +150 / -57 (1L) | +597 / -497 (2L) | +1265 / -1153 (3L) |
| **Late 180** | +1445 / -1242 (1L) | +298 / -164 (1L) | +365 / -230 (2L) | +501 / -362 (2L) | +208 / -76 (1L) | +644 / -504 (2L) | +1318 / -1160 (3L) |
| **PartialLP** | +159 / -106 (2L) | +208 / -174 (2L) V:11 | +278 / -254 (2L) V:21 | +408 / -413 (2L) V:50 | +81 / -38 (2L) | +541 / -502 (2L) V:6 | +1085 / -1122 (3L) V:89 |
| **Whale** | +41461 / -39982 (1L) | +17012 / -14637 (1L) | +1454 / 0 (0L) | +3085 / -1529 (1L) | +7480 / -5518 (1L) | +29138 / -26915 (1L) | +40712 / -38428 (1L) |
| **Whale R** | +15240 / -13761 (1L) | +298 / -1769 (3L) V:3846 | +2447 / -993 (3L) | +2555 / -999 (3L) | +1322 / -27 (2L) V:667 | +827 / -8536 (4L) V:9931 | +1603 / -14925 (5L) V:15606 |
| **RealLife** | +1425 / -1337 (2L) | +183 / -121 (1L) | +244 / -183 (2L) | +359 / -300 (1L) | +97 / -35 (1L) | +404 / -343 (2L) | +835 / -773 (3L) |
| **Stochastic** | +7476 / -7045 (3L) | +944 / -781 (6L) | +844 / -681 (6L) | +1015 / -848 (6L) | +471 / -311 (5L) | +2144 / -1974 (8L) | +3482 / -3293 (9L) |

`L` = losers, `V` = vault residual (only shown when non-zero).

---

## Key Observations

| Observation | Detail |
|------------|--------|
| **Zero residual** | Most scenarios across all models show V=0. Residuals appear mainly in Hold, PartialLP, and Reverse Whale. |
| **P15YN is gentlest** | Fewest losers and smallest losses across most scenarios. Sub-quadratic growth is the most fair. |
| **P25YN is steepest** | Highest profits AND highest losses. Super-quadratic amplifies first-mover advantage. |
| **SYN whale-proof** | Whale scenario: SYN is the only model with 0 losers (sigmoid ceiling limits whale's impact). |
| **Reverse whale stress** | Whale exiting first causes large residuals in steeper curves (P20YN: 9.9k, P25YN: 15.6k). |

---

## Key Invariants (Verified)

1. **LP phase conservation**: After all LP removals, vault ≈ buy_usdc
2. **Yield distribution completeness**: LP yield + buy yield = total vault yield
3. **System conservation**: deposits + yield = withdrawals + residual
4. **buy_usdc unchanged by LP removal**: `remove_liquidity()` only decrements lp_usdc
5. **All curves start at base_price = 1.0**: EXP, SIG, LOG, POLY all return p(0) ≈ 1.0
