"""
Comparison graph: Analytical WCRT (compute_wcrt) vs Deadline
for all 9 test cases (3 categories × 3 test cases each).

Layout
------
  Figure 1  –  3 rows (categories) × 3 cols (test cases)  per-stream bar charts
  Figure 2  –  Summary: max WCRT and WCRT-miss count across all test cases
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from src.parser import load_testcase
from src.analysis import compute_wcrt

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))

CATEGORIES = {
    "Provided": {
        "color": "#1565C0",
        "cases": [
            {
                "label": "test_case_1",
                "path": os.path.join(BASE, "examples", "test_case_1"),
            },
            {
                "label": "test_case_2",
                "path": os.path.join(BASE, "examples", "test_case_2"),
            },
            {
                "label": "test_case_3",
                "path": os.path.join(BASE, "examples", "test_case_3"),
            },
        ],
    },
    "Baseline generated": {
        "color": "#2E7D32",
        "cases": [
            {
                "label": "test_case_1",
                "path": os.path.join(BASE, "examples", "examples_simulator", "generated", "baseline", "test_case_1"),
            },
            {
                "label": "test_case_2",
                "path": os.path.join(BASE, "examples", "examples_simulator", "generated", "baseline", "test_case_2"),
            },
            {
                "label": "test_case_3",
                "path": os.path.join(BASE, "examples", "examples_simulator", "generated", "baseline", "test_case_3"),
            },
        ],
    },
    "Heavy generated": {
        "color": "#B71C1C",
        "cases": [
            {
                "label": "test_case_1",
                "path": os.path.join(BASE, "examples", "examples_simulator", "generated", "heavy", "test_case_1"),
            },
            {
                "label": "test_case_2",
                "path": os.path.join(BASE, "examples", "examples_simulator", "generated", "heavy", "test_case_2"),
            },
            {
                "label": "test_case_3",
                "path": os.path.join(BASE, "examples", "examples_simulator", "generated", "heavy", "test_case_3"),
            },
        ],
    },
}

COLOR_OK   = "#4CAF50"
COLOR_MISS = "#F44336"
COLOR_DL   = "#FF9800"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def avb_streams(streams):
    return sorted([s for s in streams if s["PCP"] > 0], key=lambda s: s["id"])


def collect(cfg):
    streams, topology, routes = load_testcase(cfg["path"])
    wcrt = compute_wcrt(streams, topology, routes)
    avb = avb_streams(streams)
    ids       = [s["id"] for s in avb]
    deadlines = [s["destinations"][0]["deadline"] for s in avb]
    analytical = [wcrt[s["id"]] for s in avb]
    return {"ids": ids, "deadlines": deadlines, "analytical": analytical}


# ---------------------------------------------------------------------------
# Figure 1 – per-stream bar charts (3 rows × 3 cols)
# ---------------------------------------------------------------------------

cat_names = list(CATEGORIES.keys())
fig1, axes1 = plt.subplots(3, 3, figsize=(20, 15))
fig1.suptitle("AVB Stream WCRT – Analytical vs Deadline (all test cases)",
              fontsize=15, fontweight="bold", y=0.99)

for row_idx, cat_name in enumerate(cat_names):
    cat = CATEGORIES[cat_name]
    for col_idx, case_cfg in enumerate(cat["cases"]):
        ax = axes1[row_idx, col_idx]
        d = collect(case_cfg)
        ids, deadlines, analytical = d["ids"], d["deadlines"], d["analytical"]
        x = np.arange(len(ids))

        colors = [COLOR_OK if w <= dl else COLOR_MISS
                  for w, dl in zip(analytical, deadlines)]
        ax.bar(x, analytical, color=colors, zorder=3, width=0.55)

        for xi, dl in zip(x, deadlines):
            ax.hlines(dl, xi - 0.38, xi + 0.38,
                      colors=COLOR_DL, linewidths=2.0, zorder=4)

        # max WCRT annotation
        max_w = max(analytical)
        max_idx = analytical.index(max_w)
        ax.annotate(f"{max_w:.1f}",
                    xy=(max_idx, max_w), xytext=(0, 6),
                    textcoords="offset points", ha="center", fontsize=7,
                    arrowprops=dict(arrowstyle="->", lw=0.7))

        ax.set_xticks(x)
        ax.set_xticklabels([f"S{i}" for i in ids], fontsize=7)
        ax.set_ylabel("WCRT [µs]", fontsize=8)
        ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
        ax.set_axisbelow(True)
        ax.set_title(f"{cat_name} – {case_cfg['label']}", fontsize=9, fontweight="bold",
                     color=cat["color"])

        misses = sum(1 for w, dl in zip(analytical, deadlines) if w > dl)
        ax.text(0.99, 0.97, f"{misses} miss / {len(ids)} streams",
                transform=ax.transAxes, ha="right", va="top", fontsize=7.5,
                color=COLOR_MISS if misses else COLOR_OK, fontweight="bold")

# Shared legend
legend_handles = [
    mpatches.Patch(color=COLOR_OK,   label="WCRT ≤ deadline"),
    mpatches.Patch(color=COLOR_MISS, label="WCRT > deadline (MISS)"),
    plt.Line2D([0], [0], color=COLOR_DL, lw=2,  label="Deadline"),
]
fig1.legend(handles=legend_handles, loc="lower center", ncol=4, fontsize=9,
            bbox_to_anchor=(0.5, 0.0))

plt.tight_layout(rect=[0, 0.04, 1, 0.98])
out1 = os.path.join(BASE, "wcrt_comparison_all.png")
plt.savefig(out1, dpi=150, bbox_inches="tight")
print(f"Figure 1 saved to: {out1}")

# ---------------------------------------------------------------------------
# Figure 2 – Summary: grouped bar chart (max WCRT + WCRT misses per test case)
# ---------------------------------------------------------------------------

fig2, (ax_wc, ax_miss) = plt.subplots(1, 2, figsize=(16, 6))
fig2.suptitle("Summary: Max Analytical WCRT and Deadline Misses – All Test Cases",
              fontsize=13, fontweight="bold")

tc_labels = ["test_case_1", "test_case_2", "test_case_3"]
n_tc = len(tc_labels)
x = np.arange(n_tc)
bar_w = 0.25
offsets = [-bar_w, 0, bar_w]

for i, (cat_name, off) in enumerate(zip(cat_names, offsets)):
    cat = CATEGORIES[cat_name]
    max_wcrts  = []
    miss_counts = []
    for case_cfg in cat["cases"]:
        d = collect(case_cfg)
        max_wcrts.append(max(d["analytical"]))
        miss_counts.append(sum(1 for w, dl in zip(d["analytical"], d["deadlines"]) if w > dl))

    bars = ax_wc.bar(x + off, max_wcrts, width=bar_w, label=cat_name,
                     color=cat["color"], zorder=3, alpha=0.85)
    for b, v in zip(bars, max_wcrts):
        ax_wc.text(b.get_x() + b.get_width() / 2, v + 15, f"{v:.0f}",
                   ha="center", va="bottom", fontsize=7.5, rotation=90)

    bars2 = ax_miss.bar(x + off, miss_counts, width=bar_w, label=cat_name,
                        color=cat["color"], zorder=3, alpha=0.85)
    for b, v in zip(bars2, miss_counts):
        if v > 0:
            ax_miss.text(b.get_x() + b.get_width() / 2, v + 0.05, str(v),
                         ha="center", va="bottom", fontsize=8, fontweight="bold")

ax_wc.set_xticks(x)
ax_wc.set_xticklabels(tc_labels)
ax_wc.set_ylabel("Max Analytical WCRT [µs]")
ax_wc.set_title("Max WCRT per Test Case")
ax_wc.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
ax_wc.set_axisbelow(True)
ax_wc.legend(fontsize=9)

ax_miss.set_xticks(x)
ax_miss.set_xticklabels(tc_labels)
ax_miss.set_ylabel("Number of streams with WCRT > deadline")
ax_miss.set_title("Deadline Misses per Test Case")
ax_miss.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
ax_miss.set_axisbelow(True)
ax_miss.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
ax_miss.legend(fontsize=9)

plt.tight_layout()
out2 = os.path.join(BASE, "wcrt_summary.png")
plt.savefig(out2, dpi=150, bbox_inches="tight")
print(f"Figure 2 saved to: {out2}")
