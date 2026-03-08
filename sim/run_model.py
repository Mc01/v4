"""
╔═══════════════════════════════════════════════════════════════════════════╗
║            Commonwealth Protocol - Model Test Suite                       ║
╚═══════════════════════════════════════════════════════════════════════════╝

Tests 7 active models (*YN) defined in MODELS.md:
- 5 curve types: Constant Product (C), Exponential (E), Sigmoid (S), Logarithmic (L), Polynomial (P)
- 4 fixed invariants:
  - Token Inflation = always yes
  - Buy/Sell impacts price = always yes
  - Yield -> Price = always yes
  - LP -> Price = always no

Usage:
    python test_model.py                  # Compare 7 active *YN models
    python test_model.py CYN              # Detailed scenarios for one model
    python test_model.py CYN,EYN,SYN      # Compare specific models
    python test_model.py --all            # Include archived models
    python test_model.py --multi CYN      # Multi-user scenario for one model
    python test_model.py --bank CYN       # Bank run scenario for one model
"""
import argparse
import sys
from decimal import Decimal as D
from typing import Union, cast

from .core import (
    MODELS, ACTIVE_MODELS, CURVE_NAMES, Color,
    SingleUserResult, MultiUserResult, BankRunResult,
    ScenarioResult,
)

# Union of all result types for the comparison table formatter
AnyScenarioResult = Union[SingleUserResult, MultiUserResult, BankRunResult, ScenarioResult]

