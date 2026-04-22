"""
gen_paper_figures.py — Generate publication-quality figures for Paper 2.

Generates:
  - fig_architecture.png: Pre-execution planning pipeline (for §3)
  - fig_conditions.png: 5-condition comparison bar chart (for §5)

Usage:
    python3 scripts/gen_paper_figures.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# ── Paths ──────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "paper" / "figures"
FIG_DIR.mkdir(exist_ok=True)

# ── Style ──────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 8,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

COL_W = 3.25  # ACL column width


def _box(ax, x, y, w, h, text, color="#E8E8E8", textcolor="black",
         fontsize=7, bold=False, border_color=None):
    """Draw a rounded rectangle with centered text."""
    bc = border_color or color
    box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                          boxstyle="round,pad=0.05",
                          facecolor=color, edgecolor=bc, linewidth=0.8)
    ax.add_patch(box)
    weight = "bold" if bold else "normal"
    ax.text(x, y, text, ha="center", va="center",
            fontsize=fontsize, color=textcolor, weight=weight)


def _arrow(ax, x1, y1, x2, y2, color="gray"):
    """Draw an arrow between two points."""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->,head_width=0.15,head_length=0.1",
                                color=color, lw=0.8))


def gen_architecture():
    """Generate architecture diagram showing the pre-execution planning pipeline."""
    fig, ax = plt.subplots(figsize=(COL_W, 1.8))
    ax.set_xlim(-0.1, 3.35)
    ax.set_ylim(-0.15, 1.55)
    ax.axis("off")

    # Row 1 (top): Baseline — User → Agent → Result
    y_top = 1.25
    ax.text(-0.05, y_top, "Baseline:", fontsize=6.5, va="center",
            fontstyle="italic", color="#888888")
    _box(ax, 0.8, y_top, 0.65, 0.35, "User\nRequest", "#F0F0F0", fontsize=6)
    _arrow(ax, 1.15, y_top, 1.55, y_top, "#AAAAAA")
    _box(ax, 2.05, y_top, 0.8, 0.35, "gpt-4o Agent\n(ReAct loop)", "#F0F0F0",
         fontsize=6)
    _arrow(ax, 2.48, y_top, 2.85, y_top, "#AAAAAA")
    _box(ax, 3.1, y_top, 0.4, 0.35, "Result", "#F0F0F0", fontsize=6)

    # Divider
    ax.plot([-0.05, 3.35], [0.85, 0.85], '--', color="#CCCCCC", lw=0.5)

    # Row 2 (bottom): Ours — User → Decomposer → Sub-goals → Agent → Result
    y_bot = 0.4
    ax.text(-0.05, y_bot, "Ours:", fontsize=6.5, va="center",
            fontstyle="italic", color="#0072B2", weight="bold")

    _box(ax, 0.55, y_bot, 0.55, 0.4, "User\nRequest", "#E8F4FD",
         border_color="#0072B2", fontsize=6)

    _arrow(ax, 0.85, y_bot, 1.05, y_bot, "#0072B2")

    _box(ax, 1.45, y_bot, 0.6, 0.4, "Decomposer\n(cheap LM)",
         "#0072B2", textcolor="white", fontsize=6, bold=True)

    _arrow(ax, 1.78, y_bot, 1.98, y_bot, "#0072B2")

    # Sub-goal list as a small structured box
    _box(ax, 2.3, y_bot, 0.5, 0.4, "Sub-goal\nList", "#E8F4FD",
         border_color="#0072B2", fontsize=6)

    _arrow(ax, 2.58, y_bot, 2.73, y_bot, "#0072B2")

    _box(ax, 3.05, y_bot, 0.5, 0.4, "Executor\n(gpt-4o)", "#D55E00",
         textcolor="white", fontsize=6, bold=True)

    # Sub-goal example below
    ax.text(1.88, -0.05, r'e.g. (exchange, "helmet", size$\rightarrow$M)',
            fontsize=5, ha="center", va="top", color="#666666",
            fontstyle="italic")

    # Cost labels
    ax.text(1.45, 0.08, "<$0.001", fontsize=5, ha="center", color="#0072B2")
    ax.text(3.05, 0.08, "~$0.85", fontsize=5, ha="center", color="#D55E00")

    fig.tight_layout(pad=0.1)
    out = FIG_DIR / "fig_architecture.png"
    fig.savefig(out)
    plt.close()
    print(f"  Saved: {out}")


def gen_conditions():
    """Generate 5-condition comparison bar chart."""
    conditions = ["Baseline", "Rule-based", "Oracle", "Tiny-LM", "Same-model"]
    means = [34.8, 33.3, 57.6, 36.4, 34.8]
    stds = [22.4, 13.9, 13.9, 4.5, 2.6]

    colors = ["#AAAAAA", "#AAAAAA", "#0072B2", "#AAAAAA", "#AAAAAA"]

    fig, ax = plt.subplots(figsize=(COL_W, 2.2))
    x = np.arange(len(conditions))
    bars = ax.bar(x, means, yerr=stds, capsize=3, color=colors,
                  edgecolor="white", linewidth=0.5, width=0.6,
                  error_kw={"linewidth": 0.8})

    # Value labels
    for i, (m, s) in enumerate(zip(means, stds)):
        weight = "bold" if conditions[i] == "Oracle" else "normal"
        ax.text(i, m + s + 1.5, f"{m}", ha="center", va="bottom",
                fontsize=7, weight=weight)

    # Quality gap: dashed baseline reference + vertical annotation on Oracle bar
    ax.axhline(y=34.8, color="#AAAAAA", linewidth=0.5, linestyle=":", alpha=0.6,
               zorder=1)
    ax.annotate("", xy=(2, 34.8), xytext=(2, 57.6),
                arrowprops=dict(arrowstyle="<->", color="#0072B2", lw=0.7))
    ax.text(2.45, 46, "22.7pp\ngap", fontsize=6, color="#0072B2", ha="left")

    ax.set_xticks(x)
    ax.set_xticklabels(conditions, fontsize=7)
    ax.set_ylabel(r"Mean pass$^1$ (%)")
    ax.set_ylim(0, 80)
    ax.grid(True, axis="y", alpha=0.15, linewidth=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout(pad=0.3)
    out = FIG_DIR / "fig_conditions.png"
    fig.savefig(out)
    plt.close()
    print(f"  Saved: {out}")


if __name__ == "__main__":
    print("Generating Paper 2 figures...")
    gen_architecture()
    gen_conditions()
    print("Done.")
