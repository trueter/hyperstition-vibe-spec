#!/usr/bin/env python3
"""Render the two figures used by FIELD_REPORT.pdf."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
os.makedirs("img", exist_ok=True)
INK, MUTED, ACCENT, WARN = "#1a1a1a", "#8a8a8a", "#2f6fdb", "#c0392b"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False,
    "axes.spines.right": False, "figure.facecolor": "white",
})

# --- Figure 1: vibe distribution vs the spec's own trigger points -------------
buckets = ["0–9", "10–19", "20–29", "30–39", "40–49", "50–59", "60–69", "70–79", "80–89", "90–99"]
pct = [34.47, 41.97, 20.79, 1.69, 0.27, 0.16, 0.15, 0.14, 0.18, 0.18]

fig, ax = plt.subplots(figsize=(7.2, 3.1))
colors = [ACCENT if i < 3 else WARN for i in range(len(buckets))]
ax.bar(buckets, pct, color=colors, width=0.72)
for i, v in enumerate(pct):
    ax.text(i, v + 0.9, f"{v:g}%", ha="center", va="bottom", fontsize=7.5,
            color=INK if v > 1 else MUTED)
ax.set_ylabel("Share of recorded time (%)")
ax.set_xlabel("Shared vibe bucket (0–100 scale)")
ax.set_ylim(0, 50)
ax.axvspan(7.5, 9.5, color=WARN, alpha=0.07)
ax.text(8.5, 34, "PEAK_ARM = 82\n0.36% of runtime", ha="center", va="center",
        fontsize=7.5, color=WARN)
ax.set_title("Vibe never leaves the bottom third of its own scale",
             fontsize=10.5, loc="left", pad=10)
fig.text(0.01, -0.02, "109,344 one-second samples · 10 logged sessions · 19–25 Jul 2026",
         fontsize=7, color=MUTED)
fig.tight_layout()
fig.savefig("img/vibe-distribution.png", dpi=200, bbox_inches="tight")

# --- Figure 2: mean vibe by hour ---------------------------------------------
hours = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
         "20", "21", "22", "23"]
means = [15.8, 12.7, 12.4, 12.4, 11.6, 11.7, 13.7, 15.3, 15.0, 14.7, 14.5, 14.8, 27.9,
         19.5, 8.5, 5.0, 19.5]
x = list(range(len(hours)))

fig, ax = plt.subplots(figsize=(7.2, 2.9))
ax.plot(x, means, color=ACCENT, linewidth=1.8, marker="o", markersize=3.2)
ax.fill_between(x, means, color=ACCENT, alpha=0.10)
ax.axhspan(11, 16, color=MUTED, alpha=0.14)
ax.text(4.5, 16.6, "11–16 baseline holds even at 03:00 — sensor noise, not people",
        fontsize=7.5, color=MUTED)
ax.axvline(12.5, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)))
ax.text(12.6, 26, "gap: <1 min\nof data 13–19h", fontsize=6.8, color=MUTED, va="top")
ax.set_xticks(x)
ax.set_xticklabels(hours)
ax.set_ylabel("Mean shared vibe (0–100)")
ax.set_xlabel("Hour of day (venue local time, UTC+2)")
ax.set_ylim(0, 32)
ax.set_title("A detector reading the room, or reading its own noise floor?",
             fontsize=10.5, loc="left", pad=10)
fig.text(0.01, -0.03, "Mean of all per-session vibe logs, bucketed by hour · hours with <1 min of data omitted",
         fontsize=7, color=MUTED)
fig.tight_layout()
fig.savefig("img/vibe-hourly.png", dpi=200, bbox_inches="tight")

# --- Figure 3: time above the arming threshold, before and after the taper ----
labels = ["20 Jul\n17:58", "21 Jul\n18:14", "21 Jul\n23:34", "22 Jul\n23:15",
          "23 Jul\n21:13", "25 Jul\n19:32"]
a82 = [3.80, 1.00, 0.00, 0.20, 0.00, 0.00]
post = [False, False, False, False, True, True]

fig, ax = plt.subplots(figsize=(7.2, 2.8))
bars = ax.bar(labels, a82, width=0.6,
              color=[WARN if p else ACCENT for p in post])
for i, v in enumerate(a82):
    ax.text(i, v + 0.09, f"{v:.2f}%", ha="center", va="bottom", fontsize=7.5,
            color=WARN if post[i] else INK)
ax.axvline(3.5, color=INK, linewidth=1.0, linestyle=(0, (4, 3)))
ax.text(3.6, 3.3, "VIBE_FLOOR / VIBE_TAPER\nadded 23 Jul (undocumented)",
        fontsize=7.5, color=INK, va="top")
ax.text(1.5, 3.3, "escalation layer\nnot yet built", fontsize=7.5,
        color=MUTED, ha="center", va="top")
ax.set_ylabel("Share of session at vibe >= 82 (%)")
ax.set_ylim(0, 4.3)
ax.set_title("The trigger became unreachable the day the taper shipped",
             fontsize=10.5, loc="left", pad=10)
fig.text(0.01, -0.05, "Red bars are the only two sessions in which the escalation layer was actually running.",
         fontsize=7, color=MUTED)
fig.tight_layout()
fig.savefig("img/vibe-taper.png", dpi=200, bbox_inches="tight")

print("wrote img/vibe-distribution.png, img/vibe-hourly.png, img/vibe-taper.png")