from .scenarios import (
    single_user_scenario,
    multi_user_scenario,
    bank_run_scenario,
    reverse_multi_user_scenario,
    reverse_bank_run_scenario,
    hold_before_scenario,
    hold_with_scenario,
    hold_after_scenario,
    late_90_scenario,
    late_180_scenario,
    partial_lp_scenario,
    whale_scenario,
    reverse_whale_scenario,
    real_life_scenario,
    stochastic_scenario,
)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          COMPARISON TABLE                                 ║
# ╠═══════════════════════════════════════════════════════════════════════════╣
# ║  Transposed layout: scenarios as rows, models as columns.                 ║
# ║  Each cell shows: total gains, total losses, loser count, vault residual. ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def run_comparison(codenames: list[str]) -> None:
    """Run all scenarios across models and print a side-by-side comparison table."""
    C = Color
    
    print(f"\n{C.DIM}Running scenarios...{C.END}", end="", flush=True)
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │              Collect Results: Run Every Scenario for Each Model       │
    # └───────────────────────────────────────────────────────────────────────┘

    model_results: dict[str, dict[str, AnyScenarioResult]] = {}
    for code in codenames:
        model_results[code] = {
            "single": single_user_scenario(code, verbosity=0),
            "multi": multi_user_scenario(code, verbosity=0),
            "bank": bank_run_scenario(code, verbosity=0),
            "rmulti": reverse_multi_user_scenario(code, verbosity=0),
            "rbank": reverse_bank_run_scenario(code, verbosity=0),
            "hold_before": hold_before_scenario(code, verbosity=0),
            "hold_with": hold_with_scenario(code, verbosity=0),
            "hold_after": hold_after_scenario(code, verbosity=0),
            "late_90": late_90_scenario(code, verbosity=0),
            "late_180": late_180_scenario(code, verbosity=0),
            "partial": partial_lp_scenario(code, verbosity=0),
            "whale": whale_scenario(code, verbosity=0),
            "rwhale": reverse_whale_scenario(code, verbosity=0),
            "real": real_life_scenario(code, verbosity=0),
            "stochastic": stochastic_scenario(code, verbosity=0),
        }
    
    print(f"\r{' ' * 30}\r", end="")
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                            Formatters                                 │
    # └───────────────────────────────────────────────────────────────────────┘

    def fmt_profit(val: D, width: int = 7, decimals: int = 0) -> str:
        """Format profit with color."""
        num = int(val) if decimals == 0 else float(val)
        if decimals == 0:
            raw = f"{num:,}".replace(",", "_")
            formatted = f"{raw:>{width}}"
        else:
            formatted = f"{num:>{width}.{decimals}f}"
        if val > 0:
            return f"{C.GREEN}{formatted}{C.END}"
        elif val < 0:
            return f"{C.RED}{formatted}{C.END}"
        return formatted
    
    def fmt_losers(n: int, width: int = 1) -> str:
        formatted = f"{n:>{width}d}"
        if n > 0:
            return f"{C.RED}{formatted}{C.END}"
        return formatted
    
    def fmt_vault(val: D, width: int = 5) -> str:
        """Format vault with color."""
        displayed = round(float(val))
        raw = f"{displayed:,}".replace(",", "_")
        formatted = f"{raw:>{width}}"
        if displayed != 0:
            return f"{C.YELLOW}{formatted}{C.END}"
        return formatted
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                           Table Header                                │
    # └───────────────────────────────────────────────────────────────────────┘

    print()
    print(f"{C.BOLD}{C.HEADER}{'='*60}{C.END}")
    print(f"{C.BOLD}{C.HEADER}  MODEL COMPARISON{C.END}")
    print(f"{C.BOLD}{C.HEADER}{'='*60}{C.END}")
    print()
    
    # Sub-column widths: +(gains) -(losses) #(losers) V(vault) — compact
    GAIN_W, LOSS_W, NUM_W, VLT_W = 7, 7, 1, 6
    # Cell = 1 + GAIN_W + 1 + LOSS_W + 1 + NUM_W + 1 + VLT_W + 1 = 26
    CELL_W = 1 + GAIN_W + 1 + LOSS_W + 1 + NUM_W + 1 + VLT_W + 1
    SCN_W = 10  # Scenario label width
    
    hdr = f"  {'Scenario':<{SCN_W}}│"
    for code in codenames:
        hdr += f"{code:^{CELL_W}}│"
    print(hdr)

    hdr_sep = f"  {'─'*SCN_W}┼"
    for _ in codenames:
        hdr_sep += f"{'─'*CELL_W}┼"
    print(hdr_sep)

    sub_hdr = f"  {'':>{SCN_W}}│"
    for _ in codenames:
        sub_hdr += f" {C.CYAN}{'+':{f'>{GAIN_W}'}} {'-':{f'>{LOSS_W}'}} {'#':{f'>{NUM_W}'}} {'V':{f'>{VLT_W}'}}{C.END} │"
    print(sub_hdr)
    
    sep = f"  {'─'*SCN_W}┼"
    for _ in codenames:
        sep += f"{'─'*CELL_W}┼"
    print(sep)
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                      Rows: One Per Scenario                           │
    # └───────────────────────────────────────────────────────────────────────┘

    scenarios = [
        ("single", "Single", False),
        ("multi", "Multi", True),
        ("rmulti", "Multi R", True),
        ("bank", "Bank", True),
        ("rbank", "Bank R", True),
        ("hold_before", "Hold Bfr", True),
        ("hold_with", "Hold Wth", True),
        ("hold_after", "Hold Aft", True),
        ("late_90", "Late 90d", True),
        ("late_180", "Late 180", True),
        ("partial", "PartialLP", True),
        ("whale", "Whale", True),
        ("rwhale", "Whale R", True),
        ("real", "RealLife", True),
        ("stochastic", "Stochastc", True),
    ]
    
    for scenario_key, scenario_label, is_group in scenarios:
        row = f"  {scenario_label:<{SCN_W}}│"

        for code in codenames:
            result = model_results[code][scenario_key]

            if not is_group:
                r = cast(SingleUserResult, result)
                profit = r["profit"]
                g = fmt_profit(profit, GAIN_W, 1)
                v = fmt_vault(r["vault_remaining"], VLT_W)
                row += f" {g} {C.DIM}{'-':>{LOSS_W}} {'-':>{NUM_W}}{C.END} {v} │"
            else:
                r = cast(Union[MultiUserResult, BankRunResult], result)
                profits = list(r["profits"].values())
                plus = sum((p for p in profits if p > 0), D(0))
                minus = sum((p for p in profits if p < 0), D(0))
                bank = cast(BankRunResult, result)
                losers = bank.get("losers", sum(1 for p in profits if p <= 0))

                g = fmt_profit(plus, GAIN_W)
                l = fmt_profit(minus, LOSS_W)
                n = fmt_losers(losers, NUM_W)
                v = fmt_vault(r["vault"], VLT_W)
                row += f" {g} {l} {n} {v} │"

        print(row)
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                              Legend                                   │
    # └───────────────────────────────────────────────────────────────────────┘

    print()
    print(f"  {C.DIM}+ = total profits │ - = total losses │ # = loser count │ V = vault residual{C.END}")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                           CLI ENTRY POINT                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Commonwealth Protocol - Model Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_model.py                    # Compare 7 active *YN models (table view)
  python test_model.py CYN                # All scenarios for one model (verbose)
  python test_model.py CYN,EYN,SYN        # Compare specific models (table view)
  python test_model.py --all              # Include all 16 models (incl. archived)
  python test_model.py --single           # Single-user scenario for active models
  python test_model.py --multi CYN        # Multi-user scenario for one model
  python test_model.py --bank CYN,EYN     # Bank run scenario for specific models
  python test_model.py --rmulti           # Reverse multi-user (last buyer exits first)
  python test_model.py --rbank            # Reverse bank run (last buyer exits first)
  python test_model.py --hold CYN         # Hold scenario (passive holder dilution)
  python test_model.py --late CYN         # Late entrant scenario (first-mover advantage)
  python test_model.py --partial CYN      # Partial LP scenario (mixed strategies)
  python test_model.py --whale CYN        # Whale entry scenario (concentration/slippage)
  python test_model.py --rwhale CYN       # Reverse whale (whale exits first)
  python test_model.py --real CYN         # Real life scenario (continuous flow)
  python test_model.py --stochastic CYN   # Stochastic scenario (random arrivals)
