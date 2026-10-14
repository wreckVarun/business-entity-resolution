"""Charts for the README, built from the JSON reports.

Usage: python src/figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
FIG = REPORTS / "figures"

INK, MUTED, ACCENT, ACCENT2 = "#1f2937", "#6b7280", "#2563eb", "#f59e0b"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED})


def blocking() -> None:
    b = json.loads((REPORTS / "blocking.json").read_text())["by_top_k"]
    k = [r["top_k"] for r in b]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(k, [r["pair_recall"] for r in b], marker="o", color=ACCENT, label="true pairs kept (recall)")
    ax.plot(k, [r["ceiling_f05"] for r in b], marker="s", color=ACCENT2, label="best possible F0.5")
    ax.axvline(40, color=MUTED, ls="--", lw=1)
    ax.text(43, 0.27, "top-40 used", color=MUTED)
    ax.set_xscale("log")
    ax.set_xticks(k)
    ax.set_xticklabels(k)
    ax.set_xlabel("candidates kept per Source 1 entity")
    ax.set_ylim(0.2, 1.0)
    ax.set_title("Blocking: how many true matches survive", loc="left", color=INK)
    ax.legend(frameon=False, loc="center right")
    fig.tight_layout()
    fig.savefig(FIG / "blocking_recall.png", dpi=160, bbox_inches="tight")


def threshold_curve() -> None:
    v = json.loads((REPORTS / "validation.json").read_text())
    rows = v["threshold_grid"]
    best = v["best"]
    single = sorted((r for r in rows if r["t_top"] == r["t_more"]), key=lambda r: r["t_top"])
    same_top = sorted((r for r in rows if r["t_top"] == best["t_top"]), key=lambda r: r["t_more"])
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot([r["t_top"] for r in single], [r["f05"] for r in single], color=MUTED, label="one threshold for every candidate")
    ax.plot([r["t_more"] for r in same_top], [r["f05"] for r in same_top], color=ACCENT,
            label=f"best candidate at {best['t_top']}, others at x")
    ax.scatter([best["t_more"]], [best["f05"]], color=ACCENT2, zorder=3)
    ax.annotate(f"best: F0.5 {best['f05']:.4f} at {best['t_more']}", (best["t_more"], best["f05"]), xytext=(-150, -40),
                textcoords="offset points", color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_xlabel("probability threshold")
    ax.set_ylabel("entity F0.5 (validation)")
    ax.set_title("Choosing the decision thresholds", loc="left", color=INK)
    ax.legend(frameon=False, loc="lower center")
    fig.tight_layout()
    fig.savefig(FIG / "threshold_curve.png", dpi=160, bbox_inches="tight")


def importance() -> None:
    v = json.loads((REPORTS / "validation.json").read_text())
    imp = list(v["feature_importance_gain"].items())[:15][::-1]
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.barh([k for k, _ in imp], [x for _, x in imp], color=ACCENT)
    ax.set_xlabel("share of total split gain")
    ax.set_title("Top 15 features (LightGBM gain)", loc="left", color=INK)
    fig.tight_layout()
    fig.savefig(FIG / "feature_importance.png", dpi=160, bbox_inches="tight")


def loco() -> None:
    p = REPORTS / "leave_one_country_out.json"
    if not p.exists():
        return
    rows = json.loads(p.read_text())
    labels = [r["held_out_country"] for r in rows]
    x = np.arange(len(rows))
    series = [
        ("country in training data", "trained_with_it", ACCENT),
        ("country never seen, thresholds tuned on its labels", "trained_without_it", ACCENT2),
        ("country never seen, main thresholds (as for France)", "trained_without_it_main_thresholds", "#9ca3af"),
    ]
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    w = 0.26
    vals_all = []
    for i, (lab, key, col) in enumerate(series):
        vals = [r[key]["f05"] for r in rows]
        vals_all += vals
        ax.bar(x + (i - 1) * w, vals, w, color=col, label=lab)
        for xi, v in zip(x, vals):
            ax.text(xi + (i - 1) * w, v + 0.004, f"{v:.3f}", ha="center", color=INK, fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"evaluated on {c}" for c in labels])
    ax.set_ylim(min(vals_all) - 0.1, 1.02)
    ax.set_ylabel("entity F0.5")
    ax.set_title("Cost of a country the model has never seen", loc="left", color=INK)
    ax.legend(frameon=False, loc="lower center", fontsize=8, bbox_to_anchor=(0.5, -0.42), ncol=1)
    fig.tight_layout()
    fig.savefig(FIG / "leave_one_country_out.png", dpi=160, bbox_inches="tight")


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    blocking()
    threshold_curve()
    importance()
    loco()
    print("figures ->", FIG)
