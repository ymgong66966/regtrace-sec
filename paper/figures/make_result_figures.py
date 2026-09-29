#!/usr/bin/env python3
"""Generate paper-ready result figures for the RegTrace paper."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


OUT = Path(__file__).resolve().parent


COLORS = {
    "navy": "#244C7A",
    "blue": "#3478B8",
    "teal": "#1B9AAA",
    "green": "#4B9B68",
    "orange": "#E28B35",
    "red": "#C94C4C",
    "purple": "#7A5AA6",
    "gray": "#8C8C8C",
    "light_gray": "#E8ECEF",
    "dark": "#222222",
}


def setup():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10.5,
            "axes.titlesize": 12.5,
            "axes.labelsize": 10.5,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "legend.fontsize": 9.5,
            "figure.dpi": 180,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.8,
        }
    )


def save(fig, name: str):
    for ext in ["pdf", "png"]:
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)


def annotate_bars(ax, bars, dy=0.012, fmt="{:.3f}"):
    for bar in bars:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + dy,
            fmt.format(h),
            ha="center",
            va="bottom",
            fontsize=8.5,
            color=COLORS["dark"],
        )


def evidence_ablation():
    labels = ["Response\nonly", "+ Raw amended\nsnippets", "+ Oracle evidence\nsummary"]
    macro = [0.575, 0.748, 0.956]
    resolved = [0.333, 0.651, 0.938]
    unresolved = [0.817, 0.844, 0.975]
    x = np.arange(len(labels))
    width = 0.24

    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    b1 = ax.bar(x - width, macro, width, label="Macro-F1", color=COLORS["navy"])
    b2 = ax.bar(x, resolved, width, label="Resolved F1", color=COLORS["teal"])
    b3 = ax.bar(x + width, unresolved, width, label="Unresolved F1", color=COLORS["orange"])
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("F1")
    ax.set_title("Evidence is the main missing ingredient in response review")
    ax.set_xticks(x, labels)
    ax.grid(axis="y", color=COLORS["light_gray"], linewidth=0.8)
    ax.legend(ncols=3, frameon=False, loc="upper left")
    annotate_bars(ax, b1)
    ax.annotate(
        "+17.3 macro-F1",
        xy=(1, macro[1]),
        xytext=(0.45, 0.92),
        arrowprops=dict(arrowstyle="->", color=COLORS["dark"], lw=1),
        ha="center",
        fontsize=10,
        fontweight="bold",
    )
    ax.text(
        2,
        0.12,
        "Oracle summary is an upper bound,\nnot a deployable baseline",
        ha="center",
        va="bottom",
        fontsize=8.8,
        color="#555555",
        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="none", alpha=0.88),
    )
    save(fig, "result_1_evidence_ablation")


def feedback_ladder():
    methods = ["Majority", "Handwritten", "MIPROv2", "GEPA\nscalar", "GEPA\ncategory", "GEPA\nfull"]
    macro = [0.409, 0.402, 0.652, 0.675, 0.595, 0.756]
    unresolved = [0.817, 0.286, 0.684, 0.773, 0.627, 0.839]
    resolved = [0.000, 0.518, 0.619, 0.577, 0.562, 0.674]
    colors = [COLORS["gray"], COLORS["gray"], COLORS["orange"], COLORS["blue"], COLORS["purple"], COLORS["green"]]
    x = np.arange(len(methods))

    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    bars = ax.bar(x, macro, color=colors, width=0.68)
    ax.plot(x, unresolved, color=COLORS["red"], marker="o", lw=2, label="Unresolved F1")
    ax.plot(x, resolved, color=COLORS["teal"], marker="o", lw=2, label="Resolved F1")
    ax.set_ylim(0, 0.93)
    ax.set_ylabel("Score")
    ax.set_title("Full natural-language feedback gives the strongest reviewer")
    ax.set_xticks(x, methods)
    ax.grid(axis="y", color=COLORS["light_gray"], linewidth=0.8)
    ax.legend(frameon=False, loc="upper left")
    annotate_bars(ax, bars, dy=0.015)
    ax.annotate(
        "+10.4 over MIPROv2",
        xy=(5, macro[5]),
        xytext=(4.1, 0.88),
        arrowprops=dict(arrowstyle="->", color=COLORS["dark"], lw=1),
        ha="center",
        fontsize=9.5,
        fontweight="bold",
    )
    ax.text(
        4.35,
        0.10,
        "Same test-time evidence;\nonly feedback richness changes",
        ha="center",
        fontsize=8.8,
        color="#555555",
        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="none", alpha=0.88),
    )
    save(fig, "result_2_feedback_ladder")


def generalization():
    methods = ["Baseline", "MIPROv2", "GEPA-scalar", "GEPA-full"]
    temporal = [0.434, 0.519, 0.650, 0.791]
    topic = [0.440, 0.565, 0.524, 0.734]
    colors = [COLORS["gray"], COLORS["orange"], COLORS["blue"], COLORS["green"]]
    x = np.arange(2)
    width = 0.18

    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    for i, method in enumerate(methods):
        vals = [temporal[i], topic[i]]
        ax.bar(x + (i - 1.5) * width, vals, width, label=method, color=colors[i])
    ax.set_ylim(0, 0.88)
    ax.set_ylabel("Macro-F1")
    ax.set_title("The learned policy transfers across time and issue categories", pad=24)
    ax.set_xticks(x, ["Temporal holdout\n(2024-2025)", "Topic holdout\n(crypto/non-GAAP held out)"])
    ax.grid(axis="y", color=COLORS["light_gray"], linewidth=0.8)
    ax.legend(ncols=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.10))
    for xi, top in zip(x, [temporal[-1], topic[-1]]):
        ax.text(xi + 1.5 * width, top + 0.025, f"{top:.3f}", ha="center", fontsize=9, fontweight="bold")
    save(fig, "result_3_generalization")


def cross_domain():
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.9), gridspec_kw={"width_ratios": [1.15, 1]})

    cms_methods = ["Generic", "Minimal\nseed", "Scalar", "Category", "Full"]
    cms = [0.694, 0.642, 0.663, 0.635, 0.723]
    cms_colors = [COLORS["gray"], COLORS["gray"], COLORS["blue"], COLORS["purple"], COLORS["green"]]
    axes[0].bar(np.arange(len(cms_methods)), cms, color=cms_colors, width=0.68)
    axes[0].set_title("CMS: feedback adapts the reviewer")
    axes[0].set_ylabel("Macro-F1")
    axes[0].set_ylim(0.55, 0.76)
    axes[0].set_xticks(np.arange(len(cms_methods)), cms_methods)
    axes[0].grid(axis="y", color=COLORS["light_gray"], linewidth=0.8)
    axes[0].text(4, cms[-1] + 0.006, "0.723", ha="center", fontweight="bold", fontsize=9)
    axes[0].annotate(
        "+2.9 over generic",
        xy=(4, cms[-1]),
        xytext=(3.05, 0.747),
        arrowprops=dict(arrowstyle="->", color=COLORS["dark"], lw=1),
        fontsize=8.8,
        fontweight="bold",
        ha="center",
    )

    fda_methods = ["Generic", "Strict\nRegTrace", "Calibrated\nRegTrace"]
    fda = [0.918, 0.880, 0.950]
    fda_colors = [COLORS["gray"], COLORS["orange"], COLORS["green"]]
    axes[1].bar(np.arange(len(fda_methods)), fda, color=fda_colors, width=0.62)
    axes[1].set_title("FDA: constructor reshapes the task")
    axes[1].set_ylim(0.84, 0.97)
    axes[1].set_xticks(np.arange(len(fda_methods)), fda_methods)
    axes[1].grid(axis="y", color=COLORS["light_gray"], linewidth=0.8)
    axes[1].text(2, fda[-1] + 0.005, "0.950", ha="center", fontweight="bold", fontsize=9)
    axes[1].annotate(
        "calibration fixes\nover-rejection",
        xy=(2, fda[-1]),
        xytext=(1.12, 0.942),
        arrowprops=dict(arrowstyle="->", color=COLORS["dark"], lw=1),
        fontsize=8.6,
        fontweight="bold",
        ha="center",
    )
    fig.suptitle("RegTrace transfers as a construction-and-feedback pattern, not a copied SEC prompt", y=1.05)
    fig.tight_layout()
    save(fig, "result_4_cross_domain_adaptation")


def validation_and_corroboration():
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.9), gridspec_kw={"width_ratios": [1, 1.05]})

    groups = ["Unresolved\nlabels", "Resolved\nlabels"]
    rates = [0.681, 0.092]
    bars = axes[0].bar(groups, rates, color=[COLORS["red"], COLORS["teal"]], width=0.58)
    axes[0].set_ylim(0, 0.78)
    axes[0].set_ylabel("Direct/partial corroboration rate")
    axes[0].set_title("Later SEC follow-up supports the labels")
    axes[0].grid(axis="y", color=COLORS["light_gray"], linewidth=0.8)
    annotate_bars(axes[0], bars, fmt="{:.1%}")
    axes[0].text(
        0.5,
        0.735,
        "N=236 with verified follow-up",
        ha="center",
        va="bottom",
        fontsize=8.6,
        color="#555555",
    )

    methods = ["Benchmark\nlabel", "OOF\nGEPA-full", "Handwritten\nbaseline"]
    macro = [0.756, 0.590, 0.460]
    bars2 = axes[1].bar(np.arange(len(methods)), macro, color=[COLORS["green"], COLORS["blue"], COLORS["gray"]], width=0.62)
    axes[1].set_ylim(0, 0.84)
    axes[1].set_ylabel("Macro-F1 vs noisy follow-up reference")
    axes[1].set_title("Follow-up is best used as label-validity evidence")
    axes[1].set_xticks(np.arange(len(methods)), methods)
    axes[1].grid(axis="y", color=COLORS["light_gray"], linewidth=0.8)
    annotate_bars(axes[1], bars2)
    fig.tight_layout()
    save(fig, "result_5_label_validation")


def main():
    setup()
    evidence_ablation()
    feedback_ladder()
    generalization()
    cross_domain()
    validation_and_corroboration()
    print(f"Wrote result figures to {OUT}")


if __name__ == "__main__":
    main()
