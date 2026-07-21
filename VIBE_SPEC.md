# Vibe Crowd Intensity — Spec

Source of truth: `apps/tracker/src/vibe.py` (`VibeEngine.update`, lines ~220-305).
Delivered to the web tracker page via `apps/tracker/src/tracks_bridge.py` →
`apps/web/components/TrackerLab.tsx` / `apps/web/lib/tracks/types.ts`.

## Overview

The tracker page's "vibe crowd intensity" widget derives five metrics from
person-tracking boxes: **energy**, **bounce**, **density**, **synchrony**, and
a blended **vibe** composite.

Common pipeline per channel:

1. Compute raw value.
2. Normalize against a rolling peak: `x / max(p95 over last 300s, floor)`, clipped to 1.
3. EMA smooth (`channel_tau_s = 1.5s`).
4. Weighted-sum into composite.
5. EMA smooth again (`fast_tau_s = 0.5s`) → `vibe`.

## Metrics

### Energy (`vibe.py:216, 271, 286`)

Per track: windowed displacement speed in body-heights/sec:

```
speed = hypot(dx, dy) / span / h
```

Computed over a `speed_window_s = 0.5s` window (not instantaneous vx/vy —
those are jitter-dominated per the noise-model notes at `vibe.py:25-35`).
Clipped to `MAX_SPEED_BH = 6.0`.

`energy_raw = mean(speeds)` across tracks. Normalized against `energy_floor = 0.5` bh/s.

### Bounce (`vibe.py:254-261, 273`)

Per track, over a `window_s = 2.0s` position history:

1. Linearly detrend `cy` (`resid = cy - polyfit(t, cy, 1)`) to remove camera-approach drift.
2. `track_bounce = std(resid) / mean_h`, capped at 0.5.

`bounce_raw = median(track_bounces)` across tracks — median so one flickering
box can't dominate. Requires ≥8 samples spanning ≥75% of the window.
Normalized against `bounce_floor = 0.08` bh.

### Density (`vibe.py:274`)

`density_raw = len(tracks)` — raw track count. Normalized against
`density_floor = 8.0` people via the same peak-relative p95 scheme.

### Synchrony (`vibe.py:275-280`)

Circular mean of unit displacement vectors for "moving" tracks
(speed > `move_gate = 0.2` bh/s):

```
mx = mean(ux); my = mean(uy)
synchrony_raw = hypot(mx, my)
```

1 = all aligned, 0 = vectors cancel out. Requires `min_movers = 4`, else
forced to 0 — below that the circular mean is noisy (measured 0.33/frame
jumps). Already 0..1, no normalization needed.

### Vibe composite (`vibe.py:294-299`)

```
composite = (0.40*energy + 0.25*bounce + 0.20*density + 0.15*synchrony) / sum(weights)
vibe = EMA(composite, tau=0.5s)
rising = clip(vibe - EMA(composite, tau=30s), -1, 1)   # heating-up indicator
```

## Extras

- **tempo_bpm / tempo_conf**: FFT (Hann-windowed, resampled to 20Hz) over the
  crowd's mean vertical velocity, searching the 0.8–4Hz band (48–240 BPM).
  Confidence = (peak bin + 2 neighbors) / total band power, gated at
  `tempo_conf_gate = 0.40`.
- **arms_up**: reserved for phase-2 pose keypoints, always 0 for now.

## Calibration provenance

All thresholds (floors, gates, taus, weights) were tuned empirically against
a "long-queue capture" (2026-07-20, ~3100 frames / 28 tracks) documented in
the module docstring at `vibe.py:25-45`.
