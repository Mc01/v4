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
    """Run all scenarios for each model and print comprehensive comparison table."""
    C = Color
    all_results = []
    
    print(f"\n{C.DIM}Running scenarios...{C.END}", end="", flush=True)
    
    for code in codenames:
        single_r = single_user_scenario(code, verbose=False)
        multi_r = multi_user_scenario(code, verbose=False)
        bank_r = bank_run_scenario(code, verbose=False)
        rmulti_r = reverse_multi_user_scenario(code, verbose=False)
        rbank_r = reverse_bank_run_scenario(code, verbose=False)
        all_results.append({
            "codename": code,
            "single": single_r,
            "multi": multi_r,
            "bank": bank_r,
            "rmulti": rmulti_r,
            "rbank": rbank_r,
        })
    
    print(f"\r{' ' * 30}\r", end="")  # Clear loading message
    
    # Header
    curve_abbr = {"Constant Product": "CP", "Exponential": "Exp", "Sigmoid": "Sig", "Logarithmic": "Log"}
    
    print()
    print(f"{C.BOLD}{C.HEADER}{'='*40}{C.END}")
    print(f"{C.BOLD}{C.HEADER}  MODEL COMPARISON - FIFO vs LIFO{C.END}")
    print(f"{C.BOLD}{C.HEADER}{'='*40}{C.END}")
    print()
    
    # Column headers
    hdr = (f"  {'Model':6s} {'Crv':4s} │ {'S':>6s} │ "
           f"{'M+':>6s} {'M-':>6s} {'#':>2s} {'V':>5s} │ "
           f"{'B+':>6s} {'B-':>7s} {'#':>2s} {'V':>5s} │ "
           f"{'RM+':>6s} {'RM-':>6s} {'#':>2s} {'V':>5s} │ "
           f"{'RB+':>6s} {'RB-':>7s} {'#':>2s} {'V':>5s}")
    print(hdr)
    sep = (f"  {'──────':6s} {'───':4s} │ {'──────':>6s} │ "
           f"{'──────':>6s} {'──────':>6s} {'──':>2s} {'─────':>5s} │ "
           f"{'──────':>6s} {'───────':>7s} {'──':>2s} {'─────':>5s} │ "
           f"{'──────':>6s} {'──────':>6s} {'──':>2s} {'─────':>5s} │ "
           f"{'──────':>6s} {'───────':>7s} {'──':>2s} {'─────':>5s}")
    print(sep)
    
    for r in all_results:
        code = r["codename"]
        cfg = MODELS[code]
        curve = curve_abbr.get(CURVE_NAMES[cfg["curve"]], "?")
        
        # Single
        s_profit = r["single"]["profit"]
        
        # Multi (FIFO)
        m_profits = list(r["multi"]["profits"].values())
        m_winners = sum(D(1) for p in m_profits if p > 0)
        m_losers = len(m_profits) - int(m_winners)
        m_plus = sum(p for p in m_profits if p > 0)
        m_minus = sum(p for p in m_profits if p < 0)
        m_vault = r["multi"]["vault"]
        
        # Bank (FIFO)
        b_plus = sum(p for p in r["bank"]["profits"].values() if p > 0)
        b_minus = sum(p for p in r["bank"]["profits"].values() if p < 0)
        b_losers = r["bank"]["losers"]
        b_vault = r["bank"]["vault"]
        
        # Reverse Multi (LIFO)
        rm_profits = list(r["rmulti"]["profits"].values())
        rm_plus = sum(p for p in rm_profits if p > 0)
        rm_minus = sum(p for p in rm_profits if p < 0)
        rm_losers = sum(1 for p in rm_profits if p <= 0)
        rm_vault = r["rmulti"]["vault"]
        
        # Reverse Bank (LIFO)
        rb_plus = sum(p for p in r["rbank"]["profits"].values() if p > 0)
        rb_minus = sum(p for p in r["rbank"]["profits"].values() if p < 0)
        rb_losers = r["rbank"]["losers"]
        rb_vault = r["rbank"]["vault"]
        
        # Format row with colors
        def fmt_profit(val, width=6, decimals=0):
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
            """Format vault: yellow if != 0 (rounded to avoid tiny residuals)."""
            rounded = round(val, 2)
            if rounded != D(0):
                return f"{C.YELLOW}{float(val):>{width}.0f}{C.END}"
            return f"{float(val):>{width}.0f}"
        
        # Single profit
        s_col = fmt_profit(s_profit, 6, 1)
        
        row = (f"  {code:6s} {curve:4s} │ {s_col} │ "
               f"{fmt_profit(m_plus)} {fmt_profit(m_minus)} {fmt_losers(m_losers)} {fmt_vault(m_vault)} │ "
               f"{fmt_profit(b_plus)} {fmt_profit(b_minus, 7)} {fmt_losers(b_losers)} {fmt_vault(b_vault)} │ "
               f"{fmt_profit(rm_plus)} {fmt_profit(rm_minus)} {fmt_losers(rm_losers)} {fmt_vault(rm_vault)} │ "
               f"{fmt_profit(rb_plus)} {fmt_profit(rb_minus, 7)} {fmt_losers(rb_losers)} {fmt_vault(rb_vault)}")
        print(row)
    
    # Legend
    print()
    print(f"  S = Single user profit │ M = Multi (4 users, FIFO) │ B = Bank run (10 users, FIFO) │ RM/RB = Reverse (LIFO)")
    print(f"  + = profits, - = losses, # = losers, V = vault remaining │ Crv: CP/Exp/Sig/Log")


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