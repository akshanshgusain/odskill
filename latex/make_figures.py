"""Build the paper's three figures as vector PDFs, straight from results/."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

BLUE, GREY, INK, QUIET = "#2a6fb0", "#9a9a9a", "#222222", "#666666"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["cmr10"], "mathtext.fontset": "cm", "axes.formatter.use_mathtext": True, "axes.unicode_minus": False, "font.size": 9,
    "axes.edgecolor": QUIET, "axes.linewidth": 0.6, "axes.labelcolor": INK,
    "xtick.color": QUIET, "ytick.color": QUIET, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "legend.frameon": False,
})
MODELS = [("anthropic/claude-haiku-5.5", "haiku", "Claude Haiku 5.5"),
          ("deepseek/deepseek-v4.1-flash-1017", "deepseek", "DeepSeek V4.1 Flash")]


def grid(ax):
    ax.set_ylim(-0.03, 1.03)
    ax.set_yticks([0, 0.5, 1])
    for t in (0.5, 1.0):
        ax.axhline(t, color="#e4e4e4", lw=0.6, zorder=0)


def figure1():
    cells = [json.loads(l) for l in (RES / "exp1/cells.jsonl").read_text().splitlines() if l.strip()]
    cells = [c for c in cells if c["names"] == "canonical"]
    assert len(cells) == 24
    noises = [20, 100, 300]
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.5), sharey=True)
    for ax, (exe, _, title) in zip(axes, MODELS):
        for prompt, colour in (("forced", BLUE), ("neutral", GREY)):
            for arm, style in (("directive", "-"), ("plain", "--")):
                rows = sorted((c for c in cells if c["executor"] == exe and c["agent_prompt"] == prompt and c["arm"] == arm),
                              key=lambda c: c["noise_k"])
                assert [r["noise_k"] for r in rows] == noises
                off = 0.06 if arm == "directive" else -0.06
                xs = [i + off for i in range(3)]
                ys = [r["f1"] for r in rows]
                lo = [y - r["f1_ci95"][0] for y, r in zip(ys, rows)]
                hi = [r["f1_ci95"][1] - y for y, r in zip(ys, rows)]
                ax.errorbar(xs, ys, yerr=[lo, hi], color=colour, ls=style, lw=1.3, marker="o", ms=3.2,
                            elinewidth=0.7, capsize=0)
        ax.set_xticks(range(3), [str(n) for n in noises])
        ax.set_xlim(-0.35, 2.35)
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        ax.set_xlabel("Distractor skills in the index")
        grid(ax)
    axes[0].set_ylabel("F1 of loads")
    handles = [Line2D([], [], color=BLUE, lw=1.3, label="Load instruction"),
               Line2D([], [], color=GREY, lw=1.3, label="No instruction"),
               Line2D([], [], color=INK, lw=1.0, ls="-", label="Directive wording"),
               Line2D([], [], color=INK, lw=1.0, ls="--", label="Plain wording")]
    fig.legend(handles=handles, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.0), fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(OUT / "fig1_exp1_f1.pdf")
    plt.close(fig)


def kept_series(history):
    kept, out = 0.0, []
    for it in history:
        if it["verdict"] != "reject":
            kept = it["f1"]
        out.append(kept)
    return out


def figure2():
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.5), sharey=True)
    finals = {}
    for ax, (arm, colour, title) in zip(axes, (("nowiki", BLUE, "Without the wiki (nowiki)"),
                                                ("wikisel", GREY, "With the wiki (wikisel)"))):
        labels = {}
        for seed in range(3):
            h = json.loads((RES / f"exp2/{arm}-s{seed}/history.json").read_text())
            assert [it["iteration"] for it in h] == list(range(7))
            k = kept_series(h)
            ax.step(range(7), k, where="post", color=colour, lw=1.4)
            for it in h:
                hollow = it["verdict"] == "reject"
                ax.plot(it["iteration"], it["f1"], "o", ms=3.6, color=colour,
                        mfc="white" if hollow else colour, mew=1.0)
            finals[(arm, seed)] = k[-1]
            labels.setdefault(round(k[-1], 3), []).append(seed)
        for value, seeds in labels.items():
            ax.text(6.25, value + (0.04 if value < 0.02 else 0), ", ".join(f"s{s}" for s in seeds) + f": {value:.2f}",
                    va="center", fontsize=7.5, color=INK)
        ax.set_xticks(range(7))
        ax.set_xlim(-0.3, 7.6)
        ax.set_xlabel("Iteration")
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        grid(ax)
    axes[0].set_ylabel("Validation F1")
    handles = [Line2D([], [], color=INK, lw=1.2, label="F1 of the descriptions kept so far"),
               Line2D([], [], color=INK, marker="o", ls="", ms=3.6, label="Accepted or baseline"),
               Line2D([], [], color=INK, marker="o", ls="", ms=3.6, mfc="white", label="Rejected candidate")]
    fig.legend(handles=handles, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0), fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(OUT / "fig2_exp2_val.pdf")
    plt.close(fig)
    return finals


def figure3():
    sets = [("Plain", ["plain"]), ("Directive", ["directive"]),
            ("nowiki", [f"nowiki-s{s}" for s in range(3)]), ("wikisel", [f"wikisel-s{s}" for s in range(3)])]
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.2), sharey=True)
    for ax, (_, key, title) in zip(axes, MODELS):
        for row, (name, runs) in enumerate(sets):
            y0 = len(sets) - 1 - row
            ax.axhline(y0, color="#ececec", lw=0.6, zorder=0)
            vals = []
            for run in runs:
                f1 = json.loads((RES / f"test/{key}/{run}/summary.json").read_text())["f1"]
                seed = int(run[-1]) if run[-2:-1] == "s" else 0
                dy = (seed - 1) * 0.16 if len(runs) > 1 else 0
                ax.plot(f1, y0 + dy, "o", ms=4.5, color=BLUE if name == "nowiki" else GREY, alpha=0.9)
                vals.append((seed, f1, y0 + dy))
            if len(vals) > 1:
                med = sorted(v[1] for v in vals)[1]
                for seed, f1, y in vals:
                    if abs(f1 - med) > 0.3:
                        ax.text(f1 + 0.03, y, f"s{seed}: {f1:.2f}", va="center", fontsize=7.5, color=INK)
        ax.set_yticks(range(len(sets)), [s[0] for s in reversed(sets)])
        ax.set_xlim(-0.03, 1.03)
        ax.set_xticks([0, 0.5, 1])
        ax.set_ylim(-0.6, len(sets) - 0.4)
        ax.set_xlabel("Test F1 of loads")
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_test.pdf")
    plt.close(fig)


if __name__ == "__main__":
    figure1()
    print(figure2())
    figure3()
    print("ok")
