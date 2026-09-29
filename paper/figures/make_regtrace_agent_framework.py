#!/usr/bin/env python3
"""Draw the RegTrace-Agent framework figure.

The figure is intentionally a high-level systems diagram. It reflects the
current paper story: an adaptive TraceSpec constructor maps regulatory corpora
into request-response-evidence-feedback traces; a runtime reviewer uses only
approved fields; feedback and audit signals improve the reviewer policy offline.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["font.family"] = "DejaVu Sans"

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT = Path(__file__).resolve().parent

COLORS = {
    "ink": "#111827",
    "muted": "#4B5563",
    "gray": "#6B7280",
    "construction": "#2457A6",
    "construction_fill": "#E8F0FF",
    "runtime": "#08746F",
    "runtime_fill": "#E6FFFA",
    "learning": "#6D3AA8",
    "learning_fill": "#F2EAFE",
    "validation": "#B35C00",
    "validation_fill": "#FFF3DE",
    "guard": "#BE123C",
    "guard_fill": "#FFE4E6",
    "white": "#FFFFFF",
}


def box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str,
    edge: str,
    fill: str,
    *,
    title_size: float = 7.2,
    body_size: float = 6.25,
    lw: float = 1.5,
    header: bool = False,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.8",
        linewidth=lw,
        edgecolor=edge,
        facecolor=fill,
        zorder=2,
    )
    ax.add_patch(patch)
    if header:
        header_h = 1.35
        ax.add_patch(
            FancyBboxPatch(
                (x, y + h - header_h),
                w,
                header_h,
                boxstyle="round,pad=0.012,rounding_size=0.8",
                linewidth=0,
                facecolor=edge,
                zorder=3,
            )
        )
        ax.add_patch(
            plt.Rectangle((x, y + h - 0.75), w, 0.75, linewidth=0, facecolor=edge, zorder=3)
        )
        ax.text(
            x + w / 2,
            y + h - 0.67,
            title,
            ha="center",
            va="center",
            fontsize=title_size,
            fontweight="bold",
            color="white",
            zorder=4,
        )
        body_y = y + h - 1.85
    else:
        ax.text(
            x + w / 2,
            y + h - 1.05,
            title,
            ha="center",
            va="center",
            fontsize=title_size,
            fontweight="bold",
            color=edge,
            zorder=4,
        )
        body_y = y + h - 3.00

    ax.text(
        x + w / 2,
        body_y,
        body,
        ha="center",
        va="top",
        fontsize=body_size,
        color=COLORS["ink"],
        linespacing=1.18,
        zorder=4,
    )


def label(ax, x, y, text, color=COLORS["muted"], size=7.2):
    ax.text(x, y, text, ha="center", va="center", fontsize=size, color=color, zorder=5)


def arrow(ax, start, end, color=COLORS["gray"], rad=0.0, lw=1.8, style="-|>", ms=12):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=ms,
            linewidth=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            zorder=1,
        )
    )


def main():
    fig, ax = plt.subplots(figsize=(7.4, 5.45))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(
        50,
        96,
        "RegTrace-Agent: adaptive regulatory review from context to feedback",
        ha="center",
        va="center",
        fontsize=9.6,
        fontweight="bold",
        color=COLORS["ink"],
    )

    # Section labels.
    ax.text(4.5, 84.8, "A. Construct trace schema", ha="left", va="center", fontsize=7.8, fontweight="bold", color=COLORS["construction"])
    ax.text(4.5, 55.3, "B. Run evidence-grounded reviewer", ha="left", va="center", fontsize=7.8, fontweight="bold", color=COLORS["runtime"])
    ax.text(4.5, 26.5, "C. Learn, validate, and release", ha="left", va="center", fontsize=7.8, fontweight="bold", color=COLORS["learning"])

    # Top row: adaptive construction.
    box(
        ax,
        5,
        70,
        21,
        12,
        "Regulatory corpus",
        "SEC comments + responses\nCMS deficiencies + POCs\nFDA warnings + closeouts",
        COLORS["construction"],
        COLORS["construction_fill"],
    )
    box(
        ax,
        31,
        70,
        25,
        12,
        "TraceSpec constructor",
        "propose roles\naccept, reshape,\nor reject task",
        COLORS["construction"],
        COLORS["construction_fill"],
    )
    box(
        ax,
        61,
        70,
        34,
        12,
        "Domain TraceSpec",
        "request / response / evidence\nlabel + feedback policy\nhidden fields",
        COLORS["construction"],
        COLORS["construction_fill"],
    )

    arrow(ax, (26, 76), (31, 76), COLORS["construction"], lw=2.0)
    arrow(ax, (56, 76), (61, 76), COLORS["construction"], lw=2.0)

    # Small domain outcomes.
    box(
        ax,
        62.5,
        62.5,
        9.5,
        5.2,
        "SEC",
        "evidence\nresolution",
        COLORS["construction"],
        COLORS["white"],
        title_size=6.2,
        body_size=5.7,
        lw=1.0,
    )
    box(
        ax,
        74,
        62.5,
        9.5,
        5.2,
        "CMS",
        "POC\nadequacy",
        COLORS["construction"],
        COLORS["white"],
        title_size=6.2,
        body_size=5.7,
        lw=1.0,
    )
    box(
        ax,
        85.5,
        62.5,
        9.5,
        5.2,
        "FDA",
        "closeout\ntrace",
        COLORS["construction"],
        COLORS["white"],
        title_size=6.2,
        body_size=5.6,
        lw=1.0,
    )

    # Middle row: runtime reviewer.
    box(
        ax,
        5,
        40,
        19,
        11,
        "Approved inputs",
        "reviewer request\norganization response\nmetadata",
        COLORS["runtime"],
        COLORS["runtime_fill"],
    )
    box(
        ax,
        29,
        40,
        20,
        11,
        "Evidence pack",
        "retrieve/select\nrevised artifacts\nranked snippets",
        COLORS["runtime"],
        COLORS["runtime_fill"],
    )
    box(
        ax,
        54,
        40,
        20,
        11,
        "Obligation review",
        "decompose request\nmatch named items\ncheck gaps",
        COLORS["runtime"],
        COLORS["runtime_fill"],
    )
    box(
        ax,
        78,
        40,
        17,
        11,
        "Guarded verdict",
        "resolved?\nrationale\nmissing item",
        COLORS["guard"],
        COLORS["guard_fill"],
        title_size=6.9,
    )

    arrow(ax, (24, 45.5), (29, 45.5), COLORS["runtime"], lw=2.0)
    arrow(ax, (49, 45.5), (54, 45.5), COLORS["runtime"], lw=2.0)
    arrow(ax, (74, 45.5), (78, 45.5), COLORS["runtime"], lw=2.0)
    arrow(ax, (77.5, 70), (66, 51), COLORS["construction"], rad=0.08, lw=1.6)

    # Boundary label.
    ax.plot([5, 95], [35.2, 35.2], color="#CBD5E1", lw=1.1, ls="--", zorder=0)
    ax.text(
        50,
        36.6,
        "Test-time boundary: labels, feedback, audit notes, and later follow-up are hidden from the reviewer.",
        ha="center",
        va="center",
        fontsize=5.9,
        color=COLORS["muted"],
        bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none", alpha=0.92),
        zorder=6,
    )

    # Bottom row: learning, validation, release.
    box(
        ax,
        5,
        13,
        21,
        11,
        "Adjudication signals",
        "visible-evidence labels\nLLM/human audit\nSEC follow-up",
        COLORS["learning"],
        COLORS["learning_fill"],
    )
    box(
        ax,
        31,
        13,
        20,
        11,
        "Feedback pack",
        "scalar correctness\ncoarse category\nwritten critique",
        COLORS["learning"],
        COLORS["learning_fill"],
    )
    box(
        ax,
        56,
        13,
        18,
        11,
        "Optimizer",
        "GEPA reflects on\nfailure traces\nupdates policy",
        COLORS["learning"],
        COLORS["learning_fill"],
    )
    box(
        ax,
        79,
        13,
        16,
        11,
        "Release package",
        "splits + metadata\nretrieval records\nprompts + outputs",
        COLORS["validation"],
        COLORS["validation_fill"],
    )

    arrow(ax, (26, 18.5), (31, 18.5), COLORS["learning"], lw=2.0)
    arrow(ax, (51, 18.5), (56, 18.5), COLORS["learning"], lw=2.0)
    arrow(ax, (74, 18.5), (79, 18.5), COLORS["validation"], lw=1.8)
    ax.text(
        66.5,
        30.0,
        "improved\nreview policy",
        ha="center",
        va="center",
        fontsize=6.7,
        fontweight="bold",
        color=COLORS["learning"],
        bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor=COLORS["learning"], linewidth=1.1),
        zorder=6,
    )
    arrow(ax, (65, 24), (66.2, 28.2), COLORS["learning"], rad=0.08, lw=2.1)
    arrow(ax, (66.8, 31.8), (64.8, 40), COLORS["learning"], rad=0.10, lw=2.1)

    ax.text(
        50,
        4.5,
        "Key idea: the reusable object is a trace-to-feedback review system, not a single SEC prompt.",
        ha="center",
        va="center",
        fontsize=7.4,
        fontweight="bold",
        color=COLORS["ink"],
    )

    for ext in ["pdf", "png"]:
        fig.savefig(OUT / f"regtrace_agent_framework.{ext}", bbox_inches="tight", pad_inches=0.05, dpi=300)
    plt.close(fig)
    print(f"Wrote {OUT / 'regtrace_agent_framework.pdf'}")


if __name__ == "__main__":
    main()
