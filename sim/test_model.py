"""
Commonwealth Protocol - Model Test Suite

Tests 4 active models (*YN) defined in MODELS.md:
- 4 curve types: Constant Product (C), Exponential (E), Sigmoid (S), Logarithmic (L)
- 4 fixed invariants:
  - Token Inflation = always yes
  - Buy/Sell impacts price = always yes
  - Yield -> Price = always yes
  - LP -> Price = always no

Usage:
    python test_model.py                  # Compare 4 active *YN models
    python test_model.py CYN              # Detailed scenarios for one model
    python test_model.py CYN,EYN,SYN      # Compare specific models
    python test_model.py --all            # Include archived models
    python test_model.py --multi CYN      # Multi-user scenario for one model
    python test_model.py --bank CYN       # Bank run scenario for one model
"""
import argparse
import sys
from decimal import Decimal as D

# Import core infrastructure
from .core import (
    K, MODELS, ACTIVE_MODELS, CURVE_NAMES, Color,
    create_model, model_label, User, Vault, LP,
)

# Import scenarios
from .scenarios import (
    single_user_scenario,
    multi_user_scenario,
    bank_run_scenario,
    reverse_multi_user_scenario,
    reverse_bank_run_scenario,
)

# =============================================================================
# Comparison Output
# =============================================================================

