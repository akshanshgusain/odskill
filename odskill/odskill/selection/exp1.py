"""Experiment 1 cell, and the same flags the test evaluation uses.

Load-only. The switches are recorded in the run manifest by evolve_desc.

    python -m odskill.selection.exp1 --arm plain --agent-prompt neutral --names canonical \
        --noise-k 100 --split val --passes 1 --budget 1 --run-dir results/exp1/cell
    python -m odskill.selection.evolve_desc --split test --i-understand-this-is-the-test-split \
        --agent-prompt neutral --names canonical --budget 1 --run-dir results/test/cell
"""

from odskill.selection.evolve_desc import main

if __name__ == "__main__":
    main()
