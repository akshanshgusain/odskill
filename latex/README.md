# LaTeX source for "Will It Load? What Decides Whether Agents Use On-Demand Skills"

Build: `latexmk -pdf main.tex`

Regenerate figures and the appendix table from ../results:

    python3 make_figures.py
    python3 make_tables.py   # writes tables/exp1_cells.tex; its rows are pasted into main.tex Table 3

arXiv upload: arxiv_upload.zip (main.tex, main.bbl, refs.bib, figures/).