def run_comparison(codenames: list[str]):
    """Run all scenarios for each model and print transposed comparison table.
    
    Transposed layout: Scenarios as rows, Models as columns.
    This format is optimized for many scenarios with fewer models.
    """
    C = Color
    
    print(f"\n{C.DIM}Running scenarios...{C.END}", end="", flush=True)
    
    # Collect results for each model
    model_results = {}
    for code in codenames:
        model_results[code] = {
            "single": single_user_scenario(code, verbose=False),
            "multi": multi_user_scenario(code, verbose=False),
            "bank": bank_run_scenario(code, verbose=False),
            "rmulti": reverse_multi_user_scenario(code, verbose=False),
            "rbank": reverse_bank_run_scenario(code, verbose=False),
        }
    
    print(f"\r{' ' * 30}\r", end="")  # Clear loading message
    
    # Curve abbreviations
    curve_abbr = {"Constant Product": "CP", "Exponential": "Exp", "Sigmoid": "Sig", "Logarithmic": "Log"}
    
    # Helper formatters
    def fmt_profit(val, width=7, decimals=0):
        """Format value with color: green positive, red negative."""
        v = float(val)
        fmt = f">{width}.{decimals}f"
        if v > 0:
            return f"{C.GREEN}{v:{fmt}}{C.END}"
        elif v < 0:
            return f"{C.RED}{v:{fmt}}{C.END}"
        return f"{v:{fmt}}"
    
    def fmt_losers(n, width=2):
        """Format loser count: red if > 0."""
        if n > 0:
            return f"{C.RED}{n:>{width}d}{C.END}"
        return f"{n:>{width}d}"
    
    def fmt_vault(val, width=5):
        """Format vault: yellow if != 0."""
        rounded = round(val, 2)
        if rounded != D(0):
            return f"{C.YELLOW}{float(val):>{width}.0f}{C.END}"
        return f"{float(val):>{width}.0f}"
    
    # Header
    print()
    print(f"{C.BOLD}{C.HEADER}{'='*60}{C.END}")
    print(f"{C.BOLD}{C.HEADER}  MODEL COMPARISON - FIFO vs LIFO {C.END}")
    print(f"{C.BOLD}{C.HEADER}{'='*60}{C.END}")
    print()
    
    # Build model column headers with curve type
    model_hdrs = []
    for code in codenames:
        cfg = MODELS[code]
        curve = curve_abbr.get(CURVE_NAMES[cfg["curve"]], "?")
        model_hdrs.append(f"{code}({curve})")
    
    # Sub-columns: +(5) -(5) #(2) V(4)
    GAIN_W, LOSS_W, NUM_W, VLT_W = 5, 5, 2, 4
    CELL_W = 24
    
    # Print header row (model names)
    hdr = f"  {'Scenario':<12}│"
    for mh in model_hdrs:
        hdr += f"{mh:^{CELL_W}}│"
    print(hdr)

    # Separator between scenario header and sub-header
    hdr_sep = f"  {'─'*12}┼"
    for _ in codenames:
        hdr_sep += f"{'─'*CELL_W}┼"
    print(hdr_sep)

    # Print sub-header row: " Gain │  Loss │ #L │"
    sub_hdr = f"  {'Stats':<12}│"
    for _ in codenames:
        sub_hdr += f" {C.DIM}{'+':>{GAIN_W}}  {'-':>{LOSS_W}}  {'#':>{NUM_W}}  {'V':>{VLT_W}}{C.END} │"
    print(sub_hdr)
    
    # Separator row matching sub-header positions
    sep = f"  {'─'*12}┼"
    for _ in codenames:
        sep += f"{'─'*CELL_W}┼"
    print(sep)
    
    # Scenario definitions
    scenarios = [
        ("single", "Single", False),
        ("multi", "Multi FIFO", True),
        ("bank", "Bank FIFO", True),
        ("rmulti", "Multi LIFO", True),
        ("rbank", "Bank LIFO", True),
    ]
    
    for scenario_key, scenario_label, is_group in scenarios:
        row = f"  {scenario_label:<12}│"

        for code in codenames:
            r = model_results[code][scenario_key]

            if not is_group:
                # Single: show profit in Gain column, dashes elsewhere
                profit = r["profit"]
                g = fmt_profit(profit, GAIN_W, 1)
                v = fmt_vault(r["vault_remaining"], VLT_W)
                row += f" {g}  {'─':>{LOSS_W}}  {'─':>{NUM_W}}  {v} │"
            else:
                # Multi/Bank: Gain, Loss, #Losers
                profits = list(r["profits"].values())
                plus = sum(p for p in profits if p > 0)
                minus = sum(p for p in profits if p < 0)
                losers = r.get("losers", sum(1 for p in profits if p <= 0))

                g = fmt_profit(plus, GAIN_W)
                l = fmt_profit(minus, LOSS_W)
                n = fmt_losers(losers, NUM_W)
                v = fmt_vault(r["vault"], VLT_W)
                row += f" {g}  {l}  {n}  {v} │"

        print(row)
    
    # Legend
    print()
    print(f"  {C.DIM}+ = total profits │ - = total losses │ # = loser count │ V = vault residual{C.END}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Commonwealth Protocol - Model Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_model.py                    # Compare 4 active *YN models (table view)
  python test_model.py CYN                # All scenarios for one model (verbose)
  python test_model.py CYN,EYN,SYN        # Compare specific models (table view)
  python test_model.py --all              # Include all 16 models (incl. archived)
  python test_model.py --single           # Single-user scenario for active models
  python test_model.py --multi CYN        # Multi-user scenario for one model
  python test_model.py --bank CYN,EYN     # Bank run scenario for specific models
  python test_model.py --rmulti           # Reverse multi-user (last buyer exits first)
  python test_model.py --rbank            # Reverse bank run (last buyer exits first)
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
    
    args = parser.parse_args()
    
    # Parse model codes
    if args.models:
        codes = [c.strip().upper() for c in args.models.split(",")]
        # Validate
        for code in codes:
            if code not in MODELS:
                print(f"Unknown model: {code}")
                print(f"Available: {', '.join(sorted(MODELS.keys()))}")
                sys.exit(1)
    else:
        # Default to active models, or all if --all flag is set
        codes = list(MODELS.keys()) if args.include_all else ACTIVE_MODELS
    
    # Determine which scenarios to run
    run_single = args.single
    run_multi = args.multi
    run_bank = args.bank
    run_rmulti = args.rmulti
    run_rbank = args.rbank
    run_all = not (run_single or run_multi or run_bank or run_rmulti or run_rbank)
    
    # Verbose mode for single model, comparison table for multiple
    verbose = len(codes) == 1
    
    if run_all and not verbose:
        # Full comparison table
        run_comparison(codes)
    else:
        # Individual scenarios
        for code in codes:
            if run_single or run_all:
                single_user_scenario(code, verbose=verbose)
            if run_multi or run_all:
                multi_user_scenario(code, verbose=verbose)
            if run_bank or run_all:
                bank_run_scenario(code, verbose=verbose)
            if run_rmulti or run_all:
                reverse_multi_user_scenario(code, verbose=verbose)
            if run_rbank or run_all:
                reverse_bank_run_scenario(code, verbose=verbose)