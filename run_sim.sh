#!/bin/sh
# Usage:
#   ./run_sim.sh                 # Compare all active models
#   ./run_sim.sh CYN             # All scenarios for one model (verbose)
#   ./run_sim.sh CYN,EYN         # Compare specific models
#   ./run_sim.sh --single        # Single-user scenario only
#   ./run_sim.sh --multi         # Multi-user scenario only
#   ./run_sim.sh --bank          # Bank run scenario only
#   ./run_sim.sh --rmulti        # Reverse multi-user (LIFO exit order)
#   ./run_sim.sh --rbank         # Reverse bank run (LIFO exit order)
#   ./run_sim.sh --hold          # Hold scenarios (passive holder dilution)
#   ./run_sim.sh --late          # Late entrant scenarios (90d and 180d)
#   ./run_sim.sh --partial       # Partial LP scenario (mixed strategies)
#   ./run_sim.sh --whale         # Whale entry scenario (concentration/slippage)
#   ./run_sim.sh --rwhale        # Reverse whale scenario (whale exits first)
#   ./run_sim.sh --real          # Real life scenario (continuous flow)
#   ./run_sim.sh --stochastic    # Stochastic scenario (random arrivals)
#   ./run_sim.sh --help          # Show all options

python3 -m sim.run_model "$@"
