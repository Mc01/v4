#!/bin/sh
# Usage:
#   ./run_sim.sh                 # Compare all 4 active models (CYN, EYN, SYN, LYN)
#   ./run_sim.sh CYN             # All scenarios for one model (verbose)
#   ./run_sim.sh CYN,EYN         # Compare specific models
#   ./run_sim.sh --single        # Single-user scenario only
#   ./run_sim.sh --multi         # Multi-user scenario only
#   ./run_sim.sh --bank          # Bank run scenario only
#   ./run_sim.sh --rmulti        # Reverse multi-user (LIFO)
#   ./run_sim.sh --rbank         # Reverse bank run (LIFO)
#   ./run_sim.sh --help          # Show all options

python3 -m sim.run_model "$@"