"""
    )
    parser.add_argument(
        "models", nargs="?", default=None,
        help="Model code(s) to test, comma-separated (e.g., CYN or CYN,EYN,SYN). Default: active *YN models."
    )
    parser.add_argument(
        "--all", "-a", action="store_true", dest="include_all",
        help="Include archived models (non-*YN) in comparison"
    )
    parser.add_argument(
        "--single", action="store_true",
        help="Run single-user scenario (verbose if one model)"
    )
    parser.add_argument(
        "--multi", action="store_true",
        help="Run multi-user scenario (verbose if one model)"
    )
    parser.add_argument(
        "--bank", action="store_true",
        help="Run bank run scenario (verbose if one model)"
    )
    parser.add_argument(
        "--rmulti", action="store_true",
        help="Run reverse multi-user scenario (LIFO exit order)"
    )
    parser.add_argument(
        "--rbank", action="store_true",
        help="Run reverse bank run scenario (LIFO exit order)"
    )
    parser.add_argument(
        "--hold", action="store_true",
        help="Run hold scenarios (passive holder before/with/after LPers)"
    )
    parser.add_argument(
        "--late", action="store_true",
        help="Run late entrant scenarios (90d and 180d wait periods)"
    )
    parser.add_argument(
        "--partial", action="store_true",
        help="Run partial LP scenario (heterogeneous LP strategies)"
    )
    parser.add_argument(
        "--whale", action="store_true",
        help="Run whale entry scenario (concentration/slippage test)"
    )
    parser.add_argument(
        "--rwhale", action="store_true",
        help="Run reverse whale scenario (whale exits first)"
    )
    parser.add_argument(
        "--real", action="store_true",
        help="Run real life scenario (continuous entry/exit flow)"
    )
    parser.add_argument(
        "--stochastic", action="store_true",
        help="Run stochastic scenario (random arrivals over time)"
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Verbosity level: -v (VERBOSE), -vv (DEBUG). Default: NORMAL."
    )
    
    args = parser.parse_args()
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │              Parse and Validate Model Codes                           │
    # └───────────────────────────────────────────────────────────────────────┘

    if args.models:
        codes = [c.strip().upper() for c in args.models.split(",")]
        for code in codes:
            if code not in MODELS:
                print(f"Unknown model: {code}")
                print(f"Available: {', '.join(sorted(MODELS.keys()))}")
                sys.exit(1)
    else:
        codes = list(MODELS.keys()) if args.include_all else ACTIVE_MODELS
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │     Dispatch: Comparison Table (Multiple) or Verbose (Single)         │
    # └───────────────────────────────────────────────────────────────────────┘

    run_single = args.single
    run_multi = args.multi
    run_bank = args.bank
    run_rmulti = args.rmulti
    run_rbank = args.rbank
    run_hold = args.hold
    run_late = args.late
    run_partial = args.partial
    run_whale = args.whale
    run_rwhale = args.rwhale
    run_real = args.real
    run_stochastic = args.stochastic
    
    any_flag = (run_single or run_multi or run_bank or run_rmulti or run_rbank or
                run_hold or run_late or run_partial or run_whale or run_rwhale or
                run_real or run_stochastic)
    run_all = not any_flag
    
    verbose = len(codes) == 1
    verbosity = args.verbose  # 1, 2, or 3
    
    # Verbosity level for scenario output
    v: int = args.verbose if args.verbose > 0 else 1

    # Show comparison table only when no specific flags and multiple models
    if run_all and not verbose:
        run_comparison(codes)
    
    # Run specific scenario if flags provided
    if args.single:
        for code in codes:
            single_user_scenario(code, verbosity=v)

    if args.multi:
        for code in codes:
            multi_user_scenario(code, verbosity=v)

    if args.bank:
        for code in codes:
            bank_run_scenario(code, verbosity=v)

    if args.rmulti:
        for code in codes:
            reverse_multi_user_scenario(code, verbosity=v)

    if args.rbank:
        for code in codes:
            reverse_bank_run_scenario(code, verbosity=v)

    if args.hold:
        for code in codes:
            # All 3 hold variants for now
            hold_before_scenario(code, verbosity=v)
            hold_with_scenario(code, verbosity=v)
            hold_after_scenario(code, verbosity=v)

    if args.late:
        for code in codes:
            late_90_scenario(code, verbosity=v)
            late_180_scenario(code, verbosity=v)

    if args.partial:
        for code in codes:
            partial_lp_scenario(code, verbosity=v)
        
    if args.whale:
        for code in codes:
            whale_scenario(code, verbosity=v)

    if args.rwhale:
        for code in codes:
            reverse_whale_scenario(code, verbosity=v)

    if args.real:
        for code in codes:
            real_life_scenario(code, verbosity=v)

    if args.stochastic:
        for code in codes:
            stochastic_scenario(code, verbosity=v)
