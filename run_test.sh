#!/bin/sh
# Usage:
#   ./run_test.sh               # Run the full test suite (all models)

python3 -m sim.test.run_all "$@"
