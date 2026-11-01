"""Shared plot style. Each method keeps one color in every figure: the rule blue, the researched
method orange, and NEH_EWDD aqua (the first three slots of a palette checked for color-vision
deficiency). Text uses ink colors, never a series color."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e4e3df"
COLORS = {"rule": "#2a78d6", "ig": "#eb6834", "neh": "#1baf7a"}
LABELS = {
    "rule": "EDD rule (rule to beat)",
    "ig": "Iterated greedy (researched)",
    "neh": "NEH_EWDD (construction only)",
}


def new_figure(ncols: int, width: float = 10.0, height: float = 4.2):
    plt.rcParams.update(
        {
            "font.size": 10,
            "text.color": INK,
            "axes.labelcolor": INK_SECONDARY,
            "axes.edgecolor": GRID,
            "axes.titlecolor": INK,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "xtick.color": INK_SECONDARY,
            "ytick.color": INK_SECONDARY,
            "legend.frameon": False,
        }
    )
    fig, axes = plt.subplots(1, ncols, figsize=(width, height), facecolor=SURFACE)
    axes = list(axes) if ncols > 1 else [axes]
    for ax in axes:
        ax.set_facecolor(SURFACE)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    return fig, axes


def _tick_format(top: float):
    """Whole numbers with separators below 10,000 and compact thousands on an axis that reaches it."""
    if top >= 10_000:
        return lambda v, _: "0" if v == 0 else f"{v / 1000:g}K"
    return lambda v, _: f"{v:,.0f}"


def save(fig, path, rect=(0, 0, 1, 1)) -> None:
    for ax in fig.axes:
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_tick_format(ax.get_ylim()[1])))
    fig.tight_layout(rect=rect)
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)
