import os

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["font.family"] = "DejaVu Sans"

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


OUT = os.path.join(os.path.dirname(__file__), "regtrace_agent_framework.pdf")

COLORS = {
    "ink": "#111827",
    "muted": "#475569",
    "slate": "#334155",
    "panel": "#F8FAFC",
    "blue": "#1D4ED8",
    "blue_light": "#DBEAFE",
    "teal": "#047857",
    "teal_light": "#D1FAE5",
    "amber": "#B45309",
    "amber_light": "#FEF3C7",
    "red": "#B91C1C",
    "red_light": "#FEE2E2",
    "purple": "#6D28D9",
    "purple_light": "#EDE9FE",
    "green": "#15803D",
    "green_light": "#DCFCE7",
}


def panel(ax, x, y, w, h, title, color, fill):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=1.8",
            linewidth=1.3,
            edgecolor=color,
            facecolor=fill,
            zorder=0,
        )
    )
    ax.text(
        x + 1.8,
        y + h - 2.8,
        title,
        ha="left",
        va="center",
        fontsize=8.8,
        fontweight="bold",
        color=color,
        zorder=5,
    )


def card(ax, x, y, w, h, title, subtitle, rows, color, fill):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.014,rounding_size=1.2",
            linewidth=1.8,
            edgecolor=color,
            facecolor=fill,
            zorder=3,
        )
    )
    header_h = 4.6
    ax.add_patch(Rectangle((x, y + h - header_h), w, header_h, linewidth=0, facecolor=color, zorder=4))
    ax.text(x + w / 2, y + h - 1.65, title, ha="center", va="center",
            fontsize=7.7, fontweight="bold", color="white", zorder=5)
    ax.text(x + w / 2, y + h - 3.35, subtitle, ha="center", va="center",
            fontsize=6.2, color="white", zorder=5)

    start_y = y + h - header_h - 2.1
    for i, row in enumerate(rows):
        ax.text(x + 1.2, start_y - i * 2.25, row, ha="left", va="center",
                fontsize=6.9, color=COLORS["ink"], zorder=5)


def arrow(ax, start, end, color=None, rad=0.0, lw=1.9, label=None, label_offset=0.0):
    color = color or COLORS["slate"]
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            zorder=2,
        )
    )
    if label:
        lx = (start[0] + end[0]) / 2
        ly = (start[1] + end[1]) / 2 + label_offset
        ax.text(lx, ly, label, ha="center", va="center", fontsize=6.4,
                fontweight="bold", color=color, zorder=6)


fig, ax = plt.subplots(figsize=(7.15, 4.55))
ax.set_xlim(0, 100)
ax.set_ylim(0, 70)
ax.axis("off")
fig.patch.set_facecolor("white")

ax.text(
    50,
    67.4,
    "RegTrace-Agent: closed-loop evidence review and feedback optimization",
    ha="center",
    va="center",
    fontsize=10.3,
    fontweight="bold",
    color=COLORS["ink"],
)

panel(ax, 3, 33.5, 94, 30, "Runtime path", COLORS["slate"], COLORS["panel"])
panel(ax, 3, 5, 94, 24.5, "Learning loop", COLORS["purple"], "#F8F5FF")

card(
    ax,
    6,
    42.0,
    18.5,
    15,
    "Trace",
    "parse + align",
    ["SEC comment", "response letter", "revision cues"],
    COLORS["blue"],
    COLORS["blue_light"],
)
card(
    ax,
    30,
    42.0,
    18.5,
    15,
    "Evidence",
    "retrieve + rerank",
    ["amended filing", "ranked snippets", "evidence pack"],
    COLORS["teal"],
    COLORS["teal_light"],
)
card(
    ax,
    54,
    42.0,
    18.5,
    15,
    "Review",
    "decompose + verify",
    ["request atoms", "named items", "numbers/exhibits", "gap check"],
    COLORS["amber"],
    COLORS["amber_light"],
)
card(
    ax,
    78,
    42.0,
    16,
    15,
    "Verdict",
    "decide + explain",
    ["resolved?", "rationale", "missing req."],
    COLORS["red"],
    COLORS["red_light"],
)

card(
    ax,
    13,
    11.5,
    20,
    13,
    "Feedback",
    "labels -> critiques",
    ["scalar/category/full", "gap rationale", "SEC follow-up"],
    COLORS["purple"],
    COLORS["purple_light"],
)
card(
    ax,
    41,
    11.5,
    20,
    13,
    "Optimizer",
    "GEPA",
    ["read failures", "edit prompt/program", "select policy"],
    COLORS["purple"],
    COLORS["purple_light"],
)
card(
    ax,
    69,
    11.5,
    20,
    13,
    "Policy",
    "runtime rules",
    ["evidence required", "partial != resolved", "no over-demand"],
    COLORS["green"],
    COLORS["green_light"],
)

arrow(ax, (24.5, 49.5), (30, 49.5))
arrow(ax, (48.5, 49.5), (54, 49.5))
arrow(ax, (72.5, 49.5), (78, 49.5))

ax.text(
    50,
    35.3,
    "errors + hard cases",
    ha="center",
    va="center",
    fontsize=6.4,
    fontweight="bold",
    color=COLORS["purple"],
    bbox=dict(boxstyle="round,pad=0.22", facecolor="#F8F5FF", edgecolor=COLORS["purple"], linewidth=1.2),
    zorder=7,
)
arrow(ax, (86, 42.0), (60, 35.3), COLORS["purple"], rad=0.0, lw=2.2)
arrow(ax, (40, 35.3), (23, 25.3), COLORS["purple"], rad=0.08, lw=2.2)
arrow(ax, (33, 18.0), (41, 18.0), COLORS["purple"], lw=2.0)
arrow(ax, (61, 18.0), (69, 18.0), COLORS["purple"], lw=2.0)
arrow(ax, (79, 24.5), (64, 42.0), COLORS["green"], rad=-0.20, lw=2.3)

ax.text(
    50,
    2.8,
    "Test-time inputs: SEC comment, company response, retrieved amended evidence. Feedback fields are train/audit only.",
    ha="center",
    va="center",
    fontsize=6.5,
    color=COLORS["muted"],
)

fig.savefig(OUT, bbox_inches="tight", pad_inches=0.05)
