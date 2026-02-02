"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    Unified Scenario Output Formatter                       ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Provides consistent, color-coded output with configurable verbosity.      ║
║                                                                           ║
║  Verbosity Levels:                                                        ║
║    1 (-v)   : Buy, Exit, Add/Remove LP, Compound, Key summaries           ║
║    2 (-vv)  : L1 + expanded event details + more rectangular summaries    ║
║    3 (-vvv) : L2 + every action + rectangular summary after everything    ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
from decimal import Decimal as D
from typing import Optional, Dict
from enum import IntEnum


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                              ANSI COLORS                                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class C:
    """ANSI color codes for terminal output."""
    PURPLE = '\033[35m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                           VERBOSITY LEVELS                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class V(IntEnum):
    """Verbosity levels for output control."""
    NORMAL = 1   # -v (default)
    VERBOSE = 2  # -vv
    DEBUG = 3    # -vvv


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                          NUMBER FORMATTING                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def fmt(value: D, decimals: int = 2) -> str:
    """Format number with underscore separators for readability."""
    if value == D('Inf') or value == D('-Inf'):
        return str(value)
    
    # Format with specified decimals
    formatted = f"{value:,.{decimals}f}"
    # Replace commas with underscores
    return formatted.replace(",", "_")


def pct(change: D, decimals: int = 1) -> str:
    """Format percentage change with color."""
    pct_val = change * 100
    sign = "+" if pct_val >= 0 else ""
    color = C.GREEN if pct_val >= 0 else C.RED
    return f"{color}{sign}{pct_val:.{decimals}f}%{C.END}"


def price_change(before: D, after: D) -> str:
    """Calculate and format price change percentage."""
    if before == 0:
        return ""
    change = (after - before) / before
    return f" ({pct(change)})"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                              FORMATTER                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class Formatter:
    """Centralized output formatter with verbosity control."""
    
    def __init__(self, verbosity: int = 1):
        self.verbosity = verbosity
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                         ASCII Art Headers                             │
    # └───────────────────────────────────────────────────────────────────────┘
    def set_lp(self, lp):
        """Register LP instance for debug stats."""
        self.lp = lp
        
    def _auto_stats(self, action: str):
        """Print stats automatically in DEBUG mode."""
        if self.verbosity >= V.DEBUG and hasattr(self, 'lp') and self.lp:
            self.stats(f"Post-{action} State", self.lp, level=V.DEBUG)
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                           ASCII Art Headers                             │
    # └───────────────────────────────────────────────────────────────────────┘
    
    def header(self, title: str, subtitle: str = ""):
        """Print chunky ASCII art header for scenario."""
        if self.verbosity < V.NORMAL:
            return
        
        width = 75
        title_padded = title.center(width - 4)
        
        print()
        print(f"{C.PURPLE}{C.BOLD}╔{'═' * (width - 2)}╗{C.END}")
        print(f"{C.PURPLE}{C.BOLD}║{' ' * (width - 2)}║{C.END}")
        print(f"{C.PURPLE}{C.BOLD}║  {title_padded}  ║{C.END}")
        if subtitle:
            sub_padded = subtitle.center(width - 4)
            print(f"{C.PURPLE}{C.BOLD}║  {sub_padded}  ║{C.END}")
        print(f"{C.PURPLE}{C.BOLD}║{' ' * (width - 2)}║{C.END}")
        print(f"{C.PURPLE}{C.BOLD}╚{'═' * (width - 2)}╝{C.END}")
    
    def section(self, title: str):
        """Print smaller ASCII section divider."""
        if self.verbosity < V.NORMAL:
            return
        
        width = 73
        title_padded = title.center(width - 4)
        
        print(f"{C.PURPLE}┌{'─' * (width - 2)}┐{C.END}")
        print(f"{C.PURPLE}│  {title_padded}  │{C.END}")
        print(f"{C.PURPLE}└{'─' * (width - 2)}┘{C.END}")
        print()
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                           Event Messages                              │
    # └───────────────────────────────────────────────────────────────────────┘
    
    def buy(self, n: int, total: int, name: str, amount: D, 
            price_before: D, tokens: D, price_after: D, emoji: str = ""):
        """Print buy event with price change."""
        if self.verbosity < V.NORMAL:
            return
        
        name_display = f"{emoji} {name}" if emoji else name
        change = price_change(price_before, price_after)
        
        print(f"{C.GREEN}[Buy {n}/{total}]{C.END} {name_display}: "
              f"{fmt(amount)} @ {fmt(price_before, 4)} → "
              f"{C.YELLOW}{fmt(tokens)}{C.END} tokens{change}")
        self._auto_stats("Buy")
    
    def add_lp(self, name: str, tokens: D, usdc: D, emoji: str = ""):
        """Print add liquidity event."""
        if self.verbosity < V.NORMAL:
            return
        
        name_display = f"{emoji} {name}" if emoji else name
        print(f"{C.GREEN}[+LP]{C.END} {name_display}: "
              f"{fmt(tokens)} tokens + {fmt(usdc)} USDC")
        self._auto_stats("AddLiquidity")
    
    def compound(self, days: int, vault_before: D, vault_after: D, 
                 price_before: D, price_after: D):
        """Print compound event with changes."""
        if self.verbosity < V.NORMAL:
            return
        
        vault_change = price_change(vault_before, vault_after)
        p_change = price_change(price_before, price_after)
        
        print(f"{C.YELLOW}[Compound]{C.END} {days}d → "
              f"Vault: {C.YELLOW}{fmt(vault_after)}{C.END}{vault_change}, "
              f"Price: {C.GREEN}{fmt(price_after, 6)}{C.END}{p_change}")
        self._auto_stats("Compound")
    
    def remove_lp(self, name: str, tokens: D, usdc: D, emoji: str = ""):
        """Print remove liquidity event."""
        if self.verbosity < V.NORMAL:
            return
        
        name_display = f"{emoji} {name}" if emoji else name
        print(f"{C.RED}[-LP]{C.END} {name_display}: "
              f"{fmt(tokens)} tokens + {fmt(usdc)} USDC")
        self._auto_stats("RemoveLiquidity")
    
    def exit(self, n: int, total: int, name: str, profit: D,
             price_before: D, price_after: D, emoji: str = "", 
             roi: Optional[D] = None):
        """Print exit/sell event with profit and price change."""
        if self.verbosity < V.NORMAL:
            return
        
        name_display = f"{emoji} {name}" if emoji else name
        profit_color = C.GREEN if profit >= 0 else C.RED
        profit_sign = "+" if profit >= 0 else ""
        change = price_change(price_before, price_after)
        
        roi_str = ""
        if roi is not None:
            roi_color = C.GREEN if roi >= 0 else C.RED
            roi_sign = "+" if roi >= 0 else ""
            roi_str = f" [{roi_color}{roi_sign}{roi:.1f}%{C.END}]"
        
        print(f"{C.RED}[Exit {n}/{total}]{C.END} {name_display}: "
              f"Profit {profit_color}{profit_sign}{fmt(profit)}{C.END}{roi_str}{change}")
        self._auto_stats("Exit/Sell")
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                       Rectangular Summaries                           │
    # └───────────────────────────────────────────────────────────────────────┘
    
    def stats(self, label: str, lp, level: int = 1):
        """Print rectangular stats box. Level controls detail."""
        if self.verbosity < level:
            return

        from .core import CURVE_NAMES, CurveType

        print()
        print(f"{C.CYAN}  ┌─ {label} ─────────────────────────────────────────{C.END}")
        
        # Section 1: Market State
        print(f"{C.CYAN}  │{C.END} {C.BOLD}Market State:{C.END}")
        print(f"{C.CYAN}  │{C.END} Price: {C.YELLOW}{lp.price:.6f}{C.END}   "
              f"Minted: {C.YELLOW}{fmt(lp.minted)}{C.END}")
        print(f"{C.CYAN}  │{C.END} Vault (TVL): {C.YELLOW}{fmt(lp.vault.balance_of())}{C.END}   "
              f"Compounding Index: {C.YELLOW}{lp.vault.compounding_index:.6f}{C.END} ({lp.vault.compounds}d)")
        
        # Section 2: Liquidity Depth
        print(f"{C.CYAN}  │{C.END}")
        print(f"{C.CYAN}  │{C.END} {C.BOLD}Liquidity Depth:{C.END}")
        
        total_lp_tokens = sum(lp.liquidity_token.values()) if lp.liquidity_token else D(0)
        buy_principal = lp.buy_usdc
        lp_principal = lp.lp_usdc
        
        print(f"{C.CYAN}  │{C.END} Total Liquidity: {C.YELLOW}{fmt(total_lp_tokens)}{C.END} tokens + {C.YELLOW}{fmt(lp.lp_usdc)}{C.END} USDC")
        print(f"{C.CYAN}  │{C.END} USDC Split: Buy={C.YELLOW}{fmt(buy_principal)}{C.END}, LP={C.YELLOW}{fmt(lp_principal)}{C.END}")
        print(f"{C.CYAN}  │{C.END} Price-Effective TVL: {C.YELLOW}{fmt(lp._get_effective_usdc())}{C.END}")

        # Section 3: Curve Mechanics
        print(f"{C.CYAN}  │{C.END}")
        print(f"{C.CYAN}  │{C.END} {C.BOLD}Curve Mechanics:{C.END}")
        
        if lp.curve_type == CurveType.CONSTANT_PRODUCT:
            tr = lp._get_token_reserve()
            ur = lp._get_usdc_reserve()
            print(f"{C.CYAN}  │{C.END} Virtual Reserves: {C.DIM}x={fmt(tr)}, y={fmt(ur)}{C.END}")
            k_val = fmt(lp.k) if lp.k else "None"
            print(f"{C.CYAN}  │{C.END} Invariant (k): {C.YELLOW}{k_val}{C.END}")
            print(f"{C.CYAN}  │{C.END} Exposure: {C.DIM}{fmt(lp.get_exposure())}{C.END}   Virtual Liq: {C.DIM}{fmt(lp.get_virtual_liquidity())}{C.END}")
        else:
            print(f"{C.CYAN}  │{C.END} Curve Type: {C.YELLOW}{CURVE_NAMES[lp.curve_type]}{C.END}")
            print(f"{C.CYAN}  │{C.END} Integral Multiplier: {C.YELLOW}{lp._get_price_multiplier():.6f}{C.END}")
        
        # Expanded details at verbosity >= 2
        if self.verbosity >= V.VERBOSE and level <= V.VERBOSE:
            if lp.liquidity_token:
                print(f"{C.CYAN}  │{C.END}")
                print(f"{C.CYAN}  │{C.END} {C.BOLD}LP Positions:{C.END}")
                for user, tokens in lp.liquidity_token.items():
                    usdc = lp.liquidity_usd.get(user, D(0))
                    print(f"{C.CYAN}  │{C.END}   {user}: {C.YELLOW}{fmt(tokens)}{C.END} tokens, {C.YELLOW}{fmt(usdc)}{C.END} USDC")
        
        print(f"{C.CYAN}  └─────────────────────────────────────────────────────{C.END}\n")
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                          Final Summary                                │
    # └───────────────────────────────────────────────────────────────────────┘
    def summary(self, results: Dict[str, D], vault: D, 
                title: str = "FINAL SUMMARY"):
        """Print final scenario summary with winners/losers."""
        if self.verbosity < V.NORMAL:
            return
        
        winners = sum(1 for p in results.values() if p > 0)
        losers = sum(1 for p in results.values() if p <= 0)
        total = sum(results.values(), D(0))
        
        total_color = C.GREEN if total > 0 else C.RED
        total_sign = "+" if total >= 0 else ""
        
        width = 60
        title_padded = title.center(width - 4)
        
        print()
        print(f"{C.PURPLE}{C.BOLD}╔{'═' * (width - 2)}╗{C.END}")
        print(f"{C.PURPLE}{C.BOLD}║  {title_padded}  ║{C.END}")
        print(f"{C.PURPLE}{C.BOLD}╠{'═' * (width - 2)}╣{C.END}")
        print(f"{C.PURPLE}{C.BOLD}║{' ' * (width - 2)}║{C.END}")
        
        row1_content = f"Winners: {C.GREEN}{winners}{C.END}   Losers: {C.RED}{losers}{C.END}"
        row2_content = f"Total Profit: {total_color}{total_sign}{fmt(total)}{C.END}"
        row3_content = f"Vault Remaining: {C.YELLOW}{fmt(vault)}{C.END}"
        
        self._print_box_row(row1_content, width)
        self._print_box_row(row2_content, width)
        self._print_box_row(row3_content, width)
        
        print(f"{C.PURPLE}{C.BOLD}║{' ' * (width - 2)}║{C.END}")
        print(f"{C.PURPLE}{C.BOLD}╚{'═' * (width - 2)}╝{C.END}")
        
    def _print_box_row(self, content: str, width: int):
        """Helper to print a box row with ANSI-aware padding."""
        # Strip ANSI to measure visible length
        visible_len = len(self._strip_ansi(content))
        padding = width - 4 - visible_len
        if padding < 0: padding = 0
        
        print(f"{C.PURPLE}{C.BOLD}║{C.END}   {content}{' ' * (padding - 1)} {C.PURPLE}{C.BOLD}║{C.END}")

    def _strip_ansi(self, text: str) -> str:
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    # ┌───────────────────────────────────────────────────────────────────────┐
    # │                          Debug Messages                               │
    # └───────────────────────────────────────────────────────────────────────┘
    
    def debug(self, message: str):
        """Print debug message (only at verbosity 3)."""
        if self.verbosity >= V.DEBUG:
            print(f"{C.DIM}[DEBUG] {message}{C.END}")
    
    def info(self, message: str):
        """Print info message (verbosity 2+)."""
        if self.verbosity >= V.VERBOSE:
            print(f"{C.DIM}{message}{C.END}")
    
    def wait(self, days: int):
        """Print wait/time passing indicator."""
        if self.verbosity >= V.NORMAL:
            print(f"{C.DIM}  ... {days} days pass ...{C.END}")
